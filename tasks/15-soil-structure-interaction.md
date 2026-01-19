# Task 15: Soil-Structure Interaction

## Priority: MEDIUM
## Estimated Effort: 4-6 days

## Problem Statement

The current implementation:
- Assumes fixed-base structures
- Ignores foundation compliance
- Does not account for soil damping
- May over/underestimate response for flexible soils

## Implementation Plan

### 1. Create SSI module
Create `src/seismic_twin/ssi/` directory with:

```
ssi/
├── __init__.py
├── foundation.py      # Foundation impedance models
├── soil_profiles.py   # Soil property definitions
└── ssi_model.py       # Combined SSI building model
```

### 2. Implement soil property classes

```python
# src/seismic_twin/ssi/soil_profiles.py

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class SoilLayer:
    """Single soil layer properties."""
    thickness: float      # [m]
    shear_velocity: float # Vs [m/s]
    density: float        # [kg/m³]
    damping: float        # Material damping ratio
    poisson_ratio: float = 0.33

    @property
    def shear_modulus(self) -> float:
        """Dynamic shear modulus G [Pa]."""
        return self.density * self.shear_velocity ** 2

    @property
    def youngs_modulus(self) -> float:
        """Young's modulus E [Pa]."""
        return 2 * self.shear_modulus * (1 + self.poisson_ratio)


class SoilProfile:
    """Multi-layer soil profile."""

    def __init__(self, layers: List[SoilLayer], water_table_depth: Optional[float] = None):
        """
        Parameters:
        -----------
        layers : List[SoilLayer]
            Soil layers from surface to bedrock
        water_table_depth : float, optional
            Depth to water table [m]
        """
        self.layers = layers
        self.water_table_depth = water_table_depth

    @property
    def total_depth(self) -> float:
        return sum(layer.thickness for layer in self.layers)

    def get_vs30(self) -> float:
        """
        Compute time-averaged Vs in top 30m (Vs30).

        Used for site classification (ASCE 7, Eurocode 8).
        """
        travel_time = 0.0
        depth = 0.0

        for layer in self.layers:
            if depth + layer.thickness <= 30:
                travel_time += layer.thickness / layer.shear_velocity
                depth += layer.thickness
            else:
                remaining = 30 - depth
                travel_time += remaining / layer.shear_velocity
                break

        return 30.0 / travel_time if travel_time > 0 else self.layers[-1].shear_velocity

    def get_site_class(self) -> str:
        """
        Determine site class per ASCE 7.

        Returns: 'A', 'B', 'C', 'D', 'E', or 'F'
        """
        vs30 = self.get_vs30()
        if vs30 > 1500:
            return 'A'  # Hard rock
        elif vs30 > 760:
            return 'B'  # Rock
        elif vs30 > 360:
            return 'C'  # Dense soil
        elif vs30 > 180:
            return 'D'  # Stiff soil
        else:
            return 'E'  # Soft soil

    @classmethod
    def from_vs30(cls, vs30: float, depth: float = 30.0) -> 'SoilProfile':
        """Create uniform profile from Vs30 value."""
        layer = SoilLayer(
            thickness=depth,
            shear_velocity=vs30,
            density=1800.0,  # Typical soil
            damping=0.05,
        )
        return cls([layer])
```

### 3. Implement foundation impedance

