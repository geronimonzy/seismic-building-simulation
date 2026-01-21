"""
Base classes for Ground Motion Prediction Equations (GMPEs).

This module provides abstract base classes and data structures for
implementing GMPEs used in seismic hazard analysis.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class GMPEInput:
    """
    Input parameters for GMPE prediction.

    Attributes
    ----------
    magnitude : float
        Earthquake moment magnitude (Mw).
    distance_rjb : float
        Joyner-Boore distance in km (closest distance to fault surface projection).
    vs30 : float
        Time-averaged shear-wave velocity in top 30m (m/s).
        Default is 760 m/s (NEHRP B/C boundary).
    period : float
        Spectral period in seconds. 0.0 corresponds to PGA.
    """

    magnitude: float
    distance_rjb: float
    vs30: float = 760.0
    period: float = 0.0

    def __post_init__(self) -> None:
        """Validate input parameters."""
        if self.magnitude < 0 or self.magnitude > 10:
            raise ValueError(f"Magnitude must be between 0 and 10, got {self.magnitude}")
        if self.distance_rjb < 0:
            raise ValueError(f"Distance must be non-negative, got {self.distance_rjb}")
        if self.vs30 <= 0:
            raise ValueError(f"Vs30 must be positive, got {self.vs30}")
        if self.period < 0:
            raise ValueError(f"Period must be non-negative, got {self.period}")


@dataclass
class GMPEOutput:
    """
    Output from GMPE prediction.

    Attributes
    ----------
    median_sa : float
        Median spectral acceleration in g.
    sigma_total : float
        Total standard deviation (natural log units).
    sigma_inter : float
        Inter-event standard deviation (natural log units).
    sigma_intra : float
        Intra-event standard deviation (natural log units).
    """

    median_sa: float
    sigma_total: float
    sigma_inter: float = 0.0
    sigma_intra: float = 0.0

    def __post_init__(self) -> None:
        """Compute total sigma if not provided."""
        if self.sigma_total == 0 and (self.sigma_inter > 0 or self.sigma_intra > 0):
            self.sigma_total = np.sqrt(self.sigma_inter**2 + self.sigma_intra**2)

    @property
    def plus_sigma(self) -> float:
        """Median + 1 sigma value in g."""
        return self.median_sa * np.exp(self.sigma_total)

    @property
    def minus_sigma(self) -> float:
        """Median - 1 sigma value in g."""
        return self.median_sa * np.exp(-self.sigma_total)


class BaseGMPE(ABC):
    """
    Abstract base class for Ground Motion Prediction Equations.

    GMPEs predict ground motion intensity measures (e.g., PGA, Sa) as
    functions of earthquake magnitude, distance, and site conditions.

    Subclasses must implement:
    - predict(): Core prediction for single input
    - name: Human-readable model name
    - valid_periods: Array of valid spectral periods
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the GMPE model."""
        pass

    @property
    @abstractmethod
    def valid_periods(self) -> NDArray[np.floating]:
        """Array of valid spectral periods for this GMPE."""
        pass

    @abstractmethod
    def predict(self, params: GMPEInput) -> GMPEOutput:
        """
        Predict ground motion for given input parameters.

        Parameters
        ----------
        params : GMPEInput
            Input parameters (magnitude, distance, vs30, period).

        Returns
        -------
        GMPEOutput
            Predicted median SA and uncertainty.
        """
        pass

    def predict_pga(
        self,
        magnitude: float,
        distance_rjb: float,
        vs30: float = 760.0,
    ) -> float:
        """
        Predict Peak Ground Acceleration.

        Parameters
        ----------
        magnitude : float
            Moment magnitude.
        distance_rjb : float
            Joyner-Boore distance in km.
        vs30 : float
            Shear-wave velocity in m/s.

        Returns
        -------
        float
            Predicted median PGA in g.
        """
        params = GMPEInput(
            magnitude=magnitude,
            distance_rjb=distance_rjb,
            vs30=vs30,
            period=0.0,
        )
        return self.predict(params).median_sa

    def predict_spectrum(
        self,
        magnitude: float,
        distance_rjb: float,
        periods: NDArray[np.floating] | None = None,
        vs30: float = 760.0,
    ) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """
        Predict response spectrum for multiple periods.

        Parameters
        ----------
        magnitude : float
            Moment magnitude.
        distance_rjb : float
            Joyner-Boore distance in km.
        periods : ndarray, optional
            Spectral periods in seconds. If None, uses model's valid_periods.
        vs30 : float
            Shear-wave velocity in m/s.

        Returns
        -------
        tuple[ndarray, ndarray]
            (periods, Sa) - periods in seconds and spectral accelerations in g.
        """
        if periods is None:
            periods = self.valid_periods

        sa_values = np.zeros(len(periods))
        for i, period in enumerate(periods):
            params = GMPEInput(
                magnitude=magnitude,
                distance_rjb=distance_rjb,
                vs30=vs30,
                period=period,
            )
            sa_values[i] = self.predict(params).median_sa

        return periods, sa_values

    def predict_pga_with_sigma(
        self,
        magnitude: float,
        distance_rjb: float,
        vs30: float = 760.0,
    ) -> GMPEOutput:
        """
        Predict PGA with uncertainty.

        Parameters
        ----------
        magnitude : float
            Moment magnitude.
        distance_rjb : float
            Joyner-Boore distance in km.
        vs30 : float
            Shear-wave velocity in m/s.

        Returns
        -------
        GMPEOutput
            Predicted PGA with uncertainty.
        """
        params = GMPEInput(
            magnitude=magnitude,
            distance_rjb=distance_rjb,
            vs30=vs30,
            period=0.0,
        )
        return self.predict(params)
