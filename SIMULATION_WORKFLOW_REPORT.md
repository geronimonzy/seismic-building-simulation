# Comprehensive Report: Seismic Building Simulation Workflow

**Project:** Seismic Digital Twin  
**Repository:** geronimonzy/seismic-building-simulation  
**Date:** January 2026

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
   - [Building Modeling](#1-building-modeling-mdof-shear-building)
   - [Ground Motion Generation](#2-ground-motion-generation)
   - [Time Integration Analysis](#3-time-integration-analysis)
   - [Sensor-Based Calibration](#4-sensor-based-calibration)
   - [Uncertainty Quantification](#5-uncertainty-quantification)
   - [Wave Propagation Prediction](#6-wave-propagation-prediction)
4. [Simulation Workflow](#simulation-workflow)
5. [Dashboard Interface](#dashboard-interface)
6. [Data Structures](#data-structures)
7. [Mathematical Formulations](#mathematical-formulations)
8. [Usage Examples](#usage-examples)
9. [Technology Stack](#technology-stack)

---

## Executive Summary

The **Seismic Digital Twin** is a comprehensive Python package for seismic building response simulation, uncertainty quantification, and structural health monitoring. The system combines:

- **Multi-degree-of-freedom (MDOF) structural models** with Rayleigh damping
- **Synthetic and real earthquake data integration** from SCEDC
- **Time history analysis** using Newmark-β integration
- **Sensor-based model calibration** for real-time structural health monitoring
- **Monte Carlo uncertainty propagation** for probabilistic risk assessment
- **GMPE-based wave propagation prediction** for ground motion forecasting
- **Interactive web dashboard** for workflow execution and visualization

The simulation enables engineers to predict seismic building response, calibrate models from sensor measurements, and quantify uncertainty in structural performance.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SEISMIC DIGITAL TWIN                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Building   │  │    Ground    │  │     Time     │         │
│  │   Modeling   │→ │    Motion    │→ │ Integration  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│         │                  │                  │                 │
│         ↓                  ↓                  ↓                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Calibration  │  │ Uncertainty  │  │     Wave     │         │
│  │   (Sensor)   │  │   Analysis   │  │  Prediction  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            Interactive Web Dashboard (Dash)             │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Module Organization

```
src/seismic_twin/
├── building/           # Structural models (MDOFShearBuilding)
├── ground_motion/      # Synthetic & real earthquake generation
├── analysis/           # Time integration (Newmark-β), demand metrics
├── calibration/        # Sensor-based model updating
├── uncertainty/        # Monte Carlo propagation
├── prediction/         # Wave propagation (GMPE-based)
│   ├── gmpe/           # Ground Motion Prediction Equations
│   ├── waveform_prediction.py
│   ├── distance.py
│   └── validation.py
├── data/               # Real earthquake data fetching (SCEDC S3)
├── visualization/      # Matplotlib plotting utilities
└── dashboard/          # Plotly Dash web interface
    ├── layouts/        # Page layouts
    ├── callbacks/      # Interactive logic
    ├── figures/        # Plotly visualizations
    ├── state/          # State management (Pydantic schemas)
    └── presets.py      # Building/earthquake presets
```

---

## Core Components

### 1. Building Modeling (MDOF Shear Building)

**Module:** `src/seismic_twin/building/mdof_model.py`

#### Concept

The **MDOFShearBuilding** class represents a building as a lumped-mass system where:
- Each floor is modeled as a concentrated mass
- Stories provide lateral stiffness (no axial deformation)
- Each floor has one horizontal degree of freedom

#### Key Features

**Structural Matrices:**
1. **Mass Matrix (M)** - Diagonal matrix with floor masses
2. **Stiffness Matrix (K)** - Tridiagonal for shear buildings
3. **Damping Matrix (C)** - Rayleigh damping (proportional to M and K)

**Modal Properties:**
- Natural frequencies (ω) and periods (T)
- Mode shapes (eigenvectors)
- Computed via generalized eigenvalue problem: `K·φ = ω² M·φ`

#### Mathematical Formulation

**Stiffness Matrix Assembly:**
```
For story i with stiffness k_i:
K[i,i] = k[i] + k[i+1]      (diagonal: sum of adjacent stiffnesses)
K[i,i+1] = -k[i+1]          (off-diagonal: coupling)
K[i+1,i] = -k[i+1]
```

Example for 3-DOF system:
```
     ┌                        ┐
     │  k₁+k₂    -k₂      0  │
K =  │   -k₂    k₂+k₃   -k₃  │
     │    0      -k₃     k₃  │
     └                        ┘
```

**Rayleigh Damping:**
```
C = α·M + β·K

where α and β are chosen to match target damping ratio ζ at two frequencies:
α = 2·ζ·ω₁·ωₙ / (ω₁ + ωₙ)
β = 2·ζ / (ω₁ + ωₙ)

Typical damping ratios:
- Steel/RC buildings: 2-5%
- Masonry: 7-10%
```

#### Implementation Example

```python
from seismic_twin.building import MDOFShearBuilding
import numpy as np

# 5-story building
building = MDOFShearBuilding(
    masses=np.full(5, 100_000),        # 100 tonnes per floor
    stiffnesses=np.full(5, 80e6),      # 80 MN/m per story
    damping_ratio=0.05,                # 5% damping
    story_heights=np.full(5, 3.5),     # 3.5m story height
)

# Access properties
print(f"Fundamental period: {building.natural_periods[0]:.2f} s")
print(f"Mass matrix shape: {building.M.shape}")
print(f"Mode shapes: {building.mode_shapes}")
```

#### Dynamic Updates

Models can be updated during calibration:
```python
building.update_stiffness(scale_factor=0.9)  # Reduce stiffness by 10%
building.update_damping(new_ratio=0.04)      # Change damping to 4%
```

Updates automatically recompute:
- Stiffness matrix K
- Modal properties (frequencies, mode shapes)
- Damping matrix C (based on new frequencies)

---

### 2. Ground Motion Generation

**Module:** `src/seismic_twin/ground_motion/synthetic.py`

#### Synthetic Generation

The system generates realistic earthquake-like ground motions using **modulated filtered noise**:

**Three-Step Process:**

1. **White Noise Generation**
   - Random Gaussian noise with zero mean
   
2. **Bandpass Filtering**
   - Butterworth 4th-order filter centered at predominant frequency
   - Frequency band: `[f₀ - bandwidth, f₀ + bandwidth]`
   
3. **Envelope Modulation (Saragoni-Hart)**
   ```
   e(t) = a·t^b·exp(-c·t)
   
   where:
   - b controls rise rate (typically 2.0)
   - c controls decay rate (related to strong motion duration)
   - Peak occurs at t_max ≈ duration × 0.3
   ```

4. **PGA Scaling**
   - Scale to achieve target peak ground acceleration

**Parameters:**
- `duration` - Total time (e.g., 30s)
- `dt` - Time step (e.g., 0.01s for 100 Hz sampling)
- `target_pga` - Peak ground acceleration in g (e.g., 0.3g)
- `predominant_freq` - Dominant frequency in Hz (e.g., 2.0 Hz for soft soil)
- `bandwidth` - Frequency spread (e.g., 1.5 Hz)
- `seed` - Random seed for reproducibility

#### Vertical Component Generation

Vertical ground motion can be generated with configurable vertical-to-horizontal (V/H) ratio:

```python
time, acc_h, acc_v = generate_2component_ground_motion(
    duration=30.0,
    dt=0.01,
    target_pga=0.3,      # Horizontal PGA
    v_h_ratio=0.67,      # Vertical PGA = 0.67 × horizontal PGA
    predominant_freq=2.0,
    seed=42
)
```

**Typical V/H ratios:**
- Near-fault: 0.5 - 1.0
- Far-field: 0.5 - 0.7
- Default: 0.67 (2/3 rule)

#### Real Earthquake Data

Integration with **SCEDC (Southern California Earthquake Data Center)** S3 archive:

```python
from seismic_twin.data import SCEDCS3Fetcher

fetcher = SCEDCS3Fetcher()

# Fetch Ridgecrest M7.1 earthquake
record = fetcher.get_ground_motion_record(
    event_id="ci38457511",    # USGS event ID
    network="CI",
    station="CLC",            # China Lake station
    channel="HNE",            # East component
)

# Record includes:
# - Time series (record.time, record.acceleration)
# - PGA in g (record.pga)
# - Metadata (station, epicentral distance, etc.)
```

#### Site Response Modification

Apply site amplification effects using NEHRP site classes:

```python
from seismic_twin.ground_motion import apply_site_response, SiteClass

# Modify for soft soil (Class D: Vs30 = 180-360 m/s)
modified_acc = apply_site_response(
    acceleration=ground_acc,
    site_class=SiteClass.D,
    dt=0.01
)
```

---

### 3. Time Integration Analysis

**Module:** `src/seismic_twin/analysis/integration.py`

#### Newmark-β Method

The **Newmark-β** method is an implicit time-stepping algorithm for solving the equations of motion:

**Equation of Motion:**
```
M·ü + C·u̇ + K·u = -M·r·a_g(t)

where:
- u, u̇, ü = relative displacement, velocity, acceleration vectors
- a_g(t) = ground acceleration time history
- r = influence vector (default: ones for uniform ground motion)
```

**Algorithm Parameters:**
- `β = 0.25` (average acceleration method - unconditionally stable)
- `γ = 0.5` (no numerical damping)

**Integration Steps:**

At each time step i → i+1:

1. **Effective Stiffness Matrix:**
   ```
   K_eff = K + (1/β·dt²)·M + (γ/β·dt)·C
   ```

2. **Effective Load Vector:**
   ```
   P_eff = -M·r·a_g(t_{i+1}) + M·Δu_pred + C·Δv_pred
   
   where Δu_pred, Δv_pred are predictor terms from current state
   ```

3. **Solve for Displacement:**
   ```
   u_{i+1} = K_eff⁻¹ · P_eff
   ```
   (Uses LU factorization for efficiency)

4. **Update Velocity and Acceleration:**
   ```
   a_{i+1} = (1/β·dt²)·(u_{i+1} - u_i) - (1/β·dt)·v_i - (1/2β - 1)·a_i
   v_{i+1} = v_i + dt·[(1-γ)·a_i + γ·a_{i+1}]
   ```

**Output:**
Returns `IntegrationResult` containing:
- `time` - Time vector (n_steps)
- `displacement` - Relative displacement (n_dof × n_steps)
- `velocity` - Relative velocity (n_dof × n_steps)
- `acceleration` - Relative acceleration (n_dof × n_steps)
- `absolute_acceleration` - Total acceleration = relative + ground (n_dof × n_steps)

#### Demand Metrics

**Engineering demand parameters** computed from response:

```python
from seismic_twin.analysis import compute_demand_metrics

metrics = compute_demand_metrics(
    displacement=result.displacement,
    velocity=result.velocity,
    absolute_acceleration=result.absolute_acceleration,
    ground_acceleration=ground_acc,
    story_heights=story_heights
)
```

**Metrics computed:**

1. **Maximum Displacement** - Peak displacement per floor
2. **Inter-Story Drift Ratio (IDR)**
   ```
   IDR[i] = (u[i] - u[i-1]) / h[i]
   
   where h[i] is story height
   ```
   
3. **Maximum Floor Acceleration** - Peak absolute acceleration per floor

4. **Energy Balance** - Conservation check
   ```
   E_kinetic = (1/2)·v^T·M·v
   E_strain = (1/2)·u^T·K·u
   E_damping = ∫ u̇^T·C·u̇ dt
   E_input = -∫ M·r·a_g·u̇ dt
   ```

**Performance Limits (FEMA 356):**
- **Immediate Occupancy (IO):** IDR < 0.7%
- **Life Safety (LS):** IDR < 2.5%
- **Collapse Prevention (CP):** IDR < 5.0%

---

### 4. Sensor-Based Calibration

**Module:** `src/seismic_twin/calibration/calibrator.py`

#### Purpose

Update building model parameters (stiffness, damping) to match sensor measurements from real earthquakes, enabling **structural health monitoring** and **digital twin updating**.

#### Workflow

```
┌────────────────┐
│  Sensor Data   │ (measured displacement from accelerometers)
└────────┬───────┘
         │
         ↓
┌────────────────────────────────────────────┐
│  1. Run simulation with current model     │
│  2. Compare predictions vs. measurements  │
│  3. Compute residuals (NRMSE, correlation)│
│  4. Update parameters to reduce error     │
│  5. Repeat until convergence              │
└────────────────────────────────────────────┘
         │
         ↓
┌────────────────┐
│ Calibrated     │
│ Model          │
└────────────────┘
```

#### StructuralCalibration Class

**Initialization:**
```python
from seismic_twin.calibration import StructuralCalibration

calibration = StructuralCalibration(
    model=building,                      # Initial MDOFShearBuilding
    ground_acceleration=ground_acc,      # Excitation applied
    dt=0.01,
    measured_displacement=sensor_data,   # From sensors (n_sensors × n_steps)
    sensor_floors=[0, 2, 4],            # Floor indices with sensors
)
```

#### Optimization Strategy: Grid Search

**Parameter Space:**
- **Stiffness factor:** 0.5 to 2.0 (multiply all stiffnesses)
- **Damping ratio:** 0.01 to 0.10 (1% to 10%)

**Algorithm:**
```
best_error = infinity

for each stiffness_factor in grid:
    for each damping_ratio in grid:
        # Update model
        update_model(stiffness_factor, damping_ratio)
        
        # Run simulation
        prediction = newmark_beta(M, C, K, ground_acc, dt)
        
        # Extract at sensor locations
        predicted_sensor = prediction.displacement[sensor_floors, :]
        
        # Compute error
        error = NRMSE(predicted_sensor, measured_displacement)
        
        if error < best_error:
            best_error = error
            best_params = (stiffness_factor, damping_ratio)
        
        if error < tolerance:
            break  # Early stopping
```

**Error Metric (NRMSE):**
```
NRMSE = √[mean((y_pred - y_meas)²)] / (max(y_meas) - min(y_meas))

Typical tolerance: NRMSE < 0.02 (2%)
```

#### Calibration Result

```python
best_result = calibration.calibrate(
    max_iterations=15,
    tolerance=0.02,
    stiffness_bounds=(0.7, 1.3),
    damping_bounds=(0.02, 0.08),
)

# Access results
print(f"Stiffness factor: {best_result.stiffness_factor}")
print(f"Damping ratio: {best_result.damping_ratio}")
print(f"Final NRMSE: {best_result.nrmse}")

# Get calibrated model
calibrated_building = calibration.get_calibrated_model()
```

#### Convergence Tracking

```python
iterations, nrmse_history = calibration.get_convergence_history()

# Plot convergence
import matplotlib.pyplot as plt
plt.plot(iterations, nrmse_history)
plt.xlabel('Iteration')
plt.ylabel('NRMSE')
```

#### Use Cases

1. **Post-earthquake assessment** - Update model after real event
2. **Continuous monitoring** - Track stiffness degradation over time
3. **Baseline refinement** - Improve initial model from ambient vibration tests
4. **Damage detection** - Identify stiffness loss in specific stories

---

### 5. Uncertainty Quantification

**Module:** `src/seismic_twin/uncertainty/monte_carlo.py`

#### Purpose

Propagate parameter uncertainties through the simulation to obtain **probabilistic response bounds**, enabling risk assessment and reliability analysis.

#### Monte Carlo Sampling

**Parameter Distributions:**

All parameters use **lognormal distributions** (ensures positive values):

1. **Stiffness** - Per-story multipliers
   ```
   k_i^(sample) = k_i^(nominal) × LN(μ, σ)
   
   where σ = √[ln(1 + CoV²)]
   typical CoV = 5% (low uncertainty)
   ```

2. **Damping Ratio** - Global multiplier
   ```
   ζ^(sample) = ζ^(nominal) × LN(μ, σ)
   
   typical CoV = 20% (high uncertainty due to measurement difficulty)
   ```

3. **Mass** - Per-floor multipliers
   ```
   m_i^(sample) = m_i^(nominal) × LN(μ, σ)
   
   typical CoV = 0-2% (usually well-known)
   ```

#### Workflow

```python
from seismic_twin.uncertainty import UncertaintyAnalysis

uncertainty = UncertaintyAnalysis(
    model=calibrated_building,
    ground_acceleration=ground_acc,
    dt=0.01,
)

# Run Monte Carlo ensemble
mc_result = uncertainty.run_mc_ensemble(
    n_samples=100,           # Number of random samples
    stiffness_cov=0.05,      # 5% coefficient of variation
    damping_cov=0.20,        # 20% coefficient of variation
    mass_cov=0.0,            # No uncertainty in mass
    seed=42,                 # Reproducibility
    verbose=True,
)
```

**Process:**
1. Sample n parameter sets from distributions
2. For each sample:
   - Create building model with sampled parameters
   - Run Newmark-β integration
   - Store displacement, velocity, acceleration time histories
   - Extract maximum inter-story drift
3. Compute statistics across ensemble:
   - 5th, 50th, 95th percentiles
   - Mean and standard deviation

#### Output Structure

**MonteCarloResult contains:**
- `displacement_bounds` - Statistical bounds at each time step
  - `percentile_5`, `percentile_50`, `percentile_95`
  - `mean`, `std`
- `velocity_bounds` - Same structure for velocity
- `acceleration_bounds` - Same structure for acceleration
- `drift_distribution` - Maximum IDR distribution across samples
- `parameter_samples` - Record of all sampled parameters

#### Statistical Analysis

**Drift Statistics:**
```python
drift_stats = uncertainty.get_drift_statistics()

print(f"Mean max drift: {drift_stats['mean'] * 100:.2f}%")
print(f"5th percentile: {drift_stats['p5'] * 100:.2f}%")
print(f"95th percentile: {drift_stats['p95'] * 100:.2f}%")
print(f"Standard deviation: {drift_stats['std'] * 100:.2f}%")
```

**Probability of Exceedance:**
```python
# Probability of exceeding Life Safety limit (2.5% drift)
p_exceed = uncertainty.get_probability_of_exceedance(threshold=0.025)
print(f"P(IDR > 2.5%) = {p_exceed:.2%}")
```

#### Visualization

Plot uncertainty bands:
```python
import matplotlib.pyplot as plt

floor_idx = -1  # Top floor
plt.fill_between(
    time,
    mc_result.displacement_bounds.percentile_5[floor_idx, :],
    mc_result.displacement_bounds.percentile_95[floor_idx, :],
    alpha=0.3,
    label='90% confidence interval'
)
plt.plot(time, mc_result.displacement_bounds.percentile_50[floor_idx, :], 
         label='Median response')
```

#### Applications

1. **Seismic fragility analysis** - P(damage | ground motion intensity)
2. **Code compliance** - Verify performance under parameter variability
3. **Risk assessment** - Quantify confidence in safety predictions
4. **Sensitivity analysis** - Identify most influential parameters

---

### 6. Wave Propagation Prediction

**Module:** `src/seismic_twin/prediction/`

#### Purpose

Predict ground motion at a **target location** using recordings from nearby **source stations** and empirical attenuation models (**GMPEs**), enabling:
- Site-specific seismic hazard assessment
- Sparse instrumentation network interpolation
- Pre-event scenario planning

#### Architecture

**Three Components:**

1. **WaveformPredictor** - Main orchestrator
2. **GMPE (Boore-Atkinson 2008)** - Attenuation model
3. **Distance Calculations** - Geometric metrics

#### How It Works

**Amplitude Scaling Principle:**

Ground motion amplitude decreases with distance from the earthquake source. If we know:
- Recording at source station (distance R_s from fault)
- Target location (distance R_t from fault)
- Earthquake magnitude and fault geometry

We can predict the target waveform:

```
a_target(t) = a_source(t) × (PGA_target / PGA_source)

where PGA ratio is computed from GMPE:
  PGA_target = GMPE(M, R_t, Vs30_target)
  PGA_source = GMPE(M, R_s, Vs30_source)
```

**Key Assumption:** Waveform shape is preserved; only amplitude scales with distance.

#### WaveformPredictor Usage

```python
from seismic_twin.prediction import WaveformPredictor, BooreAtkinson2008

# Initialize with GMPE
gmpe = BooreAtkinson2008()
predictor = WaveformPredictor(gmpe=gmpe)

# Predict at target location
prediction = predictor.predict_at_location(
    source_waveform=source_acceleration,     # Recorded at source station
    source_lat=35.77, source_lon=-117.60,    # Source station coordinates
    target_lat=35.70, target_lon=-117.55,    # Target location
    event_lat=35.766, event_lon=-117.605,    # Earthquake epicenter
    event_depth=10.0,                        # Focal depth (km)
    event_magnitude=7.1,                     # Moment magnitude
    dt=0.01,                                 # Time step
)

# Access results
predicted_acceleration = prediction.predicted_waveform  # in g
predicted_pga = prediction.predicted_pga
scale_factor = prediction.scale_factor
```

#### GMPE: Boore-Atkinson 2008

**Ground Motion Prediction Equation** for spectral acceleration:

```
ln(Sa) = F_M + F_D + F_S + ε

where:
F_M = magnitude term (source contribution)
F_D = distance term (path attenuation)
F_S = site term (local amplification)
ε   = aleatory uncertainty (standard deviation)
```

**Magnitude Term:**
```
F_M = e1 + e2·(M - M_h) + e3·(M - M_h)²     for M ≤ M_h
F_M = e4 + e5·(M - M_h)                      for M > M_h

M_h = 6.75 (hinge magnitude)
```

**Distance Term (Geometric Spreading + Anelastic Attenuation):**
```
F_D = [c1 + c2·(M - M_ref)]·ln(R / R_ref) + c3·(R - R_ref)

R = √(R_jb² + h²)  (effective distance with depth h)
```

**Site Term (Vs30 Amplification):**
```
F_S = b_lin·ln(Vs30 / V_ref) + b_nl·ln(PGA_rock / 0.1)

Vs30 = time-averaged shear-wave velocity in top 30m
V_ref = 760 m/s (reference rock site)
```

**Aleatory Uncertainty:**
- Inter-event (τ): Between-earthquake variability
- Intra-event (σ): Within-earthquake variability
- Total: σ_total = √(τ² + σ²)

#### Distance Metrics

**Joyner-Boore Distance (R_jb):**
- Closest horizontal distance to surface projection of fault rupture
- For point source (M < 6): ≈ epicentral distance
- For finite fault (M ≥ 6): computed from fault geometry (strike, dip, length, width)

**Epicentral Distance:**
```
Haversine formula on sphere (Earth radius = 6371 km):
d = 2·R·arcsin(√[sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)])
```

#### Validation Metrics

**PredictionValidator** compares predicted vs. actual recordings:

```python
from seismic_twin.prediction import PredictionValidator

validator = PredictionValidator()
result = validator.validate(
    actual=actual_waveform,
    predicted=predicted_waveform,
    dt=0.01,
)

# Peak metrics
print(f"PGA ratio: {result.peak_metrics.pga_ratio:.2f}")
print(f"PGA error: {result.peak_metrics.pga_error_percent:.1f}%")

# Time-series metrics
print(f"Correlation: {result.time_series_metrics.correlation:.3f}")
print(f"NRMSE: {result.time_series_metrics.nrmse:.3f}")

# Spectrum metrics
print(f"Spectrum goodness-of-fit: {result.spectrum_metrics.goodness_of_fit:.2f}")

# Overall grade (A, B, C, D, F)
print(f"Grade: {result.grade}")
```

**Grading Criteria:**
- **A:** PGA ratio 0.85-1.15, correlation > 0.9, NRMSE < 0.15
- **B:** PGA ratio 0.70-1.30, correlation > 0.75, NRMSE < 0.25
- **C:** PGA ratio 0.55-1.45, correlation > 0.6, NRMSE < 0.35
- **D:** PGA ratio 0.40-1.60, correlation > 0.4, NRMSE < 0.50
- **F:** Outside all above bounds

#### Cross-Validation

Leave-one-out validation across station network:

```python
# Predict at each station using all others
predictions = predictor.cross_validate_stations(
    stations=station_list,
    event_lat=event_lat,
    event_lon=event_lon,
    event_depth=event_depth,
    event_magnitude=magnitude,
)

# Aggregate validation scores
for station_id, pred in predictions.items():
    print(f"{station_id}: Grade {pred.validation.grade}")
```

---

## Simulation Workflow

### Complete End-to-End Pipeline

The simulation follows a 5-phase workflow:

```
Phase 1: Ground Motion → Phase 2: Building Model → Phase 3: Initial Analysis
                                                              ↓
Phase 5: Uncertainty   ← Phase 4: Calibration ← (Optional: Sensor Data)
```

### Detailed Workflow Steps

#### Phase 1: Ground Motion Generation

**Input:** Seismic hazard parameters  
**Output:** Time history of ground acceleration

```python
from seismic_twin.ground_motion import generate_synthetic_ground_motion

time, ground_acceleration = generate_synthetic_ground_motion(
    duration=30.0,              # seconds
    dt=0.01,                    # 100 Hz sampling
    target_pga=0.35,            # 0.35g peak acceleration
    predominant_freq=2.5,       # 2.5 Hz (soft soil)
    bandwidth=2.0,
    seed=42,
)
```

**Alternative:** Load real earthquake from SCEDC
```python
from seismic_twin.data import SCEDCS3Fetcher

fetcher = SCEDCS3Fetcher()
record = fetcher.get_ground_motion_record(
    event_id="ci38457511",
    network="CI",
    station="CLC",
    channel="HNE"
)
ground_acceleration = record.acceleration
time = record.time
```

#### Phase 2: Building Model Creation

**Input:** Structural properties  
**Output:** MDOF model with M, K, C matrices

```python
from seismic_twin.building import MDOFShearBuilding
import numpy as np

# 4-story building parameters
building = MDOFShearBuilding(
    masses=np.full(4, 100_000),        # 100 tonnes per floor
    stiffnesses=np.full(4, 50e6),      # 50 MN/m per story
    damping_ratio=0.05,                # 5% damping
    story_heights=np.full(4, 3.5),     # 3.5m story height
)

print(f"T1 = {building.natural_periods[0]:.2f} s")
```

#### Phase 3: Initial Prediction (Time History Analysis)

**Input:** Building model + ground motion  
**Output:** Response time histories

```python
from seismic_twin.analysis import newmark_beta, compute_demand_metrics

# Run time integration
result = newmark_beta(
    M=building.M,
    C=building.C,
    K=building.K,
    ground_acceleration=ground_acceleration,
    dt=0.01,
)

# Compute demand metrics
metrics = compute_demand_metrics(
    displacement=result.displacement,
    velocity=result.velocity,
    absolute_acceleration=result.absolute_acceleration,
    ground_acceleration=ground_acceleration,
    story_heights=building.story_heights,
)

print(f"Max roof displacement: {metrics.max_displacement[-1] * 100:.1f} cm")
print(f"Max inter-story drift: {np.max(metrics.inter_story_drift_ratio) * 100:.2f}%")
```

#### Phase 4: Sensor-Based Calibration (Optional)

**Input:** Measured sensor data  
**Output:** Calibrated model

```python
from seismic_twin.calibration import StructuralCalibration

# Simulate sensor measurements (in practice, from real sensors)
sensor_floors = [0, 1, 2, 3]  # Sensors on all floors
measured_displacement = result.displacement  # Placeholder for real data

# Calibrate
calibration = StructuralCalibration(
    model=building,
    ground_acceleration=ground_acceleration,
    dt=0.01,
    measured_displacement=measured_displacement,
    sensor_floors=sensor_floors,
)

best_result = calibration.calibrate(
    max_iterations=15,
    tolerance=0.02,
)

calibrated_building = calibration.get_calibrated_model()
print(f"Calibrated stiffness factor: {best_result.stiffness_factor:.2f}")
```

#### Phase 5: Uncertainty Quantification

**Input:** Calibrated model  
**Output:** Probabilistic response bounds

```python
from seismic_twin.uncertainty import UncertaintyAnalysis

uncertainty = UncertaintyAnalysis(
    model=calibrated_building,
    ground_acceleration=ground_acceleration,
    dt=0.01,
)

mc_result = uncertainty.run_mc_ensemble(
    n_samples=100,
    stiffness_cov=0.05,   # 5% uncertainty
    damping_cov=0.20,     # 20% uncertainty
    seed=42,
)

drift_stats = uncertainty.get_drift_statistics()
print(f"Mean drift: {drift_stats['mean'] * 100:.2f}%")
print(f"95th percentile: {drift_stats['p95'] * 100:.2f}%")
```

### Visualization

```python
from seismic_twin.visualization.plots import create_results_figure

fig = create_results_figure(
    time=time,
    ground_acceleration=ground_acceleration,
    initial_displacement=result.displacement,
    calibrated_displacement=calibrated_result.displacement,
    measured_displacement=measured_displacement,
    calibration_iterations=iterations,
    calibration_nrmse=nrmse_history,
    mc_mean=mc_result.displacement_bounds.percentile_50,
    mc_lower=mc_result.displacement_bounds.percentile_5,
    mc_upper=mc_result.displacement_bounds.percentile_95,
    drift_ratios=metrics.inter_story_drift_ratio,
    floor=-1,  # Top floor
)

fig.savefig('results.png', dpi=150, bbox_inches='tight')
```

---

## Dashboard Interface

### Overview

The **interactive web dashboard** provides a no-code interface for the complete simulation workflow through **5 interconnected pages**:

```
1. Building → 2. Ground Motion → 3. Wave Prediction → 4. Simulation → 5. Results
```

### Page-by-Page Breakdown

#### Page 1: Building Configuration (`/building`)

**Purpose:** Define structural model

**Features:**
- **Manual Input:** Stories, mass per floor, stiffness per story, damping, story height
- **Preset Selection:** Pre-configured building types
  - Low-rise RC Frame (3 stories)
  - Mid-rise RC Frame (8 stories)
  - High-rise Steel (20 stories)
  - Historic Masonry (4 stories)
  - Light Wood Frame (2 stories)
  - Industrial Steel (1 story)
- **Location Settings:** Latitude/longitude for site-specific predictions
- **Modal Analysis:** View natural periods and mode shapes
- **Import/Export:** JSON configuration files

**UI Components:**
- Number input sliders
- Preset dropdown
- Mode shape visualization (Plotly)
- Validation indicators (✓ Building configured)

#### Page 2: Ground Motion (`/ground-motion`)

**Purpose:** Define seismic excitation

**Features:**
- **Synthetic Generation:**
  - Target PGA (g)
  - Duration (s)
  - Predominant frequency (Hz)
  - Bandwidth (Hz)
  - **Vertical component** with V/H ratio control
- **Real Earthquake Data:**
  - USGS event ID (e.g., ci38457511 for Ridgecrest)
  - Station/channel selection
  - Automatic fetching from SCEDC S3
- **Preset Scenarios:**
  - Moderate - Stiff Soil (0.2g)
  - Strong - Soft Soil (0.4g)
  - Very Strong - Near Fault (0.6g)
  - Design Level DBE (0.3g)
  - Maximum Considered MCE (0.5g)

**UI Components:**
- Tab layout (Synthetic | Real | Presets)
- Waveform plot (time-history)
- Response spectrum plot
- PGA indicator
- Vertical component checkbox

#### Page 3: Wave Prediction (`/wave-prediction`)

**Purpose:** GMPE-based ground motion prediction

**Features:**
- **Event Loading:** Fetch earthquake by USGS ID
- **Station Network:** Display available recording stations
- **Prediction Methods:**
  - Station-to-station prediction
  - Predict at building location
- **Validation:** Compare predicted vs. actual
  - Waveform comparison
  - Response spectrum comparison
  - Quality grade (A-F)
- **Transfer:** Send predicted waveform to Simulation page

**Workflow:**
1. Set building location (optional)
2. Load event (e.g., ci38457511)
3. Select target/source stations OR click "Predict at Building"
4. Review validation metrics
5. Click "Use for Simulation"

**UI Components:**
- Event input field
- Station map (lat/lon scatter)
- Prediction controls
- Validation tabs (Waveforms | Spectra | Metrics)
- Transfer button

#### Page 4: Simulation (`/simulation`)

**Purpose:** Run structural analysis

**Features:**
- **Deterministic Analysis:**
  - Newmark-β integration
  - Real-time progress bar (background callback)
  - Horizontal + vertical response (if vertical GM available)
  - Vertical stiffness factor slider (10x-100x)
- **Monte Carlo Analysis:**
  - Number of samples (10-500)
  - Stiffness CoV (%)
  - Damping CoV (%)
  - Mass CoV (%)
- **Pre-flight Checks:**
  - ✓ Building configured
  - ✓ Ground motion loaded
  - ✓ Ready to simulate

**UI Components:**
- "Run Simulation" button (disables during execution)
- Progress indicator
- Monte Carlo toggle
- Parameter sliders
- Status badges

#### Page 5: Results (`/results`)

**Purpose:** Visualize and analyze response

**Features:**
- **7 Visualization Tabs:**
  1. **Summary** - Key metrics with performance indicators
  2. **Time History** - Displacement/velocity/acceleration plots
     - Axis selector: Horizontal | Vertical | Both
  3. **Response Spectrum** - Spectral acceleration vs. period
  4. **Drift Profile** - Inter-story drift with threshold lines (IO/LS/CP)
     - Axis selector for horizontal/vertical results
  5. **Uncertainty Bands** - 5th/50th/95th percentile bounds
  6. **Energy Balance** - Kinetic, strain, damping, input energy
     - Combined from horizontal + vertical
  7. **Mode Shapes** - Animated building deformation

**Summary Metrics:**
- Max displacement (cm)
- Max drift ratio (%) with color coding
- Max floor acceleration (g)
- Fundamental period (s)
- Number of MC samples (if run)

**UI Components:**
- Tab navigation
- Interactive Plotly charts
- Download button (results as JSON)
- Performance badges (IO/LS/CP)

### Dashboard Technology

**Framework:** Plotly Dash (Python)
- Multi-page routing
- Reactive callbacks
- Client-side state management

**State Management:**
- `dcc.Store` components (session-based)
- Pydantic schemas for type safety
- JSON serialization for persistence

**Background Tasks:**
- DiskcacheManager (development)
- Progress updates via long callbacks
- Prevents duplicate submissions

**Styling:**
- Dash Bootstrap Components (dbc)
- Bootstrap Icons
- Responsive grid layout

### Running the Dashboard

```bash
# Install with dashboard dependencies
pip install -e ".[dashboard]"

# Launch
python -m seismic_twin.dashboard

# Opens at http://localhost:8050
```

**Docker:**
```bash
docker compose -f docker-compose.dashboard.yml up --build
```

---

## Data Structures

### Core Result Objects

#### IntegrationResult
```python
@dataclass
class IntegrationResult:
    time: ndarray                     # Time vector (n_steps,)
    displacement: ndarray             # Relative displacement (n_dof, n_steps)
    velocity: ndarray                 # Relative velocity (n_dof, n_steps)
    acceleration: ndarray             # Relative acceleration (n_dof, n_steps)
    absolute_acceleration: ndarray    # Total acceleration (n_dof, n_steps)
```

#### DemandMetrics
```python
@dataclass
class DemandMetrics:
    max_displacement: ndarray         # Peak displacement per floor (n_dof,)
    max_velocity: ndarray             # Peak velocity per floor (n_dof,)
    max_acceleration: ndarray         # Peak acceleration per floor (n_dof,)
    inter_story_drift_ratio: ndarray  # Drift ratios per story (n_dof,)
```

#### CalibrationResult
```python
@dataclass
class CalibrationResult:
    iteration: int
    stiffness_factor: float
    damping_ratio: float
    nrmse: float
    correlation: float
    predicted_displacement: ndarray
```

#### MonteCarloResult
```python
@dataclass
class MonteCarloResult:
    displacement_bounds: UncertaintyBounds
    velocity_bounds: UncertaintyBounds
    acceleration_bounds: UncertaintyBounds
    drift_distribution: ndarray       # Max drift per sample (n_samples,)
    parameter_samples: dict           # Record of sampled parameters
```

#### UncertaintyBounds
```python
@dataclass
class UncertaintyBounds:
    percentile_5: ndarray
    percentile_50: ndarray            # Median
    percentile_95: ndarray
    mean: ndarray
    std: ndarray
```

#### StationPrediction
```python
@dataclass
class StationPrediction:
    predicted_waveform: ndarray       # Acceleration time-series (g)
    predicted_pga: float
    scale_factor: float
    source_station_id: str
    target_station_id: str
    source_lat: float
    source_lon: float
    target_lat: float
    target_lon: float
    source_distance_km: float
    target_distance_km: float
```

#### ValidationResult
```python
@dataclass
class ValidationResult:
    peak_metrics: PeakMetrics         # PGA ratio, error %
    spectrum_metrics: SpectrumMetrics # Goodness-of-fit
    time_series_metrics: TimeMetrics  # Correlation, NRMSE, Arias ratio
    overall_score: float              # Combined score 0-100
    grade: str                        # A, B, C, D, F
```

---

## Mathematical Formulations

### Equation of Motion

**MDOF system subjected to ground excitation:**

```
M·ü(t) + C·u̇(t) + K·u(t) = -M·r·a_g(t)

where:
M = mass matrix (n×n)
C = damping matrix (n×n)
K = stiffness matrix (n×n)
u = relative displacement vector (n×1)
r = influence vector (n×1) [typically ones for horizontal ground motion]
a_g(t) = ground acceleration scalar
```

**Absolute motion:**
```
u_abs = u + r·u_g
ü_abs = ü + r·a_g
```

### Rayleigh Damping

**Proportional damping formulation:**
```
C = α·M + β·K

where α, β are chosen to achieve target damping ratio ζ at two frequencies ω_i, ω_j:

α = 2·ζ·ω_i·ω_j / (ω_i + ω_j)
β = 2·ζ / (ω_i + ω_j)

Resulting damping ratio at frequency ω:
ζ(ω) = (α/2ω) + (β·ω/2)
```

### Newmark-β Integration

**Prediction equations:**
```
u̇_{n+1} = u̇_n + [(1-γ)·Δt]·ü_n + [γ·Δt]·ü_{n+1}
u_{n+1} = u_n + Δt·u̇_n + [(1/2-β)·Δt²]·ü_n + [β·Δt²]·ü_{n+1}

Standard parameters:
β = 1/4, γ = 1/2 (average acceleration, unconditionally stable)
```

**Effective equation (implicit):**
```
K_eff·u_{n+1} = P_eff

K_eff = K + (γ/βΔt)·C + (1/βΔt²)·M
P_eff = external load + predictor terms
```

### Inter-Story Drift Ratio

```
IDR_i = (u_i - u_{i-1}) / h_i

where:
u_i = displacement of floor i
h_i = height of story i
```

### Energy Balance

```
E_kinetic(t) = (1/2)·u̇^T·M·u̇
E_strain(t) = (1/2)·u^T·K·u
E_damping(t) = ∫_0^t u̇^T·C·u̇ dτ
E_input(t) = -∫_0^t (M·r·a_g)^T·u̇ dτ

Conservation: E_input = E_kinetic + E_strain + E_damping
```

### Response Spectrum

**Spectral displacement at period T:**
```
Sd(T) = max|u_SDOF(t)|

where u_SDOF is response of SDOF oscillator with period T and damping ζ
```

**Spectral acceleration:**
```
Sa(T) = (2π/T)²·Sd(T)
```

### GMPE (Boore-Atkinson 2008)

**Median spectral acceleration:**
```
ln(Sa) = e1 + e2·(M-M_h) + e3·(M-M_h)² + e4·(8.5-M)² + e5·(M-M_h) + e6·R + e7·ln(R)
         + b_lin·ln(Vs30/V_ref) + b_nl·ln[(PGA_rock + c)/(PGA_ref + c)]

R = √(R_jb² + h²)
M_h = 6.75 (hinge magnitude)
V_ref = 760 m/s
```

### Haversine Distance Formula

**Epicentral distance on Earth's surface:**
```
a = sin²(Δφ/2) + cos(φ1)·cos(φ2)·sin²(Δλ/2)
c = 2·atan2(√a, √(1-a))
d = R_earth·c

where:
φ = latitude (radians)
λ = longitude (radians)
R_earth = 6371 km
```

---

## Usage Examples

### Example 1: Basic Simulation

```python
import numpy as np
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.analysis import newmark_beta, compute_demand_metrics

# 1. Create building
building = MDOFShearBuilding(
    masses=np.full(5, 100_000),
    stiffnesses=np.full(5, 80e6),
    damping_ratio=0.05,
    story_heights=np.full(5, 3.5),
)

# 2. Generate ground motion
time, acc = generate_synthetic_ground_motion(
    duration=30.0, dt=0.01, target_pga=0.3, predominant_freq=2.0
)

# 3. Run analysis
result = newmark_beta(building.M, building.C, building.K, acc, dt=0.01)

# 4. Compute metrics
metrics = compute_demand_metrics(
    result.displacement, result.velocity,
    result.absolute_acceleration, acc, building.story_heights
)

print(f"Max drift: {np.max(metrics.inter_story_drift_ratio)*100:.2f}%")
```

### Example 2: Calibration Workflow

```python
from seismic_twin.calibration import StructuralCalibration

# Assume measured_displacement from sensors
calibration = StructuralCalibration(
    model=building,
    ground_acceleration=acc,
    dt=0.01,
    measured_displacement=measured_disp,
    sensor_floors=[0, 2, 4],
)

best = calibration.calibrate(max_iterations=15, tolerance=0.02)
calibrated_model = calibration.get_calibrated_model()

print(f"Stiffness factor: {best.stiffness_factor:.2f}")
print(f"Damping ratio: {best.damping_ratio:.3f}")
```

### Example 3: Monte Carlo Analysis

```python
from seismic_twin.uncertainty import UncertaintyAnalysis

ua = UncertaintyAnalysis(calibrated_model, acc, dt=0.01)
mc = ua.run_mc_ensemble(n_samples=100, stiffness_cov=0.05, damping_cov=0.20)

stats = ua.get_drift_statistics()
p_exceed = ua.get_probability_of_exceedance(threshold=0.025)

print(f"95th percentile drift: {stats['p95']*100:.2f}%")
print(f"P(drift > 2.5%) = {p_exceed:.1%}")
```

### Example 4: Wave Prediction

```python
from seismic_twin.prediction import WaveformPredictor, BooreAtkinson2008

predictor = WaveformPredictor(gmpe=BooreAtkinson2008())

prediction = predictor.predict_at_location(
    source_waveform=source_acc,
    source_lat=35.77, source_lon=-117.60,
    target_lat=35.70, target_lon=-117.55,
    event_lat=35.766, event_lon=-117.605,
    event_depth=10.0, event_magnitude=7.1,
    dt=0.01,
)

print(f"Predicted PGA: {prediction.predicted_pga:.3f} g")
print(f"Scale factor: {prediction.scale_factor:.2f}")
```

### Example 5: Real Earthquake Data

```python
from seismic_twin.data import SCEDCS3Fetcher

fetcher = SCEDCS3Fetcher()
record = fetcher.get_ground_motion_record(
    event_id="ci38457511",  # Ridgecrest M7.1
    network="CI",
    station="CLC",
    channel="HNE",
)

# Use in simulation
result = newmark_beta(
    building.M, building.C, building.K,
    ground_acceleration=record.acceleration,
    dt=record.dt,
)

print(f"Station: {record.station}")
print(f"PGA: {record.pga:.3f} g")
print(f"Distance: {record.epicentral_distance_km:.1f} km")
```

### Example 6: Two-Axis Simulation

```python
from seismic_twin.ground_motion import generate_2component_ground_motion

# Generate horizontal + vertical
time, acc_h, acc_v = generate_2component_ground_motion(
    duration=30.0, dt=0.01,
    target_pga=0.3,        # Horizontal PGA
    v_h_ratio=0.67,        # Vertical = 0.67 × horizontal
    predominant_freq=2.0,
)

# Run horizontal analysis
result_h = newmark_beta(building.M, building.C, building.K, acc_h, dt=0.01)

# Run vertical analysis (with axial stiffness)
vertical_stiffness_factor = 50.0  # Axial stiffness >> lateral
K_vertical = building.K * vertical_stiffness_factor
result_v = newmark_beta(building.M, building.C, K_vertical, acc_v, dt=0.01)

print(f"Horizontal max drift: {np.max(result_h.displacement)*100:.1f} cm")
print(f"Vertical max displacement: {np.max(result_v.displacement)*100:.1f} cm")
```

---

## Technology Stack

### Core Dependencies

**Scientific Computing:**
- **NumPy** - Array operations, linear algebra
- **SciPy** - Signal processing (filters), eigenvalue solvers, LU factorization
- **Matplotlib** - Static visualization

**Data Management:**
- **Pandas** - Tabular data handling
- **Pydantic** - Schema validation, type checking

**Seismic Data:**
- **ObsPy** (optional) - Seismic data processing, waveform I/O

### Dashboard Dependencies

**Web Framework:**
- **Dash** - Python web framework
- **Plotly** - Interactive visualizations
- **Dash Bootstrap Components** - UI components, styling

**Background Tasks:**
- **Diskcache** - Cache manager for long-running tasks (development)
- **Celery** (optional) - Distributed task queue (production)

### Development Tools

**Testing:**
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting

**Code Quality:**
- **ruff** - Fast Python linter
- **pre-commit** - Git hooks for code quality

**Containerization:**
- **Docker** - Containerized deployment
- **Docker Compose** - Multi-service orchestration

### Python Version

**Requirement:** Python ≥ 3.9

**Reason:** Uses modern type hints (`from __future__ import annotations`), dataclasses, Pydantic v2

### Installation Options

```bash
# Basic (core simulation)
pip install -e .

# With dashboard
pip install -e ".[dashboard]"

# With real data support
pip install -e ".[data]"

# Full development
pip install -e ".[dev,dashboard,data]"
```

---

## Conclusion

The **Seismic Digital Twin** provides a comprehensive, production-ready platform for seismic building simulation and structural health monitoring. The system integrates:

✅ **Rigorous structural dynamics** (Newmark-β, modal analysis)  
✅ **Realistic earthquake inputs** (synthetic + real SCEDC data)  
✅ **Model calibration** (sensor-based updating)  
✅ **Uncertainty quantification** (Monte Carlo)  
✅ **Wave propagation** (GMPE-based prediction)  
✅ **User-friendly interface** (interactive dashboard)

**Key Strengths:**

1. **Modularity** - Each component (building, ground motion, analysis) is independent and reusable
2. **Validation** - Extensive test suite ensures numerical accuracy
3. **Scalability** - Handles 1-DOF to 20+ story buildings
4. **Extensibility** - Easy to add new GMPEs, building models, or analysis methods
5. **Production-ready** - Docker deployment, type safety, error handling

**Typical Applications:**

- Seismic performance assessment
- Structural health monitoring
- Code compliance verification
- Risk and fragility analysis
- Real-time earthquake response prediction
- Educational demonstrations

The workflow enables both **forward prediction** (what will happen given a scenario) and **inverse calibration** (what are the true properties given observations), making it a true **digital twin** for seismic engineering.

---

**Report Generated:** January 2026  
**For Questions:** See README.md or repository documentation
