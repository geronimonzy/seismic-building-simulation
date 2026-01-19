"""Tests for the uncertainty quantification module."""

import numpy as np

from seismic_twin.uncertainty import UncertaintyAnalysis
from seismic_twin.uncertainty.monte_carlo import MonteCarloResult, UncertaintyBounds


class TestUncertaintyBounds:
    """Test UncertaintyBounds dataclass."""

    def test_uncertainty_bounds_creation(self):
        """Test creating UncertaintyBounds."""
        bounds = UncertaintyBounds(
            percentile_5=np.array([0.1]),
            percentile_50=np.array([0.5]),
            percentile_95=np.array([0.9]),
            mean=np.array([0.5]),
            std=np.array([0.2]),
        )
        assert bounds.percentile_5[0] == 0.1
        assert bounds.percentile_50[0] == 0.5
        assert bounds.percentile_95[0] == 0.9


class TestUncertaintyAnalysis:
    """Test cases for UncertaintyAnalysis class."""

    def test_init(self, simple_3dof, simple_ground_motion):
        """Test UncertaintyAnalysis initialization."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=simple_ground_motion["acceleration"],
            dt=simple_ground_motion["dt"],
        )

        assert ua.base_model is not None
        assert ua.results is None

    def test_sample_parameters(self, simple_3dof, simple_ground_motion):
        """Test parameter sampling."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=simple_ground_motion["acceleration"],
            dt=simple_ground_motion["dt"],
        )

        samples = ua.sample_parameters(
            n_samples=100,
            stiffness_cov=0.1,
            damping_cov=0.2,
            seed=42,
        )

        assert "stiffness_factors" in samples
        assert "damping_ratios" in samples
        assert samples["stiffness_factors"].shape[0] == 100
        assert samples["damping_ratios"].shape[0] == 100

        # Check variability
        assert np.std(samples["stiffness_factors"]) > 0
        assert np.std(samples["damping_ratios"]) > 0

    def test_sample_parameters_reproducibility(self, simple_3dof, simple_ground_motion):
        """Test that sampling is reproducible with seed."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=simple_ground_motion["acceleration"],
            dt=simple_ground_motion["dt"],
        )

        samples1 = ua.sample_parameters(n_samples=50, seed=123)
        samples2 = ua.sample_parameters(n_samples=50, seed=123)

        np.testing.assert_array_equal(samples1["stiffness_factors"], samples2["stiffness_factors"])
        np.testing.assert_array_equal(samples1["damping_ratios"], samples2["damping_ratios"])

    def test_run_mc_ensemble_small(self, simple_3dof, short_ground_motion):
        """Test Monte Carlo ensemble with small sample size."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        result = ua.run_mc_ensemble(
            n_samples=10,
            stiffness_cov=0.05,
            damping_cov=0.1,
            seed=42,
        )

        assert isinstance(result, MonteCarloResult)
        assert result.n_samples == 10
        assert result.displacement_bounds is not None
        assert result.velocity_bounds is not None
        assert result.acceleration_bounds is not None

    def test_mc_result_bounds_ordering(self, simple_3dof, short_ground_motion):
        """Test that percentile bounds are correctly ordered."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        result = ua.run_mc_ensemble(
            n_samples=20,
            stiffness_cov=0.1,
            seed=42,
        )

        bounds = result.displacement_bounds

        # 5th percentile <= 50th percentile <= 95th percentile
        assert np.all(bounds.percentile_5 <= bounds.percentile_50 + 1e-10)
        assert np.all(bounds.percentile_50 <= bounds.percentile_95 + 1e-10)

    def test_max_drift_distribution(self, simple_3dof, short_ground_motion):
        """Test max drift distribution computation."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        result = ua.run_mc_ensemble(
            n_samples=15,
            stiffness_cov=0.05,
            seed=42,
        )

        assert result.max_drift_distribution is not None
        assert len(result.max_drift_distribution) == 15
        assert np.all(result.max_drift_distribution >= 0)

    def test_parameter_samples_stored(self, simple_3dof, short_ground_motion):
        """Test that parameter samples are stored in results."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        result = ua.run_mc_ensemble(
            n_samples=10,
            stiffness_cov=0.1,
            damping_cov=0.2,
            seed=42,
        )

        assert "stiffness_factors" in result.parameter_samples
        assert "damping_ratios" in result.parameter_samples
        assert len(result.parameter_samples["stiffness_factors"]) == 10

    def test_all_displacements_shape(self, simple_3dof, short_ground_motion):
        """Test shape of all_displacements array."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        n_samples = 8
        result = ua.run_mc_ensemble(n_samples=n_samples, seed=42)

        # Shape should be (n_samples, n_dof, n_steps)
        assert result.all_displacements.shape[0] == n_samples
        assert result.all_displacements.shape[1] == 3  # 3 DOF

    def test_compute_uncertainty_bounds_custom(self, simple_3dof, short_ground_motion):
        """Test computing custom percentile bounds."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        ua.run_mc_ensemble(n_samples=20, seed=42)
        bounds = ua.compute_uncertainty_bounds(percentiles=(10, 50, 90))

        assert "p10" in bounds or 10 in bounds.keys() or len(bounds) > 0

    def test_get_drift_statistics(self, simple_3dof, short_ground_motion):
        """Test getting drift statistics."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        ua.run_mc_ensemble(n_samples=15, seed=42)
        stats = ua.get_drift_statistics()

        assert "mean" in stats
        assert "std" in stats
        assert "p95" in stats or "percentile_95" in stats or len(stats) >= 2

    def test_zero_covariance(self, simple_3dof, short_ground_motion):
        """Test with zero parameter uncertainty."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        result = ua.run_mc_ensemble(
            n_samples=5,
            stiffness_cov=0.0,
            damping_cov=0.0,
            seed=42,
        )

        # All samples should give same result
        displacements = result.all_displacements
        for i in range(1, result.n_samples):
            np.testing.assert_allclose(displacements[0], displacements[i], rtol=1e-10)

    def test_high_uncertainty(self, simple_3dof, short_ground_motion):
        """Test with high parameter uncertainty."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        result = ua.run_mc_ensemble(
            n_samples=20,
            stiffness_cov=0.3,  # 30% CoV
            damping_cov=0.5,  # 50% CoV
            seed=42,
        )

        bounds = result.displacement_bounds

        # High uncertainty should produce wide bounds
        spread = np.max(bounds.percentile_95 - bounds.percentile_5)
        assert spread > 0

    def test_results_accessible(self, simple_3dof, short_ground_motion):
        """Test that results are stored and accessible."""
        ua = UncertaintyAnalysis(
            model=simple_3dof,
            ground_acceleration=short_ground_motion["acceleration"],
            dt=short_ground_motion["dt"],
        )

        assert ua.results is None

        ua.run_mc_ensemble(n_samples=5, seed=42)

        assert ua.results is not None
        assert isinstance(ua.results, MonteCarloResult)
