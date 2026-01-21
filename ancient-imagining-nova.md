# Wave Propagation Prediction System - Implementation Plan

## Overview

Implement a GMPE-based wave propagation prediction system that:
1. Places a "virtual building" at a target station location
2. Uses waveforms from nearby stations to predict ground motion at that location
3. Validates predictions against actual recorded data at the target station

**Key Decisions:**
- GMPE Model: Boore-Atkinson 2008 (uses Rjb distance)
- Waveform Prediction: Scale nearest station waveform by GMPE ratio
- Metrics: Peak values (PGA/PGV/PGD) + Response spectrum + Time-series (NRMSE, correlation)
- Interface: Core Python API + Dashboard page

---

## Module Structure

```
src/seismic_twin/
    prediction/                          # NEW MODULE
        __init__.py
        gmpe/
            __init__.py
            base.py                      # Abstract GMPE base class
            boore_atkinson_2008.py       # BA08 implementation
        distance.py                      # Rjb distance calculations
        waveform_prediction.py           # Waveform scaling logic
        validation.py                    # Comparison metrics

    dashboard/
        layouts/
            wave_prediction.py           # NEW: Dashboard page
        callbacks/
            wave_prediction_callbacks.py # NEW: Page callbacks
        figures/
            validation_plots.py          # NEW: Comparison plots
        state/
            schemas.py                   # MODIFY: Add PredictionState

examples/
    run_wave_prediction.py               # NEW: Example workflow

tests/
    test_gmpe.py                         # NEW: GMPE unit tests
    test_wave_prediction.py              # NEW: Integration tests
```

---

## Phase 1: GMPE Module

### 1.1 Base Class (`prediction/gmpe/base.py`)

```python
@dataclass
class GMPEInput:
    magnitude: float           # Mw
    distance_rjb: float        # km
    vs30: float = 760.0        # m/s (rock default)
    period: float = 0.0        # 0.0 = PGA

@dataclass
class GMPEOutput:
    median_sa: float           # g
    sigma_total: float         # log units

class BaseGMPE(ABC):
    def predict(self, input_params: GMPEInput) -> GMPEOutput: ...
    def predict_pga(self, magnitude: float, distance_rjb: float) -> float: ...
    def predict_spectrum(self, magnitude: float, distance_rjb: float) -> tuple[NDArray, NDArray]: ...
```

### 1.2 Boore-Atkinson 2008 (`prediction/gmpe/boore_atkinson_2008.py`)

Implements BA08 equation:
```
ln(Y) = Fm(M) + Fd(Rjb, M) + Fs(Vs30, A1100)
```

- Magnitude term: bilinear with hinge at Mh
- Distance term: geometric spreading with magnitude-dependent attenuation
- Site term: ignored initially (Vs30=760 rock assumption)

Coefficient tables from published paper for periods 0.01s to 10s.

### 1.3 Distance Utilities (`prediction/distance.py`)

```python
def compute_rjb_distance(
    station_lat: float, station_lon: float,
    epicenter_lat: float, epicenter_lon: float,
    fault_geometry: Optional[FaultGeometry] = None,
) -> float:
    """For M<6 or unknown geometry, Rjb ≈ Repi (epicentral distance)."""

def compute_epicentral_distance(lat1, lon1, lat2, lon2) -> float:
    """Haversine formula."""
```

---

## Phase 2: Waveform Prediction

### 2.1 Core Predictor (`prediction/waveform_prediction.py`)

```python
@dataclass
class StationPrediction:
    target_station_id: str
    predicted_waveform: NDArray
    predicted_pga: float
    source_station_id: str
    scale_factor: float
    time: NDArray
    dt: float

class WaveformPredictor:
    def predict_at_location(
        self,
        target_lat: float, target_lon: float,
        event_info: EventInfo,
        source_records: Sequence[GroundMotionRecord],
    ) -> StationPrediction:
        """
        Algorithm:
        1. Select N nearest source stations
        2. For nearest station:
           - Compute Rjb for source and target
           - scale_factor = GMPE_PGA(target_Rjb) / GMPE_PGA(source_Rjb)
           - predicted_waveform = source_waveform * scale_factor
        """

    def predict_cross_validation(
        self,
        event_info: EventInfo,
        all_records: Sequence[GroundMotionRecord],
    ) -> list[tuple[GroundMotionRecord, StationPrediction]]:
        """Leave-one-out cross-validation."""
```

---

## Phase 3: Validation Module

### 3.1 Metrics (`prediction/validation.py`)

```python
@dataclass
class PeakMetrics:
    actual_pga: float
    predicted_pga: float
    pga_ratio: float              # predicted / actual
    pga_error_percent: float
    # Same for PGV, PGD

@dataclass
class SpectrumMetrics:
    periods: NDArray
    actual_sa: NDArray
    predicted_sa: NDArray
    mean_sa_ratio: float          # geometric mean
    gof_short_period: float       # 0.1-0.5s
    gof_mid_period: float         # 0.5-1.0s
    gof_long_period: float        # 1.0-3.0s

@dataclass
class TimeSeriesMetrics:
    nrmse: float
    correlation: float
    arias_ratio: float
    duration_ratio: float

@dataclass
class ValidationResult:
    station_id: str
    distance_km: float
    peak_metrics: PeakMetrics
    spectrum_metrics: SpectrumMetrics
    time_series_metrics: TimeSeriesMetrics
    overall_score: float          # 0-1 composite
    quality_grade: str            # A/B/C/D/F

class PredictionValidator:
    def validate(self, actual: GroundMotionRecord, predicted: StationPrediction) -> ValidationResult: ...
    def validate_cross_validation(self, pairs: list[tuple]) -> ValidationSummary: ...
```

