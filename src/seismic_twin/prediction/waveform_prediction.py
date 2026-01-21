"""
Waveform Prediction Module

This module provides functionality for predicting ground motion waveforms
at target locations using recordings from nearby seismic stations and
GMPE-based amplitude scaling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from seismic_twin.prediction.distance import compute_epicentral_distance, compute_rjb_distance
from seismic_twin.prediction.gmpe import BaseGMPE, BooreAtkinson2008

if TYPE_CHECKING:
    from seismic_twin.data.records import EventInfo, GroundMotionRecord


@dataclass
class StationPrediction:
    """
    Prediction result for a target station.

    Attributes
    ----------
    target_station_id : str
        Identifier for the target station.
    target_lat : float
        Target station latitude.
    target_lon : float
        Target station longitude.
    target_distance_km : float
        Target Rjb distance in km.
    predicted_waveform : NDArray
        Predicted acceleration time history in g.
    predicted_pga : float
        Predicted peak ground acceleration in g.
    source_station_id : str
        Station used as source for prediction.
    source_distance_km : float
        Source station Rjb distance in km.
    scale_factor : float
        Amplitude scaling factor applied.
    time : NDArray
        Time vector in seconds.
    dt : float
        Time step in seconds.
    actual_waveform : NDArray, optional
        Actual recorded waveform (for validation).
    actual_pga : float, optional
        Actual recorded PGA (for validation).
    """

    target_station_id: str
    target_lat: float
    target_lon: float
    target_distance_km: float
    predicted_waveform: NDArray[np.floating]
    predicted_pga: float
    source_station_id: str
    source_distance_km: float
    scale_factor: float
    time: NDArray[np.floating]
    dt: float
    actual_waveform: NDArray[np.floating] | None = None
    actual_pga: float | None = None


@dataclass
class PredictionPair:
    """
    A pair of predicted and actual waveforms for validation.

    Attributes
    ----------
    station_id : str
        Station identifier.
    distance_km : float
        Station distance from epicenter in km.
    time : NDArray
        Time vector in seconds.
    dt : float
        Time step in seconds.
    predicted : NDArray
        Predicted waveform in g.
    actual : NDArray
        Actual recorded waveform in g.
    scale_factor : float
        Scaling factor used for prediction.
    source_station : str
        Station used as prediction source.
    """

    station_id: str
    distance_km: float
    time: NDArray[np.floating]
    dt: float
    predicted: NDArray[np.floating]
    actual: NDArray[np.floating]
    scale_factor: float
    source_station: str


class WaveformPredictor:
    """
    Predicts ground motion waveforms at target locations using GMPE scaling.

    Uses a GMPE to compute the expected amplitude ratio between a source
    recording location and a target location, then scales the source
    waveform accordingly.

    Parameters
    ----------
    gmpe : BaseGMPE, optional
        GMPE model to use for predictions. Defaults to BooreAtkinson2008.
    vs30 : float
        Reference Vs30 for predictions. Default is 760 m/s (rock).

    Examples
    --------
    >>> from seismic_twin.prediction import WaveformPredictor
    >>> predictor = WaveformPredictor()
    >>> prediction = predictor.predict_at_location(
    ...     target_lat=35.7,
    ...     target_lon=-117.5,
    ...     target_station_id="TARGET",
    ...     event_info=event,
    ...     source_records=[record1, record2],
    ... )
    """

    def __init__(
        self,
        gmpe: BaseGMPE | None = None,
        vs30: float = 760.0,
    ) -> None:
        """Initialize the predictor."""
        self.gmpe = gmpe or BooreAtkinson2008()
        self.vs30 = vs30

    def predict_at_location(
        self,
        target_lat: float,
        target_lon: float,
        target_station_id: str,
        event_info: EventInfo,
        source_records: list[GroundMotionRecord],
        source_selection: str = "nearest",
    ) -> StationPrediction:
        """
        Predict waveform at a target location.

        Parameters
        ----------
        target_lat : float
            Target latitude in degrees.
        target_lon : float
            Target longitude in degrees.
        target_station_id : str
            Identifier for the target.
        event_info : EventInfo
            Earthquake event information.
        source_records : list[GroundMotionRecord]
            Available source station records.
        source_selection : str
            Method for selecting source station: "nearest" or "best".

        Returns
        -------
        StationPrediction
            Predicted waveform at target location.

        Raises
        ------
        ValueError
            If no suitable source records are available.
        """
        if not source_records:
            raise ValueError("At least one source record is required")

        # Compute target distance
        target_rjb = compute_rjb_distance(
            target_lat,
            target_lon,
            event_info.latitude,
            event_info.longitude,
            event_info.magnitude,
        )

        # Select source station
        source_record = self._select_source_station(
            target_lat,
            target_lon,
            target_station_id,
            source_records,
            source_selection,
        )

        # Compute source distance
        source_rjb = compute_rjb_distance(
            source_record.station_latitude,
            source_record.station_longitude,
            event_info.latitude,
            event_info.longitude,
            event_info.magnitude,
        )

        # Compute scaling factor using GMPE
        scale_factor = self.gmpe.compute_scale_factor(
            magnitude=event_info.magnitude,
            source_distance=source_rjb,
            target_distance=target_rjb,
            vs30=self.vs30,
        )

        # Scale waveform
        predicted_waveform = source_record.acceleration * scale_factor
        predicted_pga = np.max(np.abs(predicted_waveform))

        return StationPrediction(
            target_station_id=target_station_id,
            target_lat=target_lat,
            target_lon=target_lon,
            target_distance_km=target_rjb,
            predicted_waveform=predicted_waveform,
            predicted_pga=predicted_pga,
            source_station_id=source_record.station,
            source_distance_km=source_rjb,
            scale_factor=scale_factor,
            time=source_record.time,
            dt=source_record.dt,
        )

    def _select_source_station(
        self,
        target_lat: float,
        target_lon: float,
        target_station_id: str,
        source_records: list[GroundMotionRecord],
        method: str = "nearest",
    ) -> GroundMotionRecord:
        """
        Select the best source station for prediction.

        Parameters
        ----------
        target_lat : float
            Target latitude.
        target_lon : float
            Target longitude.
        target_station_id : str
            Target station ID (to exclude from sources).
        source_records : list[GroundMotionRecord]
            Available source records.
        method : str
            Selection method: "nearest" (closest to target) or
            "best" (based on quality metrics).

        Returns
        -------
        GroundMotionRecord
            Selected source record.
        """
        # Filter out target station from sources
        valid_records = [
            r for r in source_records if r.station != target_station_id
        ]

        if not valid_records:
            raise ValueError(
                f"No valid source stations available (target={target_station_id})"
            )

        if method == "nearest":
            # Select station closest to target
            distances = []
            for record in valid_records:
                dist = compute_epicentral_distance(
                    target_lat,
                    target_lon,
                    record.station_latitude,
                    record.station_longitude,
                )
                distances.append(dist)

            min_idx = np.argmin(distances)
            return valid_records[min_idx]

        elif method == "best":
            # Select station with highest PGA (presumably best SNR)
            pgas = [record.pga for record in valid_records]
            max_idx = np.argmax(pgas)
            return valid_records[max_idx]

        else:
            raise ValueError(f"Unknown selection method: {method}")

    def predict_cross_validation(
        self,
        event_info: EventInfo,
        all_records: list[GroundMotionRecord],
        source_selection: str = "nearest",
    ) -> list[PredictionPair]:
        """
        Perform leave-one-out cross-validation predictions.

        For each station, predicts its waveform using all other stations
        as potential sources, then compares to the actual recording.

        Parameters
        ----------
        event_info : EventInfo
            Earthquake event information.
        all_records : list[GroundMotionRecord]
            All available station records.
        source_selection : str
            Method for selecting source station.

        Returns
        -------
        list[PredictionPair]
            List of prediction-actual pairs for validation.
        """
        if len(all_records) < 2:
            raise ValueError("At least 2 records required for cross-validation")

        pairs = []

        for target_record in all_records:
            # Get source records (all except target)
            source_records = [r for r in all_records if r.station != target_record.station]

            # Predict at target location
            prediction = self.predict_at_location(
                target_lat=target_record.station_latitude,
                target_lon=target_record.station_longitude,
                target_station_id=target_record.station,
                event_info=event_info,
                source_records=source_records,
                source_selection=source_selection,
            )

            # Create validation pair
            pair = PredictionPair(
                station_id=target_record.station,
                distance_km=prediction.target_distance_km,
                time=prediction.time,
                dt=prediction.dt,
                predicted=prediction.predicted_waveform,
                actual=target_record.acceleration,
                scale_factor=prediction.scale_factor,
                source_station=prediction.source_station_id,
            )
            pairs.append(pair)

        return pairs

    def predict_multiple_targets(
        self,
        targets: list[tuple[float, float, str]],
        event_info: EventInfo,
        source_records: list[GroundMotionRecord],
        source_selection: str = "nearest",
    ) -> list[StationPrediction]:
        """
        Predict waveforms at multiple target locations.

        Parameters
        ----------
        targets : list[tuple[float, float, str]]
            List of (latitude, longitude, station_id) tuples.
        event_info : EventInfo
            Earthquake event information.
        source_records : list[GroundMotionRecord]
            Available source station records.
        source_selection : str
            Method for selecting source station.

        Returns
        -------
        list[StationPrediction]
            Predictions for all target locations.
        """
        predictions = []

        for lat, lon, station_id in targets:
            prediction = self.predict_at_location(
                target_lat=lat,
                target_lon=lon,
                target_station_id=station_id,
                event_info=event_info,
                source_records=source_records,
                source_selection=source_selection,
            )
            predictions.append(prediction)

        return predictions
