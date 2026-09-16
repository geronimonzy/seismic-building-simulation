"""
Wave Propagation Prediction Module

This module provides GMPE-based wave propagation prediction functionality
for predicting ground motion at target locations using waveforms from
nearby seismic stations.
"""

from seismic_twin.prediction.distance import (
    compute_epicentral_distance,
    compute_rjb_distance,
)
from seismic_twin.prediction.gmpe import BaseGMPE, BooreAtkinson2008, GMPEInput, GMPEOutput
from seismic_twin.prediction.validation import (
    PeakMetrics,
    PredictionValidator,
    SpectrumMetrics,
    TimeSeriesMetrics,
    ValidationResult,
    ValidationSummary,
)
from seismic_twin.prediction.waveform_prediction import (
    StationPrediction,
    WaveformPredictor,
)

__all__ = [
    # GMPE classes
    "BaseGMPE",
    "BooreAtkinson2008",
    "GMPEInput",
    "GMPEOutput",
    # Distance functions
    "compute_epicentral_distance",
    "compute_rjb_distance",
    # Waveform prediction
    "StationPrediction",
    "WaveformPredictor",
    # Validation
    "PeakMetrics",
    "SpectrumMetrics",
    "TimeSeriesMetrics",
    "ValidationResult",
    "ValidationSummary",
    "PredictionValidator",
]
