"""
SeismicDataFetcher - Fetch real earthquake data from USGS/FDSN networks.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np

from seismic_twin.data.cache import CacheManager
from seismic_twin.data.exceptions import DataNotFoundError, NetworkError
from seismic_twin.data.records import EventInfo, FiniteFaultModel, GroundMotionRecord

# Gravity constant for unit conversion
G_MPS2 = 9.81


class SeismicDataFetcher:
    """
    Fetch earthquake data from FDSN web services.

    Uses ObsPy to query FDSN-compliant data centers for earthquake
    event metadata and waveform data.

    Parameters
    ----------
    data_center : str
        Data center to query. One of: "USGS", "IRIS", "GFZ", "INGV",
        "EMSC", "NCEDC", "SCEDC".
    cache_dir : str or Path
        Directory for caching downloaded data.
    timeout : float
        Request timeout in seconds.

    Examples
    --------
    >>> fetcher = SeismicDataFetcher("IRIS")
    >>> events = fetcher.search_events(
    ...     start_time="2020-01-01",
    ...     end_time="2020-01-02",
    ...     min_magnitude=5.0,
    ... )
    """

    VALID_DATA_CENTERS = ["USGS", "IRIS", "GFZ", "INGV", "EMSC", "NCEDC", "SCEDC"]

    def __init__(
        self,
        data_center: str = "USGS",
        cache_dir: Union[str, Path] = ".seismic_cache",
        timeout: float = 60.0,
    ):
        if data_center.upper() not in self.VALID_DATA_CENTERS:
            raise ValueError(
                f"Invalid data center: {data_center}. Valid options: {self.VALID_DATA_CENTERS}"
            )

        self.data_center = data_center.upper()
        self.timeout = timeout
        self.cache = CacheManager(cache_dir)

        # Lazy-loaded ObsPy clients
        self._fdsn_client = None
        self._event_client = None

    @property
    def fdsn_client(self):
        """Lazily initialize FDSN waveform client."""
        if self._fdsn_client is None:
            try:
                from obspy.clients.fdsn import Client

                self._fdsn_client = Client(self.data_center, timeout=self.timeout)
            except ImportError as e:
                raise ImportError(
                    "ObsPy is required for fetching seismic data. "
                    "Install it with: pip install obspy"
                ) from e
            except Exception as e:
                raise NetworkError(f"Failed to connect to {self.data_center}: {e}") from e
        return self._fdsn_client

    @property
    def event_client(self):
        """Lazily initialize event client (uses USGS for events if available)."""
        if self._event_client is None:
            try:
                from obspy.clients.fdsn import Client

                # USGS has the most comprehensive earthquake catalog
                self._event_client = Client("USGS", timeout=self.timeout)
            except ImportError as e:
                raise ImportError(
                    "ObsPy is required for fetching seismic data. "
                    "Install it with: pip install obspy"
                ) from e
            except Exception as e:
                raise NetworkError(f"Failed to connect to event service: {e}") from e
        return self._event_client

    def search_events(
        self,
        start_time: Union[str, datetime],
        end_time: Union[str, datetime],
        min_magnitude: float = 4.0,
        max_magnitude: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        max_radius_km: Optional[float] = None,
        limit: int = 50,
    ) -> list[EventInfo]:
        """
        Search for earthquake events.

        Parameters
        ----------
        start_time : str or datetime
            Start of search window (ISO format string or datetime).
        end_time : str or datetime
            End of search window.
        min_magnitude : float
            Minimum magnitude.
        max_magnitude : float, optional
            Maximum magnitude.
        latitude : float, optional
            Center latitude for radius search.
        longitude : float, optional
            Center longitude for radius search.
        max_radius_km : float, optional
            Maximum radius in km from center point.
        limit : int
            Maximum number of events to return.

        Returns
        -------
        list[EventInfo]
            List of matching events, sorted by magnitude (descending).
        """
        from obspy import UTCDateTime

        start = UTCDateTime(start_time)
        end = UTCDateTime(end_time)

        kwargs = {
            "starttime": start,
            "endtime": end,
            "minmagnitude": min_magnitude,
            "limit": limit,
        }

        if max_magnitude is not None:
            kwargs["maxmagnitude"] = max_magnitude

        if latitude is not None and longitude is not None and max_radius_km is not None:
            kwargs["latitude"] = latitude
            kwargs["longitude"] = longitude
            kwargs["maxradius"] = max_radius_km / 111.19  # Convert km to degrees

        try:
            catalog = self.event_client.get_events(**kwargs)
        except Exception as e:
            if "No data" in str(e) or "404" in str(e):
                return []
            raise NetworkError(f"Failed to search events: {e}") from e

        events = []
        for event in catalog:
            origin = event.preferred_origin() or event.origins[0]
            magnitude = event.preferred_magnitude() or event.magnitudes[0]

            event_info = EventInfo(
                event_id=str(event.resource_id).split("/")[-1],
                origin_time=origin.time.datetime,
                latitude=origin.latitude,
                longitude=origin.longitude,
                depth_km=origin.depth / 1000.0 if origin.depth else 0.0,
                magnitude=magnitude.mag,
                magnitude_type=magnitude.magnitude_type or "Unknown",
                region=str(
                    event.event_descriptions[0].text if event.event_descriptions else "Unknown"
                ),
                source_catalog=self.data_center,
            )
            events.append(event_info)

            # Cache event info
            self.cache.save_event(event_info)

        # Sort by magnitude descending
        events.sort(key=lambda e: e.magnitude, reverse=True)
        return events

    def get_event_info(self, event_id: str) -> EventInfo:
        """
        Get information for a specific earthquake event.

        Parameters
        ----------
        event_id : str
            Event identifier (e.g., USGS event ID).

        Returns
        -------
        EventInfo
            Event information.

        Raises
        ------
        DataNotFoundError
            If the event is not found.
        """
        # Check cache first
        cached = self.cache.get_event(event_id)
        if cached is not None:
            return cached

        try:
            catalog = self.event_client.get_events(eventid=event_id)
        except Exception as e:
            raise DataNotFoundError(f"Event {event_id} not found: {e}") from e

        if len(catalog) == 0:
            raise DataNotFoundError(f"Event {event_id} not found")

        event = catalog[0]
        origin = event.preferred_origin() or event.origins[0]
        magnitude = event.preferred_magnitude() or event.magnitudes[0]

        event_info = EventInfo(
            event_id=event_id,
            origin_time=origin.time.datetime,
            latitude=origin.latitude,
            longitude=origin.longitude,
            depth_km=origin.depth / 1000.0 if origin.depth else 0.0,
            magnitude=magnitude.mag,
            magnitude_type=magnitude.magnitude_type or "Unknown",
            region=str(event.event_descriptions[0].text if event.event_descriptions else "Unknown"),
            source_catalog=self.data_center,
        )

        self.cache.save_event(event_info)
        return event_info

    def get_ground_motion_record(
        self,
        event_id: str,
        network: Optional[str] = None,
        station: Optional[str] = None,
        channel: str = "HN*",
        component: str = "E",
        max_distance_km: float = 100.0,
        pre_event_sec: float = 10.0,
        post_event_sec: float = 120.0,
        apply_baseline_correction: bool = True,
        apply_highpass_filter: bool = True,
        highpass_freq: float = 0.1,
    ) -> GroundMotionRecord:
        """
        Fetch ground motion record for an earthquake.

        Parameters
        ----------
        event_id : str
            Event identifier.
        network : str, optional
            Network code (e.g., "CI"). If None, searches nearby stations.
        station : str, optional
            Station code. If None, finds closest station.
        channel : str
            Channel code pattern (e.g., "HN*" for strong motion).
        component : str
            Component: "E" (east), "N" (north), or "Z" (vertical).
        max_distance_km : float
            Maximum distance from epicenter to search for stations.
        pre_event_sec : float
            Seconds of data before event origin.
        post_event_sec : float
            Seconds of data after event origin.
        apply_baseline_correction : bool
            Apply polynomial baseline correction.
        apply_highpass_filter : bool
            Apply highpass filter to remove drift.
        highpass_freq : float
            Highpass filter cutoff frequency in Hz.

        Returns
        -------
        GroundMotionRecord
            Ground motion record with acceleration in g units.

        Raises
        ------
        DataNotFoundError
            If no suitable waveform data is found.
        """
        from obspy import UTCDateTime
        from obspy.geodetics import gps2dist_azimuth

        # Get event info
        event_info = self.get_event_info(event_id)

        # Map component to channel suffix
        component_map = {"E": "E", "N": "N", "Z": "Z", "1": "1", "2": "2"}
        comp_suffix = component_map.get(component.upper(), "E")

        # Determine channel code
        if not channel.endswith("*"):
            full_channel = channel
        else:
            full_channel = channel[:-1] + comp_suffix

        # Check cache
        if network and station:
            cache_key = self.cache.make_waveform_key(event_id, network, station, full_channel)
            cached = self.cache.get_waveform(cache_key)
            if cached is not None:
                return cached

        # Define time window
        origin_time = UTCDateTime(event_info.origin_time)
        start_time = origin_time - pre_event_sec
        end_time = origin_time + post_event_sec

        # Find stations if not specified
        if network is None or station is None:
            network, station = self._find_nearest_station(
                event_info.latitude,
                event_info.longitude,
                origin_time,
                channel,
                max_distance_km,
            )

        # Fetch waveform
        try:
            stream = self.fdsn_client.get_waveforms(
                network=network,
                station=station,
                location="*",
                channel=full_channel,
                starttime=start_time,
                endtime=end_time,
            )
        except Exception as e:
            raise DataNotFoundError(
                f"No waveform data found for {network}.{station}.{full_channel}: {e}"
            ) from e

        if len(stream) == 0:
            raise DataNotFoundError(
                f"No waveform data found for {network}.{station}.{full_channel}"
            )

        # Get first trace
        trace = stream[0]

        # Remove instrument response to get acceleration in m/s²
        try:
            trace.remove_response(output="ACC")
        except Exception:
            # If response removal fails, data may already be in physical units
            pass

        # Get station coordinates
        try:
            inventory = self.fdsn_client.get_stations(
                network=network,
                station=station,
                level="station",
            )
            sta_lat = inventory[0][0].latitude
            sta_lon = inventory[0][0].longitude
        except Exception:
            sta_lat = 0.0
            sta_lon = 0.0

        # Calculate epicentral distance
        if sta_lat != 0.0 and sta_lon != 0.0:
            dist_m, _, _ = gps2dist_azimuth(
                event_info.latitude, event_info.longitude, sta_lat, sta_lon
            )
            epicentral_distance_km = dist_m / 1000.0
        else:
            epicentral_distance_km = 0.0

        # Extract data
        acceleration_mps2 = trace.data.astype(np.float64)
        dt = trace.stats.delta
        n_samples = len(acceleration_mps2)
        time = np.arange(n_samples) * dt

        # Processing history
        processing_history = ["instrument_response_removed"]

        # Apply processing
        if apply_baseline_correction:
            from seismic_twin.ground_motion.synthetic import baseline_correction

            acceleration_mps2 = baseline_correction(acceleration_mps2, dt)
            processing_history.append("baseline_correction")

        if apply_highpass_filter:
            from seismic_twin.ground_motion.synthetic import apply_highpass_filter as hp_filter

            acceleration_mps2 = hp_filter(acceleration_mps2, dt, highpass_freq)
            processing_history.append(f"highpass_filter_{highpass_freq}Hz")

        # Convert to g units
        acceleration_g = acceleration_mps2 / G_MPS2
        processing_history.append("converted_to_g")

        # Calculate PGA
        pga = float(np.max(np.abs(acceleration_g)))

        record = GroundMotionRecord(
            time=time,
            acceleration=acceleration_g,
            dt=dt,
            event_id=event_id,
            network=network,
            station=station,
            channel=full_channel,
            component=component.upper(),
            station_latitude=sta_lat,
            station_longitude=sta_lon,
            epicentral_distance_km=epicentral_distance_km,
            pga=pga,
            processing_history=processing_history,
        )

        # Cache the result
        cache_key = self.cache.make_waveform_key(event_id, network, station, full_channel)
        self.cache.save_waveform(cache_key, record)

        return record

    def _find_nearest_station(
        self,
        lat: float,
        lon: float,
        origin_time,
        channel: str,
        max_distance_km: float,
    ) -> tuple[str, str]:
        """Find the nearest station with data for the given event."""
        from obspy.geodetics import gps2dist_azimuth

        max_radius_deg = max_distance_km / 111.19

        try:
            inventory = self.fdsn_client.get_stations(
                latitude=lat,
                longitude=lon,
                maxradius=max_radius_deg,
                channel=channel,
                starttime=origin_time - 10,
                endtime=origin_time + 10,
                level="station",
            )
        except Exception as e:
            raise DataNotFoundError(
                f"No stations found within {max_distance_km} km of event: {e}"
            ) from e

        if len(inventory) == 0:
            raise DataNotFoundError(f"No stations found within {max_distance_km} km of event")

        # Find closest station
        min_dist = float("inf")
        best_network = None
        best_station = None

        for network in inventory:
            for station in network:
                dist_m, _, _ = gps2dist_azimuth(lat, lon, station.latitude, station.longitude)
                if dist_m < min_dist:
                    min_dist = dist_m
                    best_network = network.code
                    best_station = station.code

        if best_network is None:
            raise DataNotFoundError("No suitable station found")

        return best_network, best_station

    def get_all_ground_motion_records(
        self,
        event_id: str,
        channel: str = "HN*",
        max_distance_km: float = 100.0,
        max_stations: int = 10,
        **kwargs,
    ) -> list[GroundMotionRecord]:
        """
        Fetch ground motion records from multiple stations.

        Parameters
        ----------
        event_id : str
            Event identifier.
        channel : str
            Channel code pattern.
        max_distance_km : float
            Maximum distance from epicenter.
        max_stations : int
            Maximum number of stations to fetch.
        **kwargs
            Additional arguments passed to get_ground_motion_record.

        Returns
        -------
        list[GroundMotionRecord]
            List of ground motion records, sorted by distance.
        """
        from obspy import UTCDateTime
        from obspy.geodetics import gps2dist_azimuth

        event_info = self.get_event_info(event_id)
        origin_time = UTCDateTime(event_info.origin_time)

        max_radius_deg = max_distance_km / 111.19

        try:
            inventory = self.fdsn_client.get_stations(
                latitude=event_info.latitude,
                longitude=event_info.longitude,
                maxradius=max_radius_deg,
                channel=channel,
                starttime=origin_time - 10,
                endtime=origin_time + 10,
                level="station",
            )
        except Exception as e:
            raise DataNotFoundError(f"No stations found: {e}") from e

        # Collect stations with distances
        stations = []
        for network in inventory:
            for station in network:
                dist_m, _, _ = gps2dist_azimuth(
                    event_info.latitude,
                    event_info.longitude,
                    station.latitude,
                    station.longitude,
                )
                stations.append((network.code, station.code, dist_m / 1000.0))

        # Sort by distance and limit
        stations.sort(key=lambda x: x[2])
        stations = stations[:max_stations]

        # Fetch records
        records = []
        for net, sta, _ in stations:
            try:
                record = self.get_ground_motion_record(
                    event_id=event_id,
                    network=net,
                    station=sta,
                    channel=channel,
                    **kwargs,
                )
                records.append(record)
            except DataNotFoundError:
                continue

        return records

    def get_finite_fault_model(self, event_id: str, source: str = "usgs") -> FiniteFaultModel:
        """
        Get finite fault model for an earthquake.

        Parameters
        ----------
        event_id : str
            Event identifier.
        source : str
            Source for finite fault model: "usgs" or "gcmt".

        Returns
        -------
        FiniteFaultModel
            Finite fault model parameters.

        Raises
        ------
        DataNotFoundError
            If no finite fault model is available.
        """
        import requests

        cache_key = self.cache.make_finite_fault_key(event_id)
        cached = self.cache.get_finite_fault(cache_key)
        if cached is not None:
            return cached

        # Try USGS finite fault API
        if source.lower() == "usgs":
            try:
                response = requests.get(
                    "https://earthquake.usgs.gov/fdsnws/event/1/query",
                    params={
                        "eventid": event_id,
                        "format": "geojson",
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                raise DataNotFoundError(f"Failed to fetch finite fault model: {e}") from e

            properties = data.get("properties", {})
            products = properties.get("products", {})
            finite_fault_products = products.get("finite-fault", [])

            if not finite_fault_products:
                raise DataNotFoundError(f"No finite fault model available for {event_id}")

            ff_data = finite_fault_products[0].get("properties", {})

            # Extract basic parameters (actual values may need parsing from files)
            event_info = self.get_event_info(event_id)

            model = FiniteFaultModel(
                event_id=event_id,
                hypocenter=(
                    event_info.latitude,
                    event_info.longitude,
                    event_info.depth_km,
                ),
                strike=float(ff_data.get("strike", 0)),
                dip=float(ff_data.get("dip", 0)),
                rake=float(ff_data.get("rake", 0)),
                length_km=float(ff_data.get("length", 0)),
                width_km=float(ff_data.get("width", 0)),
                moment_tensor=None,
                source="usgs",
            )

            self.cache.save_finite_fault(cache_key, model)
            return model

        raise DataNotFoundError(f"Unsupported finite fault source: {source}")


def fetch_ground_motion_record(
    event_id: str,
    station: Optional[str] = None,
    component: str = "E",
    data_center: str = "USGS",
    **kwargs,
) -> GroundMotionRecord:
    """
    Convenience function to fetch a ground motion record.

    Parameters
    ----------
    event_id : str
        Event identifier.
    station : str, optional
        Station code. If None, finds closest station.
    component : str
        Component direction: "E", "N", or "Z".
    data_center : str
        Data center to use.
    **kwargs
        Additional arguments passed to SeismicDataFetcher.get_ground_motion_record.

    Returns
    -------
    GroundMotionRecord
        Ground motion record.

    Examples
    --------
    >>> record = fetch_ground_motion_record("us7000abcd", component="E")
    >>> time, acc = record.to_tuple()
    """
    fetcher = SeismicDataFetcher(data_center=data_center)
    return fetcher.get_ground_motion_record(
        event_id=event_id,
        station=station,
        component=component,
        **kwargs,
    )
