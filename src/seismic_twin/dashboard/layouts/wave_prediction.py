"""Wave Prediction page layout."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from seismic_twin.dashboard.layouts.base import create_page_header


def create_wave_prediction_layout() -> html.Div:
    """Create the wave prediction page layout."""
    return html.Div(
        [
            create_page_header(
                "Wave Propagation Prediction",
                "Predict ground motion at target locations using GMPE-based scaling",
            ),
            dbc.Row(
                [
                    # Left column: Configuration
                    dbc.Col(
                        [
                            # Event Selection Card
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-lightning me-2"),
                                                "Event Selection",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Event ID input
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Event ID",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.Input(
                                                                id="input-event-id",
                                                                type="text",
                                                                placeholder="e.g., ci38457511",
                                                                value="ci38457511",
                                                            ),
                                                            dbc.Button(
                                                                "Load",
                                                                id="btn-load-event",
                                                                color="primary",
                                                            ),
                                                        ],
                                                    ),
                                                    dbc.FormText(
                                                        "Enter USGS event ID (e.g., ci38457511 for 2019 Ridgecrest M7.1)"
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Loading indicator
                                            dcc.Loading(
                                                id="loading-event",
                                                type="default",
                                                children=html.Div(id="event-loading-placeholder"),
                                            ),
                                            # Event info display
                                            html.Div(
                                                id="event-info-display",
                                                style={"display": "none"},
                                                children=[
                                                    html.Hr(),
                                                    html.H6("Event Information"),
                                                    html.Div(id="event-info-content"),
                                                ],
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Station Selection Card
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-broadcast-pin me-2"),
                                                "Station Selection",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Target station
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Target Station (to predict)",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="dropdown-target-station",
                                                        placeholder="Select target station...",
                                                        clearable=True,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Source stations
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Source Stations (for prediction)",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dbc.Checklist(
                                                        id="checklist-source-stations",
                                                        options=[],
                                                        value=[],
                                                        className="station-checklist",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Quick selection buttons
                                            html.Div(
                                                [
                                                    dbc.ButtonGroup(
                                                        [
                                                            dbc.Button(
                                                                "Select All",
                                                                id="btn-select-all-stations",
                                                                color="secondary",
                                                                size="sm",
                                                                outline=True,
                                                            ),
                                                            dbc.Button(
                                                                "Clear",
                                                                id="btn-clear-stations",
                                                                color="secondary",
                                                                size="sm",
                                                                outline=True,
                                                            ),
                                                        ],
                                                        size="sm",
                                                    ),
                                                ],
                                            ),
                                            # Predict at Building Location option
                                            html.Div(
                                                [
                                                    html.Hr(),
                                                    dbc.Alert(
                                                        [
                                                            html.I(className="bi bi-building me-2"),
                                                            "Building location is set. You can predict ground motion directly at your building site.",
                                                        ],
                                                        color="info",
                                                        className="py-2 mb-2",
                                                    ),
                                                    dbc.Button(
                                                        [
                                                            html.I(
                                                                className="bi bi-geo-alt-fill me-2"
                                                            ),
                                                            "Predict at Building Location",
                                                        ],
                                                        id="btn-predict-at-building",
                                                        color="info",
                                                        className="w-100",
                                                    ),
                                                ],
                                                id="div-predict-at-building",
                                                style={"display": "none"},
                                            ),
                                        ]
                                    ),
                                ],
                                id="card-station-selection",
                                className="mb-3",
                                style={"display": "none"},
                            ),
                            # Run Prediction Card
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(className="bi bi-play-fill me-2"),
                                                    "Run Prediction",
                                                ],
                                                id="btn-run-prediction",
                                                color="success",
                                                size="lg",
                                                className="w-100",
                                                disabled=True,
                                            ),
                                        ]
                                    ),
                                ],
                                id="card-run-prediction",
                                style={"display": "none"},
                            ),
                        ],
                        md=4,
                    ),
                    # Right column: Results
                    dbc.Col(
                        [
                            # Status card
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-info-circle me-2"),
                                                "Status",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.Alert(
                                                id="alert-prediction-status",
                                                children="Enter an event ID and click Load to begin.",
                                                color="info",
                                            ),
                                            dbc.Progress(
                                                id="progress-prediction",
                                                value=0,
                                                striped=True,
                                                animated=True,
                                                style={"display": "none"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Results tabs
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dbc.Tabs(
                                                [
                                                    dbc.Tab(
                                                        label="Time History",
                                                        tab_id="tab-waveform",
                                                        children=[
                                                            dcc.Loading(
                                                                dcc.Graph(
                                                                    id="graph-waveform-comparison",
                                                                    config={"displayModeBar": True},
                                                                    style={"height": "400px"},
                                                                ),
                                                            ),
                                                        ],
                                                    ),
                                                    dbc.Tab(
                                                        label="Response Spectrum",
                                                        tab_id="tab-spectrum",
                                                        children=[
                                                            dcc.Loading(
                                                                dcc.Graph(
                                                                    id="graph-spectrum-comparison",
                                                                    config={"displayModeBar": True},
                                                                    style={"height": "400px"},
                                                                ),
                                                            ),
                                                        ],
                                                    ),
                                                    dbc.Tab(
                                                        label="Validation Metrics",
                                                        tab_id="tab-metrics",
                                                        children=[
                                                            html.Div(
                                                                id="validation-metrics-content",
                                                                className="p-3",
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                                id="tabs-prediction-results",
                                                active_tab="tab-waveform",
                                            ),
                                        ]
                                    ),
                                ],
                                id="card-results",
                                style={"display": "none"},
                            ),
                            # Use for Simulation Card
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dbc.Alert(
                                                [
                                                    html.I(className="bi bi-check-circle me-2"),
                                                    "Prediction complete! Transfer this waveform to use as ground motion input for structural simulation.",
                                                ],
                                                color="success",
                                                className="mb-3",
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(className="bi bi-box-arrow-right me-2"),
                                                    "Use for Simulation",
                                                ],
                                                id="btn-use-prediction-for-sim",
                                                color="primary",
                                                size="lg",
                                                className="w-100",
                                            ),
                                            html.Div(
                                                id="alert-transfer-status",
                                                className="mt-3",
                                            ),
                                        ]
                                    ),
                                ],
                                id="card-use-prediction",
                                className="mt-3",
                                style={"display": "none"},
                            ),
                        ],
                        md=8,
                    ),
                ],
            ),
        ]
    )
