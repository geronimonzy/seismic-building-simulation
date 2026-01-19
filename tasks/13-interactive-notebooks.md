# Task 13: Interactive Jupyter Notebooks

## Priority: HIGH
## Estimated Effort: 3-4 days

## Problem Statement

The current project:
- Has no interactive examples for learning
- Documentation lacks hands-on tutorials
- No visual exploration of concepts
- Difficult for new users to experiment

## Implementation Plan

### 1. Create notebooks directory structure

```
examples/
├── notebooks/
│   ├── 01_basic_workflow.ipynb
│   ├── 02_ground_motion_analysis.ipynb
│   ├── 03_building_models.ipynb
│   ├── 04_calibration_tutorial.ipynb
│   └── 05_uncertainty_quantification.ipynb
└── data/
    └── sample_records/
```

### 2. Notebook 01: Basic Workflow

**01_basic_workflow.ipynb**

```python
# Cell 1: Introduction (Markdown)
"""
# Seismic Digital Twin - Basic Workflow

This notebook demonstrates the complete workflow for seismic building analysis:
1. Create a building model
2. Generate earthquake ground motion
3. Run time history analysis
4. Visualize results

## Setup
"""

# Cell 2: Imports
import numpy as np
import matplotlib.pyplot as plt
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.analysis import newmark_beta, compute_demand_metrics

# Cell 3: Create Building (with explanation)
"""
## Step 1: Create Building Model

We'll model a 4-story reinforced concrete building.
"""
building = MDOFShearBuilding(
    masses=[100e3, 100e3, 100e3, 100e3],     # 100 tons per floor
    stiffnesses=[50e6, 50e6, 45e6, 40e6],    # Decreasing stiffness
    damping_ratio=0.05,                       # 5% critical damping
    story_heights=[4.0, 3.5, 3.5, 3.0],      # First floor taller
)

print(f"Building DOF: {building.n_dof}")
print(f"Natural periods: {1/building.natural_frequencies} s")

# Cell 4: Visualize building properties
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
# ... visualization code ...

# Cell 5: Generate ground motion
"""
## Step 2: Generate Earthquake Ground Motion

We'll create a synthetic earthquake with:
- Duration: 30 seconds
- Peak ground acceleration: 0.3g
"""
time, ground_acc = generate_synthetic_ground_motion(
    duration=30.0,
    dt=0.01,
    target_pga=0.3,
    predominant_freq=2.5,
)

# Cell 6: Run analysis
"""
## Step 3: Run Time History Analysis
"""
result = newmark_beta(building.M, building.C, building.K, ground_acc, dt=0.01)

# Cell 7: Compute demand metrics
metrics = compute_demand_metrics(result, building.story_heights)
print(f"Max roof displacement: {metrics.max_displacement[-1]:.3f} m")
print(f"Max inter-story drift: {metrics.inter_story_drift_ratio.max()*100:.2f}%")

# Cell 8: Interactive visualization
# Use ipywidgets for interactive exploration
```

### 3. Notebook 02: Ground Motion Analysis

**02_ground_motion_analysis.ipynb**

Topics covered:
- Synthetic ground motion generation
- Frequency content analysis (FFT)
- Response spectrum computation
- Comparing different earthquake scenarios
- Loading real records (if obspy available)

```python
# Key cells:

# Response spectrum computation
from seismic_twin.ground_motion import compute_response_spectrum

periods = np.logspace(-1, 1, 100)  # 0.1 to 10 seconds
Sa = compute_response_spectrum(ground_acc, dt, periods, damping=0.05)

plt.figure(figsize=(10, 5))
plt.loglog(periods, Sa / 9.81)
plt.xlabel("Period (s)")
plt.ylabel("Spectral Acceleration (g)")
plt.title("Response Spectrum")
plt.grid(True, which="both", ls="-", alpha=0.5)

# Compare different PGA levels
pga_levels = [0.1, 0.2, 0.3, 0.5]
for pga in pga_levels:
    _, acc = generate_synthetic_ground_motion(duration=20, dt=0.01, target_pga=pga)
    # ... plot comparison ...
```

### 4. Notebook 03: Building Models

**03_building_models.ipynb**

Topics covered:
- Single vs multi-DOF systems
- Effect of mass and stiffness
- Natural frequencies and mode shapes
- Rayleigh damping
- Parameter sensitivity

```python
# Mode shape visualization
from scipy.linalg import eigh

eigenvalues, eigenvectors = eigh(building.K, building.M)
natural_freqs = np.sqrt(eigenvalues) / (2 * np.pi)

fig, axes = plt.subplots(1, 4, figsize=(14, 6))
heights = np.cumsum([0] + list(building.story_heights))

for i, ax in enumerate(axes):
    mode = eigenvectors[:, i]
    mode = mode / np.max(np.abs(mode))  # Normalize

    ax.plot([0] + list(mode), heights, 'o-', linewidth=2)
    ax.set_title(f"Mode {i+1}\nf = {natural_freqs[i]:.2f} Hz")
    ax.set_xlabel("Normalized Displacement")
    ax.set_ylabel("Height (m)")
    ax.axvline(0, color='k', linestyle='--', alpha=0.3)
    ax.grid(True)
```

### 5. Notebook 04: Calibration Tutorial

