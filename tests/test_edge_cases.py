"""Edge case and boundary condition tests."""

import numpy as np

from seismic_twin.analysis import compute_demand_metrics, newmark_beta
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.ground_motion.synthetic import (
    apply_highpass_filter,
    baseline_correction,
)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_dof_system(self):
        """Single DOF system should work correctly."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.05,
        )

        assert model.n_dof == 1
        assert model.M.shape == (1, 1)
        assert model.K.shape == (1, 1)
        assert model.C.shape == (1, 1)

        dt = 0.01
        ground_acc = 0.1 * 9.81 * np.sin(2 * np.pi * np.arange(0, 5, dt))

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        assert result.displacement.shape == (1, len(ground_acc))

    def test_very_short_time_history(self):
        """Very short time history (< 10 steps) should still work."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.05,
        )

        ground_acc = np.array([0.1, 0.2, 0.1, 0.0, -0.1])
        dt = 0.01

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        assert result.displacement.shape == (1, 5)
        assert result.time.shape == (5,)

    def test_zero_input_zero_response(self):
        """Zero ground motion should produce zero response."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0]),
            stiffnesses=np.array([50000.0, 50000.0]),
            damping_ratio=0.05,
        )

        ground_acc = np.zeros(100)
        dt = 0.01

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        np.testing.assert_allclose(result.displacement, 0, atol=1e-15)
        np.testing.assert_allclose(result.velocity, 0, atol=1e-15)

    def test_very_stiff_system(self):
        """Very high stiffness should not cause numerical issues."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([1e12]),  # Very stiff
            damping_ratio=0.05,
        )

        dt = 0.0001  # Small timestep for stability
        ground_acc = 0.1 * 9.81 * np.sin(2 * np.pi * 10 * np.arange(0, 0.5, dt))

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        # Should produce finite, small displacements
        assert np.all(np.isfinite(result.displacement))
        assert np.max(np.abs(result.displacement)) < 1e-6

    def test_very_flexible_system(self):
        """Very low stiffness should not cause issues."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([100.0]),  # Very flexible
            damping_ratio=0.05,
        )

        dt = 0.01
        ground_acc = 0.1 * 9.81 * np.sin(2 * np.pi * 0.1 * np.arange(0, 20, dt))

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        assert np.all(np.isfinite(result.displacement))

    def test_high_damping(self):
        """High damping (ζ > 0.5) should be handled."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.7,  # Overdamped
        )

        dt = 0.01
        ground_acc = 0.1 * 9.81 * np.sin(2 * np.pi * np.arange(0, 5, dt))

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        # Should produce finite results
        assert np.all(np.isfinite(result.displacement))

        # Overdamped system should not oscillate much
        # Response should be smooth

    def test_critical_damping(self):
        """Critical damping (ζ = 1.0) should work."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=1.0,  # Critically damped
        )

        dt = 0.01
        ground_acc = np.zeros(500)
        ground_acc[0] = 10.0  # Impulse

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        # Should return to zero without oscillation
        assert np.all(np.isfinite(result.displacement))

    def test_small_timestep(self):
        """Very small dt should not cause issues."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.05,
        )

        dt = 0.0001  # Very small
        n_steps = 1000
        ground_acc = 0.1 * np.sin(2 * np.pi * 5 * np.arange(n_steps) * dt)

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        assert np.all(np.isfinite(result.displacement))

    def test_large_timestep(self):
        """Large dt should still work (may be less accurate)."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.05,
        )

        dt = 0.1  # Large timestep
        ground_acc = 0.1 * np.sin(2 * np.pi * 0.5 * np.arange(0, 20, dt))

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        # Should still be finite
        assert np.all(np.isfinite(result.displacement))

    def test_uniform_masses_and_stiffnesses(self):
        """Uniform system should have known modal properties."""
        n_dof = 3
        model = MDOFShearBuilding(
            masses=np.array([1000.0] * n_dof),
            stiffnesses=np.array([50000.0] * n_dof),
            damping_ratio=0.05,
        )

        # First mode should have increasing amplitudes
        first_mode = np.abs(model.mode_shapes[:, 0])
        assert np.all(np.diff(first_mode) >= 0)

    def test_varying_story_heights(self):
        """Different story heights should be handled."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
            story_heights=np.array([5.0, 3.5, 3.0]),  # Different heights
        )

        assert len(model.story_heights) == 3
        assert model.story_heights[0] == 5.0


