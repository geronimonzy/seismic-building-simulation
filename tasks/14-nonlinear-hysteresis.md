# Task 14: Nonlinear Hysteretic Models

## Priority: MEDIUM
## Estimated Effort: 5-7 days

## Problem Statement

The current implementation:
- Only supports linear elastic behavior
- Cannot model yielding/damage during strong earthquakes
- Does not capture energy dissipation through hysteresis
- Limited for assessing structural damage or collapse risk

## Implementation Plan

### 1. Create nonlinearity module
Create `src/seismic_twin/nonlinearity/` directory with:

```
nonlinearity/
├── __init__.py
├── hysteresis.py      # Hysteretic element models
├── materials.py       # Material stress-strain relations
└── integration.py     # Nonlinear time integration
```

### 2. Implement HystereticElement base class

```python
# src/seismic_twin/nonlinearity/hysteresis.py

from abc import ABC, abstractmethod
import numpy as np
from typing import Tuple
from dataclasses import dataclass

@dataclass
class HystereticState:
    """State of a hysteretic element."""
    deformation: float
    force: float
    tangent_stiffness: float
    plastic_deformation: float = 0.0
    damage_index: float = 0.0

class HystereticElement(ABC):
    """Abstract base class for hysteretic spring elements."""

    @abstractmethod
    def compute_force(
        self,
        deformation: float,
        deformation_prev: float,
    ) -> Tuple[float, float]:
        """
        Compute restoring force given current and previous deformation.

        Returns:
            force: Restoring force
            tangent_stiffness: Tangent stiffness for Newton iteration
        """
        pass

    @abstractmethod
    def get_state(self) -> HystereticState:
        """Return current state of the element."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset element to initial state."""
        pass

    @abstractmethod
    def copy(self) -> 'HystereticElement':
        """Create independent copy."""
        pass
```

### 3. Implement Bilinear Hysteresis model

```python
class BilinearHysteresis(HystereticElement):
    """
    Bilinear elasto-plastic hysteresis model.

    Backbone:
        - Elastic: F = k_elastic * u for |u| < u_yield
        - Plastic: F = F_yield + k_plastic * (u - u_yield)

    Unloading follows elastic stiffness.
    """

    def __init__(
        self,
        k_elastic: float,
        k_plastic: float,
        yield_force: float,
    ):
        """
        Parameters:
        -----------
        k_elastic : float
            Initial (elastic) stiffness [N/m]
        k_plastic : float
            Post-yield stiffness [N/m], typically 0.02-0.10 * k_elastic
        yield_force : float
            Yield force [N]
        """
        self.k_elastic = k_elastic
        self.k_plastic = k_plastic
        self.yield_force = yield_force
        self.yield_disp = yield_force / k_elastic

        # State variables
        self._plastic_disp = 0.0
        self._force_prev = 0.0
        self._disp_prev = 0.0
        self._loading_direction = 0  # +1 or -1 or 0

    def compute_force(
        self,
        deformation: float,
        deformation_prev: float,
    ) -> Tuple[float, float]:
        """Compute force using kinematic hardening rules."""
        delta_disp = deformation - deformation_prev

        # Trial elastic response
        trial_force = self._force_prev + self.k_elastic * delta_disp

        # Check yield condition
        if abs(trial_force) <= self.yield_force:
            # Still elastic
            force = trial_force
            tangent = self.k_elastic
        else:
            # Yielding
            sign = np.sign(trial_force)
            force = sign * self.yield_force + self.k_plastic * (
                deformation - sign * self.yield_disp - self._plastic_disp
            )
            tangent = self.k_plastic

            # Update plastic deformation
            self._plastic_disp += (abs(trial_force) - self.yield_force) / self.k_elastic * sign

        # Update state
        self._force_prev = force
        self._disp_prev = deformation

        return force, tangent

    def get_state(self) -> HystereticState:
        return HystereticState(
            deformation=self._disp_prev,
            force=self._force_prev,
            tangent_stiffness=self.k_elastic,  # Simplified
            plastic_deformation=self._plastic_disp,
        )

    def reset(self) -> None:
        self._plastic_disp = 0.0
        self._force_prev = 0.0
        self._disp_prev = 0.0

    def copy(self) -> 'BilinearHysteresis':
        elem = BilinearHysteresis(
            self.k_elastic, self.k_plastic, self.yield_force
        )
        elem._plastic_disp = self._plastic_disp
        elem._force_prev = self._force_prev
        elem._disp_prev = self._disp_prev
        return elem
```

### 4. Implement Bouc-Wen model (smooth hysteresis)

