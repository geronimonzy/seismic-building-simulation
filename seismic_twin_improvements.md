# Seismic Building Simulation - Improvement Plan

## Executive Summary

Your package is well-structured with good modularization. This plan proposes **7 major improvement areas** with concrete, prioritized actions to make it production-ready, extensible, and suitable for research deployment.

---

## 1. Architecture & Design Patterns

### 1.1 Problem
- No formal data model layer (validation, serialization)
- No configuration management (reproducibility)
- Tight coupling between modules (e.g., calibration tightly coupled to specific model)
- No plugin/extension system for custom models/methods

### 1.2 Recommendations

#### A. Introduce Pydantic Data Models (Priority: HIGH)

Replace implicit assumptions with explicit validation:

```python
# src/seismic_twin/models/datamodels.py

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Tuple
import numpy as np

class BuildingConfig(BaseModel):
    """Validated building configuration."""
    n_stories: int = Field(..., ge=1, le=100, description="Number of stories")
    masses: List[float] = Field(..., description="Floor masses [kg]")
    stiffnesses: List[float] = Field(..., description="Story stiffnesses [N/m]")
    story_heights: List[float] = Field(..., description="Story heights [m]")
    damping_ratio: float = Field(0.05, ge=0.01, le=0.20, description="Modal damping ratio")
    name: Optional[str] = None
    
    @validator('masses', 'stiffnesses', 'story_heights')
    def check_lengths_match(cls, v, values):
        if 'n_stories' in values:
            if len(v) != values['n_stories']:
                raise ValueError(f"Length must equal n_stories={values['n_stories']}")
        return v
    
    @validator('masses', 'stiffnesses')
    def check_positive(cls, v):
        if any(x <= 0 for x in v):
            raise ValueError("All values must be positive")
        return v

class GroundMotionConfig(BaseModel):
    """Earthquake scenario configuration."""
    duration: float = Field(..., gt=0, description="Duration [s]")
    dt: float = Field(..., gt=0, le=0.1, description="Time step [s]")
    target_pga: float = Field(..., gt=0, description="PGA in g")
    predominant_freq: float = Field(2.5, gt=0, description="Hz")
    magnitude: Optional[float] = Field(None, ge=4.0, le=9.0, description="Mw")
    epicenter: Optional[Tuple[float, float]] = Field(None, description="(lat, lon)")
    rupture_id: Optional[str] = None

class SensorConfig(BaseModel):
    """Sensor network configuration."""
    sensor_name: str
    floor_index: int = Field(..., ge=0, description="0-indexed floor")
    measurement_type: str = Field(..., regex="^(displacement|velocity|acceleration)$")
    uncertainty_std: Optional[float] = Field(None, ge=0, description="Measurement noise std")

class CalibrationConfig(BaseModel):
    """Calibration problem setup."""
    max_iterations: int = Field(20, gt=0)
    tolerance: float = Field(0.01, gt=0)
    stiffness_bounds: Tuple[float, float] = (0.7, 1.3)
    damping_bounds: Tuple[float, float] = (0.02, 0.15)
    optimization_method: str = Field("grid_search", regex="^(grid_search|nelder_mead|bayesian)$")

class ProjectConfig(BaseModel):
    """Complete project configuration (YAML/JSON serializable)."""
    project_name: str
    building: BuildingConfig
    ground_motion: GroundMotionConfig
    sensors: List[SensorConfig]
    calibration: CalibrationConfig
    
    class Config:
        schema_extra = {
            "example": {
                "project_name": "christchurch_mw6.2",
                "building": {
                    "n_stories": 4,
                    "masses": [100000, 100000, 100000, 100000],
                    "stiffnesses": [50e6, 50e6, 50e6, 50e6],
                    "story_heights": [3.5, 3.5, 3.5, 3.0],
                    "damping_ratio": 0.05,
                    "name": "4-story RC moment frame"
                },
                "ground_motion": {
                    "duration": 30.0,
                    "dt": 0.01,
                    "target_pga": 0.35,
                    "predominant_freq": 2.5,
                    "magnitude": 6.2
                },
                "sensors": [
                    {"sensor_name": "acc_f1", "floor_index": 0, "measurement_type": "acceleration", "uncertainty_std": 0.01},
                    {"sensor_name": "disp_f3", "floor_index": 2, "measurement_type": "displacement", "uncertainty_std": 0.005}
                ],
                "calibration": {
                    "max_iterations": 15,
                    "tolerance": 0.02,
                    "optimization_method": "nelder_mead"
                }
            }
        }
```

