"""
Tests for Ground Motion Prediction Equations (GMPE) module.
"""

import numpy as np
import pytest

from seismic_twin.prediction.distance import (
    compute_epicentral_distance,
    compute_hypocentral_distance,
    compute_rjb_distance,
)
from seismic_twin.prediction.gmpe import BooreAtkinson2008, GMPEInput, GMPEOutput


class TestGMPEInput:
    """Tests for GMPEInput dataclass."""

    def test_valid_input(self):
        """Test creation with valid parameters."""
        params = GMPEInput(
            magnitude=7.0,
            distance_rjb=50.0,
            vs30=760.0,
            period=1.0,
        )
        assert params.magnitude == 7.0
        assert params.distance_rjb == 50.0
        assert params.vs30 == 760.0
        assert params.period == 1.0

    def test_default_values(self):
        """Test default values for optional parameters."""
        params = GMPEInput(magnitude=6.5, distance_rjb=30.0)
        assert params.vs30 == 760.0
        assert params.period == 0.0

    def test_invalid_magnitude(self):
        """Test validation of magnitude range."""
        with pytest.raises(ValueError, match="Magnitude must be between"):
            GMPEInput(magnitude=15.0, distance_rjb=50.0)

        with pytest.raises(ValueError, match="Magnitude must be between"):
            GMPEInput(magnitude=-1.0, distance_rjb=50.0)

    def test_invalid_distance(self):
        """Test validation of distance."""
        with pytest.raises(ValueError, match="Distance must be non-negative"):
            GMPEInput(magnitude=6.5, distance_rjb=-10.0)

    def test_invalid_vs30(self):
        """Test validation of Vs30."""
        with pytest.raises(ValueError, match="Vs30 must be positive"):
            GMPEInput(magnitude=6.5, distance_rjb=50.0, vs30=0.0)

    def test_invalid_period(self):
        """Test validation of period."""
        with pytest.raises(ValueError, match="Period must be non-negative"):
            GMPEInput(magnitude=6.5, distance_rjb=50.0, period=-0.1)


class TestGMPEOutput:
    """Tests for GMPEOutput dataclass."""

    def test_output_creation(self):
        """Test creation of output."""
        output = GMPEOutput(
            median_sa=0.5,
            sigma_total=0.6,
            sigma_inter=0.3,
            sigma_intra=0.52,
        )
        assert output.median_sa == 0.5
        assert output.sigma_total == 0.6

    def test_plus_minus_sigma(self):
        """Test plus and minus sigma properties."""
        output = GMPEOutput(median_sa=0.5, sigma_total=0.6)

        # Plus sigma should be larger than median
        assert output.plus_sigma > output.median_sa
        assert output.plus_sigma == pytest.approx(0.5 * np.exp(0.6), rel=1e-5)

        # Minus sigma should be smaller than median
        assert output.minus_sigma < output.median_sa
        assert output.minus_sigma == pytest.approx(0.5 * np.exp(-0.6), rel=1e-5)


