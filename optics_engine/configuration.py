from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .models import ValidationIssue, ValidationResult
from .system import CompiledSystem


@dataclass(frozen=True)
class RuntimeLayout:
    centers_mm: np.ndarray
    rotations: np.ndarray
    configuration: dict[str, Any]


def _group_shift_from_entry(entry: dict[str, Any]) -> tuple[str, np.ndarray]:
    group = str(entry.get("group") or entry.get("id"))
    return group, np.array(
        [
            float(entry.get("shift_x_mm", 0.0)),
            float(entry.get("shift_y_mm", 0.0)),
            float(entry.get("shift_z_mm", 0.0)),
        ],
        dtype=float,
    )


def group_shifts_from_configuration(compiled: CompiledSystem, configuration: dict[str, Any] | None) -> dict[str, np.ndarray]:
    configuration = configuration or {}
    shifts: dict[str, np.ndarray] = {}

    zoom_id = configuration.get("zoom_position")
    if zoom_id:
        for zoom in compiled.system.zoom_positions:
            if zoom.id == zoom_id:
                for group_id, position in zoom.group_positions.items():
                    shifts[group_id] = np.array([position.shift_x_mm, position.shift_y_mm, position.shift_z_mm], dtype=float)
                break

    for group_id, value in configuration.get("group_positions", {}).items():
        if isinstance(value, dict):
            shifts[group_id] = np.array(
                [
                    float(value.get("shift_x_mm", 0.0)),
                    float(value.get("shift_y_mm", 0.0)),
                    float(value.get("shift_z_mm", 0.0)),
                ],
                dtype=float,
            )

    for entry in configuration.get("decenters", []):
        group_id, shift = _group_shift_from_entry(entry)
        shifts[group_id] = shifts.get(group_id, np.zeros(3, dtype=float)) + shift

    return shifts


def _rotation_y(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c = np.cos(a)
    s = np.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]], dtype=float)


def _rotation_z(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c = np.cos(a)
    s = np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=float)


def _rotation_from_tilt(entry: dict[str, Any]) -> np.ndarray:
    # tilt_y tilts the optical axis toward +Z; tilt_z tilts toward +Y.
    return _rotation_z(float(entry.get("tilt_z_deg", 0.0))) @ _rotation_y(float(entry.get("tilt_y_deg", 0.0)))


def _tilt_surface_range(compiled: CompiledSystem, entry: dict[str, Any]) -> tuple[int | None, int | None]:
    if "group" in entry:
        return compiled.group_ranges.get(str(entry["group"]), (None, None))
    if "from_surface" in entry and "to_surface" in entry:
        try:
            start = compiled.surface_index(str(entry["from_surface"]))
            end = compiled.surface_index(str(entry["to_surface"]))
        except KeyError:
            return None, None
        return start, end
    return None, None


def runtime_layout(compiled: CompiledSystem, configuration: dict[str, Any] | None = None) -> RuntimeLayout:
    configuration = configuration or {}
    centers = np.zeros((len(compiled.surfaces), 3), dtype=float)
    centers[:, 0] = np.array(compiled.surface_positions_mm, dtype=float)
    rotations = np.tile(np.eye(3), (len(compiled.surfaces), 1, 1))
    for group_id, shift in group_shifts_from_configuration(compiled, configuration).items():
        if group_id not in compiled.group_ranges:
            continue
        for idx in compiled.group_indices(group_id):
            centers[idx] += shift
    for entry in configuration.get("tilts", []):
        start, end = _tilt_surface_range(compiled, entry)
        if start is None or end is None or start > end:
            continue
        rotation = _rotation_from_tilt(entry)
        reference = entry.get("rotation_center", {}) if isinstance(entry.get("rotation_center", {}), dict) else {}
        ref_idx = start
        if reference.get("reference") == "to_surface_vertex":
            ref_idx = end
        center_offset = np.array(
            [
                float(reference.get("offset_x_mm", 0.0)),
                float(reference.get("offset_y_mm", 0.0)),
                float(reference.get("offset_z_mm", 0.0)),
            ],
            dtype=float,
        )
        pivot = centers[ref_idx] + center_offset
        for idx in range(start, end + 1):
            centers[idx] = pivot + rotation @ (centers[idx] - pivot)
            rotations[idx] = rotation @ rotations[idx]
    return RuntimeLayout(centers_mm=centers, rotations=rotations, configuration=configuration)


