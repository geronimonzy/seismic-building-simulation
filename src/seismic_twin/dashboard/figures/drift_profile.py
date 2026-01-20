"""Drift profile visualization."""

import numpy as np
import plotly.graph_objects as go

# ASCE 7 drift limits for reference
DRIFT_LIMITS = {
    "io": 0.007,  # Immediate Occupancy
    "ls": 0.025,  # Life Safety
    "cp": 0.050,  # Collapse Prevention
}


def create_drift_profile_figure(
    drift_ratios: list[float] | np.ndarray,
    story_heights: list[float] | np.ndarray | None = None,
    title: str = "Inter-Story Drift Profile",
    show_limits: bool = True,
    limit_type: str = "ls",
) -> go.Figure:
    """
    Create a horizontal bar chart showing drift ratios per story.

    Parameters
    ----------
    drift_ratios : array-like
        Maximum inter-story drift ratios per story.
    story_heights : array-like, optional
        Story heights in meters (for y-axis positioning).
    title : str
        Plot title.
    show_limits : bool
        If True, show performance limit lines.
    limit_type : str
        Type of limit to highlight ('io', 'ls', 'cp').

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    drift_ratios = np.asarray(drift_ratios)
    n_stories = len(drift_ratios)

    if n_stories == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No drift data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title=title, template="plotly_white")
        return fig

    # Story labels
    story_labels = [f"Story {i + 1}" for i in range(n_stories)]

    # Determine bar colors based on drift limits
    colors = []
    for dr in drift_ratios:
        if dr >= DRIFT_LIMITS["cp"]:
            colors.append("#d62728")  # red - collapse prevention exceeded
        elif dr >= DRIFT_LIMITS["ls"]:
            colors.append("#ff7f0e")  # orange - life safety exceeded
        elif dr >= DRIFT_LIMITS["io"]:
            colors.append("#ffd92f")  # yellow - immediate occupancy exceeded
        else:
            colors.append("#2ca02c")  # green - within IO

    fig = go.Figure()

    # Add horizontal bars
    fig.add_trace(
        go.Bar(
            x=drift_ratios,
            y=story_labels,
            orientation="h",
            marker=dict(color=colors, line=dict(color="black", width=1)),
            text=[f"{dr:.4f}" for dr in drift_ratios],
            textposition="outside",
            hovertemplate="%{y}<br>Drift Ratio: %{x:.4f}<extra></extra>",
        )
    )

    # Add vertical limit lines
    if show_limits:
        # IO limit
        fig.add_vline(
            x=DRIFT_LIMITS["io"],
            line_dash="dash",
            line_color="#2ca02c",
            opacity=0.7,
            annotation_text="IO (0.7%)",
            annotation_position="top",
        )
        # LS limit
        fig.add_vline(
            x=DRIFT_LIMITS["ls"],
            line_dash="dash",
            line_color="#ff7f0e",
            opacity=0.7,
            annotation_text="LS (2.5%)",
            annotation_position="top",
        )
        # CP limit
        fig.add_vline(
            x=DRIFT_LIMITS["cp"],
            line_dash="dash",
            line_color="#d62728",
            opacity=0.7,
            annotation_text="CP (5%)",
            annotation_position="top",
        )

    # Update layout
    max_drift = max(drift_ratios) if len(drift_ratios) > 0 else 0.05
    x_max = max(max_drift * 1.3, DRIFT_LIMITS["cp"] * 1.1)

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Inter-Story Drift Ratio",
        yaxis_title="Story",
        template="plotly_white",
        xaxis=dict(range=[0, x_max], tickformat=".3f"),
        showlegend=False,
        margin=dict(l=80, r=40, t=60, b=60),
        height=max(300, n_stories * 50 + 100),
    )

    return fig


def create_drift_envelope_figure(
    drift_ratios: list[float] | np.ndarray,
    drift_p5: list[float] | np.ndarray | None = None,
    drift_p95: list[float] | np.ndarray | None = None,
    title: str = "Drift Profile with Uncertainty",
) -> go.Figure:
    """
    Create a drift profile with uncertainty bounds (if available).

    Parameters
    ----------
    drift_ratios : array-like
        Median or mean drift ratios per story.
    drift_p5 : array-like, optional
        5th percentile drift ratios.
    drift_p95 : array-like, optional
        95th percentile drift ratios.
    title : str
        Plot title.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    drift_ratios = np.asarray(drift_ratios)
    n_stories = len(drift_ratios)

    if n_stories == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No drift data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title=title, template="plotly_white")
        return fig

    story_numbers = np.arange(1, n_stories + 1)

    fig = go.Figure()

    # Add uncertainty band if available
    if drift_p5 is not None and drift_p95 is not None:
        drift_p5 = np.asarray(drift_p5)
        drift_p95 = np.asarray(drift_p95)

        # Fill between p5 and p95
        fig.add_trace(
            go.Scatter(
                x=np.concatenate([drift_p5, drift_p95[::-1]]),
                y=np.concatenate([story_numbers, story_numbers[::-1]]),
                fill="toself",
                fillcolor="rgba(31, 119, 180, 0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                name="90% CI",
                hoverinfo="skip",
            )
        )

    # Add main drift profile
    fig.add_trace(
        go.Scatter(
            x=drift_ratios,
            y=story_numbers,
            mode="lines+markers",
            name="Median",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=8),
            hovertemplate="Story %{y}<br>Drift: %{x:.4f}<extra></extra>",
        )
    )

    # Add limit lines
    fig.add_vline(
        x=DRIFT_LIMITS["ls"],
        line_dash="dash",
        line_color="#ff7f0e",
        opacity=0.7,
        annotation_text="LS (2.5%)",
        annotation_position="top right",
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Inter-Story Drift Ratio",
        yaxis_title="Story",
        template="plotly_white",
        yaxis=dict(dtick=1),
        margin=dict(l=60, r=40, t=60, b=60),
        height=max(300, n_stories * 40 + 100),
    )

    return fig
