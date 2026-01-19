"""Tests for the analysis module."""

import numpy as np

from seismic_twin.analysis import compute_demand_metrics, newmark_beta
from seismic_twin.analysis.metrics import compute_correlation, compute_nrmse
from seismic_twin.building import MDOFShearBuilding


class TestNewmarkBeta:
    """Test cases for Newmark-beta time integration."""

    def test_zero_input_zero_response(self):
        """Test that zero ground motion produces zero response."""
        building = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0]),
            stiffnesses=np.array([100000.0, 100000.0]),
            damping_ratio=0.05,
        )

        n_steps = 100
        dt = 0.01
        ground_acc = np.zeros(n_steps)

        result = newmark_beta(
            M=building.M,
            C=building.C,
            K=building.K,
            ground_acceleration=ground_acc,
            dt=dt,
        )

        np.testing.assert_array_almost_equal(result.displacement, 0)
        np.testing.assert_array_almost_equal(result.velocity, 0)

    def test_output_shape_correct(self):
        """Test that output arrays have correct shape."""
        n_dof = 3
        building = MDOFShearBuilding(
            masses=np.full(n_dof, 1000.0),
            stiffnesses=np.full(n_dof, 100000.0),
            damping_ratio=0.05,
        )

        n_steps = 500
        dt = 0.01
        ground_acc = np.random.randn(n_steps) * 0.1

        result = newmark_beta(
            M=building.M,
            C=building.C,
            K=building.K,
            ground_acceleration=ground_acc,
            dt=dt,
        )

        assert result.displacement.shape == (n_dof, n_steps)
        assert result.velocity.shape == (n_dof, n_steps)
        assert result.acceleration.shape == (n_dof, n_steps)
        assert result.absolute_acceleration.shape == (n_dof, n_steps)
        assert len(result.time) == n_steps

    def test_free_vibration_decay(self):
        """Test that free vibration decays due to damping."""
        # Single DOF system
        m = 1000.0
        k = 40000.0  # omega = sqrt(k/m) = 6.32 rad/s
        xi = 0.05

        building = MDOFShearBuilding(
            masses=np.array([m]),
            stiffnesses=np.array([k]),
            damping_ratio=xi,
        )

        # Initial impulse followed by free vibration
        dt = 0.01
        n_steps = 1000
        ground_acc = np.zeros(n_steps)
        ground_acc[0:10] = 0.5  # Short impulse

        result = newmark_beta(
            M=building.M,
            C=building.C,
            K=building.K,
            ground_acceleration=ground_acc,
            dt=dt,
        )

        # Get envelope of displacement
        disp = result.displacement[0, :]

        # Find peaks
        peaks = []
        for i in range(1, len(disp) - 1):
            if disp[i] > disp[i - 1] and disp[i] > disp[i + 1] and disp[i] > 0.001:
                peaks.append(disp[i])

        # Peaks should decay
        if len(peaks) > 2:
            assert peaks[-1] < peaks[0]

    def test_resonance_amplification(self):
        """Test that excitation at natural frequency causes amplification."""
        # Single DOF system
        m = 1000.0
        k = 40000.0
        omega_n = np.sqrt(k / m)
        omega_n / (2 * np.pi)

        building = MDOFShearBuilding(
            masses=np.array([m]),
            stiffnesses=np.array([k]),
            damping_ratio=0.02,  # Low damping
        )

        dt = 0.01
        duration = 20.0
        n_steps = int(duration / dt)
        time = np.arange(n_steps) * dt

        # Excitation at natural frequency
        amplitude = 0.1
        ground_acc_resonant = amplitude * np.sin(omega_n * time)

        # Excitation at twice natural frequency
        ground_acc_off = amplitude * np.sin(2 * omega_n * time)

        result_resonant = newmark_beta(
            M=building.M,
            C=building.C,
            K=building.K,
            ground_acceleration=ground_acc_resonant,
            dt=dt,
        )

        result_off = newmark_beta(
            M=building.M,
            C=building.C,
            K=building.K,
            ground_acceleration=ground_acc_off,
            dt=dt,
        )

        max_resonant = np.max(np.abs(result_resonant.displacement))
        max_off = np.max(np.abs(result_off.displacement))

        # Resonant response should be larger
        assert max_resonant > max_off

    def test_energy_conservation_undamped(self):
        """Test energy conservation for undamped system under free vibration."""
        building = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.0,  # No damping
        )

        # Very short impulse then free vibration
        dt = 0.001  # Small time step for accuracy
        n_steps = 5000
        ground_acc = np.zeros(n_steps)
        ground_acc[0:5] = 1.0

        result = newmark_beta(
            M=building.M,
            C=building.C,
            K=building.K,
            ground_acceleration=ground_acc,
            dt=dt,
        )

        # Compute total mechanical energy after impulse
        u = result.displacement[0, 100:]
        v = result.velocity[0, 100:]
        m = building.masses[0]
        k = building.stiffnesses[0]

        kinetic = 0.5 * m * v**2
        potential = 0.5 * k * u**2
        total_energy = kinetic + potential

        # Energy should be approximately constant (within 5%)
        energy_variation = (np.max(total_energy) - np.min(total_energy)) / np.mean(total_energy)
        assert energy_variation < 0.05


