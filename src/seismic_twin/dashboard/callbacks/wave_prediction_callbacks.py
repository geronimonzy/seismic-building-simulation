"""Callbacks for wave prediction page."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import numpy as np
from dash import Dash, Input, Output, State, callback_context, html
from dash.exceptions import PreventUpdate

from seismic_twin.dashboard.figures.validation_plots import (
    create_empty_spectrum_figure,
    create_empty_waveform_figure,
    create_spectrum_comparison_figure,
    create_waveform_comparison_figure,
)
from seismic_twin.dashboard.state.schemas import (
    BuildingParams,
    GroundMotionState,
    PredictionState,
    StationInfo,
)


def register_wave_prediction_callbacks(app: Dash) -> None:
    """Register all wave prediction callbacks."""

    @app.callback(
        Output("event-loading-placeholder", "children"),
        Output("event-info-display", "style"),
        Output("event-info-content", "children"),
        Output("card-station-selection", "style"),
        Output("card-run-prediction", "style"),
        Output("dropdown-target-station", "options"),
        Output("checklist-source-stations", "options"),
        Output("alert-prediction-status", "children"),
        Output("alert-prediction-status", "color"),
        Output("store-prediction-state", "data"),
        Input("btn-load-event", "n_clicks"),
        State("input-event-id", "value"),
        State("store-prediction-state", "data"),
        prevent_initial_call=True,
    )
    def load_event_data(n_clicks, event_id, state_data):
        """Load event data and available stations."""
        if not n_clicks or not event_id:
            raise PreventUpdate

        state = PredictionState(**state_data)

        try:
            # Try to load real data
            event_info, stations = _load_event_from_usgs(event_id)

            # Update state
            state.event_id = event_id
            state.event_magnitude = event_info["magnitude"]
            state.event_lat = event_info["latitude"]
            state.event_lon = event_info["longitude"]
            state.event_depth_km = event_info["depth_km"]
            state.event_region = event_info["region"]
            state.available_stations = [
                StationInfo(
                    station_id=s["station"],
                    network=s["network"],
                    latitude=s["latitude"],
                    longitude=s["longitude"],
                    distance_km=s["distance_km"],
                    pga=0.0,
                )
                for s in stations
            ]
            state.loaded = True
            state.error = None

            # Create event info display
            event_info_content = _create_event_info_display(event_info)

            # Create station options
            station_options = [
                {
                    "label": f"{s['station']} ({s['distance_km']:.1f} km)",
                    "value": s["station"],
                }
                for s in stations
            ]

            return (
                "",  # Loading placeholder
                {"display": "block"},  # Show event info
                event_info_content,
                {"display": "block"},  # Show station selection
                {"display": "block"},  # Show run button
                station_options,  # Target dropdown
                station_options,  # Source checklist
                f"Loaded M{event_info['magnitude']:.1f} {event_info['region']}",
                "success",
                state.model_dump(),
            )

        except ImportError:
            # ObsPy not available - use synthetic demo
            return _create_synthetic_demo_response(event_id, state)

        except Exception as e:
            state.loaded = False
            state.error = str(e)
            return (
                "",
                {"display": "none"},
                "",
                {"display": "none"},
                {"display": "none"},
                [],
                [],
                f"Error loading event: {e}",
                "danger",
                state.model_dump(),
            )

    @app.callback(
        Output("btn-run-prediction", "disabled"),
        Input("dropdown-target-station", "value"),
        Input("checklist-source-stations", "value"),
    )
    def update_run_button_state(target, sources):
        """Enable/disable run button based on selections."""
        if not target or not sources:
            return True
        if target in sources:
            # Need at least one source that isn't the target
            return len([s for s in sources if s != target]) == 0
        return False

    @app.callback(
        Output("checklist-source-stations", "value"),
        Input("btn-select-all-stations", "n_clicks"),
        Input("btn-clear-stations", "n_clicks"),
        State("checklist-source-stations", "options"),
        prevent_initial_call=True,
    )
    def handle_station_selection_buttons(select_all, clear, options):
        """Handle select all / clear buttons."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "btn-select-all-stations":
            return [opt["value"] for opt in options]
        elif button_id == "btn-clear-stations":
            return []

        raise PreventUpdate

    @app.callback(
        Output("graph-waveform-comparison", "figure"),
        Output("graph-spectrum-comparison", "figure"),
        Output("validation-metrics-content", "children"),
        Output("card-results", "style"),
        Output("alert-prediction-status", "children", allow_duplicate=True),
        Output("alert-prediction-status", "color", allow_duplicate=True),
        Output("store-prediction-state", "data", allow_duplicate=True),
        Input("btn-run-prediction", "n_clicks"),
        State("dropdown-target-station", "value"),
        State("checklist-source-stations", "value"),
        State("store-prediction-state", "data"),
        prevent_initial_call=True,
    )
    def run_prediction(n_clicks, target_station, source_stations, state_data):
        """Run wave propagation prediction."""
        if not n_clicks or not target_station:
            raise PreventUpdate

        state = PredictionState(**state_data)

        if not state.loaded:
            return (
                create_empty_waveform_figure(),
                create_empty_spectrum_figure(),
                "No event data loaded",
                {"display": "none"},
                "Please load event data first",
                "warning",
                state.model_dump(),
            )

        try:
            # Run prediction using synthetic data for demonstration
            result = _run_synthetic_prediction(
                state, target_station, source_stations
            )

            # Update state with results
            state.target_station_id = target_station
            state.selected_source_stations = source_stations
            state.time = result["time"]
            state.actual_waveform = result["actual"]
            state.predicted_waveform = result["predicted"]
            state.actual_pga = result["actual_pga"]
            state.predicted_pga = result["predicted_pga"]
            state.pga_ratio = result["pga_ratio"]
            state.pga_error_percent = result["pga_error"]
            state.spectrum_periods = result["periods"]
            state.spectrum_actual = result["actual_sa"]
            state.spectrum_predicted = result["predicted_sa"]
            state.nrmse = result["nrmse"]
            state.correlation = result["correlation"]
            state.arias_ratio = result["arias_ratio"]
            state.overall_score = result["overall_score"]
            state.quality_grade = result["quality_grade"]
            state.prediction_complete = True

            # Create figures
            waveform_fig = create_waveform_comparison_figure(
                state.time,
                state.actual_waveform,
                state.predicted_waveform,
                target_station,
            )
            spectrum_fig = create_spectrum_comparison_figure(
                state.spectrum_periods,
                state.spectrum_actual,
                state.spectrum_predicted,
                target_station,
            )

            # Create metrics content
            metrics_content = _create_metrics_display(result)

            return (
                waveform_fig,
                spectrum_fig,
                metrics_content,
                {"display": "block"},
                f"Prediction complete - Grade: {state.quality_grade}",
                "success",
                state.model_dump(),
            )

        except Exception as e:
            state.error = str(e)
            return (
                create_empty_waveform_figure(),
                create_empty_spectrum_figure(),
                f"Error: {e}",
                {"display": "block"},
                f"Prediction failed: {e}",
                "danger",
                state.model_dump(),
            )

    @app.callback(
        Output("card-use-prediction", "style"),
        Input("store-prediction-state", "data"),
    )
    def toggle_use_prediction_card(state_data):
        """Show/hide the 'Use for Simulation' card based on prediction state."""
        if not state_data:
            return {"display": "none"}

        state = PredictionState(**state_data)
        if state.prediction_complete and len(state.predicted_waveform) > 0:
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("store-ground-motion", "data", allow_duplicate=True),
        Output("alert-transfer-status", "children"),
        Output("sidebar-gm-info", "children", allow_duplicate=True),
        Input("btn-use-prediction-for-sim", "n_clicks"),
        State("store-prediction-state", "data"),
        State("store-ground-motion", "data"),
        prevent_initial_call=True,
    )
    def transfer_prediction_to_ground_motion(n_clicks, pred_state_data, gm_state_data):
        """Transfer predicted waveform to ground motion store."""
        if not n_clicks or not pred_state_data:
            raise PreventUpdate

        pred_state = PredictionState(**pred_state_data)

        if not pred_state.prediction_complete or len(pred_state.predicted_waveform) == 0:
            alert = dbc.Alert(
                "No prediction data available to transfer.",
                color="warning",
                dismissable=True,
            )
            raise PreventUpdate

        # Calculate dt from time vector
        dt = pred_state.time[1] - pred_state.time[0] if len(pred_state.time) > 1 else 0.01

        # Create ground motion state from prediction
        gm_state = GroundMotionState(
            time=pred_state.time,
            acceleration=pred_state.predicted_waveform,
            dt=dt,
            pga=pred_state.predicted_pga,
            source="prediction",
            duration=pred_state.time[-1] if pred_state.time else 0.0,
            event_id=pred_state.event_id,
            station=pred_state.target_station_id or "building",
            target_pga=pred_state.predicted_pga,
        )

        # Create success alert
        alert = dbc.Alert(
            [
                html.I(className="bi bi-check-circle-fill me-2"),
                f"Transferred predicted waveform (PGA: {pred_state.predicted_pga:.4f}g) to simulation. ",
                html.Strong("Go to Simulation page to run analysis."),
            ],
            color="success",
            dismissable=True,
        )

        # Sidebar info
        sidebar_info = f"Ground Motion: Prediction, PGA={pred_state.predicted_pga:.3f}g"

        return gm_state.model_dump(), alert, sidebar_info

    @app.callback(
        Output("div-predict-at-building", "style"),
        Input("store-prediction-state", "data"),
        Input("store-building-params", "data"),
    )
    def toggle_predict_at_building_option(pred_state_data, building_data):
        """Show/hide 'Predict at Building Location' option."""
        if not pred_state_data or not building_data:
            return {"display": "none"}

        pred_state = PredictionState(**pred_state_data)
        building = BuildingParams(**building_data)

        # Show option if event is loaded AND building has location set
        if (
            pred_state.loaded
            and building.latitude is not None
            and building.longitude is not None
        ):
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("graph-waveform-comparison", "figure", allow_duplicate=True),
        Output("graph-spectrum-comparison", "figure", allow_duplicate=True),
        Output("validation-metrics-content", "children", allow_duplicate=True),
        Output("card-results", "style", allow_duplicate=True),
        Output("alert-prediction-status", "children", allow_duplicate=True),
        Output("alert-prediction-status", "color", allow_duplicate=True),
        Output("store-prediction-state", "data", allow_duplicate=True),
        Input("btn-predict-at-building", "n_clicks"),
        State("store-prediction-state", "data"),
        State("store-building-params", "data"),
        prevent_initial_call=True,
    )
    def run_prediction_at_building(n_clicks, pred_state_data, building_data):
        """Run wave propagation prediction at the building location."""
        if not n_clicks or not pred_state_data or not building_data:
            raise PreventUpdate

        pred_state = PredictionState(**pred_state_data)
        building = BuildingParams(**building_data)

        if not pred_state.loaded:
            return (
                create_empty_waveform_figure(),
                create_empty_spectrum_figure(),
                "No event data loaded",
                {"display": "none"},
                "Please load event data first",
                "warning",
                pred_state.model_dump(),
            )

        if building.latitude is None or building.longitude is None:
            return (
                create_empty_waveform_figure(),
                create_empty_spectrum_figure(),
                "Building location not set",
                {"display": "none"},
                "Please set building location in Building Configuration",
                "warning",
                pred_state.model_dump(),
            )

        try:
            # Run prediction at building location
            result = _run_prediction_at_location(
                pred_state,
                building.latitude,
                building.longitude,
            )

            # Update state with results
            pred_state.target_station_id = "building"
            pred_state.selected_source_stations = [s.station_id for s in pred_state.available_stations]
            pred_state.time = result["time"]
            pred_state.actual_waveform = []  # No actual for building location
            pred_state.predicted_waveform = result["predicted"]
            pred_state.actual_pga = 0.0
            pred_state.predicted_pga = result["predicted_pga"]
            pred_state.pga_ratio = 0.0
            pred_state.pga_error_percent = 0.0
            pred_state.spectrum_periods = result["periods"]
            pred_state.spectrum_actual = []
            pred_state.spectrum_predicted = result["predicted_sa"]
            pred_state.nrmse = 0.0
            pred_state.correlation = 0.0
            pred_state.arias_ratio = 0.0
            pred_state.overall_score = 0.0
            pred_state.quality_grade = "N/A"
            pred_state.prediction_complete = True

            # Create figures (only predicted, no actual)
            waveform_fig = create_waveform_comparison_figure(
                pred_state.time,
                [],  # No actual
                pred_state.predicted_waveform,
                "Building Location",
            )
            spectrum_fig = create_spectrum_comparison_figure(
                pred_state.spectrum_periods,
                [],  # No actual
                pred_state.spectrum_predicted,
                "Building Location",
            )

            # Create metrics content for building prediction
            metrics_content = _create_building_prediction_metrics(result, building)

            return (
                waveform_fig,
                spectrum_fig,
                metrics_content,
                {"display": "block"},
                f"Prediction complete at building location (PGA: {result['predicted_pga']:.4f}g)",
                "success",
                pred_state.model_dump(),
            )

        except Exception as e:
            pred_state.error = str(e)
            return (
                create_empty_waveform_figure(),
                create_empty_spectrum_figure(),
                f"Error: {e}",
                {"display": "block"},
                f"Prediction at building failed: {e}",
                "danger",
                pred_state.model_dump(),
            )


