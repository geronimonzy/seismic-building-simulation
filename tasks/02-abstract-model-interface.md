# Task 02: Abstract Model Interface

## Priority: HIGH
## Estimated Effort: 2-3 days

## Problem Statement

The current implementation:
- Has tight coupling between the MDOF shear building model and other modules
- Cannot easily swap different structural model types (3D, nonlinear, etc.)
- Makes benchmarking different models difficult
- Lacks a plugin/extension system for custom models

## Implementation Plan

### 1. Create abstract base class
Create `src/seismic_twin/building/base.py` with `StructuralModel` ABC.

### 2. Define Abstract Interface

```python
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

    # Convenience properties
    @property
    def M(self) -> np.ndarray:
        return self.get_mass_matrix()

    @property
    def K(self) -> np.ndarray:
        return self.get_stiffness_matrix()

    @property
    def C(self) -> np.ndarray:
        return self.get_damping_matrix()

    @property
    def n_dof(self) -> int:
        return self.get_n_dof()
```

### 3. Refactor MDOFShearBuilding

Update `MDOFShearBuilding` to inherit from `StructuralModel`:

```python
class MDOFShearBuilding(StructuralModel):
    """MDOF shear building implementing the abstract interface."""

    def get_influence_vector(self, direction: str = 'x') -> np.ndarray:
        """For MDOF shear: excitation in lateral direction."""
        if direction != 'x':
            raise ValueError("MDOF shear only supports 'x' direction")
        return np.ones(self.n_dof)

    def get_n_dof(self) -> int:
        return self._n_dof

    def update_parameter(self, param_name: str, value: float) -> None:
        """Update model parameter and rebuild matrices."""
        if param_name == 'stiffness_factor':
            self._stiffnesses = self._base_stiffnesses * value
            self._rebuild_matrices()
        elif param_name == 'damping_ratio':
            self._damping_ratio = value
            self._rebuild_matrices()
        else:
            raise ValueError(f"Unknown parameter: {param_name}")

    def copy(self) -> 'MDOFShearBuilding':
        """Create independent copy."""
        return MDOFShearBuilding(
            masses=self._masses.copy(),
            stiffnesses=self._stiffnesses.copy(),
            damping_ratio=self._damping_ratio,
            story_heights=self._story_heights.copy()
        )
```

### 4. Update dependent modules

Modify modules to accept `StructuralModel` instead of `MDOFShearBuilding`:
- `analysis/integration.py` - Accept any StructuralModel
- `calibration/calibrator.py` - Accept any StructuralModel
- `uncertainty/monte_carlo.py` - Accept any StructuralModel

### 5. Add type hints

Use Protocol or ABC type hints in function signatures:
```python
def newmark_beta(
    model: StructuralModel,
    ground_acceleration: np.ndarray,
    dt: float,
    ...
) -> IntegrationResult:
```

### 6. Add tests

- Test ABC interface compliance for MDOFShearBuilding
- Test that modules work with ABC type
- Test copy() creates independent instance
- Test update_parameter() correctly modifies model

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/building/base.py` | Create |
| `src/seismic_twin/building/__init__.py` | Modify (export ABC) |
| `src/seismic_twin/building/mdof_model.py` | Modify (inherit ABC) |
| `src/seismic_twin/analysis/integration.py` | Modify (type hints) |
| `src/seismic_twin/calibration/calibrator.py` | Modify (type hints) |
| `src/seismic_twin/uncertainty/monte_carlo.py` | Modify (type hints) |
| `tests/test_base_model.py` | Create |

## Dependencies

None (uses standard library `abc`)

## Success Criteria

- [ ] `StructuralModel` ABC implemented with all required methods
- [ ] `MDOFShearBuilding` correctly implements the interface
- [ ] All existing tests still pass
- [ ] New models can be created by inheriting from `StructuralModel`
- [ ] Type hints allow IDE to recognize model interface
- [ ] `copy()` creates truly independent instances

## Future Extensions Enabled

This task enables:
- 3D building models
- Lumped mass vs distributed models
- Nonlinear models (Task 14)
- Easy benchmarking between model types