**04_calibration_tutorial.ipynb**

Topics covered:
- Why calibration is needed
- Generating synthetic "measurements"
- Running calibration
- Convergence analysis
- Validating calibrated model

```python
# Generate synthetic measurements
true_model = MDOFShearBuilding(...)
result_true = newmark_beta(true_model.M, true_model.C, true_model.K, ground_acc, dt)

# Add realistic noise
noise_std = 0.002  # 2mm measurement noise
measurements = result_true.displacement + np.random.randn(*result_true.displacement.shape) * noise_std

# Create perturbed model (what we'd have before calibration)
perturbed_model = MDOFShearBuilding(
    masses=true_masses,
    stiffnesses=[s * 0.8 for s in true_stiffnesses],  # 20% underestimated
    damping_ratio=0.07,  # Wrong damping
    story_heights=true_heights,
)

# Run calibration
from seismic_twin.calibration import StructuralCalibration

calib = StructuralCalibration(
    perturbed_model, ground_acc, dt,
    measurements, measured_floors=[0, 1, 2, 3]
)

result = calib.calibrate(max_iterations=15, tolerance=0.01)

# Visualize convergence
plt.figure(figsize=(8, 5))
plt.semilogy(range(len(calib.nrmse_history)), calib.nrmse_history, 'o-')
plt.xlabel("Iteration")
plt.ylabel("NRMSE")
plt.title("Calibration Convergence")
plt.grid(True)
```

### 6. Notebook 05: Uncertainty Quantification

**05_uncertainty_quantification.ipynb**

Topics covered:
- Sources of uncertainty
- Monte Carlo sampling
- Parameter distributions
- Confidence bounds
- Results interpretation

```python
from seismic_twin.uncertainty import UncertaintyAnalysis

# Run Monte Carlo
uncertainty = UncertaintyAnalysis()
mc_result = uncertainty.run_mc_ensemble(
    model=building,
    ground_acceleration=ground_acc,
    dt=0.01,
    n_samples=200,
    stiffness_cov=0.10,  # 10% uncertainty in stiffness
    damping_cov=0.30,    # 30% uncertainty in damping
)

# Plot uncertainty bounds
fig, ax = plt.subplots(figsize=(12, 5))

time = np.arange(len(ground_acc)) * 0.01
floor = -1  # Roof

ax.fill_between(time,
                mc_result.percentiles['p5'][:, floor],
                mc_result.percentiles['p95'][:, floor],
                alpha=0.3, label='90% CI')
ax.plot(time, mc_result.percentiles['p50'][:, floor],
        'b-', linewidth=2, label='Median')
ax.plot(time, result.displacement[:, floor],
        'r--', linewidth=1.5, label='Nominal')

ax.set_xlabel("Time (s)")
ax.set_ylabel("Roof Displacement (m)")
ax.legend()
ax.set_title("Displacement Uncertainty Bounds")
```

### 7. Add interactive widgets (optional)

```python
# Using ipywidgets for interactive exploration
from ipywidgets import interact, FloatSlider

@interact(
    pga=FloatSlider(min=0.1, max=0.5, step=0.05, value=0.3, description='PGA (g)'),
    damping=FloatSlider(min=0.02, max=0.15, step=0.01, value=0.05, description='Damping'),
)
def explore_response(pga, damping):
    model = MDOFShearBuilding(
        masses=[100e3]*4,
        stiffnesses=[50e6]*4,
        damping_ratio=damping,
        story_heights=[3.5]*4,
    )
    _, acc = generate_synthetic_ground_motion(duration=20, dt=0.01, target_pga=pga)
    result = newmark_beta(model.M, model.C, model.K, acc, 0.01)

    plt.figure(figsize=(10, 4))
    plt.plot(result.time, result.displacement[:, -1])
    plt.xlabel("Time (s)")
    plt.ylabel("Roof Displacement (m)")
    plt.title(f"PGA={pga}g, ζ={damping}")
    plt.show()
```

### 8. Include in documentation

Add notebooks to Sphinx docs using nbsphinx:

```rst
.. toctree::
   :maxdepth: 1
   :caption: Tutorials

   ../examples/notebooks/01_basic_workflow
   ../examples/notebooks/02_ground_motion_analysis
   ../examples/notebooks/03_building_models
   ../examples/notebooks/04_calibration_tutorial
   ../examples/notebooks/05_uncertainty_quantification
```

## Files to Create

| File | Action |
|------|--------|
| `examples/notebooks/01_basic_workflow.ipynb` | Create |
| `examples/notebooks/02_ground_motion_analysis.ipynb` | Create |
| `examples/notebooks/03_building_models.ipynb` | Create |
| `examples/notebooks/04_calibration_tutorial.ipynb` | Create |
| `examples/notebooks/05_uncertainty_quantification.ipynb` | Create |
| `examples/data/sample_records/` | Create with sample data |

## Dependencies

- `jupyter` or `jupyterlab`
- `ipywidgets` (optional, for interactive elements)
- `nbsphinx` (for docs integration)

## Success Criteria

- [ ] All 5 notebooks created and tested
- [ ] Notebooks run without errors
- [ ] Clear explanations accompany all code
- [ ] Visualizations are informative
- [ ] Interactive widgets work (where applicable)
- [ ] Notebooks integrated into documentation
