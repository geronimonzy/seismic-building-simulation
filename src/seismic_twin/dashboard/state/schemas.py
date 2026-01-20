"""
Pydantic schemas for dashboard state serialization.

These models define the structure of data stored in dcc.Store components
and passed between callbacks.
"""

from typing import Optional

from pydantic import BaseModel, Field


class BuildingParams(BaseModel):
    """Building configuration parameters."""

    n_stories: int = Field(default=3, ge=1, le=20, description="Number of stories")
    masses: list[float] = Field(
        default_factory=lambda: [100000.0, 100000.0, 100000.0],
        description="Floor masses in kg",
    )
    stiffnesses: list[float] = Field(
        default_factory=lambda: [1e8, 1e8, 1e8],
        description="Inter-story stiffnesses in N/m",
    )
    damping_ratio: float = Field(default=0.05, ge=0.01, le=0.15, description="Modal damping ratio")
    story_heights: list[float] = Field(
        default_factory=lambda: [3.5, 3.5, 3.5],
        description="Story heights in meters",
    )
    uniform_mass: bool = Field(default=True, description="Use uniform mass per floor")
    uniform_stiffness: bool = Field(default=True, description="Use uniform stiffness per story")
    uniform_height: bool = Field(default=True, description="Use uniform story height")

    def to_arrays(self) -> tuple[list[float], list[float], list[float]]:
        """Return masses, stiffnesses, story_heights as lists."""
        return self.masses, self.stiffnesses, self.story_heights


class GroundMotionState(BaseModel):
    """Ground motion state for storage."""

    time: list[float] = Field(default_factory=list, description="Time vector in seconds")
    acceleration: list[float] = Field(
        default_factory=list, description="Acceleration time history in g"
    )
    dt: float = Field(default=0.01, description="Time step in seconds")
    pga: float = Field(default=0.0, description="Peak ground acceleration in g")
    source: str = Field(default="synthetic", description="Source of ground motion")
    duration: float = Field(default=30.0, description="Duration in seconds")
    event_id: Optional[str] = Field(default=None, description="Event ID for real earthquakes")
    station: Optional[str] = Field(default=None, description="Station code for real earthquakes")

    # Synthetic generation parameters
    target_pga: float = Field(default=0.3, description="Target PGA for synthetic motion")
    predominant_freq: float = Field(default=2.0, description="Predominant frequency in Hz")
    bandwidth: float = Field(default=1.5, description="Bandwidth parameter")
    seed: Optional[int] = Field(default=None, description="Random seed")


class SimulationConfig(BaseModel):
    """Simulation configuration."""

    enable_mc: bool = Field(default=False, description="Enable Monte Carlo analysis")
    mc_samples: int = Field(default=100, ge=10, le=1000, description="Number of MC samples")
    stiffness_cov: float = Field(default=0.05, ge=0.0, le=0.3, description="Stiffness COV")
    damping_cov: float = Field(default=0.20, ge=0.0, le=0.5, description="Damping COV")
    mass_cov: float = Field(default=0.0, ge=0.0, le=0.2, description="Mass COV")
    mc_seed: Optional[int] = Field(default=42, description="Random seed for MC")


class SimulationResults(BaseModel):
    """Simulation results for storage."""

    # Time vector
    time: list[float] = Field(default_factory=list)

    # Displacement results (n_dof x n_steps, flattened)
    displacement: list[list[float]] = Field(default_factory=list)
    velocity: list[list[float]] = Field(default_factory=list)
    acceleration: list[list[float]] = Field(default_factory=list)

    # Demand metrics
    max_displacement: list[float] = Field(default_factory=list)
    max_velocity: list[float] = Field(default_factory=list)
    max_acceleration: list[float] = Field(default_factory=list)
    inter_story_drift_ratio: list[float] = Field(default_factory=list)
    peak_ground_acceleration: float = Field(default=0.0)

    # Building properties for reference
    natural_periods: list[float] = Field(default_factory=list)
    natural_frequencies: list[float] = Field(default_factory=list)

    # Monte Carlo results (if enabled)
    mc_enabled: bool = Field(default=False)
    displacement_p5: list[list[float]] = Field(default_factory=list)
    displacement_p50: list[list[float]] = Field(default_factory=list)
    displacement_p95: list[list[float]] = Field(default_factory=list)
    max_drift_distribution: list[float] = Field(default_factory=list)

    # Status
    completed: bool = Field(default=False)
    error: Optional[str] = Field(default=None)


class DashboardState(BaseModel):
    """Complete dashboard state."""

    building: BuildingParams = Field(default_factory=BuildingParams)
    ground_motion: GroundMotionState = Field(default_factory=GroundMotionState)
    simulation_config: SimulationConfig = Field(default_factory=SimulationConfig)
    results: Optional[SimulationResults] = Field(default=None)
    current_page: str = Field(default="building")
