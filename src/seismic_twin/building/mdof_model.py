"""
Multi-Degree-of-Freedom (MDOF) Shear Building Model

This module implements a shear building model for seismic analysis,
where each floor is treated as a lumped mass connected by inter-story
stiffness elements.
"""

from typing import Optional

import numpy as np
from numpy.typing import NDArray
from scipy import linalg


class MDOFShearBuilding:
    """
    Multi-degree-of-freedom shear building model for seismic analysis.

    The model represents a building as a series of lumped masses (floors)
    connected by lateral stiffness elements. Each floor has one horizontal
    degree of freedom.

    Parameters
    ----------
    masses : array_like
        Floor masses in kg, from bottom to top.
    stiffnesses : array_like
        Inter-story stiffnesses in N/m, from bottom to top.
    damping_ratio : float
        Modal damping ratio (typically 0.02-0.05 for buildings).
    story_heights : array_like, optional
        Story heights in meters. Defaults to 3.5m per story.

    Attributes
    ----------
    n_dof : int
        Number of degrees of freedom (floors).
    M : ndarray
        Mass matrix (diagonal).
    K : ndarray
        Stiffness matrix (tridiagonal).
    C : ndarray
        Damping matrix (Rayleigh damping).
    natural_periods : ndarray
        Natural periods of vibration in seconds.
    natural_frequencies : ndarray
        Natural frequencies in rad/s.
    mode_shapes : ndarray
        Mode shape matrix (columns are mode shapes).
    """

    def __init__(
        self,
        masses: NDArray[np.floating],
        stiffnesses: NDArray[np.floating],
        damping_ratio: float = 0.05,
        story_heights: Optional[NDArray[np.floating]] = None,
    ) -> None:
        self.masses = np.asarray(masses, dtype=np.float64)
        self.stiffnesses = np.asarray(stiffnesses, dtype=np.float64)
        self.damping_ratio = damping_ratio
        self.n_dof = len(self.masses)

        if len(self.stiffnesses) != self.n_dof:
            raise ValueError(
                f"Number of stiffnesses ({len(self.stiffnesses)}) must equal "
                f"number of masses ({self.n_dof})"
            )

        if story_heights is None:
            self.story_heights = np.full(self.n_dof, 3.5)
        else:
            self.story_heights = np.asarray(story_heights, dtype=np.float64)

        # Assemble system matrices
        self.M = self._assemble_mass_matrix()
        self.K = self._assemble_stiffness_matrix()

        # Compute modal properties
        self._compute_modal_properties()

        # Assemble damping matrix using Rayleigh damping
        self.C = self._assemble_damping_matrix()

    def _assemble_mass_matrix(self) -> NDArray[np.floating]:
        """Assemble the diagonal mass matrix."""
        return np.diag(self.masses)

    def _assemble_stiffness_matrix(self) -> NDArray[np.floating]:
        """
        Assemble the tridiagonal stiffness matrix.

        For a shear building, the stiffness matrix has the form:
        K[i,i] = k[i] + k[i+1]  (diagonal)
        K[i,i+1] = K[i+1,i] = -k[i+1]  (off-diagonal)
        """
        K = np.zeros((self.n_dof, self.n_dof), dtype=np.float64)

        for i in range(self.n_dof):
            # Diagonal term: sum of stiffnesses connecting to this floor
            K[i, i] = self.stiffnesses[i]
            if i < self.n_dof - 1:
                K[i, i] += self.stiffnesses[i + 1]

            # Off-diagonal terms
            if i < self.n_dof - 1:
                K[i, i + 1] = -self.stiffnesses[i + 1]
                K[i + 1, i] = -self.stiffnesses[i + 1]

        return K

    def _compute_modal_properties(self) -> None:
        """Compute natural frequencies and mode shapes via eigenvalue analysis."""
        # Solve generalized eigenvalue problem: K*phi = omega^2 * M * phi
        eigenvalues, eigenvectors = linalg.eigh(self.K, self.M)

        # Eigenvalues are omega^2, ensure non-negative
        eigenvalues = np.maximum(eigenvalues, 0.0)

        # Natural frequencies in rad/s
        self.natural_frequencies = np.sqrt(eigenvalues)

        # Natural periods in seconds
        self.natural_periods = np.zeros_like(self.natural_frequencies)
        nonzero_mask = self.natural_frequencies > 1e-10
        self.natural_periods[nonzero_mask] = 2.0 * np.pi / self.natural_frequencies[nonzero_mask]

        # Mode shapes (mass-normalized by scipy.linalg.eigh)
        self.mode_shapes = eigenvectors

    def _assemble_damping_matrix(self) -> NDArray[np.floating]:
        """
        Assemble Rayleigh damping matrix.

        Rayleigh damping: C = alpha * M + beta * K
        where alpha and beta are chosen to achieve the target damping ratio
        at the first and last mode frequencies.
        """
        if self.n_dof == 1:
            # Single DOF: classical damping
            omega = self.natural_frequencies[0]
            c = 2.0 * self.damping_ratio * omega * self.masses[0]
            return np.array([[c]])

        # Use first and last mode frequencies for Rayleigh damping
        omega_1 = self.natural_frequencies[0]
        omega_n = self.natural_frequencies[-1]

        if omega_1 < 1e-10 or omega_n < 1e-10:
            # Fallback to mass-proportional damping
            alpha = 2.0 * self.damping_ratio * self.natural_frequencies[0]
            return alpha * self.M

        # Solve for alpha and beta:
        # xi = alpha/(2*omega) + beta*omega/2
        # At omega_1: xi_1 = alpha/(2*omega_1) + beta*omega_1/2
        # At omega_n: xi_n = alpha/(2*omega_n) + beta*omega_n/2
        A = np.array(
            [
                [1.0 / (2.0 * omega_1), omega_1 / 2.0],
                [1.0 / (2.0 * omega_n), omega_n / 2.0],
            ]
        )
        b = np.array([self.damping_ratio, self.damping_ratio])
        alpha, beta = np.linalg.solve(A, b)

        return alpha * self.M + beta * self.K

    def get_modal_participation_factors(
        self, influence_vector: Optional[NDArray[np.floating]] = None
    ) -> NDArray[np.floating]:
        """
        Compute modal participation factors for ground motion excitation.

        Parameters
        ----------
        influence_vector : ndarray, optional
            Influence vector defining how ground motion affects each DOF.
            Defaults to unit vector (uniform ground motion).

        Returns
        -------
        ndarray
            Modal participation factors for each mode.
        """
        if influence_vector is None:
            influence_vector = np.ones(self.n_dof)

        # Participation factor: gamma_n = phi_n^T * M * r / (phi_n^T * M * phi_n)
        # For mass-normalized modes, denominator = 1
        gamma = np.zeros(self.n_dof)
        for i in range(self.n_dof):
            phi = self.mode_shapes[:, i]
            gamma[i] = phi @ self.M @ influence_vector

        return gamma

    def update_stiffness(self, scale_factor: float) -> None:
        """
        Update stiffnesses by a scale factor and recompute matrices.

        Parameters
        ----------
        scale_factor : float
            Multiplicative factor for all stiffnesses.
        """
        self.stiffnesses = self.stiffnesses * scale_factor
        self.K = self._assemble_stiffness_matrix()
        self._compute_modal_properties()
        self.C = self._assemble_damping_matrix()

    def update_damping(self, new_damping_ratio: float) -> None:
        """
        Update damping ratio and recompute damping matrix.

        Parameters
        ----------
        new_damping_ratio : float
            New modal damping ratio.
        """
        self.damping_ratio = new_damping_ratio
        self.C = self._assemble_damping_matrix()

    def set_stiffnesses(self, stiffnesses: NDArray[np.floating]) -> None:
        """
        Set new stiffness values and recompute matrices.

        Parameters
        ----------
        stiffnesses : array_like
            New inter-story stiffnesses in N/m.
        """
        self.stiffnesses = np.asarray(stiffnesses, dtype=np.float64)
        self.K = self._assemble_stiffness_matrix()
        self._compute_modal_properties()
        self.C = self._assemble_damping_matrix()

    def copy(self) -> "MDOFShearBuilding":
        """Create a deep copy of the building model."""
        return MDOFShearBuilding(
            masses=self.masses.copy(),
            stiffnesses=self.stiffnesses.copy(),
            damping_ratio=self.damping_ratio,
            story_heights=self.story_heights.copy(),
        )

    def __repr__(self) -> str:
        return (
            f"MDOFShearBuilding(n_dof={self.n_dof}, "
            f"T1={self.natural_periods[0]:.3f}s, "
            f"damping={self.damping_ratio:.1%})"
        )
