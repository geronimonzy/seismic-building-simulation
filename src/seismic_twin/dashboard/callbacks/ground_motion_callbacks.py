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


def register_ground_motion_callbacks(app: Dash) -> None:
    """Register ground motion page callbacks."""

    @app.callback(
        Output("store-ground-motion", "data"),
        Output("graph-ground-motion", "figure"),
        Output("display-gm-source", "children"),
        Output("display-gm-pga", "children"),
        Output("display-gm-duration", "children"),
        Output("sidebar-gm-info", "children"),
        Input("btn-generate-synthetic", "n_clicks"),
        State("input-target-pga", "value"),
        State("input-duration", "value"),
        State("input-predominant-freq", "value"),
        State("input-bandwidth", "value"),
        State("input-seed", "value"),
        State("store-ground-motion", "data"),
        prevent_initial_call=True,
    )
    def generate_synthetic_ground_motion(
        n_clicks,
        target_pga,
        duration,
        predominant_freq,
        bandwidth,
        seed,
        current_gm,
    ):
        """Generate synthetic ground motion."""
        from seismic_twin import generate_synthetic_ground_motion
        from seismic_twin.dashboard.figures import create_ground_motion_figure
        from seismic_twin.dashboard.state.schemas import GroundMotionState

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
            )

        # Handle defaults
        target_pga = target_pga or 0.3
        duration = duration or 30
        predominant_freq = predominant_freq or 2.0
        bandwidth = bandwidth or 1.5

        try:
            # Generate ground motion
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
            )

            # Create figure
            fig = create_ground_motion_figure(
                time,
                acceleration,
                title="Synthetic Ground Motion",
                show_pga=True,
                show_rangeslider=True,
            )

            return (
                gm_state.model_dump(),
                fig,
                "Synthetic",
                f"{pga:.3f} g",
                f"{duration:.1f} s",
                f"Ground Motion: Synthetic, PGA={pga:.2f}g",
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

        if not event_id:
            error_alert = dbc.Alert("Please enter an event ID", color="warning")
            empty_fig = create_ground_motion_figure([], [])
            return (
                current_gm or GroundMotionState().model_dump(),
                empty_fig,
                "-",
                "-",
                "-",
                "Ground Motion: None",
                error_alert,
            )

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

            # Create ground motion state
            gm_state = GroundMotionState(
                time=time.tolist(),
                acceleration=acceleration.tolist(),
                dt=dt,
                pga=pga,
                source="real",
                duration=duration,
                event_id=event_id,
                station=station,
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
            empty_fig = create_ground_motion_figure([], [])
            return (
                current_gm or GroundMotionState().model_dump(),
                empty_fig,
                "-",
                "-",
                "-",
                "Ground Motion: None",
                error_alert,
            )

        except Exception as e:
            error_alert = dbc.Alert(f"Error fetching data: {str(e)}", color="danger")
            empty_fig = create_ground_motion_figure([], [])
            return (
                current_gm or GroundMotionState().model_dump(),
                empty_fig,
                "-",
                "-",
                "-",
                "Ground Motion: Error",
                error_alert,
            )

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
            alert = create_import_alert(
                f"Successfully imported: {name}", "success", duration=4000
            )

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
