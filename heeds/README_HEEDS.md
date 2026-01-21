# HEEDS MDO Integration Guide

This guide explains how to set up Simcenter HEEDS to optimize seismic building parameters using this simulation wrapper.

## Overview

The integration allows HEEDS to:
- **Vary building parameters**: n_stories, mass, stiffness, damping, story height
- **Run seismic simulations**: Using pre-defined ground motion
- **Evaluate responses**: max drift, roof displacement, floor acceleration, periods

## Files

| File | Description |
|------|-------------|
| `run_simulation.py` | Main wrapper script executed by HEEDS |
| `input_template.json` | Input template with variable placeholders |
| `output_template.json` | Output format specification |
| `ground_motion.json` | Pre-defined seismic excitation |
| `test_wrapper.py` | Test script for validation |

## Quick Start

### 1. Test the Wrapper Locally

Before configuring HEEDS, verify the wrapper works:

```bash
cd heeds/
python test_wrapper.py
```

Or run a single simulation:

```bash
python run_simulation.py --input sample_input.json --output test_output.json
```

### 2. Create HEEDS Project

1. Open HEEDS and create a new project
2. Set the working directory to this `heeds/` folder

### 3. Add Text File Portal

1. **Analysis** → **Add Analysis** → **Text File**
2. Configure:
   - **Name**: SeismicSimulation
   - **Working Directory**: Path to `heeds/` folder
   - **Execution Command**:
     ```
     python run_simulation.py --input input.json --output output.json
     ```

### 4. Tag Input Variables

Open `input_template.json` in HEEDS Tagger:

1. Select numeric values and create variables:

| Variable | Type | Lower Bound | Upper Bound | Default |
|----------|------|-------------|-------------|---------|
| `n_stories` | Integer | 3 | 10 | 5 |
| `mass_per_floor` | Real | 50000 | 500000 | 100000 |
| `stiffness_per_story` | Real | 5e7 | 5e8 | 1e8 |
| `damping_ratio` | Real | 0.02 | 0.10 | 0.05 |
| `story_height` | Real | 3.0 | 4.0 | 3.5 |

2. The tagged file format uses `<variable_name>` placeholders:
   ```json
   "n_stories": <n_stories>
   ```

### 5. Tag Output Responses

Open `output_template.json` in HEEDS Tagger:

| Response | Type | Objective |
|----------|------|-----------|
| `max_drift` | Real | Minimize |
| `max_roof_disp` | Real | Minimize |
| `max_floor_acc` | Real | Minimize |
| `T1` | Real | Info |
| `T2` | Real | Info |
| `T3` | Real | Info |
| `total_mass` | Real | Constraint |
| `total_stiffness` | Real | Info |
| `status` | String | Info |

### 6. Define Optimization Study

#### Single Objective Optimization

Minimize inter-story drift:

1. **Objective**: Minimize `max_drift`
2. **Constraints**:
   - `max_floor_acc <= 2.0` (2g maximum)
   - `total_mass <= 1000000` (1000 tons)
3. **Method**: SHERPA (recommended)
4. **Evaluations**: 100-500

#### Multi-Objective Optimization

Balance drift and acceleration:

1. **Objectives**:
   - Minimize `max_drift`
   - Minimize `max_floor_acc`
2. **Constraints**:
   - `total_mass <= 1000000`
3. **Method**: SHERPA with Pareto
4. **Evaluations**: 200-1000

#### Design of Experiments (DOE)

Explore design space:

1. **Method**: Latin Hypercube or Full Factorial
2. **Samples**: 50-200
3. **Post-process**: Sensitivity analysis

## Input Variables

### Building Parameters

| Variable | Description | Units | Typical Range |
|----------|-------------|-------|---------------|
| `n_stories` | Number of stories | - | 3-20 |
| `mass_per_floor` | Floor mass | kg | 50,000-500,000 |
| `stiffness_per_story` | Lateral stiffness | N/m | 1e7-1e9 |
| `damping_ratio` | Modal damping | - | 0.01-0.15 |
| `story_height` | Story height | m | 2.5-5.0 |

### Fixed Parameters

The following are fixed in `ground_motion.json`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `target_pga` | 0.3 g | Peak ground acceleration |
| `duration` | 30 s | Ground motion duration |
| `predominant_freq` | 2.0 Hz | Dominant frequency |
| `seed` | 42 | Random seed for reproducibility |

To change these, edit `ground_motion.json` directly.

## Output Responses

| Response | Description | Units | Objective |
|----------|-------------|-------|-----------|
| `max_drift` | Maximum inter-story drift ratio | - | Minimize (< 0.02) |
| `max_roof_disp` | Maximum roof displacement | m | Minimize |
| `max_floor_acc` | Maximum floor acceleration | g | Minimize (< 2.0) |
| `T1` | Fundamental period | s | Monitor |
| `T2` | Second mode period | s | Monitor |
| `T3` | Third mode period | s | Monitor |
| `total_mass` | Building total mass | kg | Constraint |
| `total_stiffness` | Total lateral stiffness | N/m | Monitor |

### Design Criteria

Typical seismic design limits:

- **Life Safety**: `max_drift < 0.02` (2%)
- **Immediate Occupancy**: `max_drift < 0.01` (1%)
- **Operational**: `max_drift < 0.005` (0.5%)
- **Acceleration**: `max_floor_acc < 0.5g` (comfort), `< 2.0g` (damage)

## Custom Ground Motion

To use a specific earthquake record:

1. Edit `ground_motion.json`:
   ```json
   {
     "source": "timeseries",
     "dt": 0.01,
     "time": [0.0, 0.01, 0.02, ...],
     "acceleration": [0.0, 0.001, -0.002, ...]
   }
   ```

2. Or generate from parameters:
   ```json
   {
     "source": "synthetic",
     "target_pga": 0.4,
     "duration": 40.0,
     "predominant_freq": 1.5,
     "seed": 123
   }
   ```

## Troubleshooting

### Simulation Fails

Check `output.json` for error messages:
```json
{
  "status": "error: <message>"
}
```

Common issues:
- Invalid parameter ranges (negative values)
- Missing Python dependencies
- Ground motion file not found

### Run Test Script

```bash
python test_wrapper.py
```

This validates:
- Basic simulation runs
- Parameter variations work
- Results are physically reasonable

### Check Python Environment

Ensure seismic_twin is installed:
```bash
pip install -e /path/to/seismic-building-simulation
```

## Advanced Configuration

### Distributed Execution

For cluster execution, HEEDS can run simulations on remote nodes:

1. Configure Job Controller (PBS, SLURM, etc.)
2. Set up Python environment on compute nodes
3. Use shared filesystem for input/output files

### Batch Processing

Run multiple designs without HEEDS:

```python
import json
from run_simulation import run_simulation
from pathlib import Path

designs = [
    {"n_stories": 5, "mass_per_floor": 100000, ...},
    {"n_stories": 7, "mass_per_floor": 120000, ...},
]

for i, design in enumerate(designs):
    input_data = {
        "building": design,
        "ground_motion": {"source": "file", "file_path": "ground_motion.json"}
    }
    result = run_simulation(input_data, Path("."))
    print(f"Design {i}: max_drift={result['max_drift']:.4f}")
```

## References

- [Simcenter HEEDS Documentation](https://plm.sw.siemens.com/en-US/simcenter/integration-solutions/heeds/)
- [HEEDS Getting Started Guide](https://www.egr.msu.edu/classes/me475/averillr/Lab1/HEEDS.pdf)
- [ASCE 7 Seismic Design Criteria](https://www.asce.org/publications-and-news/asce-7)