**Benefits:**
- YAML/JSON serialization → reproducibility
- Automatic validation → catch errors early
- Self-documenting configs
- IDE autocomplete support

#### B. Abstract Model Interface (Priority: HIGH)

Allow swapping building models:

```python
# src/seismic_twin/building/base.py

from abc import ABC, abstractmethod
import numpy as np

class StructuralModel(ABC):
    """Abstract base for structural models."""
    
    @abstractmethod
    def get_mass_matrix(self) -> np.ndarray:
        """Return (n_dof, n_dof) mass matrix."""
        pass
    
    @abstractmethod
    def get_stiffness_matrix(self) -> np.ndarray:
        """Return (n_dof, n_dof) stiffness matrix."""
        pass
    
    @abstractmethod
    def get_damping_matrix(self) -> np.ndarray:
        """Return (n_dof, n_dof) damping matrix."""
        pass
    
    @abstractmethod
    def get_influence_vector(self, direction: str = 'x') -> np.ndarray:
        """Return influence vector for excitation direction ('x', 'y', 'z')."""
        pass
    
    @abstractmethod
    def get_n_dof(self) -> int:
        """Number of DOF."""
        pass
    
    @abstractmethod
    def update_parameter(self, param_name: str, value: float) -> None:
        """Update a model parameter (e.g., stiffness scale, damping ratio)."""
        pass
    
    @abstractmethod
    def copy(self) -> 'StructuralModel':
        """Create independent copy."""
        pass


class MDOFShearBuilding(StructuralModel):
    """Implements the abstract interface."""
    # ... existing implementation ...
    
    def get_influence_vector(self, direction: str = 'x') -> np.ndarray:
        """For MDOF shear: excitation in lateral direction."""
        return np.ones(self.n_dof)
    
    def get_n_dof(self) -> int:
        return self.n_dof
```

**Enables:**
- 3D building models
- Lumped mass vs distributed models
- Custom nonlinear models
- Easy benchmarking

---

## 2. Integration with Real Data Sources

### 2.1 Problem
- Currently only generates synthetic ground motions
- No connection to USGS/seismic network data
- No finite-fault model support

### 2.2 Recommendations

#### A. SeismoHub Integration Layer (Priority: HIGH)

```python
# src/seismic_twin/data/seismic_catalog.py

from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np
from typing import Tuple, List

class SeismicDataFetcher:
    """Fetch real earthquake data from USGS/regional networks."""
    
    def __init__(self, network: str = "US"):
        """
        Parameters:
        -----------
        network : str
            FDSN network code (US=USGS, GE=GFZ, etc.)
        """
        self.client = Client(network)
    
    def get_event_finite_fault(
        self, 
        event_id: str,
        source: str = "usgs"  # "usgs" or "globalcmt"
    ) -> dict:
        """
        Fetch finite-fault model for an event.
        
        Returns:
        --------
        dict with keys:
            - rupture: array of (lon, lat, depth, slip, rake, rake_slip)
            - hypocenter: (lon, lat, depth, time)
            - magnitude: Mw
            - moment_tensor: (Mrr, Mtt, Mpp, Mrt, Mrp, Mtp)
        """
        if source == "usgs":
            # Parse from USGS Finite Fault DB
            # https://earthquake.usgs.gov/earthquakes/events/
            rupture_data = self._parse_usgs_finite_fault(event_id)
        elif source == "globalcmt":
            # Use CMT solution
            rupture_data = self._fetch_globalcmt(event_id)
        
        return rupture_data
    
    def get_event_seismograms(
        self,
        event_id: str,
        network_code: str = "HZ",
        distance_range: Tuple[float, float] = (0, 180),
    ) -> List[dict]:
        """
        Fetch actual seismic recordings of an event.
        
        Returns:
        --------
        List of waveforms with metadata.
        """
        # Query FDSN
        events = self.client.get_events(eventid=event_id, limit=1)
        event = events[0]
        
        # Fetch waveforms
        t1 = event.origins[0].time
        t2 = t1 + 300  # 5 minutes after origin
        
        try:
            st = self.client.get_waveforms(
                network="*", station="*", location="*", channel=network_code,
                starttime=t1, endtime=t2,
                minradius=distance_range[0], maxradius=distance_range[1],
            )
        except Exception as e:
            print(f"Warning: No waveforms found: {e}")
            return []
        
        waveforms = []
        for trace in st:
            waveforms.append({
                'network': trace.stats.network,
                'station': trace.stats.station,
                'location': trace.stats.location,
                'channel': trace.stats.channel,
                'latitude': trace.stats.sac.get('stla', None),
                'longitude': trace.stats.sac.get('stlo', None),
                'depth_m': trace.stats.sac.get('stdp', None),
                'time': np.arange(len(trace)) * trace.stats.delta,
                'acceleration': trace.data,  # Typically in m/s² from USGS
                'dt': trace.stats.delta,
            })
        
        return waveforms
    
    def _parse_usgs_finite_fault(self, event_id: str) -> dict:
        """Parse USGS Finite Fault DB URL."""
        import requests
        url = f"https://earthquake.usgs.gov/earthquakes/events/{event_id}/finite_fault.php"
        # ... parsing logic ...
        pass
    
    def _fetch_globalcmt(self, event_id: str) -> dict:
        """Fetch from Global CMT catalog."""
        # ... CMT API logic ...
        pass


# Usage example
if __name__ == "__main__":
    fetcher = SeismicDataFetcher(network="US")
    
    # Get finite-fault model
    rupture = fetcher.get_event_finite_fault("us2011k820")  # Christchurch
    print(f"Magnitude: {rupture['magnitude']}")
    
    # Get recordings from nearby stations
    recordings = fetcher.get_event_seismograms("us2011k820", distance_range=(0, 50))
    print(f"Found {len(recordings)} station records")
```

