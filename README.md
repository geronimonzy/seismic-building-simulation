# Seismic Digital Twin

[![Tests](https://github.com/your-org/seismic-building-simulation/actions/workflows/tests.yml/badge.svg)](https://github.com/your-org/seismic-building-simulation/actions/workflows/tests.yml)
[![Code Quality](https://github.com/your-org/seismic-building-simulation/actions/workflows/quality.yml/badge.svg)](https://github.com/your-org/seismic-building-simulation/actions/workflows/quality.yml)
[![codecov](https://codecov.io/gh/your-org/seismic-building-simulation/graph/badge.svg)](https://codecov.io/gh/your-org/seismic-building-simulation)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A Python package for seismic building response simulation with sensor-based model calibration and uncertainty quantification.

## Overview

This package implements a complete digital twin workflow for buildings under earthquake loading:

1. **Ground Motion Generation** - Synthetic earthquake records with realistic characteristics
2. **Structural Modeling** - Multi-degree-of-freedom (MDOF) shear building models
3. **Time History Analysis** - Newmark-beta integration for dynamic response
4. **Model Calibration** - Sensor-based parameter updating to match measurements
5. **Uncertainty Quantification** - Monte Carlo analysis for probabilistic assessment

## Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/seismic-building-simulation.git
cd seismic-building-simulation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install in editable mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Project Structure

```
seismic-building-simulation/
├── src/seismic_twin/
│   ├── building/          # Structural models
│   │   └── mdof_model.py  # MDOFShearBuilding class
│   ├── ground_motion/     # Earthquake input generation
│   │   └── synthetic.py   # Synthetic motion & utilities
│   ├── analysis/          # Dynamic analysis
│   │   ├── integration.py # Newmark-beta, modal superposition
│   │   └── metrics.py     # Engineering demand parameters
│   ├── calibration/       # Model updating
│   │   └── calibrator.py  # StructuralCalibration class
│   ├── uncertainty/       # Probabilistic analysis
│   │   └── monte_carlo.py # UncertaintyAnalysis class
│   └── visualization/     # Plotting utilities
│       └── plots.py       # Result visualization
├── examples/
│   └── run_workflow.py    # Complete workflow example
├── tests/                 # Test suite (105 tests, 85% coverage)
└── pyproject.toml
```

## Quick Start

### Basic Building Analysis

```python
import numpy as np
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.analysis import newmark_beta, compute_demand_metrics

# Create a 4-story building
building = MDOFShearBuilding(
    masses=np.array([100_000, 100_000, 100_000, 100_000]),      # kg per floor
    stiffnesses=np.array([50e6, 50e6, 50e6, 50e6]),            # N/m per story
    damping_ratio=0.05,                                         # 5% damping
    story_heights=np.array([3.5, 3.5, 3.5, 3.5]),              # meters
)

print(f"Fundamental period: {building.natural_periods[0]:.3f} s")
print(f"Natural frequencies: {building.natural_frequencies / (2*np.pi)} Hz")

# Generate synthetic ground motion
time, ground_acc = generate_synthetic_ground_motion(
    duration=30.0,          # seconds
    dt=0.01,                # time step
    target_pga=0.35,        # peak ground acceleration in g
    predominant_freq=2.5,   # Hz
    seed=42,
)

# Run time history analysis
result = newmark_beta(
    M=building.M,
    C=building.C,
    K=building.K,
    ground_acceleration=ground_acc,
    dt=0.01,
)

# Compute engineering demand parameters
metrics = compute_demand_metrics(
    displacement=result.displacement,
    velocity=result.velocity,
    absolute_acceleration=result.absolute_acceleration,
    ground_acceleration=ground_acc,
    story_heights=building.story_heights,
)

print(f"Max roof displacement: {metrics.max_displacement[-1] * 100:.2f} cm")
print(f"Max inter-story drift: {np.max(metrics.inter_story_drift_ratio) * 100:.3f}%")
print(f"Max floor acceleration: {np.max(metrics.max_acceleration):.3f} g")
```

### Sensor-Based Calibration

```python
from seismic_twin.calibration import StructuralCalibration

# Assume we have measured displacement data from sensors
# measured_displacement shape: (n_floors, n_timesteps)
sensor_floors = np.array([0, 1, 2, 3])  # sensors on all floors

calibration = StructuralCalibration(
    model=building,
    ground_acceleration=ground_acc,
    dt=0.01,
    measured_displacement=measured_displacement,
    sensor_floors=sensor_floors,
)

# Run automatic calibration
best_result = calibration.calibrate(
    max_iterations=15,
    tolerance=0.02,
    stiffness_bounds=(0.7, 1.3),  # search 70%-130% of initial
    damping_bounds=(0.02, 0.08),  # search 2%-8% damping
)

print(f"Calibrated stiffness factor: {best_result.stiffness_factor:.3f}")
print(f"Calibrated damping ratio: {best_result.damping_ratio:.3f}")
print(f"Final NRMSE: {best_result.nrmse:.4f}")

# Get the calibrated model
calibrated_building = calibration.get_calibrated_model()
```

### Uncertainty Quantification

```python
from seismic_twin.uncertainty import UncertaintyAnalysis

uncertainty = UncertaintyAnalysis(
    model=calibrated_building,
    ground_acceleration=ground_acc,
    dt=0.01,
)

# Run Monte Carlo ensemble
mc_result = uncertainty.run_mc_ensemble(
    n_samples=100,
    stiffness_cov=0.05,  # 5% coefficient of variation
    damping_cov=0.20,    # 20% coefficient of variation
    seed=456,
)

# Get drift statistics
drift_stats = uncertainty.get_drift_statistics()
print(f"Mean max drift: {drift_stats['mean'] * 100:.3f}%")
print(f"5th percentile: {drift_stats['p5'] * 100:.3f}%")
print(f"95th percentile: {drift_stats['p95'] * 100:.3f}%")

# Probability of exceeding a threshold
p_exceed = uncertainty.get_probability_of_exceedance(
    threshold=0.02,  # 2% drift
    response_type='drift',
)
print(f"P(drift > 2%): {p_exceed:.1%}")
```

### Visualization

```python
from seismic_twin.visualization.plots import (
    plot_ground_motion,
    plot_displacement_comparison,
    plot_uncertainty_bounds,
    create_results_figure,
)
import matplotlib.pyplot as plt

# Single plot
fig, ax = plt.subplots()
plot_ground_motion(time, ground_acc, ax=ax)
plt.savefig("ground_motion.png")

# Comprehensive results figure
fig = create_results_figure(
    time=time,
    ground_acceleration=ground_acc,
    initial_displacement=initial_result.displacement,
    calibrated_displacement=calibrated_result.displacement,
    measured_displacement=measured_displacement,
    calibration_iterations=iterations,
    calibration_nrmse=nrmse_history,
    mc_mean=mc_result.displacement_bounds.percentile_50,
    mc_lower=mc_result.displacement_bounds.percentile_5,
    mc_upper=mc_result.displacement_bounds.percentile_95,
    drift_ratios=metrics.inter_story_drift_ratio,
    floor=-1,  # top floor
)
fig.savefig("results.png", dpi=150, bbox_inches="tight")
```

## Module Reference

### `seismic_twin.building`

| Class | Description |
|-------|-------------|
| `MDOFShearBuilding` | N-story shear building with lumped masses and lateral stiffnesses |

Key methods:
- `update_stiffness(scale_factor)` - Scale all stiffnesses
- `update_damping(new_ratio)` - Update damping ratio
- `get_modal_participation_factors()` - For ground motion excitation
- `copy()` - Create independent copy

### `seismic_twin.ground_motion`

| Function | Description |
|----------|-------------|
| `generate_synthetic_ground_motion()` | Bandpass-filtered noise with Saragoni-Hart envelope |
| `generate_harmonic_ground_motion()` | Simple sinusoidal motion for testing |
| `baseline_correction()` | Remove polynomial baseline drift |
| `apply_highpass_filter()` | Remove low-frequency content |
| `compute_response_spectrum()` | Pseudo-acceleration response spectrum |

### `seismic_twin.analysis`

| Function/Class | Description |
|----------------|-------------|
| `newmark_beta()` | Implicit time integration (unconditionally stable) |
| `modal_superposition()` | Modal decomposition method |
| `compute_demand_metrics()` | Max displacement, drift, acceleration |
| `compute_nrmse()` | Normalized root mean square error |
| `compute_arias_intensity()` | Ground motion intensity measure |
| `compute_energy_balance()` | Kinetic, strain, damping energy |
| `IntegrationResult` | Container for time history results |
| `DemandMetrics` | Container for engineering demand parameters |

### `seismic_twin.calibration`

| Class | Description |
|-------|-------------|
| `StructuralCalibration` | Iterative model updating from sensor data |
| `CalibrationResult` | Single iteration result |

Key methods:
- `calibrate()` - Automatic grid search optimization
- `run_simple_calibration()` - Gradient-based iterative approach
- `get_calibrated_model()` - Return updated model
- `get_convergence_history()` - NRMSE vs iteration

### `seismic_twin.uncertainty`

| Class | Description |
|-------|-------------|
| `UncertaintyAnalysis` | Monte Carlo uncertainty propagation |
| `MonteCarloResult` | Ensemble results with percentile bounds |
| `UncertaintyBounds` | Percentile statistics container |

Key methods:
- `run_mc_ensemble()` - Run Monte Carlo simulation
- `get_drift_statistics()` - Mean, std, percentiles of max drift
- `get_probability_of_exceedance()` - P(response > threshold)

### `seismic_twin.visualization`

| Function | Description |
|----------|-------------|
| `plot_ground_motion()` | Acceleration time history |
| `plot_displacement_comparison()` | Initial vs calibrated vs measured |
| `plot_calibration_convergence()` | NRMSE vs iteration |
| `plot_uncertainty_bounds()` | Percentile envelope with mean |
| `plot_max_drifts()` | Bar chart of inter-story drifts |
| `plot_mode_shapes()` | Modal deflection shapes |
| `plot_energy_balance()` | Energy components vs time |
| `create_results_figure()` | Comprehensive 6-panel summary |

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=seismic_twin --cov-report=html

# Run specific test file
pytest tests/test_building.py -v
```

## Complete Workflow Example

See `examples/run_workflow.py` for a complete demonstration that:

1. Generates synthetic ground motion (PGA = 0.35g)
2. Creates a 4-story building model
3. Runs initial prediction
4. Simulates sensor measurements with noise
5. Calibrates the model to match measurements
6. Runs Monte Carlo uncertainty analysis
7. Generates a comprehensive results figure

```bash
python examples/run_workflow.py
```

Output: `digital_twin_results.png`

## Requirements

- Python >= 3.9
- numpy >= 1.21.0
- scipy >= 1.7.0
- matplotlib >= 3.4.0
- pandas >= 1.3.0

## License

MIT License
