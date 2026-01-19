"""
Engineering Demand Parameters (EDPs) and Structural Metrics

This module provides functions for computing various engineering demand
parameters commonly used in seismic performance assessment.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray


@dataclass
class DemandMetrics:
    """Container for engineering demand parameters."""

    max_displacement: NDArray[np.floating]  # Maximum displacement per floor
    max_velocity: NDArray[np.floating]  # Maximum velocity per floor
    max_acceleration: NDArray[np.floating]  # Maximum absolute acceleration per floor
    inter_story_drift_ratio: NDArray[np.floating]  # Max drift ratio per story
    residual_displacement: NDArray[np.floating]  # Final displacement per floor
    peak_ground_acceleration: float  # PGA of input motion

    def __repr__(self) -> str:
        return (
            f"DemandMetrics(\n"
            f"  max_roof_disp={self.max_displacement[-1]:.4f} m,\n"
            f"  max_drift_ratio={np.max(self.inter_story_drift_ratio):.4f},\n"
            f"  max_floor_acc={np.max(self.max_acceleration):.3f} g,\n"
            f"  PGA={self.peak_ground_acceleration:.3f} g\n"
            f")"
        )


def compute_demand_metrics(
    displacement: NDArray[np.floating],
    velocity: NDArray[np.floating],
    absolute_acceleration: NDArray[np.floating],
    ground_acceleration: NDArray[np.floating],
    story_heights: NDArray[np.floating],
) -> DemandMetrics:
    """
    Compute engineering demand parameters from time history response.

    Parameters
    ----------
    displacement : ndarray
        Relative displacement time history (n_dof x n_steps) in meters.
    velocity : ndarray
        Relative velocity time history (n_dof x n_steps) in m/s.
    absolute_acceleration : ndarray
        Absolute acceleration time history (n_dof x n_steps) in m/s^2.
    ground_acceleration : ndarray
        Ground acceleration time history (n_steps,) in g.
    story_heights : ndarray
        Story heights (n_dof,) in meters.

    Returns
    -------
    DemandMetrics
        Container with computed engineering demand parameters.
    """
    n_dof = displacement.shape[0]

    # Maximum response values
    max_displacement = np.max(np.abs(displacement), axis=1)
    max_velocity = np.max(np.abs(velocity), axis=1)
    max_acceleration = np.max(np.abs(absolute_acceleration), axis=1) / 9.81  # Convert to g

    # Inter-story drift ratio
    # Drift ratio = (u_i - u_{i-1}) / h_i
    inter_story_drift = np.zeros((n_dof, displacement.shape[1]))
    inter_story_drift[0, :] = displacement[0, :] / story_heights[0]
    for i in range(1, n_dof):
        inter_story_drift[i, :] = (
            (displacement[i, :] - displacement[i - 1, :]) / story_heights[i]
        )

    inter_story_drift_ratio = np.max(np.abs(inter_story_drift), axis=1)

    # Residual displacement (final value)
    residual_displacement = displacement[:, -1]

    # Peak ground acceleration
    peak_ground_acceleration = np.max(np.abs(ground_acceleration))

    return DemandMetrics(
        max_displacement=max_displacement,
        max_velocity=max_velocity,
        max_acceleration=max_acceleration,
        inter_story_drift_ratio=inter_story_drift_ratio,
        residual_displacement=residual_displacement,
        peak_ground_acceleration=peak_ground_acceleration,
    )


def compute_nrmse(
    prediction: NDArray[np.floating],
    measurement: NDArray[np.floating],
) -> float:
    """
    Compute Normalized Root Mean Square Error.

    NRMSE = sqrt(mean((pred - meas)^2)) / (max(meas) - min(meas))

    Parameters
    ----------
    prediction : ndarray
        Predicted response time history.
    measurement : ndarray
        Measured response time history.

    Returns
    -------
    float
        NRMSE value (0 = perfect match).
    """
    rmse = np.sqrt(np.mean((prediction - measurement) ** 2))
    range_meas = np.max(measurement) - np.min(measurement)

    if range_meas < 1e-10:
        return 0.0 if rmse < 1e-10 else float("inf")

    return rmse / range_meas


def compute_correlation(
    prediction: NDArray[np.floating],
    measurement: NDArray[np.floating],
) -> float:
    """
    Compute Pearson correlation coefficient.

    Parameters
    ----------
    prediction : ndarray
        Predicted response time history.
    measurement : ndarray
        Measured response time history.

    Returns
    -------
    float
        Correlation coefficient (-1 to 1).
    """
    pred_centered = prediction - np.mean(prediction)
    meas_centered = measurement - np.mean(measurement)

    numerator = np.sum(pred_centered * meas_centered)
    denominator = np.sqrt(np.sum(pred_centered**2) * np.sum(meas_centered**2))

    if denominator < 1e-10:
        return 0.0

    return numerator / denominator


def compute_arias_intensity(
    acceleration: NDArray[np.floating],
    dt: float,
) -> float:
    """
    Compute Arias Intensity of ground motion.

    I_a = (pi / 2g) * integral(a^2 dt)

    Parameters
    ----------
    acceleration : ndarray
        Ground acceleration time history in g.
    dt : float
        Time step in seconds.

    Returns
    -------
    float
        Arias Intensity in m/s.
    """
    acc_mps2 = acceleration * 9.81
    return np.pi / (2 * 9.81) * np.trapezoid(acc_mps2**2, dx=dt)


def compute_significant_duration(
    acceleration: NDArray[np.floating],
    dt: float,
    lower_bound: float = 0.05,
    upper_bound: float = 0.95,
) -> float:
    """
    Compute significant duration of ground motion.

    The duration between when Arias Intensity reaches lower_bound and
    upper_bound of the total.

    Parameters
    ----------
    acceleration : ndarray
        Ground acceleration time history in g.
    dt : float
        Time step in seconds.
    lower_bound : float
        Lower bound fraction (default 0.05 for 5%).
    upper_bound : float
        Upper bound fraction (default 0.95 for 95%).

    Returns
    -------
    float
        Significant duration in seconds.
    """
    acc_mps2 = acceleration * 9.81
    cumulative = np.cumsum(acc_mps2**2) * dt
    total = cumulative[-1]

    if total < 1e-10:
        return 0.0

    normalized = cumulative / total

    idx_lower = np.searchsorted(normalized, lower_bound)
    idx_upper = np.searchsorted(normalized, upper_bound)

    return (idx_upper - idx_lower) * dt


def compute_base_shear(
    M: NDArray[np.floating],
    absolute_acceleration: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Compute base shear time history.

    V_base = sum(m_i * a_i)

    Parameters
    ----------
    M : ndarray
        Mass matrix (diagonal).
    absolute_acceleration : ndarray
        Absolute acceleration time history (n_dof x n_steps) in m/s^2.

    Returns
    -------
    ndarray
        Base shear time history in N.
    """
    masses = np.diag(M)
    return np.sum(masses[:, np.newaxis] * absolute_acceleration, axis=0)


