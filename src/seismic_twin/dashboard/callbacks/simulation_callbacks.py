"""Callbacks for the simulation page."""

from __future__ import annotations

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
        Output("card-vertical-analysis", "style"),
        Input("store-building-params", "data"),
        Input("store-ground-motion", "data"),
    )
    def update_preflight_checks(building_params, ground_motion):
        """Update preflight check indicators and vertical analysis visibility."""
        building_ok = (
            building_params is not None
            and building_params.get("n_stories", 0) > 0
            and len(building_params.get("masses", [])) > 0
        )
        gm_ok = ground_motion is not None and len(ground_motion.get("acceleration", [])) > 0
        has_vertical = ground_motion is not None and ground_motion.get("has_vertical", False)

        building_icon, building_color = _get_check_icon_and_color(building_ok)
        gm_icon, gm_color = _get_check_icon_and_color(gm_ok)

        # Show vertical analysis card only if vertical ground motion exists
        vertical_style = {"display": "block"} if has_vertical else {"display": "none"}

        return building_icon, building_color, gm_icon, gm_color, vertical_style

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
        State("slider-vertical-stiffness", "value"),
        State("store-simulation-results", "data"),
        background=True,
        progress=[Output("progress-simulation", "value")],
        progress_default=[0],
        running=[
            (Output("btn-run-simulation", "disabled"), True, False),
            (Output("alert-simulation-status", "children"), "Running simulation...", ""),
            (Output("alert-simulation-status", "color"), "info", "success"),
        ],
        prevent_initial_call=True,
    )
    def run_simulation(
        set_progress,
        n_clicks,
        building_params,
        ground_motion,
        enable_mc,
        mc_samples,
        stiffness_cov,
        damping_cov,
        mass_cov,
        mc_seed,
        vertical_stiffness_factor,
        current_results,
    ):
        """Run the seismic simulation with optional two-axis analysis."""
        from seismic_twin import MDOFShearBuilding, compute_demand_metrics, newmark_beta
        from seismic_twin.analysis import compute_energy_balance
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

        # Default vertical stiffness factor
        vertical_stiffness_factor = vertical_stiffness_factor or 50.0

        try:
            set_progress([5])

            # Create building model
            model = MDOFShearBuilding(
                masses=np.array(building_params["masses"]),
                stiffnesses=np.array(building_params["stiffnesses"]),
                damping_ratio=building_params["damping_ratio"],
                story_heights=np.array(building_params["story_heights"]),
            )

            set_progress([10])

            # Get horizontal ground motion
            acc_h = np.array(ground_motion["acceleration"])
            dt = ground_motion["dt"]
            has_vertical = ground_motion.get("has_vertical", False)

            set_progress([15])

            # ===== HORIZONTAL ANALYSIS =====
            result_h = newmark_beta(
                M=model.M,
                C=model.C,
                K=model.K,
                ground_acceleration=acc_h,
                dt=dt,
            )

            set_progress([30])

            metrics_h = compute_demand_metrics(
                displacement=result_h.displacement,
                velocity=result_h.velocity,
                absolute_acceleration=result_h.absolute_acceleration,
                ground_acceleration=acc_h,
                story_heights=model.story_heights,
            )

            set_progress([35])

            energy_h = compute_energy_balance(
                M=model.M,
                C=model.C,
                K=model.K,
                displacement=result_h.displacement,
                velocity=result_h.velocity,
                ground_acceleration=acc_h,
                dt=dt,
            )

            set_progress([40])

            # Prepare base results (horizontal)
            sim_results = SimulationResults(
                time=result_h.time.tolist(),
                displacement=[row.tolist() for row in result_h.displacement],
                velocity=[row.tolist() for row in result_h.velocity],
                acceleration=[row.tolist() for row in result_h.absolute_acceleration],
                max_displacement=metrics_h.max_displacement.tolist(),
                max_velocity=metrics_h.max_velocity.tolist(),
                max_acceleration=metrics_h.max_acceleration.tolist(),
                inter_story_drift_ratio=metrics_h.inter_story_drift_ratio.tolist(),
                peak_ground_acceleration=float(metrics_h.peak_ground_acceleration),
                natural_periods=model.natural_periods.tolist(),
                natural_frequencies=model.natural_frequencies.tolist(),
                vertical_stiffness_factor=vertical_stiffness_factor,
                completed=True,
            )

            # Initialize energy with horizontal values
            energy_kinetic = energy_h["kinetic"]
            energy_strain = energy_h["strain"]
            energy_damping = energy_h["damping"]
            energy_input = energy_h["input"]

            set_progress([45])

            # ===== VERTICAL ANALYSIS (if vertical ground motion exists) =====
            if has_vertical and len(ground_motion.get("acceleration_vertical", [])) > 0:
                acc_v = np.array(ground_motion["acceleration_vertical"])

                # Create vertical stiffness matrix (axial stiffness = lateral * factor)
                K_vertical = model.K * vertical_stiffness_factor

                # Recompute damping for vertical (using same damping ratio but new K)
                # C = alpha*M + beta*K where we maintain the same damping ratio
                # For simplicity, scale C proportionally
                C_vertical = model.C * np.sqrt(vertical_stiffness_factor)

                set_progress([50])

                result_v = newmark_beta(
                    M=model.M,
                    C=C_vertical,
                    K=K_vertical,
                    ground_acceleration=acc_v,
                    dt=dt,
                )

                set_progress([60])

                metrics_v = compute_demand_metrics(
                    displacement=result_v.displacement,
                    velocity=result_v.velocity,
                    absolute_acceleration=result_v.absolute_acceleration,
                    ground_acceleration=acc_v,
                    story_heights=model.story_heights,
                )

                energy_v = compute_energy_balance(
                    M=model.M,
                    C=C_vertical,
                    K=K_vertical,
                    displacement=result_v.displacement,
                    velocity=result_v.velocity,
                    ground_acceleration=acc_v,
                    dt=dt,
                )

                set_progress([65])

                # Store vertical results
                sim_results.displacement_vertical = [row.tolist() for row in result_v.displacement]
                sim_results.velocity_vertical = [row.tolist() for row in result_v.velocity]
                sim_results.acceleration_vertical = [
                    row.tolist() for row in result_v.absolute_acceleration
                ]
                sim_results.max_displacement_vertical = metrics_v.max_displacement.tolist()
                sim_results.max_velocity_vertical = metrics_v.max_velocity.tolist()
                sim_results.max_acceleration_vertical = metrics_v.max_acceleration.tolist()
                sim_results.inter_story_drift_ratio_vertical = (
                    metrics_v.inter_story_drift_ratio.tolist()
                )
                sim_results.peak_ground_acceleration_vertical = float(
                    metrics_v.peak_ground_acceleration
                )
                sim_results.has_vertical_results = True

                # Compute vertical natural frequencies
                # omega^2 = K/M, so omega_v = omega_h * sqrt(factor)
                sim_results.natural_frequencies_vertical = [
                    f * np.sqrt(vertical_stiffness_factor) for f in model.natural_frequencies
                ]
                sim_results.natural_periods_vertical = [
                    1.0 / f if f > 0 else 0 for f in sim_results.natural_frequencies_vertical
                ]

                # Combine energy from both axes
                energy_kinetic = energy_h["kinetic"] + energy_v["kinetic"]
                energy_strain = energy_h["strain"] + energy_v["strain"]
                energy_damping = energy_h["damping"] + energy_v["damping"]
                energy_input = energy_h["input"] + energy_v["input"]

            set_progress([70])

            # Store energy balance (combined if vertical exists)
            sim_results.energy_kinetic = energy_kinetic.tolist()
            sim_results.energy_strain = energy_strain.tolist()
            sim_results.energy_damping = energy_damping.tolist()
            sim_results.energy_input = energy_input.tolist()

            # Monte Carlo analysis if enabled (horizontal only for now)
            mc_enabled = enable_mc and "enabled" in enable_mc
            if mc_enabled:
                set_progress([75])

                ua = UncertaintyAnalysis(model, acc_h, dt)
                mc_result = ua.run_mc_ensemble(
                    n_samples=mc_samples or 100,
                    stiffness_cov=stiffness_cov or 0.05,
                    damping_cov=damping_cov or 0.20,
                    mass_cov=mass_cov or 0.0,
                    seed=mc_seed or 42,
                )

                set_progress([95])

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

            set_progress([100])

            # Format summary values
            max_drift = max(sim_results.inter_story_drift_ratio)
            max_disp = sim_results.max_displacement[-1]  # Roof displacement
            max_acc = max(sim_results.max_acceleration)

            # Build status message
            status_msg = "Simulation completed successfully!"
            if has_vertical:
                status_msg = "Two-axis simulation completed successfully!"

            sidebar_info = f"Simulation: Complete (max drift={max_drift:.3f})"
            if has_vertical:
                max_drift_v = max(sim_results.inter_story_drift_ratio_vertical)
                sidebar_info = f"Simulation: H={max_drift:.3f}, V={max_drift_v:.4f}"

            return (
                sim_results.model_dump(),
                100,
                status_msg,
                "success",
                {"display": "block"},
                f"{max_drift:.4f}",
                f"{max_disp:.4f}",
                f"{max_acc:.3f}",
                sidebar_info,
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
