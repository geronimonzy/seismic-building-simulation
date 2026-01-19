"""
Uncertainty Quantification via Monte Carlo Simulation

This module implements Monte Carlo methods for propagating parameter
uncertainty through structural response predictions.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from seismic_twin.analysis import compute_demand_metrics, newmark_beta
from seismic_twin.building import MDOFShearBuilding


@dataclass
class UncertaintyBounds:
    """Container for uncertainty quantification results."""

    percentile_5: NDArray[np.floating]
    percentile_50: NDArray[np.floating]
    percentile_95: NDArray[np.floating]
    mean: NDArray[np.floating]
    std: NDArray[np.floating]


@dataclass
class MonteCarloResult:
    """Container for Monte Carlo simulation results."""

    n_samples: int
    displacement_bounds: UncertaintyBounds
    velocity_bounds: UncertaintyBounds
    acceleration_bounds: UncertaintyBounds
    max_drift_distribution: NDArray[np.floating]
    parameter_samples: dict[str, NDArray[np.floating]]
    all_displacements: NDArray[np.floating]  # (n_samples, n_dof, n_steps)


class UncertaintyAnalysis:
    """
    Monte Carlo uncertainty analysis for structural response.

    This class performs uncertainty propagation by sampling from
    parameter distributions and running multiple simulations.

    Parameters
    ----------
    model : MDOFShearBuilding
        Base structural model (mean values).
    ground_acceleration : ndarray
        Ground acceleration time history (in g).
    dt : float
        Time step in seconds.

    Attributes
    ----------
    base_model : MDOFShearBuilding
        Base model with nominal parameters.
    results : MonteCarloResult or None
        Results from the most recent Monte Carlo run.
    """

    def __init__(
        self,
        model: MDOFShearBuilding,
        ground_acceleration: NDArray[np.floating],
        dt: float,
    ) -> None:
        self.base_model = model.copy()
        self.ground_acceleration = ground_acceleration
        self.dt = dt
        self.results: Optional[MonteCarloResult] = None

    def sample_parameters(
        self,
        n_samples: int,
        stiffness_cov: float = 0.05,
        damping_cov: float = 0.20,
        mass_cov: float = 0.0,
        seed: Optional[int] = None,
    ) -> dict[str, NDArray[np.floating]]:
        """
        Generate parameter samples from distributions.

        Parameters are sampled from lognormal distributions to ensure
        positive values.

        Parameters
        ----------
        n_samples : int
            Number of Monte Carlo samples.
        stiffness_cov : float
            Coefficient of variation for stiffness (default 5%).
        damping_cov : float
            Coefficient of variation for damping ratio (default 20%).
        mass_cov : float
            Coefficient of variation for mass (default 0%, deterministic).
        seed : int, optional
            Random seed for reproducibility.

        Returns
        -------
        dict
            Dictionary with arrays of sampled parameters.
        """
        if seed is not None:
            np.random.seed(seed)

        n_dof = self.base_model.n_dof

        # Sample stiffness multipliers (lognormal)
        if stiffness_cov > 0:
            sigma_k = np.sqrt(np.log(1 + stiffness_cov**2))
            mu_k = -0.5 * sigma_k**2
            stiffness_factors = np.exp(np.random.normal(mu_k, sigma_k, (n_samples, n_dof)))
        else:
            stiffness_factors = np.ones((n_samples, n_dof))

        # Sample damping ratios (lognormal)
        if damping_cov > 0:
            sigma_xi = np.sqrt(np.log(1 + damping_cov**2))
            mu_xi = np.log(self.base_model.damping_ratio) - 0.5 * sigma_xi**2
            damping_ratios = np.exp(np.random.normal(mu_xi, sigma_xi, n_samples))
        else:
            damping_ratios = np.full(n_samples, self.base_model.damping_ratio)

        # Sample mass multipliers (lognormal)
        if mass_cov > 0:
            sigma_m = np.sqrt(np.log(1 + mass_cov**2))
            mu_m = -0.5 * sigma_m**2
            mass_factors = np.exp(np.random.normal(mu_m, sigma_m, (n_samples, n_dof)))
        else:
            mass_factors = np.ones((n_samples, n_dof))

        return {
            "stiffness_factors": stiffness_factors,
            "damping_ratios": damping_ratios,
            "mass_factors": mass_factors,
        }

    def run_mc_ensemble(
        self,
        n_samples: int = 100,
        stiffness_cov: float = 0.05,
        damping_cov: float = 0.20,
        mass_cov: float = 0.0,
        seed: Optional[int] = None,
        verbose: bool = False,
    ) -> MonteCarloResult:
        """
        Run Monte Carlo ensemble simulations.

        Parameters
        ----------
        n_samples : int
            Number of Monte Carlo samples.
        stiffness_cov : float
            Coefficient of variation for stiffness.
        damping_cov : float
            Coefficient of variation for damping.
        mass_cov : float
            Coefficient of variation for mass.
        seed : int, optional
            Random seed for reproducibility.
        verbose : bool
            If True, print progress.

        Returns
        -------
        MonteCarloResult
            Container with ensemble results.
        """
        # Sample parameters
        params = self.sample_parameters(
            n_samples=n_samples,
            stiffness_cov=stiffness_cov,
            damping_cov=damping_cov,
            mass_cov=mass_cov,
            seed=seed,
        )

        n_dof = self.base_model.n_dof
        n_steps = len(self.ground_acceleration)

        # Storage for results
        all_displacements = np.zeros((n_samples, n_dof, n_steps))
        all_velocities = np.zeros((n_samples, n_dof, n_steps))
        all_accelerations = np.zeros((n_samples, n_dof, n_steps))
        max_drifts = np.zeros(n_samples)

        # Run simulations
        for i in range(n_samples):
            if verbose and (i + 1) % 10 == 0:
                print(f"  MC sample {i + 1}/{n_samples}")

            # Create model with sampled parameters
            model = self._create_sampled_model(
                stiffness_factors=params["stiffness_factors"][i],
                damping_ratio=params["damping_ratios"][i],
                mass_factors=params["mass_factors"][i],
            )

            # Run simulation
            result = newmark_beta(
                M=model.M,
                C=model.C,
                K=model.K,
                ground_acceleration=self.ground_acceleration,
                dt=self.dt,
            )

            # Store results
            all_displacements[i] = result.displacement
            all_velocities[i] = result.velocity
            all_accelerations[i] = result.absolute_acceleration

            # Compute max drift
            metrics = compute_demand_metrics(
                displacement=result.displacement,
                velocity=result.velocity,
                absolute_acceleration=result.absolute_acceleration,
                ground_acceleration=self.ground_acceleration,
                story_heights=model.story_heights,
            )
            max_drifts[i] = np.max(metrics.inter_story_drift_ratio)

        # Compute bounds
        displacement_bounds = self._compute_bounds(all_displacements)
        velocity_bounds = self._compute_bounds(all_velocities)
        acceleration_bounds = self._compute_bounds(all_accelerations)

        self.results = MonteCarloResult(
            n_samples=n_samples,
            displacement_bounds=displacement_bounds,
            velocity_bounds=velocity_bounds,
            acceleration_bounds=acceleration_bounds,
            max_drift_distribution=max_drifts,
            parameter_samples=params,
            all_displacements=all_displacements,
        )

        return self.results

    def _create_sampled_model(
        self,
        stiffness_factors: NDArray[np.floating],
        damping_ratio: float,
        mass_factors: NDArray[np.floating],
    ) -> MDOFShearBuilding:
        """Create a model instance with sampled parameters."""
        sampled_stiffnesses = self.base_model.stiffnesses * stiffness_factors
        sampled_masses = self.base_model.masses * mass_factors

        return MDOFShearBuilding(
            masses=sampled_masses,
            stiffnesses=sampled_stiffnesses,
            damping_ratio=damping_ratio,
            story_heights=self.base_model.story_heights,
        )

    def _compute_bounds(self, data: NDArray[np.floating]) -> UncertaintyBounds:
        """Compute percentile bounds from ensemble data."""
        # data shape: (n_samples, n_dof, n_steps)
        return UncertaintyBounds(
            percentile_5=np.percentile(data, 5, axis=0),
            percentile_50=np.percentile(data, 50, axis=0),
            percentile_95=np.percentile(data, 95, axis=0),
            mean=np.mean(data, axis=0),
            std=np.std(data, axis=0),
        )

    def compute_uncertainty_bounds(
        self, percentiles: tuple[float, ...] = (5, 50, 95)
    ) -> dict[str, NDArray[np.floating]]:
        """
        Compute custom percentile bounds from results.

        Parameters
        ----------
        percentiles : tuple
            Percentiles to compute.

        Returns
        -------
        dict
            Dictionary mapping percentile to displacement array.
        """
        if self.results is None:
            raise ValueError("Run run_mc_ensemble() first")

        return {
            f"p{p}": np.percentile(self.results.all_displacements, p, axis=0) for p in percentiles
        }

    def get_drift_statistics(self) -> dict[str, float]:
        """
        Get statistics of maximum inter-story drift distribution.

        Returns
        -------
        dict
            Dictionary with mean, std, percentiles of max drift.
        """
        if self.results is None:
            raise ValueError("Run run_mc_ensemble() first")

        drifts = self.results.max_drift_distribution

        return {
            "mean": float(np.mean(drifts)),
            "std": float(np.std(drifts)),
            "p5": float(np.percentile(drifts, 5)),
            "p50": float(np.percentile(drifts, 50)),
            "p95": float(np.percentile(drifts, 95)),
            "max": float(np.max(drifts)),
            "min": float(np.min(drifts)),
        }

    def get_probability_of_exceedance(
        self, threshold: float, response_type: str = "drift"
    ) -> float:
        """
        Compute probability of exceeding a threshold.

        Parameters
        ----------
        threshold : float
            Threshold value.
        response_type : str
            Type of response ('drift', 'displacement', 'acceleration').

        Returns
        -------
        float
            Probability of exceedance (0 to 1).
        """
        if self.results is None:
            raise ValueError("Run run_mc_ensemble() first")

        if response_type == "drift":
            values = self.results.max_drift_distribution
        elif response_type == "displacement":
            values = np.max(np.abs(self.results.all_displacements), axis=(1, 2))
        elif response_type == "acceleration":
            values = np.max(np.abs(self.results.acceleration_bounds.mean), axis=(0, 1))
            # Use individual samples
            values = np.max(np.abs(np.percentile(self.results.all_displacements, 50, axis=0)))
        else:
            raise ValueError(f"Unknown response_type: {response_type}")

        return float(np.mean(values > threshold))