#### B. SCEC Broadband Platform Interface (Priority: MEDIUM)

```python
# src/seismic_twin/ground_motion/scec_bbp.py

import subprocess
import tempfile
import os

class SCECBroadbandPlatform:
    """Interface to SCEC BBP for physics-based ground motion synthesis."""
    
    def __init__(self, bbp_path: str):
        """
        Parameters:
        -----------
        bbp_path : str
            Path to BBP installation root
        """
        self.bbp_path = bbp_path
        self.bbp_run = os.path.join(bbp_path, "bbp_run.py")
    
    def run_scenario(
        self,
        event_name: str,
        rupture_file: str,
        velocity_model: str,
        stations_file: str,
        method: str = "gp",  # or "exsim", "ucsb"
    ) -> dict:
        """
        Run BBP scenario simulation.
        
        Parameters:
        -----------
        event_name : str
            Name of event (e.g., "christchurch_mw6.2")
        rupture_file : str
            Path to SRF file (from USGS or synthetic)
        velocity_model : str
            Region velocity model (e.g., "nz_can", "scec_i16.3")
        stations_file : str
            Text file with columns: lon lat name
        method : str
            BBP method: "gp" (Graves-Pitarka), "exsim", "ucsb"
        
        Returns:
        --------
        dict with keys:
            - 'seismograms': dict mapping station -> (time, acc_e, acc_n, acc_z)
            - 'stations': list of station metadata dicts
            - 'run_dir': output directory
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "python", self.bbp_run,
                "--event-name", event_name,
                "--scenario",
                "--rupture-file", rupture_file,
                "--station-file", stations_file,
                "--velocity-model", velocity_model,
                "--method", method,
                "--output-dir", tmpdir,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"BBP failed: {result.stderr}")
            
            # Parse outputs
            seismograms = self._parse_bbp_output(tmpdir)
            
            return {
                'seismograms': seismograms,
                'run_dir': tmpdir,
                'method': method,
            }
    
    def _parse_bbp_output(self, output_dir: str) -> dict:
        """Parse BBP acc files."""
        # ...
        pass
```

---

## 3. Data Management & Serialization

### 3.1 Problem
- No standard way to save/load models and results
- Difficult to share reproducible analyses
- No version control for model configurations

### 3.2 Recommendations

#### A. HDF5 + YAML Storage (Priority: HIGH)