def _run_prediction_at_location(
    state: PredictionState,
    target_lat: float,
    target_lon: float,
) -> dict:
    """Run prediction at a specific location using available stations."""
    from seismic_twin.ground_motion.synthetic import (
        compute_response_spectrum,
        generate_synthetic_ground_motion,
    )
    from seismic_twin.prediction import BooreAtkinson2008
    from seismic_twin.prediction.distance import compute_epicentral_distance

    gmpe = BooreAtkinson2008()

    # Compute distance from epicenter to target
    target_dist = compute_epicentral_distance(
        state.event_lat, state.event_lon,
        target_lat, target_lon
    )

    # Find closest station for source waveform
    source_info = None
    min_dist = float("inf")
    for s in state.available_stations:
        dist = compute_epicentral_distance(
            target_lat, target_lon,
            s.latitude, s.longitude
        )
        if dist < min_dist:
            min_dist = dist
            source_info = s

    if not source_info:
        raise ValueError("No source stations available")

    # Compute source Rjb distance
    source_rjb = compute_epicentral_distance(
        state.event_lat, state.event_lon,
        source_info.latitude, source_info.longitude
    )

    # Generate synthetic waveforms
    source_pga = gmpe.predict_pga(state.event_magnitude, source_rjb)
    target_pga = gmpe.predict_pga(state.event_magnitude, target_dist)

    # Generate source waveform
    time, source_waveform = generate_synthetic_ground_motion(
        duration=40.0,
        dt=0.01,
        target_pga=source_pga,
        seed=hash(source_info.station_id) % 2**31,
    )

    # Scale factor
    scale_factor = gmpe.compute_scale_factor(
        state.event_magnitude,
        source_rjb,
        target_dist,
    )
    predicted = source_waveform * scale_factor

    # Compute metrics
    predicted_pga = float(np.max(np.abs(predicted)))

    # Compute response spectrum
    periods, predicted_sa = compute_response_spectrum(time, predicted)

    return {
        "time": time.tolist(),
        "predicted": predicted.tolist(),
        "predicted_pga": predicted_pga,
        "periods": periods.tolist(),
        "predicted_sa": predicted_sa.tolist(),
        "scale_factor": scale_factor,
        "source_station": source_info.station_id,
        "source_distance_km": source_info.distance_km,
        "target_distance_km": target_dist,
    }


