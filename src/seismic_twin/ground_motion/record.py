"""
Ground Motion Record Data Structures

This module provides dataclasses for storing and manipulating ground motion
records with single or multiple components.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass
class GroundMotionRecord:
    """
    Container for ground motion record with optional multi-component data.

    Supports single horizontal component or horizontal + vertical components.
    All accelerations are stored in g units.

    Attributes
    ----------
    time : ndarray
        Time vector in seconds.
    horizontal : ndarray
        Horizontal acceleration component in g.
    vertical : ndarray, optional
        Vertical acceleration component in g.
    dt : float
        Time step in seconds.
    metadata : dict
        Additional metadata (source, station, event info, etc.).
    """

    time: NDArray[np.floating]
    horizontal: NDArray[np.floating]
    vertical: NDArray[np.floating] | None = None
    dt: float = field(init=False)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Compute derived properties."""
        if len(self.time) > 1:
            self.dt = float(self.time[1] - self.time[0])
        else:
            self.dt = 0.01

        # Ensure arrays
        self.time = np.asarray(self.time)
        self.horizontal = np.asarray(self.horizontal)
        if self.vertical is not None:
            self.vertical = np.asarray(self.vertical)

    @property
    def n_points(self) -> int:
        """Number of time points."""
        return len(self.time)

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        return float(self.time[-1] - self.time[0])

    @property
    def pga_horizontal(self) -> float:
        """Peak ground acceleration (horizontal) in g."""
        return float(np.max(np.abs(self.horizontal)))

    @property
    def pga_vertical(self) -> float | None:
        """Peak ground acceleration (vertical) in g."""
        if self.vertical is None:
            return None
        return float(np.max(np.abs(self.vertical)))

    @property
    def pga(self) -> float:
        """Peak ground acceleration (maximum of all components) in g."""
        pga = self.pga_horizontal
        if self.vertical is not None:
            pga = max(pga, self.pga_vertical)
        return pga

    @property
    def has_vertical(self) -> bool:
        """Whether vertical component is available."""
        return self.vertical is not None

    @property
    def v_h_ratio(self) -> float | None:
        """Vertical to horizontal PGA ratio."""
        if self.vertical is None:
            return None
        if self.pga_horizontal > 0:
            return self.pga_vertical / self.pga_horizontal
        return None

    def get_component(self, component: str) -> NDArray[np.floating]:
        """
        Get acceleration for specified component.

        Parameters
        ----------
        component : str
            Component name: 'horizontal', 'H', 'vertical', 'V', or 'Z'.

        Returns
        -------
        ndarray
            Acceleration time history.

        Raises
        ------
        ValueError
            If component not available.
        """
        component = component.upper()
        if component in ("HORIZONTAL", "H", "X", "E", "N"):
            return self.horizontal
        elif component in ("VERTICAL", "V", "Z", "UP"):
            if self.vertical is None:
                raise ValueError("Vertical component not available")
            return self.vertical
        else:
            raise ValueError(f"Unknown component: {component}")

    def scale(self, factor: float, component: str = "all") -> GroundMotionRecord:
        """
        Scale ground motion by a factor.

        Parameters
        ----------
        factor : float
            Scaling factor.
        component : str
            'horizontal', 'vertical', or 'all'.

        Returns
        -------
        GroundMotionRecord
            New scaled record.
        """
        h_scaled = self.horizontal.copy()
        v_scaled = self.vertical.copy() if self.vertical is not None else None

        component = component.lower()
        if component in ("horizontal", "h", "all"):
            h_scaled *= factor
        if component in ("vertical", "v", "all") and v_scaled is not None:
            v_scaled *= factor

        return GroundMotionRecord(
            time=self.time.copy(),
            horizontal=h_scaled,
            vertical=v_scaled,
            metadata=self.metadata.copy(),
        )

    def scale_to_pga(self, target_pga: float, component: str = "horizontal") -> GroundMotionRecord:
        """
        Scale record to achieve target PGA.

        Parameters
        ----------
        target_pga : float
            Target PGA in g.
        component : str
            Component to use for scaling reference ('horizontal' or 'vertical').

        Returns
        -------
        GroundMotionRecord
            Scaled record.
        """
        if component.lower() in ("horizontal", "h"):
            current_pga = self.pga_horizontal
        else:
            current_pga = self.pga_vertical or self.pga_horizontal

        if current_pga > 0:
            factor = target_pga / current_pga
        else:
            factor = 1.0

        return self.scale(factor, component="all")

    def trim(self, start_time: float, end_time: float) -> GroundMotionRecord:
        """
        Trim record to specified time window.

        Parameters
        ----------
        start_time : float
            Start time in seconds.
        end_time : float
            End time in seconds.

        Returns
        -------
        GroundMotionRecord
            Trimmed record.
        """
        mask = (self.time >= start_time) & (self.time <= end_time)
        return GroundMotionRecord(
            time=self.time[mask] - start_time,
            horizontal=self.horizontal[mask],
            vertical=self.vertical[mask] if self.vertical is not None else None,
            metadata=self.metadata.copy(),
        )

    def resample(self, new_dt: float) -> GroundMotionRecord:
        """
        Resample record to new time step.

        Parameters
        ----------
        new_dt : float
            New time step in seconds.

        Returns
        -------
        GroundMotionRecord
            Resampled record.
        """
        from scipy.interpolate import interp1d

        new_time = np.arange(0, self.duration + new_dt, new_dt)

        h_interp = interp1d(self.time, self.horizontal, kind="linear", fill_value=0.0)
        h_new = h_interp(new_time)

        v_new = None
        if self.vertical is not None:
            v_interp = interp1d(self.time, self.vertical, kind="linear", fill_value=0.0)
            v_new = v_interp(new_time)

        return GroundMotionRecord(
            time=new_time,
            horizontal=h_new,
            vertical=v_new,
            metadata=self.metadata.copy(),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        data = {
            "time": self.time.tolist(),
            "horizontal": self.horizontal.tolist(),
            "metadata": self.metadata,
        }
        if self.vertical is not None:
            data["vertical"] = self.vertical.tolist()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> GroundMotionRecord:
        """Create from dictionary."""
        return cls(
            time=np.array(data["time"]),
            horizontal=np.array(data["horizontal"]),
            vertical=np.array(data["vertical"]) if "vertical" in data else None,
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        v_info = f", V/H={self.v_h_ratio:.2f}" if self.has_vertical else ""
        return (
            f"GroundMotionRecord(duration={self.duration:.1f}s, "
            f"PGA_H={self.pga_horizontal:.3f}g{v_info})"
        )


@dataclass
class GroundMotionSuite:
    """
    Collection of ground motion records for analysis.

    Useful for Monte Carlo analysis or comparing multiple scenarios.
    """

    records: list[GroundMotionRecord] = field(default_factory=list)
    name: str = "Unnamed Suite"
    metadata: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> GroundMotionRecord:
        return self.records[idx]

    def __iter__(self):
        return iter(self.records)

    def add(self, record: GroundMotionRecord) -> None:
        """Add a record to the suite."""
        self.records.append(record)

    @property
    def pga_statistics(self) -> dict:
        """Compute PGA statistics across all records."""
        pgas = [r.pga_horizontal for r in self.records]
        return {
            "mean": np.mean(pgas),
            "std": np.std(pgas),
            "min": np.min(pgas),
            "max": np.max(pgas),
            "median": np.median(pgas),
        }

    def scale_all_to_pga(self, target_pga: float) -> GroundMotionSuite:
        """Scale all records to target PGA."""
        scaled_records = [r.scale_to_pga(target_pga) for r in self.records]
        return GroundMotionSuite(
            records=scaled_records,
            name=f"{self.name} (scaled to {target_pga}g)",
            metadata=self.metadata.copy(),
        )
