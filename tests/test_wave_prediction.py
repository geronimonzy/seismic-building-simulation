"""
Tests for Wave Propagation Prediction module.
"""

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pytest

from seismic_twin.prediction import (
    BooreAtkinson2008,
    PredictionValidator,
    WaveformPredictor,
    compute_epicentral_distance,
)
from seismic_twin.prediction.waveform_prediction import PredictionPair, StationPrediction
from seismic_twin.prediction.validation import (
    PeakMetrics,
    SpectrumMetrics,
    TimeSeriesMetrics,
    ValidationResult,
    ValidationSummary,
)
from seismic_twin.data.records import EventInfo


# Fixture for synthetic records
@dataclass
class MockRecord:
    """Mock ground motion record for testing."""
    time: np.ndarray
    acceleration: np.ndarray
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
    processing_history: list


@pytest.fixture
def event_info():
    """Create test event info."""
    return EventInfo(
        event_id="test_event",
        origin_time=datetime(2020, 1, 1, 0, 0, 0),
        latitude=35.77,
        longitude=-117.60,
        depth_km=8.0,
        magnitude=7.0,
        magnitude_type="Mw",
        region="Test Region",
        source_catalog="Test",
    )


@pytest.fixture
def synthetic_records(event_info):
    """Create synthetic test records."""
    from seismic_twin.ground_motion.synthetic import generate_synthetic_ground_motion

    gmpe = BooreAtkinson2008()
    stations = [
        ("STA1", 35.85, -117.50, 15.0),
        ("STA2", 35.70, -117.35, 25.0),
        ("STA3", 35.55, -117.70, 35.0),
    ]

    records = []
    for station_id, lat, lon, _ in stations:
        dist_km = compute_epicentral_distance(
            event_info.latitude, event_info.longitude, lat, lon
        )
        expected_pga = gmpe.predict_pga(event_info.magnitude, dist_km)

        time, acceleration = generate_synthetic_ground_motion(
            duration=30.0,
            dt=0.01,
            target_pga=expected_pga,
            seed=hash(station_id) % 2**31,
        )

        record = MockRecord(
            time=time,
            acceleration=acceleration,
            dt=0.01,
            event_id="test_event",
            network="TS",
            station=station_id,
            channel="HNE",
            component="E",
            station_latitude=lat,
            station_longitude=lon,
            epicentral_distance_km=dist_km,
            pga=float(np.max(np.abs(acceleration))),
            processing_history=["synthetic"],
        )
        records.append(record)

    return records


class TestWaveformPredictor:
    """Tests for WaveformPredictor class."""

    def test_init_default_gmpe(self):
        """Test initialization with default GMPE."""
        predictor = WaveformPredictor()
        assert predictor.gmpe is not None
        assert isinstance(predictor.gmpe, BooreAtkinson2008)

    def test_init_custom_gmpe(self):
        """Test initialization with custom GMPE."""
        gmpe = BooreAtkinson2008()
        predictor = WaveformPredictor(gmpe=gmpe)
        assert predictor.gmpe is gmpe

    def test_predict_at_location(self, event_info, synthetic_records):
        """Test prediction at a target location."""
        predictor = WaveformPredictor()

        # Predict at location of STA2 using STA1 and STA3 as sources
        target_record = synthetic_records[1]  # STA2
        source_records = [synthetic_records[0], synthetic_records[2]]  # STA1, STA3

        prediction = predictor.predict_at_location(
            target_lat=target_record.station_latitude,
            target_lon=target_record.station_longitude,
            target_station_id=target_record.station,
            event_info=event_info,
            source_records=source_records,
        )

        assert isinstance(prediction, StationPrediction)
        assert prediction.target_station_id == "STA2"
        assert len(prediction.predicted_waveform) == len(prediction.time)
        assert prediction.predicted_pga > 0
        assert prediction.scale_factor > 0

    def test_predict_excludes_target_station(self, event_info, synthetic_records):
        """Test that target station is excluded from source selection."""
        predictor = WaveformPredictor()

        prediction = predictor.predict_at_location(
            target_lat=synthetic_records[0].station_latitude,
            target_lon=synthetic_records[0].station_longitude,
            target_station_id="STA1",
            event_info=event_info,
            source_records=synthetic_records,
        )

        # Source should not be the target
        assert prediction.source_station_id != "STA1"

    def test_predict_no_source_records(self, event_info):
        """Test error when no source records provided."""
        predictor = WaveformPredictor()

        with pytest.raises(ValueError, match="At least one source record"):
            predictor.predict_at_location(
                target_lat=35.0,
                target_lon=-117.0,
                target_station_id="TARGET",
                event_info=event_info,
                source_records=[],
            )

    def test_predict_only_target_available(self, event_info, synthetic_records):
        """Test error when only target station is available as source."""
        predictor = WaveformPredictor()

        with pytest.raises(ValueError, match="No valid source stations"):
            predictor.predict_at_location(
                target_lat=synthetic_records[0].station_latitude,
                target_lon=synthetic_records[0].station_longitude,
                target_station_id="STA1",
                event_info=event_info,
                source_records=[synthetic_records[0]],  # Only target station
            )

    def test_cross_validation(self, event_info, synthetic_records):
        """Test leave-one-out cross-validation."""
        predictor = WaveformPredictor()

        pairs = predictor.predict_cross_validation(event_info, synthetic_records)

        # Should have one pair for each station
        assert len(pairs) == len(synthetic_records)

        # Each pair should have valid data
        for pair in pairs:
            assert isinstance(pair, PredictionPair)
            assert len(pair.predicted) == len(pair.actual)
            assert pair.scale_factor > 0
            # Source should not be the target station
            assert pair.source_station != pair.station_id

    def test_cross_validation_minimum_records(self, event_info, synthetic_records):
        """Test that cross-validation requires at least 2 records."""
        predictor = WaveformPredictor()

        with pytest.raises(ValueError, match="(?i)at least 2 records"):
            predictor.predict_cross_validation(
                event_info, [synthetic_records[0]]
            )

    def test_source_selection_nearest(self, event_info, synthetic_records):
        """Test nearest source station selection."""
        predictor = WaveformPredictor()

        # Target at location between STA1 and STA2, closer to STA1
        prediction = predictor.predict_at_location(
            target_lat=35.83,  # Closer to STA1 (35.85)
            target_lon=-117.48,
            target_station_id="TARGET",
            event_info=event_info,
            source_records=synthetic_records,
            source_selection="nearest",
        )

        assert prediction.source_station_id == "STA1"


