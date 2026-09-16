"""
Prediction Validation Module

This module provides functionality for validating wave propagation predictions
against actual recordings, computing various metrics including peak values,
spectral comparisons, and time-series similarity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from seismic_twin.analysis.metrics import (
    compute_arias_intensity,
    compute_correlation,
    compute_nrmse,
)
from seismic_twin.ground_motion.synthetic import compute_response_spectrum

if TYPE_CHECKING:
    from seismic_twin.prediction.waveform_prediction import PredictionPair


@dataclass
class PeakMetrics:
    """
    Peak ground motion comparison metrics.

    Attributes
    ----------
    actual_pga : float
        Actual peak ground acceleration in g.
    predicted_pga : float
        Predicted peak ground acceleration in g.
    pga_ratio : float
        Ratio of predicted to actual PGA.
    pga_error_percent : float
        Percentage error in PGA prediction.
    """

    actual_pga: float
    predicted_pga: float
    pga_ratio: float
    pga_error_percent: float


@dataclass
class SpectrumMetrics:
    """
    Response spectrum comparison metrics.

    Attributes
    ----------
    periods : NDArray
        Spectral periods in seconds.
    actual_sa : NDArray
        Actual spectral acceleration values in g.
    predicted_sa : NDArray
        Predicted spectral acceleration values in g.
    mean_sa_ratio : float
        Mean ratio of predicted to actual Sa across all periods.
    gof_short_period : float
        Goodness of fit for short periods (T < 0.5s).
    gof_mid_period : float
        Goodness of fit for mid periods (0.5s <= T < 2s).
    gof_long_period : float
        Goodness of fit for long periods (T >= 2s).
    """

    periods: NDArray[np.floating]
    actual_sa: NDArray[np.floating]
    predicted_sa: NDArray[np.floating]
    mean_sa_ratio: float
    gof_short_period: float
    gof_mid_period: float
    gof_long_period: float


@dataclass
class TimeSeriesMetrics:
    """
    Time series comparison metrics.

    Attributes
    ----------
    nrmse : float
        Normalized root mean square error.
    correlation : float
        Pearson correlation coefficient.
    arias_ratio : float
        Ratio of predicted to actual Arias intensity.
    phase_goodness : float
        Goodness of phase alignment (0-1).
    """

    nrmse: float
    correlation: float
    arias_ratio: float
    phase_goodness: float


@dataclass
class ValidationResult:
    """
    Complete validation result for a single station prediction.

    Attributes
    ----------
    station_id : str
        Station identifier.
    distance_km : float
        Station distance from epicenter in km.
    peak_metrics : PeakMetrics
        Peak value comparison metrics.
    spectrum_metrics : SpectrumMetrics
        Spectral comparison metrics.
    timeseries_metrics : TimeSeriesMetrics
        Time series comparison metrics.
    overall_score : float
        Combined validation score (0-1, higher is better).
    quality_grade : str
        Quality grade: A (>=0.8), B (>=0.6), C (>=0.4), D (>=0.2), F (<0.2).
    """

    station_id: str
    distance_km: float
    peak_metrics: PeakMetrics
    spectrum_metrics: SpectrumMetrics
    timeseries_metrics: TimeSeriesMetrics
    overall_score: float
    quality_grade: str


@dataclass
class ValidationSummary:
    """
    Summary of validation results across multiple stations.

    Attributes
    ----------
    n_stations : int
        Number of stations validated.
    mean_pga_ratio : float
        Mean PGA prediction ratio.
    std_pga_ratio : float
        Standard deviation of PGA ratio.
    mean_correlation : float
        Mean waveform correlation.
    mean_overall_score : float
        Mean overall validation score.
    individual_results : list[ValidationResult]
        Results for each individual station.
    """

    n_stations: int
    mean_pga_ratio: float
    std_pga_ratio: float
    mean_correlation: float
    mean_overall_score: float
    individual_results: list[ValidationResult] = field(default_factory=list)


class PredictionValidator:
    """
    Validates wave propagation predictions against actual recordings.

    Computes various metrics comparing predicted and actual ground motions,
    including peak values, spectral content, and time series similarity.

    Parameters
    ----------
    damping_ratio : float
        Damping ratio for response spectrum computation. Default is 0.05.
    periods : NDArray, optional
        Periods for response spectrum comparison. If None, uses default range.

    Examples
    --------
    >>> from seismic_twin.prediction import PredictionValidator, WaveformPredictor
    >>> predictor = WaveformPredictor()
    >>> pairs = predictor.predict_cross_validation(event_info, records)
    >>> validator = PredictionValidator()
    >>> summary = validator.validate_cross_validation(pairs)
    >>> print(f"Mean correlation: {summary.mean_correlation:.2f}")
    """

    # Score weights for overall quality assessment
    WEIGHT_PGA = 0.30
    WEIGHT_SPECTRUM = 0.40
    WEIGHT_CORRELATION = 0.30

    def __init__(
        self,
        damping_ratio: float = 0.05,
        periods: NDArray[np.floating] | None = None,
    ) -> None:
        """Initialize the validator."""
        self.damping_ratio = damping_ratio
        self.periods = periods or np.logspace(-2, 1, 50)  # 0.01s to 10s

    def validate_prediction(
        self,
        time: NDArray[np.floating],
        predicted: NDArray[np.floating],
        actual: NDArray[np.floating],
        station_id: str = "unknown",
        distance_km: float = 0.0,
    ) -> ValidationResult:
        """
        Validate a single prediction against actual recording.

        Parameters
        ----------
        time : NDArray
            Time vector in seconds.
        predicted : NDArray
            Predicted acceleration time history in g.
        actual : NDArray
            Actual acceleration time history in g.
        station_id : str
            Station identifier.
        distance_km : float
            Station distance from epicenter.

        Returns
        -------
        ValidationResult
            Comprehensive validation metrics.
        """
        dt = time[1] - time[0]

        # Compute peak metrics
        peak_metrics = self._compute_peak_metrics(predicted, actual)

        # Compute spectrum metrics
        spectrum_metrics = self._compute_spectrum_metrics(time, predicted, actual)

        # Compute time series metrics
        timeseries_metrics = self._compute_timeseries_metrics(predicted, actual, dt)

        # Compute overall score
        overall_score = self._compute_overall_score(
            peak_metrics, spectrum_metrics, timeseries_metrics
        )

        # Assign quality grade
        quality_grade = self._assign_grade(overall_score)

        return ValidationResult(
            station_id=station_id,
            distance_km=distance_km,
            peak_metrics=peak_metrics,
            spectrum_metrics=spectrum_metrics,
            timeseries_metrics=timeseries_metrics,
            overall_score=overall_score,
            quality_grade=quality_grade,
        )

    def validate_pair(self, pair: PredictionPair) -> ValidationResult:
        """
        Validate a PredictionPair.

        Parameters
        ----------
        pair : PredictionPair
            Prediction-actual pair from cross-validation.

        Returns
        -------
        ValidationResult
            Comprehensive validation metrics.
        """
        return self.validate_prediction(
            time=pair.time,
            predicted=pair.predicted,
            actual=pair.actual,
            station_id=pair.station_id,
            distance_km=pair.distance_km,
        )

    def validate_cross_validation(
        self,
        pairs: list[PredictionPair],
    ) -> ValidationSummary:
        """
        Validate all cross-validation prediction pairs.

        Parameters
        ----------
        pairs : list[PredictionPair]
            List of prediction-actual pairs.

        Returns
        -------
        ValidationSummary
            Summary statistics across all stations.
        """
        results = []
        pga_ratios = []
        correlations = []
        scores = []

        for pair in pairs:
            result = self.validate_pair(pair)
            results.append(result)
            pga_ratios.append(result.peak_metrics.pga_ratio)
            correlations.append(result.timeseries_metrics.correlation)
            scores.append(result.overall_score)

        return ValidationSummary(
            n_stations=len(pairs),
            mean_pga_ratio=float(np.mean(pga_ratios)),
            std_pga_ratio=float(np.std(pga_ratios)),
            mean_correlation=float(np.mean(correlations)),
            mean_overall_score=float(np.mean(scores)),
            individual_results=results,
        )

    def _compute_peak_metrics(
        self,
        predicted: NDArray[np.floating],
        actual: NDArray[np.floating],
    ) -> PeakMetrics:
        """Compute peak ground motion metrics."""
        actual_pga = float(np.max(np.abs(actual)))
        predicted_pga = float(np.max(np.abs(predicted)))

        if actual_pga > 0:
            pga_ratio = predicted_pga / actual_pga
            pga_error = abs(predicted_pga - actual_pga) / actual_pga * 100
        else:
            pga_ratio = 1.0 if predicted_pga == 0 else float("inf")
            pga_error = 0.0 if predicted_pga == 0 else 100.0

        return PeakMetrics(
            actual_pga=actual_pga,
            predicted_pga=predicted_pga,
            pga_ratio=pga_ratio,
            pga_error_percent=pga_error,
        )

    def _compute_spectrum_metrics(
        self,
        time: NDArray[np.floating],
        predicted: NDArray[np.floating],
        actual: NDArray[np.floating],
    ) -> SpectrumMetrics:
        """Compute response spectrum comparison metrics."""
        # Compute response spectra
        _, predicted_sa = compute_response_spectrum(
            time, predicted, self.periods, self.damping_ratio
        )
        _, actual_sa = compute_response_spectrum(time, actual, self.periods, self.damping_ratio)

        # Compute Sa ratios
        valid_mask = actual_sa > 1e-10
        if np.any(valid_mask):
            sa_ratios = np.where(valid_mask, predicted_sa / actual_sa, 1.0)
            mean_sa_ratio = float(np.mean(sa_ratios[valid_mask]))
        else:
            sa_ratios = np.ones_like(predicted_sa)
            mean_sa_ratio = 1.0

        # Compute goodness of fit by period range
        short_mask = self.periods < 0.5
        mid_mask = (self.periods >= 0.5) & (self.periods < 2.0)
        long_mask = self.periods >= 2.0

        gof_short = self._compute_spectral_gof(predicted_sa, actual_sa, short_mask)
        gof_mid = self._compute_spectral_gof(predicted_sa, actual_sa, mid_mask)
        gof_long = self._compute_spectral_gof(predicted_sa, actual_sa, long_mask)

        return SpectrumMetrics(
            periods=self.periods,
            actual_sa=actual_sa,
            predicted_sa=predicted_sa,
            mean_sa_ratio=mean_sa_ratio,
            gof_short_period=gof_short,
            gof_mid_period=gof_mid,
            gof_long_period=gof_long,
        )

    def _compute_spectral_gof(
        self,
        predicted_sa: NDArray[np.floating],
        actual_sa: NDArray[np.floating],
        mask: NDArray[np.bool_],
    ) -> float:
        """
        Compute spectral goodness of fit for a period range.

        Uses the Anderson (2004) goodness of fit metric.
        """
        if not np.any(mask):
            return 0.0

        pred = predicted_sa[mask]
        act = actual_sa[mask]

        # Avoid log of zero
        pred = np.maximum(pred, 1e-10)
        act = np.maximum(act, 1e-10)

        # Log residual
        residual = np.log(pred) - np.log(act)

        # GOF score (1 = perfect, 0 = poor)
        # Based on Anderson (2004) criteria
        std_residual = np.std(residual)
        mean_residual = np.abs(np.mean(residual))

        # Convert to 0-1 score
        gof = np.exp(-std_residual) * np.exp(-mean_residual)

        return float(gof)

    def _compute_timeseries_metrics(
        self,
        predicted: NDArray[np.floating],
        actual: NDArray[np.floating],
        dt: float,
    ) -> TimeSeriesMetrics:
        """Compute time series comparison metrics."""
        # NRMSE
        nrmse = compute_nrmse(predicted, actual)

        # Correlation
        correlation = compute_correlation(predicted, actual)

        # Arias intensity ratio
        arias_pred = compute_arias_intensity(predicted, dt)
        arias_act = compute_arias_intensity(actual, dt)
        if arias_act > 0:
            arias_ratio = arias_pred / arias_act
        else:
            arias_ratio = 1.0 if arias_pred == 0 else float("inf")

        # Phase goodness (based on correlation and envelope similarity)
        # Higher correlation indicates better phase alignment
        phase_goodness = max(0.0, correlation)

        return TimeSeriesMetrics(
            nrmse=nrmse,
            correlation=correlation,
            arias_ratio=arias_ratio,
            phase_goodness=phase_goodness,
        )

    def _compute_overall_score(
        self,
        peak: PeakMetrics,
        spectrum: SpectrumMetrics,
        timeseries: TimeSeriesMetrics,
    ) -> float:
        """
        Compute overall prediction quality score.

        Score components:
        - PGA accuracy (30%): Based on log ratio being close to 1
        - Spectral match (40%): Mean of period-range GOF scores
        - Correlation (30%): Waveform correlation coefficient

        Returns
        -------
        float
            Overall score from 0 to 1.
        """
        # PGA score: penalize deviation from ratio = 1
        log_ratio = np.log(max(0.1, min(10, peak.pga_ratio)))
        pga_score = np.exp(-abs(log_ratio))

        # Spectrum score: average of period-range GOF
        spectrum_score = (
            spectrum.gof_short_period + spectrum.gof_mid_period + spectrum.gof_long_period
        ) / 3.0

        # Correlation score: map [-1, 1] to [0, 1]
        correlation_score = (timeseries.correlation + 1) / 2.0

        # Weighted sum
        overall = (
            self.WEIGHT_PGA * pga_score
            + self.WEIGHT_SPECTRUM * spectrum_score
            + self.WEIGHT_CORRELATION * correlation_score
        )

        return float(np.clip(overall, 0, 1))

    def _assign_grade(self, score: float) -> str:
        """Assign quality grade based on overall score."""
        if score >= 0.8:
            return "A"
        elif score >= 0.6:
            return "B"
        elif score >= 0.4:
            return "C"
        elif score >= 0.2:
            return "D"
        else:
            return "F"
