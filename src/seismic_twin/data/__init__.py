"""
SeismoHub - Real earthquake data fetching module.

This module provides tools for fetching real earthquake data from
USGS/FDSN networks using ObsPy.
"""

from seismic_twin.data.cache import CacheManager
from seismic_twin.data.exceptions import (
    CacheError,
    DataNotFoundError,
    NetworkError,
    SeismoHubError,
)
from seismic_twin.data.records import EventInfo, FiniteFaultModel, GroundMotionRecord

__all__ = [
    # Data classes
    "GroundMotionRecord",
    "EventInfo",
    "FiniteFaultModel",
    # Exceptions
    "SeismoHubError",
    "DataNotFoundError",
    "NetworkError",
    "CacheError",
    # Cache
    "CacheManager",
]

# Lazy imports for fetcher to avoid ObsPy import overhead
def __getattr__(name: str):
    if name in ("SeismicDataFetcher", "fetch_ground_motion_record"):
        from seismic_twin.data.fetcher import SeismicDataFetcher, fetch_ground_motion_record
        if name == "SeismicDataFetcher":
            return SeismicDataFetcher
        return fetch_ground_motion_record
    if name == "SCEDCS3Fetcher":
        from seismic_twin.data.scedc_s3 import SCEDCS3Fetcher
        return SCEDCS3Fetcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
