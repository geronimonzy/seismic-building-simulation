"""Progress indicator components."""

import dash_bootstrap_components as dbc
from dash import html


def create_progress_indicator(
    progress: int = 0,
    status: str = "Ready",
    color: str = "primary",
) -> html.Div:
    """
    Create a progress indicator with status message.

    Parameters
    ----------
    progress : int
        Progress percentage (0-100).
    status : str
        Status message to display.
    color : str
        Bootstrap color class.

    Returns
    -------
    html.Div
        Progress indicator component.
    """
    return html.Div(
        [
            dbc.Progress(
                value=progress,
                striped=progress < 100,
                animated=progress < 100,
                color=color,
                className="mb-2",
                style={"height": "25px"},
            ),
            html.P(
                status,
                className="text-center text-muted small",
            ),
        ]
    )


def create_status_badge(status: str) -> dbc.Badge:
    """
    Create a status badge based on simulation state.

    Parameters
    ----------
    status : str
        Status string ('ready', 'running', 'completed', 'error').

    Returns
    -------
    dbc.Badge
        Bootstrap badge component.
    """
    color_map = {
        "ready": "secondary",
        "running": "primary",
        "completed": "success",
        "error": "danger",
    }
    icon_map = {
        "ready": "bi-circle",
        "running": "bi-hourglass-split",
        "completed": "bi-check-circle",
        "error": "bi-x-circle",
    }

    color = color_map.get(status, "secondary")
    icon = icon_map.get(status, "bi-circle")

    return dbc.Badge(
        [
            html.I(className=f"bi {icon} me-1"),
            status.capitalize(),
        ],
        color=color,
        className="me-2",
    )
