"""
Visualization Utilities for Seismic Analysis

This module provides functions for plotting ground motion, structural
response, calibration results, and uncertainty bounds.
"""

from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray


def plot_ground_motion(
    time: NDArray[np.floating],
    acceleration: NDArray[np.floating],
    ax: Optional[plt.Axes] = None,
    title: str = "Ground Motion",
    color: str = "black",
) -> plt.Axes:
    """
    Plot ground acceleration time history.

    Parameters
    ----------
    time : ndarray
        Time vector in seconds.
    acceleration : ndarray
        Ground acceleration in g.
    ax : matplotlib Axes, optional
        Axes to plot on. If None, creates new figure.
    title : str
        Plot title.
    color : str
        Line color.

    Returns
    -------
    matplotlib Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 3))

    ax.plot(time, acceleration, color=color, linewidth=0.8)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Acceleration (g)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="gray", linewidth=0.5)

    # Add PGA annotation
    pga = np.max(np.abs(acceleration))
    ax.annotate(
        f"PGA = {pga:.3f}g",
        xy=(0.98, 0.95),
        xycoords="axes fraction",
        ha="right",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    return ax


def plot_displacement_comparison(
    time: NDArray[np.floating],
    initial: NDArray[np.floating],
    refined: NDArray[np.floating],
    measured: NDArray[np.floating],
    floor: int = -1,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
) -> plt.Axes:
    """
    Plot comparison of initial prediction, refined prediction, and measurements.

    Parameters
    ----------
    time : ndarray
        Time vector in seconds.
    initial : ndarray
        Initial model displacement (n_dof x n_steps or n_steps).
    refined : ndarray
        Refined model displacement (n_dof x n_steps or n_steps).
    measured : ndarray
        Measured displacement (n_dof x n_steps or n_steps).
    floor : int
        Floor index to plot. -1 for top floor.
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str, optional
        Plot title.

    Returns
    -------
    matplotlib Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))

    # Handle 1D or 2D arrays
    if initial.ndim == 2:
        initial = initial[floor, :]
    if refined.ndim == 2:
        refined = refined[floor, :]
    if measured.ndim == 2:
        measured = measured[floor, :]

    ax.plot(time, measured, "k-", linewidth=1.5, label="Measured", alpha=0.8)
    ax.plot(time, initial, "b--", linewidth=1.0, label="Initial Prediction", alpha=0.7)
    ax.plot(time, refined, "r-", linewidth=1.0, label="Calibrated Prediction", alpha=0.7)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (m)")
    if title is None:
        title = f"Displacement Comparison (Floor {floor + 1 if floor >= 0 else 'Top'})"
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    return ax


def plot_calibration_convergence(
    iterations: NDArray[np.floating],
    nrmse: NDArray[np.floating],
    ax: Optional[plt.Axes] = None,
    title: str = "Calibration Convergence",
) -> plt.Axes:
    """
    Plot NRMSE convergence over calibration iterations.

    Parameters
    ----------
    iterations : ndarray
        Iteration numbers.
    nrmse : ndarray
        NRMSE values at each iteration.
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str
        Plot title.

    Returns
    -------
    matplotlib Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4))

    ax.plot(iterations, nrmse, "bo-", linewidth=1.5, markersize=8)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("NRMSE")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    # Mark minimum
    min_idx = np.argmin(nrmse)
    ax.plot(iterations[min_idx], nrmse[min_idx], "r*", markersize=15, label="Best")
    ax.annotate(
        f"Min NRMSE = {nrmse[min_idx]:.4f}",
        xy=(iterations[min_idx], nrmse[min_idx]),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=9,
    )

    return ax


def plot_uncertainty_bounds(
    time: NDArray[np.floating],
    mean: NDArray[np.floating],
    lower: NDArray[np.floating],
    upper: NDArray[np.floating],
    measured: Optional[NDArray[np.floating]] = None,
    floor: int = -1,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    fill_alpha: float = 0.3,
) -> plt.Axes:
    """
    Plot uncertainty bounds from Monte Carlo analysis.

    Parameters
    ----------
    time : ndarray
        Time vector in seconds.
    mean : ndarray
        Mean response (n_dof x n_steps or n_steps).
    lower : ndarray
        Lower percentile bound (n_dof x n_steps or n_steps).
    upper : ndarray
        Upper percentile bound (n_dof x n_steps or n_steps).
    measured : ndarray, optional
        Measured response for comparison.
    floor : int
        Floor index to plot. -1 for top floor.
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str, optional
        Plot title.
    fill_alpha : float
        Transparency for uncertainty band.

    Returns
    -------
    matplotlib Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))

    # Handle 1D or 2D arrays
    if mean.ndim == 2:
        mean = mean[floor, :]
    if lower.ndim == 2:
        lower = lower[floor, :]
    if upper.ndim == 2:
        upper = upper[floor, :]

    # Plot uncertainty band
    ax.fill_between(
        time,
        lower,
        upper,
        alpha=fill_alpha,
        color="blue",
        label="5th-95th percentile",
    )

    # Plot mean
    ax.plot(time, mean, "b-", linewidth=1.5, label="Median")

    # Plot measured if provided
    if measured is not None:
        if measured.ndim == 2:
            measured = measured[floor, :]
        ax.plot(time, measured, "k--", linewidth=1.0, label="Measured", alpha=0.8)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (m)")
    if title is None:
        title = f"Uncertainty Bounds (Floor {floor + 1 if floor >= 0 else 'Top'})"
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    return ax