def compute_energy_balance(
    M: NDArray[np.floating],
    C: NDArray[np.floating],
    K: NDArray[np.floating],
    displacement: NDArray[np.floating],
    velocity: NDArray[np.floating],
    ground_acceleration: NDArray[np.floating],
    dt: float,
) -> dict:
    """
    Compute energy balance for verification.

    Parameters
    ----------
    M : ndarray
        Mass matrix.
    C : ndarray
        Damping matrix.
    K : ndarray
        Stiffness matrix.
    displacement : ndarray
        Displacement time history (n_dof x n_steps).
    velocity : ndarray
        Velocity time history (n_dof x n_steps).
    ground_acceleration : ndarray
        Ground acceleration (n_steps,) in g.
    dt : float
        Time step in seconds.

    Returns
    -------
    dict
        Dictionary with kinetic, strain, damping, and input energy time histories.
    """
    n_steps = displacement.shape[1]
    ag_mps2 = ground_acceleration * 9.81

    # Kinetic energy: 0.5 * v^T * M * v
    kinetic = np.array([
        0.5 * velocity[:, i] @ M @ velocity[:, i]
        for i in range(n_steps)
    ])

    # Strain energy: 0.5 * u^T * K * u
    strain = np.array([
        0.5 * displacement[:, i] @ K @ displacement[:, i]
        for i in range(n_steps)
    ])

    # Damping energy (cumulative): integral(v^T * C * v) dt
    damping_power = np.array([
        velocity[:, i] @ C @ velocity[:, i]
        for i in range(n_steps)
    ])
    damping = np.cumsum(damping_power) * dt

    # Input energy (cumulative): -integral(v^T * M * r * a_g) dt
    influence = np.ones(M.shape[0])
    input_power = np.array([
        -velocity[:, i] @ M @ influence * ag_mps2[i]
        for i in range(n_steps)
    ])
    input_energy = np.cumsum(input_power) * dt

    return {
        "kinetic": kinetic,
        "strain": strain,
        "damping": damping,
        "input": input_energy,
        "total": kinetic + strain + damping,
    }
