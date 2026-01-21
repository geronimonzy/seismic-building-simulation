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

    # Building location (optional, for wave prediction)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90, description="Building latitude")
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Building longitude"
    )

    def to_arrays(self) -> tuple[list[float], list[float], list[float]]:
        """Return masses, stiffnesses, story_heights as lists."""
        return self.masses, self.stiffnesses, self.story_heights


class GroundMotionState(BaseModel):
    """Ground motion state for storage."""

    time: list[float] = Field(default_factory=list, description="Time vector in seconds")
    acceleration: list[float] = Field(
        default_factory=list, description="Horizontal acceleration time history in g"
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

    # Vertical component fields
    acceleration_vertical: list[float] = Field(
        default_factory=list, description="Vertical acceleration time history in g"
    )
    v_h_ratio: float = Field(default=0.67, description="Vertical to horizontal PGA ratio")
    has_vertical: bool = Field(default=False, description="Whether vertical component exists")
    pga_vertical: float = Field(default=0.0, description="Peak vertical ground acceleration in g")


class SimulationConfig(BaseModel):
    """Simulation configuration."""

    enable_mc: bool = Field(default=False, description="Enable Monte Carlo analysis")
    mc_samples: int = Field(default=100, ge=10, le=1000, description="Number of MC samples")
    stiffness_cov: float = Field(default=0.05, ge=0.0, le=0.3, description="Stiffness COV")
    damping_cov: float = Field(default=0.20, ge=0.0, le=0.5, description="Damping COV")
    mass_cov: float = Field(default=0.0, ge=0.0, le=0.2, description="Mass COV")
    mc_seed: Optional[int] = Field(default=42, description="Random seed for MC")

    # Vertical analysis configuration
    vertical_stiffness_factor: float = Field(
        default=50.0,
        ge=10.0,
        le=100.0,
        description="Axial/lateral stiffness ratio for vertical analysis",
    )


class SimulationResults(BaseModel):
    """Simulation results for storage."""

    # Time vector
    time: list[float] = Field(default_factory=list)

    # Horizontal displacement results (n_dof x n_steps)
    displacement: list[list[float]] = Field(default_factory=list)
    velocity: list[list[float]] = Field(default_factory=list)
    acceleration: list[list[float]] = Field(default_factory=list)

    # Horizontal demand metrics
    max_displacement: list[float] = Field(default_factory=list)
    max_velocity: list[float] = Field(default_factory=list)
    max_acceleration: list[float] = Field(default_factory=list)
    inter_story_drift_ratio: list[float] = Field(default_factory=list)
    peak_ground_acceleration: float = Field(default=0.0)

    # Vertical displacement results (n_dof x n_steps)
    displacement_vertical: list[list[float]] = Field(default_factory=list)
    velocity_vertical: list[list[float]] = Field(default_factory=list)
    acceleration_vertical: list[list[float]] = Field(default_factory=list)

    # Vertical demand metrics
    max_displacement_vertical: list[float] = Field(default_factory=list)
    max_velocity_vertical: list[float] = Field(default_factory=list)
    max_acceleration_vertical: list[float] = Field(default_factory=list)
    inter_story_drift_ratio_vertical: list[float] = Field(
        default_factory=list, description="Axial strain per story"
    )
    peak_ground_acceleration_vertical: float = Field(default=0.0)

    # Multi-axis metadata
    has_vertical_results: bool = Field(default=False)
    vertical_stiffness_factor: float = Field(default=50.0)

    # Building properties for reference
    natural_periods: list[float] = Field(default_factory=list)
    natural_frequencies: list[float] = Field(default_factory=list)

    # Vertical building properties
    natural_periods_vertical: list[float] = Field(default_factory=list)
    natural_frequencies_vertical: list[float] = Field(default_factory=list)

    # Monte Carlo results (if enabled)
    mc_enabled: bool = Field(default=False)
    displacement_p5: list[list[float]] = Field(default_factory=list)
    displacement_p50: list[list[float]] = Field(default_factory=list)
    displacement_p95: list[list[float]] = Field(default_factory=list)
    max_drift_distribution: list[float] = Field(default_factory=list)

    # Energy balance results (combined from both axes if vertical exists)
    energy_kinetic: list[float] = Field(default_factory=list)
    energy_strain: list[float] = Field(default_factory=list)
    energy_damping: list[float] = Field(default_factory=list)
    energy_input: list[float] = Field(default_factory=list)

    # Status
    completed: bool = Field(default=False)
    error: Optional[str] = Field(default=None)


class StationInfo(BaseModel):
    """Information about a seismic station."""

    station_id: str = Field(description="Station code")
    network: str = Field(default="CI", description="Network code")
    latitude: float = Field(description="Station latitude")
    longitude: float = Field(description="Station longitude")
    distance_km: float = Field(default=0.0, description="Distance from epicenter in km")
    pga: float = Field(default=0.0, description="Peak ground acceleration in g")


class PredictionState(BaseModel):
    """State for wave propagation prediction."""

    # Event information
    event_id: Optional[str] = Field(default=None, description="Event ID (e.g., ci38457511)")
    event_magnitude: float = Field(default=0.0, description="Event magnitude")
    event_lat: float = Field(default=0.0, description="Epicenter latitude")
    event_lon: float = Field(default=0.0, description="Epicenter longitude")
    event_depth_km: float = Field(default=0.0, description="Event depth in km")
    event_region: str = Field(default="", description="Region name")

    # Available stations
    available_stations: list[StationInfo] = Field(
        default_factory=list, description="List of available stations"
    )

    # Selection
    target_station_id: Optional[str] = Field(default=None, description="Target station to predict")
    selected_source_stations: list[str] = Field(
        default_factory=list, description="Selected source stations"
    )

    # Waveform data
    time: list[float] = Field(default_factory=list, description="Time vector")
    dt: float = Field(default=0.01, description="Time step")
    actual_waveform: list[float] = Field(default_factory=list, description="Actual waveform")
    predicted_waveform: list[float] = Field(default_factory=list, description="Predicted waveform")

    # Peak metrics
    actual_pga: float = Field(default=0.0, description="Actual PGA")
    predicted_pga: float = Field(default=0.0, description="Predicted PGA")
    pga_ratio: float = Field(default=0.0, description="Predicted/Actual PGA ratio")
    pga_error_percent: float = Field(default=0.0, description="PGA error percentage")

    # Spectrum comparison
    spectrum_periods: list[float] = Field(default_factory=list, description="Spectral periods")
    spectrum_actual: list[float] = Field(default_factory=list, description="Actual Sa")
    spectrum_predicted: list[float] = Field(default_factory=list, description="Predicted Sa")

    # Time series metrics
    nrmse: float = Field(default=0.0, description="Normalized RMSE")
    correlation: float = Field(default=0.0, description="Correlation coefficient")
    arias_ratio: float = Field(default=0.0, description="Arias intensity ratio")

    # Overall quality
    overall_score: float = Field(default=0.0, description="Overall quality score (0-1)")
    quality_grade: str = Field(default="", description="Quality grade (A-F)")

    # Status
    loaded: bool = Field(default=False, description="Whether event data is loaded")
    prediction_complete: bool = Field(default=False, description="Whether prediction is complete")
    error: Optional[str] = Field(default=None, description="Error message if any")


class DashboardState(BaseModel):
    """Complete dashboard state."""

    building: BuildingParams = Field(default_factory=BuildingParams)
    ground_motion: GroundMotionState = Field(default_factory=GroundMotionState)
    simulation_config: SimulationConfig = Field(default_factory=SimulationConfig)
    results: Optional[SimulationResults] = Field(default=None)
    prediction: PredictionState = Field(default_factory=PredictionState)
    current_page: str = Field(default="building")
