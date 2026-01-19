"""Numerical accuracy tests validating against analytical solutions."""

import numpy as np
from scipy.linalg import eigh

from seismic_twin.analysis import compute_demand_metrics, newmark_beta
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion.synthetic import compute_response_spectrum


class TestNumericalAccuracy:
    """Validate integration accuracy against analytical solutions."""

    def test_single_dof_undamped_free_vibration(self):
        """
        Test undamped SDOF oscillator response to impulse.

        For an undamped system with initial velocity, the analytical solution is:
            u(t) = (v0/ω) * sin(ωt)
        where ω = sqrt(k/m)
        """
        m, k = 1.0, 100.0  # ω = 10 rad/s
        omega = np.sqrt(k / m)

        M = np.array([[m]])
        K = np.array([[k]])
        C = np.zeros((1, 1))

        # Apply impulse via ground motion
        dt = 0.001
        n_steps = 5000
        ground_acc = np.zeros(n_steps)
        # Small initial impulse
        ground_acc[0] = 1.0 / dt

        result = newmark_beta(M, C, K, ground_acc, dt)

        # Check periodicity - peaks should occur at T/4, 5T/4, 9T/4, etc.
        period = 2 * np.pi / omega
        peak_times = result.time[np.where(np.diff(np.sign(result.velocity[0, :])) < 0)[0]]

        if len(peak_times) >= 2:
            measured_period = np.mean(np.diff(peak_times))
            np.testing.assert_allclose(measured_period, period, rtol=0.05)

    def test_single_dof_damped_decay(self):
        """
        Test damped SDOF oscillator exponential decay.

        For underdamped system, amplitude decays as exp(-ζωt).
        """
        m, k = 1.0, 100.0
        zeta = 0.05
        omega = np.sqrt(k / m)
        c = 2 * zeta * omega * m

        M = np.array([[m]])
        K = np.array([[k]])
        C = np.array([[c]])

        dt = 0.001
        n_steps = 10000
        ground_acc = np.zeros(n_steps)
        ground_acc[0] = 10.0  # Initial impulse

        result = newmark_beta(M, C, K, ground_acc, dt)

        # Find peaks
        disp = result.displacement[0, :]
        peaks_idx = []
        for i in range(1, len(disp) - 1):
            if disp[i] > disp[i - 1] and disp[i] > disp[i + 1] and disp[i] > 0:
                peaks_idx.append(i)

        if len(peaks_idx) >= 3:
            peak_values = np.abs(disp[peaks_idx[:5]])
            peak_times = result.time[peaks_idx[:5]]

            # Fit exponential decay
            log_peaks = np.log(peak_values)
            decay_rate = -np.polyfit(peak_times, log_peaks, 1)[0]

            # Expected decay rate is ζω
            expected_decay = zeta * omega
            np.testing.assert_allclose(decay_rate, expected_decay, rtol=0.1)

    def test_multi_dof_natural_frequencies(self):
        """Test MDOF system natural frequencies match eigenvalue analysis."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
            story_heights=np.array([3.5, 3.5, 3.0]),
        )

        # Compute eigenvalues directly
        eigenvalues, _ = eigh(model.K, model.M)
        expected_freqs = np.sqrt(eigenvalues)

        # Compare to model's natural frequencies
        np.testing.assert_allclose(
            np.sort(model.natural_frequencies),
            np.sort(expected_freqs),
            rtol=1e-10,
        )

    def test_natural_frequency_ordering(self):
        """Test natural frequencies are in ascending order."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 90e3, 80e3, 70e3]),
            stiffnesses=np.array([60e6, 55e6, 50e6, 45e6]),
            damping_ratio=0.05,
        )

        freqs = model.natural_frequencies
        assert np.all(np.diff(freqs) >= 0), "Natural frequencies should be ascending"

    def test_mode_shape_orthogonality(self):
        """Test mode shapes are M-orthogonal."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
        )

        modes = model.mode_shapes
        M = model.M

        # Check M-orthogonality: φi^T M φj = 0 for i ≠ j
        for i in range(model.n_dof):
            for j in range(i + 1, model.n_dof):
                cross = modes[:, i] @ M @ modes[:, j]
                assert abs(cross) < 1e-10, f"Modes {i} and {j} not M-orthogonal"

    def test_energy_conservation_undamped(self):
        """Test energy conservation for undamped system."""
        m, k = 1000.0, 100000.0

        M = np.array([[m]])
        K = np.array([[k]])
        C = np.zeros((1, 1))

        dt = 0.001
        n_steps = 2000
        ground_acc = np.zeros(n_steps)
        ground_acc[0] = 5.0  # Initial impulse

        result = newmark_beta(M, C, K, ground_acc, dt)

        # Compute total energy at each step
        energies = []
        for i in range(100, n_steps):  # Skip initial transient
            ke = 0.5 * m * result.velocity[0, i] ** 2
            pe = 0.5 * k * result.displacement[0, i] ** 2
            energies.append(ke + pe)

        # Energy should be approximately constant
        energy_std = np.std(energies)
        energy_mean = np.mean(energies)
        assert energy_std / energy_mean < 0.01, "Energy not conserved"

    def test_energy_dissipation_damped(self):
        """Test energy dissipation for damped system."""
        m, k = 1000.0, 100000.0
        zeta = 0.1
        omega = np.sqrt(k / m)
        c = 2 * zeta * omega * m

        M = np.array([[m]])
        K = np.array([[k]])
        C = np.array([[c]])

        dt = 0.001
        n_steps = 5000
        ground_acc = np.zeros(n_steps)
        ground_acc[0] = 10.0

        result = newmark_beta(M, C, K, ground_acc, dt)

        # Initial energy
        initial_ke = 0.5 * m * result.velocity[0, 10] ** 2
        initial_pe = 0.5 * k * result.displacement[0, 10] ** 2
        initial_energy = initial_ke + initial_pe

        # Final energy
        final_ke = 0.5 * m * result.velocity[0, -1] ** 2
        final_pe = 0.5 * k * result.displacement[0, -1] ** 2
        final_energy = final_ke + final_pe

        # Energy should decrease
        assert final_energy < initial_energy

    def test_resonance_amplification(self):
        """Test response amplification at resonance."""
        m, k = 1.0, (2 * np.pi) ** 2  # ω = 2π rad/s, f = 1 Hz
        zeta = 0.05

        omega = np.sqrt(k / m)
        c = 2 * zeta * omega * m

        M = np.array([[m]])
        K = np.array([[k]])
        C = np.array([[c]])

        dt = 0.01
        duration = 50.0
        time = np.arange(0, duration, dt)

        # At resonance (f = 1 Hz)
        ground_acc_resonance = 0.1 * np.sin(2 * np.pi * 1.0 * time)

        # Off resonance (f = 3 Hz)
        ground_acc_off = 0.1 * np.sin(2 * np.pi * 3.0 * time)

        result_resonance = newmark_beta(M, C, K, ground_acc_resonance, dt)
        result_off = newmark_beta(M, C, K, ground_acc_off, dt)

        max_resonance = np.max(np.abs(result_resonance.displacement))
        max_off = np.max(np.abs(result_off.displacement))

        # Resonance should produce larger response
        assert max_resonance > max_off * 2


class TestBenchmarkValidation:
    """Validate against expected structural behavior."""

    def test_first_mode_dominance(self):
        """Test that first mode dominates for typical building."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
        )

        # Participation factors should show first mode dominance
        # (for typical buildings with uniform mass)
        first_mode = model.mode_shapes[:, 0]

        # First mode should have same-sign components (all moving together)
        assert np.all(np.sign(first_mode) == np.sign(first_mode[0]))

    def test_period_lengthening_with_height(self):
        """Test that taller buildings have longer periods."""
        short_building = MDOFShearBuilding(
            masses=np.array([100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6]),
            damping_ratio=0.05,
        )

        tall_building = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6, 50e6, 50e6]),
            damping_ratio=0.05,
        )

        assert tall_building.natural_periods[0] > short_building.natural_periods[0]

    def test_drift_increases_with_height(self):
        """Test that drift generally increases with height."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
            story_heights=np.array([3.5, 3.5, 3.0]),
        )

        dt = 0.01
        time = np.arange(0, 10, dt)
        ground_acc = 0.2 * 9.81 * np.sin(2 * np.pi * 1.5 * time)

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)
        metrics = compute_demand_metrics(
            result.displacement,
            result.velocity,
            result.absolute_acceleration,
            ground_acc,
            model.story_heights,
        )

        # Top floor displacement should be larger than bottom
        assert metrics.max_displacement[-1] >= metrics.max_displacement[0]

    def test_response_spectrum_shape(self):
        """Test response spectrum has expected shape."""
        dt = 0.01
        duration = 20.0
        time = np.arange(0, duration, dt)

        # Create broadband ground motion
        np.random.seed(42)
        ground_acc = np.random.randn(len(time)) * 0.3
        ground_acc *= np.exp(-0.1 * time)  # Decay envelope

        periods = np.logspace(-1, 1, 50)  # 0.1s to 10s
        _, Sa = compute_response_spectrum(time, ground_acc, periods=periods)

        # Response spectrum should:
        # 1. Be positive
        assert np.all(Sa >= 0)

        # 2. Have finite values
        assert np.all(np.isfinite(Sa))

        # 3. Generally decrease at long periods
        assert Sa[-1] < Sa[len(Sa) // 2]
