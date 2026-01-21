"""Building configuration page layout."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from seismic_twin.dashboard.layouts.base import create_page_header
from seismic_twin.dashboard.presets import get_building_preset_options


def create_building_layout() -> html.Div:
    """Create the building configuration page layout."""
    return html.Div(
        [
            create_page_header(
                "Building Configuration",
                "Configure the structural model parameters for seismic analysis",
            ),
            dbc.Row(
                [
                    # Left column: Input controls
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-sliders me-2"),
                                                "Model Parameters",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Preset selector
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Preset Configuration",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dbc.Select(
                                                        id="select-building-preset",
                                                        options=get_building_preset_options(),
                                                        value="custom",
                                                        className="mb-2",
                                                    ),
                                                    html.Div(
                                                        id="building-preset-description",
                                                        className="text-muted small mb-2",
                                                    ),
                                                    # Import/Export buttons
                                                    dbc.ButtonGroup(
                                                        [
                                                            dcc.Upload(
                                                                id="upload-building-preset",
                                                                children=dbc.Button(
                                                                    [
                                                                        html.I(
                                                                            className="bi bi-upload me-1"
                                                                        ),
                                                                        "Import JSON",
                                                                    ],
                                                                    color="outline-secondary",
                                                                    size="sm",
                                                                ),
                                                                accept=".json",
                                                            ),
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="bi bi-download me-1"
                                                                    ),
                                                                    "Export Current",
                                                                ],
                                                                id="btn-export-building",
                                                                color="outline-secondary",
                                                                size="sm",
                                                            ),
                                                        ],
                                                        className="w-100",
                                                    ),
                                                    dcc.Download(id="download-building-preset"),
                                                    html.Div(
                                                        id="building-import-alert",
                                                        className="mt-2",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Hr(),
                                            # Number of stories
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Number of Stories",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dbc.Input(
                                                        id="input-n-stories",
                                                        type="number",
                                                        min=1,
                                                        max=20,
                                                        step=1,
                                                        value=3,
                                                        className="mb-3",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Hr(),
                                            # Mass configuration
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Floor Mass",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dbc.Checklist(
                                                        id="check-uniform-mass",
                                                        options=[
                                                            {
                                                                "label": "Uniform mass per floor",
                                                                "value": "uniform",
                                                            }
                                                        ],
                                                        value=["uniform"],
                                                        className="mb-2",
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.Input(
                                                                id="input-mass-uniform",
                                                                type="number",
                                                                min=1000,
                                                                max=1e9,
                                                                value=100000,
                                                            ),
                                                            dbc.InputGroupText("kg"),
                                                        ],
                                                        className="mb-2",
                                                    ),
                                                    html.Div(
                                                        id="mass-per-floor-inputs",
                                                        style={"display": "none"},
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Hr(),
                                            # Stiffness configuration
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Inter-Story Stiffness",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dbc.Checklist(
                                                        id="check-uniform-stiffness",
                                                        options=[
                                                            {
                                                                "label": "Uniform stiffness per story",
                                                                "value": "uniform",
                                                            }
                                                        ],
                                                        value=["uniform"],
                                                        className="mb-2",
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.Input(
                                                                id="input-stiffness-uniform",
                                                                type="number",
                                                                min=1e4,
                                                                max=1e12,
                                                                value=1e8,
                                                            ),
                                                            dbc.InputGroupText("N/m"),
                                                        ],
                                                        className="mb-2",
                                                    ),
                                                    html.Div(
                                                        id="stiffness-per-story-inputs",
                                                        style={"display": "none"},
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Hr(),
                                            # Story height
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Story Height",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dbc.InputGroup(
                                                        [
                                                            dbc.Input(
                                                                id="input-story-height",
                                                                type="number",
                                                                min=2.0,
                                                                max=10.0,
                                                                step=0.1,
                                                                value=3.5,
                                                            ),
                                                            dbc.InputGroupText("m"),
                                                        ],
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Hr(),
                                            # Damping ratio
                                            html.Div(
                                                [
                                                    html.Label(
                                                        "Damping Ratio",
                                                        className="form-label fw-bold",
                                                    ),
                                                    dcc.Slider(
                                                        id="slider-damping-ratio",
                                                        min=0.01,
                                                        max=0.15,
                                                        step=0.005,
                                                        value=0.05,
                                                        marks={
                                                            0.02: "2%",
                                                            0.05: "5%",
                                                            0.10: "10%",
                                                            0.15: "15%",
                                                        },
                                                        tooltip={
                                                            "placement": "bottom",
                                                            "always_visible": True,
                                                        },
                                                    ),
                                                ],
                                                className="mb-4",
                                            ),
                                            # Update button
                                            dbc.Button(
                                                [
                                                    html.I(className="bi bi-arrow-clockwise me-2"),
                                                    "Update Model",
                                                ],
                                                id="btn-update-building",
                                                color="primary",
                                                className="w-100",
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Building Location Card (Optional)
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-geo-alt me-2"),
                                                "Building Location (Optional)",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.Alert(
                                                [
                                                    html.I(className="bi bi-info-circle me-2"),
                                                    "Set your building's location to enable ",
                                                    "ground motion prediction at this site.",
                                                ],
                                                color="info",
                                                className="py-2",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Latitude",
                                                                className="form-label",
                                                            ),
                                                            dbc.Input(
                                                                id="input-building-latitude",
                                                                type="number",
                                                                min=-90,
                                                                max=90,
                                                                step=0.001,
                                                                placeholder="e.g., 35.77",
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Longitude",
                                                                className="form-label",
                                                            ),
                                                            dbc.Input(
                                                                id="input-building-longitude",
                                                                type="number",
                                                                min=-180,
                                                                max=180,
                                                                step=0.001,
                                                                placeholder="e.g., -117.60",
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                ],
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                        md=5,
                        lg=4,
                    ),
                    # Right column: Visualization
                    dbc.Col(
                        [
                            # Modal properties card
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-info-circle me-2"),
                                                "Modal Properties",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.H6(
                                                                "Natural Periods",
                                                                className="text-muted",
                                                            ),
                                                            html.Div(
                                                                id="display-natural-periods",
                                                                className="font-monospace",
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.H6(
                                                                "Natural Frequencies",
                                                                className="text-muted",
                                                            ),
                                                            html.Div(
                                                                id="display-natural-frequencies",
                                                                className="font-monospace",
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Mode shapes plot
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-bar-chart me-2"),
                                                "Mode Shapes",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="graph-mode-shapes",
                                                config={
                                                    "displayModeBar": True,
                                                    "displaylogo": False,
                                                },
                                                style={"height": "400px"},
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
