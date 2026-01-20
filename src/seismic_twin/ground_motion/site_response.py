"""
Site Response and Soil Amplification

This module implements site response analysis based on NEHRP site classification
and provides frequency-dependent amplification factors for ground motion modification.

Site Classes (NEHRP/ASCE 7):
- A: Hard rock (Vs30 > 1500 m/s)
- B: Rock (760 < Vs30 <= 1500 m/s)
- C: Very dense soil / soft rock (360 < Vs30 <= 760 m/s)
- D: Stiff soil (180 < Vs30 <= 360 m/s)
- E: Soft clay (Vs30 < 180 m/s)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
from numpy.typing import NDArray


class SiteClass(Enum):
    """NEHRP site classification."""

    A = "A"  # Hard rock
    B = "B"  # Rock
    C = "C"  # Very dense soil / soft rock
    D = "D"  # Stiff soil
    E = "E"  # Soft clay


# Site class Vs30 boundaries (m/s)
VS30_BOUNDARIES = {
    SiteClass.A: (1500, float("inf")),
    SiteClass.B: (760, 1500),
    SiteClass.C: (360, 760),
    SiteClass.D: (180, 360),
    SiteClass.E: (0, 180),
}

# Typical Vs30 values for each site class (m/s)
TYPICAL_VS30 = {
    SiteClass.A: 2000,
    SiteClass.B: 1000,
    SiteClass.C: 500,
    SiteClass.D: 250,
    SiteClass.E: 120,
}

# Site period approximation: T_site ~ 4H/Vs30 where H is typical depth
# We use simplified resonance frequencies for each site class (Hz)
SITE_RESONANCE_FREQ = {
    SiteClass.A: 15.0,  # Very high - essentially no amplification
    SiteClass.B: 8.0,
    SiteClass.C: 4.0,
    SiteClass.D: 2.0,
    SiteClass.E: 1.0,
}

# Peak amplification factors at resonance
PEAK_AMPLIFICATION = {
    SiteClass.A: 1.0,
    SiteClass.B: 1.2,
    SiteClass.C: 1.5,
    SiteClass.D: 2.0,
    SiteClass.E: 3.0,
}


@dataclass
class SiteProperties:
    """Container for site properties."""

    site_class: SiteClass
    vs30: float  # Average shear wave velocity in top 30m (m/s)
    resonance_freq: float  # Site resonance frequency (Hz)
    peak_amplification: float  # Peak amplification factor
    soil_depth: Optional[float] = None  # Depth to bedrock (m)
    damping: float = 0.05  # Soil damping ratio

    @classmethod
    def from_vs30(cls, vs30: float, soil_depth: Optional[float] = None) -> "SiteProperties":
        """
        Create site properties from Vs30 value.

        Parameters
        ----------
        vs30 : float
            Average shear wave velocity in top 30m (m/s).
        soil_depth : float, optional
            Depth to bedrock in meters.

        Returns
        -------
        SiteProperties
            Site properties based on Vs30.
        """
        # Determine site class
        site_class = classify_site(vs30)

        # Estimate resonance frequency
        if soil_depth is not None and soil_depth > 0:
            # f = Vs / (4 * H) for fundamental mode
            resonance_freq = vs30 / (4 * soil_depth)
        else:
            resonance_freq = SITE_RESONANCE_FREQ[site_class]

        # Estimate peak amplification (inverse relationship with Vs30)
        # Using simplified impedance contrast model
        vs_rock = 760  # Reference rock velocity
        impedance_ratio = vs_rock / vs30
        peak_amplification = min(4.0, max(1.0, impedance_ratio**0.5 * 1.2))

        return cls(
            site_class=site_class,
            vs30=vs30,
            resonance_freq=resonance_freq,
            peak_amplification=peak_amplification,
            soil_depth=soil_depth,
        )

    @classmethod
    def from_site_class(cls, site_class: SiteClass | str) -> "SiteProperties":
        """
        Create site properties from site class using typical values.

        Parameters
        ----------
        site_class : SiteClass or str
            NEHRP site class (A, B, C, D, or E).

        Returns
        -------
        SiteProperties
            Site properties with typical values.
        """
        if isinstance(site_class, str):
            site_class = SiteClass(site_class.upper())

        return cls(
            site_class=site_class,
            vs30=TYPICAL_VS30[site_class],
            resonance_freq=SITE_RESONANCE_FREQ[site_class],
            peak_amplification=PEAK_AMPLIFICATION[site_class],
        )


def classify_site(vs30: float) -> SiteClass:
    """
    Classify site based on Vs30 value.

    Parameters
    ----------
    vs30 : float
        Average shear wave velocity in top 30m (m/s).

    Returns
    -------
    SiteClass
        NEHRP site classification.
    """
    if vs30 > 1500:
        return SiteClass.A
    elif vs30 > 760:
        return SiteClass.B
    elif vs30 > 360:
        return SiteClass.C
    elif vs30 > 180:
        return SiteClass.D
    else:
        return SiteClass.E


def compute_site_amplification(
    frequencies: NDArray[np.floating],
    site: SiteProperties,
) -> NDArray[np.floating]:
    """
    Compute frequency-dependent site amplification factors.

    Uses a simplified single-layer soil model with:
    - Low-frequency amplification proportional to impedance contrast
    - Resonance peak at site frequency
    - High-frequency de-amplification (soil damping)

    Parameters
    ----------
    frequencies : ndarray
        Frequencies at which to compute amplification (Hz).
    site : SiteProperties
        Site properties.

    Returns
    -------
    ndarray
        Amplification factors at each frequency.
    """
    f = np.asarray(frequencies)
    f0 = site.resonance_freq
    A0 = site.peak_amplification
    xi = site.damping

    # Simplified transfer function magnitude
    # |H(f)| = A0 / sqrt((1 - (f/f0)^2)^2 + (2*xi*f/f0)^2)
    # With modifications for physical behavior

    # Avoid division by zero
    f_safe = np.maximum(f, 1e-6)

    # Frequency ratio
    r = f_safe / f0

    # Transfer function (SDOF-like response)
    denominator = np.sqrt((1 - r**2) ** 2 + (2 * xi * r) ** 2)

    # Baseline amplification (low-frequency plateau)
    baseline = 1.0 + (A0 - 1.0) * 0.5

    # Full transfer function
    amplification = baseline * A0 / (denominator * A0)

    # Clip to physical range
    amplification = np.clip(amplification, 0.5, A0 * 1.5)

    # High-frequency roll-off (soil damping effect)
    # Reduce amplification above ~2*f0
    high_freq_factor = 1.0 / (1.0 + (f_safe / (3 * f0)) ** 2)
    amplification = 1.0 + (amplification - 1.0) * high_freq_factor

    return amplification


def apply_site_response(
    time: NDArray[np.floating],
    acceleration: NDArray[np.floating],
    site: SiteProperties | SiteClass | str,
) -> NDArray[np.floating]:
    """
    Apply site response amplification to ground motion.

    Parameters
    ----------
    time : ndarray
        Time vector in seconds.
    acceleration : ndarray
        Input (rock/reference) acceleration time history in g.
    site : SiteProperties, SiteClass, or str
        Site properties or site class.

    Returns
    -------
    ndarray
        Amplified acceleration time history in g.
    """
    # Convert to SiteProperties if needed
    if isinstance(site, str):
        site = SiteProperties.from_site_class(site)
    elif isinstance(site, SiteClass):
        site = SiteProperties.from_site_class(site)

    # If site class A (hard rock), no amplification needed
    if site.site_class == SiteClass.A:
        return acceleration.copy()

    dt = time[1] - time[0]
    n_points = len(acceleration)

    # Compute FFT
    acc_fft = np.fft.rfft(acceleration)
    frequencies = np.fft.rfftfreq(n_points, dt)

    # Compute amplification factors
    amplification = compute_site_amplification(frequencies, site)

    # Apply amplification in frequency domain
    acc_fft_amplified = acc_fft * amplification

    # Inverse FFT
    acc_amplified = np.fft.irfft(acc_fft_amplified, n=n_points)

    return acc_amplified


def compute_site_period(vs30: float, depth: float) -> float:
    """
    Compute fundamental site period.

    Parameters
    ----------
    vs30 : float
        Average shear wave velocity (m/s).
    depth : float
        Soil layer depth (m).

    Returns
    -------
    float
        Fundamental site period in seconds.
    """
    if depth <= 0 or vs30 <= 0:
        return 0.0
    return 4 * depth / vs30


def get_nehrp_coefficients(
    site_class: SiteClass | str,
    ss: float,
    s1: float,
) -> tuple[float, float]:
    """
    Get NEHRP site coefficients Fa and Fv.

    Based on ASCE 7-22 Tables 11.4-1 and 11.4-2.

    Parameters
    ----------
    site_class : SiteClass or str
        NEHRP site class.
    ss : float
        Mapped short-period spectral acceleration (g).
    s1 : float
        Mapped 1-second spectral acceleration (g).

    Returns
    -------
    tuple[float, float]
        Site coefficients (Fa, Fv).
    """
    if isinstance(site_class, str):
        site_class = SiteClass(site_class.upper())

    # Simplified Fa values (short-period amplification)
    # These are approximate - actual values depend on Ss
    fa_table = {
        SiteClass.A: 0.8,
        SiteClass.B: 0.9,
        SiteClass.C: 1.1,
        SiteClass.D: 1.2,
        SiteClass.E: 1.4,
    }

    # Simplified Fv values (long-period amplification)
    fv_table = {
        SiteClass.A: 0.8,
        SiteClass.B: 0.8,
        SiteClass.C: 1.4,
        SiteClass.D: 1.8,
        SiteClass.E: 2.4,
    }

    # Adjust for actual Ss and S1 values (simplified interpolation)
    fa = fa_table[site_class]
    fv = fv_table[site_class]

    # Reduce amplification at high shaking levels (nonlinear soil response)
    if ss > 1.0:
        fa *= 0.9
    if s1 > 0.5:
        fv *= 0.9

    return fa, fv


def design_response_spectrum(
    site_class: SiteClass | str,
    ss: float,
    s1: float,
    tl: float = 8.0,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Generate ASCE 7 design response spectrum.

    Parameters
    ----------
    site_class : SiteClass or str
        NEHRP site class.
    ss : float
        Mapped short-period spectral acceleration (g).
    s1 : float
        Mapped 1-second spectral acceleration (g).
    tl : float
        Long-period transition period (s).

    Returns
    -------
    tuple[ndarray, ndarray]
        Periods (s) and spectral accelerations (g).
    """
    fa, fv = get_nehrp_coefficients(site_class, ss, s1)

    # Site-adjusted spectral values
    sms = fa * ss
    sm1 = fv * s1

    # Design spectral values (2/3 factor for risk-targeted)
    sds = (2 / 3) * sms
    sd1 = (2 / 3) * sm1

    # Control periods
    t0 = 0.2 * sd1 / sds
    ts = sd1 / sds

    # Generate spectrum
    periods = np.logspace(-2, 1, 200)  # 0.01 to 10 seconds
    sa = np.zeros_like(periods)

    for i, t in enumerate(periods):
        if t < t0:
            # Rising portion
            sa[i] = sds * (0.4 + 0.6 * t / t0)
        elif t < ts:
            # Constant acceleration plateau
            sa[i] = sds
        elif t < tl:
            # Velocity-controlled region
            sa[i] = sd1 / t
        else:
            # Displacement-controlled region
            sa[i] = sd1 * tl / t**2

    return periods, sa
