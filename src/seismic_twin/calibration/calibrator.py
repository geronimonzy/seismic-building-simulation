"""
Sensor-Based Model Calibration

This module implements iterative calibration of structural models
using measured response data from sensors.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from seismic_twin.analysis import newmark_beta
from seismic_twin.analysis.metrics import compute_correlation, compute_nrmse
from seismic_twin.building import MDOFShearBuilding


@dataclass
class CalibrationResult:
    """Container for calibration iteration results."""

    iteration: int
    stiffness_factor: float
    damping_ratio: float
    nrmse: float
    correlation: float
    prediction: NDArray[np.floating]


class StructuralCalibration:
    """
    Sensor-based calibration for MDOF structural models.

    This class implements iterative model updating to match measured
    response data by adjusting stiffness and damping parameters.

    Parameters
    ----------
    model : MDOFShearBuilding
        Initial structural model.
    ground_acceleration : ndarray
        Ground acceleration time history (in g).
    dt : float
        Time step in seconds.
    measured_displacement : ndarray
        Measured displacement time history (n_sensors x n_steps).
    sensor_floors : array_like
        Floor indices where sensors are located (0-indexed).

    Attributes
    ----------
    history : list of CalibrationResult
        History of calibration iterations.
    """

    def __init__(
        self,
        model: MDOFShearBuilding,
        ground_acceleration: NDArray[np.floating],
        dt: float,
        measured_displacement: NDArray[np.floating],
        sensor_floors: NDArray[np.integer],
    ) -> None:
        self.model = model.copy()
        self.initial_model = model.copy()
        self.ground_acceleration = ground_acceleration
        self.dt = dt
        self.measured_displacement = np.atleast_2d(measured_displacement)
        self.sensor_floors = np.asarray(sensor_floors)

        self.history: list[CalibrationResult] = []
        self._current_stiffness_factor = 1.0

    def compute_residuals(self) -> tuple[float, float, NDArray[np.floating]]:
        """
        Compute residuals between model prediction and measurements.

        Returns
        -------
        nrmse : float
            Normalized root mean square error.
        correlation : float
            Pearson correlation coefficient.
        prediction : ndarray
            Predicted displacement at sensor locations.
        """
        # Run simulation
        result = newmark_beta(
            M=self.model.M,
            C=self.model.C,
            K=self.model.K,
            ground_acceleration=self.ground_acceleration,
            dt=self.dt,
        )

        # Extract prediction at sensor locations
        prediction = result.displacement[self.sensor_floors, :]

        # Compute metrics (average over all sensors)
        nrmse_values = []
        corr_values = []

        for i in range(len(self.sensor_floors)):
            nrmse_values.append(compute_nrmse(prediction[i, :], self.measured_displacement[i, :]))
            corr_values.append(
                compute_correlation(prediction[i, :], self.measured_displacement[i, :])
            )

        avg_nrmse = np.mean(nrmse_values)
        avg_corr = np.mean(corr_values)

        return avg_nrmse, avg_corr, prediction

    def update_stiffness(self, scale_factor: float) -> None:
        """
        Update model stiffness by a scale factor.

        Parameters
        ----------
        scale_factor : float
            Multiplicative factor for all stiffnesses.
        """
        self._current_stiffness_factor *= scale_factor
        self.model.update_stiffness(scale_factor)

    def update_damping(self, new_damping_ratio: float) -> None:
        """
        Update model damping ratio.

        Parameters
        ----------
        new_damping_ratio : float
            New damping ratio.
        """
        self.model.update_damping(new_damping_ratio)

    def run_iteration(
        self,
        stiffness_adjustment: float = 1.0,
        damping_adjustment: Optional[float] = None,
    ) -> CalibrationResult:
        """
        Run a single calibration iteration.

        Parameters
        ----------
        stiffness_adjustment : float
            Factor to multiply current stiffness by.
        damping_adjustment : float, optional
            New damping ratio. If None, keeps current value.

        Returns
        -------
        CalibrationResult
            Results of this iteration.
        """
        # Apply adjustments
        if stiffness_adjustment != 1.0:
            self.update_stiffness(stiffness_adjustment)

        if damping_adjustment is not None:
            self.update_damping(damping_adjustment)

        # Compute residuals
        nrmse, correlation, prediction = self.compute_residuals()

        # Record result
        result = CalibrationResult(
            iteration=len(self.history) + 1,
            stiffness_factor=self._current_stiffness_factor,
            damping_ratio=self.model.damping_ratio,
            nrmse=nrmse,
            correlation=correlation,
            prediction=prediction,
        )
        self.history.append(result)

        return result

    def calibrate(
        self,
        max_iterations: int = 10,
        tolerance: float = 0.01,
        stiffness_bounds: tuple[float, float] = (0.5, 2.0),
        damping_bounds: tuple[float, float] = (0.01, 0.10),
    ) -> CalibrationResult:
        """
        Run automatic calibration using gradient-free optimization.

        Uses a simple grid search followed by local refinement.

        Parameters
        ----------
        max_iterations : int
            Maximum number of iterations.
        tolerance : float
            NRMSE tolerance for convergence.
        stiffness_bounds : tuple
            (min, max) bounds for stiffness factor.
        damping_bounds : tuple
            (min, max) bounds for damping ratio.

        Returns
        -------
        CalibrationResult
            Best calibration result.
        """
        # Initial evaluation
        result = self.run_iteration()

        if result.nrmse < tolerance:
            return result

        best_result = result
        best_nrmse = result.nrmse

        # Grid search phase
        stiffness_grid = np.linspace(stiffness_bounds[0], stiffness_bounds[1], 5)
        damping_grid = np.linspace(damping_bounds[0], damping_bounds[1], 3)

        for k_factor in stiffness_grid:
            for xi in damping_grid:
                if len(self.history) >= max_iterations:
                    break

                # Reset to initial model
                self.model = self.initial_model.copy()
                self._current_stiffness_factor = 1.0

                # Apply parameters
                result = self.run_iteration(
                    stiffness_adjustment=k_factor,
                    damping_adjustment=xi,
                )

                if result.nrmse < best_nrmse:
                    best_nrmse = result.nrmse
                    best_result = result

                if result.nrmse < tolerance:
                    return result

        # Set model to best parameters found
        self.model = self.initial_model.copy()
        self._current_stiffness_factor = 1.0
        self.model.update_stiffness(best_result.stiffness_factor)
        self.model.update_damping(best_result.damping_ratio)

        return best_result

    def run_simple_calibration(
        self,
        n_iterations: int = 5,
        stiffness_learning_rate: float = 0.1,
        damping_learning_rate: float = 0.01,
    ) -> CalibrationResult:
        """
        Run simple iterative calibration based on response frequency matching.

        This method adjusts stiffness based on the ratio of measured to
        predicted predominant frequencies.

        Parameters
        ----------
        n_iterations : int
            Number of iterations.
        stiffness_learning_rate : float
            Learning rate for stiffness updates.
        damping_learning_rate : float
            Learning rate for damping updates.

        Returns
        -------
        CalibrationResult
            Final calibration result.
        """
        # Initial evaluation
        result = self.run_iteration()

        for _ in range(n_iterations - 1):
            # Estimate frequency ratio from phase shift
            # Simple heuristic: if prediction leads measurement, increase stiffness
            pred = result.prediction[0, :]
            meas = self.measured_displacement[0, :]

            # Cross-correlation to find phase shift
            correlation = np.correlate(pred, meas, mode="full")
            lag = np.argmax(correlation) - len(pred) + 1

            # Adjust stiffness based on lag
            # Positive lag means prediction is delayed -> increase stiffness
            if abs(lag) > 1:
                freq_ratio = 1.0 + stiffness_learning_rate * np.sign(lag)
            else:
                freq_ratio = 1.0

            # Adjust damping based on amplitude ratio
            pred_amp = np.max(np.abs(pred))
            meas_amp = np.max(np.abs(meas))

            if pred_amp > 0:
                amp_ratio = meas_amp / pred_amp
                # If prediction amplitude > measurement, increase damping
                damping_adj = self.model.damping_ratio
                if amp_ratio < 0.95:
                    damping_adj *= 1.0 + damping_learning_rate
                elif amp_ratio > 1.05:
                    damping_adj *= 1.0 - damping_learning_rate

                damping_adj = np.clip(damping_adj, 0.01, 0.15)
            else:
                damping_adj = self.model.damping_ratio

            result = self.run_iteration(
                stiffness_adjustment=freq_ratio,
                damping_adjustment=damping_adj,
            )

        return result

    def reset(self) -> None:
        """Reset calibration to initial state."""
        self.model = self.initial_model.copy()
        self._current_stiffness_factor = 1.0
        self.history.clear()

    def get_calibrated_model(self) -> MDOFShearBuilding:
        """Return a copy of the calibrated model."""
        return self.model.copy()

    def get_convergence_history(self) -> tuple[NDArray, NDArray]:
        """
        Get convergence history arrays.

        Returns
        -------
        iterations : ndarray
            Iteration numbers.
        nrmse : ndarray
            NRMSE values at each iteration.
        """
        iterations = np.array([r.iteration for r in self.history])
        nrmse = np.array([r.nrmse for r in self.history])
        return iterations, nrmse
