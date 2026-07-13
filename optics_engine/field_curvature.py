from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .analysis import analyze_spot
from .configuration import runtime_layout
from .system import CompiledSystem
from .tracing import trace_forward


@dataclass(frozen=True)
class FieldCurvatureRow:
    field_id: str
    theta_y_deg: float
    theta_z_deg: float
    best_focus_shift_mm: float | None
    rms_radius_mm: float | None
    method: str


@dataclass(frozen=True)
class FieldCurvatureResult:
    rows: list[FieldCurvatureRow]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class MSImageSurfaceRow:
    field_id: str
    tangential_focus_shift_mm: float | None
    sagittal_focus_shift_mm: float | None
    method: str


@dataclass(frozen=True)
class MSImageSurfaceResult:
    rows: list[MSImageSurfaceRow]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class _RmsFocus:
    shift_mm: float | None
    rms_mm: float | None
    boundary: str | None


@dataclass(frozen=True)
class _CoddingtonFocus:
    tangential_shift_mm: float
    sagittal_shift_mm: float


def _sensor_shifted_configuration(configuration: dict | None, shift_x_mm: float) -> dict:
    config = dict(configuration or {})
    positions = dict(config.get("group_positions", {}))
    existing = dict(positions.get("__SENSOR_SCAN__", {}))
    existing["shift_x_mm"] = shift_x_mm
    positions["__SENSOR_SCAN__"] = existing
    config["group_positions"] = positions
    return config


def _with_sensor_group(compiled: CompiledSystem):
    if "__SENSOR_SCAN__" in compiled.group_ranges or compiled.sensor_index is None:
        return compiled
    from dataclasses import replace

    ranges = dict(compiled.group_ranges)
    ranges["__SENSOR_SCAN__"] = (compiled.sensor_index, compiled.sensor_index)
    return replace(compiled, group_ranges=ranges)


