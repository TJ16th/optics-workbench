from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .core import asphere_sag_and_slope
from .models import ValidationIssue, ValidationResult
from .system import CompiledSystem


@dataclass(frozen=True)
class RuntimeLayout:
    centers_mm: np.ndarray
    rotations: np.ndarray
    configuration: dict[str, Any]


@dataclass(frozen=True)
class SurfaceGapValue:
    surface_ids: tuple[str, str]
    medium_id: str
    radial_height_mm: float | None
    vertex_gap_mm: float
    edge_gap_mm: float | None


def _clear_radius(surface) -> float | None:
    radius = surface.semi_diameter_mm
    if surface.aperture is not None:
        radius = surface.aperture.outer_semi_diameter_mm or surface.aperture.semi_diameter_mm or radius
    return None if radius is None else float(radius)


def _surface_sag(surface, radial_height_mm: float) -> float:
    if surface.surface_type == "plane" or surface.kind in {"aperture_stop", "mechanical_aperture", "thin_lens", "sensor", "eye_reference", "dummy"}:
        return 0.0
    if surface.surface_type == "aspherical_even":
        sag, _ = asphere_sag_and_slope(
            np.asarray([radial_height_mm], dtype=float),
            float(surface.radius_mm),
            float(surface.conic),
            surface.asphere_coefficients,
        )
        return float(sag[0])
    radius = float(surface.radius_mm)
    if radius == 0.0:
        return 0.0
    under_root = radius * radius - radial_height_mm * radial_height_mm
    if under_root < 0.0:
        return float("nan")
    return radius - float(np.copysign(np.sqrt(under_root), radius))


def surface_gap_values(compiled: CompiledSystem, configuration: dict[str, Any] | None = None) -> list[SurfaceGapValue]:
    layout = runtime_layout(compiled, configuration)
    rows: list[SurfaceGapValue] = []
    for index in range(len(compiled.surfaces) - 1):
        first = compiled.surfaces[index]
        second = compiled.surfaces[index + 1]
        if first.thickness_after_mm < 0.0:
            continue
        vertex_gap = float(layout.centers_mm[index + 1, 0] - layout.centers_mm[index, 0])
        radii = [_clear_radius(first), _clear_radius(second)]
        radial_height = None if any(radius is None for radius in radii) else min(float(radii[0]), float(radii[1]))
        edge_gap = None
        if radial_height is not None:
            edge_gap = vertex_gap + _surface_sag(second, radial_height) - _surface_sag(first, radial_height)
            if not np.isfinite(edge_gap):
                edge_gap = None
        rows.append(
            SurfaceGapValue(
                surface_ids=(first.id, second.id),
                medium_id=first.material_after or "AIR",
                radial_height_mm=radial_height,
                vertex_gap_mm=vertex_gap,
                edge_gap_mm=edge_gap,
            )
        )
    return rows


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
    min_edge_thickness_mm: float = 0.0,
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

    for row in surface_gap_values(compiled, configuration):
        if row.vertex_gap_mm < 0.0:
            issues.append(
                ValidationIssue(
                    code="negative_air_gap",
                    params={"surface_ids": list(row.surface_ids), "gap_mm": row.vertex_gap_mm, "min_air_gap_mm": 0.0},
                    message_en="surface vertex order is reversed",
                    surface_id=row.surface_ids[0],
                    severity="error",
                )
            )
            continue
        if row.edge_gap_mm is not None and row.edge_gap_mm < 0.0:
            issues.append(
                ValidationIssue(
                    code="surface_interference",
                    params={"surface_ids": list(row.surface_ids), "edge_gap_mm": row.edge_gap_mm, "radial_height_mm": row.radial_height_mm},
                    message_en="adjacent clear apertures intersect after surface sag is applied",
                    surface_id=row.surface_ids[0],
                    severity="warning",
                )
            )
        threshold = min_air_gap_mm if row.medium_id == "AIR" else min_edge_thickness_mm
        code = "min_air_gap" if row.medium_id == "AIR" else "edge_thickness_below_min"
        value = row.edge_gap_mm if row.edge_gap_mm is not None else row.vertex_gap_mm
        if value < threshold:
            issues.append(
                ValidationIssue(
                    code=code,
                    params={
                        "surface_ids": list(row.surface_ids),
                        "value_mm": value,
                        "minimum_mm": float(threshold),
                        "radial_height_mm": row.radial_height_mm,
                    },
                    message_en="surface gap is below the requested minimum",
                    surface_id=row.surface_ids[0],
                    severity="warning",
                )
            )

    status = "ok"
    if any(issue.severity == "error" for issue in issues):
        status = "error"
    elif issues:
        status = "warning"
    return ValidationResult(status=status, issues=issues)