```python
# src/seismic_twin/io/storage.py

import h5py
import yaml
from pathlib import Path
from datetime import datetime

class ProjectArchive:
    """Save/load complete analysis to HDF5 + metadata."""
    
    def save(
        self,
        filename: str,
        building: StructuralModel,
        ground_motion: np.ndarray,
        dt: float,
        results: dict,
        config: ProjectConfig,
        metadata: dict = None,
    ) -> None:
        """
        Save entire project to HDF5 archive.
        
        Structure:
        ----------
        project.h5:
          ├── metadata/
          │   ├── timestamp (str)
          │   ├── version (str)
          │   └── description (str)
          ├── config.yaml (serialized ProjectConfig)
          ├── ground_motion/
          │   ├── time (array)
          │   ├── acceleration (array)
          │   └── dt (scalar)
          ├── building/
          │   ├── masses (array)
          │   ├── stiffnesses (array)
          │   └── properties (dict)
          └── results/
              ├── initial/
              │   ├── displacement (array, n_time × n_dof)
              │   ├── velocity (array)
              │   └── acceleration (array)
              ├── calibrated/
              │   ├── displacement (array)
              │   └── parameters (dict)
              └── uncertainty/
                  ├── mc_ensemble (array, n_samples × n_time × n_dof)
                  └── percentiles (dict with p5, p50, p95)
        """
        with h5py.File(filename, 'w') as hf:
            # Metadata
            meta_grp = hf.create_group('metadata')
            meta_grp.attrs['timestamp'] = datetime.now().isoformat()
            meta_grp.attrs['version'] = "1.0"
            meta_grp.attrs['description'] = metadata.get('description', '') if metadata else ''
            
            # Config (as YAML string)
            config_grp = hf.create_group('config')
            config_yaml = config.json()  # Pydantic .json()
            config_grp.attrs['config_json'] = config_yaml
            
            # Ground motion
            gm_grp = hf.create_group('ground_motion')
            gm_grp.create_dataset('acceleration', data=ground_motion)
            gm_grp.attrs['dt'] = dt
            
            # Building properties
            bldg_grp = hf.create_group('building')
            # ... serialize model matrices ...
            
            # Results
            res_grp = hf.create_group('results')
            for key, val in results.items():
                if isinstance(val, np.ndarray):
                    res_grp.create_dataset(key, data=val)
                elif isinstance(val, dict):
                    sub_grp = res_grp.create_group(key)
                    for k, v in val.items():
                        if isinstance(v, np.ndarray):
                            sub_grp.create_dataset(k, data=v)
    
    @staticmethod
    def load(filename: str) -> dict:
        """Load entire project from archive."""
        with h5py.File(filename, 'r') as hf:
            # Extract all data
            config_json = hf['config'].attrs['config_json']
            config = ProjectConfig.parse_raw(config_json)
            
            ground_motion = hf['ground_motion']['acceleration'][:]
            dt = hf['ground_motion'].attrs['dt']
            
            results = {}
            for key in hf['results'].keys():
                if isinstance(hf['results'][key], h5py.Dataset):
                    results[key] = hf['results'][key][:]
                else:
                    results[key] = {k: hf['results'][key][k][:] for k in hf['results'][key].keys()}
            
            return {
                'config': config,
                'ground_motion': ground_motion,
                'dt': dt,
                'results': results,
            }
```

#### B. Experiment Tracking (Priority: MEDIUM)

```python
# src/seismic_twin/tracking/experiments.py

import sqlite3
import json
from pathlib import Path

class ExperimentTracker:
    """Log and retrieve analysis runs (like MLflow for structural dynamics)."""
    
    def __init__(self, db_path: str = ".seismic_experiments.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Create schema if needed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    project_name TEXT,
                    building_n_stories INTEGER,
                    target_pga REAL,
                    method TEXT,
                    initial_nrmse REAL,
                    final_nrmse REAL,
                    config_json TEXT,
                    results_file TEXT,
                    notes TEXT
                )
            """)
            conn.commit()
    
    def log_run(
        self,
        project_name: str,
        config: ProjectConfig,
        initial_nrmse: float,
        final_nrmse: float,
        results_file: str,
        notes: str = "",
    ) -> int:
        """Log a completed analysis run."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO runs 
                (timestamp, project_name, building_n_stories, target_pga, method, 
                 initial_nrmse, final_nrmse, config_json, results_file, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                project_name,
                config.building.n_stories,
                config.ground_motion.target_pga,
                config.calibration.optimization_method,
                initial_nrmse,
                final_nrmse,
                config.json(),
                results_file,
                notes,
            ))
            conn.commit()
            return cursor.lastrowid
    
    def query_runs(self, project_name: str = None) -> list:
        """Retrieve past runs."""
        with sqlite3.connect(self.db_path) as conn:
            if project_name:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE project_name = ? ORDER BY timestamp DESC",
                    (project_name,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM runs ORDER BY timestamp DESC").fetchall()
            return rows
```

---

## 4. Computational Performance

### 4.1 Problem
- All-Python implementation may be slow for large ensembles
- No parallelization
- Time integration is a bottleneck

### 4.2 Recommendations

#### A. Numba JIT Compilation (Priority: HIGH)