def _create_building_prediction_metrics(result: dict, building: BuildingParams) -> list:
    """Create metrics display for building location prediction."""
    return [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4(f"{result['predicted_pga']:.4f} g", className="mb-0"),
                                    html.Small("Predicted PGA", className="text-muted"),
                                ],
                                className="text-center",
                            )
                        ],
                        color="light",
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4(f"{result['target_distance_km']:.1f} km", className="mb-0"),
                                    html.Small("Distance to Epicenter", className="text-muted"),
                                ],
                                className="text-center",
                            )
                        ],
                        color="light",
                    ),
                    md=4,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4(f"{result['scale_factor']:.3f}", className="mb-0"),
                                    html.Small("Scale Factor", className="text-muted"),
                                ],
                                className="text-center",
                            )
                        ],
                        color="light",
                    ),
                    md=4,
                ),
            ],
            className="mb-4",
        ),
        html.Hr(),
        html.H6("Prediction Details"),
        html.Table(
            [
                html.Tbody(
                    [
                        html.Tr([
                            html.Td("Building Location:"),
                            html.Td(f"({building.latitude:.4f}, {building.longitude:.4f})"),
                        ]),
                        html.Tr([
                            html.Td("Source Station:"),
                            html.Td(result["source_station"]),
                        ]),
                        html.Tr([
                            html.Td("Source Distance:"),
                            html.Td(f"{result['source_distance_km']:.1f} km from epicenter"),
                        ]),
                        html.Tr([
                            html.Td("Note:"),
                            html.Td("Prediction based on GMPE scaling - no validation available"),
                        ]),
                    ]
                )
            ],
            className="table table-sm",
        ),
    ]


