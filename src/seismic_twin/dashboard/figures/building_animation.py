"""2D building animation with wave visualization for seismic response."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


def create_building_animation_figure(
    story_heights: np.ndarray | list[float],
    displacement: np.ndarray,
    time: np.ndarray,
    ground_acceleration: np.ndarray | None = None,
    scale_factor: float = 50.0,
    max_frames: int = 300,
    show_undeformed: bool = True,
    show_labels: bool = True,
    show_wave: bool = True,
) -> go.Figure:
    """
    Create an animated 2D building deformation visualization.

    Parameters
    ----------
    story_heights : array-like
        Heights of each story in meters (length = n_stories).
    displacement : np.ndarray
        Displacement time history array of shape (n_dof, n_timesteps).
    time : np.ndarray
        Time vector in seconds.
    ground_acceleration : np.ndarray, optional
        Ground acceleration time history for base motion visualization.
    scale_factor : float
        Amplification factor for displacement visualization.
    max_frames : int
        Maximum number of animation frames (downsampled from time steps).
    show_undeformed : bool
        Whether to show the undeformed building outline.
    show_labels : bool
        Whether to show floor labels.
    show_wave : bool
        Whether to show approaching wave animation.

    Returns
    -------
    go.Figure
        Plotly figure with animation frames and controls.
    """
    story_heights = np.asarray(story_heights, dtype=np.float32)
    displacement = np.asarray(displacement, dtype=np.float32)
    time = np.asarray(time, dtype=np.float32)

    # Handle empty data
    if len(time) == 0 or displacement.size == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No simulation data available.<br>Run a simulation first.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(title="Building Animation", template="plotly_white")
        return fig

    n_timesteps = len(time)

    # Compute floor elevations (cumulative heights)
    floor_elevations = np.concatenate([[0], np.cumsum(story_heights)])

    # Building geometry parameters
    building_width = 10.0  # Fixed visual width in meters
    half_width = building_width / 2

    # Downsample frames if needed
    frame_step = max(1, n_timesteps // max_frames)
    frame_indices = np.arange(0, n_timesteps, frame_step)

    # Process ground acceleration for base motion
    if ground_acceleration is not None:
        ground_acc = np.asarray(ground_acceleration, dtype=np.float32)
        # Scale ground motion for visualization (arbitrary scaling for visual effect)
        ground_disp = ground_acc * scale_factor * 0.1
    else:
        ground_disp = np.zeros(n_timesteps, dtype=np.float32)

    # Wave visualization parameters
    wave_start_x = -25.0  # Wave starts from left
    wave_end_x = -half_width - 2  # Wave ends near building base
    duration = time[-1] if len(time) > 0 else 1.0

    # Create the figure with initial frame (t=0)
    fig = go.Figure()

    # --- Static traces (undeformed building) ---
    if show_undeformed:
        # Undeformed building outline (gray dashed)
        undeformed_x = []
        undeformed_y = []
        # Left column
        undeformed_x.extend([-half_width, -half_width, None])
        undeformed_y.extend([0, floor_elevations[-1], None])
        # Right column
        undeformed_x.extend([half_width, half_width, None])
        undeformed_y.extend([0, floor_elevations[-1], None])
        # Floor slabs
        for elev in floor_elevations:
            undeformed_x.extend([-half_width, half_width, None])
            undeformed_y.extend([elev, elev, None])

        fig.add_trace(
            go.Scatter(
                x=undeformed_x,
                y=undeformed_y,
                mode="lines",
                line=dict(color="lightgray", width=2, dash="dash"),
                name="Undeformed",
                showlegend=True,
                hoverinfo="skip",
            )
        )

    # Ground line (static)
    fig.add_trace(
        go.Scatter(
            x=[-30, 30],
            y=[0, 0],
            mode="lines",
            line=dict(color="#8B4513", width=3),
            name="Ground",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Floor labels (static)
    if show_labels:
        for i, elev in enumerate(floor_elevations[1:], 1):
            fig.add_annotation(
                x=half_width + 2,
                y=elev,
                text=f"Floor {i}",
                showarrow=False,
                font=dict(size=10, color="gray"),
                xanchor="left",
            )

    # --- Initial animated traces (will be updated in frames) ---
    # Deformed building (initial state)
    initial_deformed_x, initial_deformed_y = _compute_deformed_building(
        floor_elevations, displacement[:, 0], scale_factor, half_width
    )

    fig.add_trace(
        go.Scatter(
            x=initial_deformed_x,
            y=initial_deformed_y,
            mode="lines",
            line=dict(color="#1f77b4", width=3),
            name="Deformed",
            showlegend=True,
            fill="toself",
            fillcolor="rgba(31, 119, 180, 0.1)",
        )
    )

    # Ground motion bar (at base)
    ground_bar_width = building_width * 0.8
    fig.add_trace(
        go.Scatter(
            x=[-ground_bar_width / 2, ground_bar_width / 2],
            y=[-0.5, -0.5],
            mode="lines",
            line=dict(color="#A0522D", width=8),
            name="Base Motion",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Wave pattern (if enabled)
    if show_wave:
        wave_x, wave_y = _compute_wave(0, duration, wave_start_x, wave_end_x)
        fig.add_trace(
            go.Scatter(
                x=wave_x,
                y=wave_y,
                mode="lines",
                line=dict(color="#4169E1", width=2),
                name="Seismic Wave",
                showlegend=True,
                opacity=0.6,
            )
        )

    # Time indicator text
    fig.add_annotation(
        x=0.02,
        y=0.98,
        xref="paper",
        yref="paper",
        text=f"t = {time[0]:.2f} s",
        showarrow=False,
        font=dict(size=14, color="black"),
        bgcolor="rgba(255,255,255,0.8)",
        borderpad=4,
        xanchor="left",
        yanchor="top",
        name="time_annotation",
    )

    # --- Generate animation frames ---
    frames = []
    slider_steps = []

    for idx in frame_indices:
        t = time[idx]

        # Deformed building for this frame
        deformed_x, deformed_y = _compute_deformed_building(
            floor_elevations, displacement[:, idx], scale_factor, half_width
        )

        # Ground motion bar position
        base_offset = ground_disp[idx] if idx < len(ground_disp) else 0
        ground_bar_x = [
            -ground_bar_width / 2 + base_offset,
            ground_bar_width / 2 + base_offset,
        ]

        # Wave position
        wave_x, wave_y = _compute_wave(t, duration, wave_start_x, wave_end_x)

        # Build frame data - trace indices must match the order above
        frame_data = [
            # Trace 0: Undeformed (static, but include for consistency)
            go.Scatter(visible=show_undeformed),
            # Trace 1: Ground line (static)
            go.Scatter(),
            # Trace 2: Deformed building
            go.Scatter(x=deformed_x, y=deformed_y),
            # Trace 3: Ground motion bar
            go.Scatter(x=ground_bar_x),
            # Trace 4: Wave (if enabled)
            go.Scatter(x=wave_x, y=wave_y) if show_wave else go.Scatter(),
        ]

        # Frame layout with updated time annotation
        frame_layout = go.Layout(
            annotations=[
                dict(
                    x=0.02,
                    y=0.98,
                    xref="paper",
                    yref="paper",
                    text=f"t = {t:.2f} s",
                    showarrow=False,
                    font=dict(size=14, color="black"),
                    bgcolor="rgba(255,255,255,0.8)",
                    borderpad=4,
                    xanchor="left",
                    yanchor="top",
                ),
            ]
            + (
                [
                    dict(
                        x=half_width + 2,
                        y=elev,
                        text=f"Floor {i}",
                        showarrow=False,
                        font=dict(size=10, color="gray"),
                        xanchor="left",
                    )
                    for i, elev in enumerate(floor_elevations[1:], 1)
                ]
                if show_labels
                else []
            )
        )

        frames.append(
            go.Frame(
                data=frame_data,
                name=str(idx),
                layout=frame_layout,
            )
        )

        # Slider step
        slider_steps.append(
            dict(
                args=[
                    [str(idx)],
                    dict(
                        frame=dict(duration=50, redraw=True),
                        mode="immediate",
                        transition=dict(duration=0),
                    ),
                ],
                label=f"{t:.1f}s",
                method="animate",
            )
        )

    fig.frames = frames

    # --- Animation controls ---
    # Play/Pause buttons
    updatemenus = [
        dict(
            type="buttons",
            showactive=False,
            y=0,
            x=0.1,
            xanchor="right",
            yanchor="top",
            pad=dict(t=0, r=10),
            buttons=[
                dict(
                    label="Play",
                    method="animate",
                    args=[
                        None,
                        dict(
                            frame=dict(duration=50, redraw=True),
                            fromcurrent=True,
                            transition=dict(duration=0),
                        ),
                    ],
                ),
                dict(
                    label="Pause",
                    method="animate",
                    args=[
                        [None],
                        dict(
                            frame=dict(duration=0, redraw=False),
                            mode="immediate",
                            transition=dict(duration=0),
                        ),
                    ],
                ),
            ],
        )
    ]

    # Time slider
    sliders = [
        dict(
            active=0,
            yanchor="top",
            xanchor="left",
            currentvalue=dict(
                font=dict(size=12),
                prefix="Time: ",
                visible=True,
                xanchor="right",
            ),
            transition=dict(duration=0),
            pad=dict(b=10, t=50),
            len=0.9,
            x=0.1,
            y=0,
            steps=slider_steps,
        )
    ]

    # --- Layout ---
    total_height = floor_elevations[-1]
    y_padding = total_height * 0.15

    fig.update_layout(
        title=dict(text="Building Deformation Animation", font=dict(size=16)),
        template="plotly_white",
        xaxis=dict(
            title="Horizontal Position (m)",
            range=[-30, 20],
            constrain="domain",
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            title="Elevation (m)",
            range=[-2, total_height + y_padding],
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        updatemenus=updatemenus,
        sliders=sliders,
        margin=dict(l=60, r=40, t=80, b=100),
    )

    return fig


def _compute_deformed_building(
    floor_elevations: np.ndarray,
    floor_displacements: np.ndarray,
    scale_factor: float,
    half_width: float,
) -> tuple[list[float], list[float]]:
    """
    Compute deformed building outline coordinates.

    Returns x, y coordinate lists for a closed polygon representing the building.
    """
    n_floors = len(floor_elevations) - 1  # Number of floors (not including ground)

    # Scale displacements
    scaled_disp = np.zeros(len(floor_elevations))
    scaled_disp[1:] = floor_displacements[:n_floors] * scale_factor

    # Build closed polygon: left side up, across top, right side down, across bottom
    x_coords = []
    y_coords = []

    # Left side (bottom to top)
    for elev, disp in zip(floor_elevations, scaled_disp):
        x_coords.append(-half_width + disp)
        y_coords.append(elev)

    # Top (left to right)
    x_coords.append(half_width + scaled_disp[-1])
    y_coords.append(floor_elevations[-1])

    # Right side (top to bottom)
    for i in range(len(floor_elevations) - 2, -1, -1):
        x_coords.append(half_width + scaled_disp[i])
        y_coords.append(floor_elevations[i])

    # Close the polygon
    x_coords.append(x_coords[0])
    y_coords.append(y_coords[0])

    return x_coords, y_coords


def _compute_wave(
    current_time: float,
    total_duration: float,
    start_x: float,
    end_x: float,
    wave_length: float = 8.0,
    wave_amplitude: float = 1.5,
) -> tuple[list[float], list[float]]:
    """
    Compute wave pattern coordinates for visualization.

    The wave moves from left to right, fading as it approaches the building.
    """
    # Wave progress (0 to 1)
    progress = min(current_time / total_duration, 1.0) if total_duration > 0 else 0

    # Wave center position (moves right over time)
    wave_center = start_x + progress * (end_x - start_x + 15)

    # Generate wave points
    x_points = np.linspace(start_x, end_x, 50)
    y_points = []

    for x in x_points:
        # Distance from wave center affects amplitude
        dist_from_center = abs(x - wave_center)
        # Gaussian envelope for wave amplitude
        envelope = np.exp(-0.5 * (dist_from_center / wave_length) ** 2)
        # Sine wave with envelope
        phase = 2 * np.pi * (x - wave_center) / wave_length
        y = wave_amplitude * envelope * np.sin(phase)
        y_points.append(y)

    return list(x_points), y_points
