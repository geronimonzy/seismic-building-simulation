#!/usr/bin/env python
"""
Wave Propagation Prediction Example

This example demonstrates how to use the wave propagation prediction system
to predict ground motion at target locations using recordings from nearby
seismic stations and GMPE-based amplitude scaling.

It can run in two modes:
1. With real data from SCEDC (requires obspy and network access)
2. With synthetic data (standalone, no external dependencies)

Usage:
    python examples/run_wave_prediction.py

Requirements for real data mode:
    - obspy: pip install obspy
    - Network access to SCEDC S3 and USGS
"""

from __future__ import annotations

import numpy as np

from seismic_twin.prediction import (
    BooreAtkinson2008,
    PredictionValidator,
    WaveformPredictor,
    compute_epicentral_distance,
)


def create_synthetic_records():
    """
    Create synthetic ground motion records for demonstration.

    Simulates records from 5 stations at different distances from
    a M7.1 earthquake (similar to 2019 Ridgecrest).
    """
    from dataclasses import dataclass
    from datetime import datetime

    from seismic_twin.ground_motion.synthetic import generate_synthetic_ground_motion
    from seismic_twin.data.records import EventInfo

    # Simulate Ridgecrest M7.1 event
    event_info = EventInfo(
        event_id="synthetic_m71",
        origin_time=datetime(2019, 7, 6, 3, 19, 53),
        latitude=35.7695,
        longitude=-117.5993,
        depth_km=8.0,
        magnitude=7.1,
        magnitude_type="Mw",
        region="Ridgecrest, CA",
        source_catalog="Synthetic",
    )

    # Create synthetic stations at different distances
    stations = [
        ("STA1", 35.85, -117.50, 15.0),   # ~15 km
        ("STA2", 35.70, -117.35, 25.0),   # ~25 km
        ("STA3", 35.55, -117.70, 30.0),   # ~30 km
        ("STA4", 35.90, -117.80, 35.0),   # ~35 km
        ("STA5", 35.45, -117.50, 45.0),   # ~45 km
    ]

    # Use GMPE to compute expected PGA at each distance
    gmpe = BooreAtkinson2008()

    # Create records with proper dataclass
    @dataclass
    class SyntheticRecord:
        time: np.ndarray
        acceleration: np.ndarray
        dt: float
        event_id: str
        network: str
        station: str
        channel: str
        component: str
        station_latitude: float
        station_longitude: float
        epicentral_distance_km: float
        pga: float
        processing_history: list

    records = []
    for station_id, lat, lon, _ in stations:
        # Compute actual distance
        dist_km = compute_epicentral_distance(
            event_info.latitude, event_info.longitude, lat, lon
        )

        # Get expected PGA from GMPE
        expected_pga = gmpe.predict_pga(event_info.magnitude, dist_km)

        # Generate synthetic record with appropriate PGA
        time, acceleration = generate_synthetic_ground_motion(
            duration=60.0,
            dt=0.01,
            target_pga=expected_pga,
            predominant_freq=2.0,
            bandwidth=1.5,
            seed=hash(station_id) % 2**31,
        )

        record = SyntheticRecord(
            time=time,
            acceleration=acceleration,
            dt=0.01,
            event_id="synthetic_m71",
            network="SY",
            station=station_id,
            channel="HNE",
            component="E",
            station_latitude=lat,
            station_longitude=lon,
            epicentral_distance_km=dist_km,
            pga=float(np.max(np.abs(acceleration))),
            processing_history=["synthetic"],
        )
        records.append(record)

    return event_info, records


def run_with_real_data():
    """
    Run wave prediction using real SCEDC data.

    Requires obspy and network access.
    """
    from seismic_twin.data import SCEDCS3Fetcher

    print("=" * 60)
    print("Wave Propagation Prediction - Real Data Mode")
    print("=" * 60)
    print()

    # Initialize fetcher
    fetcher = SCEDCS3Fetcher()

    # Ridgecrest M7.1 earthquake
    event_id = "ci38457511"

    print(f"Fetching data for event: {event_id}")
    print("-" * 40)

    # Fetch records from multiple stations
    stations = ["CLC", "JRC2", "SRT", "TOW2", "MPM"]
    records = []

    for station in stations:
        try:
            print(f"  Fetching {station}...")
            record = fetcher.get_ground_motion_record(
                event_id=event_id,
                station=station,
            )
            records.append(record)
            print(f"    OK - PGA: {record.pga:.4f}g, Distance: {record.epicentral_distance_km:.1f} km")
        except Exception as e:
            print(f"    FAILED - {e}")

    if len(records) < 2:
        print("\nError: Need at least 2 stations for cross-validation")
        return

    # Get event info from first record
    from seismic_twin.data.records import EventInfo
    from datetime import datetime

    # We need to get event info - use USGS client
    from obspy.clients.fdsn import Client
    client = Client("USGS")
    catalog = client.get_events(eventid=event_id)
    event = catalog[0]
    origin = event.preferred_origin()
    magnitude = event.preferred_magnitude()

    event_info = EventInfo(
        event_id=event_id,
        origin_time=origin.time.datetime,
        latitude=origin.latitude,
        longitude=origin.longitude,
        depth_km=origin.depth / 1000.0,
        magnitude=magnitude.mag,
        magnitude_type=magnitude.magnitude_type or "Mw",
        region="Ridgecrest, CA",
        source_catalog="USGS",
    )

    print()
    print(f"Event: M{event_info.magnitude:.1f} {event_info.region}")
    print(f"Successfully loaded {len(records)} stations")
    print()

    # Run prediction and validation
    run_prediction_validation(event_info, records)