def _best_focus_for_field(
    compiled: CompiledSystem,
    field: dict,
    configuration: dict | None,
    *,
    axis: str | None = None,
    search_mm: float = 5.0,
    steps: int = 11,
) -> _RmsFocus:
    compiled = _with_sensor_group(compiled)
    shifts = np.linspace(-search_mm, search_mm, steps)
    best_index = None
    best_rms = None
    for index, shift in enumerate(shifts):
        config = _sensor_shifted_configuration(configuration, float(shift))
        trace = trace_forward(
            compiled,
            [field],
            {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
            [compiled.system.wavelengths_nm.primary],
            {"configuration": config},
        )
        mask = trace.arrived_mask
        if not np.any(mask):
            continue
        y = trace.sensor_y_mm[mask]
        z = trace.sensor_z_mm[mask]
        if axis in {"tangential", "sagittal"}:
            field_y = np.tan(np.deg2rad(float(field.get("theta_y_deg", 0.0))))
            field_z = np.tan(np.deg2rad(float(field.get("theta_z_deg", 0.0))))
            norm = float(np.hypot(field_y, field_z))
            meridional = np.array([1.0, 0.0]) if norm <= 1.0e-12 else np.array([field_y, field_z]) / norm
            projection_axis = meridional if axis == "tangential" else np.array([-meridional[1], meridional[0]])
            projected = y * projection_axis[0] + z * projection_axis[1]
            value = float(np.sqrt(np.mean((projected - np.mean(projected)) ** 2)))
        else:
            spot = analyze_spot(trace)
            value = float(spot.rms_radius_mm) if spot.rms_radius_mm is not None else np.inf
        if best_rms is None or value < best_rms:
            best_index = index
            best_rms = value
    if best_index is None:
        return _RmsFocus(shift_mm=None, rms_mm=None, boundary=None)
    boundary = "lower" if best_index == 0 else "upper" if best_index == len(shifts) - 1 else None
    return _RmsFocus(shift_mm=float(shifts[best_index]), rms_mm=best_rms, boundary=boundary)


def _is_coaxial(compiled: CompiledSystem, configuration: dict | None) -> bool:
    layout = runtime_layout(compiled, configuration)
    return bool(
        np.allclose(layout.centers_mm[:, 1:], 0.0, atol=1.0e-12)
        and np.allclose(layout.rotations, np.eye(3)[None, :, :], atol=1.0e-12)
    )


def _supports_coddington(compiled: CompiledSystem) -> bool:
    powered = [surface for surface in compiled.surfaces if surface.kind in {"refractive", "mirror", "thin_lens"}]
    return bool(powered) and all(
        surface.kind == "thin_lens"
        or (surface.kind == "refractive" and surface.surface_type in {"spherical", "plane"})
        for surface in powered
    )


def _chief_ray_path(compiled: CompiledSystem, field: dict, configuration: dict | None) -> list[dict[str, Any]] | None:
    trace = trace_forward(
        compiled,
        [field],
        {
            "samples_per_field": 1,
            "pupil_distribution": "grid",
            "ray_aiming": {"mode": "full", "strategy": "exact", "tolerance_mm": 1.0e-8},
        },
        [compiled.system.wavelengths_nm.primary],
        {"configuration": configuration or {}, "store_path": True, "include_analysis_metadata": False},
    )
    if trace.status.size != 1 or str(trace.status[0]) != "alive" or not trace.paths[0]:
        return None
    return trace.paths[0]


def _coddington_focus(
    compiled: CompiledSystem,
    field: dict,
    configuration: dict | None,
) -> _CoddingtonFocus | None:
    path = _chief_ray_path(compiled, field, configuration)
    if path is None or compiled.sensor_index is None:
        return None

    path_positions = {entry["surface_id"]: index for index, entry in enumerate(path)}
    layout = runtime_layout(compiled, configuration)
    wavelength = compiled.system.wavelengths_nm.primary
    current_n = compiled.material_index("AIR", wavelength)
    tangential_distance = np.inf
    sagittal_distance = np.inf
    previous_point: np.ndarray | None = None
    last_point: np.ndarray | None = None
    last_outgoing: np.ndarray | None = None

    for surface_index, surface in enumerate(compiled.surfaces):
        if surface.kind not in {"refractive", "thin_lens"}:
            continue
        path_index = path_positions.get(surface.id)
        if path_index is None or path_index + 1 >= len(path):
            return None
        entry = path[path_index]
        point = np.asarray(entry["point_mm"], dtype=float)
        incoming = np.asarray(entry["direction"], dtype=float)
        outgoing = np.asarray(path[path_index + 1]["direction"], dtype=float)

        if previous_point is not None:
            separation = float(np.linalg.norm(point - previous_point))
            if np.isfinite(tangential_distance):
                tangential_distance -= separation
            if np.isfinite(sagittal_distance):
                sagittal_distance -= separation

        if surface.kind == "thin_lens":
            # The ideal thin lens has the same paraxial power in both principal
            # sections, so its Coddington update reduces to the thin-lens law.
            surface_power = current_n / float(surface.focal_length_mm)
            tangential_vergence = surface_power
            sagittal_vergence = surface_power
            if np.isfinite(tangential_distance) and abs(tangential_distance) > 1.0e-12:
                tangential_vergence += current_n / tangential_distance
            if np.isfinite(sagittal_distance) and abs(sagittal_distance) > 1.0e-12:
                sagittal_vergence += current_n / sagittal_distance
            if abs(tangential_vergence) <= 1.0e-14 or abs(sagittal_vergence) <= 1.0e-14:
                return None
            tangential_distance = current_n / tangential_vergence
            sagittal_distance = current_n / sagittal_vergence
        else:
            radius = float(surface.radius_mm)
            if abs(radius) <= 1.0e-12:
                normal = layout.rotations[surface_index][:, 0]
                curvature = 0.0
            else:
                sphere_center = layout.centers_mm[surface_index] + layout.rotations[surface_index] @ np.array([radius, 0.0, 0.0])
                normal = point - sphere_center
                normal /= np.linalg.norm(normal)
                curvature = 1.0 / radius
            cos_in = abs(float(np.dot(incoming, normal)))
            cos_out = abs(float(np.dot(outgoing, normal)))
            n_after = compiled.material_index(surface.material_after, wavelength)
            surface_power = (n_after * cos_out - current_n * cos_in) * curvature

            # Coddington's tangential and sagittal recurrences use conjugate
            # distances measured along the aimed chief ray.
            tangential_vergence = surface_power
            if np.isfinite(tangential_distance) and abs(tangential_distance) > 1.0e-12:
                tangential_vergence += current_n * cos_in * cos_in / tangential_distance
            sagittal_vergence = surface_power
            if np.isfinite(sagittal_distance) and abs(sagittal_distance) > 1.0e-12:
                sagittal_vergence += current_n / sagittal_distance
            if abs(tangential_vergence) <= 1.0e-14 or abs(sagittal_vergence) <= 1.0e-14:
                return None

            tangential_distance = n_after * cos_out * cos_out / tangential_vergence
            sagittal_distance = n_after / sagittal_vergence
            current_n = n_after
        previous_point = point
        last_point = point
        last_outgoing = outgoing

    if last_point is None or last_outgoing is None:
        return None
    sensor_x = float(layout.centers_mm[compiled.sensor_index, 0])
    tangential_x = float(last_point[0] + tangential_distance * last_outgoing[0])
    sagittal_x = float(last_point[0] + sagittal_distance * last_outgoing[0])
    return _CoddingtonFocus(tangential_x - sensor_x, sagittal_x - sensor_x)


def _boundary_warning(field_id: str, axis: str, focus: _RmsFocus, search_mm: float) -> dict[str, Any] | None:
    if focus.boundary is None or focus.shift_mm is None:
        return None
    params = {
        "field_id": field_id,
        "axis": axis,
        "boundary": focus.boundary,
        "best_focus_shift_mm": focus.shift_mm,
        "search_min_mm": -float(search_mm),
        "search_max_mm": float(search_mm),
    }
    return {
        "severity": "warning",
        "code": "solve_not_converged",
        "params": params,
        "message_en": (
            f"RMS focus search for field {field_id!r}, axis {axis!r} selected the "
            f"{focus.boundary} boundary at {focus.shift_mm:.6g} mm within "
            f"[-{search_mm:.6g}, {search_mm:.6g}] mm."
        ),
    }


def _coddington_failure_warning(field_id: str) -> dict[str, Any]:
    params = {"field_id": field_id, "method": "coddington", "fallback_method": "rms_search"}
    return {
        "severity": "warning",
        "code": "aiming_failed",
        "params": params,
        "message_en": f"Coddington chief-ray aiming failed for field {field_id!r}; rms_search was used.",
    }


def _method_for_system(compiled: CompiledSystem, configuration: dict | None, requested_method: str | None) -> str:
    if requested_method not in {None, "auto", "coddington", "rms_search"}:
        raise ValueError(f"unknown image-surface method {requested_method!r}")
    coddington_available = _is_coaxial(compiled, configuration) and _supports_coddington(compiled)
    if requested_method == "coddington" and not coddington_available:
        raise ValueError("coddington requires a coaxial spherical refractive or ideal thin-lens system")
    if requested_method == "rms_search":
        return "rms_search"
    return "coddington" if coddington_available else "rms_search"


def analyze_field_curvature(
    compiled: CompiledSystem,
    fields: list[dict],
    configuration: dict | None = None,
    *,
    search_mm: float = 5.0,
    method: str | None = None,
) -> FieldCurvatureResult:
    method = _method_for_system(compiled, configuration, method)
    rows: list[FieldCurvatureRow] = []
    warnings: list[dict[str, Any]] = []
    for field in fields:
        field_id = str(field.get("id", "field"))
        if method == "coddington":
            focus = _coddington_focus(compiled, field, configuration)
            if focus is not None:
                rows.append(
                    FieldCurvatureRow(
                        field_id=field_id,
                        theta_y_deg=float(field.get("theta_y_deg", 0.0)),
                        theta_z_deg=float(field.get("theta_z_deg", 0.0)),
                        best_focus_shift_mm=0.5 * (focus.tangential_shift_mm + focus.sagittal_shift_mm),
                        rms_radius_mm=None,
                        method=method,
                    )
                )
                continue
            warnings.append(_coddington_failure_warning(field_id))
        rms = _best_focus_for_field(compiled, field, configuration, search_mm=search_mm)
        warning = _boundary_warning(field_id, "radial", rms, search_mm)
        if warning is not None:
            warnings.append(warning)
        rows.append(
            FieldCurvatureRow(
                field_id=field_id,
                theta_y_deg=float(field.get("theta_y_deg", 0.0)),
                theta_z_deg=float(field.get("theta_z_deg", 0.0)),
                best_focus_shift_mm=rms.shift_mm,
                rms_radius_mm=rms.rms_mm,
                method="rms_search",
            )
        )
    row_methods = {row.method for row in rows}
    actual_method = method if not row_methods else next(iter(row_methods)) if len(row_methods) == 1 else "mixed"
    metadata: dict[str, Any] = {
        "method": actual_method,
        "wavelength_nm": float(compiled.system.wavelengths_nm.primary),
        "ray_sampling_independent": actual_method == "coddington",
    }
    if actual_method == "coddington":
        metadata.update(
            {
                "chief_rays_per_field": 1,
                "ray_aiming_mode": "full",
                "ray_aiming_strategy": "exact",
                "equations": "coddington_tangential_sagittal_recurrence",
            }
        )
    elif actual_method == "rms_search":
        metadata.update(
            {
                "samples_per_field": 21,
                "pupil_distribution": "grid",
                "ray_aiming_mode": "paraxial",
                "search_range_mm": float(search_mm),
                "search_steps": 11,
            }
        )
    if warnings:
        metadata["warnings"] = warnings
    return FieldCurvatureResult(rows=rows, metadata=metadata)


def analyze_ms_image_surface(
    compiled: CompiledSystem,
    fields: list[dict],
    configuration: dict | None = None,
    *,
    search_mm: float = 5.0,
    method: str | None = None,
) -> MSImageSurfaceResult:
    method = _method_for_system(compiled, configuration, method)
    rows: list[MSImageSurfaceRow] = []
    warnings: list[dict[str, Any]] = []
    for field in fields:
        field_id = str(field.get("id", "field"))
        if method == "coddington":
            focus = _coddington_focus(compiled, field, configuration)
            if focus is not None:
                rows.append(
                    MSImageSurfaceRow(
                        field_id=field_id,
                        tangential_focus_shift_mm=focus.tangential_shift_mm,
                        sagittal_focus_shift_mm=focus.sagittal_shift_mm,
                        method=method,
                    )
                )
                continue
            warnings.append(_coddington_failure_warning(field_id))

        tangential = _best_focus_for_field(compiled, field, configuration, axis="tangential", search_mm=search_mm)
        sagittal = _best_focus_for_field(compiled, field, configuration, axis="sagittal", search_mm=search_mm)
        for axis, result in (("tangential", tangential), ("sagittal", sagittal)):
            warning = _boundary_warning(field_id, axis, result, search_mm)
            if warning is not None:
                warnings.append(warning)
        rows.append(
            MSImageSurfaceRow(
                field_id=field_id,
                tangential_focus_shift_mm=tangential.shift_mm,
                sagittal_focus_shift_mm=sagittal.shift_mm,
                method="rms_search",
            )
        )
    row_methods = {row.method for row in rows}
    actual_method = method if not row_methods else next(iter(row_methods)) if len(row_methods) == 1 else "mixed"
    metadata: dict[str, Any] = {
        "method": actual_method,
        "wavelength_nm": float(compiled.system.wavelengths_nm.primary),
        "ray_sampling_independent": actual_method == "coddington",
    }
    if actual_method == "coddington":
        metadata.update(
            {
                "chief_rays_per_field": 1,
                "ray_aiming_mode": "full",
                "ray_aiming_strategy": "exact",
                "equations": "coddington_tangential_sagittal_recurrence",
            }
        )
    elif actual_method == "rms_search":
        metadata.update(
            {
                "samples_per_field": 21,
                "pupil_distribution": "grid",
                "ray_aiming_mode": "paraxial",
                "search_range_mm": float(search_mm),
                "search_steps": 11,
            }
        )
    if warnings:
        metadata["warnings"] = warnings
    return MSImageSurfaceResult(rows=rows, metadata=metadata)
