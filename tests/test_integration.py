"""Integration tests for complete analysis workflows."""

import numpy as np

from seismic_twin.analysis import compute_demand_metrics, newmark_beta
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.calibration import StructuralCalibration
from seismic_twin.ground_motion import generate_synthetic_ground_motion
from seismic_twin.uncertainty import UncertaintyAnalysis


class TestCompleteWorkflow:
    """Test complete analysis workflows."""

    def test_basic_workflow(self):
        """Test basic: build model -> generate motion -> run analysis -> compute metrics."""
        # Step 1: Create building model
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
            story_heights=np.array([3.5, 3.5, 3.0]),
        )

        # Step 2: Generate ground motion
        time, ground_acc = generate_synthetic_ground_motion(
            duration=20.0,
            dt=0.01,
            target_pga=0.3,
            seed=42,
        )

        # Step 3: Run time history analysis
        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt=0.01)

        # Step 4: Compute demand metrics
        metrics = compute_demand_metrics(
            result.displacement,
            result.velocity,
            result.absolute_acceleration,
            ground_acc,
            model.story_heights,
        )

        # Verify results
        assert result.displacement.shape == (3, len(time))
        assert len(metrics.max_displacement) == 3
        assert len(metrics.inter_story_drift_ratio) == 3
        assert np.all(metrics.max_displacement > 0)

    def test_workflow_with_calibration(self):
        """Test workflow including calibration step."""
        # Step 1: Create "true" building model
        true_model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
            story_heights=np.array([3.5, 3.5, 3.0]),
        )

        # Step 2: Generate ground motion
        time, ground_acc = generate_synthetic_ground_motion(
            duration=15.0,
            dt=0.01,
            target_pga=0.25,
            seed=123,
        )

        # Step 3: Simulate "measured" response
        true_result = newmark_beta(true_model.M, true_model.C, true_model.K, ground_acc, dt=0.01)
        measured_displacement = true_result.displacement

        # Step 4: Create initial (perturbed) model
        initial_model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6 * 1.15, 50e6 * 1.15, 50e6 * 1.15]),  # 15% high
            damping_ratio=0.06,  # Slightly different damping
            story_heights=np.array([3.5, 3.5, 3.0]),
        )

        # Step 5: Calibrate model
        calibrator = StructuralCalibration(
            model=initial_model,
            ground_acceleration=ground_acc,
            dt=0.01,
            measured_displacement=measured_displacement,
            sensor_floors=np.array([0, 1, 2]),
        )

        best_result = calibrator.calibrate(max_iterations=15, tolerance=0.05)

        # Step 6: Verify calibration improved the fit
        assert best_result.nrmse < 0.2

    def test_workflow_with_uncertainty(self):
        """Test workflow including Monte Carlo uncertainty analysis."""
        # Step 1: Create building model
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6]),
            damping_ratio=0.05,
            story_heights=np.array([3.5, 3.5]),
        )

        # Step 2: Generate ground motion
        time, ground_acc = generate_synthetic_ground_motion(
            duration=10.0,
            dt=0.01,
            target_pga=0.2,
            seed=42,
        )

        # Step 3: Run uncertainty analysis
        ua = UncertaintyAnalysis(
            model=model,
            ground_acceleration=ground_acc,
            dt=0.01,
        )

        result = ua.run_mc_ensemble(
            n_samples=20,
            stiffness_cov=0.1,
            damping_cov=0.2,
            seed=42,
        )

        # Step 4: Verify uncertainty bounds
        assert result.n_samples == 20
        assert result.displacement_bounds is not None

        # Bounds should be ordered correctly
        bounds = result.displacement_bounds
        assert np.all(bounds.percentile_5 <= bounds.percentile_95 + 1e-10)

    def test_full_pipeline_with_all_components(self):
        """Test complete pipeline: model -> motion -> analysis -> calibration -> uncertainty."""
        # Create true model
        true_model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6]),
            damping_ratio=0.05,
            story_heights=np.array([3.5, 3.5]),
        )

        # Generate ground motion
        _, ground_acc = generate_synthetic_ground_motion(
            duration=10.0, dt=0.01, target_pga=0.2, seed=42
        )

        # Get "measurements" from true model
        true_result = newmark_beta(true_model.M, true_model.C, true_model.K, ground_acc, dt=0.01)

        # Create perturbed initial model
        initial_model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3]),
            stiffnesses=np.array([50e6 * 1.1, 50e6 * 1.1]),
            damping_ratio=0.04,
            story_heights=np.array([3.5, 3.5]),
        )

        # Calibrate
        calibrator = StructuralCalibration(
            model=initial_model,
            ground_acceleration=ground_acc,
            dt=0.01,
            measured_displacement=true_result.displacement,
            sensor_floors=np.array([0, 1]),
        )
        calibrator.calibrate(max_iterations=10)

        # Get calibrated model
        calibrated_model = calibrator.get_calibrated_model()

        # Run uncertainty analysis on calibrated model
        ua = UncertaintyAnalysis(
            model=calibrated_model,
            ground_acceleration=ground_acc,
            dt=0.01,
        )

        mc_result = ua.run_mc_ensemble(n_samples=10, stiffness_cov=0.05, seed=42)

        # Verify pipeline completed successfully
        assert mc_result is not None
        assert mc_result.n_samples == 10


