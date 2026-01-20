"""Ground motion configuration page layout."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from seismic_twin.dashboard.layouts.base import create_page_header
from seismic_twin.dashboard.presets import get_ground_motion_preset_options


def create_ground_motion_layout() -> html.Div:
    """Create the ground motion configuration page layout."""
    return html.Div(
        [
            create_page_header(
                "Ground Motion",
                "Generate synthetic ground motion or fetch real earthquake records",
            ),
            dbc.Row(
                [
                    # Left column: Input controls
                    dbc.Col(
                        [
                            dbc.Tabs(
                                [
                                    # Synthetic ground motion tab
                                    dbc.Tab(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    # Preset selector
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Preset Scenario",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.Select(
                                                                id="select-gm-preset",
                                                                options=get_ground_motion_preset_options(),
                                                                value="custom",
                                                                className="mb-2",
                                                            ),
                                                            html.Div(
                                                                id="gm-preset-description",
                                                                className="text-muted small mb-2",
                                                            ),
                                                            # Import/Export buttons
                                                            dbc.ButtonGroup(
                                                                [
                                                                    dcc.Upload(
                                                                        id="upload-gm-preset",
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
                                                                        id="btn-export-gm",
                                                                        color="outline-secondary",
                                                                        size="sm",
                                                                    ),
                                                                ],
                                                                className="w-100",
                                                            ),
                                                            dcc.Download(id="download-gm-preset"),
                                                            html.Div(
                                                                id="gm-import-alert",
                                                                className="mt-2",
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Hr(),
                                                    # PGA
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Peak Ground Acceleration (PGA)",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.InputGroup(
                                                                [
                                                                    dbc.Input(
                                                                        id="input-target-pga",
                                                                        type="number",
                                                                        min=0.01,
                                                                        max=2.0,
                                                                        step=0.01,
                                                                        value=0.3,
                                                                    ),
                                                                    dbc.InputGroupText("g"),
                                                                ],
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Duration
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Duration",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.InputGroup(
                                                                [
                                                                    dbc.Input(
                                                                        id="input-duration",
                                                                        type="number",
                                                                        min=5,
                                                                        max=120,
                                                                        step=1,
                                                                        value=30,
                                                                    ),
                                                                    dbc.InputGroupText("s"),
                                                                ],
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Predominant frequency
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Predominant Frequency",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.InputGroup(
                                                                [
                                                                    dbc.Input(
                                                                        id="input-predominant-freq",
                                                                        type="number",
                                                                        min=0.1,
                                                                        max=20.0,
                                                                        step=0.1,
                                                                        value=2.0,
                                                                    ),
                                                                    dbc.InputGroupText("Hz"),
                                                                ],
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Bandwidth
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Bandwidth",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.InputGroup(
                                                                [
                                                                    dbc.Input(
                                                                        id="input-bandwidth",
                                                                        type="number",
                                                                        min=0.1,
                                                                        max=10.0,
                                                                        step=0.1,
                                                                        value=1.5,
                                                                    ),
                                                                    dbc.InputGroupText("Hz"),
                                                                ],
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Random seed
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Random Seed (optional)",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.Input(
                                                                id="input-seed",
                                                                type="number",
                                                                min=0,
                                                                placeholder="Leave empty for random",
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Hr(),
                                                    # Vertical component section
                                                    html.Div(
                                                        [
                                                            dbc.Checklist(
                                                                id="check-enable-vertical",
                                                                options=[
                                                                    {
                                                                        "label": "Generate Vertical Component",
                                                                        "value": "enabled",
                                                                    }
                                                                ],
                                                                value=[],
                                                                className="fw-bold mb-2",
                                                            ),
                                                            html.Div(
                                                                id="vertical-options",
                                                                children=[
                                                                    html.Label(
                                                                        "V/H Ratio",
                                                                        className="form-label",
                                                                    ),
                                                                    dbc.InputGroup(
                                                                        [
                                                                            dbc.Input(
                                                                                id="input-vh-ratio",
                                                                                type="number",
                                                                                min=0.3,
                                                                                max=1.0,
                                                                                step=0.01,
                                                                                value=0.67,
                                                                            ),
                                                                            dbc.InputGroupText(
                                                                                "typical: 0.5-0.75"
                                                                            ),
                                                                        ],
                                                                    ),
                                                                    dbc.FormText(
                                                                        "Vertical to horizontal PGA ratio"
                                                                    ),
                                                                ],
                                                                style={"display": "none"},
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Generate button
                                                    dbc.Button(
                                                        [
                                                            html.I(
                                                                className="bi bi-lightning me-2"
                                                            ),
                                                            "Generate Ground Motion",
                                                        ],
                                                        id="btn-generate-synthetic",
                                                        color="primary",
                                                        className="w-100",
                                                    ),
                                                ]
                                            ),
                                            className="border-0",
                                        ),
                                        label="Synthetic",
                                        tab_id="tab-synthetic",
                                    ),
                                    # Real earthquake tab
                                    dbc.Tab(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    dbc.Alert(
                                                        [
                                                            html.I(
                                                                className="bi bi-info-circle me-2"
                                                            ),
                                                            "Requires ",
                                                            html.Code(
                                                                "pip install seismic-twin[data]"
                                                            ),
                                                        ],
                                                        color="info",
                                                        className="mb-3",
                                                    ),
                                                    # Event search
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Earthquake Event ID",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.Input(
                                                                id="input-event-id",
                                                                type="text",
                                                                placeholder="e.g., ci38457511",
                                                            ),
                                                            dbc.FormText(
                                                                "SCEDC event ID or USGS event code"
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Station
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Station Code (optional)",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.Input(
                                                                id="input-station",
                                                                type="text",
                                                                placeholder="e.g., CI.PAS",
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Channel
                                                    html.Div(
                                                        [
                                                            html.Label(
                                                                "Channel",
                                                                className="form-label fw-bold",
                                                            ),
                                                            dbc.Select(
                                                                id="select-channel",
                                                                options=[
                                                                    {
                                                                        "label": "HNE (East)",
                                                                        "value": "HNE",
                                                                    },
                                                                    {
                                                                        "label": "HNN (North)",
                                                                        "value": "HNN",
                                                                    },
                                                                    {
                                                                        "label": "HNZ (Vertical)",
                                                                        "value": "HNZ",
                                                                    },
                                                                    {
                                                                        "label": "BHE",
                                                                        "value": "BHE",
                                                                    },
                                                                    {
                                                                        "label": "BHN",
                                                                        "value": "BHN",
                                                                    },
                                                                ],
                                                                value="HNE",
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Fetch button
                                                    dbc.Button(
                                                        [
                                                            html.I(
                                                                className="bi bi-cloud-download me-2"
                                                            ),
                                                            "Fetch Record",
                                                        ],
                                                        id="btn-fetch-real",
                                                        color="primary",
                                                        className="w-100",
                                                    ),
                                                    # Status message
                                                    html.Div(
                                                        id="fetch-status",
                                                        className="mt-3",
                                                    ),
                                                ]
                                            ),
                                            className="border-0",
                                        ),
                                        label="Real Earthquake",
                                        tab_id="tab-real",
                                    ),
                                ],
                                id="tabs-ground-motion",
                                active_tab="tab-synthetic",
                            ),
                        ],
                        md=5,
                        lg=4,
                    ),
                    # Right column: Preview plot
                    dbc.Col(
                        [
                            # Ground motion info card
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-info-circle me-2"),
                                                "Ground Motion Info",
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
                                                                "Source", className="text-muted"
                                                            ),
                                                            html.P(
                                                                id="display-gm-source",
                                                                className="font-monospace",
                                                                children="Not generated",
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.H6("PGA", className="text-muted"),
                                                            html.P(
                                                                id="display-gm-pga",
                                                                className="font-monospace",
                                                                children="-",
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.H6(
                                                                "Duration", className="text-muted"
                                                            ),
                                                            html.P(
                                                                id="display-gm-duration",
                                                                className="font-monospace",
                                                                children="-",
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                ]
                                            ),
                                            # Vertical PGA row (only shown if vertical exists)
                                            html.Div(
                                                id="vertical-pga-row",
                                                children=[
                                                    html.Hr(className="my-2"),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    html.H6(
                                                                        "Vertical PGA",
                                                                        className="text-muted",
                                                                    ),
                                                                    html.P(
                                                                        id="display-gm-pga-vertical",
                                                                        className="font-monospace",
                                                                        children="-",
                                                                    ),
                                                                ],
                                                                md=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    html.H6(
                                                                        "V/H Ratio",
                                                                        className="text-muted",
                                                                    ),
                                                                    html.P(
                                                                        id="display-gm-vh-ratio",
                                                                        className="font-monospace",
                                                                        children="-",
                                                                    ),
                                                                ],
                                                                md=4,
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                                style={"display": "none"},
                                            ),
                                        ]
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Ground motion plot
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            [
                                                html.I(className="bi bi-activity me-2"),
                                                "Time History Preview",
                                            ],
                                            className="mb-0",
                                        )
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Graph(
                                                id="graph-ground-motion",
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
