"""Callbacks for the ground motion page."""

import json
from datetime import datetime

import numpy as np
from dash import Dash, Input, Output, State, html, no_update

from seismic_twin.dashboard.presets import (
    GROUND_MOTION_REQUIRED_FIELDS,
    create_import_alert,
    decode_uploaded_json,
    get_ground_motion_preset,
    validate_preset_fields,
)


def _create_two_component_figure(time, horizontal, vertical):
    """Create figure showing both horizontal and vertical components."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Horizontal (X)", "Vertical (Z)"),
    )

    # Horizontal component
    fig.add_trace(
        go.Scatter(
            x=time,
            y=horizontal,
            mode="lines",
            name="Horizontal",
            line={"color": "#1f77b4", "width": 1},
        ),
        row=1,
        col=1,
    )

    # Vertical component
    fig.add_trace(
        go.Scatter(
            x=time,
            y=vertical,
            mode="lines",
            name="Vertical",
            line={"color": "#ff7f0e", "width": 1},
        ),
        row=2,
        col=1,
    )

    # Add PGA markers
    h_pga_idx = np.argmax(np.abs(horizontal))
    v_pga_idx = np.argmax(np.abs(vertical))

    fig.add_trace(
        go.Scatter(
            x=[time[h_pga_idx]],
            y=[horizontal[h_pga_idx]],
            mode="markers",
            name=f"PGA: {np.abs(horizontal[h_pga_idx]):.3f}g",
            marker={"color": "red", "size": 10, "symbol": "x"},
            showlegend=True,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[time[v_pga_idx]],
            y=[vertical[v_pga_idx]],
            mode="markers",
            name=f"PGA: {np.abs(vertical[v_pga_idx]):.3f}g",
            marker={"color": "red", "size": 10, "symbol": "x"},
            showlegend=True,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title="Synthetic Ground Motion (Two-Component)",
        height=400,
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        margin={"l": 60, "r": 30, "t": 80, "b": 50},
    )

    fig.update_yaxes(title_text="Acceleration (g)", row=1, col=1)
    fig.update_yaxes(title_text="Acceleration (g)", row=2, col=1)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)

    return fig


def register_ground_motion_callbacks(app: Dash) -> None:
    """Register ground motion page callbacks."""

    @app.callback(
        Output("vertical-options", "style"),
        Input("check-enable-vertical", "value"),
    )
    def toggle_vertical_options(enable_vertical):
        """Show/hide vertical component options."""
        if enable_vertical and "enabled" in enable_vertical:
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("store-ground-motion", "data"),
        Output("graph-ground-motion", "figure"),
        Output("display-gm-source", "children"),
        Output("display-gm-pga", "children"),
        Output("display-gm-duration", "children"),
        Output("sidebar-gm-info", "children"),
        Output("vertical-pga-row", "style"),
        Output("display-gm-pga-vertical", "children"),
        Output("display-gm-vh-ratio", "children"),
        Input("btn-generate-synthetic", "n_clicks"),
        State("input-target-pga", "value"),
        State("input-duration", "value"),
        State("input-predominant-freq", "value"),
        State("input-bandwidth", "value"),
        State("input-seed", "value"),
        State("check-enable-vertical", "value"),
        State("input-vh-ratio", "value"),
        State("store-ground-motion", "data"),
        prevent_initial_call=True,
    )
    def generate_synthetic_ground_motion_callback(
        n_clicks,
        target_pga,
        duration,
        predominant_freq,
        bandwidth,
        seed,
        enable_vertical,
        v_h_ratio,
        current_gm,
    ):
        """Generate synthetic ground motion with optional vertical component."""
        from seismic_twin import generate_synthetic_ground_motion
        from seismic_twin.dashboard.figures import create_ground_motion_figure
        from seismic_twin.dashboard.state.schemas import GroundMotionState
        from seismic_twin.ground_motion.synthetic import generate_vertical_component

        def _error_response(error_msg: str):
            """Return error state tuple."""
            empty_fig = create_ground_motion_figure([], [])
            return (
                current_gm or GroundMotionState().model_dump(),
                empty_fig,
                f"Error: {error_msg}",
                "-",
                "-",
                "Ground Motion: Error",
                {"display": "none"},
                "-",
                "-",
            )

        # Handle defaults
        target_pga = target_pga or 0.3
        duration = duration or 30
        predominant_freq = predominant_freq or 2.0
        bandwidth = bandwidth or 1.5
        v_h_ratio = v_h_ratio or 0.67
        has_vertical = enable_vertical and "enabled" in enable_vertical

        try:
            # Generate horizontal ground motion
            time, acceleration = generate_synthetic_ground_motion(
                duration=float(duration),
                dt=0.01,
                target_pga=float(target_pga),
                predominant_freq=float(predominant_freq),
                bandwidth=float(bandwidth),
                seed=int(seed) if seed is not None else None,
            )

            # Compute actual PGA
            pga = float(np.max(np.abs(acceleration)))
            dt = float(time[1] - time[0]) if len(time) > 1 else 0.01

            # Create ground motion state
            gm_state = GroundMotionState(
                time=time.tolist(),
                acceleration=acceleration.tolist(),
                dt=dt,
                pga=pga,
                source="synthetic",
                duration=float(duration),
                target_pga=float(target_pga),
                predominant_freq=float(predominant_freq),
                bandwidth=float(bandwidth),
                seed=int(seed) if seed is not None else None,
                v_h_ratio=float(v_h_ratio),
            )

            # Generate vertical component if enabled
            vertical_pga_display = "-"
            vh_ratio_display = "-"
            vertical_row_style = {"display": "none"}

            if has_vertical:
                v_seed = int(seed) + 1000 if seed is not None else None
                vertical = generate_vertical_component(
                    horizontal=acceleration,
                    dt=dt,
                    v_h_ratio=float(v_h_ratio),
                    freq_shift=1.3,
                    seed=v_seed,
                )
                pga_vertical = float(np.max(np.abs(vertical)))

                gm_state.acceleration_vertical = vertical.tolist()
                gm_state.has_vertical = True
                gm_state.pga_vertical = pga_vertical

                vertical_pga_display = f"{pga_vertical:.3f} g"
                actual_vh_ratio = pga_vertical / pga if pga > 0 else 0
                vh_ratio_display = f"{actual_vh_ratio:.2f}"
                vertical_row_style = {"display": "block"}

            # Create figure (show both components if vertical exists)
            if has_vertical and len(gm_state.acceleration_vertical) > 0:
                fig = _create_two_component_figure(
                    time,
                    acceleration,
                    np.array(gm_state.acceleration_vertical),
                )
            else:
                fig = create_ground_motion_figure(
                    time,
                    acceleration,
                    title="Synthetic Ground Motion",
                    show_pga=True,
                    show_rangeslider=True,
                )

            sidebar_info = f"Ground Motion: Synthetic, PGA={pga:.2f}g"
            if has_vertical:
                sidebar_info += f" (V: {gm_state.pga_vertical:.2f}g)"

            return (
                gm_state.model_dump(),
                fig,
                "Synthetic",
                f"{pga:.3f} g",
                f"{duration:.1f} s",
                sidebar_info,
                vertical_row_style,
                vertical_pga_display,
                vh_ratio_display,
            )

        except Exception as e:
            return _error_response(str(e))

    @app.callback(
        Output("store-ground-motion", "data", allow_duplicate=True),
        Output("graph-ground-motion", "figure", allow_duplicate=True),
        Output("display-gm-source", "children", allow_duplicate=True),
        Output("display-gm-pga", "children", allow_duplicate=True),
        Output("display-gm-duration", "children", allow_duplicate=True),
        Output("sidebar-gm-info", "children", allow_duplicate=True),
        Output("vertical-pga-row", "style", allow_duplicate=True),
        Output("display-gm-pga-vertical", "children", allow_duplicate=True),
        Output("display-gm-vh-ratio", "children", allow_duplicate=True),
        Output("fetch-status", "children"),
        Input("btn-fetch-real", "n_clicks"),
        State("input-event-id", "value"),
        State("input-station", "value"),
        State("select-channel", "value"),
        State("store-ground-motion", "data"),
        prevent_initial_call=True,
    )
    def fetch_real_ground_motion(
        n_clicks,
        event_id,
        station,
        channel,
        current_gm,
    ):
        """Fetch real earthquake record."""
        import dash_bootstrap_components as dbc

        from seismic_twin.dashboard.figures import create_ground_motion_figure
        from seismic_twin.dashboard.state.schemas import GroundMotionState

        def _return_error(msg, alert):
            empty_fig = create_ground_motion_figure([], [])
            return (
                current_gm or GroundMotionState().model_dump(),
                empty_fig,
                "-",
                "-",
                "-",
                msg,
                {"display": "none"},
                "-",
                "-",
                alert,
            )

        if not event_id:
            error_alert = dbc.Alert("Please enter an event ID", color="warning")
            return _return_error("Ground Motion: None", error_alert)

        try:
            # Try to import data fetcher
            from seismic_twin import SeismicDataFetcher

            fetcher = SeismicDataFetcher()

            # Fetch data
            result = fetcher.fetch_event_data(
                event_id=event_id,
                station=station,
                channel=channel or "HNE",
            )

            time = result["time"]
            acceleration = result["acceleration"]
            pga = float(np.max(np.abs(acceleration)))
            dt = float(time[1] - time[0]) if len(time) > 1 else 0.01
            duration = float(time[-1] - time[0]) if len(time) > 1 else 0

            # Create ground motion state (real records don't have vertical by default)
            gm_state = GroundMotionState(
                time=time.tolist(),
                acceleration=acceleration.tolist(),
                dt=dt,
                pga=pga,
                source="real",
                duration=duration,
                event_id=event_id,
                station=station,
                has_vertical=False,
            )

            # Create figure
            fig = create_ground_motion_figure(
                time,
                acceleration,
                title=f"Real Earthquake: {event_id}",
                show_pga=True,
                show_rangeslider=True,
            )

            success_alert = dbc.Alert(
                f"Successfully fetched record for event {event_id}",
                color="success",
            )

            return (
                gm_state.model_dump(),
                fig,
                f"Real: {event_id}",
                f"{pga:.3f} g",
                f"{duration:.1f} s",
                f"Ground Motion: {event_id}, PGA={pga:.2f}g",
                {"display": "none"},
                "-",
                "-",
                success_alert,
            )

        except ImportError:
            error_alert = dbc.Alert(
                [
                    "Data fetching requires additional dependencies. ",
                    html.Code("pip install seismic-twin[data]"),
                ],
                color="danger",
            )
            return _return_error("Ground Motion: None", error_alert)

        except Exception as e:
            error_alert = dbc.Alert(f"Error fetching data: {str(e)}", color="danger")
            return _return_error("Ground Motion: Error", error_alert)

    @app.callback(
        Output("input-target-pga", "value", allow_duplicate=True),
        Output("input-duration", "value", allow_duplicate=True),
        Output("input-predominant-freq", "value", allow_duplicate=True),
        Output("input-bandwidth", "value", allow_duplicate=True),
        Output("gm-preset-description", "children"),
        Input("select-gm-preset", "value"),
        prevent_initial_call=True,
    )
    def load_gm_preset(preset_id):
        """Load ground motion preset values into input fields."""
        if not preset_id or preset_id == "custom":
            return no_update, no_update, no_update, no_update, ""

        preset = get_ground_motion_preset(preset_id)
        if not preset:
            return no_update, no_update, no_update, no_update, ""

        params = preset["params"]
        description = preset["description"]

        return (
            params["target_pga"],
            params["duration"],
            params["predominant_freq"],
            params["bandwidth"],
            description,
        )

    @app.callback(
        Output("download-gm-preset", "data"),
        Input("btn-export-gm", "n_clicks"),
        State("input-target-pga", "value"),
        State("input-duration", "value"),
        State("input-predominant-freq", "value"),
        State("input-bandwidth", "value"),
        prevent_initial_call=True,
    )
    def export_gm_preset(n_clicks, pga, duration, freq, bandwidth):
        """Export current ground motion configuration as JSON."""
        if not n_clicks:
            return no_update

        preset_data = {
            "name": "Custom Scenario",
            "description": "User-defined ground motion scenario",
            "target_pga": pga or 0.3,
            "duration": duration or 30,
            "predominant_freq": freq or 2.0,
            "bandwidth": bandwidth or 1.5,
        }

        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"ground_motion_preset_{timestamp}.json"

        return dict(
            content=json.dumps(preset_data, indent=2),
            filename=filename,
        )

    @app.callback(
        Output("input-target-pga", "value", allow_duplicate=True),
        Output("input-duration", "value", allow_duplicate=True),
        Output("input-predominant-freq", "value", allow_duplicate=True),
        Output("input-bandwidth", "value", allow_duplicate=True),
        Output("select-gm-preset", "value", allow_duplicate=True),
        Output("gm-import-alert", "children"),
        Input("upload-gm-preset", "contents"),
        State("upload-gm-preset", "filename"),
        prevent_initial_call=True,
    )
    def import_gm_preset(contents, filename):
        """Import ground motion configuration from JSON file."""
        no_change = (no_update,) * 5

        if not contents:
            return (*no_change, "")

        try:
            data = decode_uploaded_json(contents)

            missing = validate_preset_fields(data, GROUND_MOTION_REQUIRED_FIELDS)
            if missing:
                alert = create_import_alert(
                    f"Missing fields in JSON: {', '.join(missing)}", "danger"
                )
                return (*no_change, alert)

            name = data.get("name", "Imported")
            alert = create_import_alert(f"Successfully imported: {name}", "success", duration=4000)

            return (
                data["target_pga"],
                data["duration"],
                data["predominant_freq"],
                data["bandwidth"],
                "custom",
                alert,
            )

        except ValueError as e:
            alert = create_import_alert(str(e), "danger")
            return (*no_change, alert)
        except Exception as e:
            alert = create_import_alert(f"Error importing file: {e}", "danger")
            return (*no_change, alert)
