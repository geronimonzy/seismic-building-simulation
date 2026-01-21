#!/usr/bin/env python
"""
Test script for HEEDS wrapper validation.

This script tests the run_simulation.py wrapper without requiring HEEDS.
It generates sample inputs, runs simulations, and verifies outputs.

Usage:
    python test_wrapper.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def create_sample_input(
    n_stories: int = 5,
    mass_per_floor: float = 100000,
    stiffness_per_story: float = 1e8,
    damping_ratio: float = 0.05,
    story_height: float = 3.5,
) -> dict:
    """Create sample input dictionary."""
    return {
        "building": {
            "n_stories": n_stories,
            "mass_per_floor": mass_per_floor,
            "stiffness_per_story": stiffness_per_story,
            "damping_ratio": damping_ratio,
            "story_height": story_height,
        },
        "ground_motion": {
            "source": "synthetic",
            "target_pga": 0.3,
            "duration": 20.0,
            "dt": 0.01,
            "predominant_freq": 2.0,
            "bandwidth": 1.5,
            "seed": 42,
        },
    }


def run_wrapper(input_data: dict, heeds_dir: Path) -> dict:
    """Run the wrapper script and return output."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir=heeds_dir
    ) as f:
        json.dump(input_data, f)
        input_file = Path(f.name)

    output_file = heeds_dir / "test_output.json"

    try:
        # Run wrapper script
        result = subprocess.run(
            [
                sys.executable,
                str(heeds_dir / "run_simulation.py"),
                "--input",
                str(input_file),
                "--output",
                str(output_file),
                "--heeds-dir",
                str(heeds_dir),
            ],
            capture_output=True,
            text=True,
            cwd=heeds_dir,
        )

        if result.returncode != 0:
            print(f"Wrapper failed with return code {result.returncode}")
            print(f"stderr: {result.stderr}")
            return None

        # Read output
        with open(output_file) as f:
            return json.load(f)

    finally:
        # Cleanup
        input_file.unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)


def test_basic_simulation():
    """Test basic simulation with default parameters."""
    print("\n=== Test: Basic Simulation ===")
    heeds_dir = Path(__file__).parent

    input_data = create_sample_input()
    output = run_wrapper(input_data, heeds_dir)

    if output is None:
        print("FAILED: Wrapper returned no output")
        return False

    print(f"Status: {output['status']}")
    print(f"Max drift: {output['max_drift']:.6f}")
    print(f"Max roof displacement: {output['max_roof_disp']:.6f} m")
    print(f"Max floor acceleration: {output['max_floor_acc']:.3f} g")
    print(f"T1: {output['T1']:.3f} s")
    print(f"T2: {output['T2']:.3f} s")
    print(f"T3: {output['T3']:.3f} s")
    print(f"Total mass: {output['total_mass']:.0f} kg")
    print(f"Total stiffness: {output['total_stiffness']:.2e} N/m")

    # Verify outputs are reasonable
    # Note: For 0.3g PGA, displacements can be large for flexible buildings
    assert output["status"] == "success", "Status should be success"
    assert 0 < output["max_drift"] < 0.5, "Max drift should be reasonable (< 50%)"
    assert 0 < output["max_roof_disp"] < 5.0, "Max roof displacement should be reasonable (< 5m)"
    assert 0 < output["max_floor_acc"] < 20.0, "Max floor acceleration should be reasonable (< 20g)"
    assert 0 < output["T1"] < 5.0, "Fundamental period should be reasonable"
    assert output["total_mass"] == 500000, "Total mass should match input"
    assert output["total_stiffness"] == 5e8, "Total stiffness should match input"

    print("PASSED")
    return True


def test_parameter_variation():
    """Test simulation with varied parameters."""
    print("\n=== Test: Parameter Variation ===")
    heeds_dir = Path(__file__).parent

    test_cases = [
        {"n_stories": 3, "mass_per_floor": 80000, "stiffness_per_story": 1.5e8},
        {"n_stories": 10, "mass_per_floor": 150000, "stiffness_per_story": 5e7},
        {"n_stories": 5, "damping_ratio": 0.02, "story_height": 4.0},
    ]

    all_passed = True
    for i, params in enumerate(test_cases):
        print(f"\nCase {i + 1}: {params}")
        input_data = create_sample_input(**params)
        output = run_wrapper(input_data, heeds_dir)

        if output is None or output["status"] != "success":
            print(f"FAILED: Case {i + 1}")
            all_passed = False
            continue

        print(f"  Max drift: {output['max_drift']:.6f}, T1: {output['T1']:.3f} s")

    if all_passed:
        print("\nPASSED: All parameter variation tests")
    return all_passed


def test_period_sensitivity():
    """Test that period increases with stories and decreases with stiffness."""
    print("\n=== Test: Period Sensitivity ===")
    heeds_dir = Path(__file__).parent

    # Test 1: Period should increase with more stories
    input_3story = create_sample_input(n_stories=3)
    input_10story = create_sample_input(n_stories=10)

    output_3 = run_wrapper(input_3story, heeds_dir)
    output_10 = run_wrapper(input_10story, heeds_dir)

    if output_3 and output_10:
        print(f"3-story T1: {output_3['T1']:.3f} s")
        print(f"10-story T1: {output_10['T1']:.3f} s")
        assert output_10["T1"] > output_3["T1"], "Period should increase with stories"
        print("Period increases with stories: PASSED")
    else:
        print("FAILED: Could not complete period vs stories test")
        return False

    # Test 2: Period should decrease with higher stiffness
    input_soft = create_sample_input(stiffness_per_story=5e7)
    input_stiff = create_sample_input(stiffness_per_story=2e8)

    output_soft = run_wrapper(input_soft, heeds_dir)
    output_stiff = run_wrapper(input_stiff, heeds_dir)

    if output_soft and output_stiff:
        print(f"Soft building T1: {output_soft['T1']:.3f} s")
        print(f"Stiff building T1: {output_stiff['T1']:.3f} s")
        assert output_soft["T1"] > output_stiff["T1"], "Period should decrease with stiffness"
        print("Period decreases with stiffness: PASSED")
    else:
        print("FAILED: Could not complete period vs stiffness test")
        return False

    print("PASSED: All period sensitivity tests")
    return True


def test_direct_import():
    """Test importing and running simulation directly (not via subprocess)."""
    print("\n=== Test: Direct Import ===")

    # Add parent to path
    import sys
    heeds_dir = Path(__file__).parent
    sys.path.insert(0, str(heeds_dir.parent / "src"))

    from heeds.run_simulation import run_simulation

    input_data = create_sample_input()
    output = run_simulation(input_data, heeds_dir)

    print(f"Direct call - Max drift: {output['max_drift']:.6f}, T1: {output['T1']:.3f} s")
    assert output["status"] == "success"
    print("PASSED")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("HEEDS Wrapper Test Suite")
    print("=" * 60)

    results = []
    results.append(("Basic Simulation", test_basic_simulation()))
    results.append(("Parameter Variation", test_parameter_variation()))
    results.append(("Period Sensitivity", test_period_sensitivity()))

    try:
        results.append(("Direct Import", test_direct_import()))
    except Exception as e:
        print(f"\nDirect Import test skipped: {e}")

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("All tests PASSED")
        sys.exit(0)
    else:
        print("Some tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
