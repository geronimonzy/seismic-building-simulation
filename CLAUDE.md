# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## GitHub Access

Use token from `.gittoken` file to access the git repo via GitHub API.

**IMPORTANT**: The token in `.gittoken` is READ-ONLY. Never use it with `gh auth login` as this will overwrite the user's authentication and break their ability to push.

```bash
# WRONG - Do NOT do this (overwrites user's auth):
gh auth login --with-token < .gittoken

# CORRECT - Use token directly with gh api:
gh api repos/OWNER/REPO/actions/runs --header "Authorization: token $(cat .gittoken)"

# CORRECT - Or set GH_TOKEN for a single command:
GH_TOKEN=$(cat .gittoken) gh run list
```

## Build and Development Commands

```bash
# Install in editable mode
pip install -e .

# Install with development dependencies (pytest, pytest-cov)
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=seismic_twin --cov-report=html

# Run a specific test file
pytest tests/test_building.py -v

# Run a specific test class or method
pytest tests/test_building.py::TestMDOFShearBuilding::test_single_dof_natural_frequency -v

# Run the complete workflow example
python examples/run_workflow.py
```

## Architecture Overview

This is a seismic digital twin package (`seismic_twin`) for building response simulation with sensor-based calibration. The package follows a modular pipeline architecture:

```
Ground Motion → Building Model → Time Integration → Calibration → Uncertainty
```

### Core Modules (src/seismic_twin/)

- **building/** - `MDOFShearBuilding` class for N-story shear building models with lumped masses and lateral stiffnesses. Assembles mass (M), stiffness (K), and damping (C) matrices using Rayleigh damping.

- **ground_motion/** - Synthetic earthquake generation with bandpass filtering and Saragoni-Hart envelope. Also provides baseline correction and response spectrum computation.

- **analysis/** - Two integration methods:
  - `newmark_beta()` - Implicit time integration (unconditionally stable), returns `IntegrationResult` dataclass
  - `modal_superposition()` - Modal decomposition approach
  - `compute_demand_metrics()` - Returns `DemandMetrics` with max displacement, inter-story drift ratio, floor acceleration

- **calibration/** - `StructuralCalibration` class for iterative model updating from sensor measurements. Uses grid search optimization over stiffness scaling factors and damping ratios to minimize NRMSE.

- **uncertainty/** - `UncertaintyAnalysis` class for Monte Carlo propagation of parameter uncertainties. Returns percentile bounds (5th, 50th, 95th) for displacement predictions.

- **visualization/** - Plotting utilities including `create_results_figure()` for comprehensive 6-panel summary plots.

### Key Data Structures

- `IntegrationResult`: Contains displacement, velocity, acceleration, absolute_acceleration arrays (shape: n_dof × n_timesteps) and time vector
- `DemandMetrics`: Contains max_displacement, max_velocity, max_acceleration, inter_story_drift_ratio arrays
- `CalibrationResult`: Contains stiffness_factor, damping_ratio, nrmse for each iteration
- `MonteCarloResult`: Contains displacement_bounds with percentile statistics

### Typical Workflow

1. Create building model with masses, stiffnesses, damping_ratio, story_heights
2. Generate or load ground motion (acceleration time series)
3. Run `newmark_beta()` with M, C, K matrices and ground acceleration
4. Compute engineering demand parameters with `compute_demand_metrics()`
5. If sensor data available: use `StructuralCalibration.calibrate()` to update model
6. Run `UncertaintyAnalysis.run_mc_ensemble()` for probabilistic bounds

### Units Convention

- Mass: kg
- Stiffness: N/m
- Displacement: meters
- Acceleration: m/s² (or g units where noted)
- Story heights: meters

## Dashboard

The interactive dashboard (`src/seismic_twin/dashboard/`) provides a web interface for building analysis. Run with:

```bash
# Install dashboard dependencies
pip install -e ".[dashboard]"

# Launch dashboard
python -m seismic_twin.dashboard
```

### Preset Configurations

The dashboard supports preset configurations for both building models and ground motion scenarios.

**Built-in Presets** (`presets.py`):
- **Building presets**: Low-rise RC, Mid-rise RC, High-rise Steel, Historic Masonry, Light Wood Frame, Industrial Steel
- **Ground motion presets**: Moderate-Stiff Soil, Strong-Soft Soil, Very Strong-Near Fault, Design Level (DBE), Maximum Considered (MCE), Low Seismicity

**Import/Export JSON Format**:

Building preset JSON:
```json
{
  "name": "Custom Building",
  "description": "Optional description",
  "n_stories": 3,
  "mass_per_floor": 100000,
  "stiffness_per_story": 100000000,
  "damping_ratio": 0.05,
  "story_height": 3.5
}
```

Ground motion preset JSON:
```json
{
  "name": "Custom Scenario",
  "description": "Optional description",
  "target_pga": 0.3,
  "duration": 30,
  "predominant_freq": 2.0,
  "bandwidth": 1.5
}
```

**Combined Scenario Format** (see `examples/presets/`):
```json
{
  "name": "Scenario Name",
  "description": "Scenario description",
  "building": { ... building params ... },
  "ground_motion": { ... ground motion params ... }
}
```

Example scenarios are provided in `examples/presets/` demonstrating typical analysis use cases.