def run_with_synthetic_data():
    """
    Run wave prediction using synthetic data.

    No external dependencies required.
    """
    print("=" * 60)
    print("Wave Propagation Prediction - Synthetic Data Mode")
    print("=" * 60)
    print()

    event_info, records = create_synthetic_records()

    print(f"Event: M{event_info.magnitude:.1f} {event_info.region} (Synthetic)")
    print(f"Created {len(records)} synthetic station records")
    print()

    # Print station info
    print("Station Summary:")
    print("-" * 50)
    for record in records:
        print(
            f"  {record.station}: Distance={record.epicentral_distance_km:.1f} km, "
            f"PGA={record.pga:.4f}g"
        )
    print()

    # Run prediction and validation
    run_prediction_validation(event_info, records)


def run_prediction_validation(event_info, records):
    """
    Run wave prediction cross-validation and display results.
    """
    print("Running Leave-One-Out Cross-Validation")
    print("-" * 50)

    # Create predictor and validator
    predictor = WaveformPredictor()
    validator = PredictionValidator()

    # Run cross-validation
    pairs = predictor.predict_cross_validation(event_info, records)

    # Validate predictions
    summary = validator.validate_cross_validation(pairs)

    # Print results
    print()
    print("Individual Station Results:")
    print("-" * 70)
    print(f"{'Station':<10} {'Dist (km)':<10} {'PGA Ratio':<12} {'Correlation':<12} {'Grade':<6}")
    print("-" * 70)

    for result in summary.individual_results:
        print(
            f"{result.station_id:<10} "
            f"{result.distance_km:<10.1f} "
            f"{result.peak_metrics.pga_ratio:<12.3f} "
            f"{result.timeseries_metrics.correlation:<12.3f} "
            f"{result.quality_grade:<6}"
        )

    print("-" * 70)
    print()

    # Summary statistics
    print("Summary Statistics:")
    print("-" * 40)
    print(f"  Number of stations:    {summary.n_stations}")
    print(f"  Mean PGA ratio:        {summary.mean_pga_ratio:.3f} +/- {summary.std_pga_ratio:.3f}")
    print(f"  Mean correlation:      {summary.mean_correlation:.3f}")
    print(f"  Mean overall score:    {summary.mean_overall_score:.3f}")
    print()

    # Quality assessment
    grades = [r.quality_grade for r in summary.individual_results]
    grade_counts = {g: grades.count(g) for g in "ABCDF" if grades.count(g) > 0}

    print("Quality Distribution:")
    print("-" * 40)
    for grade, count in sorted(grade_counts.items()):
        pct = count / len(grades) * 100
        bar = "#" * int(pct / 5)
        print(f"  Grade {grade}: {count} stations ({pct:.0f}%) {bar}")
    print()

    # Interpretation
    print("Interpretation:")
    print("-" * 40)
    if summary.mean_correlation > 0.7:
        print("  * Excellent waveform correlation - predictions capture phase well")
    elif summary.mean_correlation > 0.5:
        print("  * Good waveform correlation - predictions are reasonable")
    else:
        print("  * Lower correlation - GMPE scaling captures amplitude but not phase")

    if 0.7 <= summary.mean_pga_ratio <= 1.3:
        print("  * PGA predictions are well-calibrated (within 30%)")
    elif summary.mean_pga_ratio < 0.7:
        print("  * PGA tends to be under-predicted")
    else:
        print("  * PGA tends to be over-predicted")

    print()
    print("=" * 60)
    print("Wave prediction example completed successfully!")
    print("=" * 60)


def main():
    """Main entry point."""
    # Try real data first, fall back to synthetic
    try:
        import obspy  # noqa: F401
        print("ObsPy detected - attempting to use real data...")
        print()
        try:
            run_with_real_data()
        except Exception as e:
            print(f"\nFailed to fetch real data: {e}")
            print("Falling back to synthetic data mode...\n")
            run_with_synthetic_data()
    except ImportError:
        print("ObsPy not installed - using synthetic data mode")
        print("(Install obspy for real seismic data: pip install obspy)")
        print()
        run_with_synthetic_data()


if __name__ == "__main__":
    main()