```python
# src/seismic_twin/ssi/foundation.py

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class ImpedanceFunction:
    """Frequency-dependent foundation impedance."""
    frequency: np.ndarray          # [Hz]
    stiffness_horizontal: np.ndarray  # Kh [N/m]
    stiffness_rocking: np.ndarray     # Kr [N·m/rad]
    damping_horizontal: np.ndarray    # Ch [N·s/m]
    damping_rocking: np.ndarray       # Cr [N·m·s/rad]


class RigidCircularFoundation:
    """
    Rigid circular foundation on elastic half-space.

    Based on Gazetas (1991) impedance functions.
    """

    def __init__(
        self,
        radius: float,
        soil_shear_velocity: float,
        soil_density: float,
        poisson_ratio: float = 0.33,
        embedment_depth: float = 0.0,
    ):
        """
        Parameters:
        -----------
        radius : float
            Foundation radius [m]
        soil_shear_velocity : float
            Soil Vs [m/s]
        soil_density : float
            Soil density [kg/m³]
        poisson_ratio : float
            Soil Poisson's ratio
        embedment_depth : float
            Foundation embedment [m]
        """
        self.radius = radius
        self.Vs = soil_shear_velocity
        self.rho = soil_density
        self.nu = poisson_ratio
        self.D = embedment_depth

        # Shear modulus
        self.G = soil_density * soil_shear_velocity ** 2

    def get_static_stiffness(self) -> Tuple[float, float, float]:
        """
        Compute static foundation stiffnesses.

        Returns:
            Kh: Horizontal stiffness [N/m]
            Kv: Vertical stiffness [N/m]
            Kr: Rocking stiffness [N·m/rad]
        """
        R = self.radius
        G = self.G
        nu = self.nu

        # Gazetas (1991) formulas for surface foundation
        Kh = 8 * G * R / (2 - nu)                    # Horizontal
        Kv = 4 * G * R / (1 - nu)                    # Vertical
        Kr = 8 * G * R**3 / (3 * (1 - nu))          # Rocking

        # Embedment correction factors (simplified)
        if self.D > 0:
            eta = self.D / R
            Kh *= (1 + 0.55 * eta)
            Kv *= (1 + 0.28 * eta)
            Kr *= (1 + 2.52 * eta)

        return Kh, Kv, Kr

    def get_impedance(
        self,
        frequencies: np.ndarray,
    ) -> ImpedanceFunction:
        """
        Compute frequency-dependent impedance functions.

        Parameters:
        -----------
        frequencies : array
            Frequencies to evaluate [Hz]

        Returns:
        --------
        ImpedanceFunction with stiffness and damping arrays
        """
        R = self.radius
        Vs = self.Vs
        rho = self.rho

        # Dimensionless frequency
        a0 = 2 * np.pi * frequencies * R / Vs

        # Static stiffnesses
        Kh_static, _, Kr_static = self.get_static_stiffness()

        # Dynamic stiffness coefficients (Veletsos & Wei, 1971)
        # k(a0) = K_static * (k1(a0) + i*a0*c1(a0))

        # Horizontal (simplified approximation)
        k1_h = 1 - 0.2 * a0**2 / (1 + a0**2)
        c1_h = 0.576 * a0 / (1 + 0.4 * a0**2)

        # Rocking (simplified approximation)
        k1_r = 1 - 0.35 * a0**2 / (1 + a0**2)
        c1_r = 0.3 * a0 / (1 + 0.25 * a0**2)

        # Dynamic stiffness and damping
        Kh = Kh_static * k1_h
        Kr = Kr_static * k1_r

        # Radiation damping
        Ch = Kh_static * c1_h * R / Vs
        Cr = Kr_static * c1_r * R / Vs

        return ImpedanceFunction(
            frequency=frequencies,
            stiffness_horizontal=Kh,
            stiffness_rocking=Kr,
            damping_horizontal=Ch,
            damping_rocking=Cr,
        )

    def get_simple_springs(
        self,
        dominant_frequency: Optional[float] = None,
    ) -> Tuple[float, float, float, float]:
        """
        Get simplified constant spring/dashpot values.

        For use in time-domain analysis.

        Parameters:
        -----------
        dominant_frequency : float, optional
            Frequency to evaluate impedance at [Hz]
            If None, uses static values with radiation damping

        Returns:
        --------
        Kh, Kr, Ch, Cr: Spring and dashpot values
        """
        if dominant_frequency is None:
            # Use static stiffness with approximate radiation damping
            Kh, _, Kr = self.get_static_stiffness()
            Ch = 0.576 * self.rho * self.Vs * np.pi * self.radius**2
            Cr = 0.3 * self.rho * self.Vs * np.pi * self.radius**4
        else:
            impedance = self.get_impedance(np.array([dominant_frequency]))
            Kh = impedance.stiffness_horizontal[0]
            Kr = impedance.stiffness_rocking[0]
            Ch = impedance.damping_horizontal[0]
            Cr = impedance.damping_rocking[0]

        return Kh, Kr, Ch, Cr


class RigidRectangularFoundation:
    """
    Rigid rectangular foundation.

    Uses Pais & Kausel (1988) formulas.
    """

    def __init__(
        self,
        length: float,  # 2L (full length)
        width: float,   # 2B (full width)
        soil_shear_velocity: float,
        soil_density: float,
        poisson_ratio: float = 0.33,
    ):
        self.L = length / 2  # Half-length
        self.B = width / 2   # Half-width
        self.Vs = soil_shear_velocity
        self.rho = soil_density
        self.nu = poisson_ratio
        self.G = soil_density * soil_shear_velocity ** 2

    def get_static_stiffness(self) -> Tuple[float, float, float, float]:
        """
        Compute static stiffnesses.

        Returns:
            Kx, Ky, Kz, Krx (rocking about x), Kry (rocking about y)
        """
        L, B = self.L, self.B
        G = self.G
        nu = self.nu

        # Aspect ratio
        ratio = L / B

        # Pais & Kausel (1988) - simplified
        Ab = 4 * L * B  # Foundation area
        Ib = 4 * L * B**3 / 3  # Moment of inertia about x

        Kz = G * np.sqrt(Ab) / (1 - nu) * (
            3.1 * ratio**0.75 + 1.6
        )

        Kx = G * np.sqrt(Ab) / (2 - nu) * (
            6.8 * ratio**0.65 + 2.4
        )

        Krx = G * Ib / (1 - nu) * (
            3.73 * ratio**2.4 + 0.27
        )

        return Kx, Kx, Kz, Krx  # Assume Ky = Kx for simplicity
```

### 4. Implement SSI building model