def plot_max_drifts(
    drift_ratios: NDArray[np.floating],
    story_labels: Optional[List[str]] = None,
    ax: Optional[plt.Axes] = None,
    title: str = "Maximum Inter-Story Drift Ratios",
    threshold: Optional[float] = None,
) -> plt.Axes:
    """
    Plot bar chart of maximum inter-story drift ratios.

    Parameters
    ----------
    drift_ratios : ndarray
        Maximum drift ratio for each story.
    story_labels : list of str, optional
        Labels for each story.
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str
        Plot title.
    threshold : float, optional
        Performance threshold to draw as horizontal line.

    Returns
    -------
    matplotlib Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    n_stories = len(drift_ratios)
    if story_labels is None:
        story_labels = [f"Story {i + 1}" for i in range(n_stories)]

    x = np.arange(n_stories)
    colors = plt.cm.Blues(np.linspace(0.4, 0.8, n_stories))

    bars = ax.bar(x, drift_ratios * 100, color=colors, edgecolor="navy", linewidth=1.2)

    # Add value labels on bars
    for bar, dr in zip(bars, drift_ratios):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{dr * 100:.2f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    if threshold is not None:
        ax.axhline(
            y=threshold * 100,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Threshold ({threshold * 100:.1f}%)",
        )
        ax.legend()

    ax.set_xlabel("Story")
    ax.set_ylabel("Drift Ratio (%)")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(story_labels, rotation=45, ha="right")
    ax.grid(True, alpha=0.3, axis="y")

    return ax


def plot_mode_shapes(
    mode_shapes: NDArray[np.floating],
    n_modes: int = 3,
    story_heights: Optional[NDArray[np.floating]] = None,
    ax: Optional[plt.Axes] = None,
    title: str = "Mode Shapes",
) -> plt.Axes:
    """
    Plot structural mode shapes.

    Parameters
    ----------
    mode_shapes : ndarray
        Mode shape matrix (n_dof x n_modes).
    n_modes : int
        Number of modes to plot.
    story_heights : ndarray, optional
        Story heights for y-axis scaling.
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str
        Plot title.

    Returns
    -------
    matplotlib Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))

    n_dof = mode_shapes.shape[0]
    n_modes = min(n_modes, mode_shapes.shape[1])

    if story_heights is None:
        heights = np.arange(1, n_dof + 1)
    else:
        heights = np.cumsum(story_heights)

    # Add ground level
    heights_with_ground = np.concatenate([[0], heights])

    colors = plt.cm.tab10(np.linspace(0, 1, n_modes))

    for i in range(n_modes):
        mode = mode_shapes[:, i]
        # Normalize mode shape
        mode_norm = mode / np.max(np.abs(mode))
        mode_with_ground = np.concatenate([[0], mode_norm])

        ax.plot(
            mode_with_ground,
            heights_with_ground,
            "o-",
            color=colors[i],
            linewidth=2,
            markersize=8,
            label=f"Mode {i + 1}",
        )

    ax.axvline(x=0, color="gray", linewidth=0.5)
    ax.set_xlabel("Normalized Displacement")
    ax.set_ylabel("Height (m)" if story_heights is not None else "Floor")
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    return ax


