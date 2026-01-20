"""Callbacks for the simulation page."""

import numpy as np
from dash import Dash, Input, Output, State


def _get_check_icon_and_color(is_ok: bool) -> tuple[str, str | None]:
    """Return icon class and color based on check status."""
    if is_ok:
        return "bi bi-check-circle-fill text-success", "success"
    return "bi bi-circle text-muted", None


def register_simulation_callbacks(app: Dash) -> None:
    """Register simulation page callbacks."""

    @app.callback(
        Output("check-building-icon", "className"),
        Output("check-building", "color"),
        Output("check-gm-icon", "className"),
        Output("check-gm", "color"),
        Input("store-building-params", "data"),
        Input("store-ground-motion", "data"),
    )
    def update_preflight_checks(building_params, ground_motion):
        """Update preflight check indicators."""
        building_ok = (
            building_params is not None
            and building_params.get("n_stories", 0) > 0
            and len(building_params.get("masses", [])) > 0
        )
        gm_ok = (
            ground_motion is not None
            and len(ground_motion.get("acceleration", [])) > 0
        )

        building_icon, building_color = _get_check_icon_and_color(building_ok)
        gm_icon, gm_color = _get_check_icon_and_color(gm_ok)

        return building_icon, building_color, gm_icon, gm_color

    @app.callback(
        Output("store-simulation-results", "data"),
        Output("progress-simulation", "value"),
        Output("alert-simulation-status", "children"),
        Output("alert-simulation-status", "color"),
        Output("simulation-summary", "style"),
        Output("summary-max-drift", "children"),
        Output("summary-max-disp", "children"),
        Output("summary-max-acc", "children"),
        Output("sidebar-sim-info", "children"),
        Input("btn-run-simulation", "n_clicks"),
        State("store-building-params", "data"),
        State("store-ground-motion", "data"),
        State("check-enable-mc", "value"),
        State("input-mc-samples", "value"),
        State("slider-stiffness-cov", "value"),
        State("slider-damping-cov", "value"),
        State("slider-mass-cov", "value"),
        State("input-mc-seed", "value"),
        State("store-simulation-results", "data"),
        prevent_initial_call=True,
    )
    def run_simulation(
        n_clicks,
        building_params,
        ground_motion,
        enable_mc,
        mc_samples,
        stiffness_cov,
        damping_cov,
        mass_cov,
        mc_seed,
        current_results,
    ):
        """Run the seismic simulation."""
        from seismic_twin import MDOFShearBuilding, compute_demand_metrics, newmark_beta
        from seismic_twin.dashboard.state.schemas import SimulationResults
        from seismic_twin.uncertainty import UncertaintyAnalysis

        def _error_response(error_msg: str):
            """Return error response tuple."""
            return (
                current_results or SimulationResults().model_dump(),
                0,
                f"Error: {error_msg}",
                "danger",
                {"display": "none"},
                "-",
                "-",
                "-",
                "Simulation: Error",
            )

        # Validate inputs
        if not building_params or len(building_params.get("masses", [])) == 0:
            return _error_response("No building model configured")

        if not ground_motion or len(ground_motion.get("acceleration", [])) == 0:
            return _error_response("No ground motion loaded")

        try:
            # Create building model
            model = MDOFShearBuilding(
                masses=np.array(building_params["masses"]),
                stiffnesses=np.array(building_params["stiffnesses"]),
                damping_ratio=building_params["damping_ratio"],
                story_heights=np.array(building_params["story_heights"]),
            )

            # Get ground motion
            acc = np.array(ground_motion["acceleration"])
            dt = ground_motion["dt"]

            # Run Newmark-beta integration
            result = newmark_beta(
                M=model.M,
                C=model.C,
                K=model.K,
                ground_acceleration=acc,
                dt=dt,
            )

            # Compute demand metrics
            metrics = compute_demand_metrics(
                displacement=result.displacement,
                velocity=result.velocity,
                absolute_acceleration=result.absolute_acceleration,
                ground_acceleration=acc,
                story_heights=model.story_heights,
            )

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
            mc_enabled = enable_mc and "enabled" in enable_mc
            if mc_enabled:
                ua = UncertaintyAnalysis(model, acc, dt)
                mc_result = ua.run_mc_ensemble(
                    n_samples=mc_samples or 100,
                    stiffness_cov=stiffness_cov or 0.05,
                    damping_cov=damping_cov or 0.20,
                    mass_cov=mass_cov or 0.0,
                    seed=mc_seed or 42,
                )

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

            # Format summary values
            max_drift = max(sim_results.inter_story_drift_ratio)
            max_disp = sim_results.max_displacement[-1]  # Roof displacement
            max_acc = max(sim_results.max_acceleration)

            return (
                sim_results.model_dump(),
                100,
                "Simulation completed successfully!",
                "success",
                {"display": "block"},
                f"{max_drift:.4f}",
                f"{max_disp:.4f}",
                f"{max_acc:.3f}",
                f"Simulation: Complete (max drift={max_drift:.3f})",
            )

        except Exception as e:
            return _error_response(str(e))

    @app.callback(
        Output("store-simulation-config", "data"),
        Input("check-enable-mc", "value"),
        Input("input-mc-samples", "value"),
        Input("slider-stiffness-cov", "value"),
        Input("slider-damping-cov", "value"),
        Input("slider-mass-cov", "value"),
        Input("input-mc-seed", "value"),
    )
    def update_simulation_config(
        enable_mc,
        mc_samples,
        stiffness_cov,
        damping_cov,
        mass_cov,
        mc_seed,
    ):
        """Update simulation configuration in store."""
        from seismic_twin.dashboard.state.schemas import SimulationConfig

        config = SimulationConfig(
            enable_mc=enable_mc and "enabled" in enable_mc,
            mc_samples=mc_samples or 100,
            stiffness_cov=stiffness_cov or 0.05,
            damping_cov=damping_cov or 0.20,
            mass_cov=mass_cov or 0.0,
            mc_seed=mc_seed,
        )
        return config.model_dump()