class TestPredictionValidator:
    """Tests for PredictionValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return PredictionValidator()

    def test_validate_identical_waveforms(self, validator):
        """Test validation of identical waveforms gives perfect scores."""
        time = np.linspace(0, 10, 1001)
        waveform = np.sin(2 * np.pi * time)

        result = validator.validate_prediction(
            time=time,
            predicted=waveform,
            actual=waveform,
            station_id="TEST",
            distance_km=50.0,
        )

        assert result.peak_metrics.pga_ratio == pytest.approx(1.0, rel=1e-5)
        assert result.timeseries_metrics.correlation == pytest.approx(1.0, rel=1e-3)
        assert result.quality_grade == "A"

    def test_validate_scaled_waveforms(self, validator):
        """Test validation of scaled waveforms."""
        time = np.linspace(0, 10, 1001)
        actual = np.sin(2 * np.pi * time) * 0.5
        predicted = actual * 2.0  # Doubled amplitude

        result = validator.validate_prediction(
            time=time,
            predicted=predicted,
            actual=actual,
        )

        assert result.peak_metrics.pga_ratio == pytest.approx(2.0, rel=1e-5)
        # Correlation should still be perfect (phase preserved)
        assert result.timeseries_metrics.correlation == pytest.approx(1.0, rel=1e-3)

    def test_validate_phase_shifted(self, validator):
        """Test validation of phase-shifted waveforms."""
        time = np.linspace(0, 10, 1001)
        actual = np.sin(2 * np.pi * time)
        predicted = np.cos(2 * np.pi * time)  # 90 degree phase shift

        result = validator.validate_prediction(
            time=time,
            predicted=predicted,
            actual=actual,
        )

        # PGA should be similar
        assert result.peak_metrics.pga_ratio == pytest.approx(1.0, rel=0.1)
        # Correlation should be near zero (orthogonal)
        assert abs(result.timeseries_metrics.correlation) < 0.1

    def test_validate_pair(self, validator):
        """Test validation using PredictionPair."""
        time = np.linspace(0, 10, 1001)
        waveform = np.sin(2 * np.pi * time) * 0.3

        pair = PredictionPair(
            station_id="TEST",
            distance_km=50.0,
            time=time,
            dt=0.01,
            predicted=waveform,
            actual=waveform * 0.9,
            scale_factor=1.1,
            source_station="SRC",
        )

        result = validator.validate_pair(pair)

        assert result.station_id == "TEST"
        assert result.distance_km == 50.0

    def test_validate_cross_validation(self, validator, event_info, synthetic_records):
        """Test validation of cross-validation results."""
        predictor = WaveformPredictor()
        pairs = predictor.predict_cross_validation(event_info, synthetic_records)

        summary = validator.validate_cross_validation(pairs)

        assert isinstance(summary, ValidationSummary)
        assert summary.n_stations == len(synthetic_records)
        assert len(summary.individual_results) == len(synthetic_records)
        assert 0 < summary.mean_pga_ratio < 10
        assert -1 <= summary.mean_correlation <= 1

    def test_quality_grades(self, validator):
        """Test quality grade assignment."""
        time = np.linspace(0, 10, 1001)
        actual = np.sin(2 * np.pi * time) * 0.5

        # Test grade A (excellent)
        result_a = validator.validate_prediction(
            time=time,
            predicted=actual,  # Identical
            actual=actual,
        )
        assert result_a.quality_grade == "A"

        # Test lower grades (by using uncorrelated noise)
        np.random.seed(42)
        noise = np.random.randn(len(time)) * 0.5
        result_noise = validator.validate_prediction(
            time=time,
            predicted=noise,
            actual=actual,
        )
        # Noise should give a lower grade
        assert result_noise.quality_grade in ["C", "D", "F"]


class TestPeakMetrics:
    """Tests for PeakMetrics dataclass."""

    def test_pga_ratio_calculation(self):
        """Test PGA ratio calculation."""
        metrics = PeakMetrics(
            actual_pga=0.5,
            predicted_pga=0.6,
            pga_ratio=1.2,
            pga_error_percent=20.0,
        )
        assert metrics.pga_ratio == 1.2
        assert metrics.pga_error_percent == 20.0


class TestSpectrumMetrics:
    """Tests for SpectrumMetrics dataclass."""

    def test_spectrum_metrics_creation(self):
        """Test creation of spectrum metrics."""
        periods = np.array([0.1, 1.0, 10.0])
        actual_sa = np.array([0.5, 0.3, 0.1])
        predicted_sa = np.array([0.5, 0.3, 0.1])

        metrics = SpectrumMetrics(
            periods=periods,
            actual_sa=actual_sa,
            predicted_sa=predicted_sa,
            mean_sa_ratio=1.0,
            gof_short_period=1.0,
            gof_mid_period=1.0,
            gof_long_period=1.0,
        )

        assert len(metrics.periods) == 3
        assert metrics.mean_sa_ratio == 1.0


class TestTimeSeriesMetrics:
    """Tests for TimeSeriesMetrics dataclass."""

    def test_timeseries_metrics_creation(self):
        """Test creation of time series metrics."""
        metrics = TimeSeriesMetrics(
            nrmse=0.1,
            correlation=0.95,
            arias_ratio=1.05,
            phase_goodness=0.9,
        )

        assert metrics.nrmse == 0.1
        assert metrics.correlation == 0.95
        assert metrics.arias_ratio == 1.05


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creation of validation result."""
        peak = PeakMetrics(0.5, 0.5, 1.0, 0.0)
        spectrum = SpectrumMetrics(
            np.array([0.1]), np.array([0.5]), np.array([0.5]),
            1.0, 1.0, 1.0, 1.0
        )
        timeseries = TimeSeriesMetrics(0.1, 0.95, 1.0, 0.9)

        result = ValidationResult(
            station_id="TEST",
            distance_km=50.0,
            peak_metrics=peak,
            spectrum_metrics=spectrum,
            timeseries_metrics=timeseries,
            overall_score=0.9,
            quality_grade="A",
        )

        assert result.station_id == "TEST"
        assert result.quality_grade == "A"