def symmetric_fields(base_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    for field in base_fields:
        theta_y = float(field.get("theta_y_deg", 0.0))
        theta_z = float(field.get("theta_z_deg", 0.0))
        candidates = {
            (theta_y, theta_z),
            (-theta_y, theta_z),
            (theta_y, -theta_z),
            (-theta_y, -theta_z),
        }
        for y, z in sorted(candidates):
            key = (round(y, 12), round(z, 12))
            if key in seen:
                continue
            seen.add(key)
            fields.append({"id": f"field_y{y:g}_z{z:g}", "type": "angular", "theta_y_deg": y, "theta_z_deg": z})
    return fields


def validate_configuration(
    compiled: CompiledSystem,
    configuration: dict[str, Any] | None = None,
    *,
    min_air_gap_mm: float = 0.0,
) -> ValidationResult:
    configuration = configuration or {}
    issues: list[ValidationIssue] = []

    group_shifts = group_shifts_from_configuration(compiled, configuration)
    for group_id in group_shifts:
        if group_id not in compiled.group_ranges:
            issues.append(
                ValidationIssue(
                    type="unknown_group",
                    params={"group_id": group_id},
                    message=f"configuration references unknown group {group_id!r}",
                    severity="error",
                )
            )

    zoom_id = configuration.get("zoom_position")
    if zoom_id and all(zoom.id != zoom_id for zoom in compiled.system.zoom_positions):
        issues.append(
            ValidationIssue(
                type="unknown_zoom_position",
                params={"zoom_position_id": zoom_id},
                message=f"configuration references unknown zoom_position {zoom_id!r}",
                severity="error",
            )
        )

    for entry in configuration.get("tilts", []):
        start, end = _tilt_surface_range(compiled, entry)
        if start is None or end is None:
            issues.append(
                ValidationIssue(
                    type="unknown_tilt_target",
                    params={"entry": entry},
                    message="tilt entry must reference a known group or from_surface/to_surface range",
                    severity="error",
                )
            )
        elif start > end:
            issues.append(
                ValidationIssue(
                    type="invalid_tilt_range",
                    params={"entry": entry},
                    message="tilt from_surface must precede to_surface",
                    severity="error",
                )
            )

    layout = runtime_layout(compiled, configuration)
    x_positions = layout.centers_mm[:, 0]
    for idx in range(len(compiled.surfaces) - 1):
        if compiled.surfaces[idx].thickness_after_mm < 0.0:
            continue
        gap = x_positions[idx + 1] - x_positions[idx]
        if gap < min_air_gap_mm:
            surface_ids = [compiled.surfaces[idx].id, compiled.surfaces[idx + 1].id]
            issues.append(
                ValidationIssue(
                    type="negative_air_gap" if gap < 0.0 else "min_air_gap",
                    params={"surface_ids": surface_ids, "gap_mm": float(gap), "min_air_gap_mm": float(min_air_gap_mm)},
                    message=(
                        f"gap between {compiled.surfaces[idx].id!r} and "
                        f"{compiled.surfaces[idx + 1].id!r} is {gap:.6g} mm"
                    ),
                    surface_id=compiled.surfaces[idx].id,
                    severity="error" if gap < 0.0 else "warning",
                )
            )

    status = "ok"
    if any(issue.severity == "error" for issue in issues):
        status = "error"
    elif issues:
        status = "warning"
    return ValidationResult(status=status, issues=issues)
