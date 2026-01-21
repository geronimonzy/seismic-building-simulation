"""
Ground Motion Prediction Equation (GMPE) Module

Provides implementations of GMPEs for predicting ground motion intensity
measures as a function of earthquake magnitude, distance, and site conditions.
"""

from seismic_twin.prediction.gmpe.base import BaseGMPE, GMPEInput, GMPEOutput
from seismic_twin.prediction.gmpe.boore_atkinson_2008 import BooreAtkinson2008

__all__ = [
    "BaseGMPE",
    "GMPEInput",
    "GMPEOutput",
    "BooreAtkinson2008",
]