```python
# src/seismic_twin/analysis/integration_fast.py

import numpy as np
from numba import jit

@jit(nopython=True, parallel=True, cache=True)
def newmark_beta_numba(
    M: np.ndarray,
    C: np.ndarray,
    K: np.ndarray,
    ground_acc: np.ndarray,
    dt: float,
    gamma: float = 0.5,
    beta: float = 0.25,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Newmark-beta integration (Numba-optimized).
    
    ~50-100x faster than pure Python for large arrays.
    """
    n_dof = M.shape[0]
    n_steps = len(ground_acc)
    
    # Preallocate
    u = np.zeros((n_steps, n_dof))
    v = np.zeros((n_steps, n_dof))
    a = np.zeros((n_steps, n_dof))
    
    # Effective matrices
    Keff = K + (gamma / (beta * dt)) * C + (1.0 / (beta * dt**2)) * M
    M_inv = np.linalg.inv(M)
    Keff_inv = np.linalg.inv(Keff)
    
    one_vec = np.ones(n_dof)
    
    for step in range(1, n_steps):
        dg = ground_acc[step] - ground_acc[step - 1]
        
        # Compute load increment
        dF = -M @ (one_vec * dg)
        dF += C @ (gamma / (beta * dt) * (u[step - 1] - u[step]) + 
                   (1 - gamma / beta) * v[step - 1] + 
                   (1 - gamma / (2 * beta)) * dt * a[step - 1])
        dF += M @ ((1.0 / (beta * dt**2)) * (u[step - 1] - u[step]) - 
                   v[step - 1] / (beta * dt) - 
                   (1.0 / (2 * beta) - 1) * a[step - 1])
        
        # Solve
        du = Keff_inv @ dF
        u[step] = u[step - 1] + du
        
        # Update v, a
        v[step] = (gamma / (beta * dt)) * du + (1 - gamma / beta) * v[step - 1] + \
                  (1 - gamma / (2 * beta)) * dt * a[step - 1]
        a[step] = (1.0 / (beta * dt**2)) * du - v[step - 1] / (beta * dt) - \
                  (1.0 / (2 * beta) - 1) * a[step - 1]
    
    return u, v, a
```

#### B. Parallel Monte Carlo (Priority: HIGH)

```python
# src/seismic_twin/uncertainty/monte_carlo_parallel.py

from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

class ParallelUncertaintyAnalysis:
    """Monte Carlo with process-level parallelism."""
    
    def __init__(self, n_workers: int = None):
        self.n_workers = n_workers or mp.cpu_count()
    
    def run_mc_ensemble_parallel(
        self,
        model: StructuralModel,
        ground_acceleration: np.ndarray,
        dt: float,
        n_samples: int,
        stiffness_cov: float = 0.05,
        damping_cov: float = 0.20,
        seed: int = None,
    ) -> MonteCarloResult:
        """
        Run MC ensemble in parallel (one model per worker).
        
        ~8-16x speedup on 16-core machine vs serial.
        """
        if seed is not None:
            np.random.seed(seed)
        
        # Generate parameter samples
        samples = self._generate_samples(n_samples, stiffness_cov, damping_cov)
        
        # Distribute to workers
        displacements = []
        velocities = []
        accelerations = []
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = {}
            for i, sample in enumerate(samples):
                future = executor.submit(
                    self._run_single_sample,
                    model, ground_acceleration, dt, sample
                )
                futures[future] = i
            
            for future in as_completed(futures):
                result = future.result()
                displacements.append(result['displacement'])
                velocities.append(result['velocity'])
                accelerations.append(result['acceleration'])
        
        # Aggregate results
        return MonteCarloResult(
            displacement_samples=np.array(displacements),
            velocity_samples=np.array(velocities),
            acceleration_samples=np.array(accelerations),
            parameter_samples=samples,
        )
    
    @staticmethod
    def _run_single_sample(
        model: StructuralModel,
        ground_acc: np.ndarray,
        dt: float,
        sample: dict,
    ) -> dict:
        """Run one model realization (runs in worker process)."""
        # Update model with sample parameters
        model_copy = model.copy()
        model_copy.update_parameter('stiffness_factor', sample['stiffness_factor'])
        model_copy.update_parameter('damping_ratio', sample['damping_ratio'])
        
        # Run analysis
        from seismic_twin.analysis.integration_fast import newmark_beta_numba
        u, v, a = newmark_beta_numba(
            model_copy.get_mass_matrix(),
            model_copy.get_damping_matrix(),
            model_copy.get_stiffness_matrix(),
            ground_acc, dt
        )
        
        return {'displacement': u, 'velocity': v, 'acceleration': a}
```

