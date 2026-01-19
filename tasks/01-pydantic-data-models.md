# Task 01: Pydantic Data Models

## Priority: HIGH
## Estimated Effort: 1-2 days

## Problem Statement

The current codebase has:
- No formal data model layer for validation and serialization
- Implicit assumptions about input data that can cause hard-to-debug errors
- No standardized configuration format for reproducibility
- Poor IDE autocomplete support due to untyped configurations

## Implementation Plan

### 1. Create datamodels module
Create `src/seismic_twin/models/datamodels.py` with Pydantic models.

### 2. Implement Configuration Classes

#### BuildingConfig
```python
class BuildingConfig(BaseModel):
    n_stories: int = Field(..., ge=1, le=100)
    masses: List[float]  # [kg]
    stiffnesses: List[float]  # [N/m]
    story_heights: List[float]  # [m]
    damping_ratio: float = Field(0.05, ge=0.01, le=0.20)
    name: Optional[str] = None
```

Validators needed:
- `masses`, `stiffnesses`, `story_heights` lengths must equal `n_stories`
- All values in `masses` and `stiffnesses` must be positive

#### GroundMotionConfig
```python
class GroundMotionConfig(BaseModel):
    duration: float = Field(..., gt=0)  # [s]
    dt: float = Field(..., gt=0, le=0.1)  # [s]
    target_pga: float = Field(..., gt=0)  # [g]
    predominant_freq: float = Field(2.5, gt=0)  # [Hz]
    magnitude: Optional[float] = Field(None, ge=4.0, le=9.0)
    epicenter: Optional[Tuple[float, float]] = None
    rupture_id: Optional[str] = None
```

#### SensorConfig
```python
class SensorConfig(BaseModel):
    sensor_name: str
    floor_index: int = Field(..., ge=0)
    measurement_type: str  # displacement|velocity|acceleration
    uncertainty_std: Optional[float] = Field(None, ge=0)
```

#### CalibrationConfig
```python
class CalibrationConfig(BaseModel):
    max_iterations: int = Field(20, gt=0)
    tolerance: float = Field(0.01, gt=0)
    stiffness_bounds: Tuple[float, float] = (0.7, 1.3)
    damping_bounds: Tuple[float, float] = (0.02, 0.15)
    optimization_method: str = "grid_search"  # grid_search|nelder_mead|bayesian
```

#### ProjectConfig
```python
class ProjectConfig(BaseModel):
    project_name: str
    building: BuildingConfig
    ground_motion: GroundMotionConfig
    sensors: List[SensorConfig]
    calibration: CalibrationConfig
```

### 3. Add YAML/JSON serialization support
- Implement `to_yaml()` and `from_yaml()` class methods
- Implement `to_json()` and `from_json()` class methods

### 4. Update existing modules to use configs
- Modify `MDOFShearBuilding` to accept `BuildingConfig`
- Modify `generate_synthetic_ground_motion()` to accept `GroundMotionConfig`
- Modify `StructuralCalibration` to accept `CalibrationConfig`

### 5. Add tests
- Test validation (valid inputs pass, invalid inputs raise)
- Test serialization round-trip (YAML and JSON)
- Test integration with existing classes

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/models/__init__.py` | Create |
| `src/seismic_twin/models/datamodels.py` | Create |
| `tests/test_datamodels.py` | Create |
| `src/seismic_twin/building/mdof_model.py` | Modify |
| `pyproject.toml` | Add pydantic dependency |

## Dependencies

- `pydantic>=2.0`
- `pyyaml` (for YAML serialization)

## Success Criteria

- [ ] All Pydantic models implemented with validators
- [ ] YAML/JSON serialization works correctly
- [ ] Invalid inputs produce clear error messages
- [ ] Existing functionality preserved (backward compatible)
- [ ] All new tests pass
- [ ] IDE autocomplete works for config objects
