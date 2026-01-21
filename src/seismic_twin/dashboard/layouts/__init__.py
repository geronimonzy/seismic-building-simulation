"""Dashboard page layouts."""

from seismic_twin.dashboard.layouts.base import create_navbar, create_sidebar
from seismic_twin.dashboard.layouts.building import create_building_layout
from seismic_twin.dashboard.layouts.ground_motion import create_ground_motion_layout
from seismic_twin.dashboard.layouts.results import create_results_layout
from seismic_twin.dashboard.layouts.simulation import create_simulation_layout
from seismic_twin.dashboard.layouts.wave_prediction import create_wave_prediction_layout

__all__ = [
    "create_navbar",
    "create_sidebar",
    "create_building_layout",
    "create_ground_motion_layout",
    "create_simulation_layout",
    "create_results_layout",
    "create_wave_prediction_layout",
]