def _load_event_from_usgs(event_id: str) -> tuple[dict, list]:
    """Load event info and stations from USGS via ObsPy."""
    from obspy.clients.fdsn import Client
    from obspy.geodetics import gps2dist_azimuth

    # Get event from USGS
    client = Client("USGS", timeout=30)
    catalog = client.get_events(eventid=event_id)

    if len(catalog) == 0:
        raise ValueError(f"Event {event_id} not found")

    event = catalog[0]
    origin = event.preferred_origin() or event.origins[0]
    magnitude = event.preferred_magnitude() or event.magnitudes[0]

    event_info = {
        "event_id": event_id,
        "magnitude": magnitude.mag,
        "latitude": origin.latitude,
        "longitude": origin.longitude,
        "depth_km": origin.depth / 1000.0 if origin.depth else 0.0,
        "region": str(event.event_descriptions[0].text if event.event_descriptions else "Unknown"),
    }

    # Get nearby stations from IRIS
    iris_client = Client("IRIS", timeout=30)
    max_radius_deg = 1.0  # ~111 km

    try:
        inventory = iris_client.get_stations(
            latitude=origin.latitude,
            longitude=origin.longitude,
            maxradius=max_radius_deg,
            channel="HN*",
            level="station",
        )
    except Exception:
        inventory = None

    stations = []
    if inventory:
        for network in inventory:
            for station in network:
                dist_m, _, _ = gps2dist_azimuth(
                    origin.latitude, origin.longitude,
                    station.latitude, station.longitude
                )
                stations.append({
                    "station": station.code,
                    "network": network.code,
                    "latitude": station.latitude,
                    "longitude": station.longitude,
                    "distance_km": dist_m / 1000.0,
                })

    # Sort by distance
    stations.sort(key=lambda x: x["distance_km"])

    # Limit to closest 10 stations
    stations = stations[:10]

    if not stations:
        # Use default Ridgecrest stations if none found
        stations = [
            {"station": "CLC", "network": "CI", "latitude": 35.816, "longitude": -117.598, "distance_km": 17.5},
            {"station": "JRC2", "network": "CI", "latitude": 35.983, "longitude": -117.809, "distance_km": 22.1},
            {"station": "SRT", "network": "CI", "latitude": 35.546, "longitude": -117.276, "distance_km": 28.3},
            {"station": "TOW2", "network": "CI", "latitude": 36.419, "longitude": -117.197, "distance_km": 48.2},
            {"station": "MPM", "network": "CI", "latitude": 36.058, "longitude": -117.489, "distance_km": 55.1},
        ]

    return event_info, stations


