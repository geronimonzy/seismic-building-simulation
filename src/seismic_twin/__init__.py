"""
Seismic Digital Twin - Building Simulation Package

A modular Python package for seismic building simulation supporting:
- Ground motion generation
- MDOF structural modeling
- Time history analysis
- Sensor-based calibration
- Uncertainty quantification
- Real earthquake data fetching (SeismoHub)
"""

from seismic_twin.analysis import compute_demand_metrics, newmark_beta
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.calibration import StructuralCalibration
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.uncertainty import UncertaintyAnalysis

__version__ = "0.1.0"

__all__ = [
    "MDOFShearBuilding",
    "generate_synthetic_ground_motion",
    "newmark_beta",
    "compute_demand_metrics",
    "StructuralCalibration",
    "UncertaintyAnalysis",
    # Data fetching (lazy imports)
    "SeismicDataFetcher",
    "fetch_ground_motion_record",
]


# Lazy imports for SeismoHub to avoid ObsPy import overhead
def __getattr__(name: str):
    if name == "SeismicDataFetcher":
        from seismic_twin.data import SeismicDataFetcher

        return SeismicDataFetcher
    if name == "fetch_ground_motion_record":
        from seismic_twin.data import fetch_ground_motion_record

        return fetch_ground_motion_record
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
