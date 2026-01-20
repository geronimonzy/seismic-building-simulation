"""Ground motion module for earthquake input generation and site response."""

from seismic_twin.ground_motion.record import (
    GroundMotionRecord,
    GroundMotionSuite,
)
from seismic_twin.ground_motion.site_response import (
    SiteClass,
    SiteProperties,
    apply_site_response,
    classify_site,
    compute_site_amplification,
    design_response_spectrum,
    get_nehrp_coefficients,
)
from seismic_twin.ground_motion.synthetic import (
    apply_highpass_filter,
    baseline_correction,
    compute_response_spectrum,
    generate_2component_ground_motion,
    generate_harmonic_ground_motion,
    generate_site_modified_motion,
    generate_synthetic_ground_motion,
    generate_vertical_component,
    read_bbp_seismogram,
)

__all__ = [
    # Record classes
    "GroundMotionRecord",
    "GroundMotionSuite",
    # Synthetic generation
    "generate_synthetic_ground_motion",
    "generate_2component_ground_motion",
    "generate_site_modified_motion",
    "generate_vertical_component",
    "generate_harmonic_ground_motion",
    "read_bbp_seismogram",
    # Processing
    "baseline_correction",
    "apply_highpass_filter",
    "compute_response_spectrum",
    # Site response
    "SiteClass",
    "SiteProperties",
    "classify_site",
    "compute_site_amplification",
    "apply_site_response",
    "get_nehrp_coefficients",
    "design_response_spectrum",
]
