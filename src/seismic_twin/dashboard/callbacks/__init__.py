"""Dashboard callbacks."""

from dash import Dash

from seismic_twin.dashboard.callbacks.building_callbacks import register_building_callbacks
from seismic_twin.dashboard.callbacks.ground_motion_callbacks import (
    register_ground_motion_callbacks,
)
from seismic_twin.dashboard.callbacks.results_callbacks import register_results_callbacks
from seismic_twin.dashboard.callbacks.simulation_callbacks import register_simulation_callbacks
from seismic_twin.dashboard.callbacks.wave_prediction_callbacks import (
    register_wave_prediction_callbacks,
)


def register_all_callbacks(app: Dash) -> None:
    """Register all callbacks with the Dash app."""
    register_building_callbacks(app)
    register_ground_motion_callbacks(app)
    register_simulation_callbacks(app)
    register_results_callbacks(app)
    register_wave_prediction_callbacks(app)


__all__ = [
    "register_all_callbacks",
    "register_building_callbacks",
    "register_ground_motion_callbacks",
    "register_simulation_callbacks",
    "register_results_callbacks",
    "register_wave_prediction_callbacks",
]
