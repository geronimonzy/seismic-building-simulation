# Task 08: Parallel Monte Carlo

## Priority: HIGH
## Estimated Effort: 2-3 days

## Problem Statement

The current Monte Carlo implementation:
- Runs samples sequentially
- Cannot utilize multi-core CPUs
- Takes excessive time for large ensembles
- Does not scale with available compute resources

## Implementation Plan

### 1. Create parallel MC module
Create `src/seismic_twin/uncertainty/monte_carlo_parallel.py`

### 2. Implement ParallelUncertaintyAnalysis class

```python
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class ParallelMCResult:
    """Results from parallel Monte Carlo analysis."""
    displacement_samples: np.ndarray  # (n_samples, n_steps, n_dof)
    velocity_samples: np.ndarray
    acceleration_samples: np.ndarray
    parameter_samples: List[Dict]
    percentiles: Dict[str, np.ndarray]  # p5, p50, p95
    computation_time: float
    n_workers: int

class ParallelUncertaintyAnalysis:
    """Monte Carlo with process-level parallelism."""

    def __init__(self, n_workers: Optional[int] = None):
        """
        Parameters:
        -----------
        n_workers : int, optional
            Number of worker processes. Defaults to CPU count.
        """
        self.n_workers = n_workers or mp.cpu_count()

    def run_mc_ensemble_parallel(
        self,
        model: 'StructuralModel',
        ground_acceleration: np.ndarray,
        dt: float,
        n_samples: int,
        stiffness_cov: float = 0.05,
        damping_cov: float = 0.20,
        seed: Optional[int] = None,
        show_progress: bool = True,
    ) -> ParallelMCResult:
        """
        Run Monte Carlo ensemble in parallel.

        Parameters:
        -----------
        model : StructuralModel
            Base structural model
        ground_acceleration : array
            Ground motion [m/s²]
        dt : float
            Time step [s]
        n_samples : int
            Number of MC samples
        stiffness_cov : float
            Coefficient of variation for stiffness
        damping_cov : float
            Coefficient of variation for damping
        seed : int, optional
            Random seed for reproducibility
        show_progress : bool
            Show progress bar

        Returns:
        --------
        ParallelMCResult with displacement bounds and statistics
        """
        pass
```

### 3. Implement sample generation

```python
def _generate_samples(
    self,
    n_samples: int,
    stiffness_cov: float,
    damping_cov: float,
    base_damping: float = 0.05,
    seed: Optional[int] = None,
) -> List[Dict]:
    """
    Generate parameter samples for MC.

    Uses Latin Hypercube Sampling for better coverage.
    """
    if seed is not None:
        np.random.seed(seed)

    # Latin Hypercube Sampling
    from scipy.stats import qmc

    sampler = qmc.LatinHypercube(d=2, seed=seed)
    lhs_samples = sampler.random(n=n_samples)

    # Transform to normal distribution
    stiffness_factors = 1.0 + stiffness_cov * (lhs_samples[:, 0] * 2 - 1) * 3
    damping_ratios = base_damping * (1 + damping_cov * (lhs_samples[:, 1] * 2 - 1) * 3)

    # Clip to reasonable bounds
    stiffness_factors = np.clip(stiffness_factors, 0.5, 1.5)
    damping_ratios = np.clip(damping_ratios, 0.01, 0.20)

    return [
        {'stiffness_factor': sf, 'damping_ratio': dr}
        for sf, dr in zip(stiffness_factors, damping_ratios)
    ]
```

### 4. Implement worker function

```python
# Module-level function for pickling
def _run_single_sample_worker(args: Tuple) -> Dict:
    """
    Run one model realization (runs in worker process).

    Must be module-level for ProcessPoolExecutor.
    """
    model_params, ground_acc, dt, sample = args

    # Reconstruct model in worker (models aren't picklable directly)
    from seismic_twin.building import MDOFShearBuilding

    model = MDOFShearBuilding(
        masses=model_params['masses'],
        stiffnesses=model_params['stiffnesses'] * sample['stiffness_factor'],
        damping_ratio=sample['damping_ratio'],
        story_heights=model_params['story_heights'],
    )

    # Run integration (use fast version if available)
    try:
        from seismic_twin.analysis.integration_fast import newmark_beta_fast
        result = newmark_beta_fast(
            model.M, model.C, model.K, ground_acc, dt
        )
    except ImportError:
        from seismic_twin.analysis import newmark_beta
        result = newmark_beta(
            model.M, model.C, model.K, ground_acc, dt
        )

    return {
        'displacement': result.displacement,
        'velocity': result.velocity,
        'acceleration': result.acceleration,
        'parameters': sample,
    }
```

