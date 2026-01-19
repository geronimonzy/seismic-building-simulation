"""Tests for the building module."""

import numpy as np
import pytest

from seismic_twin.building import MDOFShearBuilding


class TestMDOFShearBuilding:
    """Test cases for MDOFShearBuilding class."""

    def test_single_dof_natural_frequency(self):
        """Test natural frequency of single DOF system."""
        mass = 1000.0  # kg
        stiffness = 40000.0  # N/m
        expected_omega = np.sqrt(stiffness / mass)
        expected_period = 2 * np.pi / expected_omega

        building = MDOFShearBuilding(
            masses=np.array([mass]),
            stiffnesses=np.array([stiffness]),
            damping_ratio=0.05,
        )

        assert building.n_dof == 1
        np.testing.assert_almost_equal(
            building.natural_frequencies[0], expected_omega, decimal=3
        )
        np.testing.assert_almost_equal(
            building.natural_periods[0], expected_period, decimal=3
        )

    def test_two_dof_mode_shapes(self):
        """Test mode shapes of 2-DOF system with equal masses and stiffnesses."""
        mass = 1000.0
        stiffness = 100000.0

        building = MDOFShearBuilding(
            masses=np.array([mass, mass]),
            stiffnesses=np.array([stiffness, stiffness]),
            damping_ratio=0.05,
        )

        assert building.n_dof == 2
        assert len(building.natural_frequencies) == 2

        # First mode: same sign (in-phase)
        mode1 = building.mode_shapes[:, 0]
        assert np.sign(mode1[0]) == np.sign(mode1[1])

        # Second mode: opposite sign (out-of-phase)
        mode2 = building.mode_shapes[:, 1]
        assert np.sign(mode2[0]) != np.sign(mode2[1])

    def test_natural_periods_order(self):
        """Test that natural periods are in descending order (frequencies ascending)."""
        building = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0, 1000.0]),
            stiffnesses=np.array([100000.0, 80000.0, 60000.0]),
            damping_ratio=0.05,
        )

        # Frequencies should be in ascending order
        assert np.all(np.diff(building.natural_frequencies) >= 0)

        # Periods should be in descending order
        assert np.all(np.diff(building.natural_periods) <= 0)

    def test_mass_matrix_diagonal(self):
        """Test that mass matrix is diagonal."""
        masses = np.array([1000.0, 2000.0, 1500.0])
        building = MDOFShearBuilding(
            masses=masses,
            stiffnesses=np.array([100000.0, 100000.0, 100000.0]),
            damping_ratio=0.05,
        )

        # Mass matrix should be diagonal
        assert np.allclose(building.M, np.diag(masses))

    def test_stiffness_matrix_tridiagonal(self):
        """Test that stiffness matrix is symmetric tridiagonal."""
        building = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0, 1000.0]),
            stiffnesses=np.array([100000.0, 80000.0, 60000.0]),
            damping_ratio=0.05,
        )

        K = building.K

        # Should be symmetric
        assert np.allclose(K, K.T)

        # Should be tridiagonal (zeros outside tridiagonal band)
        for i in range(K.shape[0]):
            for j in range(K.shape[1]):
                if abs(i - j) > 1:
                    assert K[i, j] == 0

    def test_update_stiffness(self):
        """Test stiffness update functionality."""
        building = MDOFShearBuilding(
            masses=np.array([1000.0]),
            stiffnesses=np.array([40000.0]),
            damping_ratio=0.05,
        )

        initial_period = building.natural_periods[0]
        building.update_stiffness(2.0)  # Double stiffness

        # Period should decrease by sqrt(2)
        expected_new_period = initial_period / np.sqrt(2)
        np.testing.assert_almost_equal(
            building.natural_periods[0], expected_new_period, decimal=4
        )

    def test_update_damping(self):
        """Test damping ratio update functionality."""
        building = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0]),
            stiffnesses=np.array([100000.0, 100000.0]),
            damping_ratio=0.02,
        )

        assert building.damping_ratio == 0.02

        building.update_damping(0.10)
        assert building.damping_ratio == 0.10

    def test_copy(self):
        """Test that copy creates independent instance."""
        original = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0]),
            stiffnesses=np.array([100000.0, 100000.0]),
            damping_ratio=0.05,
        )

        copy = original.copy()

        # Modify original
        original.update_stiffness(2.0)

        # Copy should be unchanged
        assert not np.allclose(original.stiffnesses, copy.stiffnesses)
        assert not np.allclose(original.natural_periods, copy.natural_periods)

    def test_realistic_building_periods(self):
        """Test that a realistic building has reasonable natural periods."""
        # 4-story building
        n_stories = 4
        floor_mass = 100000.0  # 100 tonnes
        story_stiffness = 50000000.0  # 50 MN/m

        building = MDOFShearBuilding(
            masses=np.full(n_stories, floor_mass),
            stiffnesses=np.full(n_stories, story_stiffness),
            damping_ratio=0.05,
        )

        # Fundamental period should be roughly 0.1*N seconds for shear buildings
        # (rule of thumb: T1 ~ 0.1 * n_stories)
        assert 0.1 < building.natural_periods[0] < 2.0

    def test_invalid_stiffness_count_raises_error(self):
        """Test that mismatched masses and stiffnesses raise ValueError."""
        with pytest.raises(ValueError):
            MDOFShearBuilding(
                masses=np.array([1000.0, 1000.0]),
                stiffnesses=np.array([100000.0]),  # Wrong length
                damping_ratio=0.05,
            )

    def test_modal_participation_factors(self):
        """Test modal participation factors calculation."""
        building = MDOFShearBuilding(
            masses=np.array([1000.0, 1000.0, 1000.0]),
            stiffnesses=np.array([100000.0, 100000.0, 100000.0]),
            damping_ratio=0.05,
        )

        gamma = building.get_modal_participation_factors()

        # First mode should have largest participation factor
        assert np.abs(gamma[0]) >= np.abs(gamma[1])
        assert np.abs(gamma[0]) >= np.abs(gamma[2])
