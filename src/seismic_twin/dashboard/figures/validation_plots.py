"""Validation comparison plots for wave propagation prediction."""

from __future__ import annotations

from typing import TYPE_CHECKING

import plotly.graph_objects as go
from plotly.subplots import make_subplots

if TYPE_CHECKING:
    from numpy.typing import NDArray


def create_waveform_comparison_figure(
    time: list[float] | NDArray,
    actual: list[float] | NDArray,
    predicted: list[float] | NDArray,
    station_id: str = "",
) -> go.Figure:
    """
    Create waveform comparison figure.

    Shows actual and predicted waveforms in a 2-panel subplot.
    If actual data is empty, shows only predicted in a single panel.

    Parameters
    ----------
    time : array-like
        Time vector in seconds.
    actual : array-like
        Actual acceleration time history in g. Can be empty for building predictions.
    predicted : array-like
        Predicted acceleration time history in g.
    station_id : str
        Station identifier for title.

    Returns
    -------
    go.Figure
        Plotly figure with waveform comparison.
    """
    # Check if we have actual data
    has_actual = len(actual) > 0

    if has_actual:
        # Two-panel comparison
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=("Actual Recording", "Predicted (GMPE-scaled)"),
        )

        # Actual waveform
        fig.add_trace(
            go.Scatter(
                x=list(time),
                y=list(actual),
                mode="lines",
                name="Actual",
                line=dict(color="#1f77b4", width=1),
            ),
            row=1,
            col=1,
        )

        # Predicted waveform
        fig.add_trace(
            go.Scatter(
                x=list(time),
                y=list(predicted),
                mode="lines",
                name="Predicted",
                line=dict(color="#ff7f0e", width=1),
            ),
            row=2,
            col=1,
        )

        fig.update_xaxes(title_text="Time (s)", row=2, col=1)
        fig.update_yaxes(title_text="Acc (g)", row=1, col=1)
        fig.update_yaxes(title_text="Acc (g)", row=2, col=1)
    else:
        # Single panel for predicted only
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=list(time),
                y=list(predicted),
                mode="lines",
                name="Predicted",
                line=dict(color="#ff7f0e", width=1),
            )
        )

        fig.update_xaxes(title_text="Time (s)")
        fig.update_yaxes(title_text="Acceleration (g)")

    # Update layout
    title = "Predicted Waveform" if not has_actual else "Waveform Comparison"
    if station_id:
        title = f"{title} - {station_id}"

    fig.update_layout(
        title=title,
        height=400,
        showlegend=False,
        margin=dict(l=60, r=20, t=60, b=40),
    )

    return fig


