# Task 05: HDF5 + YAML Storage Layer

## Priority: HIGH
## Estimated Effort: 2-3 days

## Problem Statement

The current codebase:
- Has no standard way to save/load models and results
- Cannot share reproducible analyses
- Loses intermediate results when sessions end
- Has no version control for model configurations

## Implementation Plan

### 1. Create storage module
Create `src/seismic_twin/io/storage.py`

### 2. Implement ProjectArchive class

```python
import h5py
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any

class ProjectArchive:
    """Save/load complete analysis to HDF5 archive."""

    VERSION = "1.0"

    def save(
        self,
        filename: str,
        building: 'StructuralModel',
        ground_motion: np.ndarray,
        dt: float,
        results: Dict[str, Any],
        config: Optional['ProjectConfig'] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Save entire project to HDF5 archive.

        Structure:
        ----------
        project.h5:
          ├── metadata/
          │   ├── timestamp (attr)
          │   ├── version (attr)
          │   └── description (attr)
          ├── config/ (serialized ProjectConfig)
          ├── ground_motion/
          │   ├── acceleration (dataset)
          │   └── dt (attr)
          ├── building/
          │   ├── masses (dataset)
          │   ├── stiffnesses (dataset)
          │   ├── damping_ratio (attr)
          │   └── story_heights (dataset)
          └── results/
              ├── displacement (dataset)
              ├── velocity (dataset)
              ├── acceleration (dataset)
              └── calibration/ (if present)
        """
        pass

    @classmethod
    def load(cls, filename: str) -> Dict[str, Any]:
        """
        Load entire project from archive.

        Returns dict with:
            - config: ProjectConfig (if saved)
            - ground_motion: np.ndarray
            - dt: float
            - building_params: dict
            - results: dict
            - metadata: dict
        """
        pass
```

### 3. Implement save method

```python
def save(self, filename: str, building, ground_motion, dt, results,
         config=None, metadata=None) -> None:
    with h5py.File(filename, 'w') as hf:
        # Metadata
        meta = hf.create_group('metadata')
        meta.attrs['timestamp'] = datetime.now().isoformat()
        meta.attrs['version'] = self.VERSION
        meta.attrs['description'] = (metadata or {}).get('description', '')

        # Config (as JSON string)
        if config is not None:
            cfg_grp = hf.create_group('config')
            cfg_grp.attrs['config_json'] = config.model_dump_json()

        # Ground motion
        gm = hf.create_group('ground_motion')
        gm.create_dataset('acceleration', data=ground_motion,
                          compression='gzip', compression_opts=4)
        gm.attrs['dt'] = dt

        # Building
        bldg = hf.create_group('building')
        bldg.create_dataset('M', data=building.get_mass_matrix())
        bldg.create_dataset('K', data=building.get_stiffness_matrix())
        bldg.create_dataset('C', data=building.get_damping_matrix())
        bldg.attrs['n_dof'] = building.get_n_dof()

        # Results (recursive for nested dicts)
        self._save_results_recursive(hf.create_group('results'), results)

def _save_results_recursive(self, group: h5py.Group, data: Dict) -> None:
    for key, val in data.items():
        if isinstance(val, np.ndarray):
            group.create_dataset(key, data=val, compression='gzip')
        elif isinstance(val, dict):
            self._save_results_recursive(group.create_group(key), val)
        elif isinstance(val, (int, float, str, bool)):
            group.attrs[key] = val
```

### 4. Implement load method

```python
@classmethod
def load(cls, filename: str) -> Dict[str, Any]:
    with h5py.File(filename, 'r') as hf:
        # Check version compatibility
        version = hf['metadata'].attrs.get('version', '0.0')
        if version != cls.VERSION:
            warnings.warn(f"Archive version {version} != current {cls.VERSION}")

        # Load config
        config = None
        if 'config' in hf:
            config_json = hf['config'].attrs['config_json']
            from seismic_twin.models import ProjectConfig
            config = ProjectConfig.model_validate_json(config_json)

        # Load ground motion
        ground_motion = hf['ground_motion/acceleration'][:]
        dt = hf['ground_motion'].attrs['dt']

        # Load building matrices
        building_params = {
            'M': hf['building/M'][:],
            'K': hf['building/K'][:],
            'C': hf['building/C'][:],
            'n_dof': hf['building'].attrs['n_dof'],
        }

        # Load results
        results = cls._load_results_recursive(hf['results'])

        return {
            'config': config,
            'ground_motion': ground_motion,
            'dt': dt,
            'building_params': building_params,
            'results': results,
            'metadata': dict(hf['metadata'].attrs),
        }

@classmethod
def _load_results_recursive(cls, group: h5py.Group) -> Dict:
    data = {}
    # Load datasets
    for key in group.keys():
        if isinstance(group[key], h5py.Dataset):
            data[key] = group[key][:]
        else:
            data[key] = cls._load_results_recursive(group[key])
    # Load attributes
    for key, val in group.attrs.items():
        data[key] = val
    return data
```

### 5. Add convenience functions

```python
def save_quick(filename: str, **kwargs) -> None:
    """Quick save with minimal arguments."""
    archive = ProjectArchive()
    archive.save(filename, **kwargs)

def load_quick(filename: str) -> Dict:
    """Quick load returning dict."""
    return ProjectArchive.load(filename)

def list_archive_contents(filename: str) -> Dict:
    """List contents without loading data."""
    with h5py.File(filename, 'r') as hf:
        return _get_structure(hf)

def _get_structure(group, prefix='') -> Dict:
    """Recursively get HDF5 structure."""
    structure = {}
    for key in group.keys():
        path = f"{prefix}/{key}" if prefix else key
        if isinstance(group[key], h5py.Dataset):
            structure[path] = {
                'type': 'dataset',
                'shape': group[key].shape,
                'dtype': str(group[key].dtype),
            }
        else:
            structure.update(_get_structure(group[key], path))
    return structure
```

### 6. Add YAML config export

```python
def export_config_yaml(filename: str, output_path: str) -> None:
    """Export just the config from archive to YAML file."""
    data = ProjectArchive.load(filename)
    if data['config'] is not None:
        import yaml
        with open(output_path, 'w') as f:
            yaml.dump(data['config'].model_dump(), f, default_flow_style=False)
```

### 7. Add tests

- Test save/load round-trip
- Test compression is applied
- Test version warning
- Test nested results structure
- Test config serialization

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/io/__init__.py` | Create |
| `src/seismic_twin/io/storage.py` | Create |
| `tests/test_storage.py` | Create |
| `pyproject.toml` | Add h5py dependency |

## Dependencies

- `h5py>=3.0`
- `pyyaml` (for YAML export)

## Success Criteria

- [ ] Can save complete project to HDF5
- [ ] Can load project and reconstruct all data
- [ ] Compression reduces file size
- [ ] Version checking warns on mismatch
- [ ] Nested results handled correctly
- [ ] All tests pass

## Example Usage

```python
from seismic_twin.io import ProjectArchive

# Save analysis
archive = ProjectArchive()
archive.save(
    "my_analysis.h5",
    building=building,
    ground_motion=ground_acc,
    dt=0.01,
    results={
        'initial': {'displacement': u_initial},
        'calibrated': {'displacement': u_calibrated, 'nrmse': 0.05},
    },
    config=project_config,
    metadata={'description': 'Christchurch scenario'}
)

# Load later
data = ProjectArchive.load("my_analysis.h5")
print(f"Project: {data['config'].project_name}")
print(f"Max displacement: {data['results']['calibrated']['displacement'].max()}")
```
