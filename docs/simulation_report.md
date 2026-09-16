# Seismic Building Simulation: Comprehensive Technical Report

This report explains each step of the seismic digital twin simulation pipeline, including the mathematical foundations, algorithms, and code implementations.

---

## Table of Contents

1. [Pipeline Overview](#1-pipeline-overview)
2. [Step 1: Building Model Creation](#2-step-1-building-model-creation)
3. [Step 2: Ground Motion Generation](#3-step-2-ground-motion-generation)
4. [Step 3: Time History Analysis (Newmark-Beta)](#4-step-3-time-history-analysis)
5. [Step 4: Engineering Demand Parameters](#5-step-4-engineering-demand-parameters)
6. [Step 5: Sensor-Based Calibration](#6-step-5-sensor-based-calibration)
7. [Step 6: Uncertainty Quantification](#7-step-6-uncertainty-quantification)
8. [Complete Workflow Example](#8-complete-workflow-example)

---

## 1. Pipeline Overview

The simulation follows this data flow:

```
Ground Motion → Building Model → Time Integration → Demand Metrics
                                      ↓
                            [Optional] Calibration
                                      ↓
                        [Optional] Uncertainty Analysis
```

---

## 2. Step 1: Building Model Creation

**Location:** `src/seismic_twin/building/mdof_model.py`

### Concept

The building is modeled as a **Multi-Degree-of-Freedom (MDOF) shear building** where:
- Each floor is a lumped mass
- Floors are connected by inter-story stiffness (spring) elements
- Each floor has one horizontal degree of freedom

### Mass Matrix Assembly

The mass matrix is diagonal, with floor masses on the diagonal:

```python
def _assemble_mass_matrix(self) -> NDArray[np.floating]:
    """Assemble the diagonal mass matrix."""
    return np.diag(self.masses)
```

**Mathematical form:**
```
M = diag(m₁, m₂, ..., mₙ)
```

### Stiffness Matrix Assembly

The stiffness matrix has a **tridiagonal structure** characteristic of shear buildings:

```python
def _assemble_stiffness_matrix(self) -> NDArray[np.floating]:
    K = np.zeros((self.n_dof, self.n_dof), dtype=np.float64)

    for i in range(self.n_dof):
        # Diagonal term: sum of stiffnesses connecting to this floor
        K[i, i] = self.stiffnesses[i]
        if i < self.n_dof - 1:
            K[i, i] += self.stiffnesses[i + 1]

        # Off-diagonal terms
        if i < self.n_dof - 1:
            K[i, i + 1] = -self.stiffnesses[i + 1]
            K[i + 1, i] = -self.stiffnesses[i + 1]

    return K
```

**Mathematical form for a 3-story building:**
```
K = | k₁+k₂   -k₂      0   |
    | -k₂    k₂+k₃   -k₃   |
    |  0      -k₃     k₃   |
```

### Modal Analysis

Natural frequencies and mode shapes are computed via the **generalized eigenvalue problem**:

```python
def _compute_modal_properties(self) -> None:
    # Solve: K*φ = ω²*M*φ
    eigenvalues, eigenvectors = linalg.eigh(self.K, self.M)

    eigenvalues = np.maximum(eigenvalues, 0.0)
    self.natural_frequencies = np.sqrt(eigenvalues)  # rad/s
    self.natural_periods = 2.0 * np.pi / self.natural_frequencies  # seconds
    self.mode_shapes = eigenvectors
```

### Rayleigh Damping

Damping is modeled using **Rayleigh damping**, which provides proportional damping:

```
C = α·M + β·K
```

The coefficients α and β are computed to achieve the target damping ratio ξ at two control frequencies (first and last modes):

```python
def _assemble_damping_matrix(self) -> NDArray[np.floating]:
    omega_1 = self.natural_frequencies[0]
    omega_n = self.natural_frequencies[-1]

    # Solve system:
    # ξ = α/(2ω) + β·ω/2
    A = np.array([
        [1.0 / (2.0 * omega_1), omega_1 / 2.0],
        [1.0 / (2.0 * omega_n), omega_n / 2.0],
    ])
    b = np.array([self.damping_ratio, self.damping_ratio])
    alpha, beta = np.linalg.solve(A, b)

    return alpha * self.M + beta * self.K
```

---

## 3. Step 2: Ground Motion Generation

**Location:** `src/seismic_twin/ground_motion/synthetic.py`

### Algorithm

Synthetic earthquake ground motion is generated using **modulated filtered noise**:

1. **Generate white noise**
2. **Apply bandpass filter** around predominant frequency
3. **Apply Saragoni-Hart envelope** for realistic amplitude variation
4. **Scale to target PGA**

```python
def generate_synthetic_ground_motion(
    duration: float = 30.0,
    dt: float = 0.01,
    target_pga: float = 0.3,
    predominant_freq: float = 2.0,
    bandwidth: float = 1.5,
    seed: int | None = None,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
```

### Bandpass Filter

A 4th-order Butterworth bandpass filter isolates the desired frequency range:

```python
# Design bandpass filter around predominant frequency
nyquist = 0.5 / dt
low_freq = max(0.1, predominant_freq - bandwidth)
high_freq = min(nyquist - 0.1, predominant_freq + bandwidth)

low_norm = low_freq / nyquist
high_norm = high_freq / nyquist

b, a = signal.butter(4, [low_norm, high_norm], btype="band")
filtered_noise = signal.filtfilt(b, a, noise)
```

### Saragoni-Hart Envelope

The envelope function simulates the build-up and decay of earthquake intensity:

```
e(t) = a · t^b · exp(-c·t)
```

```python
# Parameters: maximum at t_max = duration * 0.3
t_max = duration * 0.3
b_env = 2.0
c_env = b_env / t_max

envelope = (time ** b_env) * np.exp(-c_env * time)
envelope = envelope / np.max(envelope)  # Normalize

acceleration = filtered_noise * envelope
```

### Response Spectrum Calculation

The pseudo-acceleration response spectrum is computed using the **Duhamel integral** for SDOF oscillators at various periods:

```python
def compute_response_spectrum(time, acceleration, periods, damping_ratio=0.05):
    for i, T in enumerate(periods):
        omega = 2 * np.pi / T
        omega_d = omega * np.sqrt(1 - damping_ratio**2)

        # State-space integration
        exp_factor = np.exp(-damping_ratio * omega * dt)
        A = exp_factor * (cos_factor + xi/sqrt(1-xi²) * sin_factor)
        B = exp_factor * sin_factor / omega_d

        for j in range(1, len(time)):
            u[j] = A * u[j-1] + B * v[j-1] - dt * acc[j-1] / omega²
            v[j] = -omega² * B * u[j-1] + A * v[j-1]

        Sa[i] = np.max(np.abs(u)) * omega² / 9.81
```

---

## 4. Step 3: Time History Analysis

**Location:** `src/seismic_twin/analysis/integration.py`

### Equation of Motion

The MDOF system under ground excitation follows:

```
M·ü + C·u̇ + K·u = -M·r·aₓ(t)
```

Where:
- **M, C, K** = mass, damping, stiffness matrices
- **u** = relative displacement vector
- **r** = influence vector (typically ones)
- **aₓ(t)** = ground acceleration

### Newmark-Beta Method

The **implicit Newmark-beta method** (β=0.25, γ=0.5) is **unconditionally stable**:

```python
def newmark_beta(M, C, K, ground_acceleration, dt, beta=0.25, gamma=0.5):
    # Convert ground acceleration to m/s²
    ag_mps2 = ground_acceleration * 9.81

    # Newmark integration constants
    a1 = 1.0 / (beta * dt**2)
    a2 = 1.0 / (beta * dt)
    a3 = 1.0 / (2.0 * beta) - 1.0
    a4 = gamma / (beta * dt)
    a5 = gamma / beta - 1.0
    a6 = dt * (gamma / (2.0 * beta) - 1.0)

    # Effective stiffness matrix
    K_eff = K + a1 * M + a4 * C

    # LU factorization for efficiency
    K_eff_lu = linalg.lu_factor(K_eff)
```

### Time Stepping Loop

```python
for i in range(n_steps - 1):
    # Effective load at t_{i+1}
    p_eff = -M @ influence_vector * ag_mps2[i + 1]

    # Add contributions from current state
    p_eff += M @ (a1 * u[:, i] + a2 * v[:, i] + a3 * a[:, i])
    p_eff += C @ (a4 * u[:, i] + a5 * v[:, i] + a6 * a[:, i])

    # Solve for displacement at t_{i+1}
    u[:, i + 1] = linalg.lu_solve(K_eff_lu, p_eff)

    # Update velocity and acceleration
    a[:, i + 1] = a1 * (u[:, i+1] - u[:, i]) - a2 * v[:, i] - a3 * a[:, i]
    v[:, i + 1] = v[:, i] + dt * ((1-gamma) * a[:, i] + gamma * a[:, i+1])
```

**Key efficiency:** LU factorization is performed once and reused for all time steps.

### Absolute Acceleration

The absolute (total) acceleration is computed as:

```python
abs_acc = a + np.outer(influence_vector, ag_mps2)
```

---

## 5. Step 4: Engineering Demand Parameters

**Location:** `src/seismic_twin/analysis/metrics.py`

### Inter-Story Drift Ratio

The critical parameter for structural damage assessment:

```
IDR_i = (u_i - u_{i-1}) / h_i
```

```python
def compute_demand_metrics(displacement, velocity, absolute_acceleration,
                           ground_acceleration, story_heights):
    # Inter-story drift ratio
    inter_story_drift = np.zeros((n_dof, n_steps))
    inter_story_drift[0, :] = displacement[0, :] / story_heights[0]

    for i in range(1, n_dof):
        inter_story_drift[i, :] = (
            (displacement[i, :] - displacement[i-1, :]) / story_heights[i]
        )

    inter_story_drift_ratio = np.max(np.abs(inter_story_drift), axis=1)
```

### Energy Balance

Verifies simulation accuracy through energy conservation:

```python
def compute_energy_balance(M, C, K, displacement, velocity, ground_acceleration, dt):
    # Kinetic energy: 0.5 * v^T * M * v
    kinetic = [0.5 * velocity[:, i] @ M @ velocity[:, i] for i in range(n_steps)]

    # Strain energy: 0.5 * u^T * K * u
    strain = [0.5 * displacement[:, i] @ K @ displacement[:, i] for i in range(n_steps)]

    # Damping energy (cumulative)
    damping_power = [velocity[:, i] @ C @ velocity[:, i] for i in range(n_steps)]
    damping = np.cumsum(damping_power) * dt

    # Input energy (cumulative)
    input_power = [-velocity[:, i] @ M @ influence * ag[i] for i in range(n_steps)]
    input_energy = np.cumsum(input_power) * dt
```

### NRMSE and Correlation

For comparing predicted vs. measured responses:

```python
def compute_nrmse(prediction, measurement):
    rmse = np.sqrt(np.mean((prediction - measurement) ** 2))
    range_meas = np.max(measurement) - np.min(measurement)
    return rmse / range_meas

def compute_correlation(prediction, measurement):
    pred_centered = prediction - np.mean(prediction)
    meas_centered = measurement - np.mean(measurement)
    return np.sum(pred_centered * meas_centered) / (
        np.sqrt(np.sum(pred_centered**2) * np.sum(meas_centered**2))
    )
```

---

## 6. Step 5: Sensor-Based Calibration

**Location:** `src/seismic_twin/calibration/calibrator.py`

### Purpose

Updates model parameters (stiffness, damping) to match measured sensor data.

### Grid Search Algorithm

```python
def calibrate(self, max_iterations=10, tolerance=0.01,
              stiffness_bounds=(0.5, 2.0), damping_bounds=(0.01, 0.10)):

    best_nrmse = float('inf')

    # Grid search: 5 stiffness values × 3 damping values
    stiffness_grid = np.linspace(stiffness_bounds[0], stiffness_bounds[1], 5)
    damping_grid = np.linspace(damping_bounds[0], damping_bounds[1], 3)

    for k_factor in stiffness_grid:
        for xi in damping_grid:
            # Reset to initial model
            self.model = self.initial_model.copy()

            # Apply parameters and run simulation
            result = self.run_iteration(
                stiffness_adjustment=k_factor,
                damping_adjustment=xi,
            )

            if result.nrmse < best_nrmse:
                best_nrmse = result.nrmse
                best_result = result

            if result.nrmse < tolerance:
                return result

    return best_result
```

### Residual Computation

```python
def compute_residuals(self):
    # Run simulation with current model
    result = newmark_beta(M=self.model.M, C=self.model.C, K=self.model.K,
                          ground_acceleration=self.ground_acceleration, dt=self.dt)

    # Extract prediction at sensor locations
    prediction = result.displacement[self.sensor_floors, :]

    # Compute metrics (average over all sensors)
    nrmse_values = []
    for i in range(len(self.sensor_floors)):
        nrmse_values.append(compute_nrmse(prediction[i], self.measured_displacement[i]))

    return np.mean(nrmse_values), np.mean(corr_values), prediction
```

### Simple Iterative Calibration

An alternative approach using **cross-correlation for frequency matching**:

```python
def run_simple_calibration(self, n_iterations=5):
    for _ in range(n_iterations - 1):
        pred = result.prediction[0, :]
        meas = self.measured_displacement[0, :]

        # Cross-correlation to find phase shift
        correlation = np.correlate(pred, meas, mode="full")
        lag = np.argmax(correlation) - len(pred) + 1

        # Positive lag → prediction delayed → increase stiffness
        if abs(lag) > 1:
            freq_ratio = 1.0 + learning_rate * np.sign(lag)

        # Amplitude ratio → adjust damping
        amp_ratio = np.max(np.abs(meas)) / np.max(np.abs(pred))
        if amp_ratio < 0.95:  # prediction too large
            damping_adj *= 1.0 + damping_learning_rate
```

---

## 7. Step 6: Uncertainty Quantification

**Location:** `src/seismic_twin/uncertainty/monte_carlo.py`

### Monte Carlo Framework

Propagates parameter uncertainties through structural response predictions.

### Lognormal Sampling

Parameters are sampled from **lognormal distributions** to ensure positive values:

```python
def sample_parameters(self, n_samples, stiffness_cov=0.05, damping_cov=0.20):
    # Lognormal: X = exp(N(μ, σ²))
    # For target mean=1 and COV: σ² = ln(1 + COV²), μ = -σ²/2

    if stiffness_cov > 0:
        sigma_k = np.sqrt(np.log(1 + stiffness_cov**2))
        mu_k = -0.5 * sigma_k**2
        stiffness_factors = np.exp(np.random.normal(mu_k, sigma_k, (n_samples, n_dof)))

    if damping_cov > 0:
        sigma_xi = np.sqrt(np.log(1 + damping_cov**2))
        mu_xi = np.log(self.base_model.damping_ratio) - 0.5 * sigma_xi**2
        damping_ratios = np.exp(np.random.normal(mu_xi, sigma_xi, n_samples))
```

### Monte Carlo Ensemble

```python
def run_mc_ensemble(self, n_samples=100, stiffness_cov=0.05, damping_cov=0.20):
    params = self.sample_parameters(n_samples, stiffness_cov, damping_cov)

    all_displacements = np.zeros((n_samples, n_dof, n_steps))
    max_drifts = np.zeros(n_samples)

    for i in range(n_samples):
        # Create model with sampled parameters
        model = self._create_sampled_model(
            stiffness_factors=params["stiffness_factors"][i],
            damping_ratio=params["damping_ratios"][i],
            mass_factors=params["mass_factors"][i],
        )

        # Run simulation
        result = newmark_beta(M=model.M, C=model.C, K=model.K,
                              ground_acceleration=self.ground_acceleration, dt=self.dt)

        all_displacements[i] = result.displacement

        # Compute max drift for this sample
        metrics = compute_demand_metrics(...)
        max_drifts[i] = np.max(metrics.inter_story_drift_ratio)

    # Extract percentile bounds
    displacement_bounds = self._compute_bounds(all_displacements)
```

### Percentile Extraction

```python
def _compute_bounds(self, data):
    # data shape: (n_samples, n_dof, n_steps)
    return UncertaintyBounds(
        percentile_5=np.percentile(data, 5, axis=0),
        percentile_50=np.percentile(data, 50, axis=0),
        percentile_95=np.percentile(data, 95, axis=0),
        mean=np.mean(data, axis=0),
        std=np.std(data, axis=0),
    )
```

### Probability of Exceedance

```python
def get_probability_of_exceedance(self, threshold, response_type="drift"):
    if response_type == "drift":
        values = self.results.max_drift_distribution

    return float(np.mean(values > threshold))  # Fraction exceeding threshold
```

---

## 8. Complete Workflow Example

From `examples/run_workflow.py`:

```python
# Phase 1: Ground Motion
time, ground_acceleration = generate_synthetic_ground_motion(
    duration=30.0, dt=0.01, target_pga=0.35, predominant_freq=2.5, seed=42
)

# Phase 2: Building Model
building = MDOFShearBuilding(
    masses=np.full(4, 100_000.0),       # 100 tonnes per floor
    stiffnesses=np.full(4, 50_000_000), # 50 MN/m per story
    damping_ratio=0.05,
    story_heights=np.full(4, 3.5),
)

# Phase 3: Time History Analysis
result = newmark_beta(M=building.M, C=building.C, K=building.K,
                      ground_acceleration=ground_acceleration, dt=0.01)

metrics = compute_demand_metrics(
    displacement=result.displacement,
    velocity=result.velocity,
    absolute_acceleration=result.absolute_acceleration,
    ground_acceleration=ground_acceleration,
    story_heights=building.story_heights,
)

# Phase 4: Calibration
calibration = StructuralCalibration(
    model=building, ground_acceleration=ground_acceleration, dt=0.01,
    measured_displacement=measured_data, sensor_floors=np.arange(4)
)
best = calibration.calibrate(stiffness_bounds=(0.7, 1.3), damping_bounds=(0.02, 0.08))

# Phase 5: Uncertainty Analysis
uncertainty = UncertaintyAnalysis(
    model=calibration.get_calibrated_model(),
    ground_acceleration=ground_acceleration, dt=0.01
)
mc_result = uncertainty.run_mc_ensemble(n_samples=100, stiffness_cov=0.05, damping_cov=0.20)
```

---

## Summary Table

| Step | Module | Key Algorithm | Primary Output |
|------|--------|---------------|----------------|
| Building Model | `building/mdof_model.py` | Eigenvalue analysis, Rayleigh damping | M, C, K matrices, modal properties |
| Ground Motion | `ground_motion/synthetic.py` | Bandpass filter + Saragoni-Hart envelope | Acceleration time history |
| Time Integration | `analysis/integration.py` | Newmark-beta (implicit) | Displacement, velocity, acceleration |
| Demand Metrics | `analysis/metrics.py` | Inter-story drift, energy balance | DemandMetrics dataclass |
| Calibration | `calibration/calibrator.py` | Grid search optimization | Calibrated model parameters |
| Uncertainty | `uncertainty/monte_carlo.py` | Lognormal sampling, percentile extraction | 5th/50th/95th percentile bounds |

---

This simulation pipeline provides a complete digital twin framework for seismic building analysis, from generating earthquake loads through uncertainty-quantified response predictions.
