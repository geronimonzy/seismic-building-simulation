"""Preset configurations for building and ground motion parameters."""

from __future__ import annotations

import base64
import json
from typing import Any, TypedDict

import dash_bootstrap_components as dbc


class BuildingPresetParams(TypedDict):
    """Building preset parameter structure."""

    n_stories: int
    mass_per_floor: float  # kg
    stiffness_per_story: float  # N/m
    damping_ratio: float  # fraction
    story_height: float  # m


class BuildingPreset(TypedDict):
    """Building preset structure."""

    name: str
    description: str
    params: BuildingPresetParams


class GroundMotionPresetParams(TypedDict):
    """Ground motion preset parameter structure."""

    target_pga: float  # g
    duration: float  # s
    predominant_freq: float  # Hz
    bandwidth: float  # Hz


class GroundMotionPreset(TypedDict):
    """Ground motion preset structure."""

    name: str
    description: str
    params: GroundMotionPresetParams


# Required fields for JSON import validation
BUILDING_REQUIRED_FIELDS = [
    "n_stories",
    "mass_per_floor",
    "stiffness_per_story",
    "damping_ratio",
    "story_height",
]

GROUND_MOTION_REQUIRED_FIELDS = [
    "target_pga",
    "duration",
    "predominant_freq",
    "bandwidth",
]


# Building presets
BUILDING_PRESETS: dict[str, BuildingPreset] = {
    "low_rise_rc": {
        "name": "Low-rise RC Frame",
        "description": "Typical 3-story reinforced concrete frame building",
        "params": {
            "n_stories": 3,
            "mass_per_floor": 150_000,
            "stiffness_per_story": 80_000_000,
            "damping_ratio": 0.05,
            "story_height": 3.5,
        },
    },
    "mid_rise_rc": {
        "name": "Mid-rise RC Frame",
        "description": "8-story reinforced concrete frame building",
        "params": {
            "n_stories": 8,
            "mass_per_floor": 120_000,
            "stiffness_per_story": 100_000_000,
            "damping_ratio": 0.05,
            "story_height": 3.2,
        },
    },
    "high_rise_steel": {
        "name": "High-rise Steel",
        "description": "Tall 20-story steel moment frame building",
        "params": {
            "n_stories": 20,
            "mass_per_floor": 100_000,
            "stiffness_per_story": 150_000_000,
            "damping_ratio": 0.02,
            "story_height": 3.8,
        },
    },
    "historic_masonry": {
        "name": "Historic Masonry",
        "description": "Older 4-story unreinforced masonry building",
        "params": {
            "n_stories": 4,
            "mass_per_floor": 200_000,
            "stiffness_per_story": 50_000_000,
            "damping_ratio": 0.08,
            "story_height": 3.0,
        },
    },
    "light_wood_frame": {
        "name": "Light Wood Frame",
        "description": "2-story residential wood construction",
        "params": {
            "n_stories": 2,
            "mass_per_floor": 30_000,
            "stiffness_per_story": 15_000_000,
            "damping_ratio": 0.05,
            "story_height": 2.8,
        },
    },
    "industrial_steel": {
        "name": "Industrial Steel",
        "description": "Single-story industrial warehouse/factory",
        "params": {
            "n_stories": 1,
            "mass_per_floor": 500_000,
            "stiffness_per_story": 200_000_000,
            "damping_ratio": 0.03,
            "story_height": 8.0,
        },
    },
}

# Ground motion presets
GROUND_MOTION_PRESETS: dict[str, GroundMotionPreset] = {
    "moderate_stiff_soil": {
        "name": "Moderate - Stiff Soil",
        "description": "Typical moderate event on firm ground",
        "params": {
            "target_pga": 0.2,
            "duration": 20,
            "predominant_freq": 3.0,
            "bandwidth": 2.0,
        },
    },
    "strong_soft_soil": {
        "name": "Strong - Soft Soil",
        "description": "Strong event amplified by soft soil",
        "params": {
            "target_pga": 0.4,
            "duration": 40,
            "predominant_freq": 1.5,
            "bandwidth": 1.0,
        },
    },
    "very_strong_near_fault": {
        "name": "Very Strong - Near Fault",
        "description": "Near-fault impulsive ground motion",
        "params": {
            "target_pga": 0.6,
            "duration": 15,
            "predominant_freq": 2.0,
            "bandwidth": 2.5,
        },
    },
    "design_level_dbe": {
        "name": "Design Level (DBE)",
        "description": "Code design basis earthquake",
        "params": {
            "target_pga": 0.3,
            "duration": 30,
            "predominant_freq": 2.0,
            "bandwidth": 1.5,
        },
    },
    "maximum_considered_mce": {
        "name": "Maximum Considered (MCE)",
        "description": "Maximum considered earthquake",
        "params": {
            "target_pga": 0.5,
            "duration": 40,
            "predominant_freq": 1.8,
            "bandwidth": 1.5,
        },
    },
    "low_seismicity": {
        "name": "Low Seismicity",
        "description": "Moderate zone typical event",
        "params": {
            "target_pga": 0.1,
            "duration": 15,
            "predominant_freq": 4.0,
            "bandwidth": 2.5,
        },
    },
}


def _get_preset_options(presets: dict[str, Any]) -> list[dict[str, str]]:
    """Build dropdown options from a presets dictionary."""
    options = [{"label": "Custom", "value": "custom"}]
    options.extend(
        {"label": preset["name"], "value": preset_id} for preset_id, preset in presets.items()
    )
    return options


def get_building_preset_options() -> list[dict[str, str]]:
    """Get dropdown options for building presets."""
    return _get_preset_options(BUILDING_PRESETS)


def get_ground_motion_preset_options() -> list[dict[str, str]]:
    """Get dropdown options for ground motion presets."""
    return _get_preset_options(GROUND_MOTION_PRESETS)


def get_building_preset(preset_id: str) -> BuildingPreset | None:
    """Get a building preset by ID."""
    return BUILDING_PRESETS.get(preset_id)


def get_ground_motion_preset(preset_id: str) -> GroundMotionPreset | None:
    """Get a ground motion preset by ID."""
    return GROUND_MOTION_PRESETS.get(preset_id)


def decode_uploaded_json(contents: str) -> dict[str, Any]:
    """
    Decode base64-encoded JSON content from file upload.

    Parameters
    ----------
    contents : str
        Base64-encoded file contents from dcc.Upload component.

    Returns
    -------
    dict
        Parsed JSON data.

    Raises
    ------
    ValueError
        If the content cannot be decoded or parsed.
    """
    try:
        _, content_string = contents.split(",")
        decoded = base64.b64decode(content_string).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid JSON file: {e}") from e


def validate_preset_fields(data: dict[str, Any], required_fields: list[str]) -> list[str]:
    """
    Validate that all required fields are present in preset data.

    Parameters
    ----------
    data : dict
        The preset data to validate.
    required_fields : list[str]
        List of required field names.

    Returns
    -------
    list[str]
        List of missing field names (empty if all present).
    """
    return [field for field in required_fields if field not in data]


def create_import_alert(
    message: str,
    color: str,
    duration: int | None = None,
) -> dbc.Alert:
    """
    Create a dismissable alert for import/export operations.

    Parameters
    ----------
    message : str
        Alert message text.
    color : str
        Bootstrap color (e.g., "success", "danger", "warning").
    duration : Optional[int]
        Auto-dismiss duration in milliseconds, or None for no auto-dismiss.

    Returns
    -------
    dbc.Alert
        Configured alert component.
    """
    return dbc.Alert(
        message,
        color=color,
        dismissable=True,
        is_open=True,
        duration=duration,
    )
