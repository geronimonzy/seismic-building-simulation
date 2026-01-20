"""Results summary components."""

import dash_bootstrap_components as dbc
from dash import html


def create_results_summary_card(
    max_drift: float,
    max_displacement: float,
    max_acceleration: float,
    pga: float,
    t1: float | None = None,
) -> dbc.Card:
    """
    Create a summary card of simulation results.

    Parameters
    ----------
    max_drift : float
        Maximum inter-story drift ratio.
    max_displacement : float
        Maximum roof displacement in meters.
    max_acceleration : float
        Maximum floor acceleration in g.
    pga : float
        Peak ground acceleration in g.
    t1 : float, optional
        Fundamental period in seconds.

    Returns
    -------
    dbc.Card
        Results summary card component.
    """
    # Determine drift performance level
    if max_drift < 0.007:
        drift_color = "success"
        drift_level = "IO"
    elif max_drift < 0.025:
        drift_color = "warning"
        drift_level = "LS"
    else:
        drift_color = "danger"
        drift_level = "CP"

    items = [
        dbc.ListGroupItem(
            [
                html.Div(
                    [
                        html.Strong("Max Inter-Story Drift"),
                        dbc.Badge(drift_level, color=drift_color, className="ms-2"),
                    ],
                    className="d-flex justify-content-between align-items-center",
                ),
                html.Span(f"{max_drift:.4f} ({max_drift * 100:.2f}%)", className="text-muted"),
            ],
        ),
        dbc.ListGroupItem(
            [
                html.Strong("Max Roof Displacement"),
                html.Br(),
                html.Span(
                    f"{max_displacement:.4f} m ({max_displacement * 1000:.2f} mm)",
                    className="text-muted",
                ),
            ],
        ),
        dbc.ListGroupItem(
            [
                html.Strong("Max Floor Acceleration"),
                html.Br(),
                html.Span(f"{max_acceleration:.3f} g", className="text-muted"),
            ],
        ),
        dbc.ListGroupItem(
            [
                html.Strong("Peak Ground Acceleration"),
                html.Br(),
                html.Span(f"{pga:.3f} g", className="text-muted"),
            ],
        ),
    ]

    if t1 is not None:
        items.append(
            dbc.ListGroupItem(
                [
                    html.Strong("Fundamental Period"),
                    html.Br(),
                    html.Span(f"{t1:.3f} s ({1 / t1:.2f} Hz)", className="text-muted"),
                ],
            )
        )

    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [
                        html.I(className="bi bi-clipboard-data me-2"),
                        "Results Summary",
                    ],
                    className="mb-0",
                )
            ),
            dbc.ListGroup(items, flush=True),
        ]
    )


def create_mc_statistics_card(
    mean_drift: float,
    p5_drift: float,
    p95_drift: float,
    n_samples: int,
) -> dbc.Card:
    """
    Create a Monte Carlo statistics card.

    Parameters
    ----------
    mean_drift : float
        Mean maximum drift ratio.
    p5_drift : float
        5th percentile drift ratio.
    p95_drift : float
        95th percentile drift ratio.
    n_samples : int
        Number of MC samples.

    Returns
    -------
    dbc.Card
        MC statistics card component.
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [
                        html.I(className="bi bi-dice-3 me-2"),
                        "Monte Carlo Statistics",
                    ],
                    className="mb-0",
                )
            ),
            dbc.CardBody(
                [
                    html.P([html.Strong("Samples: "), f"{n_samples}"]),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H6("5th Percentile", className="text-muted"),
                                    html.H4(f"{p5_drift:.4f}"),
                                ],
                                className="text-center",
                            ),
                            dbc.Col(
                                [
                                    html.H6("Mean", className="text-muted"),
                                    html.H4(f"{mean_drift:.4f}"),
                                ],
                                className="text-center",
                            ),
                            dbc.Col(
                                [
                                    html.H6("95th Percentile", className="text-muted"),
                                    html.H4(f"{p95_drift:.4f}"),
                                ],
                                className="text-center",
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )
