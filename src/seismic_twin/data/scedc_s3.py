"""
SCEDC AWS S3 Data Fetcher - Fetch seismic data from SCEDC's public S3 bucket.

SCEDC (Southern California Earthquake Data Center) hosts their complete
archive on AWS S3 without rate limits as part of the AWS Open Data program.

Bucket: s3://scedc-pds (us-west-2)
Path structure: continuous_waveforms/YYYY/YYYY_DOY/[Net][Sta][Cha][Loc]_[Year][DOY].ms
"""

import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import numpy as np

from seismic_twin.data.cache import CacheManager
from seismic_twin.data.exceptions import DataNotFoundError, NetworkError
from seismic_twin.data.records import EventInfo, GroundMotionRecord

# Constants
G_MPS2 = 9.81
SCEDC_S3_BASE_URL = "https://scedc-pds.s3.amazonaws.com"


class SCEDCS3Fetcher:
    """
    Fetch seismic data from SCEDC's public AWS S3 bucket.

    This fetcher accesses the SCEDC Public Data Set hosted on AWS S3,
    which provides unrestricted access to Southern California seismic data.

    Parameters
    ----------
    cache_dir : str or Path
        Directory for caching downloaded data.
    timeout : float
        Request timeout in seconds.

    Examples
    --------
    >>> fetcher = SCEDCS3Fetcher()
    >>> record = fetcher.get_ground_motion_record(
    ...     event_id="ci38457511",
    ...     network="CI",
    ...     station="CLC",
    ...     channel="HNE",
    ... )
    """

    # Known strong motion stations near Ridgecrest with good data
    RIDGECREST_STATIONS = [
        ("CI", "CLC", 17.5),  # China Lake - closest
        ("CI", "JRC2", 22.1),  # Junction Ranch
        ("CI", "SRT", 28.3),  # Searles
        ("CI", "TOW2", 48.2),  # Towne Pass
        ("CI", "MPM", 55.1),  # Mopi
        ("CI", "WMF", 62.4),  # Warm Springs
        ("CI", "LRL", 71.2),  # Little Lake
        ("CI", "ISA", 80.5),  # Isabella
    ]

    def __init__(
        self,
        cache_dir: Union[str, Path] = ".seismic_cache",
        timeout: float = 60.0,
    ):
        self.cache = CacheManager(cache_dir)
        self.timeout = timeout
        self._fdsn_client = None

    @property
    def fdsn_client(self):
        """Lazily initialize FDSN client for station metadata."""
        if self._fdsn_client is None:
            try:
                from obspy.clients.fdsn import Client

                # Use IRIS for station metadata (more reliable than SCEDC web service)
                self._fdsn_client = Client("IRIS", timeout=self.timeout)
            except ImportError as e:
                raise ImportError("ObsPy is required. Install with: pip install obspy") from e
        return self._fdsn_client

    def _date_to_doy(self, dt: datetime) -> tuple[int, int]:
        """Convert datetime to (year, day_of_year)."""
        return dt.year, dt.timetuple().tm_yday

    def _build_s3_url(
        self,
        network: str,
        station: str,
        channel: str,
        location: str,
        year: int,
        doy: int,
    ) -> str:
        """
        Build S3 URL for a waveform file.

        Path structure: continuous_waveforms/YYYY/YYYY_DOY/[Net][Sta]__[Cha]___[Year][DOY].ms
        Actual filename format: CICLC__HNE___2019187.ms
        - Network: 2 chars
        - Station: variable length (not padded)
        - Location: 2 chars (__  for empty)
        - Channel: 3 chars
        - Separator: ___
        - Year+DOY: 7 chars
        """
        # Location: use __ for empty/wildcard
        loc_str = location if location and location != "*" else "__"
        # Format day of year as 3 digits
        doy_str = f"{doy:03d}"

        # Format: CICLC__HNE___2019187.ms
        filename = f"{network}{station}{loc_str}{channel}___{year}{doy_str}.ms"
        path = f"continuous_waveforms/{year}/{year}_{doy_str}/{filename}"

        return f"{SCEDC_S3_BASE_URL}/{path}"

    def _download_miniseed(self, url: str) -> bytes:
        """Download miniSEED file from S3."""
        try:
            with urlopen(url, timeout=self.timeout) as response:
                return response.read()
        except HTTPError as e:
            if e.code == 404:
                raise DataNotFoundError(f"File not found: {url}") from e
            raise NetworkError(f"HTTP error {e.code} fetching {url}") from e
        except URLError as e:
            raise NetworkError(f"Network error fetching {url}: {e}") from e

    def get_ground_motion_record(
        self,
        event_id: str,
        network: str = "CI",
        station: Optional[str] = None,
        channel: str = "HNE",
        location: str = "",
        pre_event_sec: float = 10.0,
        post_event_sec: float = 90.0,
        apply_baseline_correction: bool = True,
        apply_highpass_filter: bool = True,
        highpass_freq: float = 0.1,
    ) -> GroundMotionRecord:
        """
        Fetch ground motion record from SCEDC S3.

        Parameters
        ----------
        event_id : str
            USGS event identifier (e.g., "ci38457511" for Ridgecrest).
        network : str
            Network code (default "CI" for Southern California).
        station : str, optional
            Station code. If None, tries known stations for the event.
        channel : str
            Channel code (default "HNE" for strong motion east component).
        location : str
            Location code (empty string for default).
        pre_event_sec : float
            Seconds before event to include.
        post_event_sec : float
            Seconds after event to include.
        apply_baseline_correction : bool
            Apply polynomial baseline correction.
        apply_highpass_filter : bool
            Apply highpass filter.
        highpass_freq : float
            Highpass cutoff frequency in Hz.

        Returns
        -------
        GroundMotionRecord
            Ground motion record with acceleration in g units.
        """
        from obspy import UTCDateTime, read
        from obspy.clients.fdsn import Client

        # Get event info from USGS
        event_client = Client("USGS", timeout=self.timeout)
        try:
            catalog = event_client.get_events(eventid=event_id)
            event = catalog[0]
            origin = event.preferred_origin() or event.origins[0]
            magnitude = event.preferred_magnitude() or event.magnitudes[0]
        except Exception as e:
            raise DataNotFoundError(f"Event {event_id} not found: {e}") from e

        event_info = EventInfo(
            event_id=event_id,
            origin_time=origin.time.datetime,
            latitude=origin.latitude,
            longitude=origin.longitude,
            depth_km=origin.depth / 1000.0 if origin.depth else 0.0,
            magnitude=magnitude.mag,
            magnitude_type=magnitude.magnitude_type or "Unknown",
            region=str(event.event_descriptions[0].text if event.event_descriptions else "Unknown"),
            source_catalog="USGS",
        )

        origin_time = UTCDateTime(event_info.origin_time)
        year, doy = self._date_to_doy(event_info.origin_time)

        # Stations to try
        if station:
            stations_to_try = [(network, station, 0.0)]
        else:
            # Use known stations for Ridgecrest area
            stations_to_try = self.RIDGECREST_STATIONS

        # Try each station until we find data
        last_error = None
        for net, sta, approx_dist in stations_to_try:
            # SCEDC uses __ for empty location code in filenames
            url = self._build_s3_url(net, sta, channel, "", year, doy)
            try:
                print(f"    Fetching {net}.{sta}.{channel} from S3...")
                miniseed_data = self._download_miniseed(url)

                # Parse with ObsPy
                stream = read(io.BytesIO(miniseed_data))

                if len(stream) == 0:
                    continue

                # Trim to event window
                start_time = origin_time - pre_event_sec
                end_time = origin_time + post_event_sec
                stream.trim(start_time, end_time)

                if len(stream) == 0 or len(stream[0].data) == 0:
                    continue

                trace = stream[0]

                # Get station coordinates for distance calculation
                try:
                    inventory = self.fdsn_client.get_stations(
                        network=net,
                        station=sta,
                        level="station",
                    )
                    sta_lat = inventory[0][0].latitude
                    sta_lon = inventory[0][0].longitude

                    from obspy.geodetics import gps2dist_azimuth

                    dist_m, _, _ = gps2dist_azimuth(
                        event_info.latitude, event_info.longitude, sta_lat, sta_lon
                    )
                    epicentral_distance_km = dist_m / 1000.0
                except Exception:
                    sta_lat = 0.0
                    sta_lon = 0.0
                    epicentral_distance_km = approx_dist

                # Remove instrument response to get acceleration in m/s²
                # Need to fetch instrument response from FDSN
                try:
                    inv = self.fdsn_client.get_stations(
                        network=net,
                        station=sta,
                        channel=channel,
                        level="response",
                        starttime=start_time,
                        endtime=end_time,
                    )
                    trace.attach_response(inv)
                    trace.remove_response(output="ACC")
                except Exception as resp_err:
                    # If response removal fails, we can't use this data reliably
                    print(f"    Warning: Could not remove instrument response: {resp_err}")
                    print("    Trying next station...")
                    last_error = f"Could not remove response for {net}.{sta}: {resp_err}"
                    continue

                # Extract data
                acceleration_mps2 = trace.data.astype(np.float64)
                dt = trace.stats.delta
                n_samples = len(acceleration_mps2)
                time_vec = np.arange(n_samples) * dt

                processing_history = ["instrument_response_removed"]

                # Apply processing
                if apply_baseline_correction:
                    from seismic_twin.ground_motion.synthetic import baseline_correction

                    acceleration_mps2 = baseline_correction(acceleration_mps2, dt)
                    processing_history.append("baseline_correction")

                if apply_highpass_filter:
                    from seismic_twin.ground_motion.synthetic import (
                        apply_highpass_filter as hp_filter,
                    )

                    acceleration_mps2 = hp_filter(acceleration_mps2, dt, highpass_freq)
                    processing_history.append(f"highpass_{highpass_freq}Hz")

                # Convert to g units
                acceleration_g = acceleration_mps2 / G_MPS2
                processing_history.append("converted_to_g")

                pga = float(np.max(np.abs(acceleration_g)))

                return GroundMotionRecord(
                    time=time_vec,
                    acceleration=acceleration_g,
                    dt=dt,
                    event_id=event_id,
                    network=net,
                    station=sta,
                    channel=channel,
                    component=channel[-1],
                    station_latitude=sta_lat,
                    station_longitude=sta_lon,
                    epicentral_distance_km=epicentral_distance_km,
                    pga=pga,
                    processing_history=processing_history,
                )

            except DataNotFoundError:
                last_error = f"No data at {url}"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        raise DataNotFoundError(
            f"Could not fetch data for event {event_id}. Last error: {last_error}"
        )

    def list_available_stations(
        self,
        event_id: str,
        channel: str = "HN*",
        max_distance_km: float = 100.0,
    ) -> list[tuple[str, str, float]]:
        """
        List stations that may have data for an event.

        Returns list of (network, station, distance_km) tuples.
        """
        from obspy import UTCDateTime
        from obspy.clients.fdsn import Client
        from obspy.geodetics import gps2dist_azimuth

        # Get event info
        event_client = Client("USGS", timeout=self.timeout)
        catalog = event_client.get_events(eventid=event_id)
        event = catalog[0]
        origin = event.preferred_origin() or event.origins[0]
        origin_time = UTCDateTime(origin.time)

        # Search for stations
        max_radius_deg = max_distance_km / 111.19

        try:
            inventory = self.fdsn_client.get_stations(
                latitude=origin.latitude,
                longitude=origin.longitude,
                maxradius=max_radius_deg,
                channel=channel,
                starttime=origin_time - 10,
                endtime=origin_time + 10,
                level="station",
            )
        except Exception:
            return []

        stations = []
        for network in inventory:
            for station in network:
                dist_m, _, _ = gps2dist_azimuth(
                    origin.latitude, origin.longitude, station.latitude, station.longitude
                )
                stations.append((network.code, station.code, dist_m / 1000.0))

        stations.sort(key=lambda x: x[2])
        return stations
