#!/usr/bin/env python
"""
Seismic Digital Twin - Complete Workflow Example

This script demonstrates the full workflow for seismic building simulation:
1. Create a 4-story building model (Phase 2)
2. Generate synthetic ground motion (Phase 1)
3. Run initial prediction (Phase 3)
4. Simulate sensor measurements
5. Run sensor-based calibration (Phase 4)
6. Run Monte Carlo uncertainty analysis (Phase 5)
7. Generate visualization

Output: digital_twin_results.png
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

from seismic_twin.building import MDOFShearBuilding
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.analysis import newmark_beta, compute_demand_metrics
from seismic_twin.calibration import StructuralCalibration
from seismic_twin.uncertainty import UncertaintyAnalysis
from seismic_twin.visualization.plots import create_results_figure


def main():
    print("=" * 60)
    print("Seismic Digital Twin - Complete Workflow")
    print("=" * 60)

    # =========================================================================
    # Phase 1: Ground Motion Generation
    # =========================================================================
    print("\n[Phase 1] Generating synthetic ground motion...")

    time, ground_acceleration = generate_synthetic_ground_motion(
        duration=30.0,
        dt=0.01,
        target_pga=0.35,
        predominant_freq=2.5,
        bandwidth=2.0,
        seed=42,
    )

    dt = time[1] - time[0]
    print(f"  Duration: {time[-1]:.1f} s")
    print(f"  Time step: {dt * 1000:.1f} ms")
    print(f"  PGA: {np.max(np.abs(ground_acceleration)):.3f} g")

    # =========================================================================
    # Phase 2: Structural Modeling
    # =========================================================================
    print("\n[Phase 2] Creating 4-story building model...")

    # 4-story building parameters
    n_stories = 4
    floor_mass = 100_000.0  # kg per floor (100 tonnes)
    story_stiffness = 50_000_000.0  # N/m per story (50 MN/m)
    story_height = 3.5  # m

    # Create arrays (masses and stiffnesses can vary by floor)
    masses = np.full(n_stories, floor_mass)
    stiffnesses = np.full(n_stories, story_stiffness)
    story_heights = np.full(n_stories, story_height)

    # Create building model
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
    # (simulating model uncertainty)
    true_stiffnesses = stiffnesses * 0.9  # True stiffness is 10% lower
    true_damping = 0.04  # True damping is 4%

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

    # Assume sensors on all floors
    sensor_floors = np.arange(n_stories)

    calibration = StructuralCalibration(
        model=building,
        ground_acceleration=ground_acceleration,
        dt=dt,
        measured_displacement=measured_displacement,
        sensor_floors=sensor_floors,
    )

    # Run calibration
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

    n_mc_samples = 50  # Use 50 samples for demo (increase for production)

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

    # Use top floor for visualization
    floor_idx = -1

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

    # Add overall title
    fig.suptitle("Seismic Digital Twin - Analysis Results", fontsize=14, fontweight="bold", y=1.02)

    # Save figure
    output_path = "digital_twin_results.png"
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"  Results saved to: {output_path}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Building:            {n_stories}-story, T1={building.natural_periods[0]:.3f}s")
    print(f"Ground Motion:       PGA={np.max(np.abs(ground_acceleration)):.3f}g, Duration={time[-1]:.0f}s")
    print(f"Initial Prediction:  Max drift={np.max(initial_metrics.inter_story_drift_ratio)*100:.3f}%")
    print(f"Calibration:         NRMSE improved {nrmse_history[0]:.4f} -> {best_result.nrmse:.4f}")
    print(f"Uncertainty (95%):   Max drift up to {drift_stats['p95']*100:.3f}%")
    print("=" * 60)
    print("\nWorkflow completed successfully!")


if __name__ == "__main__":
    main()