### 5. Implement main parallel execution

```python
def run_mc_ensemble_parallel(self, model, ground_acceleration, dt,
                             n_samples, **kwargs) -> ParallelMCResult:
    import time
    t_start = time.perf_counter()

    # Generate samples
    samples = self._generate_samples(
        n_samples,
        kwargs.get('stiffness_cov', 0.05),
        kwargs.get('damping_cov', 0.20),
        seed=kwargs.get('seed'),
    )

    # Prepare model parameters for serialization
    model_params = {
        'masses': model._masses.copy(),
        'stiffnesses': model._base_stiffnesses.copy(),
        'story_heights': model._story_heights.copy(),
    }

    # Prepare arguments for workers
    work_items = [
        (model_params, ground_acceleration, dt, sample)
        for sample in samples
    ]

    # Run in parallel
    results = []
    with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
        futures = {
            executor.submit(_run_single_sample_worker, item): i
            for i, item in enumerate(work_items)
        }

        if kwargs.get('show_progress', True):
            from tqdm import tqdm
            pbar = tqdm(total=n_samples, desc="MC Samples")

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if kwargs.get('show_progress', True):
                pbar.update(1)

        if kwargs.get('show_progress', True):
            pbar.close()

    # Aggregate results
    displacements = np.array([r['displacement'] for r in results])
    velocities = np.array([r['velocity'] for r in results])
    accelerations = np.array([r['acceleration'] for r in results])

    # Compute percentiles
    percentiles = {
        'p5': np.percentile(displacements, 5, axis=0),
        'p50': np.percentile(displacements, 50, axis=0),
        'p95': np.percentile(displacements, 95, axis=0),
    }

    return ParallelMCResult(
        displacement_samples=displacements,
        velocity_samples=velocities,
        acceleration_samples=accelerations,
        parameter_samples=[r['parameters'] for r in results],
        percentiles=percentiles,
        computation_time=time.perf_counter() - t_start,
        n_workers=self.n_workers,
    )
```

### 6. Add chunked processing for memory efficiency

```python
def run_mc_chunked(
    self,
    model: 'StructuralModel',
    ground_acceleration: np.ndarray,
    dt: float,
    n_samples: int,
    chunk_size: int = 100,
    **kwargs
) -> ParallelMCResult:
    """
    Run MC in chunks to limit memory usage.

    Useful when n_samples is very large.
    """
    all_results = []
    n_chunks = (n_samples + chunk_size - 1) // chunk_size

    for chunk_idx in range(n_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, n_samples)
        chunk_n = end - start

        chunk_result = self.run_mc_ensemble_parallel(
            model, ground_acceleration, dt, chunk_n,
            seed=kwargs.get('seed', 0) + chunk_idx,
            show_progress=False,
            **kwargs
        )

        all_results.append(chunk_result)
        print(f"Completed chunk {chunk_idx + 1}/{n_chunks}")

    # Combine results
    return self._combine_results(all_results)
```

### 7. Add tests

- Test parallel execution matches serial
- Test different worker counts
- Test reproducibility with seed
- Test memory efficiency with large ensembles
- Verify speedup scales with cores

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/uncertainty/monte_carlo_parallel.py` | Create |
| `src/seismic_twin/uncertainty/__init__.py` | Modify (export parallel) |
| `tests/test_monte_carlo_parallel.py` | Create |
| `pyproject.toml` | Add tqdm, scipy dependencies |

## Dependencies

- `scipy>=1.9` (for Latin Hypercube sampling)
- `tqdm` (optional, for progress bars)

## Success Criteria

- [ ] Parallel MC produces same statistics as serial
- [ ] Near-linear speedup with worker count
- [ ] Reproducible results with seed
- [ ] Memory-efficient chunked processing works
- [ ] Progress reporting works
- [ ] All tests pass

## Performance Targets

| Scenario | Serial | 4 workers | 8 workers |
|----------|--------|-----------|-----------|
| 100 samples | ~60 s | ~18 s | ~10 s |
| 500 samples | ~300 s | ~85 s | ~45 s |
| 1000 samples | ~600 s | ~165 s | ~85 s |

(Assuming Numba is also enabled for additional speedup)