class TestBooreAtkinson2008:
    """Tests for Boore-Atkinson 2008 GMPE."""

    @pytest.fixture
    def gmpe(self):
        """Create GMPE instance."""
        return BooreAtkinson2008()

    def test_name(self, gmpe):
        """Test model name."""
        assert gmpe.name == "Boore-Atkinson 2008"

    def test_valid_periods(self, gmpe):
        """Test that valid periods are defined."""
        periods = gmpe.valid_periods
        assert len(periods) > 0
        assert 0.0 in periods  # PGA
        assert 1.0 in periods  # 1 second

    def test_pga_decreases_with_distance(self, gmpe):
        """Test that PGA decreases with increasing distance."""
        distances = [10, 20, 50, 100, 200]
        pga_values = []

        for dist in distances:
            pga = gmpe.predict_pga(magnitude=7.0, distance_rjb=dist)
            pga_values.append(pga)

        # PGA should decrease monotonically with distance
        for i in range(len(pga_values) - 1):
            assert pga_values[i] > pga_values[i + 1], (
                f"PGA at {distances[i]}km ({pga_values[i]:.4f}) should be > "
                f"PGA at {distances[i + 1]}km ({pga_values[i + 1]:.4f})"
            )

    def test_pga_increases_with_magnitude(self, gmpe):
        """Test that PGA increases with increasing magnitude."""
        magnitudes = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5]
        pga_values = []

        for mag in magnitudes:
            pga = gmpe.predict_pga(magnitude=mag, distance_rjb=50.0)
            pga_values.append(pga)

        # PGA should increase monotonically with magnitude
        for i in range(len(pga_values) - 1):
            assert pga_values[i] < pga_values[i + 1], (
                f"PGA at M{magnitudes[i]} ({pga_values[i]:.4f}) should be < "
                f"PGA at M{magnitudes[i + 1]} ({pga_values[i + 1]:.4f})"
            )

    def test_spectrum_shape(self, gmpe):
        """Test that spectrum has expected shape."""
        periods, sa = gmpe.predict_spectrum(
            magnitude=7.0,
            distance_rjb=50.0,
            periods=np.array([0.1, 0.5, 1.0, 2.0, 5.0]),
        )

        # All values should be positive
        assert np.all(sa > 0)

        # Short periods generally have higher Sa than long periods
        # (for typical earthquake spectra)
        assert sa[0] > sa[-1], "Short period Sa should be > long period Sa"

    def test_pga_reasonable_values(self, gmpe):
        """Test that PGA values are in reasonable range."""
        # M7 at 50 km should give roughly 0.1-0.3g
        pga = gmpe.predict_pga(magnitude=7.0, distance_rjb=50.0)
        assert 0.05 < pga < 0.5, f"PGA={pga}g is outside reasonable range"

        # M6 at 100 km should be quite small
        pga_far = gmpe.predict_pga(magnitude=6.0, distance_rjb=100.0)
        assert pga_far < 0.1, f"PGA={pga_far}g is unexpectedly high at 100km"

        # M7.5 at 10 km should be quite large (relaxed threshold for GMPE variability)
        pga_close = gmpe.predict_pga(magnitude=7.5, distance_rjb=10.0)
        assert pga_close > 0.2, f"PGA={pga_close}g is unexpectedly low at 10km"

    def test_sigma_values(self, gmpe):
        """Test that sigma values are reasonable."""
        params = GMPEInput(magnitude=7.0, distance_rjb=50.0)
        output = gmpe.predict(params)

        # Sigma should be positive
        assert output.sigma_total > 0
        assert output.sigma_inter >= 0
        assert output.sigma_intra >= 0

        # Typical sigma is around 0.5-0.7 in log units
        assert 0.4 < output.sigma_total < 0.9

    def test_scale_factor(self, gmpe):
        """Test amplitude scale factor computation."""
        # Same distance should give scale factor of 1
        scale = gmpe.compute_scale_factor(
            magnitude=7.0,
            source_distance=50.0,
            target_distance=50.0,
        )
        assert scale == pytest.approx(1.0, rel=1e-5)

        # Closer target should have scale > 1
        scale_closer = gmpe.compute_scale_factor(
            magnitude=7.0,
            source_distance=50.0,
            target_distance=30.0,
        )
        assert scale_closer > 1.0

        # Farther target should have scale < 1
        scale_farther = gmpe.compute_scale_factor(
            magnitude=7.0,
            source_distance=50.0,
            target_distance=80.0,
        )
        assert scale_farther < 1.0

    def test_vs30_site_effect(self, gmpe):
        """Test that Vs30 affects predictions."""
        pga_rock = gmpe.predict_pga(magnitude=7.0, distance_rjb=50.0, vs30=760.0)
        pga_soft = gmpe.predict_pga(magnitude=7.0, distance_rjb=50.0, vs30=250.0)

        # Soft soil should amplify motion
        assert pga_soft > pga_rock

    def test_period_interpolation(self, gmpe):
        """Test that intermediate periods are interpolated."""
        # Get values at known periods
        params_05 = GMPEInput(magnitude=7.0, distance_rjb=50.0, period=0.5)
        params_10 = GMPEInput(magnitude=7.0, distance_rjb=50.0, period=1.0)
        params_075 = GMPEInput(magnitude=7.0, distance_rjb=50.0, period=0.75)

        sa_05 = gmpe.predict(params_05).median_sa
        sa_10 = gmpe.predict(params_10).median_sa
        sa_075 = gmpe.predict(params_075).median_sa

        # Interpolated value should be between endpoints
        # (not strictly true due to log interpolation, but approximately)
        assert min(sa_05, sa_10) <= sa_075 * 1.1  # Allow 10% tolerance
        assert sa_075 <= max(sa_05, sa_10) * 1.1


class TestDistanceFunctions:
    """Tests for distance calculation functions."""

    def test_epicentral_distance_same_point(self):
        """Test distance to same point is zero."""
        dist = compute_epicentral_distance(35.0, -117.0, 35.0, -117.0)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_epicentral_distance_known_value(self):
        """Test distance calculation with known value."""
        # LA to San Francisco is approximately 559 km
        dist = compute_epicentral_distance(
            34.0522,
            -118.2437,  # LA
            37.7749,
            -122.4194,  # SF
        )
        assert dist == pytest.approx(559, rel=0.02)  # 2% tolerance

    def test_epicentral_distance_symmetric(self):
        """Test that distance is symmetric."""
        dist_ab = compute_epicentral_distance(35.0, -117.0, 36.0, -118.0)
        dist_ba = compute_epicentral_distance(36.0, -118.0, 35.0, -117.0)
        assert dist_ab == pytest.approx(dist_ba, rel=1e-6)

    def test_hypocentral_distance(self):
        """Test hypocentral distance calculation."""
        # With zero depth, should equal epicentral
        dist_epi = compute_epicentral_distance(35.0, -117.0, 36.0, -118.0)
        dist_hypo = compute_hypocentral_distance(35.0, -117.0, 36.0, -118.0, 0.0)
        assert dist_epi == pytest.approx(dist_hypo, rel=1e-6)

        # With depth, should be larger
        dist_hypo_deep = compute_hypocentral_distance(35.0, -117.0, 36.0, -118.0, 20.0)
        assert dist_hypo_deep > dist_epi

        # Check Pythagorean relationship
        expected = np.sqrt(dist_epi**2 + 20.0**2)
        assert dist_hypo_deep == pytest.approx(expected, rel=1e-6)

    def test_rjb_distance_small_event(self):
        """Test Rjb for small event equals epicentral distance."""
        dist_epi = compute_epicentral_distance(35.0, -117.0, 36.0, -118.0)
        dist_rjb = compute_rjb_distance(
            station_lat=35.0,
            station_lon=-117.0,
            epicenter_lat=36.0,
            epicenter_lon=-118.0,
            magnitude=5.0,  # Small event
        )
        assert dist_epi == pytest.approx(dist_rjb, rel=1e-6)

    def test_rjb_distance_positive(self):
        """Test that Rjb is always positive."""
        dist = compute_rjb_distance(35.0, -117.0, 35.0, -117.0, 7.0)
        assert dist >= 0
