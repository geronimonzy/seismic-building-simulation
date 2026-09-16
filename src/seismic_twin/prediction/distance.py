"""
Distance Calculations for Seismic Analysis

This module provides functions for computing various distance metrics
used in ground motion prediction, including epicentral distance and
Joyner-Boore distance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from seismic_twin.data.records import FiniteFaultModel

# Earth's mean radius in km
EARTH_RADIUS_KM = 6371.0


def compute_epicentral_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Compute epicentral distance using Haversine formula.

    Parameters
    ----------
    lat1 : float
        Latitude of first point in degrees.
    lon1 : float
        Longitude of first point in degrees.
    lat2 : float
        Latitude of second point in degrees.
    lon2 : float
        Longitude of second point in degrees.

    Returns
    -------
    float
        Distance in kilometers.

    Notes
    -----
    Uses the Haversine formula which gives great-circle distance
    between two points on a sphere.
    """
    # Convert to radians
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    # Haversine formula
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def compute_rjb_distance(
    station_lat: float,
    station_lon: float,
    epicenter_lat: float,
    epicenter_lon: float,
    magnitude: float,
    fault_model: FiniteFaultModel | None = None,
) -> float:
    """
    Compute Joyner-Boore distance (Rjb).

    Rjb is the closest distance to the surface projection of the fault.
    For point sources (M < 6 or no fault model), Rjb is approximated
    as the epicentral distance.

    Parameters
    ----------
    station_lat : float
        Station latitude in degrees.
    station_lon : float
        Station longitude in degrees.
    epicenter_lat : float
        Earthquake epicenter latitude in degrees.
    epicenter_lon : float
        Earthquake epicenter longitude in degrees.
    magnitude : float
        Earthquake magnitude.
    fault_model : FiniteFaultModel, optional
        Finite fault model for the earthquake.

    Returns
    -------
    float
        Joyner-Boore distance in kilometers.

    Notes
    -----
    For moderate earthquakes (M < 6) or when no fault model is available,
    the difference between Rjb and Repi is typically small. This function
    uses the point-source approximation in those cases.

    For larger events with a fault model, the distance is computed to the
    closest point on the surface projection of the fault.
    """
    # Compute epicentral distance
    repi = compute_epicentral_distance(station_lat, station_lon, epicenter_lat, epicenter_lon)

    # For small events or no fault model, use point source approximation
    if magnitude < 6.0 or fault_model is None:
        return repi

    # For larger events with fault model, compute distance to fault surface
    rjb = _compute_rjb_from_fault(station_lat, station_lon, fault_model)

    return rjb


def _compute_rjb_from_fault(
    station_lat: float,
    station_lon: float,
    fault_model: FiniteFaultModel,
) -> float:
    """
    Compute Rjb from a finite fault model.

    This computes the closest distance from the station to the
    surface projection of the fault plane.

    Parameters
    ----------
    station_lat : float
        Station latitude in degrees.
    station_lon : float
        Station longitude in degrees.
    fault_model : FiniteFaultModel
        Finite fault model with geometry.

    Returns
    -------
    float
        Joyner-Boore distance in km.
    """
    # Extract fault parameters
    hypo_lat, hypo_lon, _ = fault_model.hypocenter
    length = fault_model.length_km
    dip = np.radians(fault_model.dip)
    width = fault_model.width_km

    # Surface projection width (horizontal extent)
    surface_width = width * np.cos(dip)

    # Compute fault corners in local coordinate system
    # Origin at hypocenter, x = along strike, y = perpendicular
    half_length = length / 2

    # Convert station to local coordinates relative to hypocenter
    station_dist = compute_epicentral_distance(hypo_lat, hypo_lon, station_lat, station_lon)

    # Bearing from hypocenter to station
    bearing = _compute_bearing(hypo_lat, hypo_lon, station_lat, station_lon)

    # Relative bearing (station bearing minus fault strike)
    rel_bearing = bearing - fault_model.strike

    # Station position in fault-aligned coordinates
    x_station = station_dist * np.sin(np.radians(rel_bearing))  # Along strike
    y_station = station_dist * np.cos(np.radians(rel_bearing))  # Perpendicular

    # Fault rectangle corners (surface projection)
    # Assuming hypocenter is at center of fault
    x_min = -half_length
    x_max = half_length
    y_min = 0  # At surface trace
    y_max = surface_width  # Downdip edge surface projection

    # Find closest point on rectangle to station
    closest_x = np.clip(x_station, x_min, x_max)
    closest_y = np.clip(y_station, y_min, y_max)

    # Distance to closest point
    rjb = np.sqrt((x_station - closest_x) ** 2 + (y_station - closest_y) ** 2)

    return rjb


def _compute_bearing(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Compute bearing from point 1 to point 2.

    Parameters
    ----------
    lat1, lon1 : float
        First point coordinates in degrees.
    lat2, lon2 : float
        Second point coordinates in degrees.

    Returns
    -------
    float
        Bearing in degrees (0-360, clockwise from north).
    """
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlon = np.radians(lon2 - lon1)

    x = np.sin(dlon) * np.cos(lat2_rad)
    y = np.cos(lat1_rad) * np.sin(lat2_rad) - np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(dlon)

    bearing = np.degrees(np.arctan2(x, y))
    return (bearing + 360) % 360


def compute_hypocentral_distance(
    station_lat: float,
    station_lon: float,
    epicenter_lat: float,
    epicenter_lon: float,
    depth_km: float,
) -> float:
    """
    Compute hypocentral distance.

    Parameters
    ----------
    station_lat : float
        Station latitude in degrees.
    station_lon : float
        Station longitude in degrees.
    epicenter_lat : float
        Epicenter latitude in degrees.
    epicenter_lon : float
        Epicenter longitude in degrees.
    depth_km : float
        Hypocenter depth in kilometers.

    Returns
    -------
    float
        Hypocentral distance in kilometers.
    """
    repi = compute_epicentral_distance(station_lat, station_lon, epicenter_lat, epicenter_lon)
    return np.sqrt(repi**2 + depth_km**2)


def compute_rupture_distance(
    station_lat: float,
    station_lon: float,
    fault_model: FiniteFaultModel,
) -> float:
    """
    Compute rupture distance (Rrup) - closest distance to fault surface.

    Parameters
    ----------
    station_lat : float
        Station latitude in degrees.
    station_lon : float
        Station longitude in degrees.
    fault_model : FiniteFaultModel
        Finite fault model.

    Returns
    -------
    float
        Rupture distance in kilometers.

    Notes
    -----
    This is a simplified implementation that approximates Rrup
    using the hypocentral distance and fault geometry.
    """
    hypo_lat, hypo_lon, depth_km = fault_model.hypocenter

    # Compute horizontal distance (Rjb)
    rjb = _compute_rjb_from_fault(station_lat, station_lon, fault_model)

    # Estimate vertical distance to fault
    # For sites over the fault, use depth directly
    # For sites outside, combine with horizontal distance
    dip = np.radians(fault_model.dip)
    width = fault_model.width_km

    # Simplified: use Pythagoras with depth
    # More accurate would project to fault plane
    ztor = max(0, depth_km - width * np.sin(dip) / 2)  # Top of rupture depth

    return np.sqrt(rjb**2 + ztor**2)
