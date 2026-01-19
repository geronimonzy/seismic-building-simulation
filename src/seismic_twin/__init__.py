"""
Seismic Digital Twin - Building Simulation Package

A modular Python package for seismic building simulation supporting:
- Ground motion generation
- MDOF structural modeling
- Time history analysis
- Sensor-based calibration
- Uncertainty quantification
"""

from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.analysis import newmark_beta, compute_demand_metrics
from seismic_twin.calibration import StructuralCalibration
from seismic_twin.uncertainty import UncertaintyAnalysis

__version__ = "0.1.0"

__all__ = [
    "MDOFShearBuilding",
    "generate_synthetic_ground_motion",
    "newmark_beta",
    "compute_demand_metrics",
    "StructuralCalibration",
    "UncertaintyAnalysis",
]
