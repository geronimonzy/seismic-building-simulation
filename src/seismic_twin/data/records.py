"""
Data structures for seismic records.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
from numpy.typing import NDArray


@dataclass
class GroundMotionRecord:
    """
    Ground motion record with metadata.

    This dataclass holds acceleration time history data along with
    associated metadata from seismic networks.

    Attributes
    ----------
    time : NDArray
        Time vector in seconds.
    acceleration : NDArray
        Ground acceleration time history in g units.
    dt : float
        Time step in seconds.
    event_id : str
        Unique earthquake event identifier.
    network : str
        Seismic network code (e.g., "US", "CI").
    station : str
        Station code.
    channel : str
        Channel code (e.g., "HNE", "BHZ").
    component : str
        Component direction: "E" (east), "N" (north), or "Z" (vertical).
    station_latitude : float
        Station latitude in degrees.
    station_longitude : float
        Station longitude in degrees.
    epicentral_distance_km : float
        Distance from earthquake epicenter to station in km.
    pga : float
        Peak ground acceleration in g.
    processing_history : list[str]
        List of processing steps applied to the record.
    units : str
        Acceleration units, always "g".
    """

    time: NDArray[np.floating]
    acceleration: NDArray[np.floating]
    dt: float
    event_id: str
    network: str
    station: str
    channel: str
    component: str
    station_latitude: float
    station_longitude: float
    epicentral_distance_km: float
    pga: float
    processing_history: list[str] = field(default_factory=list)
    units: str = "g"

    def to_tuple(self) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """
        Convert to tuple format for backward compatibility.

        Returns tuple (time, acceleration) matching the format
        returned by generate_synthetic_ground_motion().

        Returns
        -------
        tuple[NDArray, NDArray]
            (time, acceleration) tuple.
        """
        return self.time, self.acceleration


@dataclass
class EventInfo:
    """
    Earthquake event information.

    Attributes
    ----------
    event_id : str
        Unique event identifier (e.g., USGS event ID).
    origin_time : datetime
        Origin time of the earthquake.
    latitude : float
        Epicenter latitude in degrees.
    longitude : float
        Epicenter longitude in degrees.
    depth_km : float
        Hypocenter depth in kilometers.
    magnitude : float
        Earthquake magnitude.
    magnitude_type : str
        Magnitude type (e.g., "Mw", "mb", "ML").
    region : str
        Geographic region description.
    source_catalog : str
        Source catalog (e.g., "USGS", "IRIS").
    """

    event_id: str
    origin_time: datetime
    latitude: float
    longitude: float
    depth_km: float
    magnitude: float
    magnitude_type: str
    region: str
    source_catalog: str


@dataclass
class FiniteFaultModel:
    """
    Finite fault model for an earthquake.

    Attributes
    ----------
    event_id : str
        Unique event identifier.
    hypocenter : tuple[float, float, float]
        Hypocenter coordinates (latitude, longitude, depth_km).
    strike : float
        Fault strike angle in degrees.
    dip : float
        Fault dip angle in degrees.
    rake : float
        Fault rake angle in degrees.
    length_km : float
        Fault length in kilometers.
    width_km : float
        Fault width in kilometers.
    moment_tensor : Optional[dict]
        Moment tensor components (Mxx, Myy, Mzz, Mxy, Mxz, Myz).
    source : str
        Source of the finite fault model (e.g., "usgs", "gcmt").
    """

    event_id: str
    hypocenter: tuple[float, float, float]
    strike: float
    dip: float
    rake: float
    length_km: float
    width_km: float
    moment_tensor: Optional[dict]
    source: str
