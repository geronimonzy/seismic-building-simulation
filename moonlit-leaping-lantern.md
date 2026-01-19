# Plan: SeismoHub Integration (Real Earthquake Data)

## Summary
Add capability to fetch real earthquake data from USGS/FDSN networks using ObsPy. This enables validation against real seismic records and practical engineering applications.

## Current State
- Ground motion module only generates synthetic data
- Returns `(time, acceleration)` tuples with acceleration in **g units**
- Analysis module (`newmark_beta`) expects 1D numpy arrays in g units

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module location | `seismic_twin/data/` (new) | Separates fetching from generation/processing |
| API style | Class + convenience function | Class for state/cache, function for simple use |
| Return format | `GroundMotionRecord` dataclass | Rich metadata + `.to_tuple()` for compatibility |
| Caching | Project-local `.seismic_cache/` | Reproducible, configurable via env var |
| Units | Convert to **g** internally | Matches existing pipeline requirements |

## Files to Create

### 1. `src/seismic_twin/data/__init__.py`
Export: `SeismicDataFetcher`, `fetch_ground_motion_record`, `GroundMotionRecord`, `EventInfo`, exceptions

### 2. `src/seismic_twin/data/records.py`
```python
@dataclass
class GroundMotionRecord:
    time: NDArray[np.floating]
    acceleration: NDArray[np.floating]  # in g units
    dt: float
    event_id: str
    network: str
    station: str
    channel: str
    component: str  # E, N, Z
    station_latitude: float
    station_longitude: float
    epicentral_distance_km: float
    pga: float
    processing_history: list[str]
    units: str = "g"

    def to_tuple(self) -> tuple[NDArray, NDArray]:
        """Backward compatible with generate_synthetic_ground_motion()"""
        return self.time, self.acceleration

@dataclass
class EventInfo:
    event_id: str
    origin_time: datetime
    latitude: float
    longitude: float
    depth_km: float
    magnitude: float
    magnitude_type: str
    region: str
    source_catalog: str

@dataclass
class FiniteFaultModel:
    event_id: str
    hypocenter: tuple[float, float, float]
    strike: float
    dip: float
    rake: float
    length_km: float
    width_km: float
    moment_tensor: Optional[dict]
    source: str
```

### 3. `src/seismic_twin/data/fetcher.py`
```python
class SeismicDataFetcher:
    VALID_DATA_CENTERS = ["USGS", "IRIS", "GFZ", "INGV", "EMSC", "NCEDC", "SCEDC"]

    def __init__(self, data_center="USGS", cache_dir=".seismic_cache", timeout=60.0)

    def search_events(start_time, end_time, min_magnitude, max_magnitude,
                      latitude, longitude, max_radius_km, limit) -> list[EventInfo]

    def get_event_info(event_id) -> EventInfo

    def get_ground_motion_record(event_id, network, station, channel, component,
                                  max_distance_km, pre_event_sec, post_event_sec,
                                  apply_baseline_correction, apply_highpass_filter,
                                  highpass_freq) -> GroundMotionRecord

    def get_all_ground_motion_records(event_id, ...) -> list[GroundMotionRecord]

    def get_finite_fault_model(event_id, source="usgs") -> FiniteFaultModel

# Convenience function
def fetch_ground_motion_record(event_id, station, component, data_center) -> GroundMotionRecord
```

### 4. `src/seismic_twin/data/cache.py`
```python
class CacheManager:
    def __init__(self, cache_dir: Path)
    def get_event(event_id) -> Optional[EventInfo]
    def save_event(event: EventInfo)
    def get_waveform(cache_key) -> Optional[GroundMotionRecord]
    def save_waveform(cache_key, record: GroundMotionRecord)
    def get_finite_fault(cache_key) -> Optional[FiniteFaultModel]
    def save_finite_fault(cache_key, model: FiniteFaultModel)
    def clear()
```

Cache structure:
```
.seismic_cache/
    events/{event_id}.json
    waveforms/{event_id}_{net}_{sta}_{chan}.npz
    finite_faults/{event_id}_ff.json
```

### 5. `src/seismic_twin/data/exceptions.py`
```python
class SeismoHubError(Exception): pass
class DataNotFoundError(SeismoHubError): pass
class NetworkError(SeismoHubError): pass
class CacheError(SeismoHubError): pass
```

### 6. `tests/test_seismic_data.py`
- Test dataclass creation and `to_tuple()`
- Test fetcher with mocked ObsPy client
- Test cache round-trip
- Test integration with `newmark_beta()`

## Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add `obspy>=1.4.0`, `requests>=2.25.0` dependencies |
| `src/seismic_twin/__init__.py` | Export `SeismicDataFetcher`, `fetch_ground_motion_record` |

## Key Implementation Details

### Unit Conversion (Critical)
ObsPy returns acceleration in m/s² after instrument response removal. Must convert:
```python
acceleration_g = acceleration_mps2 / 9.81
```

### Processing Pipeline
1. Fetch raw waveform via ObsPy
2. Remove instrument response (→ m/s²)
3. Apply baseline correction (reuse existing function)
4. Apply highpass filter (reuse existing function)
5. Convert to g units
6. Return as `GroundMotionRecord`

### Lazy Loading
ObsPy client only initialized when first method called (avoids import overhead).

## Example Usage
```python
from seismic_twin.data import SeismicDataFetcher
from seismic_twin.analysis import newmark_beta

# Fetch Christchurch 2011 earthquake
fetcher = SeismicDataFetcher("USGS")
events = fetcher.search_events(
    start_time="2011-02-22",
    end_time="2011-02-23",
    min_magnitude=6.0,
    latitude=-43.5,
    longitude=172.6,
    max_radius_km=50,
)

# Get ground motion record
record = fetcher.get_ground_motion_record(
    events[0].event_id,
    channel="HN*",
    component="E",
    max_distance_km=50,
)

# Use with existing analysis pipeline
result = newmark_beta(building.M, building.C, building.K, record.acceleration, record.dt)

# Or use tuple unpacking for compatibility
time, acc = record.to_tuple()
```

## Verification
1. Run `pytest tests/test_seismic_data.py -v` for unit tests
2. Run integration test fetching real data (marked `@pytest.mark.slow`):
   ```python
   fetcher = SeismicDataFetcher("IRIS")
   events = fetcher.search_events("2020-01-01", "2020-01-02", min_magnitude=5.0)
   ```
3. Verify `newmark_beta()` accepts fetched record
4. Run full test suite: `pytest tests/ -v`

## Dependencies
- `obspy>=1.4.0` - FDSN client for earthquake data
- `requests>=2.25.0` - HTTP requests for USGS finite-fault API

## Sources
- [ObsPy FDSN Client Documentation](https://docs.obspy.org/packages/obspy.clients.fdsn.html)
- [ObsPy Client API](https://docs.obspy.org/packages/autogen/obspy.clients.fdsn.client.Client.html)