def create_spectrum_comparison_figure(
    periods: list[float] | NDArray,
    actual_sa: list[float] | NDArray,
    predicted_sa: list[float] | NDArray,
    station_id: str = "",
) -> go.Figure:
    """
    Create response spectrum comparison figure.

    Shows actual and predicted spectra on a log-log plot.
    If actual data is empty, shows only predicted spectrum.

    Parameters
    ----------
    periods : array-like
        Spectral periods in seconds.
    actual_sa : array-like
        Actual spectral acceleration in g. Can be empty for building predictions.
    predicted_sa : array-like
        Predicted spectral acceleration in g.
    station_id : str
        Station identifier for title.

    Returns
    -------
    go.Figure
        Plotly figure with spectrum comparison.
    """
    fig = go.Figure()

    # Check if we have actual data
    has_actual = len(actual_sa) > 0

    # Actual spectrum (only if available)
    if has_actual:
        fig.add_trace(
            go.Scatter(
                x=list(periods),
                y=list(actual_sa),
                mode="lines",
                name="Actual",
                line=dict(color="#1f77b4", width=2),
            )
        )

    # Predicted spectrum
    fig.add_trace(
        go.Scatter(
            x=list(periods),
            y=list(predicted_sa),
            mode="lines",
            name="Predicted",
            line=dict(color="#ff7f0e", width=2, dash="dash" if has_actual else "solid"),
        )
    )

    # Update layout
    title = "Predicted Response Spectrum" if not has_actual else "Response Spectrum Comparison"
    if station_id:
        title = f"{title} - {station_id}"

    fig.update_layout(
        title=title,
        xaxis_title="Period (s)",
        yaxis_title="Sa (g)",
        xaxis_type="log",
        yaxis_type="log",
        height=400,
        showlegend=has_actual,
        legend=dict(x=0.7, y=0.95),
        margin=dict(l=60, r=20, t=60, b=40),
    )

    # Add period range annotations
    fig.add_vrect(
        x0=0.01,
        x1=0.5,
        fillcolor="lightblue",
        opacity=0.2,
        layer="below",
        line_width=0,
        annotation_text="Short",
        annotation_position="top left",
    )
    fig.add_vrect(
        x0=0.5,
        x1=2.0,
        fillcolor="lightyellow",
        opacity=0.2,
        layer="below",
        line_width=0,
        annotation_text="Mid",
        annotation_position="top left",
    )
    fig.add_vrect(
        x0=2.0,
        x1=10.0,
        fillcolor="lightgreen",
        opacity=0.2,
        layer="below",
        line_width=0,
        annotation_text="Long",
        annotation_position="top left",
    )

    return fig


def create_empty_waveform_figure() -> go.Figure:
    """Create empty waveform figure with placeholder text."""
    fig = go.Figure()
    fig.add_annotation(
        text="Run prediction to see waveform comparison",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray"),
    )
    fig.update_layout(
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


def create_empty_spectrum_figure() -> go.Figure:
    """Create empty spectrum figure with placeholder text."""
    fig = go.Figure()
    fig.add_annotation(
        text="Run prediction to see spectrum comparison",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray"),
    )
    fig.update_layout(
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


def create_pga_scatter_figure(
    distances: list[float] | NDArray,
    actual_pgas: list[float] | NDArray,
    predicted_pgas: list[float] | NDArray,
    station_ids: list[str] | None = None,
) -> go.Figure:
    """
    Create PGA vs distance scatter plot.

    Compares actual and predicted PGA values across multiple stations.

    Parameters
    ----------
    distances : array-like
        Station distances in km.
    actual_pgas : array-like
        Actual PGA values in g.
    predicted_pgas : array-like
        Predicted PGA values in g.
    station_ids : list[str], optional
        Station identifiers for hover text.

    Returns
    -------
    go.Figure
        Plotly figure with PGA scatter comparison.
    """
    fig = go.Figure()

    hover_text = station_ids if station_ids else [f"Station {i}" for i in range(len(distances))]

    # Actual PGA
    fig.add_trace(
        go.Scatter(
            x=list(distances),
            y=list(actual_pgas),
            mode="markers",
            name="Actual",
            marker=dict(color="#1f77b4", size=12, symbol="circle"),
            text=hover_text,
            hovertemplate="Station: %{text}<br>Distance: %{x:.1f} km<br>PGA: %{y:.4f} g<extra></extra>",
        )
    )

    # Predicted PGA
    fig.add_trace(
        go.Scatter(
            x=list(distances),
            y=list(predicted_pgas),
            mode="markers",
            name="Predicted",
            marker=dict(color="#ff7f0e", size=12, symbol="diamond"),
            text=hover_text,
            hovertemplate="Station: %{text}<br>Distance: %{x:.1f} km<br>PGA: %{y:.4f} g<extra></extra>",
        )
    )

    fig.update_layout(
        title="PGA vs Distance",
        xaxis_title="Distance (km)",
        yaxis_title="PGA (g)",
        yaxis_type="log",
        height=350,
        showlegend=True,
        legend=dict(x=0.7, y=0.95),
        margin=dict(l=60, r=20, t=60, b=40),
    )

    return fig
