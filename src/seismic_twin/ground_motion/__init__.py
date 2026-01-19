"""Ground motion module for earthquake input generation."""

from seismic_twin.ground_motion.synthetic import (
    generate_synthetic_ground_motion,
    read_bbp_seismogram,
)

__all__ = ["generate_synthetic_ground_motion", "read_bbp_seismogram"]
