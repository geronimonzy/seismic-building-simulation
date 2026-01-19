"""
Time Integration Methods for Structural Dynamics

This module implements the Newmark-beta method for solving the equations
of motion of MDOF systems subjected to ground motion excitation.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from scipy import linalg


@dataclass
class IntegrationResult:
    """Container for time integration results."""

    time: NDArray[np.floating]
    displacement: NDArray[np.floating]  # Relative to ground
    velocity: NDArray[np.floating]  # Relative to ground
    acceleration: NDArray[np.floating]  # Relative to ground
    absolute_acceleration: NDArray[np.floating]  # Absolute (total)

    @property
    def n_dof(self) -> int:
        """Number of degrees of freedom."""
        return self.displacement.shape[0]

    @property
    def n_steps(self) -> int:
        """Number of time steps."""
        return self.displacement.shape[1]


def newmark_beta(
    M: NDArray[np.floating],
    C: NDArray[np.floating],
    K: NDArray[np.floating],
    ground_acceleration: NDArray[np.floating],
    dt: float,
    beta: float = 0.25,
    gamma: float = 0.5,
    influence_vector: Optional[NDArray[np.floating]] = None,
) -> IntegrationResult:
    """
    Solve MDOF equations of motion using Newmark-beta time integration.

    The equation of motion is:
        M * u'' + C * u' + K * u = -M * r * a_g(t)

    where u is the relative displacement vector, a_g is ground acceleration,
    and r is the influence vector.

    Parameters
    ----------
    M : ndarray
        Mass matrix (n_dof x n_dof).
    C : ndarray
        Damping matrix (n_dof x n_dof).
    K : ndarray
        Stiffness matrix (n_dof x n_dof).
    ground_acceleration : ndarray
        Ground acceleration time history (in g).
    dt : float
        Time step in seconds.
    beta : float
        Newmark beta parameter. Default 0.25 (average acceleration).
    gamma : float
        Newmark gamma parameter. Default 0.5 (no numerical damping).
    influence_vector : ndarray, optional
        Influence vector defining how ground motion affects each DOF.
        Defaults to ones (uniform ground motion).

    Returns
    -------
    IntegrationResult
        Container with time, displacement, velocity, and acceleration arrays.

    Notes
    -----
    Common parameter choices:
    - beta=0.25, gamma=0.5: Average acceleration (unconditionally stable)
    - beta=1/6, gamma=0.5: Linear acceleration (conditionally stable)
    - beta=0.25, gamma>0.5: Numerical damping for high frequencies
    """
    n_dof = M.shape[0]
    n_steps = len(ground_acceleration)

    if influence_vector is None:
        influence_vector = np.ones(n_dof)

    # Convert ground acceleration to m/s^2
    ag_mps2 = ground_acceleration * 9.81

    # Initialize arrays
    u = np.zeros((n_dof, n_steps))  # Relative displacement
    v = np.zeros((n_dof, n_steps))  # Relative velocity
    a = np.zeros((n_dof, n_steps))  # Relative acceleration

    # Effective load vector at t=0
    p0 = -M @ influence_vector * ag_mps2[0]

    # Initial acceleration (assuming zero initial conditions)
    # M * a0 = p0 - C * v0 - K * u0
    a[:, 0] = linalg.solve(M, p0)

    # Newmark integration constants
    a1 = 1.0 / (beta * dt**2)
    a2 = 1.0 / (beta * dt)
    a3 = 1.0 / (2.0 * beta) - 1.0
    a4 = gamma / (beta * dt)
    a5 = gamma / beta - 1.0
    a6 = dt * (gamma / (2.0 * beta) - 1.0)

    # Effective stiffness matrix
    K_eff = K + a1 * M + a4 * C

    # LU factorization for efficiency
    K_eff_lu = linalg.lu_factor(K_eff)

    # Time stepping
    for i in range(n_steps - 1):
        # Effective load at t_{i+1}
        p_eff = -M @ influence_vector * ag_mps2[i + 1]

        # Add contributions from current state
        p_eff += M @ (a1 * u[:, i] + a2 * v[:, i] + a3 * a[:, i])
        p_eff += C @ (a4 * u[:, i] + a5 * v[:, i] + a6 * a[:, i])

        # Solve for displacement at t_{i+1}
        u[:, i + 1] = linalg.lu_solve(K_eff_lu, p_eff)

        # Update velocity and acceleration
        a[:, i + 1] = a1 * (u[:, i + 1] - u[:, i]) - a2 * v[:, i] - a3 * a[:, i]
        v[:, i + 1] = v[:, i] + dt * ((1 - gamma) * a[:, i] + gamma * a[:, i + 1])

    # Time vector
    time = np.arange(n_steps) * dt

    # Absolute acceleration = relative acceleration + ground acceleration
    abs_acc = a + np.outer(influence_vector, ag_mps2)

    return IntegrationResult(
        time=time,
        displacement=u,
        velocity=v,
        acceleration=a,
        absolute_acceleration=abs_acc,
    )


def modal_superposition(
    M: NDArray[np.floating],
    K: NDArray[np.floating],
    damping_ratio: float,
    ground_acceleration: NDArray[np.floating],
    dt: float,
    n_modes: Optional[int] = None,
) -> IntegrationResult:
    """
    Solve MDOF equations using modal superposition.

    This method transforms the coupled equations into uncoupled SDOF
    oscillators in modal coordinates.

    Parameters
    ----------
    M : ndarray
        Mass matrix.
    K : ndarray
        Stiffness matrix.
    damping_ratio : float
        Modal damping ratio (same for all modes).
    ground_acceleration : ndarray
        Ground acceleration time history (in g).
    dt : float
        Time step in seconds.
    n_modes : int, optional
        Number of modes to include. Defaults to all modes.

    Returns
    -------
    IntegrationResult
        Container with time, displacement, velocity, and acceleration arrays.
    """
    n_dof = M.shape[0]
    n_steps = len(ground_acceleration)

    if n_modes is None:
        n_modes = n_dof

    # Eigenvalue analysis
    eigenvalues, mode_shapes = linalg.eigh(K, M)
    omega = np.sqrt(np.maximum(eigenvalues, 0.0))

    # Modal participation factors
    influence = np.ones(n_dof)
    gamma = np.array([mode_shapes[:, i] @ M @ influence for i in range(n_dof)])

    # Convert ground acceleration to m/s^2
    ag_mps2 = ground_acceleration * 9.81

    # Initialize modal responses
    q = np.zeros((n_modes, n_steps))  # Modal displacement
    qd = np.zeros((n_modes, n_steps))  # Modal velocity

    # Integrate each mode using exact SDOF solution
    for m in range(n_modes):
        if omega[m] < 1e-10:
            continue

        omega_m = omega[m]
        xi = damping_ratio
        omega_d = omega_m * np.sqrt(1 - xi**2)

        # Exact integration for SDOF under piece-wise linear excitation
        exp_term = np.exp(-xi * omega_m * dt)
        sin_term = np.sin(omega_d * dt)
        cos_term = np.cos(omega_d * dt)

        A11 = exp_term * (cos_term + xi * omega_m / omega_d * sin_term)
        A12 = exp_term * sin_term / omega_d
        A21 = -(omega_m**2) * exp_term * sin_term / omega_d
        A22 = exp_term * (cos_term - xi * omega_m / omega_d * sin_term)

        # Load coefficients for piece-wise linear excitation
        B1 = (2 * xi / (omega_m * dt) + A11 - 1) / omega_m**2
        B2 = (1 - 2 * xi / (omega_m * dt) - A11 + A12 * omega_m) / omega_m**2

        for i in range(n_steps - 1):
            p_m = -gamma[m] * ag_mps2[i]
            p_m1 = -gamma[m] * ag_mps2[i + 1]

            q[m, i + 1] = A11 * q[m, i] + A12 * qd[m, i] + B1 * p_m + B2 * p_m1
            qd[m, i + 1] = A21 * q[m, i] + A22 * qd[m, i]

    # Transform back to physical coordinates
    u = mode_shapes[:, :n_modes] @ q
    v = mode_shapes[:, :n_modes] @ qd

    # Compute acceleration from equation of motion
    a = np.zeros((n_dof, n_steps))
    for i in range(n_steps):
        a[:, i] = -(omega[:n_modes] ** 2) @ (
            mode_shapes[:, :n_modes].T * q[:, i][:, np.newaxis]
        ).sum(axis=0)
        a[:, i] = (
            linalg.solve(M, -K @ u[:, i] - M @ np.ones(n_dof) * ag_mps2[i])
            + np.ones(n_dof) * ag_mps2[i]
        )

    # Simpler: a = -2*xi*omega*v - omega^2*u - influence*ag
    a = np.zeros((n_dof, n_steps))
    for i in range(n_steps):
        a[:, i] = linalg.solve(M, -K @ u[:, i]) - np.ones(n_dof) * ag_mps2[i]

    time = np.arange(n_steps) * dt
    abs_acc = a + np.outer(np.ones(n_dof), ag_mps2)

    return IntegrationResult(
        time=time,
        displacement=u,
        velocity=v,
        acceleration=a,
        absolute_acceleration=abs_acc,
    )
