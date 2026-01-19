# Task 07: Numba JIT Compilation

## Priority: HIGH
## Estimated Effort: 3-4 days

## Problem Statement

The current implementation:
- Uses pure Python/NumPy for time integration
- Is slow for long time histories or many DOFs
- Cannot efficiently run large Monte Carlo ensembles
- Time integration is a major computational bottleneck

## Implementation Plan

### 1. Create fast integration module
Create `src/seismic_twin/analysis/integration_fast.py`

### 2. Implement Numba-optimized Newmark-beta

```python
import numpy as np
from numba import jit, prange
from typing import Tuple

@jit(nopython=True, cache=True)
def _newmark_beta_core(
    M: np.ndarray,
    C: np.ndarray,
    K: np.ndarray,
    F: np.ndarray,
    dt: float,
    gamma: float,
    beta: float,
    u0: np.ndarray,
    v0: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Core Newmark-beta integration loop (Numba JIT).

    Parameters:
    -----------
    M, C, K : (n_dof, n_dof) arrays
        Mass, damping, stiffness matrices
    F : (n_steps, n_dof) array
        External force history
    dt : float
        Time step
    gamma, beta : float
        Newmark parameters (0.5, 0.25 for average acceleration)
    u0, v0 : (n_dof,) arrays
        Initial conditions

    Returns:
    --------
    u, v, a : (n_steps, n_dof) arrays
        Displacement, velocity, acceleration history
    """
    n_dof = M.shape[0]
    n_steps = F.shape[0]

    # Preallocate output arrays
    u = np.zeros((n_steps, n_dof))
    v = np.zeros((n_steps, n_dof))
    a = np.zeros((n_steps, n_dof))

    # Initial conditions
    u[0] = u0
    v[0] = v0

    # Initial acceleration: M*a0 = F0 - C*v0 - K*u0
    rhs = F[0] - C @ v0 - K @ u0
    a[0] = np.linalg.solve(M, rhs)

    # Effective stiffness matrix
    c0 = 1.0 / (beta * dt * dt)
    c1 = gamma / (beta * dt)
    c2 = 1.0 / (beta * dt)
    c3 = 1.0 / (2.0 * beta) - 1.0
    c4 = gamma / beta - 1.0
    c5 = dt * (gamma / (2.0 * beta) - 1.0)

    K_eff = K + c0 * M + c1 * C

    # LU decomposition for efficiency (done once)
    # Note: In Numba, we use solve directly

    # Time stepping
    for i in range(1, n_steps):
        # Effective force
        F_eff = F[i] + M @ (c0 * u[i-1] + c2 * v[i-1] + c3 * a[i-1]) \
                     + C @ (c1 * u[i-1] + c4 * v[i-1] + c5 * a[i-1])

        # Solve for displacement
        u[i] = np.linalg.solve(K_eff, F_eff)

        # Update velocity and acceleration
        a[i] = c0 * (u[i] - u[i-1]) - c2 * v[i-1] - c3 * a[i-1]
        v[i] = v[i-1] + dt * ((1.0 - gamma) * a[i-1] + gamma * a[i])

    return u, v, a
```

### 3. Create wrapper function

```python
def newmark_beta_fast(
    M: np.ndarray,
    C: np.ndarray,
    K: np.ndarray,
    ground_acceleration: np.ndarray,
    dt: float,
    gamma: float = 0.5,
    beta: float = 0.25,
    u0: np.ndarray = None,
    v0: np.ndarray = None,
) -> 'IntegrationResult':
    """
    Fast Newmark-beta integration using Numba.

    ~50-100x faster than pure Python for large arrays.

    Parameters:
    -----------
    M, C, K : (n_dof, n_dof) arrays
        System matrices
    ground_acceleration : (n_steps,) array
        Ground acceleration [m/s²]
    dt : float
        Time step [s]
    gamma, beta : float
        Newmark parameters
    u0, v0 : (n_dof,) arrays, optional
        Initial displacement and velocity

    Returns:
    --------
    IntegrationResult dataclass
    """
    from seismic_twin.analysis.integration import IntegrationResult

    n_dof = M.shape[0]
    n_steps = len(ground_acceleration)

    # Convert to contiguous arrays for Numba
    M = np.ascontiguousarray(M, dtype=np.float64)
    C = np.ascontiguousarray(C, dtype=np.float64)
    K = np.ascontiguousarray(K, dtype=np.float64)

    # Build force vector: F = -M @ ones * ground_acc
    influence = np.ones(n_dof)
    F = -np.outer(ground_acceleration, M @ influence)
    F = np.ascontiguousarray(F, dtype=np.float64)

    # Initial conditions
    if u0 is None:
        u0 = np.zeros(n_dof, dtype=np.float64)
    if v0 is None:
        v0 = np.zeros(n_dof, dtype=np.float64)

    # Run JIT-compiled integration
    u, v, a = _newmark_beta_core(M, C, K, F, dt, gamma, beta, u0, v0)

    # Compute absolute acceleration
    abs_acc = a + ground_acceleration[:, np.newaxis]

    # Build time vector
    time = np.arange(n_steps) * dt

    return IntegrationResult(
        displacement=u,
        velocity=v,
        acceleration=a,
        absolute_acceleration=abs_acc,
        time=time,
    )
```