```python
class BoucWenHysteresis(HystereticElement):
    """
    Bouc-Wen smooth hysteresis model.

    Equation:
        F = α * k * u + (1-α) * k * z

    where z is the hysteretic variable governed by:
        dz/dt = (A - (β*|z|^n + γ*z*|z|^(n-1)) * sign(du/dt*z)) * du/dt

    Parameters:
        A, β, γ: Control shape of hysteresis loop
        n: Sharpness of yield transition (n=1: smooth, n→∞: sharp)
        α: Post-yield stiffness ratio
    """

    def __init__(
        self,
        k: float,
        alpha: float = 0.05,
        A: float = 1.0,
        beta: float = 0.5,
        gamma: float = 0.5,
        n: float = 2.0,
        yield_disp: float = 0.01,
    ):
        self.k = k
        self.alpha = alpha
        self.A = A
        self.beta = beta
        self.gamma = gamma
        self.n = n
        self.yield_disp = yield_disp

        # State
        self._z = 0.0  # Hysteretic variable
        self._disp_prev = 0.0

    def compute_force(
        self,
        deformation: float,
        deformation_prev: float,
    ) -> Tuple[float, float]:
        """Compute force using Bouc-Wen model."""
        du = deformation - deformation_prev

        # Normalize by yield displacement
        u_norm = deformation / self.yield_disp

        # Update hysteretic variable z
        z_abs_n = abs(self._z) ** self.n
        dz = (self.A - (self.beta * z_abs_n +
              self.gamma * self._z * abs(self._z) ** (self.n - 1)) *
              np.sign(du * self._z)) * du / self.yield_disp

        self._z += dz

        # Compute force
        force = self.k * (self.alpha * deformation +
                         (1 - self.alpha) * self.yield_disp * self._z)

        # Approximate tangent stiffness
        tangent = self.k * self.alpha

        self._disp_prev = deformation
        return force, tangent

    def get_state(self) -> HystereticState:
        return HystereticState(
            deformation=self._disp_prev,
            force=self.k * (self.alpha * self._disp_prev +
                          (1 - self.alpha) * self.yield_disp * self._z),
            tangent_stiffness=self.k * self.alpha,
            plastic_deformation=self._z * self.yield_disp,
        )

    def reset(self) -> None:
        self._z = 0.0
        self._disp_prev = 0.0

    def copy(self) -> 'BoucWenHysteresis':
        elem = BoucWenHysteresis(
            self.k, self.alpha, self.A, self.beta, self.gamma, self.n, self.yield_disp
        )
        elem._z = self._z
        elem._disp_prev = self._disp_prev
        return elem
```

### 5. Implement MDOFNonlinearShearBuilding

```python
# src/seismic_twin/building/nonlinear_mdof.py

class MDOFNonlinearShearBuilding(StructuralModel):
    """
    MDOF building with nonlinear hysteretic story springs.
    """

    def __init__(
        self,
        masses: List[float],
        story_heights: List[float],
        hysteretic_elements: List[HystereticElement],
        damping_ratio: float = 0.05,
    ):
        """
        Parameters:
        -----------
        masses : List[float]
            Floor masses [kg]
        story_heights : List[float]
            Story heights [m]
        hysteretic_elements : List[HystereticElement]
            One hysteretic element per story
        damping_ratio : float
            Viscous damping ratio (added to hysteretic damping)
        """
        self.masses = np.array(masses)
        self.story_heights = np.array(story_heights)
        self.hysteretic_elements = hysteretic_elements
        self.damping_ratio = damping_ratio
        self._n_dof = len(masses)

        assert len(hysteretic_elements) == self._n_dof

        # Build mass matrix (constant)
        self.M = np.diag(self.masses)

        # Initial stiffness for damping calculation
        self._K_initial = self._build_stiffness_matrix([
            elem.k_elastic if hasattr(elem, 'k_elastic') else elem.k
            for elem in hysteretic_elements
        ])

        # Rayleigh damping based on initial stiffness
        self.C = self._build_damping_matrix()

    def get_restoring_force(
        self,
        displacement: np.ndarray,
        displacement_prev: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute nonlinear restoring force and tangent stiffness.

        Returns:
            force: (n_dof,) restoring force vector
            K_tangent: (n_dof, n_dof) tangent stiffness matrix
        """
        # Inter-story drifts
        drift = np.zeros(self._n_dof)
        drift[0] = displacement[0]
        drift[1:] = displacement[1:] - displacement[:-1]

        drift_prev = np.zeros(self._n_dof)
        drift_prev[0] = displacement_prev[0]
        drift_prev[1:] = displacement_prev[1:] - displacement_prev[:-1]

        # Compute story forces
        story_forces = np.zeros(self._n_dof)
        story_tangents = np.zeros(self._n_dof)

        for i, elem in enumerate(self.hysteretic_elements):
            story_forces[i], story_tangents[i] = elem.compute_force(
                drift[i], drift_prev[i]
            )

        # Build restoring force vector
        force = np.zeros(self._n_dof)
        force[0] = story_forces[0] - story_forces[1] if self._n_dof > 1 else story_forces[0]
        for i in range(1, self._n_dof - 1):
            force[i] = story_forces[i] - story_forces[i + 1]
        if self._n_dof > 1:
            force[-1] = story_forces[-1]

        # Build tangent stiffness matrix
        K_tangent = self._build_stiffness_matrix(story_tangents)

        return force, K_tangent

    def _build_stiffness_matrix(self, stiffnesses: List[float]) -> np.ndarray:
        """Build stiffness matrix from story stiffnesses."""
        K = np.zeros((self._n_dof, self._n_dof))
        for i in range(self._n_dof):
            K[i, i] += stiffnesses[i]
            if i > 0:
                K[i, i] += stiffnesses[i-1] if i > 0 else 0
                K[i, i-1] = -stiffnesses[i]
                K[i-1, i] = -stiffnesses[i]
        return K

    # ... implement remaining StructuralModel interface methods ...
```