#### C. GPU Acceleration (Priority: MEDIUM)

```python
# src/seismic_twin/analysis/integration_gpu.py (CuPy optional dependency)

try:
    import cupy as cp
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

def newmark_beta_gpu(
    M: np.ndarray,
    C: np.ndarray,
    K: np.ndarray,
    ground_acc: np.ndarray,
    dt: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Newmark-beta on GPU (CuPy).
    
    Requires: pip install cupy-cuda11x
    ~10-50x faster for very large systems (n_dof > 1000).
    """
    if not HAS_GPU:
        raise RuntimeError("CuPy not installed. Install with: pip install cupy-cuda11x")
    
    # Transfer to GPU
    M_gpu = cp.asarray(M)
    C_gpu = cp.asarray(C)
    K_gpu = cp.asarray(K)
    acc_gpu = cp.asarray(ground_acc)
    
    n_dof = M_gpu.shape[0]
    n_steps = len(acc_gpu)
    
    # ... GPU-optimized Newmark implementation ...
    
    # Transfer back to CPU
    u_cpu = cp.asnumpy(u_gpu)
    v_cpu = cp.asnumpy(v_gpu)
    a_cpu = cp.asnumpy(a_gpu)
    
    return u_cpu, v_cpu, a_cpu
```

---

## 5. Testing & Validation

### 5.1 Problem
- Only 42 tests mentioned; insufficient coverage
- No benchmark validation suite
- No numerical accuracy tests

### 5.2 Recommendations

#### A. Expanded Test Suite (Priority: HIGH)

```python
# tests/test_integration_accuracy.py

import numpy as np
import pytest
from seismic_twin.analysis import newmark_beta

class TestNumericalAccuracy:
    """Validate integration accuracy against analytical solutions."""
    
    def test_single_dof_undamped_oscillator(self):
        """Newmark-beta on simple harmonic oscillator."""
        # Analytical: u(t) = u0 * cos(ωt) + (v0/ω) * sin(ωt)
        
        m, k = 1.0, 100.0  # ω = 10 rad/s
        u0, v0 = 0.1, 0.0  # initial conditions
        
        # Build 1-DOF system
        M = np.array([[m]])
        K = np.array([[k]])
        C = np.zeros((1, 1))
        
        # Free vibration (no excitation)
        ground_acc = np.zeros(1000)
        dt = 0.001
        
        result = newmark_beta(M, C, K, ground_acc, dt, u0=u0, v0=v0)
        
        # Check against analytical
        time = np.arange(len(result.displacement)) * dt
        u_analytical = u0 * np.cos(10 * time)
        
        error = np.max(np.abs(result.displacement[:, 0] - u_analytical))
        assert error < 0.001, f"Integration error too large: {error}"
    
    def test_El_Centro_baseline(self):
        """Reproduce known ground motion response (1940 El Centro)."""
        # Load El Centro acceleration record
        acc_el_centro = self._load_el_centro()
        
        # Standard 1-story structure
        m = 1.0
        k = 400.0  # Natural period ≈ 0.31 s
        M = np.array([[m]])
        K = np.array([[k]])
        C = 0.05 * 2 * np.sqrt(m * k) * np.eye(1)  # 5% damping
        
        result = newmark_beta(M, C, K, acc_el_centro, dt=0.01)
        
        # Compare to published response spectrum value
        # At T=0.31s, Sa ≈ 0.36g for El Centro
        spectral_accel = np.max(np.abs(result.absolute_acceleration[:, 0])) / 9.81
        
        assert 0.3 < spectral_accel < 0.45, f"Unexpected Sa: {spectral_accel}g"
    
    def test_energy_balance(self):
        """Check energy conservation (input = KE + PE + damped)."""
        # ... energy balance test ...
        pass
    
    @staticmethod
    def _load_el_centro() -> np.ndarray:
        """Load 1940 El Centro NS component."""
        # Download from PEER or use packaged version
        pass


class TestCalibrationAccuracy:
    """Validate calibration converges to true parameters."""
    
    def test_synthetic_data_calibration(self):
        """
        Generate synthetic data from known model,
        then verify calibration recovers parameters.
        """
        # True model
        true_stiffness = 50e6
        true_damping = 0.05
        
        # Generate synthetic measurements
        true_model = MDOFShearBuilding(
            masses=[100e3, 100e3, 100e3],
            stiffnesses=[true_stiffness] * 3,
            damping_ratio=true_damping,
        )
        
        time, ground_acc = generate_synthetic_ground_motion(duration=20, dt=0.01)
        result = newmark_beta(true_model.M, true_model.C, true_model.K, ground_acc, 0.01)
        
        # Add noise
        measurements = result.displacement + 0.01 * np.random.randn(*result.displacement.shape)
        
        # Calibrate from perturbed starting point
        perturbed_model = MDOFShearBuilding(
            masses=[100e3, 100e3, 100e3],
            stiffnesses=[true_stiffness * 0.8] * 3,  # Start 20% lower
            damping_ratio=true_damping * 1.2,  # Start 20% higher
        )
        
        calib = StructuralCalibration(perturbed_model, ground_acc, 0.01, measurements, [0, 1, 2])
        result = calib.calibrate(max_iterations=20, tolerance=0.01)
        
        # Check convergence
        assert result.nrmse < 0.05, f"Calibration failed: NRMSE={result.nrmse}"
        assert abs(result.stiffness_factor - 1.0) < 0.1
        assert abs(result.damping_ratio - true_damping) < 0.01
```

