#!/usr/bin/env python
"""
Seismic Digital Twin - Real Earthquake Analysis

This script demonstrates the full digital twin workflow using real earthquake data:
1. Fetch real earthquake data (2019 Ridgecrest M7.1) from SCEDC AWS S3
2. Create a 4-story building model
3. Run initial prediction
4. Simulate sensor measurements
5. Run sensor-based calibration
6. Run Monte Carlo uncertainty analysis
7. Generate visualization

Output: output/real_earthquake_results.png

Requires: pip install -e ".[dev,data]" (ObsPy for data fetching)
"""

import os

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from seismic_twin.building import MDOFShearBuilding
from seismic_twin.analysis import newmark_beta, compute_demand_metrics
from seismic_twin.calibration import StructuralCalibration
from seismic_twin.uncertainty import UncertaintyAnalysis
from seismic_twin.visualization.plots import create_results_figure


def main():
    print("=" * 60)
    print("Seismic Digital Twin - Real Earthquake Analysis")
    print("=" * 60)

    # =========================================================================
    # Phase 1: Fetch Real Earthquake Data
    # =========================================================================
    print("\n[Phase 1] Fetching real earthquake data...")

    # Import data module (requires obspy)
    try:
        from seismic_twin.data import SCEDCS3Fetcher, DataNotFoundError
    except ImportError as e:
        print(f"ERROR: {e}")
        print("Install ObsPy with: pip install obspy")
        print("Or run in Docker: docker compose run --rm seismic python examples/run_real_earthquake.py")
        return

    # 2019 Ridgecrest M7.1 earthquake
    EVENT_ID = "ci38457511"

    # Initialize S3 fetcher (no rate limits)
    s3_fetcher = SCEDCS3Fetcher()

    print(f"  Event ID: {EVENT_ID}")
    print("  Fetching from SCEDC AWS S3 (no rate limits)...")

    record = None
    channels_to_try = ["HNE", "HNN", "HNZ", "BHE", "BHN"]

    for channel in channels_to_try:
        if record is not None:
            break
        try:
            record = s3_fetcher.get_ground_motion_record(
                event_id=EVENT_ID,
                channel=channel,
                pre_event_sec=10.0,
                post_event_sec=90.0,
                apply_baseline_correction=True,
                apply_highpass_filter=True,
                highpass_freq=0.1,
            )
            break
        except DataNotFoundError:
            print(f"  Channel {channel} not found, trying next...")
            continue
        except Exception as e:
            print(f"  Error with {channel}: {e}")
            continue

    if record is None:
        print("\n  WARNING: Could not fetch real earthquake data from S3.")
        print("  Falling back to synthetic ground motion...\n")
        from seismic_twin.ground_motion import generate_synthetic_ground_motion
        time, ground_acceleration = generate_synthetic_ground_motion(
            duration=60.0,
            dt=0.01,
            target_pga=0.3,
            seed=42,
        )
        dt = 0.01
        station_info = "SYN.SYNTH (Synthetic)"
        pga = np.max(np.abs(ground_acceleration))
    else:
        time, ground_acceleration = record.to_tuple()
        dt = record.dt
        station_info = f"{record.network}.{record.station} ({record.epicentral_distance_km:.1f} km)"
        pga = record.pga

    print(f"  Station: {station_info}")
    print(f"  Duration: {time[-1]:.1f} s")
    print(f"  Time step: {dt * 1000:.1f} ms")
    print(f"  PGA: {pga:.3f} g")

    # =========================================================================
    # Phase 2: Structural Modeling
    # =========================================================================
    print("\n[Phase 2] Creating 4-story building model...")

    # 4-story reinforced concrete building
    n_stories = 4
    floor_mass = 150_000.0  # kg per floor (150 tonnes)
    story_stiffness = 80_000_000.0  # N/m per story (80 MN/m)
    story_height = 3.5  # m

    masses = np.full(n_stories, floor_mass)
    stiffnesses = np.full(n_stories, story_stiffness)
    story_heights = np.full(n_stories, story_height)

    building = MDOFShearBuilding(
        masses=masses,
        stiffnesses=stiffnesses,
        damping_ratio=0.05,
        story_heights=story_heights,
    )

    print(f"  Number of stories: {n_stories}")
    print(f"  Floor mass: {floor_mass / 1000:.0f} tonnes")
    print(f"  Story stiffness: {story_stiffness / 1e6:.0f} MN/m")
    print(f"  Fundamental period T1: {building.natural_periods[0]:.3f} s")
    freqs_hz = building.natural_frequencies / (2 * np.pi)
    print(f"  Natural frequencies: {np.array2string(freqs_hz, precision=2, separator=', ')} Hz")

    # =========================================================================
    # Phase 3: Initial Prediction
    # =========================================================================
    print("\n[Phase 3] Running initial prediction (time history analysis)...")

    initial_result = newmark_beta(
        M=building.M,
        C=building.C,
        K=building.K,
        ground_acceleration=ground_acceleration,
        dt=dt,
    )

    initial_metrics = compute_demand_metrics(
        displacement=initial_result.displacement,
        velocity=initial_result.velocity,
        absolute_acceleration=initial_result.absolute_acceleration,
        ground_acceleration=ground_acceleration,
        story_heights=story_heights,
    )

    print(f"  Max roof displacement: {initial_metrics.max_displacement[-1] * 100:.2f} cm")
    print(f"  Max inter-story drift: {np.max(initial_metrics.inter_story_drift_ratio) * 100:.3f}%")
    print(f"  Max floor acceleration: {np.max(initial_metrics.max_acceleration):.3f} g")

    # =========================================================================
    # Simulate Sensor Measurements
    # =========================================================================
    print("\n[Phase 3b] Simulating sensor measurements...")

    # Create a "true" building with slightly different properties
    # (simulating model uncertainty - true stiffness is 10% lower)
    true_stiffnesses = stiffnesses * 0.9
    true_damping = 0.04

    true_building = MDOFShearBuilding(
        masses=masses,
        stiffnesses=true_stiffnesses,
        damping_ratio=true_damping,
        story_heights=story_heights,
    )

    # Run analysis with "true" building
    true_result = newmark_beta(
        M=true_building.M,
        C=true_building.C,
        K=true_building.K,
        ground_acceleration=ground_acceleration,
        dt=dt,
    )

    # Add measurement noise (5% of signal amplitude)
    np.random.seed(123)
    noise_level = 0.05 * np.max(np.abs(true_result.displacement[-1, :]))
    measured_displacement = true_result.displacement.copy()
    measured_displacement += np.random.normal(0, noise_level, measured_displacement.shape)

    print(f"  True T1: {true_building.natural_periods[0]:.3f} s")
    print(f"  Noise level: {noise_level * 1000:.2f} mm RMS")

    # =========================================================================
    # Phase 4: Sensor-Based Calibration
    # =========================================================================
    print("\n[Phase 4] Running sensor-based calibration...")

    sensor_floors = np.arange(n_stories)

    calibration = StructuralCalibration(
        model=building,
        ground_acceleration=ground_acceleration,
        dt=dt,
        measured_displacement=measured_displacement,
        sensor_floors=sensor_floors,
    )

    best_result = calibration.calibrate(
        max_iterations=15,
        tolerance=0.02,
        stiffness_bounds=(0.7, 1.3),
        damping_bounds=(0.02, 0.08),
    )

    iterations, nrmse_history = calibration.get_convergence_history()

    print(f"  Iterations: {len(iterations)}")
    print(f"  Initial NRMSE: {nrmse_history[0]:.4f}")
    print(f"  Final NRMSE: {best_result.nrmse:.4f}")
    print(f"  Calibrated stiffness factor: {best_result.stiffness_factor:.3f}")
    print(f"  Calibrated damping ratio: {best_result.damping_ratio:.3f}")

    # Get calibrated model and run final analysis
    calibrated_building = calibration.get_calibrated_model()

    calibrated_result = newmark_beta(
        M=calibrated_building.M,
        C=calibrated_building.C,
        K=calibrated_building.K,
        ground_acceleration=ground_acceleration,
        dt=dt,
    )

    calibrated_metrics = compute_demand_metrics(
        displacement=calibrated_result.displacement,
        velocity=calibrated_result.velocity,
        absolute_acceleration=calibrated_result.absolute_acceleration,
        ground_acceleration=ground_acceleration,
        story_heights=story_heights,
    )

    print(f"  Calibrated T1: {calibrated_building.natural_periods[0]:.3f} s")

    # =========================================================================
    # Phase 5: Uncertainty Quantification
    # =========================================================================
    print("\n[Phase 5] Running Monte Carlo uncertainty analysis...")

    n_mc_samples = 50  # Use 50 samples for demo

    uncertainty = UncertaintyAnalysis(
        model=calibrated_building,
        ground_acceleration=ground_acceleration,
        dt=dt,
    )

    mc_result = uncertainty.run_mc_ensemble(
        n_samples=n_mc_samples,
        stiffness_cov=0.05,
        damping_cov=0.20,
        seed=456,
        verbose=True,
    )

    drift_stats = uncertainty.get_drift_statistics()

    print(f"  MC samples: {n_mc_samples}")
    print(f"  Mean max drift: {drift_stats['mean'] * 100:.3f}%")
    print(f"  5th percentile: {drift_stats['p5'] * 100:.3f}%")
    print(f"  95th percentile: {drift_stats['p95'] * 100:.3f}%")

    # =========================================================================
    # Generate Visualization
    # =========================================================================
    print("\n[Visualization] Creating results figure...")

    floor_idx = -1  # Top floor

    fig = create_results_figure(
        time=time,
        ground_acceleration=ground_acceleration,
        initial_displacement=initial_result.displacement,
        calibrated_displacement=calibrated_result.displacement,
        measured_displacement=measured_displacement,
        calibration_iterations=iterations,
        calibration_nrmse=nrmse_history,
        mc_mean=mc_result.displacement_bounds.percentile_50,
        mc_lower=mc_result.displacement_bounds.percentile_5,
        mc_upper=mc_result.displacement_bounds.percentile_95,
        drift_ratios=calibrated_metrics.inter_story_drift_ratio,
        floor=floor_idx,
    )

    # Add overall title with earthquake info
    title = "Seismic Digital Twin - Real Earthquake Analysis\n"
    title += f"2019 Ridgecrest M7.1 | Station: {station_info} | PGA: {pga:.3f}g"
    fig.suptitle(title, fontsize=12, fontweight="bold", y=1.02)

    # Save figure to output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "real_earthquake_results.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"  Results saved to: {output_path}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Earthquake:          2019 Ridgecrest M7.1")
    print(f"Station:             {station_info}")
    print(f"Ground Motion:       PGA={pga:.3f}g, Duration={time[-1]:.0f}s")
    print(f"Building:            {n_stories}-story RC, T1={building.natural_periods[0]:.3f}s")
    print(f"Initial Prediction:  Max drift={np.max(initial_metrics.inter_story_drift_ratio)*100:.3f}%")
    print(f"Calibration:         NRMSE improved {nrmse_history[0]:.4f} -> {best_result.nrmse:.4f}")
    print(f"Uncertainty (95%):   Max drift up to {drift_stats['p95']*100:.3f}%")

    # Performance assessment
    max_drift = np.max(calibrated_metrics.inter_story_drift_ratio)
    if max_drift < 0.01:
        performance = "Immediate Occupancy (IO) - Minor damage"
    elif max_drift < 0.02:
        performance = "Life Safety (LS) - Moderate damage"
    elif max_drift < 0.04:
        performance = "Collapse Prevention (CP) - Significant damage"
    else:
        performance = "Beyond Collapse Prevention - Severe damage"

    print(f"Performance:         {performance}")
    print("=" * 60)
    print("\nWorkflow completed successfully!")


if __name__ == "__main__":
    main()
