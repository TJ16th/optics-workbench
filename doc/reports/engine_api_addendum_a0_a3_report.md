# Engine API Addendum A0-A3 Report

作成日: 2026-07-09

## Summary

`doc/codex_engine_api_addendum_work_order.md` の A0-A3 を完了した。

| Task | Status | Commit |
|---|---|---|
| A0 Git化 | Done | `057e5db A0 baseline: engine v2.3 and UI U1-U5` |
| A1 image_plane_policy / best-focus | Done | `1e2ba13 A1 implement image plane policy best focus` |
| A2 artifact lifecycle | Done | `739423c A2 implement artifact lifecycle` |
| A3 meta capabilities / enumerations | Done | `0f5b556 A3 verify meta capabilities` |

## Verification

Python tests:

```text
57 passed in 1.10s
```

UI i18n coverage red check:

```text
error code missing glossary error: image_plane_policy_not_applicable
```

This is expected for A3. The UI Phase 2 task should add ja/en glossary entries for the new code and return coverage to green.

## /v1/meta Payload

```json
{
  "api_schema_version": "2.3.0",
  "build": {
    "numba_enabled": false,
    "numpy_version": "2.3.5",
    "pydantic_version": "2.13.4",
    "python_version": "3.12.13"
  },
  "capabilities": {
    "artifact_store": true,
    "artifacts": {
      "enabled": true,
      "ttl_seconds": 1800.0
    },
    "async_jobs": false,
    "diffraction_psf": false,
    "image_plane_policy_apply_to": [
      "evaluation_plane",
      "focus_group",
      "report_only"
    ],
    "image_plane_policy_modes": [
      "fixed_sensor",
      "paraxial_image",
      "best_focus_rms",
      "best_focus_mtf",
      "best_focus_merit",
      "custom_offset",
      "sweep"
    ],
    "system_types": [
      "focal",
      "afocal"
    ]
  },
  "engine_version": "0.1.0",
  "enumerations": {
    "error_codes": [
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
      "unknown_zoom_position"
    ],
    "metrics": [
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
      "merit"
    ],
    "ray_status_codes": [
      "alive",
      "blocked",
      "missed",
      "total_internal_reflection",
      "aiming_failed"
    ],
    "variable_key_patterns": [
      "iris_radius_mm",
      "{surface_id}_radius_mm",
      "{surface_id}_curvature",
      "{surface_id}_thickness_after_mm",
      "{surface_id}_focal_length_mm",
      "{surface_id}_semi_diameter_mm",
      "{group_id}_shift_x_mm",
      "{group_id}_shift_y_mm",
      "{group_id}_shift_z_mm"
    ],
    "warning_codes": [
      "aiming_failed",
      "edge_thickness_below_min",
      "min_air_gap",
      "missing_aperture_stop",
      "radius_key_deprecated",
      "solve_not_converged"
    ]
  },
  "material_catalog_version": "0.1.0",
  "preset_version": "0.1.0",
  "result_schema_version": "2.3.0"
}
```

## UI Phase 2 Handoff

### Added Error / Warning Codes

| Code | Severity | UI glossary status |
|---|---|---|
| `image_plane_policy_not_applicable` | error | Missing; `i18n:coverage` detects it |
| `artifact_expired` | error | Present |
| `solve_not_converged` | warning | Present |

### Artifact URI Response Fields

| Endpoint | Artifact field |
|---|---|
| `POST /v1/analysis/spot` | `artifacts.spot_points` |
| `POST /v1/analysis/ray-fan` | `artifacts.ray_fan_points` |
| `POST /v1/analysis/longitudinal-aberration` | `artifacts.longitudinal_points` |
| `POST /v1/analysis/psf` | `artifacts.psf_array` |
| `POST /v1/solve/best-focus` with sweep | `artifacts.focus_curve` |

All artifact-producing responses include `metadata.artifact_expires_at.{artifact_name}`.