```python
# src/seismic_twin/ssi/ssi_model.py

from seismic_twin.building.base import StructuralModel
import numpy as np

class SSIBuildingModel(StructuralModel):
    """
    Building with flexible foundation (SSI).

    Adds 3 DOFs at base: horizontal (u0), vertical (w0), rocking (θ)
    """

    def __init__(
        self,
        superstructure: StructuralModel,
        foundation: 'RigidCircularFoundation',
        foundation_mass: float,
        foundation_inertia: float,
        story_heights: np.ndarray,
    ):
        """
        Parameters:
        -----------
        superstructure : StructuralModel
            Fixed-base building model
        foundation : RigidCircularFoundation
            Foundation impedance model
        foundation_mass : float
            Foundation mass [kg]
        foundation_inertia : float
            Foundation rotational inertia [kg·m²]
        story_heights : array
            Height of each floor above foundation [m]
        """
        self.superstructure = superstructure
        self.foundation = foundation
        self.m_f = foundation_mass
        self.I_f = foundation_inertia
        self.heights = np.cumsum(story_heights)

        self._n_dof_super = superstructure.get_n_dof()
        self._n_dof = self._n_dof_super + 2  # Add h and θ

        # Get foundation springs
        Kh, Kr, Ch, Cr = foundation.get_simple_springs()
        self.Kh = Kh
        self.Kr = Kr
        self.Ch = Ch
        self.Cr = Cr

        # Build system matrices
        self._build_matrices()

    def _build_matrices(self):
        """Build augmented M, K, C matrices."""
        n = self._n_dof
        n_s = self._n_dof_super

        # Get superstructure matrices
        M_s = self.superstructure.get_mass_matrix()
        K_s = self.superstructure.get_stiffness_matrix()
        C_s = self.superstructure.get_damping_matrix()

        # Augmented mass matrix
        self._M = np.zeros((n, n))
        self._M[:n_s, :n_s] = M_s
        self._M[n_s, n_s] = self.m_f + np.sum(np.diag(M_s))  # Foundation + super mass
        self._M[n_s+1, n_s+1] = self.I_f + np.sum(np.diag(M_s) * self.heights**2)

        # Coupling terms (mass * height for rocking)
        for i in range(n_s):
            self._M[i, n_s] = M_s[i, i]  # Translation coupling
            self._M[n_s, i] = M_s[i, i]
            self._M[i, n_s+1] = M_s[i, i] * self.heights[i]  # Rocking coupling
            self._M[n_s+1, i] = M_s[i, i] * self.heights[i]

        # Augmented stiffness matrix
        self._K = np.zeros((n, n))
        self._K[:n_s, :n_s] = K_s
        self._K[n_s, n_s] = self.Kh
        self._K[n_s+1, n_s+1] = self.Kr

        # Augmented damping matrix
        self._C = np.zeros((n, n))
        self._C[:n_s, :n_s] = C_s
        self._C[n_s, n_s] = self.Ch
        self._C[n_s+1, n_s+1] = self.Cr

    def get_mass_matrix(self) -> np.ndarray:
        return self._M

    def get_stiffness_matrix(self) -> np.ndarray:
        return self._K

    def get_damping_matrix(self) -> np.ndarray:
        return self._C

    def get_influence_vector(self, direction: str = 'x') -> np.ndarray:
        """Influence vector for SSI model."""
        n = self._n_dof
        iota = np.zeros(n)
        iota[:self._n_dof_super] = 1.0  # Superstructure DOFs
        iota[-2] = 1.0  # Foundation horizontal
        return iota

    def get_n_dof(self) -> int:
        return self._n_dof

    def get_period_lengthening(self) -> float:
        """
        Compute period lengthening ratio due to SSI.

        T_ssi / T_fixed
        """
        # Fixed-base period
        M_s = self.superstructure.get_mass_matrix()
        K_s = self.superstructure.get_stiffness_matrix()
        omega_fixed = np.sqrt(np.linalg.eigvalsh(K_s, M_s)[0])
        T_fixed = 2 * np.pi / omega_fixed

        # SSI period
        omega_ssi = np.sqrt(np.linalg.eigvalsh(self._K, self._M)[0])
        T_ssi = 2 * np.pi / omega_ssi

        return T_ssi / T_fixed
```

### 5. Add tests

- Test soil profile Vs30 calculation
- Test foundation impedance against published values
- Test SSI model matrix assembly
- Test period lengthening
- Compare fixed-base vs SSI response

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/ssi/__init__.py` | Create |
| `src/seismic_twin/ssi/soil_profiles.py` | Create |
| `src/seismic_twin/ssi/foundation.py` | Create |
| `src/seismic_twin/ssi/ssi_model.py` | Create |
| `tests/test_ssi.py` | Create |

## Success Criteria

- [ ] Soil profile properties computed correctly
- [ ] Foundation impedance matches published solutions
- [ ] SSI model assembles correctly
- [ ] Period lengthening calculated accurately
- [ ] Time history analysis works with SSI model
- [ ] All tests pass
