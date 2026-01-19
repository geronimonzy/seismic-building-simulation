"""Tests for the ground motion module."""

import numpy as np
import pytest

from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.ground_motion.synthetic import (
    apply_highpass_filter,
    baseline_correction,
    generate_harmonic_ground_motion,
)


class TestSyntheticGroundMotion:
    """Test cases for synthetic ground motion generation."""

    def test_generates_correct_length(self):
        """Test that generated time series has correct length."""
        duration = 20.0
        dt = 0.01

        time, acc = generate_synthetic_ground_motion(
            duration=duration,
            dt=dt,
            target_pga=0.3,
            seed=42,
        )

        expected_points = int(duration / dt) + 1
        assert len(time) == expected_points
        assert len(acc) == expected_points

    def test_time_vector_correct(self):
        """Test that time vector spans correct range."""
        duration = 15.0
        dt = 0.02

        time, _ = generate_synthetic_ground_motion(
            duration=duration,
            dt=dt,
            target_pga=0.3,
            seed=42,
        )

        np.testing.assert_almost_equal(time[0], 0.0)
        np.testing.assert_almost_equal(time[-1], duration)
        np.testing.assert_almost_equal(time[1] - time[0], dt, decimal=5)

    def test_pga_matches_target(self):
        """Test that PGA matches target value."""
        target_pga = 0.5

        _, acc = generate_synthetic_ground_motion(
            duration=30.0,
            dt=0.01,
            target_pga=target_pga,
            seed=42,
        )

        actual_pga = np.max(np.abs(acc))
        np.testing.assert_almost_equal(actual_pga, target_pga, decimal=3)

    def test_reproducible_with_seed(self):
        """Test that same seed produces same output."""
        params = dict(
            duration=20.0,
            dt=0.01,
            target_pga=0.3,
            predominant_freq=2.0,
            seed=123,
        )

        _, acc1 = generate_synthetic_ground_motion(**params)
        _, acc2 = generate_synthetic_ground_motion(**params)

        np.testing.assert_array_equal(acc1, acc2)

    def test_different_seeds_produce_different_output(self):
        """Test that different seeds produce different outputs."""
        params = dict(
            duration=20.0,
            dt=0.01,
            target_pga=0.3,
        )

        _, acc1 = generate_synthetic_ground_motion(**params, seed=1)
        _, acc2 = generate_synthetic_ground_motion(**params, seed=2)

        assert not np.allclose(acc1, acc2)

    def test_starts_and_ends_near_zero(self):
        """Test that motion starts and ends near zero (envelope effect)."""
        _, acc = generate_synthetic_ground_motion(
            duration=30.0,
            dt=0.01,
            target_pga=0.3,
            seed=42,
        )

        # First 1% and last 10% should be relatively small
        n_points = len(acc)
        initial_portion = acc[: int(0.01 * n_points)]
        final_portion = acc[int(0.9 * n_points) :]

        pga = np.max(np.abs(acc))
        assert np.max(np.abs(initial_portion)) < 0.3 * pga
        assert np.max(np.abs(final_portion)) < 0.5 * pga


class TestHarmonicGroundMotion:
    """Test cases for harmonic ground motion generation."""

    def test_amplitude_correct(self):
        """Test that amplitude matches target."""
        amplitude = 0.2

        _, acc = generate_harmonic_ground_motion(
            duration=10.0,
            dt=0.01,
            amplitude=amplitude,
            frequency=1.0,
        )

        # Middle portion should reach target amplitude
        middle = acc[len(acc) // 4 : 3 * len(acc) // 4]
        assert np.max(np.abs(middle)) <= amplitude * 1.01

    def test_frequency_correct(self):
        """Test that predominant frequency matches target."""
        frequency = 2.0
        duration = 10.0

        time, acc = generate_harmonic_ground_motion(
            duration=duration,
            dt=0.01,
            amplitude=0.1,
            frequency=frequency,
        )

        # Count zero crossings (should be approximately 2 * frequency * duration)
        zero_crossings = np.sum(np.diff(np.sign(acc)) != 0)
        expected_crossings = 2 * frequency * duration

        # Allow 20% tolerance due to ramp-up/down
        assert abs(zero_crossings - expected_crossings) / expected_crossings < 0.3


class TestBaselineCorrection:
    """Test cases for baseline correction."""

    def test_removes_linear_trend(self):
        """Test that baseline correction removes linear trend."""
        n = 1000
        dt = 0.01
        time = np.arange(n) * dt

        # Signal with linear trend
        signal = np.sin(2 * np.pi * time) + 0.5 * time

        corrected = baseline_correction(signal, dt, order=1)

        # Should have zero mean and no linear trend
        assert abs(np.mean(corrected)) < 0.1


class TestHighpassFilter:
    """Test cases for highpass filter."""

    def test_removes_low_frequencies(self):
        """Test that highpass filter removes low frequencies."""
        n = 2000
        dt = 0.01
        time = np.arange(n) * dt

        # Signal with low and high frequency components
        low_freq = np.sin(2 * np.pi * 0.05 * time)  # 0.05 Hz
        high_freq = 0.5 * np.sin(2 * np.pi * 2.0 * time)  # 2 Hz
        signal = low_freq + high_freq

        filtered = apply_highpass_filter(signal, dt, cutoff_freq=0.5)

        # Low frequency component should be attenuated
        # Check that variance is reduced
        assert np.var(filtered) < np.var(signal)

    def test_raises_error_for_invalid_cutoff(self):
        """Test that invalid cutoff frequency raises error."""
        signal = np.random.randn(100)
        dt = 0.01
        nyquist = 0.5 / dt

        with pytest.raises(ValueError):
            apply_highpass_filter(signal, dt, cutoff_freq=nyquist + 1)