#### B. Continuous Integration (Priority: HIGH)

```yaml
# .github/workflows/tests.yml

name: Tests and Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run tests with coverage
      run: |
        pytest tests/ --cov=seismic_twin --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
    
    - name: Check code quality
      run: |
        flake8 src/seismic_twin --max-line-length=100
        black --check src/seismic_twin tests/
        mypy src/seismic_twin --ignore-missing-imports
```

---

## 6. Documentation & Usability

### 6.1 Problem
- Minimal user guide
- No interactive examples (Jupyter notebooks)
- No API reference with examples

### 6.2 Recommendations

#### A. Sphinx Documentation (Priority: HIGH)

```bash
# docs/index.rst

Seismic Building Simulation
============================

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/first_steps
   getting_started/examples

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   guide/building_models
   guide/ground_motion
   guide/calibration
   guide/uncertainty

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/building
   api/analysis
   api/calibration
   api/visualization

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   advanced/custom_models
   advanced/parallel_computing
   advanced/data_integration
   advanced/physics_based_methods
```

#### B. Interactive Notebooks (Priority: HIGH)

```python
# examples/notebooks/01_basic_workflow.ipynb

# This would be a Jupyter notebook with:
# 1. Building model definition (step-by-step with plots)
# 2. Ground motion generation and visualization
# 3. Time history analysis (displacements, drifts, energy)
# 4. Sensor data integration
# 5. Calibration convergence
# 6. Uncertainty quantification
# 7. Export and visualization
```

---

## 7. Advanced Features

### 7.1 Problem
- No support for nonlinear material behavior
- No P-delta effects
- No soil-structure interaction

### 7.2 Recommendations

#### A. Nonlinear Hysteretic Models (Priority: MEDIUM)

```python
# src/seismic_twin/nonlinearity/hysteresis.py

class HystereticElement(ABC):
    """Base class for hysteretic spring elements."""
    
    @abstractmethod
    def compute_force(self, deformation: float, deformation_rate: float) -> float:
        """Compute restoring force given deformation state."""
        pass
    
    @abstractmethod
    def copy(self) -> 'HystereticElement':
        pass


class BilinearHysteresis(HystereticElement):
    """Bilinear elasto-plastic spring (Clipped Optimal)."""
    
    def __init__(self, k_elastic: float, k_plastic: float, yield_force: float):
        self.k_elastic = k_elastic
        self.k_plastic = k_plastic
        self.yield_force = yield_force
        self.cumulative_inelastic_deformation = 0.0
    
    def compute_force(self, deformation: float, deformation_rate: float) -> float:
        """Bilinear backbone with Masing unloading rules."""
        # ...
        pass


class MDOFNonlinearShearBuilding(StructuralModel):
    """MDOF building with hysteretic story springs."""
    
    def __init__(
        self,
        masses: List[float],
        story_heights: List[float],
        hysteretic_elements: List[HystereticElement],
        damping_ratio: float = 0.05,
    ):
        self.masses = np.array(masses)
        self.hysteretic_elements = hysteretic_elements
        self.n_dof = len(masses)
        # ...
    
    def get_stiffness_matrix_tangent(self, deformation: np.ndarray) -> np.ndarray:
        """Tangent stiffness (deformation-dependent)."""
        K_tangent = np.zeros((self.n_dof, self.n_dof))
        for i, elem in enumerate(self.hysteretic_elements):
            k_i = elem.get_tangent_stiffness(deformation[i])
            K_tangent[i, i] += k_i
            if i > 0:
                K_tangent[i, i - 1] -= k_i
                K_tangent[i - 1, i] -= k_i
                K_tangent[i - 1, i - 1] += k_i
        return K_tangent


# Integrate with existing analysis
def newmark_beta_nonlinear(
    M: np.ndarray,
    C: np.ndarray,
    K_elastic: np.ndarray,
    hysteretic_elements: List[HystereticElement],
    ground_acceleration: np.ndarray,
    dt: float,
) -> IntegrationResult:
    """Newmark-beta for nonlinear systems (tangent stiffness iteration)."""
    # ...
    pass
```