### 6. Implement nonlinear time integration

```python
# src/seismic_twin/nonlinearity/integration.py

def newmark_beta_nonlinear(
    model: 'MDOFNonlinearShearBuilding',
    ground_acceleration: np.ndarray,
    dt: float,
    gamma: float = 0.5,
    beta: float = 0.25,
    tol: float = 1e-6,
    max_iter: int = 20,
) -> 'NonlinearIntegrationResult':
    """
    Newmark-beta for nonlinear systems with Newton-Raphson iteration.

    Parameters:
    -----------
    model : MDOFNonlinearShearBuilding
        Nonlinear building model
    ground_acceleration : array
        Ground acceleration [m/s²]
    dt : float
        Time step [s]
    tol : float
        Newton-Raphson convergence tolerance
    max_iter : int
        Maximum Newton iterations per step

    Returns:
    --------
    NonlinearIntegrationResult with displacement, ductility, damage
    """
    n_dof = model.get_n_dof()
    n_steps = len(ground_acceleration)

    # Preallocate
    u = np.zeros((n_steps, n_dof))
    v = np.zeros((n_steps, n_dof))
    a = np.zeros((n_steps, n_dof))
    iterations = np.zeros(n_steps, dtype=int)

    M = model.M
    C = model.C

    # Newmark coefficients
    c0 = 1.0 / (beta * dt * dt)
    c1 = gamma / (beta * dt)
    c2 = 1.0 / (beta * dt)
    c3 = 1.0 / (2.0 * beta) - 1.0
    c4 = gamma / beta - 1.0
    c5 = dt * (gamma / (2.0 * beta) - 1.0)

    # Initial acceleration
    influence = np.ones(n_dof)
    F0 = -M @ influence * ground_acceleration[0]
    a[0] = np.linalg.solve(M, F0)

    # Time stepping with Newton-Raphson
    for i in range(1, n_steps):
        # Predictor (assume elastic)
        u_pred = u[i-1] + dt * v[i-1] + 0.5 * dt**2 * a[i-1]

        # External force
        F_ext = -M @ influence * ground_acceleration[i]

        # Newton-Raphson iteration
        u_iter = u_pred.copy()
        for k in range(max_iter):
            # Compute restoring force and tangent
            F_int, K_t = model.get_restoring_force(u_iter, u[i-1])

            # Effective quantities
            K_eff = K_t + c0 * M + c1 * C
            R = F_ext - F_int - C @ (c1 * (u_iter - u[i-1]) + c4 * v[i-1] + c5 * a[i-1]) \
                - M @ (c0 * (u_iter - u[i-1]) - c2 * v[i-1] - c3 * a[i-1])

            # Check convergence
            if np.linalg.norm(R) < tol:
                break

            # Newton update
            du = np.linalg.solve(K_eff, R)
            u_iter += du

        iterations[i] = k + 1
        u[i] = u_iter

        # Update velocity and acceleration
        a[i] = c0 * (u[i] - u[i-1]) - c2 * v[i-1] - c3 * a[i-1]
        v[i] = v[i-1] + dt * ((1 - gamma) * a[i-1] + gamma * a[i])

    return NonlinearIntegrationResult(
        displacement=u,
        velocity=v,
        acceleration=a,
        time=np.arange(n_steps) * dt,
        iterations=iterations,
        hysteretic_states=[elem.get_state() for elem in model.hysteretic_elements],
    )
```

### 7. Add tests

- Test bilinear hysteresis backbone
- Test Bouc-Wen smooth hysteresis
- Test energy dissipation calculation
- Test Newton-Raphson convergence
- Compare linear vs nonlinear response

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/nonlinearity/__init__.py` | Create |
| `src/seismic_twin/nonlinearity/hysteresis.py` | Create |
| `src/seismic_twin/nonlinearity/integration.py` | Create |
| `src/seismic_twin/building/nonlinear_mdof.py` | Create |
| `tests/test_nonlinear.py` | Create |

## Success Criteria

- [ ] Bilinear hysteresis model works correctly
- [ ] Bouc-Wen model produces smooth loops
- [ ] Nonlinear integration converges
- [ ] Energy dissipation tracked
- [ ] Results match expected behavior
- [ ] All tests pass
