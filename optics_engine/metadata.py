from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from .evaluation_metrics import SUPPORTED_EVALUATE_METRICS
from .variables import variable_key_patterns

ENGINE_VERSION = "0.1.0"
API_SCHEMA_VERSION = "2.4.0"
RESULT_SCHEMA_VERSION = "2.4.0"
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

METRIC_CODES = list(SUPPORTED_EVALUATE_METRICS)

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
    "invalid_visual_composite_boundary",
    "material_not_found",
    "mirror_thickness_sign",
    "missing_eye_reference",
    "missing_eye_reference_offset",
    "missing_focal_length",
    "missing_sensor",
    "missing_schematic_eye_surfaces",
    "missing_terminal_eye_reference",
    "missing_terminal_sensor",
    "missing_terminal_retina_sensor",
    "multiple_aperture_stops",
    "negative_air_gap",
    "no_valid_rays",
    "optics_value_error",
    "retinal_aperture_stop_not_supported",
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
    "visual_composite_requires_afocal",
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

VARIABLE_KEY_PATTERNS = variable_key_patterns()

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STARTED_AT = datetime.now(timezone.utc).isoformat()


def _git_output(args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except Exception:
        return None
    return completed.stdout.strip()


def _load_build_info() -> dict[str, Any]:
    commit = _git_output(["rev-parse", "--short", "HEAD"]) or "unknown"
    status = _git_output(["status", "--porcelain"])
    return {
        "git_commit": commit,
        "git_dirty": True if status is None else bool(status),
        "started_at": _STARTED_AT,
    }


BUILD_INFO = _load_build_info()


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
        "build_info": dict(BUILD_INFO),
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
            "visual_evaluation_modes": ["instrument_only", "instrument_and_retinal"],
            "schematic_eye_models": ["gullstrand_simplified_relaxed"],
            "retina_surface_types": ["plane"],
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
