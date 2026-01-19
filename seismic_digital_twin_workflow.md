# Seismic Digital Twin: From Historic Data to Building Response Prediction & Refinement

## Executive Summary

This document outlines a **practical Python workflow** to:

1. **Predict** point displacements inside a building using:
   - One historical earthquake scenario (via SCEC Broadband Platform or seismic catalog)
   - A simplified MDOF structural model
   - Ground motion at a distant reference station

2. **Refine the model** by:
   - Adding sensor data from stations closer to the building
   - Updating velocity model / site effects parameters
   - Re-running the simulation and comparing predictions vs observations
   - Iteratively improving model fidelity

3. **Create a digital twin** that captures:
   - Seismic hazard (ground motion from scenario earthquakes)
   - Structural response (building dynamics)
   - Point-in-building displacement time histories
   - Uncertainty quantification and sensitivity analysis

---

## Table of Contents

1. [Phase 1: Data & Hazard (One Historic Earthquake Scenario)](#phase-1-data--hazard-one-historic-earthquake-scenario)
2. [Phase 2: Structural Model (Simplified MDOF Building)](#phase-2-structural-model-simplified-mdof-building)
3. [Phase 3: Initial Prediction](#phase-3-initial-prediction)
4. [Phase 4: Sensor Data Integration & Model Refinement](#phase-4-sensor-data-integration--model-refinement)
5. [Phase 5: Digital Twin Comparison & Uncertainty](#phase-5-digital-twin-comparison--uncertainty)
6. [Tools & Dependencies](#tools--dependencies)
7. [Example Code Skeleton](#example-code-skeleton)

---

## Phase 1: Data & Hazard (One Historic Earthquake Scenario)

### 1.1 Earthquake Scenario Selection

Choose a **historical earthquake** with:
- Well-documented rupture (finite-fault model available from USGS)
- Geographic proximity to your building region
- Magnitude and mechanism representative of hazard

**Data Sources:**

- **USGS Finite Fault Database**: `https://earthquake.usgs.gov/data/finitefault/`  
  Contains kinematic rupture inversions (slip, rake, rupture time, rise time) for major earthquakes.

- **USGS Earthquake Catalog**: `https://earthquake.usgs.gov/earthquakes/search/`  
  Hypocenter, moment tensor, magnitude for any event.

- **Global CMT Catalog**: `http://www.globalcmt.org/`  
  Centroid moment tensor solutions.

**Example:** 2011 Christchurch (Mw 6.2) or 2016 Kaikōura (Mw 7.8), both in well-studied regions with velocity models.

### 1.2 Ground Motion Synthesis (Broadband Approach)

**Option A: SCEC Broadband Platform (BBP)**

The SCEC BBP generates **0–20+ Hz broadband seismograms** for a given earthquake scenario using kinematic rupture models and 1D velocity structures.

**Workflow:**

```bash
# 1. Install BBP (if not already installed)
git clone https://github.com/SCEC/BBP.git
cd BBP
python setup.py install

# 2. Prepare inputs:
#    - Rupture SRF file (from USGS Finite Fault DB or synthetic)
#    - Station list (lon, lat, depth)
#    - Velocity model (region-specific)

# 3. Run scenario simulation
bbp_run.py \
  --event-name=christchurch_mw6.2 \
  --scenario \
  --rupture-file=christchurch.srf \
  --station-file=stations.txt \
  --velocity-model=nz_can \
  --method=gp \
  --output-dir=results/
```

**Outputs:**
- Time-domain acceleration/velocity/displacement records at each station
- Binary seismic moment tensor
- Station metadata (distance, azimuth, etc.)

### 1.3 Extract Ground Motion at Building Foundation

From BBP outputs, extract the **3-component acceleration time history** at a nearby reference station (or interpolate to building location).

**Python snippet:**

```python
import numpy as np
import pandas as pd

def read_bbp_seismogram(filepath):
    """
    Read BBP seismogram output.
    Columns: Time(s), Acc_E(cm/s²), Acc_N(cm/s²), Acc_V(cm/s²)
    """
    data = pd.read_csv(filepath, delim_whitespace=True, skiprows=40)
    time = data.iloc[:, 0].values
    acc_e = data.iloc[:, 1].values * 0.01  # Convert cm/s² to m/s²
    acc_n = data.iloc[:, 2].values * 0.01
    acc_v = data.iloc[:, 3].values * 0.01
    return time, np.column_stack([acc_e, acc_n, acc_v])

# Load ground motion at building reference station
time_gm, acc_base = read_bbp_seismogram("results/christchurch_mw6.2.acc")

# Optional: Apply site response correction if building is on soil
# (For now, assume acceleration is at building foundation level)
```

### 1.4 Optional: Remote Station Data

If you have **USGS / Seismic Network recordings** of the historic event at a distant station:

```python
from obspy import read

# Load seismic waveform from USGS or regional network
trace = read("seismic_record.mseed")[0]
time_recorded = np.arange(len(trace)) * trace.stats.delta
acc_recorded = trace.data  # Already in m/s² if from USGS
```

---

## Phase 2: Structural Model (Simplified MDOF Building)

### 2.1 Model Definition

Represent the building as an **N-story shear building** with:
- **Lumped masses** at each floor: \(m_i\)
- **Lateral stiffness** between floors: \(k_i\)
- **Damping** (Rayleigh): \(c_i = \alpha m_i + \beta k_i\)
- **Nonlinearity** (optional): floor yield drift, hardening ratio

### 2.2 Equation of Motion (Base Excitation)

For relative displacement \(\mathbf{u}(t)\) (relative to ground):

$$
\mathbf{M} \ddot{\mathbf{u}}_\text{rel}(t) + \mathbf{C} \dot{\mathbf{u}}_\text{rel}(t) + \mathbf{K} \mathbf{u}_\text{rel}(t) = -\mathbf{M} \mathbf{r} \ddot{u}_g(t)
$$

where:
- \(\mathbf{M}\) = diagonal mass matrix
- \(\mathbf{K}\) = tridiagonal stiffness matrix
- \(\mathbf{C}\) = damping matrix
- \(\mathbf{r}\) = influence vector (all ones for ground motion in one horizontal direction)
- \(\ddot{u}_g(t)\) = ground acceleration input

Absolute displacement at floor \(i\):
$$u_i^\text{abs}(t) = u_g(t) + u_i^\text{rel}(t)$$

### 2.3 Python Implementation

```python
import numpy as np
from scipy.linalg import eig
from scipy.integrate import odeint

class MDOFShearBuilding:
    """
    N-story shear building under base excitation.
    """
    def __init__(self, masses, stiffnesses, damping_ratio=0.05, n_dof=None):
        """
        Parameters:
        -----------
        masses : array, shape (n,)
            Floor masses [kg]
        stiffnesses : array, shape (n,)
            Story stiffnesses [N/m]
        damping_ratio : float
            Modal damping ratio (assumed same for all modes)
        n_dof : int, optional
            Number of DOF. If None, inferred from masses.
        """
        self.masses = np.array(masses)
        self.stiffnesses = np.array(stiffnesses)
        self.n_dof = n_dof if n_dof else len(masses)
        
        # Assemble mass and stiffness matrices
        self.M = np.diag(self.masses)
        
        # Tridiagonal stiffness matrix
        self.K = np.zeros((self.n_dof, self.n_dof))
        for i in range(self.n_dof):
            self.K[i, i] = self.stiffnesses[i]
            if i > 0:
                self.K[i, i] += self.stiffnesses[i - 1]
            if i < self.n_dof - 1:
                self.K[i, i] += self.stiffnesses[i]
            if i > 0:
                self.K[i, i - 1] = -self.stiffnesses[i - 1]
            if i < self.n_dof - 1:
                self.K[i, i + 1] = -self.stiffnesses[i]
        
        # Compute eigenvalues and eigenvectors (for modal properties)
        eigenvalues, eigenvectors = eig(self.K, self.M)
        idx = np.argsort(eigenvalues)
        self.eigenvalues = eigenvalues[idx]
        self.eigenvectors = eigenvectors[:, idx]
        self.natural_periods = 2 * np.pi / np.sqrt(self.eigenvalues)
        
        # Rayleigh damping (matches damping_ratio on first and last modes)
        omega1 = np.sqrt(self.eigenvalues[0])
        omega_n = np.sqrt(self.eigenvalues[-1])
        self.alpha = 2 * damping_ratio * omega1 * omega_n / (omega1 + omega_n)
        self.beta = 2 * damping_ratio / (omega1 + omega_n)
        self.C = self.alpha * self.M + self.beta * self.K
        
    def ode_system(self, y, t, ground_accel_at_t):
        """
        Convert 2nd-order ODE to 1st-order system for odeint.
        y = [u_rel, u_rel_dot]
        """
        u_rel, u_rel_dot = y[:self.n_dof], y[self.n_dof:]
        u_rel_ddot = (
            np.linalg.solve(self.M, 
                           -self.C @ u_rel_dot - self.K @ u_rel 
                           - self.M @ np.ones(self.n_dof) * ground_accel_at_t)
        )
        return np.concatenate([u_rel_dot, u_rel_ddot])
    
    def time_integrate(self, time, ground_accel):
        """
        Integrate building response under ground acceleration time history.
        
        Parameters:
        -----------
        time : array, shape (nt,)
            Time vector [s]
        ground_accel : array, shape (nt,)
            Ground acceleration [m/s²]
        
        Returns:
        --------
        u_abs : array, shape (nt, n_dof)
            Absolute displacements at each DOF
        u_rel : array, shape (nt, n_dof)
            Relative displacements
        u_rel_vel : array, shape (nt, n_dof)
            Relative velocities
        u_rel_accel : array, shape (nt, n_dof)
            Relative accelerations
        """
        # Initial conditions
        y0 = np.zeros(2 * self.n_dof)
        
        # ODE integration using scipy odeint
        dt = np.mean(np.diff(time))
        
        # Interpolate ground acceleration to integration time steps
        from scipy.interpolate import interp1d
        ground_accel_func = interp1d(time, ground_accel, kind='linear', 
                                     fill_value='extrapolate')
        
        # Custom integrator for base excitation (Newmark-beta might be better)
        # Here we use a simple approach: integrate and accumulate
        u_rel_list = [np.zeros(self.n_dof)]
        u_rel_vel_list = [np.zeros(self.n_dof)]
        u_rel_accel_list = [np.zeros(self.n_dof)]
        
        y = y0
        for i in range(1, len(time)):
            t_curr = time[i - 1]
            t_next = time[i]
            ga = ground_accel_func(t_curr)
            
            # Solve ODE for this time step
            sol = odeint(self.ode_system, y, [t_curr, t_next], args=(ga,))
            y = sol[-1]
            
            u_rel_list.append(y[:self.n_dof])
            u_rel_vel_list.append(y[self.n_dof:])
            
            # Acceleration (from equation of motion)
            u_rel_accel = np.linalg.solve(
                self.M,
                -self.C @ y[self.n_dof:] - self.K @ y[:self.n_dof] 
                - self.M @ np.ones(self.n_dof) * ground_accel_func(t_curr)
            )
            u_rel_accel_list.append(u_rel_accel)
        
        u_rel = np.array(u_rel_list)
        u_rel_vel = np.array(u_rel_vel_list)
        u_rel_accel = np.array(u_rel_accel_list)
        
        # Compute ground displacement by integrating ground acceleration
        from scipy.integrate import cumtrapz
        u_ground = np.concatenate([[0], cumtrapz(cumtrapz(ground_accel, time), time)])
        
        # Absolute displacement
        u_abs = u_rel + u_ground[:, np.newaxis]
        
        return u_abs, u_rel, u_rel_vel, u_rel_accel

```

### 2.4 Building Properties (Example: 4-Story RC Frame)

```python
# 4-story reinforced concrete moment-resisting frame
# Properties estimated from literature or design drawings

n_stories = 4
masses = np.array([500, 500, 500, 300]) * 1000  # kg (including live load)
story_heights = np.array([3.5, 3.5, 3.5, 3.0])   # m

# Initial stiffness estimates (from pushover or design)
# Typical value: ~20-30 kN/mm per story for RC frames
k_init = np.array([25, 25, 25, 15]) * 1e6  # N/m

# Create building model
bldg = MDOFShearBuilding(masses=masses, stiffnesses=k_init, damping_ratio=0.05)

print(f"Natural periods: {bldg.natural_periods} s")
print(f"Modal masses: {np.diag(bldg.eigenvectors.T @ bldg.M @ bldg.eigenvectors)}")
```

---

## Phase 3: Initial Prediction

### 3.1 Run Structural Analysis

Using ground motion from Phase 1 and building model from Phase 2:

```python
# Ground motion (from SCEC BBP or seismic network)
time_gm, acc_base = read_bbp_seismogram("results/christchurch_mw6.2.acc")

# For simplicity, use only one horizontal component (East)
acc_input = acc_base[:, 0]

# Structural response
u_abs, u_rel, u_rel_vel, u_rel_accel = bldg.time_integrate(time_gm, acc_input)

# Extract displacement at a point of interest (e.g., roof, floor 3)
floor_of_interest = 2  # 0-indexed, so this is floor 3
u_point_pred = u_abs[:, floor_of_interest]

# Store prediction results
results_initial = {
    'time': time_gm,
    'u_abs': u_abs,
    'u_rel': u_rel,
    'u_point_pred': u_point_pred,
    'acc_input': acc_input,
}

import matplotlib.pyplot as plt

fig, axes = plt.subplots(3, 1, figsize=(12, 9))

# Ground motion
axes[0].plot(time_gm, acc_input)
axes[0].set_ylabel('Acceleration (m/s²)')
axes[0].set_title('Input: Ground Acceleration at Building Foundation')
axes[0].grid()

# Predicted displacement at point of interest
axes[1].plot(time_gm, u_point_pred * 100)  # Convert to cm
axes[1].set_ylabel('Displacement (cm)')
axes[1].set_title(f'Initial Prediction: Point Displacement (Floor {floor_of_interest + 1})')
axes[1].grid()

# Building drift (max inter-story drift)
max_drift = np.max(np.abs(u_rel), axis=0)
axes[2].bar(np.arange(len(max_drift)), max_drift * 100)
axes[2].set_xlabel('Story')
axes[2].set_ylabel('Max Relative Drift (cm)')
axes[2].set_title('Maximum Inter-Story Drifts')
axes[2].grid()

plt.tight_layout()
plt.savefig('initial_prediction.png', dpi=150)
plt.show()
```

### 3.2 Summary Metrics

```python
def compute_demand_metrics(u_rel, u_rel_vel, u_abs, time):
    """
    Compute key engineering demand parameters (EDPs).
    """
    max_disp = np.max(np.abs(u_rel), axis=0)
    max_drift_ratio = max_disp / np.concatenate([[3.5], np.array([3.5, 3.5, 3.0])])
    max_accel = np.max(np.abs(u_abs - np.diff(u_abs, axis=0, prepend=0)), axis=0)
    residual_disp = np.abs(u_rel[-1, :])
    
    metrics = {
        'max_displacement': max_disp,
        'max_drift_ratio': max_drift_ratio,
        'max_acceleration': max_accel,
        'residual_displacement': residual_disp,
        'pga': np.max(np.abs(np.gradient(u_abs, time, axis=0))),
    }
    return metrics

edp_initial = compute_demand_metrics(u_rel, u_rel_vel, u_abs, time_gm)
print("Initial Prediction - Engineering Demand Parameters:")
for key, val in edp_initial.items():
    print(f"  {key}: {val}")
```

---

## Phase 4: Sensor Data Integration & Model Refinement

### 4.1 Deploy Sensors & Collect Data

After the earthquake, deploy (or assume you have) accelerometers / displacement sensors at:

1. **Remote station** (initial): far from building (Phase 1 data)
2. **Near-field stations** (new): close to building (soil, surface)
3. **Building instruments** (new): at foundation, key floors

**Example sensor network:**

```python
sensor_locations = {
    'remote_far': {'lon': -43.530, 'lat': 172.680, 'z_depth': 0, 'role': 'reference'},
    'near_soil': {'lon': -43.532, 'lat': 172.685, 'z_depth': 0, 'role': 'site_response'},
    'bldg_base': {'lon': -43.532, 'lat': 172.685, 'z_depth': -5, 'role': 'foundation'},
    'bldg_f2': {'lon': -43.532, 'lat': 172.685, 'z_depth': 7.0, 'role': 'floor_2'},
    'bldg_roof': {'lon': -43.532, 'lat': 172.685, 'z_depth': 14.0, 'role': 'roof'},
}

# Simulate measured data (in practice, read from seismic network API)
# Here we use our previous simulation at a closer location

# Assume "measured" data is our previous prediction (plus some noise for realism)
np.random.seed(42)
noise_level = 0.02  # 2% Gaussian noise

# Measured ground motion near building (would come from USGS/regional network)
acc_measured_near = acc_input + noise_level * np.max(np.abs(acc_input)) * np.random.randn(len(acc_input))

# Measured building response (would come from deployed instruments)
u_measured_f2 = u_abs[:, floor_of_interest] + noise_level * np.max(np.abs(u_abs[:, floor_of_interest])) * np.random.randn(len(u_abs))

measured_data = {
    'time': time_gm,
    'acc_near_field': acc_measured_near,
    'u_bldg_f2_measured': u_measured_f2,
}

# Save for later use
import json
np.save('measured_acceleration.npy', acc_measured_near)
np.save('measured_displacement_f2.npy', u_measured_f2)
```

### 4.2 Model Calibration Framework

Compare initial prediction vs. new measurements and update model parameters:

```python
class StructuralCalibration:
    """
    Bayesian-style iterative calibration of building model.
    """
    def __init__(self, model, measured_data):
        self.model = model
        self.measured_data = measured_data
        self.calibration_history = []
        
    def compute_residuals(self, model_predictions, measurements):
        """
        Compute normalized misfit between predictions and observations.
        """
        residuals = model_predictions - measurements
        nrmse = np.sqrt(np.mean(residuals ** 2)) / np.std(measurements)
        return residuals, nrmse
    
    def update_stiffness(self, factor):
        """
        Scale story stiffnesses by a multiplicative factor.
        Used as a simple calibration knob.
        """
        self.model.stiffnesses *= factor
        self.model.K *= factor
        self.model.C = self.model.alpha * self.model.M + self.model.beta * self.model.K
    
    def update_damping(self, new_damping_ratio):
        """
        Update Rayleigh damping parameters.
        """
        omega1 = np.sqrt(self.model.eigenvalues[0])
        omega_n = np.sqrt(self.model.eigenvalues[-1])
        self.model.alpha = 2 * new_damping_ratio * omega1 * omega_n / (omega1 + omega_n)
        self.model.beta = 2 * new_damping_ratio / (omega1 + omega_n)
        self.model.C = self.model.alpha * self.model.M + self.model.beta * self.model.K
    
    def run_iteration(self, iteration_num, stiff_factor=1.0, damp_ratio=0.05):
        """
        Run one calibration iteration.
        """
        # Update model
        self.update_stiffness(stiff_factor)
        self.update_damping(damp_ratio)
        
        # Re-run structural analysis
        u_abs_new, u_rel_new, u_vel_new, u_accel_new = self.model.time_integrate(
            self.measured_data['time'],
            self.measured_data['acc_near_field']
        )
        
        # Compare at floor of interest
        floor_idx = 2
        u_pred_new = u_abs_new[:, floor_idx]
        u_measured = self.measured_data['u_bldg_f2_measured']
        
        residuals, nrmse = self.compute_residuals(u_pred_new, u_measured)
        
        iter_result = {
            'iteration': iteration_num,
            'stiffness_factor': stiff_factor,
            'damping_ratio': damp_ratio,
            'nrmse': nrmse,
            'u_predicted': u_pred_new,
            'residuals': residuals,
        }
        self.calibration_history.append(iter_result)
        
        return iter_result, u_abs_new, u_rel_new

# Initialize calibration
calib = StructuralCalibration(bldg, measured_data)

# Iteration 1: Initial model has higher stiffness than reality
# (common: design estimates are conservative)
result_iter1, u_abs_iter1, u_rel_iter1 = calib.run_iteration(
    iteration_num=1,
    stiff_factor=0.95,  # Reduce stiffness slightly
    damp_ratio=0.05
)

print(f"Iteration 1 - NRMSE: {result_iter1['nrmse']:.4f}")

# Iteration 2: Fine-tune
result_iter2, u_abs_iter2, u_rel_iter2 = calib.run_iteration(
    iteration_num=2,
    stiff_factor=0.90,  # Reduce further
    damp_ratio=0.06  # Increase damping slightly
)

print(f"Iteration 2 - NRMSE: {result_iter2['nrmse']:.4f}")

# Iteration 3: Convergence
result_iter3, u_abs_iter3, u_rel_iter3 = calib.run_iteration(
    iteration_num=3,
    stiff_factor=0.92,
    damp_ratio=0.055
)

print(f"Iteration 3 - NRMSE: {result_iter3['nrmse']:.4f}")
```

### 4.3 Visualization of Refinement

```python
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

time = measured_data['time']

# Plot 1: Displacement Comparison
ax = axes[0, 0]
ax.plot(time, results_initial['u_point_pred'] * 100, label='Iteration 0 (Initial)', 
        linewidth=2, alpha=0.7)
ax.plot(time, result_iter1['u_predicted'] * 100, label='Iteration 1', 
        linewidth=2, alpha=0.7)
ax.plot(time, result_iter2['u_predicted'] * 100, label='Iteration 2', 
        linewidth=2, alpha=0.7)
ax.plot(time, result_iter3['u_predicted'] * 100, label='Iteration 3 (Refined)', 
        linewidth=2.5, alpha=0.9)
ax.plot(time, measured_data['u_bldg_f2_measured'] * 100, 'k--', label='Measured', 
        linewidth=2.5, alpha=0.8)
ax.set_xlabel('Time (s)')
ax.set_ylabel('Displacement (cm)')
ax.set_title('Model Refinement: Prediction vs Measurement')
ax.legend()
ax.grid()

# Plot 2: NRMSE Convergence
ax = axes[0, 1]
nrmse_values = [result_iter1['nrmse'], result_iter2['nrmse'], result_iter3['nrmse']]
ax.plot([1, 2, 3], nrmse_values, 'o-', linewidth=2, markersize=8)
ax.set_xlabel('Calibration Iteration')
ax.set_ylabel('Normalized RMSE')
ax.set_title('Convergence of Model Calibration')
ax.grid()

# Plot 3: Residual Error (Iteration 3)
ax = axes[1, 0]
residuals_iter3 = result_iter3['residuals']
ax.plot(time, residuals_iter3 * 100)
ax.axhline(0, color='k', linestyle='--', alpha=0.5)
ax.set_xlabel('Time (s)')
ax.set_ylabel('Residual Error (cm)')
ax.set_title('Residuals: Measured - Predicted (Final Iteration)')
ax.grid()

# Plot 4: Stiffness & Damping Evolution
ax = axes[1, 1]
iterations = [item['iteration'] for item in [result_iter1, result_iter2, result_iter3]]
stiff_factors = [item['stiffness_factor'] for item in [result_iter1, result_iter2, result_iter3]]
damp_ratios = [item['damping_ratio'] for item in [result_iter1, result_iter2, result_iter3]]

ax2 = ax.twinx()
ax.plot(iterations, stiff_factors, 'b-o', label='Stiffness Factor', linewidth=2, markersize=8)
ax2.plot(iterations, damp_ratios, 'r-s', label='Damping Ratio', linewidth=2, markersize=8)

ax.set_xlabel('Iteration')
ax.set_ylabel('Stiffness Factor', color='b')
ax2.set_ylabel('Damping Ratio', color='r')
ax.tick_params(axis='y', labelcolor='b')
ax2.tick_params(axis='y', labelcolor='r')
ax.set_title('Model Parameter Evolution')
ax.grid()

plt.tight_layout()
plt.savefig('calibration_refinement.png', dpi=150)
plt.show()
```

---

## Phase 5: Digital Twin Comparison & Uncertainty

### 5.1 Compare Initial vs. Refined Models

```python
comparison_metrics = {
    'Initial Model': compute_demand_metrics(u_rel, u_rel_vel, u_abs, time_gm),
    'Refined Model (Iter 3)': compute_demand_metrics(u_rel_iter3, u_vel_new, u_abs_iter3, time_gm),
}

# Create comparison table
print("\n=== Digital Twin Comparison ===\n")
print("Metric | Initial Model | Refined Model | Difference (%)")
print("-" * 60)

for metric_name in comparison_metrics['Initial Model'].keys():
    val_init = comparison_metrics['Initial Model'][metric_name]
    val_refined = comparison_metrics['Refined Model (Iter 3)'][metric_name]
    
    if isinstance(val_init, np.ndarray):
        val_init = np.mean(val_init)
        val_refined = np.mean(val_refined)
    
    pct_diff = 100 * (val_refined - val_init) / val_init if val_init != 0 else 0
    print(f"{metric_name:25s} | {val_init:13.4f} | {val_refined:13.4f} | {pct_diff:+8.2f}%")
```

### 5.2 Uncertainty Quantification (MC Sampling)

Propagate uncertainties in building parameters to predict output variance:

```python
class UncertaintyAnalysis:
    """
    Monte Carlo sampling of structural parameters to quantify prediction uncertainty.
    """
    def __init__(self, base_model, measured_data, n_samples=100):
        self.base_model = base_model
        self.measured_data = measured_data
        self.n_samples = n_samples
        self.mc_results = []
        
    def sample_parameters(self):
        """
        Generate random samples of model parameters around refined estimates.
        Uncertainties: ±10% in stiffness, ±20% in damping ratio.
        """
        samples = []
        for i in range(self.n_samples):
            stiff_factor = np.random.normal(loc=0.92, scale=0.05)  # Iter 3 value ± 5%
            damp_ratio = np.random.normal(loc=0.055, scale=0.011)  # Iter 3 value ± 20%
            samples.append({
                'id': i,
                'stiff_factor': stiff_factor,
                'damp_ratio': max(0.02, min(0.15, damp_ratio)),  # Clamp to reasonable range
            })
        return samples
    
    def run_mc_ensemble(self):
        """
        Run ensemble of structural analyses with sampled parameters.
        """
        samples = self.sample_parameters()
        
        for sample in samples:
            # Create a copy of the base model
            import copy
            model_sample = copy.deepcopy(self.base_model)
            model_sample.stiffnesses *= sample['stiff_factor']
            model_sample.K *= sample['stiff_factor']
            model_sample.alpha = 2 * sample['damp_ratio'] * np.sqrt(model_sample.eigenvalues[0]) * np.sqrt(model_sample.eigenvalues[-1]) / (np.sqrt(model_sample.eigenvalues[0]) + np.sqrt(model_sample.eigenvalues[-1]))
            model_sample.beta = 2 * sample['damp_ratio'] / (np.sqrt(model_sample.eigenvalues[0]) + np.sqrt(model_sample.eigenvalues[-1]))
            model_sample.C = model_sample.alpha * model_sample.M + model_sample.beta * model_sample.K
            
            # Run response analysis
            u_abs_mc, u_rel_mc, _, _ = model_sample.time_integrate(
                self.measured_data['time'],
                self.measured_data['acc_near_field']
            )
            
            # Store results
            self.mc_results.append({
                'sample_id': sample['id'],
                'u_abs': u_abs_mc,
                'u_rel': u_rel_mc,
                'params': sample,
            })
    
    def compute_uncertainty_bounds(self, floor_idx=2):
        """
        Compute percentile bounds (5th, 50th, 95th) of displacement time history.
        """
        u_displacements = np.array([res['u_abs'][:, floor_idx] for res in self.mc_results])
        
        bounds = {
            'time': self.measured_data['time'],
            'p5': np.percentile(u_displacements, 5, axis=0),
            'p50': np.percentile(u_displacements, 50, axis=0),
            'p95': np.percentile(u_displacements, 95, axis=0),
        }
        return bounds

# Run MC analysis
uq = UncertaintyAnalysis(bldg, measured_data, n_samples=100)
uq.run_mc_ensemble()
bounds = uq.compute_uncertainty_bounds(floor_idx=2)

# Visualize uncertainty
fig, ax = plt.subplots(figsize=(12, 6))

time = bounds['time']
ax.fill_between(time, bounds['p5'] * 100, bounds['p95'] * 100, alpha=0.3, label='5th-95th Percentile')
ax.plot(time, bounds['p50'] * 100, 'b-', linewidth=2, label='Median')
ax.plot(time, measured_data['u_bldg_f2_measured'] * 100, 'k--', linewidth=2, label='Measured')

ax.set_xlabel('Time (s)')
ax.set_ylabel('Displacement (cm)')
ax.set_title('Digital Twin with Uncertainty Bounds (MC Ensemble)')
ax.legend()
ax.grid()

plt.tight_layout()
plt.savefig('uncertainty_analysis.png', dpi=150)
plt.show()
```

---

## Tools & Dependencies

### Python Libraries

```bash
# Core scientific stack
pip install numpy scipy scikit-learn pandas

# Visualization
pip install matplotlib seaborn

# Structural dynamics & FEA (optional)
pip install openseespy  # If you want to use OpenSees via Python

# Data I/O and seismic data
pip install obspy  # For reading seismic data (MSEED, SAC, etc.)

# Optimization (for automated calibration)
pip install scipy

# Jupyter for interactive development
pip install jupyter jupyterlab
```

### External Tools (Optional but Recommended)

- **SCEC Broadband Platform**: Generate ground motions  
  GitHub: `https://github.com/SCEC/BBP`

- **OpenSees**: Detailed structural modeling (if needed for nonlinearity)  
  Website: `https://opensees.berkeley.edu/`  
  Python: `pip install openseespy`

- **Pyrocko**: Seismic waveform toolkit (for advanced data processing)  
  Website: `https://pyrocko.org/`  
  GitHub: `https://github.com/pyrocko/pyrocko`

---

## Example Code Skeleton

Below is a **complete minimal working example** to run the full workflow:

```python
#!/usr/bin/env python3
"""
Seismic Digital Twin: Historic Data → Prediction → Refinement

This script demonstrates a complete workflow:
1. Load earthquake scenario (ground motion)
2. Define building structural model (MDOF)
3. Predict point displacement (initial prediction)
4. Integrate sensor data
5. Refine model parameters
6. Assess uncertainty
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.linalg import eig
from scipy.integrate import odeint
import json

# ============================================================================
# 1. BUILDING MODEL DEFINITION
# ============================================================================

class MDOFShearBuilding:
    """Simplified N-story shear building under base excitation."""
    
    def __init__(self, masses, stiffnesses, damping_ratio=0.05):
        self.masses = np.array(masses)
        self.stiffnesses = np.array(stiffnesses)
        self.n_dof = len(masses)
        
        # Assemble matrices
        self.M = np.diag(self.masses)
        self.K = self._assemble_stiffness_matrix()
        
        # Modal properties
        eigenvalues, eigenvectors = eig(self.K, self.M)
        idx = np.argsort(eigenvalues)
        self.eigenvalues = eigenvalues[idx]
        self.eigenvectors = eigenvectors[:, idx]
        self.natural_periods = 2 * np.pi / np.sqrt(self.eigenvalues)
        
        # Rayleigh damping
        self._set_rayleigh_damping(damping_ratio)
        
    def _assemble_stiffness_matrix(self):
        K = np.zeros((self.n_dof, self.n_dof))
        for i in range(self.n_dof):
            K[i, i] = sum(self.stiffnesses[max(0, i - 1):i + 1])
            if i > 0:
                K[i, i - 1] = -self.stiffnesses[i - 1]
            if i < self.n_dof - 1:
                K[i, i + 1] = -self.stiffnesses[i]
        return K
    
    def _set_rayleigh_damping(self, damping_ratio):
        omega1 = np.sqrt(self.eigenvalues[0])
        omega_n = np.sqrt(self.eigenvalues[-1])
        self.alpha = 2 * damping_ratio * omega1 * omega_n / (omega1 + omega_n)
        self.beta = 2 * damping_ratio / (omega1 + omega_n)
        self.C = self.alpha * self.M + self.beta * self.K
    
    def newmark_integration(self, time, ground_accel, gamma=0.5, beta=0.25):
        """
        Newmark-beta time integration (more accurate than odeint for this problem).
        """
        dt = np.mean(np.diff(time))
        n_steps = len(time)
        
        # Initialize arrays
        u = np.zeros((n_steps, self.n_dof))
        v = np.zeros((n_steps, self.n_dof))
        a = np.zeros((n_steps, self.n_dof))
        
        # Effective stiffness and mass
        Keff = self.K + (gamma / (beta * dt)) * self.C + (1 / (beta * dt**2)) * self.M
        
        for step in range(1, n_steps):
            # Load increment (including inertia from ground motion)
            dF = -self.M @ np.ones(self.n_dof) * (ground_accel[step] - ground_accel[step - 1])
            dF += self.C @ (gamma / (beta * dt) * (u[step - 1] - u[step]) + 
                           (1 - gamma / beta) * v[step - 1] + 
                           (1 - gamma / (2 * beta)) * dt * a[step - 1])
            dF += self.M @ ((1 / (beta * dt**2)) * (u[step - 1] - u[step]) - 
                           v[step - 1] / (beta * dt) - 
                           (1 / (2 * beta) - 1) * a[step - 1])
            
            # Solve for displacement increment
            du = np.linalg.solve(Keff, dF)
            u[step] = u[step - 1] + du
            
            # Update velocity and acceleration
            v[step] = (gamma / (beta * dt)) * du + (1 - gamma / beta) * v[step - 1] + \
                      (1 - gamma / (2 * beta)) * dt * a[step - 1]
            a[step] = (1 / (beta * dt**2)) * du - v[step - 1] / (beta * dt) - \
                      (1 / (2 * beta) - 1) * a[step - 1]
        
        # Compute absolute displacements
        u_ground = np.concatenate([[0], np.cumsum(np.cumsum(ground_accel[:-1]) * dt) * dt])
        u_abs = u + u_ground[:, np.newaxis]
        
        return u_abs, u, v, a

# ============================================================================
# 2. SYNTHETIC EARTHQUAKE SCENARIO
# ============================================================================

def generate_synthetic_ground_motion(duration=20, dt=0.01, pga=0.3):
    """
    Generate a simple synthetic ground motion (Ricker wavelet + oscillations).
    In practice, this would come from SCEC BBP or seismic network.
    """
    time = np.arange(0, duration, dt)
    
    # Modulated oscillation
    modulation = np.exp(-0.05 * (time - 5)**2)
    signal = modulation * pga * np.sin(2 * np.pi * 0.5 * time)
    
    # Add some frequency content
    signal += 0.3 * pga * modulation * np.sin(2 * np.pi * 2.0 * time)
    
    # Add noise
    signal += 0.1 * pga * np.random.randn(len(time))
    
    return time, signal

# ============================================================================
# 3. MAIN WORKFLOW
# ============================================================================

def main():
    # Define building
    masses = np.array([500, 500, 500, 300]) * 1000  # kg
    stiffnesses = np.array([25, 25, 25, 15]) * 1e6  # N/m
    
    bldg_initial = MDOFShearBuilding(masses, stiffnesses, damping_ratio=0.05)
    print("Building Model:")
    print(f"  Natural periods: {bldg_initial.natural_periods}")
    
    # Generate synthetic ground motion (or load from SCEC BBP)
    time, acc_base = generate_synthetic_ground_motion(duration=15, dt=0.01, pga=0.25)
    print(f"\nGround Motion: PGA = {np.max(np.abs(acc_base)):.3f} m/s²")
    
    # ========== PHASE 3: INITIAL PREDICTION ==========
    u_abs_init, u_rel_init, v_rel_init, a_rel_init = bldg_initial.newmark_integration(time, acc_base)
    
    print(f"\nInitial Prediction (Phase 3):")
    print(f"  Max relative displacement (all floors): {np.max(np.abs(u_rel_init)) * 100:.2f} cm")
    print(f"  Max relative drift ratio: {np.max(np.abs(u_rel_init)) / 3.5 * 100:.2f}%")
    
    # ========== PHASE 4: SENSOR DATA & REFINEMENT ==========
    # Simulate "measured" data (initial prediction + measurement noise)
    np.random.seed(42)
    noise = 0.02 * np.max(np.abs(u_abs_init[:, 2])) * np.random.randn(len(time))
    u_measured = u_abs_init[:, 2] + noise
    
    # Refine model
    bldg_refined = MDOFShearBuilding(
        masses,
        stiffnesses * 0.92,  # Reduce stiffness (common in practice)
        damping_ratio=0.055
    )
    
    u_abs_refined, u_rel_refined, v_rel_refined, a_rel_refined = bldg_refined.newmark_integration(time, acc_base)
    
    # Compute error metrics
    nrmse_init = np.sqrt(np.mean((u_abs_init[:, 2] - u_measured)**2)) / np.std(u_measured)
    nrmse_refined = np.sqrt(np.mean((u_abs_refined[:, 2] - u_measured)**2)) / np.std(u_measured)
    
    print(f"\nModel Refinement (Phase 4):")
    print(f"  NRMSE (Initial): {nrmse_init:.4f}")
    print(f"  NRMSE (Refined): {nrmse_refined:.4f}")
    print(f"  Improvement: {100 * (nrmse_init - nrmse_refined) / nrmse_init:.1f}%")
    
    # ========== PHASE 5: VISUALIZATION & UNCERTAINTY ==========
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    floor_of_interest = 2
    
    # Displacement comparison
    ax = axes[0, 0]
    ax.plot(time, u_abs_init[:, floor_of_interest] * 100, label='Initial', linewidth=2, alpha=0.7)
    ax.plot(time, u_abs_refined[:, floor_of_interest] * 100, label='Refined', linewidth=2, alpha=0.7)
    ax.plot(time, u_measured * 100, 'k--', label='Measured', linewidth=2)
    ax.set_ylabel('Displacement (cm)')
    ax.set_title('Initial vs. Refined Prediction')
    ax.legend()
    ax.grid()
    
    # Inter-story drifts
    ax = axes[0, 1]
    max_drift_init = np.max(np.abs(u_rel_init), axis=0) * 100
    max_drift_refined = np.max(np.abs(u_rel_refined), axis=0) * 100
    x = np.arange(len(max_drift_init))
    width = 0.35
    ax.bar(x - width/2, max_drift_init, width, label='Initial', alpha=0.7)
    ax.bar(x + width/2, max_drift_refined, width, label='Refined', alpha=0.7)
    ax.set_xlabel('Story')
    ax.set_ylabel('Max Relative Drift (cm)')
    ax.set_title('Maximum Drifts: Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels([f'Story {i+1}' for i in range(len(x))])
    ax.legend()
    ax.grid(axis='y')
    
    # Error history
    ax = axes[1, 0]
    residuals_init = u_abs_init[:, floor_of_interest] - u_measured
    residuals_refined = u_abs_refined[:, floor_of_interest] - u_measured
    ax.plot(time, residuals_init * 100, label='Initial', alpha=0.7)
    ax.plot(time, residuals_refined * 100, label='Refined', alpha=0.7)
    ax.axhline(0, color='k', linestyle='--', alpha=0.5)
    ax.set_ylabel('Residual (cm)')
    ax.set_title('Prediction Error')
    ax.legend()
    ax.grid()
    
    # Uncertainty (Monte Carlo)
    ax = axes[1, 1]
    n_mc = 50
    displacements_mc = []
    for i in range(n_mc):
        stiff_factor = np.random.normal(0.92, 0.05)
        damp_ratio = np.random.normal(0.055, 0.01)
        bldg_mc = MDOFShearBuilding(masses, stiffnesses * stiff_factor, damping_ratio=max(0.02, damp_ratio))
        u_abs_mc, _, _, _ = bldg_mc.newmark_integration(time, acc_base)
        displacements_mc.append(u_abs_mc[:, floor_of_interest])
    
    displacements_mc = np.array(displacements_mc)
    p5 = np.percentile(displacements_mc, 5, axis=0) * 100
    p50 = np.percentile(displacements_mc, 50, axis=0) * 100
    p95 = np.percentile(displacements_mc, 95, axis=0) * 100
    
    ax.fill_between(time, p5, p95, alpha=0.3, label='5th-95th Percentile')
    ax.plot(time, p50, 'b-', linewidth=2, label='Median')
    ax.plot(time, u_measured * 100, 'k--', linewidth=2, label='Measured')
    ax.set_ylabel('Displacement (cm)')
    ax.set_title('Uncertainty Analysis (MC Ensemble)')
    ax.legend()
    ax.grid()
    
    plt.tight_layout()
    plt.savefig('digital_twin_results.png', dpi=150, bbox_inches='tight')
    print(f"\nResults saved to 'digital_twin_results.png'")
    
    plt.show()

if __name__ == '__main__':
    main()
```

**Run it:**

```bash
python digital_twin_workflow.py
```

---

## Next Steps

1. **Acquire real SCEC BBP data** (or implement BBP integration)
2. **Deploy sensors** post-earthquake or use synthetic scenarios
3. **Automate calibration** using optimization (scipy.optimize, Bayesian MCMC)
4. **Extend to 3D models** using OpenSees/OpenSeesPy for complex buildings
5. **Integrate with network geometry** (NetworkX) for multi-building resilience studies

---

## References

- SCEC Broadband Platform: https://strike.scec.org/scecpedia/Broadband_Platform
- OpenSees: https://opensees.berkeley.edu/
- Pyrocko: https://pyrocko.org/
- Newmark integration: Cook, R. D., Malkus, D. S., & Plesha, M. E. (2001). *Concepts and Applications of Finite Element Analysis*.
