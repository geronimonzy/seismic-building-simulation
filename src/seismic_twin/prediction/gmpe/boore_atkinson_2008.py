"""
Boore and Atkinson (2008) Ground Motion Prediction Equation

Implementation of the BA08 GMPE from:
Boore, D. M., and G. M. Atkinson (2008). Ground-motion prediction equations
for the average horizontal component of PGA, PGV, and 5%-damped PSA at
spectral periods between 0.01 s and 10.0 s, Earthquake Spectra 24, 99-138.

Reference: https://doi.org/10.1193/1.2830434
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from seismic_twin.prediction.gmpe.base import BaseGMPE, GMPEInput, GMPEOutput


# BA08 coefficient table
# Format: period, e1, e2, e3, e4, e5, e6, e7, Mh, c1, c2, c3, h, sigma, sigma_inter, sigma_intra
# Coefficients from Table 1 of Boore & Atkinson (2008)
_BA08_COEFFICIENTS = {
    # period: (e1, e2, e3, e4, e5, e6, e7, Mh, c1, c2, c3, h, sigma, sigma_inter, sigma_intra)
    0.000: (-0.52883, 0.28067, 0.01170, -0.04987, 1.02886, -0.21259, 6.41, 6.75, -0.66050, 0.11970, -0.01151, 1.35, 0.566, 0.256, 0.502),  # PGA
    0.010: (-0.52883, 0.28067, 0.01170, -0.04987, 1.02886, -0.21259, 6.41, 6.75, -0.66050, 0.11970, -0.01151, 1.35, 0.566, 0.256, 0.502),
    0.020: (-0.49429, 0.28183, 0.01152, -0.04841, 1.00316, -0.22356, 6.41, 6.75, -0.66220, 0.12000, -0.01151, 1.35, 0.569, 0.260, 0.506),
    0.030: (-0.30596, 0.28241, 0.01136, -0.04703, 0.94593, -0.23979, 6.41, 6.75, -0.66620, 0.12280, -0.01151, 1.35, 0.578, 0.269, 0.511),
    0.050: (0.16977, 0.28205, 0.01100, -0.04459, 0.83183, -0.26556, 6.41, 6.75, -0.69050, 0.13170, -0.01151, 1.35, 0.598, 0.290, 0.523),
    0.075: (0.52135, 0.28085, 0.01042, -0.04243, 0.76837, -0.27724, 6.41, 6.75, -0.71700, 0.13980, -0.01151, 1.55, 0.617, 0.306, 0.536),
    0.100: (0.56648, 0.28025, 0.00984, -0.04053, 0.74980, -0.28229, 6.41, 6.75, -0.72050, 0.14180, -0.01151, 1.68, 0.631, 0.318, 0.545),
    0.150: (0.48664, 0.27852, 0.00888, -0.03731, 0.73875, -0.28693, 6.41, 6.75, -0.71080, 0.14230, -0.01151, 1.86, 0.648, 0.332, 0.556),
    0.200: (0.32916, 0.27698, 0.00811, -0.03479, 0.74483, -0.28847, 6.41, 6.75, -0.69700, 0.14070, -0.01151, 1.98, 0.659, 0.342, 0.564),
    0.250: (0.17227, 0.27571, 0.00748, -0.03271, 0.75630, -0.28838, 6.41, 6.75, -0.68280, 0.13820, -0.01151, 2.07, 0.667, 0.350, 0.570),
    0.300: (0.03167, 0.27468, 0.00695, -0.03096, 0.76837, -0.28735, 6.41, 6.75, -0.66920, 0.13520, -0.01151, 2.14, 0.672, 0.356, 0.574),
    0.400: (-0.21352, 0.27312, 0.00609, -0.02812, 0.78920, -0.28403, 6.41, 6.75, -0.64630, 0.12880, -0.01151, 2.24, 0.680, 0.366, 0.580),
    0.500: (-0.40800, 0.27200, 0.00541, -0.02593, 0.80533, -0.28014, 6.41, 6.75, -0.62700, 0.12270, -0.01151, 2.32, 0.685, 0.373, 0.584),
    0.750: (-0.76780, 0.27019, 0.00422, -0.02175, 0.82949, -0.27038, 6.41, 6.75, -0.58720, 0.11000, -0.01151, 2.46, 0.693, 0.385, 0.590),
    1.000: (-1.04970, 0.26913, 0.00331, -0.01857, 0.84458, -0.26119, 6.41, 6.75, -0.55560, 0.09900, -0.01151, 2.54, 0.698, 0.393, 0.594),
    1.500: (-1.49460, 0.26802, 0.00189, -0.01368, 0.86155, -0.24544, 6.41, 6.75, -0.50830, 0.08020, -0.01151, 2.66, 0.704, 0.405, 0.600),
    2.000: (-1.85590, 0.26748, 0.00079, -0.01003, 0.87206, -0.23270, 6.41, 6.75, -0.47240, 0.06430, -0.01151, 2.73, 0.708, 0.413, 0.603),
    3.000: (-2.45500, 0.26696, -0.00103, -0.00446, 0.88547, -0.21287, 6.41, 6.75, -0.42050, 0.03890, -0.01151, 2.83, 0.713, 0.423, 0.608),
    4.000: (-2.93760, 0.26671, -0.00242, -0.00022, 0.89234, -0.19798, 6.41, 6.75, -0.38420, 0.01870, -0.01151, 2.89, 0.717, 0.430, 0.611),
    5.000: (-3.34590, 0.26660, -0.00355, 0.00333, 0.89588, -0.18669, 6.41, 6.75, -0.35650, 0.00220, -0.01151, 2.93, 0.719, 0.435, 0.613),
    7.500: (-4.12060, 0.26652, -0.00586, 0.01048, 0.90108, -0.16496, 6.41, 6.75, -0.30690, -0.02620, -0.01151, 2.99, 0.723, 0.444, 0.618),
    10.00: (-4.72850, 0.26651, -0.00774, 0.01610, 0.90387, -0.14918, 6.41, 6.75, -0.27170, -0.04800, -0.01151, 3.04, 0.726, 0.450, 0.621),
}


class BooreAtkinson2008(BaseGMPE):
    """
    Boore and Atkinson (2008) Ground Motion Prediction Equation.

    Predicts geometric mean horizontal component of PGA, PGV, and 5%-damped PSA
    for shallow crustal earthquakes in active tectonic regions.

    Valid for:
    - Magnitude: 5.0 to 8.0
    - Distance: 0 to 200 km (Rjb)
    - Periods: 0.01 to 10 s

    Reference
    ---------
    Boore, D. M., and G. M. Atkinson (2008). Ground-motion prediction equations
    for the average horizontal component of PGA, PGV, and 5%-damped PSA at
    spectral periods between 0.01 s and 10.0 s, Earthquake Spectra 24, 99-138.
    """

    def __init__(self) -> None:
        """Initialize the BA08 GMPE."""
        self._periods = np.array(sorted(_BA08_COEFFICIENTS.keys()))

    @property
    def name(self) -> str:
        """Model name."""
        return "Boore-Atkinson 2008"

    @property
    def valid_periods(self) -> NDArray[np.floating]:
        """Valid spectral periods for this GMPE."""
        return self._periods

    def _get_coefficients(self, period: float) -> tuple:
        """
        Get interpolated coefficients for a given period.

        Parameters
        ----------
        period : float
            Spectral period in seconds.

        Returns
        -------
        tuple
            Interpolated coefficients.
        """
        # Find bracketing periods
        if period <= 0:
            period = 0.0  # Use PGA coefficients

        if period in _BA08_COEFFICIENTS:
            return _BA08_COEFFICIENTS[period]

        # Linear interpolation in log space for period
        log_period = np.log(period) if period > 0 else -np.inf
        log_periods = np.array([np.log(p) if p > 0 else -np.inf for p in self._periods])

        # Find bracketing indices
        idx = np.searchsorted(self._periods, period)

        if idx == 0:
            return _BA08_COEFFICIENTS[self._periods[0]]
        if idx >= len(self._periods):
            return _BA08_COEFFICIENTS[self._periods[-1]]

        # Interpolate between adjacent periods
        p1 = self._periods[idx - 1]
        p2 = self._periods[idx]
        c1 = _BA08_COEFFICIENTS[p1]
        c2 = _BA08_COEFFICIENTS[p2]

        # Log-linear interpolation
        if p1 > 0 and p2 > 0:
            w = (np.log(period) - np.log(p1)) / (np.log(p2) - np.log(p1))
        else:
            w = (period - p1) / (p2 - p1)

        interpolated = tuple(c1[i] + w * (c2[i] - c1[i]) for i in range(len(c1)))
        return interpolated

    def predict(self, params: GMPEInput) -> GMPEOutput:
        """
        Predict ground motion for given parameters.

        Parameters
        ----------
        params : GMPEInput
            Input parameters (magnitude, distance, vs30, period).

        Returns
        -------
        GMPEOutput
            Predicted median SA and uncertainty.
        """
        M = params.magnitude
        Rjb = params.distance_rjb
        Vs30 = params.vs30
        T = params.period

        # Get coefficients
        coeffs = self._get_coefficients(T)
        e1, e2, e3, e4, e5, e6, e7, Mh, c1, c2, c3, h, sigma, sigma_inter, sigma_intra = coeffs

        # Magnitude term (bilinear with hinge at Mh)
        if M <= Mh:
            Fm = e1 + e2 * (M - Mh) + e3 * (M - Mh) ** 2
        else:
            Fm = e1 + e4 * (M - Mh)

        # Distance term
        # R = sqrt(Rjb^2 + h^2)
        R = np.sqrt(Rjb**2 + h**2)

        # Distance scaling
        Fd = (c1 + c2 * (M - 4.5)) * np.log(R / 1.0) + c3 * (R - 1.0)

        # Site term (simplified - linear Vs30 scaling)
        # Full BA08 has nonlinear site response, using simplified linear here
        # For Vs30 < Vref (760): amplification (positive Fs)
        # For Vs30 > Vref: de-amplification (negative Fs)
        Vref = 760.0  # Reference velocity
        # Use simplified linear site amplification model
        # Coefficient of about -0.6 gives ~2x amplification at Vs30=180
        blin = -0.6
        Fs = blin * np.log(Vs30 / Vref)

        # Total ln(Sa)
        ln_sa = Fm + Fd + Fs

        # Convert to g
        median_sa = np.exp(ln_sa)

        return GMPEOutput(
            median_sa=median_sa,
            sigma_total=sigma,
            sigma_inter=sigma_inter,
            sigma_intra=sigma_intra,
        )

    def predict_pga_at_distance(
        self,
        magnitude: float,
        distances: NDArray[np.floating],
        vs30: float = 760.0,
    ) -> NDArray[np.floating]:
        """
        Predict PGA at multiple distances.

        Parameters
        ----------
        magnitude : float
            Moment magnitude.
        distances : ndarray
            Array of Rjb distances in km.
        vs30 : float
            Shear-wave velocity in m/s.

        Returns
        -------
        ndarray
            Array of predicted PGA values in g.
        """
        pga_values = np.zeros(len(distances))
        for i, dist in enumerate(distances):
            params = GMPEInput(
                magnitude=magnitude,
                distance_rjb=dist,
                vs30=vs30,
                period=0.0,
            )
            pga_values[i] = self.predict(params).median_sa
        return pga_values

    def compute_scale_factor(
        self,
        magnitude: float,
        source_distance: float,
        target_distance: float,
        vs30: float = 760.0,
    ) -> float:
        """
        Compute amplitude scaling factor between two distances.

        This is used for waveform prediction to scale a recorded waveform
        from a source station to a target location.

        Parameters
        ----------
        magnitude : float
            Earthquake magnitude.
        source_distance : float
            Source station Rjb distance in km.
        target_distance : float
            Target location Rjb distance in km.
        vs30 : float
            Shear-wave velocity in m/s.

        Returns
        -------
        float
            Scale factor (target_pga / source_pga).
        """
        source_pga = self.predict_pga(magnitude, source_distance, vs30)
        target_pga = self.predict_pga(magnitude, target_distance, vs30)

        if source_pga <= 0:
            return 1.0

        return target_pga / source_pga