class TestGroundMotionEdgeCases:
    """Test edge cases for ground motion processing."""

    def test_very_short_duration(self):
        """Very short ground motion duration."""
        time, acc = generate_synthetic_ground_motion(
            duration=1.0,
            dt=0.01,
            target_pga=0.2,
            seed=42,
        )

        assert len(time) == len(acc)
        assert time[-1] < 1.1

    def test_very_long_duration(self):
        """Long duration ground motion."""
        time, acc = generate_synthetic_ground_motion(
            duration=120.0,
            dt=0.02,
            target_pga=0.1,
            seed=42,
        )

        assert time[-1] >= 119.0

    def test_high_sampling_rate(self):
        """High sampling rate (small dt)."""
        time, acc = generate_synthetic_ground_motion(
            duration=5.0,
            dt=0.001,  # 1000 Hz
            target_pga=0.2,
            seed=42,
        )

        # Duration / dt + 1 for inclusive endpoint
        assert len(time) >= 5000

    def test_low_sampling_rate(self):
        """Low sampling rate (large dt)."""
        time, acc = generate_synthetic_ground_motion(
            duration=10.0,
            dt=0.1,  # 10 Hz
            target_pga=0.2,
            seed=42,
        )

        assert len(time) >= 100

    def test_baseline_correction_flat_signal(self):
        """Baseline correction on already flat signal."""
        acc = np.zeros(1000)
        dt = 0.01

        corrected = baseline_correction(acc, dt)

        np.testing.assert_allclose(corrected, 0, atol=1e-15)

    def test_baseline_correction_with_trend(self):
        """Baseline correction removes linear trend."""
        dt = 0.01
        n = 1000
        time = np.arange(n) * dt

        # Add linear trend
        acc = 0.1 * time + np.random.randn(n) * 0.01

        corrected = baseline_correction(acc, dt)

        # Mean should be near zero
        assert abs(np.mean(corrected)) < 0.01

    def test_highpass_filter_removes_dc(self):
        """Highpass filter removes DC offset."""
        dt = 0.01
        n = 1000

        # Signal with DC offset
        acc = 0.5 + 0.1 * np.sin(2 * np.pi * 2 * np.arange(n) * dt)

        filtered = apply_highpass_filter(acc, dt, cutoff_freq=0.1)

        # DC should be removed
        assert abs(np.mean(filtered)) < 0.1


class TestDemandMetricsEdgeCases:
    """Test edge cases for demand metrics computation."""

    def test_single_story(self):
        """Single story building metrics."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.05,
            story_heights=np.array([3.5]),
        )

        dt = 0.01
        ground_acc = 0.1 * 9.81 * np.sin(2 * np.pi * np.arange(0, 5, dt))

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)
        metrics = compute_demand_metrics(
            result.displacement,
            result.velocity,
            result.absolute_acceleration,
            ground_acc,
            model.story_heights,
        )

        assert len(metrics.max_displacement) == 1
        assert len(metrics.inter_story_drift_ratio) == 1

    def test_zero_displacement_metrics(self):
        """Metrics for zero displacement response."""
        model = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0]),
            stiffnesses=np.array([50000.0, 50000.0]),
            damping_ratio=0.05,
            story_heights=np.array([3.5, 3.5]),
        )

        ground_acc = np.zeros(100)
        dt = 0.01

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)
        metrics = compute_demand_metrics(
            result.displacement,
            result.velocity,
            result.absolute_acceleration,
            ground_acc,
            model.story_heights,
        )

        assert np.all(metrics.max_displacement == 0)
        assert np.all(metrics.inter_story_drift_ratio == 0)
