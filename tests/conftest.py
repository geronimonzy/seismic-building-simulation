"""Shared pytest fixtures for seismic_twin tests."""

import numpy as np
import pytest

from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion


@pytest.fixture
def simple_sdof():
    """Single DOF system for basic testing."""
    return MDOFShearBuilding(
        masses=np.array([1000.0]),
        stiffnesses=np.array([40000.0]),
        damping_ratio=0.05,
    )


@pytest.fixture
def simple_2dof():
    """2-DOF system for testing."""
    return MDOFShearBuilding(
        masses=np.array([1000.0, 1000.0]),
        stiffnesses=np.array([100000.0, 100000.0]),
        damping_ratio=0.05,
        story_heights=np.array([3.5, 3.5]),
    )


@pytest.fixture
def simple_3dof():
    """3-story building for testing."""
    return MDOFShearBuilding(
        masses=np.array([100e3, 100e3, 100e3]),
        stiffnesses=np.array([50e6, 50e6, 50e6]),
        damping_ratio=0.05,
        story_heights=np.array([3.5, 3.5, 3.0]),
    )


@pytest.fixture
def realistic_building():
    """5-story realistic building model."""
    return MDOFShearBuilding(
        masses=np.array([150e3, 140e3, 130e3, 120e3, 100e3]),
        stiffnesses=np.array([80e6, 75e6, 70e6, 65e6, 60e6]),
        damping_ratio=0.05,
        story_heights=np.array([4.0, 3.5, 3.5, 3.5, 3.0]),
    )


@pytest.fixture
def simple_ground_motion():
    """Simple sinusoidal ground motion for testing."""
    dt = 0.01
    duration = 10.0
    time = np.arange(0, duration, dt)
    acc = 0.1 * 9.81 * np.sin(2 * np.pi * 2 * time)
    return {"time": time, "acceleration": acc, "dt": dt}


@pytest.fixture
def short_ground_motion():
    """Short duration ground motion."""
    dt = 0.01
    duration = 2.0
    time = np.arange(0, duration, dt)
    acc = 0.2 * 9.81 * np.sin(2 * np.pi * 1.5 * time) * np.exp(-0.5 * time)
    return {"time": time, "acceleration": acc, "dt": dt}


@pytest.fixture
def synthetic_earthquake():
    """Synthetic earthquake record."""
    time, acc = generate_synthetic_ground_motion(duration=20.0, dt=0.01, target_pga=0.3, seed=42)
    return {"time": time, "acceleration": acc, "dt": 0.01}


@pytest.fixture
def zero_ground_motion():
    """Zero ground motion for free vibration tests."""
    dt = 0.01
    n_steps = 1000
    return {
        "time": np.arange(n_steps) * dt,
        "acceleration": np.zeros(n_steps),
        "dt": dt,
    }
