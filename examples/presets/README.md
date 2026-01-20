# Seismic Analysis Preset Scenarios

This directory contains example preset files that combine building configurations and ground motion parameters for common seismic analysis scenarios. These files can be imported into the dashboard or used as templates for custom scenarios.

## Scenario Files

| File | Building Type | Ground Motion | Use Case |
|------|--------------|---------------|----------|
| `scenario_1_residential_moderate.json` | 3-story wood frame | M5.5-6.0 at 20km | Typical residential assessment |
| `scenario_2_office_design_level.json` | 8-story RC frame | Design Basis Earthquake | Code compliance evaluation |
| `scenario_3_hospital_mce.json` | 5-story steel braced | Maximum Considered Earthquake | Critical facility evaluation |
| `scenario_4_historic_near_fault.json` | 4-story URM masonry | Near-fault pulse | Heritage building retrofit |
| `scenario_5_highrise_soft_soil.json` | 25-story steel tower | Soft soil amplification | Soil-structure interaction |

## Scenario Descriptions

### Scenario 1: Residential Building - Moderate Earthquake

A typical 3-story wood frame residential building common in suburban California, subjected to a moderate earthquake on stiff soil. This represents a common assessment scenario for residential structures.

- **Building**: Light wood frame with 25,000 kg/floor, 12 MN/m stiffness
- **Ground Motion**: PGA 0.15g, 18s duration, 3.5 Hz predominant frequency

### Scenario 2: Office Building - Design Basis Earthquake

A modern 8-story reinforced concrete office building evaluated under code design-level ground motion. This scenario is typical for building code compliance verification.

- **Building**: RC moment frame with 180,000 kg/floor, 120 MN/m stiffness
- **Ground Motion**: PGA 0.30g, 30s duration, 2.0 Hz predominant frequency

### Scenario 3: Hospital - Maximum Considered Earthquake

A critical facility (hospital) evaluation under maximum considered earthquake intensity. Essential facilities must remain operational after major seismic events.

- **Building**: Steel braced frame with 250,000 kg/floor, 200 MN/m stiffness, 3% damping
- **Ground Motion**: PGA 0.50g, 45s duration, 1.8 Hz predominant frequency

### Scenario 4: Historic Building - Near-Fault Pulse

A vulnerable unreinforced masonry historic building subjected to near-fault ground motion with forward directivity effects. Critical for heritage building assessment and retrofit planning.

- **Building**: URM brick masonry with 220,000 kg/floor, 45 MN/m stiffness, 8% damping
- **Ground Motion**: PGA 0.55g, 12s duration (impulsive), 1.2 Hz predominant frequency

### Scenario 5: High-Rise Tower - Soft Soil Amplification

A tall steel moment frame building on a soft soil site experiencing site amplification effects. Important for understanding soil-structure interaction and long-period structural response.

- **Building**: Steel moment frame with 95,000 kg/floor, 140 MN/m stiffness, 2% damping
- **Ground Motion**: PGA 0.35g, 55s duration, 0.8 Hz predominant frequency (long-period)

## JSON File Format

Each scenario file follows this structure:

```json
{
  "name": "Scenario Name",
  "description": "Overall scenario description",
  "building": {
    "name": "Building Name",
    "description": "Building description",
    "n_stories": 5,
    "mass_per_floor": 100000,
    "stiffness_per_story": 100000000,
    "damping_ratio": 0.05,
    "story_height": 3.5
  },
  "ground_motion": {
    "name": "Ground Motion Name",
    "description": "Ground motion description",
    "target_pga": 0.3,
    "duration": 30,
    "predominant_freq": 2.0,
    "bandwidth": 1.5
  }
}
```

### Parameter Reference

**Building Parameters:**
- `n_stories`: Number of floors (integer)
- `mass_per_floor`: Lumped mass per floor in kg
- `stiffness_per_story`: Lateral stiffness per story in N/m
- `damping_ratio`: Modal damping ratio (e.g., 0.05 = 5%)
- `story_height`: Height of each story in meters

**Ground Motion Parameters:**
- `target_pga`: Peak ground acceleration in g units
- `duration`: Total duration in seconds
- `predominant_freq`: Central frequency of motion in Hz
- `bandwidth`: Frequency bandwidth in Hz

## Usage

### In the Dashboard

1. Navigate to the Building or Ground Motion configuration page
2. Click "Import JSON" button
3. Select the scenario file or a portion of it
4. Parameters will be loaded into the form fields

**Note**: The dashboard import expects either the top-level scenario format (with `building` and `ground_motion` objects) or a flat format with just the parameters. For building configuration, the importer looks for `n_stories`, `mass_per_floor`, `stiffness_per_story`, `damping_ratio`, and `story_height` fields.

### Programmatic Usage

```python
import json
from seismic_twin import MDOFShearBuilding, generate_synthetic_ground_motion
import numpy as np

# Load scenario
with open("examples/presets/scenario_2_office_design_level.json") as f:
    scenario = json.load(f)

# Create building model
bldg = scenario["building"]
model = MDOFShearBuilding(
    masses=np.full(bldg["n_stories"], bldg["mass_per_floor"]),
    stiffnesses=np.full(bldg["n_stories"], bldg["stiffness_per_story"]),
    damping_ratio=bldg["damping_ratio"],
    story_heights=np.full(bldg["n_stories"], bldg["story_height"]),
)

# Generate ground motion
gm = scenario["ground_motion"]
time, accel = generate_synthetic_ground_motion(
    duration=gm["duration"],
    dt=0.01,
    target_pga=gm["target_pga"],
    predominant_freq=gm["predominant_freq"],
    bandwidth=gm["bandwidth"],
)
```

## Creating Custom Scenarios

To create your own scenario:

1. Copy one of the existing files as a template
2. Modify the building and ground motion parameters
3. Update the name and description fields
4. Save with a descriptive filename

For building-only or ground-motion-only presets, you can use a simplified format containing just the relevant parameters (see CLAUDE.md for format details).
