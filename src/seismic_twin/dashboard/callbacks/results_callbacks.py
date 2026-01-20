"""Callbacks for the results page."""

import numpy as np
from dash import Dash, Input, Output, State


def register_results_callbacks(app: Dash) -> None:
    """Register results page callbacks."""

    @app.callback(
        Output("results-container", "style"),
        Output("no-results-message", "style"),
        Output("results-pga", "children"),
        Output("results-max-drift", "children"),
        Output("results-max-disp", "children"),
        Output("results-t1", "children"),
        Output("dropdown-floors", "options"),
        Output("dropdown-floors", "value"),
        Output("dropdown-uncertainty-floor", "options"),
        Output("dropdown-uncertainty-floor", "value"),
        Input("store-simulation-results", "data"),
    )
    def update_results_display(results):
        """Update results page based on simulation results."""
        if not results or not results.get("completed", False):
            # No results available
            return (
                {"display": "none"},
                {"display": "block"},
                "-",
                "-",
                "-",
                "-",
                [],
                [],
                [],
                None,
            )

        # Extract summary values
        pga = results.get("peak_ground_acceleration", 0)
        max_drift = max(results.get("inter_story_drift_ratio", [0]))
        max_disp = results.get("max_displacement", [0])[-1] if results.get("max_displacement") else 0
        t1 = results.get("natural_periods", [0])[0] if results.get("natural_periods") else 0

        # Create floor options
        n_floors = len(results.get("max_displacement", []))
        floor_options = [{"label": f"Floor {i + 1}", "value": i} for i in range(n_floors)]
        default_floors = list(range(min(3, n_floors)))  # Select first 3 floors by default

        return (
            {"display": "block"},
            {"display": "none"},
            f"{pga:.3f}",
            f"{max_drift:.4f}",
            f"{max_disp:.4f}",
            f"{t1:.3f}",
            floor_options,
            default_floors,
            floor_options,
            0 if n_floors > 0 else None,
        )

    @app.callback(
        Output("graph-time-history", "figure"),
        Input("dropdown-floors", "value"),
        Input("radio-response-type", "value"),
        State("store-simulation-results", "data"),
    )
    def update_time_history_plot(selected_floors, response_type, results):
        """Update time history plot based on floor selection."""
        from seismic_twin.dashboard.figures import create_time_history_figure
        from seismic_twin.dashboard.figures.time_history import create_single_response_figure

        if not results or not results.get("completed", False):
            return create_time_history_figure([], [])

        # Convert results to numpy arrays
        time = np.array(results.get("time", []))
        displacement = np.array(results.get("displacement", []))
        velocity_data = results.get("velocity", [])
        acceleration_data = results.get("acceleration", [])

        velocity = np.array(velocity_data) if velocity_data else None
        acceleration = np.array(acceleration_data) / 9.81 if acceleration_data else None

        if response_type == "all":
            return create_time_history_figure(
                time=time,
                displacement=displacement,
                velocity=velocity,
                acceleration=acceleration,
                selected_floors=selected_floors,
                title="Structural Response Time Histories",
            )

        # Response type configuration for single response figures
        response_config = {
            "displacement": {"response": displacement, "label": "Displacement", "units": "m"},
            "velocity": {"response": velocity or np.array([]), "label": "Velocity", "units": "m/s"},
            "acceleration": {"response": acceleration or np.array([]), "label": "Acceleration", "units": "g"},
        }

        config = response_config.get(response_type, response_config["displacement"])
        return create_single_response_figure(
            time=time,
            response=config["response"],
            response_type=config["label"],
            units=config["units"],
            selected_floors=selected_floors,
        )

    @app.callback(
        Output("graph-drift-profile", "figure"),
        Input("check-show-limits", "value"),
        State("store-simulation-results", "data"),
    )
    def update_drift_profile(show_limits, results):
        """Update drift profile plot."""
        from seismic_twin.dashboard.figures import create_drift_profile_figure

        if not results or not results.get("completed", False):
            return create_drift_profile_figure([])

        drift_ratios = results.get("inter_story_drift_ratio", [])
        show_limits_bool = show_limits and "show" in show_limits

        return create_drift_profile_figure(
            drift_ratios=drift_ratios,
            title="Inter-Story Drift Profile",
            show_limits=show_limits_bool,
        )

    @app.callback(
        Output("uncertainty-content", "style"),
        Output("no-mc-message", "style"),
        Output("graph-uncertainty-band", "figure"),
        Output("graph-drift-distribution", "figure"),
        Input("dropdown-uncertainty-floor", "value"),
        State("store-simulation-results", "data"),
    )
    def update_uncertainty_plots(floor_idx, results):
        """Update uncertainty plots."""
        from seismic_twin.dashboard.figures import create_uncertainty_figure
        from seismic_twin.dashboard.figures.uncertainty_band import (
            create_drift_distribution_figure,
        )

        # Check if MC results are available
        has_mc_results = (
            results
            and results.get("completed", False)
            and results.get("mc_enabled", False)
        )

        if not has_mc_results:
            return (
                {"display": "none"},
                {"display": "block"},
                create_uncertainty_figure([], [], [], [], 0),
                create_drift_distribution_figure([]),
            )

        # Get MC results
        time = np.array(results.get("time", []))
        p5 = np.array(results.get("displacement_p5", []))
        p50 = np.array(results.get("displacement_p50", []))
        p95 = np.array(results.get("displacement_p95", []))
        drift_dist = results.get("max_drift_distribution", [])

        uncertainty_fig = create_uncertainty_figure(
            time=time,
            median=p50,
            p5=p5,
            p95=p95,
            floor_idx=floor_idx if floor_idx is not None else 0,
            response_type="Displacement",
            units="m",
        )

        drift_fig = create_drift_distribution_figure(
            drift_values=drift_dist,
            title="Max Drift Distribution",
        )

        return (
            {"display": "block"},
            {"display": "none"},
            uncertainty_fig,
            drift_fig,
        )