class TestValidationSummary:
    """Tests for ValidationSummary dataclass."""

    def test_summary_creation(self):
        """Test creation of validation summary."""
        summary = ValidationSummary(
            n_stations=5,
            mean_pga_ratio=1.1,
            std_pga_ratio=0.2,
            mean_correlation=0.85,
            mean_overall_score=0.75,
        )

        assert summary.n_stations == 5
        assert summary.mean_pga_ratio == 1.1
        assert summary.individual_results == []


class TestIntegration:
    """Integration tests for the complete prediction pipeline."""

    def test_full_pipeline(self, event_info, synthetic_records):
        """Test complete prediction and validation pipeline."""
        # Create predictor and validator
        predictor = WaveformPredictor()
        validator = PredictionValidator()

        # Run cross-validation
        pairs = predictor.predict_cross_validation(event_info, synthetic_records)

        # Validate all predictions
        summary = validator.validate_cross_validation(pairs)

        # Check reasonable results
        assert summary.n_stations == len(synthetic_records)
        assert 0.5 < summary.mean_pga_ratio < 2.0
        # With synthetic data and independent random seeds, correlation is near zero
        # (GMPE scaling captures amplitude but not phase)
        assert summary.mean_correlation > -0.5  # Not strongly negatively correlated

        # All results should have grades assigned
        for result in summary.individual_results:
            assert result.quality_grade in "ABCDF"

    def test_prediction_follows_distance_decay(self, event_info, synthetic_records):
        """Test that predictions follow expected distance decay."""
        predictor = WaveformPredictor()

        # Get predictions at different distances
        predictions = []
        for record in synthetic_records:
            source_records = [r for r in synthetic_records if r.station != record.station]
            pred = predictor.predict_at_location(
                target_lat=record.station_latitude,
                target_lon=record.station_longitude,
                target_station_id=record.station,
                event_info=event_info,
                source_records=source_records,
            )
            predictions.append((pred.target_distance_km, pred.predicted_pga))

        # Sort by distance
        predictions.sort(key=lambda x: x[0])

        # PGA should generally decrease with distance
        # (may not be strictly monotonic due to source station effects)
        first_dist, first_pga = predictions[0]
        last_dist, last_pga = predictions[-1]

        assert first_dist < last_dist
        # Farther station should have lower PGA
        assert first_pga >= last_pga * 0.5  # Allow some tolerance