class TestDataConsistency:
    """Test data consistency across modules."""

    def test_displacement_shape_consistency(self):
        """Test displacement array shapes are consistent."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6, 50e6]),
            damping_ratio=0.05,
        )

        dt = 0.01
        n_steps = 1000
        ground_acc = np.zeros(n_steps)

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)

        assert result.displacement.shape[0] == model.n_dof
        assert result.displacement.shape[1] == n_steps
        assert result.velocity.shape == result.displacement.shape
        assert result.acceleration.shape == result.displacement.shape
        assert len(result.time) == n_steps

    def test_matrix_symmetry(self):
        """Test that M, C, K matrices are symmetric."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 90e3, 80e3]),
            stiffnesses=np.array([50e6, 45e6, 40e6]),
            damping_ratio=0.05,
        )

        np.testing.assert_allclose(model.M, model.M.T)
        np.testing.assert_allclose(model.K, model.K.T)
        np.testing.assert_allclose(model.C, model.C.T)

    def test_ground_motion_pga_accuracy(self):
        """Test that generated ground motion matches target PGA."""
        target_pga = 0.3  # in g

        for seed in [1, 42, 123]:
            _, acc = generate_synthetic_ground_motion(
                duration=20.0,
                dt=0.01,
                target_pga=target_pga,
                seed=seed,
            )

            # Both target_pga and acc are in g units
            actual_pga = np.max(np.abs(acc))
            # Should match target PGA exactly (function scales to target)
            np.testing.assert_allclose(actual_pga, target_pga, rtol=0.01)


class TestReproducibility:
    """Test reproducibility of analyses."""

    def test_ground_motion_reproducibility(self):
        """Test ground motion generation is reproducible with seed."""
        _, acc1 = generate_synthetic_ground_motion(duration=10.0, dt=0.01, target_pga=0.2, seed=42)
        _, acc2 = generate_synthetic_ground_motion(duration=10.0, dt=0.01, target_pga=0.2, seed=42)

        np.testing.assert_array_equal(acc1, acc2)

    def test_analysis_reproducibility(self):
        """Test time history analysis is deterministic."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6]),
            damping_ratio=0.05,
        )

        _, ground_acc = generate_synthetic_ground_motion(
            duration=5.0, dt=0.01, target_pga=0.2, seed=42
        )

        result1 = newmark_beta(model.M, model.C, model.K, ground_acc, dt=0.01)
        result2 = newmark_beta(model.M, model.C, model.K, ground_acc, dt=0.01)

        np.testing.assert_array_equal(result1.displacement, result2.displacement)

    def test_monte_carlo_reproducibility(self):
        """Test Monte Carlo is reproducible with seed."""
        model = MDOFShearBuilding(
            masses=np.array([100e3, 100e3]),
            stiffnesses=np.array([50e6, 50e6]),
            damping_ratio=0.05,
        )

        _, ground_acc = generate_synthetic_ground_motion(
            duration=5.0, dt=0.01, target_pga=0.2, seed=42
        )

        ua1 = UncertaintyAnalysis(model, ground_acc, dt=0.01)
        result1 = ua1.run_mc_ensemble(n_samples=10, stiffness_cov=0.1, seed=123)

        ua2 = UncertaintyAnalysis(model, ground_acc, dt=0.01)
        result2 = ua2.run_mc_ensemble(n_samples=10, stiffness_cov=0.1, seed=123)

        np.testing.assert_array_equal(result1.all_displacements, result2.all_displacements)
