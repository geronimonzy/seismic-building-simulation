"""
Background callback manager for long-running tasks.

Uses DiskcacheManager for development (no Redis required).
Can be extended to use CeleryManager for production deployments.
"""

import os
from pathlib import Path

from dash import DiskcacheManager

# Cache directory for background tasks
CACHE_DIR = Path(os.environ.get("DASH_CACHE_DIR", "./.seismic_cache/dash"))


def get_background_callback_manager() -> DiskcacheManager:
    """
    Get the background callback manager.

    Uses DiskcacheManager which stores task state in a local directory.
    This is suitable for development and single-server deployments.

    For production with multiple workers, consider using CeleryManager:
        from dash import CeleryManager
        from celery import Celery
        celery_app = Celery(__name__, broker="redis://localhost:6379/0")
        return CeleryManager(celery_app)

    Returns
    -------
    DiskcacheManager
        Background callback manager instance.
    """
    import diskcache

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = diskcache.Cache(str(CACHE_DIR))
    return DiskcacheManager(cache)


def run_simulation_task(
    building_params: dict,
    ground_motion: dict,
    simulation_config: dict,
    set_progress: callable,
) -> dict:
    """
    Run the seismic simulation as a background task.

    This function is called by background callbacks and reports progress
    via set_progress().

    Parameters
    ----------
    building_params : dict
        Building parameters from BuildingParams schema.
    ground_motion : dict
        Ground motion data from GroundMotionState schema.
    simulation_config : dict
        Simulation config from SimulationConfig schema.
    set_progress : callable
        Function to report progress (current, total).

    Returns
    -------
    dict
        Simulation results as SimulationResults schema dict.
    """
    import numpy as np

    from seismic_twin import MDOFShearBuilding, compute_demand_metrics, newmark_beta
    from seismic_twin.dashboard.state.schemas import SimulationResults
    from seismic_twin.uncertainty import UncertaintyAnalysis

    try:
        set_progress((0, 100))

        # Create building model
        model = MDOFShearBuilding(
            masses=np.array(building_params["masses"]),
            stiffnesses=np.array(building_params["stiffnesses"]),
            damping_ratio=building_params["damping_ratio"],
            story_heights=np.array(building_params["story_heights"]),
        )

        set_progress((10, 100))

        # Get ground motion
        acc = np.array(ground_motion["acceleration"])
        dt = ground_motion["dt"]

        if len(acc) == 0:
            return SimulationResults(
                completed=False, error="No ground motion data available"
            ).model_dump()

        set_progress((20, 100))

        # Run Newmark-beta integration
        result = newmark_beta(
            M=model.M,
            C=model.C,
            K=model.K,
            ground_acceleration=acc,
            dt=dt,
        )

        set_progress((50, 100))

        # Compute demand metrics
        metrics = compute_demand_metrics(
            displacement=result.displacement,
            velocity=result.velocity,
            absolute_acceleration=result.absolute_acceleration,
            ground_acceleration=acc,
            story_heights=model.story_heights,
        )

        set_progress((60, 100))

        # Prepare results
        sim_results = SimulationResults(
            time=result.time.tolist(),
            displacement=[row.tolist() for row in result.displacement],
            velocity=[row.tolist() for row in result.velocity],
            acceleration=[row.tolist() for row in result.absolute_acceleration],
            max_displacement=metrics.max_displacement.tolist(),
            max_velocity=metrics.max_velocity.tolist(),
            max_acceleration=metrics.max_acceleration.tolist(),
            inter_story_drift_ratio=metrics.inter_story_drift_ratio.tolist(),
            peak_ground_acceleration=float(metrics.peak_ground_acceleration),
            natural_periods=model.natural_periods.tolist(),
            natural_frequencies=model.natural_frequencies.tolist(),
            completed=True,
        )

        # Monte Carlo analysis if enabled
        if simulation_config.get("enable_mc", False):
            set_progress((70, 100))

            ua = UncertaintyAnalysis(model, acc, dt)
            mc_result = ua.run_mc_ensemble(
                n_samples=simulation_config.get("mc_samples", 100),
                stiffness_cov=simulation_config.get("stiffness_cov", 0.05),
                damping_cov=simulation_config.get("damping_cov", 0.20),
                mass_cov=simulation_config.get("mass_cov", 0.0),
                seed=simulation_config.get("mc_seed", 42),
            )

            set_progress((90, 100))

            sim_results.mc_enabled = True
            sim_results.displacement_p5 = [
                row.tolist() for row in mc_result.displacement_bounds.percentile_5
            ]
            sim_results.displacement_p50 = [
                row.tolist() for row in mc_result.displacement_bounds.percentile_50
            ]
            sim_results.displacement_p95 = [
                row.tolist() for row in mc_result.displacement_bounds.percentile_95
            ]
            sim_results.max_drift_distribution = mc_result.max_drift_distribution.tolist()

        set_progress((100, 100))
        return sim_results.model_dump()

    except Exception as e:
        return SimulationResults(completed=False, error=str(e)).model_dump()
