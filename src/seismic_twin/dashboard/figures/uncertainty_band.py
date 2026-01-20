"""Uncertainty band visualization."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


def create_uncertainty_figure(
    time: list[float] | np.ndarray,
    median: list[float] | np.ndarray,
    p5: list[float] | np.ndarray,
    p95: list[float] | np.ndarray,
    floor_idx: int = 0,
    response_type: str = "Displacement",
    units: str = "m",
    title: str | None = None,
) -> go.Figure:
    """
    Create a time history plot with uncertainty band (5th-95th percentile).

    Parameters
    ----------
    time : array-like
        Time vector in seconds.
    median : array-like
        Median (50th percentile) response. Shape (n_dof, n_steps) or (n_steps,).
    p5 : array-like
        5th percentile response.
    p95 : array-like
        95th percentile response.
    floor_idx : int
        Floor index to display (if multi-floor data).
    response_type : str
        Type of response for labeling.
    units : str
        Units for y-axis.
    title : str, optional
        Plot title.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    time = np.asarray(time)
    median = np.asarray(median)
    p5 = np.asarray(p5)
    p95 = np.asarray(p95)

    if title is None:
        title = f"{response_type} with Uncertainty (Floor {floor_idx + 1})"

    if len(time) == 0 or median.size == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No Monte Carlo results available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title=title, template="plotly_white")
        return fig

    # Extract single floor if multi-dimensional
    if median.ndim > 1:
        median = median[floor_idx]
        p5 = p5[floor_idx]
        p95 = p95[floor_idx]

    fig = go.Figure()

    # Add filled uncertainty band
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([time, time[::-1]]),
            y=np.concatenate([p5, p95[::-1]]),
            fill="toself",
            fillcolor="rgba(31, 119, 180, 0.3)",
            line=dict(color="rgba(255,255,255,0)"),
            name="90% CI (5th-95th)",
            hoverinfo="skip",
        )
    )

    # Add median line
    fig.add_trace(
        go.Scatter(
            x=time,
            y=median,
            mode="lines",
            name="Median",
            line=dict(color="#1f77b4", width=2),
            hovertemplate=f"Time: %{{x:.2f}} s<br>{response_type}: %{{y:.4f}} {units}<extra></extra>",
        )
    )

    # Add p5 and p95 lines (subtle)
    fig.add_trace(
        go.Scatter(
            x=time,
            y=p5,
            mode="lines",
            name="5th percentile",
            line=dict(color="#1f77b4", width=1, dash="dot"),
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=time,
            y=p95,
            mode="lines",
            name="95th percentile",
            line=dict(color="#1f77b4", width=1, dash="dot"),
            hoverinfo="skip",
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


def create_drift_distribution_figure(
    drift_values: list[float] | np.ndarray,
    title: str = "Maximum Drift Distribution",
    show_percentiles: bool = True,
) -> go.Figure:
    """
    Create a histogram of maximum drift values from Monte Carlo analysis.

    Parameters
    ----------
    drift_values : array-like
        Maximum drift values from MC samples.
    title : str
        Plot title.
    show_percentiles : bool
        If True, show percentile markers.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    drift_values = np.asarray(drift_values)

    if len(drift_values) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No Monte Carlo results available",
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

    # Add histogram
    fig.add_trace(
        go.Histogram(
            x=drift_values,
            nbinsx=30,
            name="Distribution",
            marker=dict(color="#1f77b4", line=dict(color="white", width=1)),
            hovertemplate="Drift: %{x:.4f}<br>Count: %{y}<extra></extra>",
        )
    )

    # Add percentile markers
    if show_percentiles:
        p5 = np.percentile(drift_values, 5)
        p50 = np.percentile(drift_values, 50)
        p95 = np.percentile(drift_values, 95)

        fig.add_vline(
            x=p5,
            line_dash="dash",
            line_color="#2ca02c",
            annotation_text=f"5th: {p5:.4f}",
            annotation_position="top left",
        )
        fig.add_vline(
            x=p50,
            line_dash="solid",
            line_color="#ff7f0e",
            annotation_text=f"50th: {p50:.4f}",
            annotation_position="top",
        )
        fig.add_vline(
            x=p95,
            line_dash="dash",
            line_color="#d62728",
            annotation_text=f"95th: {p95:.4f}",
            annotation_position="top right",
        )

    # Add LS drift limit
    fig.add_vline(
        x=0.025,
        line_dash="dot",
        line_color="gray",
        opacity=0.7,
        annotation_text="LS (2.5%)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Maximum Inter-Story Drift Ratio",
        yaxis_title="Count",
        template="plotly_white",
        showlegend=False,
        margin=dict(l=60, r=40, t=60, b=60),
    )

    return fig
