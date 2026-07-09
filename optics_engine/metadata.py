from __future__ import annotations

import os
import platform
from importlib import metadata as importlib_metadata
from typing import Any

ENGINE_VERSION = "0.1.0"
API_SCHEMA_VERSION = "2.3.0"
RESULT_SCHEMA_VERSION = "2.3.0"
MATERIAL_CATALOG_VERSION = "0.1.0"
PRESET_VERSION = "0.1.0"

IMAGE_PLANE_POLICY_MODES = [
    "fixed_sensor",
    "paraxial_image",
    "best_focus_rms",
    "best_focus_mtf",
    "best_focus_merit",
    "custom_offset",
    "sweep",
]

METRIC_CODES = [
    "rms_spot_radius",
    "spot_diagram",
    "ray_fan",
    "distortion",
    "field_curvature",
    "axial_color",
    "lateral_color",
    "relative_illumination",
    "psf",
    "mtf",
    "angular_mtf",
    "edge_thickness",
    "merit",
]

ERROR_CODES = [
    "artifact_expired",
    "artifact_not_found",
    "duplicate_surface_id",
    "group_overlap",
    "image_plane_policy_not_applicable",
    "infeasible",
    "invalid_asphere_surface",
    "invalid_group_range",
    "invalid_tilt_range",
    "material_not_found",
    "mirror_thickness_sign",
    "missing_eye_reference",
    "missing_focal_length",
    "missing_sensor",
    "missing_terminal_eye_reference",
    "missing_terminal_sensor",
    "multiple_aperture_stops",
    "negative_air_gap",
    "no_valid_rays",
    "optics_value_error",
    "system_not_found",
    "total_internal_reflection",
    "unknown_focus_group",
    "unknown_group",
    "unknown_group_surface",
    "unknown_image_plane_policy",
    "unknown_material",
    "unknown_tilt_target",
    "unknown_zoom_group",
    "unknown_zoom_position",
]

WARNING_CODES = [
    "aiming_failed",
    "edge_thickness_below_min",
    "min_air_gap",
    "missing_aperture_stop",
    "radius_key_deprecated",
    "solve_not_converged",
]

RAY_STATUS_CODES = [
    "alive",
    "blocked",
    "missed",
    "total_internal_reflection",
    "aiming_failed",
]

VARIABLE_KEY_PATTERNS = [
    "iris_radius_mm",
    "{surface_id}_radius_mm",
    "{surface_id}_curvature",
    "{surface_id}_thickness_after_mm",
    "{surface_id}_focal_length_mm",
    "{surface_id}_semi_diameter_mm",
    "{group_id}_shift_x_mm",
    "{group_id}_shift_y_mm",
    "{group_id}_shift_z_mm",
]


def health_payload() -> dict[str, str]:
    return {"status": "ok"}


def _package_version(name: str) -> str | None:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return None


def meta_payload() -> dict[str, Any]:
    return {
        "engine_version": ENGINE_VERSION,
        "api_schema_version": API_SCHEMA_VERSION,
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "material_catalog_version": MATERIAL_CATALOG_VERSION,
        "preset_version": PRESET_VERSION,
        "capabilities": {
            "diffraction_psf": False,
            "async_jobs": False,
            "artifact_store": True,
            "artifacts": {
                "enabled": True,
                "ttl_seconds": float(os.environ.get("OPTICS_ARTIFACT_TTL_SECONDS", "1800.0")),
            },
            "image_plane_policy_modes": IMAGE_PLANE_POLICY_MODES,
            "image_plane_policy_apply_to": ["evaluation_plane", "focus_group", "report_only"],
            "system_types": ["focal", "afocal"],
        },
        "build": {
            "python_version": platform.python_version(),
            "numpy_version": _package_version("numpy"),
            "pydantic_version": _package_version("pydantic"),
            "numba_enabled": False,
        },
        "enumerations": {
            "metrics": METRIC_CODES,
            "error_codes": ERROR_CODES,
            "warning_codes": WARNING_CODES,
            "ray_status_codes": RAY_STATUS_CODES,
            "variable_key_patterns": VARIABLE_KEY_PATTERNS,
        },
    }
