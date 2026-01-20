"""Callbacks for the results page."""

import numpy as np
from dash import Dash, Input, Output, State


def _create_both_axes_time_history(results, selected_floors, response_type):
    """Create time history figure showing both horizontal and vertical axes."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    time = np.array(results.get("time", []))

    # Get data for both axes
    disp_h = np.array(results.get("displacement", []))
    disp_v = np.array(results.get("displacement_vertical", []))

    if selected_floors is None:
        selected_floors = [0] if len(disp_h) > 0 else []

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Horizontal (X)", "Vertical (Z)"),
    )

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for i, floor_idx in enumerate(selected_floors):
        color = colors[i % len(colors)]

        # Horizontal
        if floor_idx < len(disp_h):
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=disp_h[floor_idx],
                    mode="lines",
                    name=f"Floor {floor_idx + 1} (H)",
                    line={"color": color, "width": 1},
                    legendgroup=f"floor{floor_idx}",
                ),
                row=1,
                col=1,
            )

        # Vertical
        if floor_idx < len(disp_v):
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=disp_v[floor_idx],
                    mode="lines",
                    name=f"Floor {floor_idx + 1} (V)",
                    line={"color": color, "width": 1, "dash": "dot"},
                    legendgroup=f"floor{floor_idx}",
                ),
                row=2,
                col=1,
            )

    fig.update_layout(
        title="Displacement Time History (Both Axes)",
        height=500,
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        margin={"l": 60, "r": 30, "t": 80, "b": 50},
    )

    fig.update_yaxes(title_text="Displacement (m)", row=1, col=1)
    fig.update_yaxes(title_text="Displacement (m)", row=2, col=1)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)

    return fig


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
        Output("axis-selector-container", "style"),
        Output("drift-axis-selector-container", "style"),
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
                {"display": "none"},
                {"display": "none"},
            )

        # Extract summary values
        pga = results.get("peak_ground_acceleration", 0)
        max_drift = max(results.get("inter_story_drift_ratio", [0]))
        max_disp = (
            results.get("max_displacement", [0])[-1] if results.get("max_displacement") else 0
        )
        t1 = results.get("natural_periods", [0])[0] if results.get("natural_periods") else 0

        # Create floor options
        n_floors = len(results.get("max_displacement", []))
        floor_options = [{"label": f"Floor {i + 1}", "value": i} for i in range(n_floors)]
        default_floors = list(range(min(3, n_floors)))  # Select first 3 floors by default

        # Show axis selector only if vertical results exist
        has_vertical = results.get("has_vertical_results", False)
        axis_style = {"display": "block"} if has_vertical else {"display": "none"}

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
            axis_style,
            axis_style,
        )

    @app.callback(
        Output("graph-time-history", "figure"),
        Input("dropdown-floors", "value"),
        Input("radio-response-type", "value"),
        Input("radio-axis-select", "value"),
        State("store-simulation-results", "data"),
    )
    def update_time_history_plot(selected_floors, response_type, axis, results):
        """Update time history plot based on floor selection and axis."""
        from seismic_twin.dashboard.figures import create_time_history_figure
        from seismic_twin.dashboard.figures.time_history import create_single_response_figure

        if not results or not results.get("completed", False):
            return create_time_history_figure([], [])

        # Convert results to numpy arrays
        time = np.array(results.get("time", []))
        has_vertical = results.get("has_vertical_results", False)

        # Get data based on axis selection
        if axis == "vertical" and has_vertical:
            displacement = np.array(results.get("displacement_vertical", []))
            velocity_data = results.get("velocity_vertical", [])
            acceleration_data = results.get("acceleration_vertical", [])
            axis_label = " (Vertical)"
        elif axis == "both" and has_vertical:
            # Create combined "both" view using subplots
            return _create_both_axes_time_history(results, selected_floors, response_type)
        else:
            # Default: horizontal
            displacement = np.array(results.get("displacement", []))
            velocity_data = results.get("velocity", [])
            acceleration_data = results.get("acceleration", [])
            axis_label = " (Horizontal)" if has_vertical else ""

        velocity = np.array(velocity_data) if velocity_data else None
        acceleration = np.array(acceleration_data) / 9.81 if acceleration_data else None

        if response_type == "all":
            return create_time_history_figure(
                time=time,
                displacement=displacement,
                velocity=velocity,
                acceleration=acceleration,
                selected_floors=selected_floors,
                title=f"Structural Response Time Histories{axis_label}",
            )

        # Response type configuration for single response figures
        response_config = {
            "displacement": {"response": displacement, "label": "Displacement", "units": "m"},
            "velocity": {"response": velocity or np.array([]), "label": "Velocity", "units": "m/s"},
            "acceleration": {
                "response": acceleration or np.array([]),
                "label": "Acceleration",
                "units": "g",
            },
        }

        config = response_config.get(response_type, response_config["displacement"])
        return create_single_response_figure(
            time=time,
            response=config["response"],
            response_type=config["label"] + axis_label,
            units=config["units"],
            selected_floors=selected_floors,
        )

    @app.callback(
        Output("graph-drift-profile", "figure"),
        Input("check-show-limits", "value"),
        Input("radio-drift-axis-select", "value"),
        State("store-simulation-results", "data"),
    )
    def update_drift_profile(show_limits, axis, results):
        """Update drift profile plot based on axis selection."""
        from seismic_twin.dashboard.figures import create_drift_profile_figure

        if not results or not results.get("completed", False):
            return create_drift_profile_figure([])

        has_vertical = results.get("has_vertical_results", False)
        show_limits_bool = show_limits and "show" in show_limits

        if axis == "vertical" and has_vertical:
            drift_ratios = results.get("inter_story_drift_ratio_vertical", [])
            title = "Axial Strain Profile (Vertical)"
            # Disable performance limits for vertical (axial strain)
            show_limits_bool = False
        else:
            drift_ratios = results.get("inter_story_drift_ratio", [])
            title = "Inter-Story Drift Profile"
            if has_vertical:
                title += " (Horizontal)"

        return create_drift_profile_figure(
            drift_ratios=drift_ratios,
            title=title,
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
            results and results.get("completed", False) and results.get("mc_enabled", False)
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

    @app.callback(
        Output("energy-content", "style"),
        Output("no-energy-message", "style"),
        Output("graph-energy-balance", "figure"),
        Input("check-energy-components", "value"),
        State("store-simulation-results", "data"),
    )
    def update_energy_balance_plot(selected_components, results):
        """Update energy balance plot based on selected components."""
        from seismic_twin.dashboard.figures import create_energy_balance_figure

        # Check if energy results are available
        has_energy_results = (
            results
            and results.get("completed", False)
            and len(results.get("energy_kinetic", [])) > 0
        )

        if not has_energy_results:
            return (
                {"display": "none"},
                {"display": "block"},
                create_energy_balance_figure([], [], [], [], []),
            )

        # Get energy data (combined from both axes if vertical exists)
        time = results.get("time", [])
        kinetic = results.get("energy_kinetic", [])
        strain = results.get("energy_strain", [])
        damping = results.get("energy_damping", [])
        input_energy = results.get("energy_input", [])

        # Build title
        has_vertical = results.get("has_vertical_results", False)
        title = "Energy Balance (Combined H+V)" if has_vertical else "Energy Balance"

        energy_fig = create_energy_balance_figure(
            time=time,
            kinetic=kinetic,
            strain=strain,
            damping=damping,
            input_energy=input_energy,
            selected_components=selected_components,
            title=title,
        )

        return (
            {"display": "block"},
            {"display": "none"},
            energy_fig,
        )

    @app.callback(
        Output("graph-building-animation", "figure"),
        Input("tabs-results", "active_tab"),
        Input("slider-animation-scale", "value"),
        Input("check-animation-options", "value"),
        State("store-simulation-results", "data"),
        State("store-building-params", "data"),
        State("store-ground-motion", "data"),
    )
    def update_building_animation(active_tab, scale, options, results, building, gm):
        """Update building animation figure."""
        from seismic_twin.dashboard.figures import create_building_animation_figure

        # Only generate animation when the tab is active (lazy loading)
        if active_tab != "tab-animation":
            return create_building_animation_figure([], np.array([]), np.array([]))

        # Check if results are available
        if not results or not results.get("completed", False):
            return create_building_animation_figure([], np.array([]), np.array([]))

        # Get building story heights
        story_heights = building.get("story_heights", [3.5, 3.5, 3.5]) if building else [3.5]

        # Get simulation results (horizontal displacement for animation)
        time = np.array(results.get("time", []))
        displacement = np.array(results.get("displacement", []))

        # Get ground motion data for base motion visualization
        ground_acceleration = None
        if gm and gm.get("acceleration"):
            ground_acceleration = np.array(gm.get("acceleration", []))

        # Parse display options
        options = options or []
        show_undeformed = "undeformed" in options
        show_labels = "labels" in options
        show_wave = "wave" in options

        return create_building_animation_figure(
            story_heights=story_heights,
            displacement=displacement,
            time=time,
            ground_acceleration=ground_acceleration,
            scale_factor=float(scale),
            show_undeformed=show_undeformed,
            show_labels=show_labels,
            show_wave=show_wave,
        )
