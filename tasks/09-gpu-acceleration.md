# Task 09: GPU Acceleration (Optional)

## Priority: MEDIUM
## Estimated Effort: 3-5 days

## Problem Statement

For very large structural systems (n_dof > 1000) or massive MC ensembles:
- Even Numba-optimized code may be slow
- CPU parallelism has limits
- GPU can provide 10-50x additional speedup
- High-fidelity models require more compute

## Implementation Plan

### 1. Create GPU integration module
Create `src/seismic_twin/analysis/integration_gpu.py`

### 2. Implement GPU availability check

```python
import numpy as np
from typing import Tuple, Optional

# Check for GPU support
HAS_GPU = False
GPU_BACKEND = None

try:
    import cupy as cp
    HAS_GPU = True
    GPU_BACKEND = "cupy"
except ImportError:
    pass

if not HAS_GPU:
    try:
        import torch
        if torch.cuda.is_available():
            HAS_GPU = True
            GPU_BACKEND = "torch"
    except ImportError:
        pass

def get_gpu_info() -> dict:
    """Get GPU availability and info."""
    info = {
        'available': HAS_GPU,
        'backend': GPU_BACKEND,
        'device_name': None,
        'memory_gb': None,
    }

    if GPU_BACKEND == "cupy":
        import cupy as cp
        device = cp.cuda.Device()
        info['device_name'] = device.name
        info['memory_gb'] = device.mem_info[1] / 1e9
    elif GPU_BACKEND == "torch":
        import torch
        info['device_name'] = torch.cuda.get_device_name(0)
        info['memory_gb'] = torch.cuda.get_device_properties(0).total_memory / 1e9

    return info
```

### 3. Implement CuPy-based Newmark-beta

```python
def newmark_beta_gpu_cupy(
    M: np.ndarray,
    C: np.ndarray,
    K: np.ndarray,
    ground_acceleration: np.ndarray,
    dt: float,
    gamma: float = 0.5,
    beta: float = 0.25,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Newmark-beta on GPU using CuPy.

    Best for large systems (n_dof > 500).

    Returns:
        u, v, a as numpy arrays (transferred back to CPU)
    """
    import cupy as cp

    # Transfer to GPU
    M_gpu = cp.asarray(M)
    C_gpu = cp.asarray(C)
    K_gpu = cp.asarray(K)
    acc_gpu = cp.asarray(ground_acceleration)

    n_dof = M_gpu.shape[0]
    n_steps = len(acc_gpu)

    # Preallocate on GPU
    u = cp.zeros((n_steps, n_dof))
    v = cp.zeros((n_steps, n_dof))
    a = cp.zeros((n_steps, n_dof))

    # Newmark coefficients
    c0 = 1.0 / (beta * dt * dt)
    c1 = gamma / (beta * dt)
    c2 = 1.0 / (beta * dt)
    c3 = 1.0 / (2.0 * beta) - 1.0
    c4 = gamma / beta - 1.0
    c5 = dt * (gamma / (2.0 * beta) - 1.0)

    # Effective stiffness
    K_eff = K_gpu + c0 * M_gpu + c1 * C_gpu

    # LU factorization (done once on GPU)
    K_eff_lu = cp.linalg.lu_factor(K_eff)

    # Force vector influence
    influence = cp.ones(n_dof)

    # Initial acceleration
    F0 = -M_gpu @ influence * acc_gpu[0]
    a[0] = cp.linalg.solve(M_gpu, F0)

    # Time stepping (GPU kernel)
    for i in range(1, n_steps):
        # Effective force
        F_eff = -M_gpu @ influence * acc_gpu[i] \
              + M_gpu @ (c0 * u[i-1] + c2 * v[i-1] + c3 * a[i-1]) \
              + C_gpu @ (c1 * u[i-1] + c4 * v[i-1] + c5 * a[i-1])

        # Solve using LU
        u[i] = cp.linalg.lu_solve(K_eff_lu, F_eff)

        # Update
        a[i] = c0 * (u[i] - u[i-1]) - c2 * v[i-1] - c3 * a[i-1]
        v[i] = v[i-1] + dt * ((1.0 - gamma) * a[i-1] + gamma * a[i])

    # Transfer back to CPU
    return cp.asnumpy(u), cp.asnumpy(v), cp.asnumpy(a)
```

### 4. Implement batched GPU Monte Carlo

