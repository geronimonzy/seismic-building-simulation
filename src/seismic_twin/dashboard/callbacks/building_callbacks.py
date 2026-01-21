"""Callbacks for the building configuration page."""

import json
from datetime import datetime

import numpy as np
from dash import Dash, Input, Output, State, html, no_update

from seismic_twin.dashboard.presets import (
    BUILDING_REQUIRED_FIELDS,
    create_import_alert,
    decode_uploaded_json,
    get_building_preset,
    validate_preset_fields,
)


def register_building_callbacks(app: Dash) -> None:
    """Register building page callbacks."""

    @app.callback(
        Output("store-building-params", "data"),
        Output("display-natural-periods", "children"),
        Output("display-natural-frequencies", "children"),
        Output("graph-mode-shapes", "figure"),
        Output("sidebar-building-info", "children"),
        Input("btn-update-building", "n_clicks"),
        State("input-n-stories", "value"),
        State("input-mass-uniform", "value"),
        State("check-uniform-mass", "value"),
        State("input-stiffness-uniform", "value"),
        State("check-uniform-stiffness", "value"),
        State("input-story-height", "value"),
        State("slider-damping-ratio", "value"),
        State("input-building-latitude", "value"),
        State("input-building-longitude", "value"),
        State("store-building-params", "data"),
        prevent_initial_call=False,
    )
    def update_building_model(
        n_clicks,
        n_stories,
        mass_uniform,
        uniform_mass_checked,
        stiffness_uniform,
        uniform_stiffness_checked,
        story_height,
        damping_ratio,
        latitude,
        longitude,
        current_params,
    ):
        """Update building model and compute modal properties."""
        from seismic_twin import MDOFShearBuilding
        from seismic_twin.dashboard.figures import create_mode_shapes_figure
        from seismic_twin.dashboard.state.schemas import BuildingParams

        # Handle defaults
        n_stories = n_stories or 3
        mass_uniform = mass_uniform or 100000
        stiffness_uniform = stiffness_uniform or 1e8
        story_height = story_height or 3.5
        damping_ratio = damping_ratio or 0.05

        # Create arrays
        use_uniform_mass = "uniform" in (uniform_mass_checked or [])
        use_uniform_stiffness = "uniform" in (uniform_stiffness_checked or [])

        # For now, uniform values are used (per-floor inputs not yet implemented)
        masses = [mass_uniform] * n_stories
        stiffnesses = [stiffness_uniform] * n_stories
        story_heights = [story_height] * n_stories

        # Create building model
        try:
            model = MDOFShearBuilding(
                masses=np.array(masses),
                stiffnesses=np.array(stiffnesses),
                damping_ratio=damping_ratio,
                story_heights=np.array(story_heights),
            )

            # Create params object
            params = BuildingParams(
                n_stories=n_stories,
                masses=masses,
                stiffnesses=stiffnesses,
                damping_ratio=damping_ratio,
                story_heights=story_heights,
                uniform_mass=use_uniform_mass,
                uniform_stiffness=use_uniform_stiffness,
                latitude=latitude,
                longitude=longitude,
            )

            # Format natural periods display
            periods_display = html.Ul(
                [
                    html.Li(f"Mode {i + 1}: {T:.3f} s")
                    for i, T in enumerate(model.natural_periods[:3])
                ]
            )

            # Format natural frequencies display
            freq_display = html.Ul(
                [
                    html.Li(f"Mode {i + 1}: {f:.2f} rad/s ({f / (2 * np.pi):.2f} Hz)")
                    for i, f in enumerate(model.natural_frequencies[:3])
                ]
            )

            # Create mode shapes figure
            mode_shapes_fig = create_mode_shapes_figure(
                model.mode_shapes,
                model.natural_periods,
                n_modes=min(3, n_stories),
            )

            # Sidebar info
            location_str = ""
            if latitude is not None and longitude is not None:
                location_str = f" @ ({latitude:.2f}, {longitude:.2f})"
            sidebar_info = f"Building: {n_stories} stories, T1={model.natural_periods[0]:.2f}s{location_str}"

            return (
                params.model_dump(),
                periods_display,
                freq_display,
                mode_shapes_fig,
                sidebar_info,
            )

        except Exception as e:
            # Return error state
            error_msg = html.Div(
                [html.I(className="bi bi-exclamation-triangle me-2"), str(e)],
                className="text-danger",
            )
            empty_fig = create_mode_shapes_figure(np.array([]), np.array([]))
            return (
                current_params or BuildingParams().model_dump(),
                error_msg,
                error_msg,
                empty_fig,
                "Building: Error",
            )

    @app.callback(
        Output("mc-options", "style"),
        Input("check-enable-mc", "value"),
    )
    def toggle_mc_options(enable_mc):
        """Show/hide Monte Carlo options based on checkbox."""
        if enable_mc and "enabled" in enable_mc:
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("mass-per-floor-inputs", "style"),
        Input("check-uniform-mass", "value"),
    )
    def toggle_mass_inputs(uniform_checked):
        """Show/hide per-floor mass inputs."""
        if not uniform_checked or "uniform" not in uniform_checked:
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("stiffness-per-story-inputs", "style"),
        Input("check-uniform-stiffness", "value"),
    )
    def toggle_stiffness_inputs(uniform_checked):
        """Show/hide per-story stiffness inputs."""
        if not uniform_checked or "uniform" not in uniform_checked:
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("input-n-stories", "value", allow_duplicate=True),
        Output("input-mass-uniform", "value", allow_duplicate=True),
        Output("input-stiffness-uniform", "value", allow_duplicate=True),
        Output("input-story-height", "value", allow_duplicate=True),
        Output("slider-damping-ratio", "value", allow_duplicate=True),
        Output("building-preset-description", "children"),
        Input("select-building-preset", "value"),
        prevent_initial_call=True,
    )
    def load_building_preset(preset_id):
        """Load building preset values into input fields."""
        if not preset_id or preset_id == "custom":
            return no_update, no_update, no_update, no_update, no_update, ""

        preset = get_building_preset(preset_id)
        if not preset:
            return no_update, no_update, no_update, no_update, no_update, ""

        params = preset["params"]
        description = preset["description"]

        return (
            params["n_stories"],
            params["mass_per_floor"],
            params["stiffness_per_story"],
            params["story_height"],
            params["damping_ratio"],
            description,
        )

    @app.callback(
        Output("download-building-preset", "data"),
        Input("btn-export-building", "n_clicks"),
        State("input-n-stories", "value"),
        State("input-mass-uniform", "value"),
        State("input-stiffness-uniform", "value"),
        State("input-story-height", "value"),
        State("slider-damping-ratio", "value"),
        prevent_initial_call=True,
    )
    def export_building_preset(n_clicks, n_stories, mass, stiffness, height, damping):
        """Export current building configuration as JSON."""
        if not n_clicks:
            return no_update

        preset_data = {
            "name": "Custom Building",
            "description": "User-defined building configuration",
            "n_stories": n_stories or 3,
            "mass_per_floor": mass or 100000,
            "stiffness_per_story": stiffness or 100000000,
            "damping_ratio": damping or 0.05,
            "story_height": height or 3.5,
        }

        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"building_preset_{timestamp}.json"

        return dict(
            content=json.dumps(preset_data, indent=2),
            filename=filename,
        )

    @app.callback(
        Output("input-n-stories", "value", allow_duplicate=True),
        Output("input-mass-uniform", "value", allow_duplicate=True),
        Output("input-stiffness-uniform", "value", allow_duplicate=True),
        Output("input-story-height", "value", allow_duplicate=True),
        Output("slider-damping-ratio", "value", allow_duplicate=True),
        Output("select-building-preset", "value", allow_duplicate=True),
        Output("building-import-alert", "children"),
        Input("upload-building-preset", "contents"),
        State("upload-building-preset", "filename"),
        prevent_initial_call=True,
    )
    def import_building_preset(contents, filename):
        """Import building configuration from JSON file."""
        no_change = (no_update,) * 6

        if not contents:
            return (*no_change, "")

        try:
            data = decode_uploaded_json(contents)

            missing = validate_preset_fields(data, BUILDING_REQUIRED_FIELDS)
            if missing:
                alert = create_import_alert(
                    f"Missing fields in JSON: {', '.join(missing)}", "danger"
                )
                return (*no_change, alert)

            name = data.get("name", "Imported")
            alert = create_import_alert(f"Successfully imported: {name}", "success", duration=4000)

            return (
                data["n_stories"],
                data["mass_per_floor"],
                data["stiffness_per_story"],
                data["story_height"],
                data["damping_ratio"],
                "custom",
                alert,
            )

        except ValueError as e:
            alert = create_import_alert(str(e), "danger")
            return (*no_change, alert)
        except Exception as e:
            alert = create_import_alert(f"Error importing file: {e}", "danger")
            return (*no_change, alert)