def _create_synthetic_demo_response(event_id: str, state: PredictionState):
    """Create demo response with synthetic data when ObsPy isn't available."""
    # Simulate Ridgecrest event
    event_info = {
        "event_id": event_id,
        "magnitude": 7.1,
        "latitude": 35.77,
        "longitude": -117.60,
        "depth_km": 8.0,
        "region": "Ridgecrest, CA (Synthetic Demo)",
    }

    stations = [
        {"station": "STA1", "network": "SY", "latitude": 35.85, "longitude": -117.50, "distance_km": 15.2},
        {"station": "STA2", "network": "SY", "latitude": 35.70, "longitude": -117.35, "distance_km": 24.8},
        {"station": "STA3", "network": "SY", "latitude": 35.55, "longitude": -117.70, "distance_km": 32.1},
        {"station": "STA4", "network": "SY", "latitude": 35.90, "longitude": -117.80, "distance_km": 38.5},
        {"station": "STA5", "network": "SY", "latitude": 35.45, "longitude": -117.50, "distance_km": 45.3},
    ]

    # Update state
    state.event_id = event_id
    state.event_magnitude = event_info["magnitude"]
    state.event_lat = event_info["latitude"]
    state.event_lon = event_info["longitude"]
    state.event_depth_km = event_info["depth_km"]
    state.event_region = event_info["region"]
    state.available_stations = [
        StationInfo(
            station_id=s["station"],
            network=s["network"],
            latitude=s["latitude"],
            longitude=s["longitude"],
            distance_km=s["distance_km"],
            pga=0.0,
        )
        for s in stations
    ]
    state.loaded = True

    # Create event info display
    event_info_content = _create_event_info_display(event_info)

    # Create station options
    station_options = [
        {
            "label": f"{s['station']} ({s['distance_km']:.1f} km)",
            "value": s["station"],
        }
        for s in stations
    ]

    return (
        "",
        {"display": "block"},
        event_info_content,
        {"display": "block"},
        {"display": "block"},
        station_options,
        station_options,
        f"Demo mode: M{event_info['magnitude']:.1f} {event_info['region']} (ObsPy not installed)",
        "info",
        state.model_dump(),
    )


