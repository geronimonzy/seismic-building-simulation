"""Mode shape visualization."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_mode_shapes_figure(
    mode_shapes: list[list[float]] | np.ndarray,
    natural_periods: list[float] | np.ndarray,
    n_modes: int = 3,
    title: str = "Mode Shapes",
) -> go.Figure:
    """
    Create a visualization of building mode shapes.

    Parameters
    ----------
    mode_shapes : array-like
        Mode shape matrix (n_dof x n_modes), columns are mode shapes.
    natural_periods : array-like
        Natural periods for each mode.
    n_modes : int
        Number of modes to display.
    title : str
        Plot title.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    mode_shapes = np.asarray(mode_shapes)
    natural_periods = np.asarray(natural_periods)

    if mode_shapes.size == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No building model configured",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title=title, template="plotly_white")
        return fig

    n_dof = mode_shapes.shape[0]
    n_modes = min(n_modes, mode_shapes.shape[1])

    # Create subplots for each mode
    fig = make_subplots(
        rows=1,
        cols=n_modes,
        subplot_titles=[f"Mode {i + 1} (T={natural_periods[i]:.2f}s)" for i in range(n_modes)],
        shared_yaxes=True,
    )

    # Story levels (including ground)
    stories = np.arange(n_dof + 1)  # 0 to n_dof
    story_labels = ["Ground"] + [f"Floor {i + 1}" for i in range(n_dof)]

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for mode_idx in range(n_modes):
        # Normalize mode shape (max = 1)
        phi = mode_shapes[:, mode_idx]
        phi_normalized = phi / np.max(np.abs(phi)) if np.max(np.abs(phi)) > 0 else phi

        # Add zero at ground level
        phi_with_ground = np.concatenate([[0], phi_normalized])

        color = colors[mode_idx % len(colors)]

        # Add mode shape line
        fig.add_trace(
            go.Scatter(
                x=phi_with_ground,
                y=stories,
                mode="lines+markers",
                name=f"Mode {mode_idx + 1}",
                line=dict(color=color, width=2),
                marker=dict(size=8),
                hovertemplate="Story %{y}<br>Amplitude: %{x:.3f}<extra></extra>",
            ),
            row=1,
            col=mode_idx + 1,
        )

        # Add zero reference line
        fig.add_vline(
            x=0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=mode_idx + 1
        )

        # Add building outline (simplified)
        fig.add_trace(
            go.Scatter(
                x=[0, 0],
                y=[0, n_dof],
                mode="lines",
                line=dict(color="lightgray", width=3),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=mode_idx + 1,
        )

    # Update layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        template="plotly_white",
        showlegend=False,
        height=400,
        margin=dict(l=60, r=40, t=80, b=60),
    )

    # Update axes
    for i in range(n_modes):
        fig.update_xaxes(
            title_text="Normalized Amplitude" if i == 0 else "",
            range=[-1.2, 1.2],
            row=1,
            col=i + 1,
        )

    fig.update_yaxes(
        title_text="Story",
        tickvals=list(range(n_dof + 1)),
        ticktext=story_labels,
        row=1,
        col=1,
    )

    return fig


def create_building_schematic(
    n_stories: int,
    story_heights: list[float] | np.ndarray,
    title: str = "Building Schematic",
) -> go.Figure:
    """
    Create a simple schematic of the building.

    Parameters
    ----------
    n_stories : int
        Number of stories.
    story_heights : array-like
        Story heights in meters.
    title : str
        Plot title.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    story_heights = np.asarray(story_heights)

    fig = go.Figure()

    # Building dimensions
    building_width = 10  # arbitrary units
    cumulative_height = np.concatenate([[0], np.cumsum(story_heights)])
    total_height = cumulative_height[-1]

    # Draw floors
    for _i, h in enumerate(cumulative_height):
        fig.add_trace(
            go.Scatter(
                x=[-building_width / 2, building_width / 2],
                y=[h, h],
                mode="lines",
                line=dict(color="black", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Draw columns
    for x in [-building_width / 2, building_width / 2]:
        fig.add_trace(
            go.Scatter(
                x=[x, x],
                y=[0, total_height],
                mode="lines",
                line=dict(color="black", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Add floor labels
    for i in range(n_stories):
        mid_height = (cumulative_height[i] + cumulative_height[i + 1]) / 2
        fig.add_annotation(
            x=0,
            y=mid_height,
            text=f"Story {i + 1}<br>h={story_heights[i]:.1f}m",
            showarrow=False,
            font=dict(size=10),
        )

    # Add ground
    fig.add_trace(
        go.Scatter(
            x=[-building_width * 0.7, building_width * 0.7],
            y=[0, 0],
            mode="lines",
            line=dict(color="brown", width=4),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Ground hatching
    for x in np.linspace(-building_width * 0.6, building_width * 0.6, 10):
        fig.add_trace(
            go.Scatter(
                x=[x, x - 1],
                y=[0, -1],
                mode="lines",
                line=dict(color="brown", width=1),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        template="plotly_white",
        xaxis=dict(visible=False, range=[-building_width, building_width]),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        height=400,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    return fig
