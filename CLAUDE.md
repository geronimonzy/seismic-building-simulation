# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## GitHub Access

Use token from `.gittoken` file to access the git repo via GitHub API.

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