```python
def batch_mc_gpu(
    M: np.ndarray,
    K_base: np.ndarray,
    ground_acceleration: np.ndarray,
    dt: float,
    stiffness_factors: np.ndarray,
    damping_ratios: np.ndarray,
) -> np.ndarray:
    """
    Batched Monte Carlo on GPU.

    Runs all samples in parallel on GPU.

    Parameters:
    -----------
    M : (n_dof, n_dof) array
        Mass matrix (same for all samples)
    K_base : (n_dof, n_dof) array
        Base stiffness matrix
    ground_acceleration : (n_steps,) array
        Ground motion
    stiffness_factors : (n_batch,) array
        Stiffness scaling factors
    damping_ratios : (n_batch,) array
        Damping ratios

    Returns:
    --------
    (n_batch, n_steps, n_dof) displacement array
    """
    import cupy as cp

    n_batch = len(stiffness_factors)
    n_dof = M.shape[0]
    n_steps = len(ground_acceleration)

    # Transfer to GPU
    M_gpu = cp.asarray(M)
    K_base_gpu = cp.asarray(K_base)
    acc_gpu = cp.asarray(ground_acceleration)
    sf_gpu = cp.asarray(stiffness_factors)
    dr_gpu = cp.asarray(damping_ratios)

    # Build batch of K and C matrices on GPU
    K_batch = cp.einsum('ij,b->bij', K_base_gpu, sf_gpu)

    # Rayleigh damping (simplified)
    # C = alpha * M, where alpha = 2 * damping * omega1
    omega1 = cp.sqrt(cp.linalg.eigvalsh(K_base_gpu, M_gpu)[0])
    alpha = 2 * dr_gpu * omega1
    C_batch = cp.einsum('ij,b->bij', M_gpu, alpha)

    # Preallocate output
    u_batch = cp.zeros((n_batch, n_steps, n_dof))

    # Run batched integration
    # (Custom CUDA kernel would be even faster)
    for b in range(n_batch):
        u_batch[b], _, _ = _newmark_single_gpu(
            M_gpu, C_batch[b], K_batch[b], acc_gpu, dt
        )

    return cp.asnumpy(u_batch)
```

### 5. Add unified interface

```python
def newmark_beta_auto(
    M: np.ndarray,
    C: np.ndarray,
    K: np.ndarray,
    ground_acceleration: np.ndarray,
    dt: float,
    backend: str = "auto",
    **kwargs
) -> 'IntegrationResult':
    """
    Automatically select best backend for integration.

    Parameters:
    -----------
    backend : str
        "auto", "cpu", "numba", "gpu"

    Selection logic:
    - n_dof < 50: Use Numba (GPU overhead not worth it)
    - n_dof >= 50 and GPU available: Use GPU
    - Otherwise: Use Numba if available, else pure Python
    """
    n_dof = M.shape[0]

    if backend == "auto":
        if n_dof >= 50 and HAS_GPU:
            backend = "gpu"
        else:
            try:
                import numba
                backend = "numba"
            except ImportError:
                backend = "cpu"

    if backend == "gpu":
        if not HAS_GPU:
            raise RuntimeError("GPU not available")
        if GPU_BACKEND == "cupy":
            u, v, a = newmark_beta_gpu_cupy(M, C, K, ground_acceleration, dt)
        else:
            raise RuntimeError(f"Unknown GPU backend: {GPU_BACKEND}")
    elif backend == "numba":
        from seismic_twin.analysis.integration_fast import newmark_beta_fast
        return newmark_beta_fast(M, C, K, ground_acceleration, dt, **kwargs)
    else:
        from seismic_twin.analysis.integration import newmark_beta
        return newmark_beta(M, C, K, ground_acceleration, dt, **kwargs)

    # Build result
    from seismic_twin.analysis.integration import IntegrationResult
    time = np.arange(len(ground_acceleration)) * dt
    abs_acc = a + ground_acceleration[:, np.newaxis]

    return IntegrationResult(
        displacement=u, velocity=v, acceleration=a,
        absolute_acceleration=abs_acc, time=time
    )
```

### 6. Add memory management

```python
class GPUMemoryManager:
    """Context manager for GPU memory."""

    def __init__(self, fraction: float = 0.8):
        """Reserve fraction of GPU memory."""
        self.fraction = fraction

    def __enter__(self):
        if GPU_BACKEND == "cupy":
            import cupy as cp
            mempool = cp.get_default_memory_pool()
            mempool.set_limit(fraction=self.fraction)
        return self

    def __exit__(self, *args):
        if GPU_BACKEND == "cupy":
            import cupy as cp
            cp.get_default_memory_pool().free_all_blocks()

def clear_gpu_memory():
    """Free all GPU memory."""
    if GPU_BACKEND == "cupy":
        import cupy as cp
        cp.get_default_memory_pool().free_all_blocks()
        cp.get_default_pinned_memory_pool().free_all_blocks()
```

### 7. Add tests

- Test GPU results match CPU
- Test memory cleanup
- Test backend selection logic
- Test batch MC correctness
- Benchmark GPU vs CPU speedup

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/analysis/integration_gpu.py` | Create |
| `src/seismic_twin/analysis/__init__.py` | Modify |
| `tests/test_integration_gpu.py` | Create |
| `pyproject.toml` | Add cupy as optional dependency |

## Dependencies

Optional (for GPU support):
- `cupy-cuda11x` or `cupy-cuda12x` (NVIDIA CUDA)
- OR `torch` with CUDA support

## Success Criteria

- [ ] GPU integration produces same results as CPU
- [ ] Automatic backend selection works
- [ ] Memory management prevents OOM errors
- [ ] 10-50x speedup for large systems
- [ ] Graceful fallback when GPU unavailable
- [ ] All tests pass (skipped if no GPU)

## Performance Targets

| System Size | CPU (Numba) | GPU (CuPy) | Speedup |
|-------------|-------------|------------|---------|
| 100 DOF | 0.5 s | 0.2 s | 2.5x |
| 500 DOF | 5 s | 0.3 s | 17x |
| 1000 DOF | 25 s | 0.5 s | 50x |
| MC 1000 samples (100 DOF) | 50 s | 3 s | 17x |

Note: GPU overhead makes it less beneficial for small systems (< 50 DOF).