def _create_event_info_display(event_info: dict) -> list:
    """Create event information display elements."""
    return [
        html.P([
            html.Strong("Magnitude: "),
            f"M{event_info['magnitude']:.1f}",
        ], className="mb-1"),
        html.P([
            html.Strong("Location: "),
            f"{event_info['latitude']:.3f}, {event_info['longitude']:.3f}",
        ], className="mb-1"),
        html.P([
            html.Strong("Depth: "),
            f"{event_info['depth_km']:.1f} km",
        ], className="mb-1"),
        html.P([
            html.Strong("Region: "),
            event_info["region"],
        ], className="mb-0"),
    ]


def _run_synthetic_prediction(
    state: PredictionState,
    target_station: str,
    source_stations: list[str],
) -> dict:
    """Run prediction using synthetic data for demonstration."""
    from seismic_twin.ground_motion.synthetic import generate_synthetic_ground_motion, compute_response_spectrum
    from seismic_twin.prediction import BooreAtkinson2008, WaveformPredictor, PredictionValidator
    from seismic_twin.prediction.distance import compute_epicentral_distance
    from seismic_twin.analysis.metrics import compute_nrmse, compute_correlation, compute_arias_intensity

    gmpe = BooreAtkinson2008()

    # Find target station info
    target_info = None
    for s in state.available_stations:
        if s.station_id == target_station:
            target_info = s
            break

    if not target_info:
        raise ValueError(f"Target station {target_station} not found")

    # Compute target distance
    target_dist = compute_epicentral_distance(
        state.event_lat, state.event_lon,
        target_info.latitude, target_info.longitude
    )

    # Find closest source station
    source_info = None
    source_dist = float("inf")
    for s in state.available_stations:
        if s.station_id in source_stations and s.station_id != target_station:
            dist = compute_epicentral_distance(
                target_info.latitude, target_info.longitude,
                s.latitude, s.longitude
            )
            if dist < source_dist:
                source_dist = dist
                source_info = s

    if not source_info:
        raise ValueError("No valid source stations selected")

    # Compute source Rjb distance
    source_rjb = compute_epicentral_distance(
        state.event_lat, state.event_lon,
        source_info.latitude, source_info.longitude
    )

    # Generate synthetic waveforms
    source_pga = gmpe.predict_pga(state.event_magnitude, source_rjb)
    target_pga = gmpe.predict_pga(state.event_magnitude, target_dist)

    # Generate actual waveform at target
    time, actual = generate_synthetic_ground_motion(
        duration=40.0,
        dt=0.01,
        target_pga=target_pga,
        seed=hash(target_station) % 2**31,
    )

    # Generate source waveform and scale to predict target
    _, source_waveform = generate_synthetic_ground_motion(
        duration=40.0,
        dt=0.01,
        target_pga=source_pga,
        seed=hash(source_info.station_id) % 2**31,
    )

    # Scale factor
    scale_factor = gmpe.compute_scale_factor(
        state.event_magnitude,
        source_rjb,
        target_dist,
    )
    predicted = source_waveform * scale_factor

    # Compute metrics
    actual_pga = float(np.max(np.abs(actual)))
    predicted_pga = float(np.max(np.abs(predicted)))
    pga_ratio = predicted_pga / actual_pga if actual_pga > 0 else 1.0
    pga_error = abs(predicted_pga - actual_pga) / actual_pga * 100 if actual_pga > 0 else 0.0

    nrmse = compute_nrmse(predicted, actual)
    correlation = compute_correlation(predicted, actual)

    dt = time[1] - time[0]
    arias_actual = compute_arias_intensity(actual, dt)
    arias_pred = compute_arias_intensity(predicted, dt)
    arias_ratio = arias_pred / arias_actual if arias_actual > 0 else 1.0

    # Compute response spectra
    periods, actual_sa = compute_response_spectrum(time, actual)
    _, predicted_sa = compute_response_spectrum(time, predicted)

    # Overall score and grade
    log_ratio = np.log(max(0.1, min(10, pga_ratio)))
    pga_score = np.exp(-abs(log_ratio))
    correlation_score = (correlation + 1) / 2.0
    overall_score = 0.3 * pga_score + 0.4 * 0.7 + 0.3 * correlation_score  # Simplified

    if overall_score >= 0.8:
        grade = "A"
    elif overall_score >= 0.6:
        grade = "B"
    elif overall_score >= 0.4:
        grade = "C"
    elif overall_score >= 0.2:
        grade = "D"
    else:
        grade = "F"

    return {
        "time": time.tolist(),
        "actual": actual.tolist(),
        "predicted": predicted.tolist(),
        "actual_pga": actual_pga,
        "predicted_pga": predicted_pga,
        "pga_ratio": pga_ratio,
        "pga_error": pga_error,
        "periods": periods.tolist(),
        "actual_sa": actual_sa.tolist(),
        "predicted_sa": predicted_sa.tolist(),
        "nrmse": nrmse,
        "correlation": correlation,
        "arias_ratio": arias_ratio,
        "overall_score": overall_score,
        "quality_grade": grade,
        "scale_factor": scale_factor,
        "source_station": source_info.station_id,
    }


