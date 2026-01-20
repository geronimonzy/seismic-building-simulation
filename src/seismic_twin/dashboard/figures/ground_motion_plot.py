"""Ground motion time history plot."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_ground_motion_figure(
    time: list[float] | np.ndarray,
    acceleration: list[float] | np.ndarray,
    title: str = "Ground Motion",
    show_pga: bool = True,
    show_rangeslider: bool = True,
) -> go.Figure:
    """
    Create an interactive ground motion time history plot.

    Parameters
    ----------
    time : array-like
        Time vector in seconds.
    acceleration : array-like
        Acceleration time history in g.
    title : str
        Plot title.
    show_pga : bool
        If True, show PGA marker and annotation.
    show_rangeslider : bool
        If True, add a range slider for zooming.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    time = np.asarray(time)
    acceleration = np.asarray(acceleration)

    if len(time) == 0 or len(acceleration) == 0:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No ground motion data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            title=title,
            xaxis_title="Time (s)",
            yaxis_title="Acceleration (g)",
            template="plotly_white",
        )
        return fig

    # Create figure
    fig = go.Figure()

    # Add acceleration trace
    fig.add_trace(
        go.Scatter(
            x=time,
            y=acceleration,
            mode="lines",
            name="Acceleration",
            line=dict(color="#1f77b4", width=1),
            hovertemplate="Time: %{x:.2f} s<br>Acc: %{y:.4f} g<extra></extra>",
        )
    )

    # Add PGA marker
    if show_pga and len(acceleration) > 0:
        pga = np.max(np.abs(acceleration))
        pga_idx = np.argmax(np.abs(acceleration))
        pga_time = time[pga_idx]
        pga_value = acceleration[pga_idx]

        fig.add_trace(
            go.Scatter(
                x=[pga_time],
                y=[pga_value],
                mode="markers",
                name=f"PGA = {pga:.3f} g",
                marker=dict(color="red", size=10, symbol="diamond"),
                hovertemplate=f"PGA: {pga:.4f} g<br>Time: {pga_time:.2f} s<extra></extra>",
            )
        )

        # Add horizontal line at PGA level
        fig.add_hline(
            y=pga,
            line_dash="dash",
            line_color="red",
            opacity=0.5,
            annotation_text=f"PGA = {pga:.3f} g",
            annotation_position="top right",
        )
        fig.add_hline(
            y=-pga,
            line_dash="dash",
            line_color="red",
            opacity=0.5,
        )

    # Update layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Time (s)",
        yaxis_title="Acceleration (g)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=60, r=40, t=60, b=60),
    )

    # Add range slider
    if show_rangeslider:
        fig.update_xaxes(
            rangeslider=dict(visible=True, thickness=0.05),
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=5, label="5s", step="second", stepmode="backward"),
                        dict(count=10, label="10s", step="second", stepmode="backward"),
                        dict(count=20, label="20s", step="second", stepmode="backward"),
                        dict(step="all", label="All"),
                    ]
                )
            ),
        )

    return fig


def create_response_spectrum_figure(
    periods: list[float] | np.ndarray,
    sa: list[float] | np.ndarray,
    title: str = "Response Spectrum",
    building_periods: list[float] | None = None,
) -> go.Figure:
    """
    Create a response spectrum plot.

    Parameters
    ----------
    periods : array-like
        Natural periods in seconds.
    sa : array-like
        Spectral acceleration in g.
    title : str
        Plot title.
    building_periods : list, optional
        Building natural periods to mark on the plot.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    periods = np.asarray(periods)
    sa = np.asarray(sa)

    fig = go.Figure()

    # Add spectrum trace
    fig.add_trace(
        go.Scatter(
            x=periods,
            y=sa,
            mode="lines",
            name="Sa",
            line=dict(color="#1f77b4", width=2),
            hovertemplate="T: %{x:.3f} s<br>Sa: %{y:.3f} g<extra></extra>",
        )
    )

    # Mark building periods
    if building_periods:
        for i, T in enumerate(building_periods):
            # Interpolate Sa at building period
            sa_at_T = np.interp(T, periods, sa)
            fig.add_trace(
                go.Scatter(
                    x=[T],
                    y=[sa_at_T],
                    mode="markers",
                    name=f"Mode {i + 1} (T={T:.2f}s)",
                    marker=dict(size=10, symbol="circle"),
                )
            )
            fig.add_vline(
                x=T,
                line_dash="dot",
                opacity=0.5,
                annotation_text=f"T{i + 1}",
                annotation_position="top",
            )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Period (s)",
        yaxis_title="Spectral Acceleration (g)",
        xaxis_type="log",
        yaxis_type="log",
        template="plotly_white",
        margin=dict(l=60, r=40, t=60, b=60),
    )

    return fig
