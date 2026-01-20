"""
Cache management for seismic data.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import numpy as np

from seismic_twin.data.exceptions import CacheError
from seismic_twin.data.records import EventInfo, FiniteFaultModel, GroundMotionRecord


class CacheManager:
    """
    Manages caching of seismic data to avoid repeated network requests.

    Cache structure:
        .seismic_cache/
            events/{event_id}.json
            waveforms/{event_id}_{net}_{sta}_{chan}.npz
            finite_faults/{event_id}_ff.json

    Parameters
    ----------
    cache_dir : Path or str
        Directory to store cached data. Defaults to ".seismic_cache".
        Can be overridden by SEISMIC_CACHE_DIR environment variable.
    """

    def __init__(self, cache_dir: Optional[Union[Path, str]] = None):
        if cache_dir is None:
            cache_dir = os.environ.get("SEISMIC_CACHE_DIR", ".seismic_cache")
        self.cache_dir = Path(cache_dir)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create cache directory structure if it doesn't exist."""
        try:
            (self.cache_dir / "events").mkdir(parents=True, exist_ok=True)
            (self.cache_dir / "waveforms").mkdir(parents=True, exist_ok=True)
            (self.cache_dir / "finite_faults").mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise CacheError(f"Failed to create cache directories: {e}") from e

    def _event_path(self, event_id: str) -> Path:
        """Get path for event cache file."""
        return self.cache_dir / "events" / f"{event_id}.json"

    def _waveform_path(self, cache_key: str) -> Path:
        """Get path for waveform cache file."""
        return self.cache_dir / "waveforms" / f"{cache_key}.npz"

    def _finite_fault_path(self, cache_key: str) -> Path:
        """Get path for finite fault cache file."""
        return self.cache_dir / "finite_faults" / f"{cache_key}.json"

    def get_event(self, event_id: str) -> Optional[EventInfo]:
        """
        Retrieve cached event information.

        Parameters
        ----------
        event_id : str
            Unique event identifier.

        Returns
        -------
        EventInfo or None
            Cached event info, or None if not in cache.
        """
        path = self._event_path(event_id)
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return EventInfo(
                event_id=data["event_id"],
                origin_time=datetime.fromisoformat(data["origin_time"]),
                latitude=data["latitude"],
                longitude=data["longitude"],
                depth_km=data["depth_km"],
                magnitude=data["magnitude"],
                magnitude_type=data["magnitude_type"],
                region=data["region"],
                source_catalog=data["source_catalog"],
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise CacheError(f"Failed to read event cache: {e}") from e

    def save_event(self, event: EventInfo) -> None:
        """
        Save event information to cache.

        Parameters
        ----------
        event : EventInfo
            Event information to cache.
        """
        path = self._event_path(event.event_id)
        data = {
            "event_id": event.event_id,
            "origin_time": event.origin_time.isoformat(),
            "latitude": event.latitude,
            "longitude": event.longitude,
            "depth_km": event.depth_km,
            "magnitude": event.magnitude,
            "magnitude_type": event.magnitude_type,
            "region": event.region,
            "source_catalog": event.source_catalog,
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise CacheError(f"Failed to write event cache: {e}") from e

    def get_waveform(self, cache_key: str) -> Optional[GroundMotionRecord]:
        """
        Retrieve cached waveform data.

        Parameters
        ----------
        cache_key : str
            Cache key in format: {event_id}_{network}_{station}_{channel}.

        Returns
        -------
        GroundMotionRecord or None
            Cached record, or None if not in cache.
        """
        path = self._waveform_path(cache_key)
        if not path.exists():
            return None

        try:
            data = np.load(path, allow_pickle=True)
            return GroundMotionRecord(
                time=data["time"],
                acceleration=data["acceleration"],
                dt=float(data["dt"]),
                event_id=str(data["event_id"]),
                network=str(data["network"]),
                station=str(data["station"]),
                channel=str(data["channel"]),
                component=str(data["component"]),
                station_latitude=float(data["station_latitude"]),
                station_longitude=float(data["station_longitude"]),
                epicentral_distance_km=float(data["epicentral_distance_km"]),
                pga=float(data["pga"]),
                processing_history=list(data["processing_history"]),
                units=str(data["units"]),
            )
        except (OSError, KeyError, ValueError) as e:
            raise CacheError(f"Failed to read waveform cache: {e}") from e

    def save_waveform(self, cache_key: str, record: GroundMotionRecord) -> None:
        """
        Save waveform data to cache.

        Parameters
        ----------
        cache_key : str
            Cache key in format: {event_id}_{network}_{station}_{channel}.
        record : GroundMotionRecord
            Record to cache.
        """
        path = self._waveform_path(cache_key)
        try:
            np.savez(
                path,
                time=record.time,
                acceleration=record.acceleration,
                dt=record.dt,
                event_id=record.event_id,
                network=record.network,
                station=record.station,
                channel=record.channel,
                component=record.component,
                station_latitude=record.station_latitude,
                station_longitude=record.station_longitude,
                epicentral_distance_km=record.epicentral_distance_km,
                pga=record.pga,
                processing_history=record.processing_history,
                units=record.units,
            )
        except OSError as e:
            raise CacheError(f"Failed to write waveform cache: {e}") from e

    def get_finite_fault(self, cache_key: str) -> Optional[FiniteFaultModel]:
        """
        Retrieve cached finite fault model.

        Parameters
        ----------
        cache_key : str
            Cache key in format: {event_id}_ff.

        Returns
        -------
        FiniteFaultModel or None
            Cached model, or None if not in cache.
        """
        path = self._finite_fault_path(cache_key)
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return FiniteFaultModel(
                event_id=data["event_id"],
                hypocenter=tuple(data["hypocenter"]),
                strike=data["strike"],
                dip=data["dip"],
                rake=data["rake"],
                length_km=data["length_km"],
                width_km=data["width_km"],
                moment_tensor=data.get("moment_tensor"),
                source=data["source"],
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise CacheError(f"Failed to read finite fault cache: {e}") from e

    def save_finite_fault(self, cache_key: str, model: FiniteFaultModel) -> None:
        """
        Save finite fault model to cache.

        Parameters
        ----------
        cache_key : str
            Cache key in format: {event_id}_ff.
        model : FiniteFaultModel
            Model to cache.
        """
        path = self._finite_fault_path(cache_key)
        data = {
            "event_id": model.event_id,
            "hypocenter": list(model.hypocenter),
            "strike": model.strike,
            "dip": model.dip,
            "rake": model.rake,
            "length_km": model.length_km,
            "width_km": model.width_km,
            "moment_tensor": model.moment_tensor,
            "source": model.source,
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise CacheError(f"Failed to write finite fault cache: {e}") from e

    def clear(self) -> None:
        """Clear all cached data."""
        import shutil

        try:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
            self._ensure_directories()
        except OSError as e:
            raise CacheError(f"Failed to clear cache: {e}") from e

    def make_waveform_key(
        self, event_id: str, network: str, station: str, channel: str
    ) -> str:
        """
        Generate cache key for waveform data.

        Parameters
        ----------
        event_id : str
            Event identifier.
        network : str
            Network code.
        station : str
            Station code.
        channel : str
            Channel code.

        Returns
        -------
        str
            Cache key.
        """
        return f"{event_id}_{network}_{station}_{channel}"

    def make_finite_fault_key(self, event_id: str) -> str:
        """
        Generate cache key for finite fault model.

        Parameters
        ----------
        event_id : str
            Event identifier.

        Returns
        -------
        str
            Cache key.
        """
        return f"{event_id}_ff"