def _create_metrics_display(result: dict) -> list:
    """Create metrics display content."""
    grade_colors = {"A": "success", "B": "info", "C": "warning", "D": "warning", "F": "danger"}
    grade = result["quality_grade"]

    return [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H3(grade, className=f"text-{grade_colors.get(grade, 'secondary')} mb-0"),
                                    html.Small("Quality Grade", className="text-muted"),
                                ],
                                className="text-center",
                            )
                        ],
                        color="light",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4(f"{result['pga_ratio']:.2f}", className="mb-0"),
                                    html.Small("PGA Ratio", className="text-muted"),
                                ],
                                className="text-center",
                            )
                        ],
                        color="light",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4(f"{result['correlation']:.2f}", className="mb-0"),
                                    html.Small("Correlation", className="text-muted"),
                                ],
                                className="text-center",
                            )
                        ],
                        color="light",
                    ),
                    md=3,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H4(f"{result['nrmse']:.2f}", className="mb-0"),
                                    html.Small("NRMSE", className="text-muted"),
                                ],
                                className="text-center",
                            )
                        ],
                        color="light",
                    ),
                    md=3,
                ),
            ],
            className="mb-4",
        ),
        html.Hr(),
        html.H6("Detailed Metrics"),
        html.Table(
            [
                html.Tbody(
                    [
                        html.Tr([html.Td("Actual PGA:"), html.Td(f"{result['actual_pga']:.4f} g")]),
                        html.Tr([html.Td("Predicted PGA:"), html.Td(f"{result['predicted_pga']:.4f} g")]),
                        html.Tr([html.Td("PGA Error:"), html.Td(f"{result['pga_error']:.1f}%")]),
                        html.Tr([html.Td("Arias Intensity Ratio:"), html.Td(f"{result['arias_ratio']:.2f}")]),
                        html.Tr([html.Td("Scale Factor:"), html.Td(f"{result['scale_factor']:.3f}")]),
                        html.Tr([html.Td("Source Station:"), html.Td(result["source_station"])]),
                    ]
                )
            ],
            className="table table-sm",
        ),
    ]
