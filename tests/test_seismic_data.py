"""
Tests for seismic data fetching module (SeismoHub).
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from seismic_twin.data import (
    CacheError,
    CacheManager,
    DataNotFoundError,
    EventInfo,
    FiniteFaultModel,
    GroundMotionRecord,
    NetworkError,
    SeismoHubError,
)


class TestGroundMotionRecord:
    """Tests for GroundMotionRecord dataclass."""

    def test_creation(self):
        """Test creating a GroundMotionRecord."""
        time = np.linspace(0, 10, 1001)
        acc = np.sin(2 * np.pi * time)

        record = GroundMotionRecord(
            time=time,
            acceleration=acc,
            dt=0.01,
            event_id="us7000test",
            network="CI",
            station="TEST",
            channel="HNE",
            component="E",
            station_latitude=34.0,
            station_longitude=-118.0,
            epicentral_distance_km=25.5,
            pga=1.0,
            processing_history=["test"],
        )

        assert record.event_id == "us7000test"
        assert record.units == "g"
        assert len(record.time) == 1001
        assert record.pga == 1.0

    def test_to_tuple(self):
        """Test to_tuple() backward compatibility method."""
        time = np.linspace(0, 10, 1001)
        acc = np.sin(2 * np.pi * time)

        record = GroundMotionRecord(
            time=time,
            acceleration=acc,
            dt=0.01,
            event_id="us7000test",
            network="CI",
            station="TEST",
            channel="HNE",
            component="E",
            station_latitude=34.0,
            station_longitude=-118.0,
            epicentral_distance_km=25.5,
            pga=1.0,
        )

        t, a = record.to_tuple()
        np.testing.assert_array_equal(t, time)
        np.testing.assert_array_equal(a, acc)


class TestEventInfo:
    """Tests for EventInfo dataclass."""

    def test_creation(self):
        """Test creating an EventInfo."""
        event = EventInfo(
            event_id="us7000test",
            origin_time=datetime(2020, 1, 1, 12, 0, 0),
            latitude=34.0,
            longitude=-118.0,
            depth_km=10.0,
            magnitude=6.5,
            magnitude_type="Mw",
            region="California",
            source_catalog="USGS",
        )

        assert event.event_id == "us7000test"
        assert event.magnitude == 6.5
        assert event.depth_km == 10.0


class TestFiniteFaultModel:
    """Tests for FiniteFaultModel dataclass."""

    def test_creation(self):
        """Test creating a FiniteFaultModel."""
        model = FiniteFaultModel(
            event_id="us7000test",
            hypocenter=(34.0, -118.0, 10.0),
            strike=45.0,
            dip=60.0,
            rake=90.0,
            length_km=50.0,
            width_km=20.0,
            moment_tensor=None,
            source="usgs",
        )

        assert model.event_id == "us7000test"
        assert model.strike == 45.0
        assert model.hypocenter == (34.0, -118.0, 10.0)


class TestExceptions:
    """Tests for exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test that all exceptions inherit from SeismoHubError."""
        assert issubclass(DataNotFoundError, SeismoHubError)
        assert issubclass(NetworkError, SeismoHubError)
        assert issubclass(CacheError, SeismoHubError)

    def test_exception_messages(self):
        """Test exception message handling."""
        exc = DataNotFoundError("Event not found")
        assert "Event not found" in str(exc)


class TestCacheManager:
    """Tests for CacheManager."""

    def test_init_creates_directories(self):
        """Test that cache directories are created on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "test_cache"
            CacheManager(cache_dir)  # Creates directories on init

            assert (cache_dir / "events").exists()
            assert (cache_dir / "waveforms").exists()
            assert (cache_dir / "finite_faults").exists()

    def test_event_cache_roundtrip(self):
        """Test saving and loading event info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            event = EventInfo(
                event_id="us7000test",
                origin_time=datetime(2020, 1, 1, 12, 0, 0),
                latitude=34.0,
                longitude=-118.0,
                depth_km=10.0,
                magnitude=6.5,
                magnitude_type="Mw",
                region="California",
                source_catalog="USGS",
            )

            cache.save_event(event)
            loaded = cache.get_event("us7000test")

            assert loaded is not None
            assert loaded.event_id == event.event_id
            assert loaded.magnitude == event.magnitude
            assert loaded.latitude == event.latitude

    def test_event_cache_miss(self):
        """Test cache miss returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            assert cache.get_event("nonexistent") is None

    def test_waveform_cache_roundtrip(self):
        """Test saving and loading waveform data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            time = np.linspace(0, 10, 1001)
            acc = np.sin(2 * np.pi * time)

            record = GroundMotionRecord(
                time=time,
                acceleration=acc,
                dt=0.01,
                event_id="us7000test",
                network="CI",
                station="TEST",
                channel="HNE",
                component="E",
                station_latitude=34.0,
                station_longitude=-118.0,
                epicentral_distance_km=25.5,
                pga=1.0,
                processing_history=["test"],
            )

            cache_key = cache.make_waveform_key("us7000test", "CI", "TEST", "HNE")
            cache.save_waveform(cache_key, record)
            loaded = cache.get_waveform(cache_key)

            assert loaded is not None
            assert loaded.event_id == record.event_id
            np.testing.assert_array_almost_equal(loaded.time, record.time)
            np.testing.assert_array_almost_equal(loaded.acceleration, record.acceleration)

    def test_finite_fault_cache_roundtrip(self):
        """Test saving and loading finite fault model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            model = FiniteFaultModel(
                event_id="us7000test",
                hypocenter=(34.0, -118.0, 10.0),
                strike=45.0,
                dip=60.0,
                rake=90.0,
                length_km=50.0,
                width_km=20.0,
                moment_tensor={"Mxx": 1e18},
                source="usgs",
            )

            cache_key = cache.make_finite_fault_key("us7000test")
            cache.save_finite_fault(cache_key, model)
            loaded = cache.get_finite_fault(cache_key)

            assert loaded is not None
            assert loaded.event_id == model.event_id
            assert loaded.strike == model.strike
            assert loaded.moment_tensor == model.moment_tensor

    def test_clear_cache(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)

            event = EventInfo(
                event_id="us7000test",
                origin_time=datetime(2020, 1, 1, 12, 0, 0),
                latitude=34.0,
                longitude=-118.0,
                depth_km=10.0,
                magnitude=6.5,
                magnitude_type="Mw",
                region="California",
                source_catalog="USGS",
            )
            cache.save_event(event)

            cache.clear()

            # Should still have directory structure but no data
            assert cache.get_event("us7000test") is None

    def test_make_waveform_key(self):
        """Test waveform cache key generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            key = cache.make_waveform_key("us7000test", "CI", "TEST", "HNE")
            assert key == "us7000test_CI_TEST_HNE"

    def test_make_finite_fault_key(self):
        """Test finite fault cache key generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(tmpdir)
            key = cache.make_finite_fault_key("us7000test")
            assert key == "us7000test_ff"


