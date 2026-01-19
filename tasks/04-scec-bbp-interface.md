# Task 04: SCEC Broadband Platform Interface

## Priority: MEDIUM
## Estimated Effort: 3-4 days

## Problem Statement

The current package:
- Only has simple synthetic ground motion generation
- Cannot produce physics-based ground motions from rupture scenarios
- Lacks support for site-specific velocity models
- Cannot simulate specific earthquake scenarios with realistic waveforms

## Implementation Plan

### 1. Create BBP interface module
Create `src/seismic_twin/ground_motion/scec_bbp.py`

### 2. Implement SCECBroadbandPlatform class

```python
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

class SCECBroadbandPlatform:
    """Interface to SCEC Broadband Platform for physics-based ground motion."""

    def __init__(self, bbp_path: Optional[str] = None):
        """
        Parameters:
        -----------
        bbp_path : str, optional
            Path to BBP installation. If None, looks for BBP_DIR env var.
        """
        self.bbp_path = bbp_path or os.environ.get('BBP_DIR')
        if self.bbp_path is None:
            raise RuntimeError("BBP not found. Set BBP_DIR or provide path.")

        self.bbp_run = Path(self.bbp_path) / "comps" / "run_bbp.py"

    def check_installation(self) -> bool:
        """Verify BBP is correctly installed."""
        pass

    def list_velocity_models(self) -> List[str]:
        """List available velocity models."""
        pass

    def list_methods(self) -> List[str]:
        """List available simulation methods."""
        return ["gp", "exsim", "ucsb", "sdsu", "song"]
```

### 3. Implement scenario simulation

```python
def run_scenario(
    self,
    event_name: str,
    rupture_file: str,
    velocity_model: str,
    stations: List[Dict],
    method: str = "gp",
    output_dir: Optional[str] = None,
) -> Dict:
    """
    Run BBP scenario simulation.

    Parameters:
    -----------
    event_name : str
        Name for this scenario
    rupture_file : str
        Path to SRF (Standard Rupture Format) file
    velocity_model : str
        Velocity model name (e.g., "labasin", "nocal")
    stations : List[Dict]
        List of station dicts with keys: name, lon, lat
    method : str
        Simulation method: "gp", "exsim", "ucsb", etc.
    output_dir : str, optional
        Output directory (temp dir if None)

    Returns:
    --------
    Dict with:
        - seismograms: dict mapping station -> (time, acc_e, acc_n, acc_z)
        - stations: station metadata
        - run_dir: output directory path
        - method: method used
    """
    pass
```

### 4. Implement input file generators

```python
def create_stations_file(
    self,
    stations: List[Dict],
    output_path: str
) -> str:
    """
    Create BBP-format station list file.

    Format: lon lat sta_name
    """
    pass

def create_simple_source(
    self,
    magnitude: float,
    lon: float,
    lat: float,
    depth_km: float,
    strike: float,
    dip: float,
    rake: float,
    output_path: str,
) -> str:
    """
    Create simple point source file for BBP.
    """
    pass
```

### 5. Implement output parsers

```python
def _parse_bbp_output(self, output_dir: str) -> Dict:
    """Parse BBP acceleration output files."""
    seismograms = {}

    # BBP outputs .acc.bbp files with format:
    # time acc_north acc_east acc_up
    for acc_file in Path(output_dir).glob("*.acc.bbp"):
        station_name = acc_file.stem.replace(".acc", "")
        data = np.loadtxt(acc_file, comments="#")
        seismograms[station_name] = {
            'time': data[:, 0],
            'acc_n': data[:, 1],  # m/s²
            'acc_e': data[:, 2],
            'acc_z': data[:, 3],
        }

    return seismograms
```

### 6. Add validation method

```python
def run_validation(
    self,
    event_id: str,
    recorded_data: Dict,
    method: str = "gp",
) -> Dict:
    """
    Run BBP validation against recorded data.

    Compares simulated vs recorded using:
    - Response spectra
    - PGA/PGV comparison
    - Goodness-of-fit scores
    """
    pass
```

### 7. Create fallback for non-BBP systems

```python
class BBPNotAvailable:
    """Stub when BBP is not installed."""

    def __init__(self):
        pass

    def __getattr__(self, name):
        raise RuntimeError(
            "SCEC BBP not installed. Install from: "
            "https://github.com/SCECcode/bbp"
        )

# In module init:
try:
    bbp = SCECBroadbandPlatform()
except RuntimeError:
    bbp = BBPNotAvailable()
```

### 8. Add tests

- Test with mock BBP installation
- Test input file generation
- Test output parsing
- Test graceful degradation when BBP unavailable

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/ground_motion/scec_bbp.py` | Create |
| `src/seismic_twin/ground_motion/__init__.py` | Modify (export BBP) |
| `tests/test_scec_bbp.py` | Create |
| `tests/fixtures/sample_bbp_output/` | Create (test data) |

## Dependencies

- SCEC BBP installation (external, optional)
- No Python dependencies beyond standard library

## Success Criteria

- [ ] Can detect BBP installation status
- [ ] Can run scenario simulations when BBP available
- [ ] Input file generators produce valid BBP format
- [ ] Output parser correctly reads acceleration files
- [ ] Clear error message when BBP not available
- [ ] All tests pass

## Example Usage

```python
from seismic_twin.ground_motion import SCECBroadbandPlatform

bbp = SCECBroadbandPlatform("/path/to/bbp")

# Define stations
stations = [
    {"name": "STA1", "lon": -118.2, "lat": 34.1},
    {"name": "STA2", "lon": -118.3, "lat": 34.2},
]

# Run simulation
results = bbp.run_scenario(
    event_name="scenario_m7",
    rupture_file="rupture.srf",
    velocity_model="labasin",
    stations=stations,
    method="gp"
)

# Use in building simulation
for sta_name, data in results['seismograms'].items():
    result = newmark_beta(model, data['acc_e'], dt=data['time'][1]-data['time'][0])
```
