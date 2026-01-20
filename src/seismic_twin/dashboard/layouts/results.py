"""Results visualization page layout."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from seismic_twin.dashboard.layouts.base import create_page_header


def create_results_layout() -> html.Div:
    """Create the results visualization page layout."""
    return html.Div(
        [
            create_page_header(
                "Simulation Results",
                "Interactive visualization of seismic response analysis results",
            ),
            # Check if results are available
            html.Div(
                id="results-container",
                children=[
                    # Summary cards row
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H3(
                                                    id="results-pga",
                                                    className="mb-0 text-primary",
                                                ),
                                                html.Small(
                                                    "Peak Ground Acceleration (g)",
                                                    className="text-muted",
                                                ),
                                            ],
                                            className="text-center py-3",
                                        )
                                    ],
                                ),
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H3(
                                                    id="results-max-drift",
                                                    className="mb-0 text-warning",
                                                ),
                                                html.Small(
                                                    "Max Inter-Story Drift",
                                                    className="text-muted",
                                                ),
                                            ],
                                            className="text-center py-3",
                                        )
                                    ],
                                ),
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H3(
                                                    id="results-max-disp",
                                                    className="mb-0 text-info",
                                                ),
                                                html.Small(
                                                    "Max Roof Displacement (m)",
                                                    className="text-muted",
                                                ),
                                            ],
                                            className="text-center py-3",
                                        )
                                    ],
                                ),
                                md=3,
                            ),
                            dbc.Col(
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H3(
                                                    id="results-t1",
                                                    className="mb-0 text-success",
                                                ),
                                                html.Small(
                                                    "Fundamental Period (s)",
                                                    className="text-muted",
                                                ),
                                            ],
                                            className="text-center py-3",
                                        )
                                    ],
                                ),
                                md=3,
                            ),
                        ],
                        className="mb-4",
                    ),
                    # Tabs for different visualizations
                    dbc.Tabs(
                        [
                            # Time histories tab
                            dbc.Tab(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Select Floors",
                                                                className="form-label",
                                                            ),
                                                            dcc.Dropdown(
                                                                id="dropdown-floors",
                                                                multi=True,
                                                                placeholder="Select floors to display...",
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Response Type",
                                                                className="form-label",
                                                            ),
                                                            dbc.RadioItems(
                                                                id="radio-response-type",
                                                                options=[
                                                                    {
                                                                        "label": "All",
                                                                        "value": "all",
                                                                    },
                                                                    {
                                                                        "label": "Displacement",
                                                                        "value": "displacement",
                                                                    },
                                                                    {
                                                                        "label": "Velocity",
                                                                        "value": "velocity",
                                                                    },
                                                                    {
                                                                        "label": "Acceleration",
                                                                        "value": "acceleration",
                                                                    },
                                                                ],
                                                                value="all",
                                                                inline=True,
                                                            ),
                                                        ],
                                                        md=5,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                id="axis-selector-container",
                                                                children=[
                                                                    html.Label(
                                                                        "Direction",
                                                                        className="form-label",
                                                                    ),
                                                                    dbc.RadioItems(
                                                                        id="radio-axis-select",
                                                                        options=[
                                                                            {
                                                                                "label": "Horizontal (X)",
                                                                                "value": "horizontal",
                                                                            },
                                                                            {
                                                                                "label": "Vertical (Z)",
                                                                                "value": "vertical",
                                                                            },
                                                                            {
                                                                                "label": "Both",
                                                                                "value": "both",
                                                                            },
                                                                        ],
                                                                        value="horizontal",
                                                                        inline=True,
                                                                    ),
                                                                ],
                                                                style={"display": "none"},
                                                            ),
                                                        ],
                                                        md=3,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            dcc.Graph(
                                                id="graph-time-history",
                                                config={
                                                    "displayModeBar": True,
                                                    "displaylogo": False,
                                                    "toImageButtonOptions": {
                                                        "format": "png",
                                                        "filename": "time_history",
                                                        "scale": 2,
                                                    },
                                                },
                                                style={"height": "500px"},
                                            ),
                                        ]
                                    ),
                                    className="border-0",
                                ),
                                label="Time Histories",
                                tab_id="tab-time-history",
                            ),
                            # Drift profile tab
                            dbc.Tab(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Checklist(
                                                                id="check-show-limits",
                                                                options=[
                                                                    {
                                                                        "label": "Show performance limits",
                                                                        "value": "show",
                                                                    }
                                                                ],
                                                                value=["show"],
                                                                inline=True,
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                id="drift-axis-selector-container",
                                                                children=[
                                                                    dbc.RadioItems(
                                                                        id="radio-drift-axis-select",
                                                                        options=[
                                                                            {
                                                                                "label": "Horizontal Drift",
                                                                                "value": "horizontal",
                                                                            },
                                                                            {
                                                                                "label": "Vertical (Axial Strain)",
                                                                                "value": "vertical",
                                                                            },
                                                                        ],
                                                                        value="horizontal",
                                                                        inline=True,
                                                                    ),
                                                                ],
                                                                style={"display": "none"},
                                                            ),
                                                        ],
                                                        md=6,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            dcc.Graph(
                                                id="graph-drift-profile",
                                                config={
                                                    "displayModeBar": True,
                                                    "displaylogo": False,
                                                    "toImageButtonOptions": {
                                                        "format": "png",
                                                        "filename": "drift_profile",
                                                        "scale": 2,
                                                    },
                                                },
                                                style={"height": "500px"},
                                            ),
                                        ]
                                    ),
                                    className="border-0",
                                ),
                                label="Drift Profile",
                                tab_id="tab-drift",
                            ),
                            # Animation tab
                            dbc.Tab(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Displacement Scale",
                                                                className="form-label",
                                                            ),
                                                            dcc.Slider(
                                                                id="slider-animation-scale",
                                                                min=10,
                                                                max=200,
                                                                step=10,
                                                                value=50,
                                                                marks={
                                                                    10: "10x",
                                                                    50: "50x",
                                                                    100: "100x",
                                                                    200: "200x",
                                                                },
                                                                tooltip={
                                                                    "placement": "bottom",
                                                                    "always_visible": False,
                                                                },
                                                            ),
                                                        ],
                                                        md=4,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Label(
                                                                "Display Options",
                                                                className="form-label",
                                                            ),
                                                            dbc.Checklist(
                                                                id="check-animation-options",
                                                                options=[
                                                                    {
                                                                        "label": "Undeformed",
                                                                        "value": "undeformed",
                                                                    },
                                                                    {
                                                                        "label": "Labels",
                                                                        "value": "labels",
                                                                    },
                                                                    {
                                                                        "label": "Wave",
                                                                        "value": "wave",
                                                                    },
                                                                ],
                                                                value=[
                                                                    "undeformed",
                                                                    "labels",
                                                                    "wave",
                                                                ],
                                                                inline=True,
                                                            ),
                                                        ],
                                                        md=8,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            dcc.Graph(
                                                id="graph-building-animation",
                                                config={
                                                    "displayModeBar": True,
                                                    "displaylogo": False,
                                                    "toImageButtonOptions": {
                                                        "format": "png",
                                                        "filename": "building_animation",
                                                        "scale": 2,
                                                    },
                                                },
                                                style={"height": "550px"},
                                            ),
                                        ]
                                    ),
                                    className="border-0",
                                ),
                                label="Animation",
                                tab_id="tab-animation",
                            ),
                            # Uncertainty tab (only if MC was enabled)
                            dbc.Tab(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                id="uncertainty-content",
                                                children=[
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    html.Label(
                                                                        "Floor",
                                                                        className="form-label",
                                                                    ),
                                                                    dcc.Dropdown(
                                                                        id="dropdown-uncertainty-floor",
                                                                        placeholder="Select floor...",
                                                                    ),
                                                                ],
                                                                md=4,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                dcc.Graph(
                                                                    id="graph-uncertainty-band",
                                                                    config={
                                                                        "displayModeBar": True,
                                                                        "displaylogo": False,
                                                                    },
                                                                    style={"height": "400px"},
                                                                ),
                                                                md=8,
                                                            ),
                                                            dbc.Col(
                                                                dcc.Graph(
                                                                    id="graph-drift-distribution",
                                                                    config={
                                                                        "displayModeBar": True,
                                                                        "displaylogo": False,
                                                                    },
                                                                    style={"height": "400px"},
                                                                ),
                                                                md=4,
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="no-mc-message",
                                                children=[
                                                    dbc.Alert(
                                                        [
                                                            html.I(
                                                                className="bi bi-info-circle me-2"
                                                            ),
                                                            "Monte Carlo analysis was not enabled. ",
                                                            "Re-run the simulation with MC enabled to see uncertainty bounds.",
                                                        ],
                                                        color="info",
                                                    ),
                                                ],
                                                style={"display": "none"},
                                            ),
                                        ]
                                    ),
                                    className="border-0",
                                ),
                                label="Uncertainty",
                                tab_id="tab-uncertainty",
                            ),
                            # Energy Balance tab
                            dbc.Tab(
                                dbc.Card(
                                    dbc.CardBody(
                                        [
                                            html.Div(
                                                id="energy-content",
                                                children=[
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    html.Label(
                                                                        "Energy Components",
                                                                        className="form-label",
                                                                    ),
                                                                    dbc.Checklist(
                                                                        id="check-energy-components",
                                                                        options=[
                                                                            {
                                                                                "label": "Kinetic",
                                                                                "value": "kinetic",
                                                                            },
                                                                            {
                                                                                "label": "Strain",
                                                                                "value": "strain",
                                                                            },
                                                                            {
                                                                                "label": "Damping",
                                                                                "value": "damping",
                                                                            },
                                                                            {
                                                                                "label": "Input",
                                                                                "value": "input",
                                                                            },
                                                                        ],
                                                                        value=[
                                                                            "kinetic",
                                                                            "strain",
                                                                            "damping",
                                                                            "input",
                                                                        ],
                                                                        inline=True,
                                                                    ),
                                                                ],
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dcc.Graph(
                                                        id="graph-energy-balance",
                                                        config={
                                                            "displayModeBar": True,
                                                            "displaylogo": False,
                                                            "toImageButtonOptions": {
                                                                "format": "png",
                                                                "filename": "energy_balance",
                                                                "scale": 2,
                                                            },
                                                        },
                                                        style={"height": "500px"},
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="no-energy-message",
                                                children=[
                                                    dbc.Alert(
                                                        [
                                                            html.I(
                                                                className="bi bi-info-circle me-2"
                                                            ),
                                                            "Energy balance data not available. ",
                                                            "Re-run simulation to compute energy balance.",
                                                        ],
                                                        color="info",
                                                    ),
                                                ],
                                                style={"display": "none"},
                                            ),
                                        ]
                                    ),
                                    className="border-0",
                                ),
                                label="Energy Balance",
                                tab_id="tab-energy",
                            ),
                        ],
                        id="tabs-results",
                        active_tab="tab-time-history",
                    ),
                ],
            ),
            # No results message
            html.Div(
                id="no-results-message",
                children=[
                    dbc.Alert(
                        [
                            html.I(className="bi bi-exclamation-triangle me-2"),
                            "No simulation results available. Please ",
                            html.A("run a simulation", href="/simulation"),
                            " first.",
                        ],
                        color="warning",
                        className="mt-4",
                    ),
                ],
                style={"display": "none"},
            ),
        ]
    )
