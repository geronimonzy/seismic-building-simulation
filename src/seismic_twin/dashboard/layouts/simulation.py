"""Simulation page layout."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from seismic_twin.dashboard.layouts.base import create_page_header


def create_simulation_layout() -> html.Div:
    """Create the simulation page layout."""
    return html.Div(
        [
            create_page_header(
                "Run Simulation",
                "Execute seismic analysis with optional Monte Carlo uncertainty quantification",
            ),
            dbc.Row(
                [
                    # Left column: Configuration
                    dbc.Col(
                        [
                            # Pre-flight checks
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-check2-square me-2"),
                                                "Pre-flight Checks",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                id="preflight-checks",
                                                children=[
                                                    dbc.ListGroup(
                                                        [
                                                            dbc.ListGroupItem(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-circle me-2",
                                                                        id="check-building-icon",
                                                                    ),
                                                                    "Building model configured",
                                                                ],
                                                                id="check-building",
                                                            ),
                                                            dbc.ListGroupItem(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-circle me-2",
                                                                        id="check-gm-icon",
                                                                    ),
                                                                    "Ground motion loaded",
                                                                ],
                                                                id="check-gm",
                                                            ),
                                                        ],
                                                        flush=True,
                                                    ),
                                                ],
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Monte Carlo options
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-dice-3 me-2"),
                                                "Monte Carlo Options",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.Checklist(
                                                id="check-enable-mc",
                                                options=[
                                                    {
                                                        "label": "Enable Monte Carlo Analysis",
                                                        "value": "enabled",
                                                    }
                                                ],
                                                value=[],
                                                className="mb-3",
                                            ),
                                            html.Div(
                                                id="mc-options",
                                                children=[
                                                    # Number of samples
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Number of Samples",
                                                                className="form-label",
                                                            ),
                                                            dbc.Input(
                                                                id="input-mc-samples",
                                                                type="number",
                                                                min=10,
                                                                max=1000,
                                                                step=10,
                                                                value=100,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Stiffness COV
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Stiffness COV",
                                                                className="form-label",
                                                            ),
                                                            dcc.Slider(
                                                                id="slider-stiffness-cov",
                                                                min=0,
                                                                max=0.3,
                                                                step=0.01,
                                                                value=0.05,
                                                                marks={
                                                                    0: "0%",
                                                                    0.1: "10%",
                                                                    0.2: "20%",
                                                                    0.3: "30%",
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": True,
                                                                },
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Damping COV
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Damping COV",
                                                                className="form-label",
                                                            ),
                                                            dcc.Slider(
                                                                id="slider-damping-cov",
                                                                min=0,
                                                                max=0.5,
                                                                step=0.01,
                                                                value=0.20,
                                                                marks={
                                                                    0: "0%",
                                                                    0.25: "25%",
                                                                    0.5: "50%",
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": True,
                                                                },
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Mass COV
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Mass COV",
                                                                className="form-label",
                                                            ),
                                                            dcc.Slider(
                                                                id="slider-mass-cov",
                                                                min=0,
                                                                max=0.2,
                                                                step=0.01,
                                                                value=0.0,
                                                                marks={
                                                                    0: "0%",
                                                                    0.1: "10%",
                                                                    0.2: "20%",
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": True,
                                                                },
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Random seed
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Random Seed",
                                                                className="form-label",
                                                            ),
                                                            dbc.Input(
                                                                id="input-mc-seed",
                                                                type="number",
                                                                value=42,
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                                style={"display": "none"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Run button
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(className="bi bi-play-fill me-2"),
                                                    "Run Simulation",
                                                ],
                                                id="btn-run-simulation",
                                                color="success",
                                                size="lg",
                                                className="w-100 mb-3",
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(className="bi bi-x-circle me-2"),
                                                    "Cancel",
                                                ],
                                                id="btn-cancel-simulation",
                                                color="danger",
                                                outline=True,
                                                className="w-100",
                                                style={"display": "none"},
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ],
                        md=5,
                        lg=4,
                    ),
                    # Right column: Status and progress
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-terminal me-2"),
                                                "Simulation Status",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Progress bar
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Progress",
                                                        className="form-label",
                                                    ),
                                                    dbc.Progress(
                                                        id="progress-simulation",
                                                        value=0,
                                                        striped=True,
                                                        animated=True,
                                                        className="mb-3",
                                                        style={"height": "25px"},
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Status message
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Status",
                                                        className="form-label",
                                                    ),
                                                    dbc.Alert(
                                                        id="alert-simulation-status",
                                                        children="Ready to run simulation",
                                                        color="secondary",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            # Results summary (shown after completion)
                                            html.Div(
                                                id="simulation-summary",
                                                style={"display": "none"},
                                                children=[
                                                    html.Hr(),
                                                    html.H6("Quick Summary", className="mb-3"),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                dbc.Card(
                                                                    [
                                                                        dbc.CardBody(
                                                                            [
                                                                                html.H4(
                                                                                    id="summary-max-drift",
                                                                                    className="mb-0",
                                                                                ),
                                                                                html.Small(
                                                                                    "Max Drift Ratio",
                                                                                    className="text-muted",
                                                                                ),
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
                                                                                html.H4(
                                                                                    id="summary-max-disp",
                                                                                    className="mb-0",
                                                                                ),
                                                                                html.Small(
                                                                                    "Max Roof Disp (m)",
                                                                                    className="text-muted",
                                                                                ),
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
                                                                                html.H4(
                                                                                    id="summary-max-acc",
                                                                                    className="mb-0",
                                                                                ),
                                                                                html.Small(
                                                                                    "Max Floor Acc (g)",
                                                                                    className="text-muted",
                                                                                ),
                                                                            ],
                                                                            className="text-center",
                                                                        )
                                                                    ],
                                                                    color="light",
                                                                ),
                                                                md=4,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Button(
                                                        [
                                                            html.I(
                                                                className="bi bi-graph-up me-2"
                                                            ),
                                                            "View Detailed Results",
                                                        ],
                                                        href="/results",
                                                        color="primary",
                                                        className="w-100",
                                                    ),
                                                ],
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ],
                        md=7,
                        lg=8,
                    ),
                ],
            ),
        ]
    )
