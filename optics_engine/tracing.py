from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

import numpy as np

from .core import (
    aperture_pass,
    field_direction,
    intersect_sphere,
    intersect_surface,
    normalize,
    reflect,
    refract,
    surface_normals_for_surface,
    thin_lens_transform,
)
from .configuration import runtime_layout, validate_configuration
from .system import CompiledSystem

STATUS_ALIVE = "alive"
STATUS_BLOCKED = "blocked"
STATUS_MISSED = "missed"
STATUS_TIR = "total_internal_reflection"
STATUS_AIMING_FAILED = "aiming_failed"


@dataclass
class TraceResult:
    origins: np.ndarray
    directions: np.ndarray
    wavelengths_nm: np.ndarray
    field_ids: list[str]
    status: np.ndarray
    sensor_y_mm: np.ndarray
    sensor_z_mm: np.ndarray
    paths: list[list[dict[str, Any]]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    eye_theta_y_deg: np.ndarray | None = None
    eye_theta_z_deg: np.ndarray | None = None

    @property
    def arrived_mask(self) -> np.ndarray:
        return (self.status == STATUS_ALIVE) & np.isfinite(self.sensor_y_mm) & np.isfinite(self.sensor_z_mm)

    @property
    def eye_arrived_mask(self) -> np.ndarray:
        if self.eye_theta_y_deg is None or self.eye_theta_z_deg is None:
            return np.zeros(self.status.shape, dtype=bool)
        return (self.status == STATUS_ALIVE) & np.isfinite(self.eye_theta_y_deg) & np.isfinite(self.eye_theta_z_deg)


@dataclass
class ReverseTraceResult:
    origins: np.ndarray
    directions: np.ndarray
    wavelengths_nm: np.ndarray
    status: np.ndarray
    object_theta_y_deg: np.ndarray
    object_theta_z_deg: np.ndarray
    paths: list[list[dict[str, Any]]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _unit_disk_samples(count: int, distribution: str = "hexapolar") -> np.ndarray:
    if count <= 1:
        return np.array([[0.0, 0.0]], dtype=float)
    if distribution == "fan_y":
        return np.column_stack([np.linspace(-1.0, 1.0, count), np.zeros(count)])
    if distribution == "fan_z":
        return np.column_stack([np.zeros(count), np.linspace(-1.0, 1.0, count)])
    if distribution == "random":
        rng = np.random.default_rng(0)
        radius = np.sqrt(rng.random(count))
        angle = 2.0 * np.pi * rng.random(count)
        return np.column_stack([radius * np.cos(angle), radius * np.sin(angle)])

    grid_size = int(np.ceil(np.sqrt(count * 4.0 / np.pi))) + 1
    values = np.linspace(-1.0, 1.0, grid_size)
    pts = np.array([(y, z) for y in values for z in values if y * y + z * z <= 1.0 + 1.0e-12], dtype=float)
    order = np.argsort(np.sum(pts * pts, axis=1))
    pts = pts[order]
    if pts.shape[0] < count:
        angles = np.linspace(0.0, 2.0 * np.pi, count - pts.shape[0], endpoint=False)
        extra = np.column_stack([np.cos(angles), np.sin(angles)])
        pts = np.vstack([pts, extra])
    return pts[:count]


def _configuration_variables(configuration: dict[str, Any] | None) -> dict[str, Any]:
    variables = (configuration or {}).get("variables", {})
    return variables if isinstance(variables, dict) else {}


def _runtime_iris_radius(configuration: dict[str, Any] | None) -> float | None:
    variables = _configuration_variables(configuration)
    if "iris_radius_mm" not in variables:
        return None
    value = float(variables["iris_radius_mm"])
    return value if np.isfinite(value) and value > 0.0 else None


def _aperture_radius(compiled: CompiledSystem, configuration: dict[str, Any] | None = None) -> tuple[int | None, float, float]:
    idx = compiled.aperture_stop_index
    if idx is None:
        return None, 1.0, 0.0
    surface = compiled.surfaces[idx]
    outer = surface.semi_diameter_mm or 1.0
    inner = 0.0
    if surface.aperture is not None:
        if surface.aperture.shape == "annulus":
            outer = surface.aperture.outer_semi_diameter_mm or surface.aperture.semi_diameter_mm or outer
            inner = surface.aperture.inner_semi_diameter_mm or 0.0
        elif surface.aperture.shape == "circle":
            outer = surface.aperture.semi_diameter_mm or surface.aperture.outer_semi_diameter_mm or outer
    runtime_outer = _runtime_iris_radius(configuration)
    if runtime_outer is not None:
        outer = runtime_outer
    return idx, float(outer), float(inner)


def _target_points_for_stop(compiled: CompiledSystem, samples: np.ndarray) -> np.ndarray:
    layout = runtime_layout(compiled)
    return _target_points_for_stop_with_layout(compiled, samples, layout.centers_mm)


def _target_points_for_stop_with_layout(
    compiled: CompiledSystem,
    samples: np.ndarray,
    centers_mm: np.ndarray,
    rotations: np.ndarray | None = None,
    configuration: dict[str, Any] | None = None,
) -> np.ndarray:
    stop_idx, outer, inner = _aperture_radius(compiled, configuration)
    stop_center = centers_mm[stop_idx] if stop_idx is not None else centers_mm[0]
    stop_rotation = np.eye(3) if rotations is None or stop_idx is None else rotations[stop_idx]
    yz = samples.copy()
    if inner > 0.0:
        radii = np.linalg.norm(yz, axis=1)
        angles = np.arctan2(yz[:, 1], yz[:, 0])
        mapped = np.sqrt(inner * inner + radii * radii * (outer * outer - inner * inner))
        yz[:, 0] = mapped * np.cos(angles)
        yz[:, 1] = mapped * np.sin(angles)
    else:
        yz *= outer
    local_targets = np.column_stack([np.zeros(yz.shape[0]), yz[:, 0], yz[:, 1]])
    return stop_center + local_targets @ stop_rotation.T


def _aperture_pass_with_runtime(points: np.ndarray, surface, surface_idx: int, compiled: CompiledSystem, configuration: dict[str, Any] | None) -> np.ndarray:
    if compiled.aperture_stop_index == surface_idx:
        runtime_outer = _runtime_iris_radius(configuration)
        if runtime_outer is not None:
            r = np.sqrt(points[:, 1] * points[:, 1] + points[:, 2] * points[:, 2])
            inner = 0.0
            if surface.aperture is not None and surface.aperture.shape == "annulus":
                inner = surface.aperture.inner_semi_diameter_mm or 0.0
            return (r <= runtime_outer + 1.0e-9) & (r >= inner - 1.0e-9)
    return aperture_pass(points, surface)


def _trace_raw(
    compiled: CompiledSystem,
    origins: np.ndarray,
    directions: np.ndarray,
    wavelengths_nm: np.ndarray,
    *,
    field_ids: list[str] | None = None,
    stop_at_surface_index: int | None = None,
    store_path: bool = True,
    centers_mm: np.ndarray | None = None,
    rotations: np.ndarray | None = None,
    configuration: dict[str, Any] | None = None,
) -> TraceResult:
    n_rays = origins.shape[0]
    current_origins = origins.copy()
    current_dirs = normalize(directions.copy())
    status = np.full(n_rays, STATUS_ALIVE, dtype=object)
    sensor_y = np.full(n_rays, np.nan)
    sensor_z = np.full(n_rays, np.nan)
    eye_theta_y = np.full(n_rays, np.nan)
    eye_theta_z = np.full(n_rays, np.nan)
    propagation_sign = np.ones(n_rays, dtype=int)
    current_n = np.array([compiled.material_index("AIR", wl) for wl in wavelengths_nm], dtype=float)
    paths: list[list[dict[str, Any]]] = [[] for _ in range(n_rays)]
    field_ids = field_ids or ["field"] * n_rays
    if centers_mm is None:
        layout = runtime_layout(compiled)
        centers_mm = layout.centers_mm
        rotations = layout.rotations
    if rotations is None:
        rotations = np.tile(np.eye(3), (len(compiled.surfaces), 1, 1))

    for surface_idx, surface in enumerate(compiled.surfaces):
        alive = status == STATUS_ALIVE
        if not np.any(alive):
            break

        alive_indices = np.where(alive)[0]
        center = centers_mm[surface_idx]
        rotation = rotations[surface_idx]
        x_vertex = 0.0
        local_origins = (current_origins[alive] - center) @ rotation
        local_dirs_alive = current_dirs[alive] @ rotation
        if surface.kind in {"refractive", "mirror"}:
            points_alive, valid_alive = intersect_surface(local_origins, local_dirs_alive, x_vertex, surface)
        else:
            points_alive, valid_alive = intersect_sphere(local_origins, local_dirs_alive, x_vertex, 0.0)
        local_points_alive = points_alive.copy()
        points_alive = points_alive @ rotation.T + center
        local_points = np.full_like(current_origins, np.nan)
        local_points[alive] = local_points_alive
        points = np.full_like(current_origins, np.nan)
        points[alive] = points_alive

        invalid_indices = alive_indices[~valid_alive]
        status[invalid_indices] = STATUS_MISSED
        valid_indices = alive_indices[valid_alive]
        if valid_indices.size == 0:
            continue

        if store_path:
            for ray_idx in valid_indices:
                paths[ray_idx].append(
                    {
                        "surface_id": surface.id,
                        "point_mm": points[ray_idx].tolist(),
                        "local_point_mm": local_points[ray_idx].tolist(),
                        "direction": current_dirs[ray_idx].tolist(),
                        "status": str(status[ray_idx]),
                    }
                )

        passes = _aperture_pass_with_runtime(local_points[valid_indices], surface, surface_idx, compiled, configuration)
        blocked = valid_indices[~passes]
        status[blocked] = STATUS_BLOCKED
        valid_indices = valid_indices[passes]
        if valid_indices.size == 0:
            continue

        current_origins[valid_indices] = points[valid_indices]

        if stop_at_surface_index is not None and surface_idx == stop_at_surface_index:
            break

        if surface.kind == "refractive":
            normals = surface_normals_for_surface(local_points[valid_indices], x_vertex, surface)
            n_after = np.array([compiled.material_index(surface.material_after, wl) for wl in wavelengths_nm[valid_indices]])
            local_in_dirs = current_dirs[valid_indices] @ rotation
            out_dirs_local, refract_ok = refract(local_in_dirs, normals, current_n[valid_indices], n_after)
            tir_indices = valid_indices[~refract_ok]
            status[tir_indices] = STATUS_TIR
            ok_indices = valid_indices[refract_ok]
            current_dirs[ok_indices] = out_dirs_local[refract_ok] @ rotation.T
            current_n[ok_indices] = n_after[refract_ok]
        elif surface.kind == "mirror":
            normals = surface_normals_for_surface(local_points[valid_indices], x_vertex, surface)
            local_in_dirs = current_dirs[valid_indices] @ rotation
            current_dirs[valid_indices] = reflect(local_in_dirs, normals) @ rotation.T
            propagation_sign[valid_indices] *= -1
        elif surface.kind == "thin_lens":
            local_out = thin_lens_transform(
                local_points[valid_indices],
                current_dirs[valid_indices] @ rotation,
                x_vertex,
                float(surface.focal_length_mm),
            )
            current_dirs[valid_indices] = local_out @ rotation.T
        elif surface.kind == "sensor":
            sensor_y[valid_indices] = local_points[valid_indices, 1]
            sensor_z[valid_indices] = local_points[valid_indices, 2]
        elif surface.kind == "eye_reference":
            local_dirs = current_dirs[valid_indices] @ rotation
            eye_theta_y[valid_indices] = np.rad2deg(np.arctan2(local_dirs[:, 1], local_dirs[:, 0]))
            eye_theta_z[valid_indices] = np.rad2deg(np.arctan2(local_dirs[:, 2], local_dirs[:, 0]))

    return TraceResult(
        origins=origins,
        directions=current_dirs,
        wavelengths_nm=wavelengths_nm,
        field_ids=field_ids,
        status=status,
        sensor_y_mm=sensor_y,
        sensor_z_mm=sensor_z,
        paths=paths,
        metadata={"system_hash": compiled.system_hash},
        eye_theta_y_deg=eye_theta_y,
        eye_theta_z_deg=eye_theta_z,
    )


def _aim_origin_to_stop(
    compiled: CompiledSystem,
    launch_x: float,
    direction: np.ndarray,
    wavelength_nm: float,
    target: np.ndarray,
    centers_mm: np.ndarray,
    rotations: np.ndarray,
    *,
    tolerance_mm: float,
    max_iterations: int,
    configuration: dict[str, Any] | None = None,
) -> tuple[np.ndarray, bool, int]:
    stop_idx = compiled.aperture_stop_index
    if stop_idx is None:
        origin = target - direction * ((target[0] - launch_x) / direction[0])
        origin[0] = launch_x
        return origin, True, 0

    stop_x = centers_mm[stop_idx, 0]
    p = target[1:3] - direction[1:3] * ((stop_x - launch_x) / direction[0])

    def residual(param: np.ndarray) -> np.ndarray | None:
        origin = np.array([[launch_x, param[0], param[1]]], dtype=float)
        result = _trace_raw(
            compiled,
            origin,
            direction.reshape(1, 3),
            np.array([wavelength_nm], dtype=float),
            stop_at_surface_index=stop_idx,
            store_path=True,
            centers_mm=centers_mm,
            rotations=rotations,
            configuration=configuration,
        )
        if result.status[0] != STATUS_ALIVE or not result.paths:
            return None
        if result.paths[0]:
            point = np.array(result.paths[0][-1]["point_mm"], dtype=float)
        else:
            return None
        return point[1:3] - target[1:3]

    iterations = 0
    for iterations in range(1, max_iterations + 1):
        res = residual(p)
        if res is None:
            return np.array([launch_x, p[0], p[1]], dtype=float), False, iterations
        if np.linalg.norm(res) <= tolerance_mm:
            return np.array([launch_x, p[0], p[1]], dtype=float), True, iterations

        jac = np.zeros((2, 2), dtype=float)
        eps = 1.0e-4
        for axis in range(2):
            shifted = p.copy()
            shifted[axis] += eps
            res_shifted = residual(shifted)
            if res_shifted is None:
                return np.array([launch_x, p[0], p[1]], dtype=float), False, iterations
            jac[:, axis] = (res_shifted - res) / eps
        try:
            delta = np.linalg.solve(jac, res)
        except np.linalg.LinAlgError:
            return np.array([launch_x, p[0], p[1]], dtype=float), False, iterations
        p -= delta

    return np.array([launch_x, p[0], p[1]], dtype=float), False, iterations


def trace_forward(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None = None,
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> TraceResult:
    t0 = time.perf_counter()
    sampling = sampling or {}
    options = options or {}
    profiling = bool(options.get("profiling", False))
    configuration = options.get("configuration") or options.get("config") or {}
    include_analysis_metadata = bool(options.get("include_analysis_metadata", True))
    config_validation = validate_configuration(compiled, configuration)
    if not config_validation.ok:
        messages = "; ".join(issue.message for issue in config_validation.issues if issue.severity == "error")
        raise ValueError(messages)
    t_validation = time.perf_counter()
    layout = runtime_layout(compiled, configuration)
    centers_mm = layout.centers_mm
    rotations = layout.rotations
    t_layout = time.perf_counter()
    wavelengths = wavelengths or [compiled.system.wavelengths_nm.primary]
    samples_per_field = int(sampling.get("samples_per_field", 1))
    distribution = sampling.get("pupil_distribution", "hexapolar")
    aiming = sampling.get("ray_aiming", {})
    aiming_mode = aiming.get("mode", "paraxial")
    tolerance_mm = float(aiming.get("tolerance_mm", 1.0e-6))
    max_iterations = int(aiming.get("max_iterations", 20))
    store_path = bool(options.get("store_path", False))

    samples = _unit_disk_samples(samples_per_field, distribution)
    targets = _target_points_for_stop_with_layout(compiled, samples, centers_mm, rotations, configuration)
    first_x = centers_mm[0, 0]
    stop_idx, stop_outer, _ = _aperture_radius(compiled, configuration)
    launch_x = min(first_x, targets[0, 0]) - max(100.0, 10.0 * stop_outer)

    origins: list[np.ndarray] = []
    directions: list[np.ndarray] = []
    ray_wavelengths: list[float] = []
    field_ids: list[str] = []
    aiming_ok: list[bool] = []
    aiming_iterations: list[int] = []

    for field in fields:
        if field.get("type", "angular") != "angular":
            raise NotImplementedError("only angular fields are implemented in this v2.1 build")
        direction = field_direction(float(field.get("theta_y_deg", 0.0)), float(field.get("theta_z_deg", 0.0)))
        for wavelength in wavelengths:
            for target in targets:
                if aiming_mode == "full":
                    origin, ok, iterations = _aim_origin_to_stop(
                        compiled,
                        launch_x,
                        direction,
                        float(wavelength),
                        target,
                        centers_mm,
                        rotations,
                        tolerance_mm=tolerance_mm,
                        max_iterations=max_iterations,
                        configuration=configuration,
                    )
                else:
                    origin = target - direction * ((target[0] - launch_x) / direction[0])
                    origin[0] = launch_x
                    ok = True
                    iterations = 0
                origins.append(origin)
                directions.append(direction)
                ray_wavelengths.append(float(wavelength))
                field_ids.append(str(field.get("id", "field")))
                aiming_ok.append(ok)
                aiming_iterations.append(iterations)
    t_generation = time.perf_counter()

    result = _trace_raw(
        compiled,
        np.array(origins, dtype=float),
        np.array(directions, dtype=float),
        np.array(ray_wavelengths, dtype=float),
        field_ids=field_ids,
        store_path=store_path,
        centers_mm=centers_mm,
        rotations=rotations,
        configuration=configuration,
    )
    t_trace = time.perf_counter()
    aiming_ok_array = np.array(aiming_ok, dtype=bool)
    result.status[~aiming_ok_array] = STATUS_AIMING_FAILED
    result.metadata.update(
        {
            "ray_aiming_mode": aiming_mode,
            "aiming_failed_count": int(np.sum(~aiming_ok_array)),
            "aiming_iterations_max": int(max(aiming_iterations) if aiming_iterations else 0),
            "samples_per_field": samples_per_field,
        }
    )
    if include_analysis_metadata:
        result.metadata.update(
            {
                "pupil_distribution": distribution,
                "wavelengths_nm": [float(wavelength) for wavelength in wavelengths],
                "evaluated_fields": [
                    {
                        "id": str(field.get("id", f"field_{idx + 1}")),
                        "type": str(field.get("type", "angular")),
                        "theta_y_deg": float(field.get("theta_y_deg", 0.0)),
                        "theta_z_deg": float(field.get("theta_z_deg", 0.0)),
                    }
                    for idx, field in enumerate(fields)
                ],
            }
        )
    if profiling:
        result.metadata["profiling"] = {
            "validation_ms": (t_validation - t0) * 1000.0,
            "layout_ms": (t_layout - t_validation) * 1000.0,
            "ray_generation_and_aiming_ms": (t_generation - t_layout) * 1000.0,
            "trace_ms": (t_trace - t_generation) * 1000.0,
            "total_ms": (t_trace - t0) * 1000.0,
            "total_rays": int(result.status.size),
            "cache_hit": None,
            "aiming_failed_count": int(np.sum(~aiming_ok_array)),
            "aiming_iterations_max": int(max(aiming_iterations) if aiming_iterations else 0),
        }
    return result


def _material_before_surface(compiled: CompiledSystem, surface_idx: int, wavelength_nm: float) -> float:
    if surface_idx <= 0:
        return compiled.material_index("AIR", wavelength_nm)
    return compiled.material_index(compiled.surfaces[surface_idx - 1].material_after, wavelength_nm)


def trace_reverse(
    compiled: CompiledSystem,
    sensor_points: list[dict[str, Any]] | None = None,
    directions: list[dict[str, Any]] | None = None,
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> ReverseTraceResult:
    options = options or {}
    configuration = options.get("configuration") or options.get("config") or {}
    config_validation = validate_configuration(compiled, configuration)
    if not config_validation.ok:
        messages = "; ".join(issue.message for issue in config_validation.issues if issue.severity == "error")
        raise ValueError(messages)
    if compiled.sensor_index is None:
        raise ValueError("reverse tracing requires a sensor surface")
    layout = runtime_layout(compiled, configuration)
    rotations = layout.rotations
    centers_mm = layout.centers_mm
    sensor_points = sensor_points or [{"y_mm": 0.0, "z_mm": 0.0}]
    wavelengths = [float(w) for w in (wavelengths or [compiled.system.wavelengths_nm.primary])]

    origins: list[np.ndarray] = []
    dirs: list[np.ndarray] = []
    ray_wavelengths: list[float] = []
    sensor_center = centers_mm[compiled.sensor_index]
    sensor_rotation = rotations[compiled.sensor_index]
    for wavelength in wavelengths:
        for idx, point in enumerate(sensor_points):
            local_point = np.array([0.0, float(point.get("y_mm", point.get("sensor_y_mm", 0.0))), float(point.get("z_mm", point.get("sensor_z_mm", 0.0)))])
            origins.append(sensor_center + local_point @ sensor_rotation.T)
            if directions and idx < len(directions):
                entry = directions[idx]
                local_dir = np.array(
                    [
                        float(entry.get("x", entry.get("dx", -1.0))),
                        float(entry.get("y", entry.get("dy", 0.0))),
                        float(entry.get("z", entry.get("dz", 0.0))),
                    ],
                    dtype=float,
                )
            else:
                local_dir = np.array([-1.0, 0.0, 0.0], dtype=float)
            dirs.append(normalize(local_dir.reshape(1, 3))[0] @ sensor_rotation.T)
            ray_wavelengths.append(wavelength)

    n_rays = len(origins)
    current_origins = np.array(origins, dtype=float)
    current_dirs = normalize(np.array(dirs, dtype=float))
    wavelengths_nm = np.array(ray_wavelengths, dtype=float)
    status = np.full(n_rays, STATUS_ALIVE, dtype=object)
    paths: list[list[dict[str, Any]]] = [[] for _ in range(n_rays)]
    store_path = bool(options.get("store_path", True))

    for surface_idx in range(compiled.sensor_index - 1, -1, -1):
        surface = compiled.surfaces[surface_idx]
        alive = status == STATUS_ALIVE
        if not np.any(alive):
            break
        alive_indices = np.where(alive)[0]
        center = centers_mm[surface_idx]
        rotation = rotations[surface_idx]
        local_origins = (current_origins[alive] - center) @ rotation
        local_dirs_alive = current_dirs[alive] @ rotation
        if surface.kind in {"refractive", "mirror"}:
            points_alive, valid_alive = intersect_surface(local_origins, local_dirs_alive, 0.0, surface)
        else:
            points_alive, valid_alive = intersect_sphere(local_origins, local_dirs_alive, 0.0, 0.0)
        local_points_alive = points_alive.copy()
        points_alive = points_alive @ rotation.T + center
        invalid_indices = alive_indices[~valid_alive]
        status[invalid_indices] = STATUS_MISSED
        valid_indices = alive_indices[valid_alive]
        if valid_indices.size == 0:
            continue
        local_points = np.full_like(current_origins, np.nan)
        local_points[valid_indices] = local_points_alive[valid_alive]
        points = np.full_like(current_origins, np.nan)
        points[valid_indices] = points_alive[valid_alive]
        passes = aperture_pass(local_points[valid_indices], surface)
        blocked = valid_indices[~passes]
        status[blocked] = STATUS_BLOCKED
        valid_indices = valid_indices[passes]
        if valid_indices.size == 0:
            continue
        current_origins[valid_indices] = points[valid_indices]
        if store_path:
            for ray_idx in valid_indices:
                paths[ray_idx].append(
                    {
                        "surface_id": surface.id,
                        "point_mm": points[ray_idx].tolist(),
                        "local_point_mm": local_points[ray_idx].tolist(),
                        "direction": current_dirs[ray_idx].tolist(),
                        "status": str(status[ray_idx]),
                    }
                )

        if surface.kind == "refractive":
            normals = surface_normals_for_surface(local_points[valid_indices], 0.0, surface)
            n_from = np.array([compiled.material_index(surface.material_after, wl) for wl in wavelengths_nm[valid_indices]])
            n_to = np.array([_material_before_surface(compiled, surface_idx, wl) for wl in wavelengths_nm[valid_indices]])
            local_in_dirs = current_dirs[valid_indices] @ rotation
            out_dirs_local, refract_ok = refract(local_in_dirs, normals, n_from, n_to)
            tir_indices = valid_indices[~refract_ok]
            status[tir_indices] = STATUS_TIR
            ok_indices = valid_indices[refract_ok]
            current_dirs[ok_indices] = out_dirs_local[refract_ok] @ rotation.T
        elif surface.kind == "mirror":
            normals = surface_normals_for_surface(local_points[valid_indices], 0.0, surface)
            local_in_dirs = current_dirs[valid_indices] @ rotation
            current_dirs[valid_indices] = reflect(local_in_dirs, normals) @ rotation.T
        elif surface.kind == "thin_lens":
            local_in = current_dirs[valid_indices] @ rotation
            local_out = local_in.copy()
            f = float(surface.focal_length_mm)
            local_out[:, 1] += local_points[valid_indices, 1] / f
            local_out[:, 2] += local_points[valid_indices, 2] / f
            current_dirs[valid_indices] = normalize(local_out) @ rotation.T

    object_theta_y = np.rad2deg(np.arctan2(current_dirs[:, 1], current_dirs[:, 0]))
    object_theta_z = np.rad2deg(np.arctan2(current_dirs[:, 2], current_dirs[:, 0]))
    return ReverseTraceResult(
        origins=current_origins,
        directions=current_dirs,
        wavelengths_nm=wavelengths_nm,
        status=status,
        object_theta_y_deg=object_theta_y,
        object_theta_z_deg=object_theta_z,
        paths=paths,
        metadata={"system_hash": compiled.system_hash, "method": "reverse_surface_sequence"},
    )