Quality scoring weights:
- PGA accuracy: 30%
- Spectrum fit: 40%
- Correlation: 30%

---

## Phase 4: Example Script

### `examples/run_wave_prediction.py`

```python
"""Demonstrate wave propagation prediction with Ridgecrest data."""

from seismic_twin.data import SCEDCS3Fetcher
from seismic_twin.prediction import (
    WaveformPredictor, PredictionValidator, BooreAtkinson2008
)

# 1. Fetch multiple station records for Ridgecrest M7.1
fetcher = SCEDCS3Fetcher()
event_id = "ci38457511"
records = fetcher.get_multiple_records(event_id, max_stations=6)

# 2. Run leave-one-out cross-validation
predictor = WaveformPredictor()
pairs = predictor.predict_cross_validation(event_info, records)

# 3. Validate all predictions
validator = PredictionValidator()
summary = validator.validate_cross_validation(pairs)

# 4. Print results
print(f"Mean PGA ratio: {summary.mean_pga_ratio:.2f}")
print(f"Mean NRMSE: {summary.mean_nrmse:.3f}")
print(f"Mean correlation: {summary.mean_correlation:.2f}")
```

---

## Phase 5: Dashboard Integration

### 5.1 State Schema (`state/schemas.py`)

```python
class PredictionState(BaseModel):
    # Event
    event_id: Optional[str] = None
    event_magnitude: Optional[float] = None
    event_lat: Optional[float] = None
    event_lon: Optional[float] = None

    # Stations
    available_stations: list[StationInfo] = []
    selected_source_stations: list[str] = []
    target_station_id: Optional[str] = None

    # Results
    prediction_completed: bool = False
    predicted_waveform: list[float] = []
    actual_waveform: list[float] = []

    # Validation metrics
    validation_pga_ratio: Optional[float] = None
    validation_nrmse: Optional[float] = None
    validation_correlation: Optional[float] = None
    validation_quality_grade: Optional[str] = None

    # Spectrum
    spectrum_periods: list[float] = []
    spectrum_actual: list[float] = []
    spectrum_predicted: list[float] = []
```

### 5.2 Page Layout (`layouts/wave_prediction.py`)

Three sections:
1. **Event & Station Selection**
   - Event ID input (default: Ridgecrest ci38457511)
   - Station list with checkboxes for source selection
   - Target station dropdown

2. **Run Prediction Button**
   - Loads data, runs GMPE scaling, validates

3. **Validation Results** (shown after prediction)
   - Peak metrics table (PGA/PGV/PGD actual vs predicted)
   - Response spectrum plot (overlay actual vs predicted)
   - Time history comparison plot
   - Summary card with NRMSE, correlation, quality grade

### 5.3 Registration

- Add route `/wave-prediction` in `app.py`
- Add sidebar link in `base.py`
- Register callbacks in `callbacks/__init__.py`

---

## Critical Files to Modify

| File | Change |
|------|--------|
| `src/seismic_twin/data/records.py` | Reference for GroundMotionRecord, EventInfo |
| `src/seismic_twin/analysis/metrics.py` | Reuse compute_nrmse, compute_correlation |
| `src/seismic_twin/ground_motion/synthetic.py` | Reuse compute_response_spectrum |
| `src/seismic_twin/dashboard/state/schemas.py` | Add PredictionState |
| `src/seismic_twin/dashboard/state/store.py` | Add prediction store |
| `src/seismic_twin/dashboard/app.py` | Add route |
| `src/seismic_twin/dashboard/layouts/base.py` | Add sidebar link |
| `src/seismic_twin/dashboard/callbacks/__init__.py` | Register callbacks |
| `src/seismic_twin/dashboard/layouts/__init__.py` | Export layout |

---

## Implementation Order

1. **Phase 1: GMPE Module**
   - Create `prediction/` package structure
   - Implement BA08 with coefficient tables
   - Add distance utilities
   - Unit tests for GMPE predictions

2. **Phase 2: Waveform Prediction**
   - Implement WaveformPredictor
   - Add cross-validation support
   - Test with Ridgecrest data

3. **Phase 3: Validation Module**
   - Implement all comparison metrics
   - Add quality scoring
   - Integration tests

4. **Phase 4: Example Script**
   - Create run_wave_prediction.py
   - Document usage

5. **Phase 5: Dashboard**
   - Add state schema
   - Create layout
   - Implement callbacks
   - Add visualization plots

---

## Verification Plan

1. **GMPE Accuracy**: Compare BA08 predictions against published values from the paper
2. **Cross-Validation**: Run with Ridgecrest data, expect:
   - Mean PGA ratio near 1.0 (0.7-1.5 acceptable)
   - Correlation > 0.7
   - NRMSE < 0.5
3. **Dashboard**: Manually test workflow end-to-end
4. **Tests**: Run `pytest tests/test_gmpe.py tests/test_wave_prediction.py`