#### B. Soil-Structure Interaction (Priority: MEDIUM)

```python
# src/seismic_twin/ssi/foundation.py

class RigidFoundation:
    """
    Rigid foundation with frequency-dependent impedance.
    Based on Gazetas coefficients.
    """
    
    def __init__(
        self,
        foundation_diameter: float,  # meters
        soil_shear_velocity: float,  # m/s
        soil_density: float,  # kg/m³
        poisson_ratio: float = 0.33,
    ):
        # Compute impedance functions
        # (frequency-dependent springs and dampers)
        pass
    
    def get_impedance(self, frequency: float) -> Tuple[float, float]:
        """
        Return (stiffness, damping) at given frequency.
        """
        pass
```

---

## 8. Recommended Implementation Roadmap

### Phase 1 (Months 1-2): Foundation
- ✅ Implement Pydantic data models
- ✅ Add abstract base classes
- ✅ Create HDF5 storage layer
- ~15-20% effort

### Phase 2 (Months 2-3): Real Data
- ✅ SeismoHub integration
- ✅ SCEC BBP wrapper
- ✅ Experiment tracker
- ~20-25% effort

### Phase 3 (Month 4): Performance
- ✅ Numba compilation
- ✅ Parallel MC
- ✅ GPU support (optional)
- ~15-20% effort

### Phase 4 (Month 5): Testing & Docs
- ✅ Expand test suite to 100+ tests
- ✅ Sphinx documentation
- ✅ 5 interactive notebooks
- ✅ GitHub Actions CI/CD
- ~20-25% effort

### Phase 5 (Month 6): Advanced
- ✅ Nonlinear hysteresis models
- ✅ SSI foundation effects
- ✅ Publication examples
- ~10-15% effort

---

## 9. Metrics for Success

| Metric | Current | Target |
|--------|---------|--------|
| Test coverage | ~70%? | **>95%** |
| Time for MC (100 samples) | ~30 sec | **<5 sec** (Numba + parallel) |
| Documentation pages | ~5 | **>20** |
| API stability | Pre-1.0 | **Semantic versioning** |
| Real data support | None | **USGS + SCEC BBP + ObsPy** |
| Performance benchmark suite | None | **10+ standard tests** |

---

## 10. Quick Wins (Do These First)

1. **Add Pydantic validation** (1-2 days) → Much better error messages
2. **Add HDF5 storage** (2-3 days) → Reproducibility
3. **Numba JIT compilation** (3-4 days) → 50-100x speedup
4. **GitHub Actions** (1-2 days) → Automated testing
5. **Sphinx docs** (3-5 days) → Professional appearance

---

## Summary Table

| Area | Problem | Solution | Priority | Effort |
|------|---------|----------|----------|--------|
| Architecture | Tight coupling | Abstract base + Pydantic | HIGH | Medium |
| Data | Synthetic only | USGS/SCEC/ObsPy integration | HIGH | Medium |
| Storage | No persistence | HDF5 + YAML | HIGH | Low |
| Performance | Serial MC slow | Numba + multiprocessing | HIGH | Medium |
| Testing | Insufficient coverage | Expand to 100+ tests + CI/CD | HIGH | Medium |
| Docs | Minimal | Sphinx + notebooks | HIGH | Medium |
| Advanced | No nonlinearity | Hysteresis models + SSI | MEDIUM | High |
| DevOps | Manual | GitHub Actions + experiment tracking | MEDIUM | Low |

---

## References & Tools

- **Pydantic**: https://pydantic-settings.readthedocs.io/
- **Sphinx**: https://www.sphinx-doc.org/
- **Numba**: https://numba.readthedocs.io/
- **ObsPy**: https://www.obspy.org/
- **HDF5**: https://www.h5py.org/
- **SCEC BBP**: https://github.com/SCEC/BBP
