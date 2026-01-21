#!/usr/bin/env python
"""
HEEDS MDO wrapper for seismic building simulation.

This script is executed by HEEDS for each design evaluation. It:
1. Reads building parameters from input JSON file
2. Loads pre-defined ground motion
3. Creates building model and runs seismic simulation
4. Extracts response metrics and writes output JSON file

Usage:
    python run_simulation.py --input input.json --output output.json

HEEDS Configuration:
    - Input file: input.json (with tagged variables)
    - Output file: output.json (with tagged responses)
    - Working directory: heeds/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_ground_motion(gm_config: dict, heeds_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Load ground motion from configuration.

    Parameters
    ----------
    gm_config : dict
        Ground motion configuration from input file.
    heeds_dir : Path
        Directory containing HEEDS files.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Time vector and acceleration array (in g).
    """
    from seismic_twin.ground_motion.synthetic import generate_synthetic_ground_motion

    source = gm_config.get("source", "synthetic")

    if source == "file":
        # Load from external ground motion file
        gm_file = heeds_dir / gm_config.get("file_path", "ground_motion.json")
        with open(gm_file) as f:
            gm_data = json.load(f)
        return load_ground_motion(gm_data, heeds_dir)

    elif source == "synthetic":
        # Generate synthetic ground motion
        time, accel = generate_synthetic_ground_motion(
            duration=gm_config.get("duration", 30.0),
            dt=gm_config.get("dt", 0.01),
            target_pga=gm_config.get("target_pga", 0.3),
            predominant_freq=gm_config.get("predominant_freq", 2.0),
            bandwidth=gm_config.get("bandwidth", 1.5),
            seed=gm_config.get("seed", 42),
        )
        return time, accel

    elif source == "timeseries":
        # Use pre-computed time history
        time = np.array(gm_data.get("time", []))
        accel = np.array(gm_data.get("acceleration", []))
        return time, accel

    else:
        raise ValueError(f"Unknown ground motion source: {source}")


def run_simulation(input_data: dict, heeds_dir: Path) -> dict:
    """
    Run seismic building simulation.

    Parameters
    ----------
    input_data : dict
        Input parameters from HEEDS.
    heeds_dir : Path
        Directory containing HEEDS files.

    Returns
    -------
    dict
        Response metrics for HEEDS.
    """
    from seismic_twin import MDOFShearBuilding
    from seismic_twin.analysis import compute_demand_metrics, newmark_beta

    # Extract building parameters
    building_config = input_data.get("building", {})
    n_stories = int(building_config.get("n_stories", 5))
    mass_per_floor = float(building_config.get("mass_per_floor", 100000))
    stiffness_per_story = float(building_config.get("stiffness_per_story", 1e8))
    damping_ratio = float(building_config.get("damping_ratio", 0.05))
    story_height = float(building_config.get("story_height", 3.5))

    # Create uniform arrays for building model
    masses = np.array([mass_per_floor] * n_stories)
    stiffnesses = np.array([stiffness_per_story] * n_stories)
    story_heights = np.array([story_height] * n_stories)

    # Create building model
    building = MDOFShearBuilding(
        masses=masses,
        stiffnesses=stiffnesses,
        damping_ratio=damping_ratio,
        story_heights=story_heights,
    )

    # Load ground motion
    gm_config = input_data.get("ground_motion", {})
    time, accel_g = load_ground_motion(gm_config, heeds_dir)

    # Convert acceleration to m/s^2
    g = 9.81
    accel = accel_g * g

    # Run time history analysis
    result = newmark_beta(
        M=building.M,
        C=building.C,
        K=building.K,
        ground_acceleration=accel,
        dt=time[1] - time[0],
    )

    # Compute demand metrics
    metrics = compute_demand_metrics(
        displacement=result.displacement,
        velocity=result.velocity,
        absolute_acceleration=result.absolute_acceleration,
        ground_acceleration=accel,
        story_heights=story_heights,
    )

    # Extract modal properties
    periods = building.natural_periods
    T1 = periods[0] if len(periods) > 0 else 0.0
    T2 = periods[1] if len(periods) > 1 else 0.0
    T3 = periods[2] if len(periods) > 2 else 0.0

    # Compute response metrics
    max_drift = float(np.max(metrics.inter_story_drift_ratio))
    max_roof_disp = float(np.max(np.abs(result.displacement[-1, :])))
    max_floor_acc = float(np.max(np.abs(result.absolute_acceleration))) / g  # Convert to g

    # Total structural properties
    total_mass = float(np.sum(masses))
    total_stiffness = float(np.sum(stiffnesses))

    return {
        "max_drift": max_drift,
        "max_roof_disp": max_roof_disp,
        "max_floor_acc": max_floor_acc,
        "T1": T1,
        "T2": T2,
        "T3": T3,
        "total_mass": total_mass,
        "total_stiffness": total_stiffness,
        "status": "success",
    }


def main():
    """Main entry point for HEEDS wrapper."""
    parser = argparse.ArgumentParser(
        description="HEEDS MDO wrapper for seismic building simulation"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file with building parameters",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file for response metrics",
    )
    parser.add_argument(
        "--heeds-dir",
        default=None,
        help="HEEDS working directory (default: input file directory)",
    )
    args = parser.parse_args()

    # Determine HEEDS directory
    input_path = Path(args.input)
    heeds_dir = Path(args.heeds_dir) if args.heeds_dir else input_path.parent

    try:
        # Read input file
        with open(input_path) as f:
            input_data = json.load(f)

        # Run simulation
        output_data = run_simulation(input_data, heeds_dir)

        # Write output file
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"Simulation completed successfully. Results written to {output_path}")
        sys.exit(0)

    except Exception as e:
        # Write error output
        error_output = {
            "max_drift": -1.0,
            "max_roof_disp": -1.0,
            "max_floor_acc": -1.0,
            "T1": -1.0,
            "T2": -1.0,
            "T3": -1.0,
            "total_mass": -1.0,
            "total_stiffness": -1.0,
            "status": f"error: {e}",
        }
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(error_output, f, indent=2)

        print(f"Simulation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
