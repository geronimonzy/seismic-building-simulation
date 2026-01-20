"""Energy balance visualization for structural dynamics verification."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


def create_energy_balance_figure(
    time: list[float] | np.ndarray,
    kinetic: list[float] | np.ndarray,
    strain: list[float] | np.ndarray,
    damping: list[float] | np.ndarray,
    input_energy: list[float] | np.ndarray,
    selected_components: list[str] | None = None,
    title: str = "Energy Balance",
) -> go.Figure:
    """
    Create an energy balance plot showing kinetic, strain, damping, and input energy.

    Parameters
    ----------
    time : array-like
        Time vector in seconds.
    kinetic : array-like
        Kinetic energy time history in Joules.
    strain : array-like
        Strain (potential) energy time history in Joules.
    damping : array-like
        Cumulative damping energy dissipated in Joules.
    input_energy : array-like
        Cumulative input energy from earthquake in Joules.
    selected_components : list[str], optional
        List of components to display. Options: 'kinetic', 'strain', 'damping', 'input'.
        If None, all components are shown.
    title : str
        Plot title.

    Returns
    -------
    go.Figure
        Plotly figure object.
    """
    time = np.asarray(time)
    kinetic = np.asarray(kinetic)
    strain = np.asarray(strain)
    damping = np.asarray(damping)
    input_energy = np.asarray(input_energy)

    # Handle empty data
    if len(time) == 0 or kinetic.size == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No energy balance data available.<br>Re-run simulation to compute energy.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title=title, template="plotly_white")
        return fig

    # Default: show all components
    if selected_components is None:
        selected_components = ["kinetic", "strain", "damping", "input"]

    # Energy component configurations
    components = {
        "kinetic": {
            "data": kinetic,
            "name": "Kinetic Energy",
            "color": "#1f77b4",  # blue
            "dash": "solid",
        },
        "strain": {
            "data": strain,
            "name": "Strain Energy",
            "color": "#ff7f0e",  # orange
            "dash": "solid",
        },
        "damping": {
            "data": damping,
            "name": "Damping Energy (cumulative)",
            "color": "#2ca02c",  # green
            "dash": "solid",
        },
        "input": {
            "data": input_energy,
            "name": "Input Energy (cumulative)",
            "color": "#d62728",  # red
            "dash": "solid",
        },
    }

    fig = go.Figure()

    # Add selected energy traces
    for component_id in selected_components:
        if component_id in components:
            comp = components[component_id]
            fig.add_trace(
                go.Scatter(
                    x=time,
                    y=comp["data"],
                    mode="lines",
                    name=comp["name"],
                    line=dict(color=comp["color"], width=2, dash=comp["dash"]),
                    hovertemplate=f"Time: %{{x:.2f}} s<br>{comp['name']}: %{{y:.2e}} J<extra></extra>",
                )
            )

    # Update layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_title="Time (s)",
        yaxis_title="Energy (J)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=60, r=40, t=80, b=60),
    )

    # Format y-axis for scientific notation if values are large
    max_value = max(
        np.max(np.abs(kinetic)) if "kinetic" in selected_components else 0,
        np.max(np.abs(strain)) if "strain" in selected_components else 0,
        np.max(np.abs(damping)) if "damping" in selected_components else 0,
        np.max(np.abs(input_energy)) if "input" in selected_components else 0,
    )

    if max_value > 1e6:
        fig.update_layout(yaxis=dict(exponentformat="e", showexponent="all"))

    return fig