class TestDemandMetrics:
    """Test cases for demand metrics computation."""

    def test_max_displacement_correct(self):
        """Test that max displacement is computed correctly."""
        n_dof = 2
        n_steps = 100
        displacement = np.random.randn(n_dof, n_steps)
        velocity = np.zeros((n_dof, n_steps))
        acceleration = np.zeros((n_dof, n_steps))
        ground_acc = np.zeros(n_steps)
        story_heights = np.array([3.5, 3.5])

        metrics = compute_demand_metrics(
            displacement=displacement,
            velocity=velocity,
            absolute_acceleration=acceleration,
            ground_acceleration=ground_acc,
            story_heights=story_heights,
        )

        expected_max = np.max(np.abs(displacement), axis=1)
        np.testing.assert_array_almost_equal(metrics.max_displacement, expected_max)

    def test_drift_ratio_calculation(self):
        """Test inter-story drift ratio calculation."""
        n_steps = 10
        # Two-story building with known displacements
        h1, h2 = 3.5, 3.0  # story heights
        u1_max = 0.035  # 1% drift at first story
        u2_max = 0.070  # relative to ground

        displacement = np.zeros((2, n_steps))
        displacement[0, :] = u1_max
        displacement[1, :] = u2_max

        metrics = compute_demand_metrics(
            displacement=displacement,
            velocity=np.zeros((2, n_steps)),
            absolute_acceleration=np.zeros((2, n_steps)),
            ground_acceleration=np.zeros(n_steps),
            story_heights=np.array([h1, h2]),
        )

        # First story drift: u1 / h1 = 0.035 / 3.5 = 0.01
        # Second story drift: (u2 - u1) / h2 = 0.035 / 3.0 = 0.0117
        np.testing.assert_almost_equal(metrics.inter_story_drift_ratio[0], 0.035 / 3.5, decimal=4)
        np.testing.assert_almost_equal(
            metrics.inter_story_drift_ratio[1], (0.070 - 0.035) / 3.0, decimal=4
        )


class TestMetricFunctions:
    """Test cases for individual metric functions."""

    def test_nrmse_perfect_match(self):
        """Test that NRMSE is zero for identical arrays."""
        signal = np.random.randn(100)
        nrmse = compute_nrmse(signal, signal)
        assert nrmse == 0.0

    def test_nrmse_scaled_signal(self):
        """Test NRMSE for scaled signal."""
        signal = np.random.randn(100)
        scaled = signal * 1.1  # 10% scale

        nrmse = compute_nrmse(scaled, signal)
        assert 0 < nrmse < 0.2  # Should be small but non-zero

    def test_correlation_perfect_match(self):
        """Test correlation is 1 for identical signals."""
        signal = np.random.randn(100)
        corr = compute_correlation(signal, signal)
        np.testing.assert_almost_equal(corr, 1.0)

    def test_correlation_anticorrelated(self):
        """Test correlation is -1 for negated signal."""
        signal = np.random.randn(100)
        corr = compute_correlation(-signal, signal)
        np.testing.assert_almost_equal(corr, -1.0)

    def test_correlation_uncorrelated(self):
        """Test correlation is near 0 for uncorrelated signals."""
        np.random.seed(42)
        signal1 = np.random.randn(1000)
        signal2 = np.random.randn(1000)

        corr = compute_correlation(signal1, signal2)
        assert abs(corr) < 0.1  # Should be near zero
