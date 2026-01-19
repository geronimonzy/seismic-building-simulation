"""Tests for the calibration module."""

import numpy as np
import pytest

from seismic_twin.analysis import newmark_beta
from seismic_twin.building import MDOFShearBuilding
from seismic_twin.calibration import StructuralCalibration
from seismic_twin.calibration.calibrator import CalibrationResult


class TestCalibrationResult:
    """Test CalibrationResult dataclass."""

    def test_calibration_result_creation(self):
        """Test creating a CalibrationResult."""
        result = CalibrationResult(
            iteration=1,
            stiffness_factor=1.0,
            damping_ratio=0.05,
            nrmse=0.1,
            correlation=0.9,
            prediction=np.zeros((3, 100)),
        )
        assert result.iteration == 1
        assert result.stiffness_factor == 1.0
        assert result.damping_ratio == 0.05
        assert result.nrmse == 0.1
        assert result.correlation == 0.9


class TestStructuralCalibration:
    """Test cases for StructuralCalibration class."""

    @pytest.fixture
    def calibration_setup(self, simple_3dof, synthetic_earthquake):
        """Create a calibration setup with synthetic measurements."""
        model = simple_3dof
        ground_acc = synthetic_earthquake["acceleration"]
        dt = synthetic_earthquake["dt"]

        # Generate "true" response as measurements
        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)
        measurements = result.displacement

        return {
            "model": model,
            "ground_acc": ground_acc,
            "dt": dt,
            "measurements": measurements,
            "sensor_floors": np.array([0, 1, 2]),
        }

    def test_calibration_init(self, calibration_setup):
        """Test StructuralCalibration initialization."""
        setup = calibration_setup
        calib = StructuralCalibration(
            model=setup["model"],
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        assert calib.model is not None
        assert calib.dt == setup["dt"]
        assert len(calib.history) == 0

    def test_compute_residuals_perfect_match(self, calibration_setup):
        """Test residuals are zero for perfect match."""
        setup = calibration_setup
        calib = StructuralCalibration(
            model=setup["model"],
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        nrmse, correlation, prediction = calib.compute_residuals()

        # Perfect match should have very low NRMSE and high correlation
        assert nrmse < 0.01, f"NRMSE should be near zero for perfect match: {nrmse}"
        assert correlation > 0.99, f"Correlation should be near 1: {correlation}"

    def test_run_iteration(self, calibration_setup):
        """Test running a single calibration iteration."""
        setup = calibration_setup
        calib = StructuralCalibration(
            model=setup["model"],
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        result = calib.run_iteration()

        assert isinstance(result, CalibrationResult)
        assert result.iteration == 1
        assert len(calib.history) == 1
        assert calib.history[0] == result

    def test_update_stiffness(self, calibration_setup):
        """Test stiffness update."""
        setup = calibration_setup
        calib = StructuralCalibration(
            model=setup["model"],
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        original_stiffness = calib.model.K.copy()
        calib.update_stiffness(1.5)

        # Stiffness should be scaled
        np.testing.assert_allclose(calib.model.K, original_stiffness * 1.5, rtol=1e-10)

    def test_update_damping(self, calibration_setup):
        """Test damping update."""
        setup = calibration_setup
        calib = StructuralCalibration(
            model=setup["model"],
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        calib.update_damping(0.10)
        assert calib.model.damping_ratio == 0.10

    def test_calibrate_convergence(self, simple_3dof, synthetic_earthquake):
        """Test calibration converges for perturbed model."""
        true_model = simple_3dof
        ground_acc = synthetic_earthquake["acceleration"]
        dt = synthetic_earthquake["dt"]

        # Generate measurements from true model
        result = newmark_beta(true_model.M, true_model.C, true_model.K, ground_acc, dt)
        measurements = result.displacement

        # Create perturbed model (20% stiffer)
        perturbed_model = MDOFShearBuilding(
            masses=true_model.masses,
            stiffnesses=true_model.stiffnesses * 1.2,
            damping_ratio=true_model.damping_ratio,
            story_heights=true_model.story_heights,
        )

        calib = StructuralCalibration(
            model=perturbed_model,
            ground_acceleration=ground_acc,
            dt=dt,
            measured_displacement=measurements,
            sensor_floors=np.array([0, 1, 2]),
        )

        best_result = calib.calibrate(max_iterations=20, tolerance=0.05)

        # Should find a reasonable fit
        assert best_result.nrmse < 0.3, f"Calibration did not converge: NRMSE={best_result.nrmse}"
        assert len(calib.history) > 1

    def test_calibrate_with_noise(self, simple_3dof, synthetic_earthquake):
        """Test calibration with noisy measurements."""
        model = simple_3dof
        ground_acc = synthetic_earthquake["acceleration"]
        dt = synthetic_earthquake["dt"]

        # Generate measurements with noise
        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)
        noise_std = 0.001  # 1mm noise
        np.random.seed(42)
        measurements = result.displacement + noise_std * np.random.randn(*result.displacement.shape)

        calib = StructuralCalibration(
            model=model,
            ground_acceleration=ground_acc,
            dt=dt,
            measured_displacement=measurements,
            sensor_floors=np.array([0, 1, 2]),
        )

        nrmse, correlation, _ = calib.compute_residuals()

        # With noise, we expect small but non-zero NRMSE
        assert nrmse > 0
        assert correlation > 0.9

    def test_single_sensor(self, simple_3dof, synthetic_earthquake):
        """Test calibration with single sensor."""
        model = simple_3dof
        ground_acc = synthetic_earthquake["acceleration"]
        dt = synthetic_earthquake["dt"]

        result = newmark_beta(model.M, model.C, model.K, ground_acc, dt)
        measurements = result.displacement[2:3, :]  # Top floor only

        calib = StructuralCalibration(
            model=model,
            ground_acceleration=ground_acc,
            dt=dt,
            measured_displacement=measurements,
            sensor_floors=np.array([2]),
        )

        nrmse, correlation, prediction = calib.compute_residuals()

        assert prediction.shape[0] == 1
        assert nrmse < 0.01

    def test_run_simple_calibration(self, calibration_setup):
        """Test simple iterative calibration."""
        setup = calibration_setup
        # Perturb the model slightly
        perturbed = setup["model"].copy()
        perturbed.update_stiffness(1.1)

        calib = StructuralCalibration(
            model=perturbed,
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        result = calib.run_simple_calibration(n_iterations=3)

        assert isinstance(result, CalibrationResult)
        assert len(calib.history) == 3

    def test_get_calibrated_model(self, calibration_setup):
        """Test getting calibrated model."""
        setup = calibration_setup
        calib = StructuralCalibration(
            model=setup["model"],
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        calib.calibrate(max_iterations=5)
        calibrated = calib.get_calibrated_model()

        assert isinstance(calibrated, MDOFShearBuilding)

    def test_convergence_history(self, calibration_setup):
        """Test getting convergence history."""
        setup = calibration_setup
        calib = StructuralCalibration(
            model=setup["model"],
            ground_acceleration=setup["ground_acc"],
            dt=setup["dt"],
            measured_displacement=setup["measurements"],
            sensor_floors=setup["sensor_floors"],
        )

        calib.calibrate(max_iterations=10)
        iterations, nrmse_history = calib.get_convergence_history()

        assert len(iterations) == len(calib.history)
        assert len(nrmse_history) == len(calib.history)
        assert all(n >= 0 for n in nrmse_history)