class TestSeismicDataFetcher:
    """Tests for SeismicDataFetcher (with mocked ObsPy)."""

    def test_invalid_data_center(self):
        """Test that invalid data center raises error."""
        from seismic_twin.data import SeismicDataFetcher

        with pytest.raises(ValueError, match="Invalid data center"):
            SeismicDataFetcher("INVALID")

    def test_valid_data_centers(self):
        """Test that valid data centers are accepted."""
        from seismic_twin.data import SeismicDataFetcher

        for dc in ["USGS", "IRIS", "GFZ", "usgs", "iris"]:
            fetcher = SeismicDataFetcher(dc)
            assert fetcher.data_center == dc.upper()

    @patch("seismic_twin.data.fetcher.SeismicDataFetcher.event_client", new_callable=MagicMock)
    def test_search_events_empty(self, mock_client):
        """Test search_events returns empty list when no events found."""
        obspy = pytest.importorskip("obspy")
        Catalog = obspy.Catalog

        mock_client.get_events.return_value = Catalog()

        from seismic_twin.data import SeismicDataFetcher

        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = SeismicDataFetcher("USGS", cache_dir=tmpdir)
            fetcher._event_client = mock_client

            events = fetcher.search_events(
                start_time="2020-01-01",
                end_time="2020-01-02",
                min_magnitude=5.0,
            )

            assert events == []

    @patch("seismic_twin.data.fetcher.SeismicDataFetcher.event_client", new_callable=MagicMock)
    def test_get_event_info_from_cache(self, mock_client):
        """Test get_event_info returns cached event."""
        from seismic_twin.data import SeismicDataFetcher

        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = SeismicDataFetcher("USGS", cache_dir=tmpdir)

            # Pre-populate cache
            event = EventInfo(
                event_id="us7000test",
                origin_time=datetime(2020, 1, 1, 12, 0, 0),
                latitude=34.0,
                longitude=-118.0,
                depth_km=10.0,
                magnitude=6.5,
                magnitude_type="Mw",
                region="California",
                source_catalog="USGS",
            )
            fetcher.cache.save_event(event)

            # Should return cached event without calling API
            result = fetcher.get_event_info("us7000test")
            assert result.event_id == "us7000test"
            mock_client.get_events.assert_not_called()


class TestIntegrationWithAnalysis:
    """Test integration with existing analysis pipeline."""

    def test_ground_motion_record_with_newmark_beta(self):
        """Test that GroundMotionRecord works with newmark_beta."""
        from seismic_twin.analysis import newmark_beta
        from seismic_twin.building import MDOFShearBuilding

        # Create a simple 2-story building
        building = MDOFShearBuilding(
            masses=[1000, 1000],
            stiffnesses=[1e6, 1e6],
            damping_ratio=0.05,
            story_heights=[3.0, 3.0],
        )

        # Create a ground motion record
        dt = 0.01
        duration = 10.0
        time = np.arange(0, duration, dt)
        acc = 0.1 * np.sin(2 * np.pi * 1.0 * time)  # 1 Hz sine wave, 0.1g

        record = GroundMotionRecord(
            time=time,
            acceleration=acc,
            dt=dt,
            event_id="synthetic",
            network="SYN",
            station="TEST",
            channel="HNE",
            component="E",
            station_latitude=0.0,
            station_longitude=0.0,
            epicentral_distance_km=0.0,
            pga=0.1,
        )

        # Run analysis using to_tuple()
        t, a = record.to_tuple()
        result = newmark_beta(building.M, building.C, building.K, a, dt)

        assert result.displacement.shape == (2, len(time))
        assert np.max(np.abs(result.displacement)) > 0


@pytest.mark.slow
class TestRealDataFetching:
    """
    Tests that fetch real data from FDSN networks.

    These tests are marked slow and require network access.
    Run with: pytest -m slow
    """

    def test_search_real_events(self):
        """Test searching for real events (requires network)."""
        pytest.importorskip("obspy")

        from seismic_twin.data import SeismicDataFetcher

        with tempfile.TemporaryDirectory() as tmpdir:
            fetcher = SeismicDataFetcher("USGS", cache_dir=tmpdir, timeout=30.0)

            # Search for M5+ events in January 2020
            events = fetcher.search_events(
                start_time="2020-01-01",
                end_time="2020-01-07",
                min_magnitude=5.0,
                limit=5,
            )

            assert len(events) > 0
            assert all(e.magnitude >= 5.0 for e in events)
            assert all(isinstance(e, EventInfo) for e in events)
