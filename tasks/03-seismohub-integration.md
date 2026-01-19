# Task 03: SeismoHub Integration Layer

## Priority: HIGH
## Estimated Effort: 3-4 days

## Problem Statement

The current codebase:
- Only generates synthetic ground motions
- Has no connection to real earthquake data (USGS, FDSN networks)
- Cannot use finite-fault rupture models from actual events
- Limits validation against real-world seismic records

## Implementation Plan

### 1. Create data fetching module
Create `src/seismic_twin/data/seismic_catalog.py`

### 2. Implement SeismicDataFetcher class

```python
from obspy.clients.fdsn import Client
from obspy import UTCDateTime
import numpy as np
from typing import Tuple, List, Optional

class SeismicDataFetcher:
    """Fetch real earthquake data from USGS/regional networks."""

    def __init__(self, network: str = "USGS"):
        """
        Parameters:
        -----------
        network : str
            FDSN network code (USGS, GFZ, IRIS, etc.)
        """
        self.client = Client(network)

    def search_events(
        self,
        start_time: str,
        end_time: str,
        min_magnitude: float = 5.0,
        max_magnitude: float = 9.0,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        max_radius_km: Optional[float] = None,
    ) -> List[dict]:
        """Search earthquake catalog."""
        pass

    def get_event_info(self, event_id: str) -> dict:
        """Get detailed event information."""
        pass

    def get_event_finite_fault(
        self,
        event_id: str,
        source: str = "usgs"
    ) -> dict:
        """
        Fetch finite-fault model for an event.

        Returns dict with:
            - rupture: array of subfault parameters
            - hypocenter: (lon, lat, depth, time)
            - magnitude: Mw
            - moment_tensor: (Mrr, Mtt, Mpp, Mrt, Mrp, Mtp)
        """
        pass

    def get_event_seismograms(
        self,
        event_id: str,
        channel_code: str = "HN*",  # Strong motion
        distance_range: Tuple[float, float] = (0, 100),  # km
        duration: float = 300,  # seconds after origin
    ) -> List[dict]:
        """
        Fetch actual seismic recordings of an event.

        Returns list of waveform dicts with:
            - network, station, location, channel
            - latitude, longitude
            - time array
            - acceleration array (m/s²)
            - dt
        """
        pass
```

### 3. Implement USGS finite-fault parser

```python
def _parse_usgs_finite_fault(self, event_id: str) -> dict:
    """Parse USGS Finite Fault database."""
    import requests

    # Fetch finite-fault JSON from USGS
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {"eventid": event_id, "format": "geojson"}

    # Parse rupture geometry, slip distribution
    # Return structured dict
```

### 4. Implement Global CMT interface

```python
def _fetch_globalcmt(self, event_id: str) -> dict:
    """Fetch moment tensor from Global CMT catalog."""
    # Query globalcmt.org or use obspy CMT client
    pass
```

### 5. Create convenience functions

```python
def fetch_strong_motion_record(
    event_id: str,
    station_code: str,
    component: str = "E",  # E, N, or Z
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Fetch a single strong motion record.

    Returns:
        time, acceleration, dt
    """
    pass

def list_available_networks() -> List[str]:
    """List available FDSN data centers."""
    pass
```

### 6. Add caching layer

```python
class CachedSeismicDataFetcher(SeismicDataFetcher):
    """SeismicDataFetcher with local caching."""

    def __init__(self, network: str = "USGS", cache_dir: str = ".seismic_cache"):
        super().__init__(network)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cached_or_fetch(self, key: str, fetch_func, *args):
        """Check cache first, fetch and cache if missing."""
        pass
```

### 7. Add tests

- Test event search (mock FDSN responses)
- Test waveform fetching
- Test caching behavior
- Test error handling for unavailable data

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/seismic_twin/data/__init__.py` | Create |
| `src/seismic_twin/data/seismic_catalog.py` | Create |
| `src/seismic_twin/data/cache.py` | Create |
| `tests/test_seismic_catalog.py` | Create |
| `pyproject.toml` | Add obspy dependency |

## Dependencies

- `obspy>=1.4.0` - FDSN client and seismological utilities
- `requests` - HTTP requests for USGS API

## Success Criteria

- [ ] Can search earthquake catalog by time/location/magnitude
- [ ] Can fetch finite-fault models from USGS
- [ ] Can download strong motion records
- [ ] Caching prevents redundant downloads
- [ ] Clear error messages when data unavailable
- [ ] All tests pass (including mocked network tests)

## Example Usage

```python
from seismic_twin.data import SeismicDataFetcher

# Fetch Christchurch 2011 earthquake data
fetcher = SeismicDataFetcher("USGS")
event_info = fetcher.get_event_info("usp000huvq")

# Get nearby strong motion records
records = fetcher.get_event_seismograms(
    "usp000huvq",
    channel_code="HN*",
    distance_range=(0, 50)
)

# Use in simulation
for record in records:
    result = newmark_beta(model, record['acceleration'], record['dt'])
```
