# Seismic Digital Twin

[![Tests](https://github.com/your-org/seismic-building-simulation/actions/workflows/tests.yml/badge.svg)](https://github.com/your-org/seismic-building-simulation/actions/workflows/tests.yml)
[![Code Quality](https://github.com/your-org/seismic-building-simulation/actions/workflows/quality.yml/badge.svg)](https://github.com/your-org/seismic-building-simulation/actions/workflows/quality.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A Python package for seismic building response simulation with an interactive web dashboard, real earthquake data integration, and uncertainty quantification.

## Features

- **Interactive Web Dashboard** - Configure buildings, run simulations, and visualize results in your browser
- **Two-Axis Simulation** - Combined horizontal (lateral) and vertical (axial) ground motion analysis with configurable V/H ratio
- **Real Earthquake Data** - Fetch actual seismic records from SCEDC (Southern California Earthquake Data Center)
- **MDOF Structural Models** - Multi-degree-of-freedom shear building models with Rayleigh damping
- **Time History Analysis** - Newmark-beta integration for dynamic response
- **Monte Carlo Analysis** - Uncertainty propagation with probabilistic bounds
- **Sensor-Based Calibration** - Model updating from measured data
- **Preset Configurations** - Built-in building types and earthquake scenarios

## Quick Start

### Option 1: Web Dashboard (Recommended)

```bash
# Install with dashboard dependencies
pip install -e ".[dashboard]"

# Launch the dashboard
python -m seismic_twin.dashboard
```

Open http://localhost:8050 in your browser.

### Option 2: Docker

```bash
docker compose -f docker-compose.dashboard.yml up --build
```

### Option 3: Python API

```python
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.analysis import newmark_beta, compute_demand_metrics
import numpy as np

# Create a 5-story building
building = MDOFShearBuilding(
    masses=np.full(5, 100_000),        # 100 tons per floor
    stiffnesses=np.full(5, 80e6),      # 80 MN/m per story
    damping_ratio=0.05,                 # 5% damping
    story_heights=np.full(5, 3.5),     # 3.5m story height
)

# Generate synthetic earthquake
time, ground_acc = generate_synthetic_ground_motion(
    duration=30.0, dt=0.01, target_pga=0.3, predominant_freq=2.0
)

# Run analysis
result = newmark_beta(building.M, building.C, building.K, ground_acc, dt=0.01)
metrics = compute_demand_metrics(
    result.displacement, result.velocity,
    result.absolute_acceleration, ground_acc, building.story_heights
)

print(f"Max drift: {np.max(metrics.inter_story_drift_ratio)*100:.2f}%")
```

## Installation

```bash
# Clone repository
git clone https://github.com/your-repo/seismic-building-simulation.git
cd seismic-building-simulation

# Basic installation
pip install -e .

# With dashboard
pip install -e ".[dashboard]"

# With real earthquake data support
pip install -e ".[data]"

# Full installation (development)
pip install -e ".[dev,dashboard,data]"
```

## Web Dashboard

The dashboard provides a complete workflow through four pages:

### 1. Building Configuration
- Define number of stories, mass, stiffness, damping
- Choose from preset building types (RC frames, steel, masonry, wood)
- View natural periods and mode shapes
- Import/export custom configurations as JSON

### 2. Ground Motion
- **Synthetic**: Generate artificial earthquakes with target PGA, duration, frequency content
- **Vertical Component**: Optional vertical ground motion with configurable V/H ratio (default 0.67)
- **Real Earthquakes**: Fetch actual records from SCEDC S3 (e.g., Ridgecrest 2019)
- Built-in scenarios (Design Level, MCE, Near-Fault, etc.)

### 3. Simulation
- Run time history analysis with real-time progress tracking
- **Two-Axis Analysis**: Separate horizontal (lateral) and vertical (axial) response computation
- **Vertical Stiffness Factor**: Configurable axial stiffness multiplier (10x-100x of lateral stiffness)
- Optional Monte Carlo uncertainty analysis
- Configurable number of samples and parameter uncertainty

### 4. Results
- Interactive time history plots (displacement, velocity, acceleration)
- **Axis Selector**: View horizontal, vertical, or combined results in Time History and Drift Profile tabs
- Inter-story drift profiles with performance thresholds
- Uncertainty bands (5th-95th percentile)
- Energy Balance visualization showing kinetic, strain, damping, and input energy time histories (combined from both axes)
- Summary metrics with performance level indicators (IO/LS/CP)

### Preset Configurations

Built-in presets for quick setup:

**Buildings:**
| Preset | Stories | Description |
|--------|---------|-------------|
| Low-rise RC Frame | 3 | Typical reinforced concrete |
| Mid-rise RC Frame | 8 | Reinforced concrete |
| High-rise Steel | 20 | Steel moment frame |
| Historic Masonry | 4 | Unreinforced masonry |
| Light Wood Frame | 2 | Residential construction |
| Industrial Steel | 1 | Warehouse/factory |

**Ground Motion:**
| Preset | PGA | Description |
|--------|-----|-------------|
| Moderate - Stiff Soil | 0.2g | Typical moderate event |
| Strong - Soft Soil | 0.4g | Amplified by soft soil |
| Very Strong - Near Fault | 0.6g | Impulsive near-fault |
| Design Level (DBE) | 0.3g | Code design basis |
| Maximum Considered (MCE) | 0.5g | Maximum considered |

Custom presets can be imported/exported as JSON files. See `examples/presets/` for examples.

## Real Earthquake Data

Fetch actual seismic records from SCEDC's AWS S3 archive:

```python
from seismic_twin.data import SCEDCS3Fetcher

fetcher = SCEDCS3Fetcher()

# Fetch Ridgecrest M7.1 earthquake record
record = fetcher.get_ground_motion_record(
    event_id="ci38457511",  # USGS event ID
    network="CI",
    station="CLC",          # China Lake station
    channel="HNE",          # East component
)

print(f"Station: {record.station}")
print(f"PGA: {record.pga:.3f} g")
print(f"Distance: {record.epicentral_distance_km:.1f} km")

# Use in simulation
time = record.time
acceleration = record.acceleration  # Already in g units
```

## Project Structure

```
seismic-building-simulation/
├── src/seismic_twin/
│   ├── building/           # Structural models (MDOFShearBuilding)
│   ├── ground_motion/      # Synthetic earthquake generation
│   ├── analysis/           # Time integration, demand metrics
│   ├── calibration/        # Sensor-based model updating
│   ├── uncertainty/        # Monte Carlo analysis
│   ├── visualization/      # Matplotlib plotting
│   ├── data/               # Real earthquake data fetching
│   │   ├── scedc_s3.py     # SCEDC S3 fetcher
│   │   ├── cache.py        # Local caching
│   │   └── records.py      # Data structures
│   └── dashboard/          # Plotly Dash web interface
│       ├── app.py          # Dash application
│       ├── layouts/        # Page layouts
│       ├── callbacks/      # Interactive callbacks
│       ├── figures/        # Plotly figure factories
│       ├── components/     # Reusable UI components
│       └── presets.py      # Preset configurations
├── examples/
│   ├── run_workflow.py     # Complete Python workflow
│   ├── run_real_earthquake.py  # Real data example
│   └── presets/            # Example JSON presets
├── tests/                  # Test suite
├── Dockerfile              # Base image
├── Dockerfile.dashboard    # Dashboard image
└── docker-compose.dashboard.yml
```

## API Reference

### Building Model

```python
from seismic_twin.building import MDOFShearBuilding

building = MDOFShearBuilding(
    masses,           # kg per floor (array)
    stiffnesses,      # N/m per story (array)
    damping_ratio,    # fraction (e.g., 0.05 for 5%)
    story_heights,    # meters per story (array)
)

# Properties
building.M              # Mass matrix
building.K              # Stiffness matrix
building.C              # Damping matrix (Rayleigh)
building.natural_periods      # Modal periods (seconds)
building.natural_frequencies  # Modal frequencies (rad/s)
building.mode_shapes          # Eigenvectors

# Methods
building.update_stiffness(scale_factor)
building.update_damping(new_ratio)
building.copy()
```

### Analysis

```python
from seismic_twin.analysis import newmark_beta, compute_demand_metrics

# Time history integration
result = newmark_beta(M, C, K, ground_acceleration, dt)
# Returns: IntegrationResult with displacement, velocity, acceleration arrays

# Engineering demand parameters
metrics = compute_demand_metrics(
    displacement, velocity, absolute_acceleration,
    ground_acceleration, story_heights
)
# Returns: DemandMetrics with max_displacement, inter_story_drift_ratio, etc.
```

### Uncertainty Analysis

```python
from seismic_twin.uncertainty import UncertaintyAnalysis

ua = UncertaintyAnalysis(model, ground_acceleration, dt)
mc_result = ua.run_mc_ensemble(
    n_samples=100,
    stiffness_cov=0.05,  # 5% coefficient of variation
    damping_cov=0.20,
)

stats = ua.get_drift_statistics()
p_exceed = ua.get_probability_of_exceedance(threshold=0.02)
```

## Running Tests

```bash
pytest tests/                    # All tests
pytest tests/ --cov=seismic_twin # With coverage
pytest tests/test_building.py -v # Specific file
```

## Requirements

**Core:**
- Python >= 3.9
- numpy, scipy, matplotlib, pandas

**Dashboard** (`pip install -e ".[dashboard]"`):
- dash, dash-bootstrap-components, plotly, pydantic

**Real Data** (`pip install -e ".[data]"`):
- obspy (for seismic data processing)

## License

MIT License
