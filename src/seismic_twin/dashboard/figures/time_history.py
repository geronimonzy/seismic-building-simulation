"""Time history response plots."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# Color palette for floor traces
FLOOR_COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # olive
    "#17becf",  # cyan
]


def create_time_history_figure(
    time: list[float] | np.ndarray,
    displacement: list[list[float]] | np.ndarray,
    velocity: list[list[float]] | np.ndarray | None = None,
    acceleration: list[list[float]] | np.ndarray | None = None,
    selected_floors: list[int] | None = None,
    title: str = "Structural Response",
) -> go.Figure:
    """
    Create a multi-row time history plot showing displacement, velocity, and acceleration.

    Parameters
    ----------
    time : array-like
        Time vector in seconds.
    displacement : array-like
        Displacement time history (n_dof x n_steps) in meters.
    velocity : array-like, optional
        Velocity time history (n_dof x n_steps) in m/s.
    acceleration : array-like, optional
        Acceleration time history (n_dof x n_steps) in m/s^2 or g.
    selected_floors : list, optional
        Floor indices to display. If None, show all floors.
    title : str
        Plot title.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    time = np.asarray(time)
    displacement = np.asarray(displacement)

    if len(time) == 0 or displacement.size == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No simulation results available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title=title, template="plotly_white")
        return fig

    # Determine number of subplots
    n_rows = 1
    row_titles = ["Displacement (m)"]
    if velocity is not None:
        velocity = np.asarray(velocity)
        n_rows += 1
        row_titles.append("Velocity (m/s)")
    if acceleration is not None:
        acceleration = np.asarray(acceleration)
        n_rows += 1
        row_titles.append("Acceleration (g)")

    # Create subplots
    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=row_titles,
    )

    n_dof = displacement.shape[0]
    if selected_floors is None:
        selected_floors = list(range(n_dof))

    # Add traces for each floor
    for floor_idx in selected_floors:
        if floor_idx >= n_dof:
            continue

        color = FLOOR_COLORS[floor_idx % len(FLOOR_COLORS)]
        floor_name = f"Floor {floor_idx + 1}"

        # Displacement
        fig.add_trace(
            go.Scatter(
                x=time,
                y=displacement[floor_idx],
                mode="lines",
                name=floor_name,
                line=dict(color=color, width=1),
                legendgroup=floor_name,
                hovertemplate=f"{floor_name}<br>Time: %{{x:.2f}} s<br>Disp: %{{y:.4f}} m<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # Velocity
        row = 2
        if velocity is not None:
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=velocity[floor_idx],
                    mode="lines",
                    name=floor_name,
                    line=dict(color=color, width=1),
                    legendgroup=floor_name,
                    showlegend=False,
                    hovertemplate=f"{floor_name}<br>Time: %{{x:.2f}} s<br>Vel: %{{y:.4f}} m/s<extra></extra>",
                ),
                row=row,
                col=1,
            )
            row += 1

        # Acceleration
        if acceleration is not None:
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=acceleration[floor_idx],
                    mode="lines",
                    name=floor_name,
                    line=dict(color=color, width=1),
                    legendgroup=floor_name,
                    showlegend=False,
                    hovertemplate=f"{floor_name}<br>Time: %{{x:.2f}} s<br>Acc: %{{y:.4f}} g<extra></extra>",
                ),
                row=row,
                col=1,
            )

    # Update layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        template="plotly_white",
        hovermode="x unified",
        height=200 * n_rows + 100,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=60, r=40, t=80, b=60),
    )

    # Update x-axis label on bottom subplot only
    fig.update_xaxes(title_text="Time (s)", row=n_rows, col=1)

    return fig


def create_single_response_figure(
    time: list[float] | np.ndarray,
    response: list[list[float]] | np.ndarray,
    response_type: str = "Displacement",
    units: str = "m",
    selected_floors: list[int] | None = None,
    title: str | None = None,
) -> go.Figure:
    """
    Create a single response type time history plot.

    Parameters
    ----------
    time : array-like
        Time vector in seconds.
    response : array-like
        Response time history (n_dof x n_steps).
    response_type : str
        Type of response (for labeling).
    units : str
        Units for y-axis label.
    selected_floors : list, optional
        Floor indices to display.
    title : str, optional
        Plot title. Defaults to response_type.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    time = np.asarray(time)
    response = np.asarray(response)

    if title is None:
        title = f"{response_type} Time History"

    if len(time) == 0 or response.size == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title=title, template="plotly_white")
        return fig

    fig = go.Figure()

    n_dof = response.shape[0]
    if selected_floors is None:
        selected_floors = list(range(n_dof))

    for floor_idx in selected_floors:
        if floor_idx >= n_dof:
            continue

        color = FLOOR_COLORS[floor_idx % len(FLOOR_COLORS)]
        floor_name = f"Floor {floor_idx + 1}"

        fig.add_trace(
            go.Scatter(
                x=time,
                y=response[floor_idx],
                mode="lines",
                name=floor_name,
                line=dict(color=color, width=1.5),
                hovertemplate=f"{floor_name}<br>Time: %{{x:.2f}} s<br>{response_type}: %{{y:.4f}} {units}<extra></extra>",
            )
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Time (s)",
        yaxis_title=f"{response_type} ({units})",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=60, r=40, t=80, b=60),
    )

    return fig
