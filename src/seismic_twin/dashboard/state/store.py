"""
dcc.Store definitions for dashboard state management.

Stores are used to persist state between callbacks and across page navigation.
"""

from dash import dcc

from seismic_twin.dashboard.state.schemas import (
    BuildingParams,
    GroundMotionState,
    SimulationConfig,
    SimulationResults,
)


def create_stores() -> list:
    """Create all dcc.Store components for state management."""
    return [
        # Building parameters store
        dcc.Store(
            id="store-building-params",
            storage_type="session",
            data=BuildingParams().model_dump(),
        ),
        # Ground motion store
        dcc.Store(
            id="store-ground-motion",
            storage_type="session",
            data=GroundMotionState().model_dump(),
        ),
        # Simulation configuration store
        dcc.Store(
            id="store-simulation-config",
            storage_type="session",
            data=SimulationConfig().model_dump(),
        ),
        # Simulation results store
        dcc.Store(
            id="store-simulation-results",
            storage_type="session",
            data=SimulationResults().model_dump(),
        ),
        # Task ID store for background jobs
        dcc.Store(
            id="store-task-id",
            storage_type="memory",
            data=None,
        ),
        # UI state store (for transient UI state)
        dcc.Store(
            id="store-ui-state",
            storage_type="memory",
            data={
                "simulation_running": False,
                "last_error": None,
            },
        ),
    ]