def plot_energy_balance(
    time: NDArray[np.floating],
    energy_dict: dict,
    ax: Optional[plt.Axes] = None,
    title: str = "Energy Balance",
) -> plt.Axes:
    """
    Plot energy time histories.

    Parameters
    ----------
    time : ndarray
        Time vector in seconds.
    energy_dict : dict
        Dictionary with 'kinetic', 'strain', 'damping', 'input' arrays.
    ax : matplotlib Axes, optional
        Axes to plot on.
    title : str
        Plot title.

    Returns
    -------
    matplotlib Axes
        The axes with the plot.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))

    ax.plot(time, energy_dict["kinetic"], label="Kinetic", linewidth=1.2)
    ax.plot(time, energy_dict["strain"], label="Strain", linewidth=1.2)
    ax.plot(time, energy_dict["damping"], label="Damping (cumulative)", linewidth=1.2)
    ax.plot(time, energy_dict["input"], label="Input (cumulative)", linewidth=1.2)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Energy (J)")
    ax.set_title(title)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    return ax


def create_results_figure(
    time: NDArray[np.floating],
    ground_acceleration: NDArray[np.floating],
    initial_displacement: NDArray[np.floating],
    calibrated_displacement: NDArray[np.floating],
    measured_displacement: NDArray[np.floating],
    calibration_iterations: NDArray[np.floating],
    calibration_nrmse: NDArray[np.floating],
    mc_mean: NDArray[np.floating],
    mc_lower: NDArray[np.floating],
    mc_upper: NDArray[np.floating],
    drift_ratios: NDArray[np.floating],
    floor: int = -1,
) -> plt.Figure:
    """
    Create comprehensive results figure with all plots.

    Parameters
    ----------
    time : ndarray
        Time vector.
    ground_acceleration : ndarray
        Ground acceleration in g.
    initial_displacement : ndarray
        Initial prediction displacement.
    calibrated_displacement : ndarray
        Calibrated prediction displacement.
    measured_displacement : ndarray
        Measured displacement.
    calibration_iterations : ndarray
        Calibration iteration numbers.
    calibration_nrmse : ndarray
        NRMSE at each iteration.
    mc_mean : ndarray
        Monte Carlo mean response.
    mc_lower : ndarray
        Monte Carlo lower bound.
    mc_upper : ndarray
        Monte Carlo upper bound.
    drift_ratios : ndarray
        Inter-story drift ratios.
    floor : int
        Floor to plot for displacement comparisons.

    Returns
    -------
    matplotlib Figure
        The complete figure.
    """
    fig = plt.figure(figsize=(14, 10))

    # Ground motion (top row, full width)
    ax1 = fig.add_subplot(3, 2, (1, 2))
    plot_ground_motion(time, ground_acceleration, ax=ax1)

    # Displacement comparison (middle left)
    ax2 = fig.add_subplot(3, 2, 3)
    plot_displacement_comparison(
        time,
        initial_displacement,
        calibrated_displacement,
        measured_displacement,
        floor=floor,
        ax=ax2,
    )

    # Calibration convergence (middle right)
    ax3 = fig.add_subplot(3, 2, 4)
    plot_calibration_convergence(calibration_iterations, calibration_nrmse, ax=ax3)

    # Uncertainty bounds (bottom left)
    ax4 = fig.add_subplot(3, 2, 5)
    plot_uncertainty_bounds(
        time,
        mc_mean,
        mc_lower,
        mc_upper,
        measured=measured_displacement,
        floor=floor,
        ax=ax4,
    )

    # Drift ratios (bottom right)
    ax5 = fig.add_subplot(3, 2, 6)
    plot_max_drifts(drift_ratios, ax=ax5, threshold=0.02)

    plt.tight_layout()

    return fig