### 4. Add parallel batch processing

```python
@jit(nopython=True, parallel=True, cache=True)
def _batch_newmark_core(
    M: np.ndarray,
    C_batch: np.ndarray,  # (n_batch, n_dof, n_dof)
    K_batch: np.ndarray,  # (n_batch, n_dof, n_dof)
    F: np.ndarray,
    dt: float,
    gamma: float,
    beta: float,
) -> np.ndarray:
    """
    Batch Newmark-beta for Monte Carlo (parallel over samples).

    Returns (n_batch, n_steps, n_dof) displacement array.
    """
    n_batch = C_batch.shape[0]
    n_steps = F.shape[0]
    n_dof = M.shape[0]

    u_batch = np.zeros((n_batch, n_steps, n_dof))

    for b in prange(n_batch):
        u, _, _ = _newmark_beta_core(
            M, C_batch[b], K_batch[b], F, dt, gamma, beta,
            np.zeros(n_dof), np.zeros(n_dof)
        )
        u_batch[b] = u

    return u_batch

def run_batch_integration(
    model: 'StructuralModel',
    ground_acceleration: np.ndarray,
    dt: float,
    stiffness_factors: np.ndarray,
    damping_ratios: np.ndarray,
) -> np.ndarray:
    """
    Run batch of integrations with varying parameters.

    Efficient for Monte Carlo analysis.
    """
    n_batch = len(stiffness_factors)
    n_dof = model.get_n_dof()

    # Build batch of C, K matrices
    C_batch = np.zeros((n_batch, n_dof, n_dof))
    K_batch = np.zeros((n_batch, n_dof, n_dof))

    base_K = model.get_stiffness_matrix()
    M = model.get_mass_matrix()

    for i in range(n_batch):
        K_batch[i] = base_K * stiffness_factors[i]
        # Rayleigh damping
        omega = np.sqrt(np.linalg.eigvalsh(K_batch[i], M)[0])
        alpha = 2 * damping_ratios[i] * omega
        C_batch[i] = alpha * M

    # Build force
    F = -np.outer(ground_acceleration, M @ np.ones(n_dof))
    F = np.ascontiguousarray(F)

    return _batch_newmark_core(M, C_batch, K_batch, F, dt, 0.5, 0.25)
```

### 5. Add automatic fallback

```python
# At module level
try:
    from numba import jit, prange
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

    # Define no-op decorator
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    prange = range

def newmark_beta_auto(
    M, C, K, ground_acceleration, dt, **kwargs
) -> 'IntegrationResult':
    """
    Automatically use fast version if Numba available.
    """
    if HAS_NUMBA:
        return newmark_beta_fast(M, C, K, ground_acceleration, dt, **kwargs)
    else:
        from seismic_twin.analysis.integration import newmark_beta
        return newmark_beta(M, C, K, ground_acceleration, dt, **kwargs)
```

### 6. Add benchmarking utility

```python
def benchmark_integration(
    n_dof: int = 10,
    n_steps: int = 10000,
    n_runs: int = 5,
) -> Dict[str, float]:
    """
    Benchmark integration implementations.

    Returns dict with timing results.
    """
    import time

    # Create test system
    M = np.eye(n_dof)
    K = np.diag([100.0] * n_dof)
    C = 0.05 * M
    acc = np.random.randn(n_steps) * 0.1

    results = {}

    # Benchmark pure Python
    from seismic_twin.analysis.integration import newmark_beta
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        newmark_beta(M, C, K, acc, 0.01)
        times.append(time.perf_counter() - t0)
    results['python'] = np.mean(times)

    # Benchmark Numba (includes compilation on first run)
    if HAS_NUMBA:
        # Warm up
        newmark_beta_fast(M, C, K, acc, 0.01)

        times = []
        for _ in range(n_runs):
            t0 = time.perf_counter()
            newmark_beta_fast(M, C, K, acc, 0.01)
            times.append(time.perf_counter() - t0)
        results['numba'] = np.mean(times)
        results['speedup'] = results['python'] / results['numba']

    return results
```

### 7. Add tests

- Test numerical accuracy vs pure Python
- Test batch processing correctness
- Test parallel execution
- Verify speedup is achieved

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/analysis/integration_fast.py` | Create |
| `src/seismic_twin/analysis/__init__.py` | Modify (export fast functions) |
| `tests/test_integration_fast.py` | Create |
| `pyproject.toml` | Add numba dependency |

## Dependencies

- `numba>=0.57` (optional but recommended)

## Success Criteria

- [ ] JIT-compiled Newmark-beta implemented
- [ ] Results match pure Python to machine precision
- [ ] 50-100x speedup achieved for typical cases
- [ ] Batch processing works correctly
- [ ] Graceful fallback when Numba unavailable
- [ ] Benchmark utility confirms performance
- [ ] All tests pass

## Performance Targets

| Scenario | Pure Python | With Numba |
|----------|-------------|------------|
| 10 DOF, 10k steps | ~2.0 s | ~0.02 s |
| 100 DOF, 10k steps | ~20 s | ~0.5 s |
| MC 100 samples | ~200 s | ~5 s |
