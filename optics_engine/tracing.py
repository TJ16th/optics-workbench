from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
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
from .models import StructuredOpticsError
from .system import CompiledSystem

STATUS_ALIVE = "alive"
STATUS_BLOCKED = "blocked"
STATUS_MISSED = "missed"
STATUS_TIR = "total_internal_reflection"
STATUS_AIMING_FAILED = "aiming_failed"

# Retain the public/internal name used by existing diagnostics. Values are
# exact solved origin bundles, not affine coefficients.
_AIMING_AFFINE_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}


@dataclass
class TraceResult:
    origins: np.ndarray
    directions: np.ndarray
    wavelengths_nm: np.ndarray
    field_ids: list[str]
    status: np.ndarray
    sensor_y_mm: np.ndarray
    sensor_z_mm: np.ndarray
    weights: np.ndarray | None = None
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
class CandidateTraceResult:
    """Raw trace results with a leading candidate axis."""

    origins: np.ndarray
    directions: np.ndarray
    wavelengths_nm: np.ndarray
    field_ids: list[list[str]]
    status: np.ndarray
    sensor_y_mm: np.ndarray
    sensor_z_mm: np.ndarray
    paths: list[list[list[dict[str, Any]]]]
    metadata: dict[str, Any] = field(default_factory=dict)
    eye_theta_y_deg: np.ndarray | None = None
    eye_theta_z_deg: np.ndarray | None = None

    def candidate(self, index: int) -> TraceResult:
        return TraceResult(
            origins=self.origins[index],
            directions=self.directions[index],
            wavelengths_nm=self.wavelengths_nm[index],
            field_ids=self.field_ids[index],
            status=self.status[index],
            sensor_y_mm=self.sensor_y_mm[index],
            sensor_z_mm=self.sensor_z_mm[index],
            paths=self.paths[index],
            metadata={"system_hash": self.metadata["system_hashes"][index]},
            eye_theta_y_deg=None if self.eye_theta_y_deg is None else self.eye_theta_y_deg[index],
            eye_theta_z_deg=None if self.eye_theta_z_deg is None else self.eye_theta_z_deg[index],
        )


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


def _sobol_2d(count: int, seed: int) -> np.ndarray:
    bits = 32
    directions = np.zeros((2, bits), dtype=np.uint32)
    for bit in range(bits):
        directions[0, bit] = np.uint32(1 << (31 - bit))
    directions[1, 0] = np.uint32(1 << 31)
    directions[1, 1] = np.uint32(3 << 30)
    for bit in range(2, bits):
        directions[1, bit] = directions[1, bit - 2] ^ (directions[1, bit - 2] >> np.uint32(2)) ^ directions[1, bit - 1]
    points = np.empty((count, 2), dtype=float)
    digital_shift = np.random.default_rng(seed).integers(0, 2**32, size=2, dtype=np.uint32)
    for index in range(count):
        gray = index ^ (index >> 1)
        value = np.zeros(2, dtype=np.uint32)
        bit = 0
        while gray:
            if gray & 1:
                value ^= directions[:, bit]
            gray >>= 1
            bit += 1
        points[index] = (value ^ digital_shift).astype(np.float64) / float(2**32)
    return points


def _hexapolar_samples(count: int) -> np.ndarray:
    points = [np.array([0.0, 0.0])]
    ring = 1
    while len(points) < count:
        ring_count = 6 * ring
        radius = ring / max(1, int(np.ceil((np.sqrt(12 * count - 3) - 3) / 6)))
        take = min(ring_count, count - len(points))
        angles = 2.0 * np.pi * np.arange(take) / take
        points.extend(np.column_stack([radius * np.cos(angles), radius * np.sin(angles)]))
        ring += 1
    result = np.asarray(points[:count], dtype=float)
    grid_size = int(np.ceil(np.sqrt(count * 4.0 / np.pi))) + 1
    values = np.linspace(-1.0, 1.0, grid_size)
    legacy_grid = np.array([(y, z) for y in values for z in values if y * y + z * z <= 1.0 + 1.0e-12], dtype=float)
    legacy_grid = legacy_grid[np.argsort(np.sum(legacy_grid * legacy_grid, axis=1))][:count]
    target_radius = float(np.max(np.linalg.norm(legacy_grid, axis=1)))
    actual_radius = float(np.max(np.linalg.norm(result, axis=1)))
    if actual_radius > 0.0:
        result *= target_radius / actual_radius
    return result


def _polar_samples(count: int) -> np.ndarray:
    if count == 1:
        return np.array([[0.0, 0.0]], dtype=float)
    rings = max(1, int(np.ceil(np.sqrt(count))))
    points: list[np.ndarray] = []
    remaining = count
    for ring in range(1, rings + 1):
        rings_left = rings - ring + 1
        ring_count = max(1, remaining // rings_left)
        radius = np.sqrt((ring - 0.5) / rings)
        angles = 2.0 * np.pi * np.arange(ring_count) / ring_count + (ring % 2) * np.pi / ring_count
        points.extend(np.column_stack([radius * np.cos(angles), radius * np.sin(angles)]))
        remaining -= ring_count
    return np.asarray(points[:count], dtype=float)


def _gaussian_quadrature_samples(count: int) -> tuple[np.ndarray, np.ndarray]:
    radial_count = max(factor for factor in range(1, int(np.sqrt(count)) + 1) if count % factor == 0)
    angular_count = count // radial_count
    nodes, radial_weights = np.polynomial.legendre.leggauss(radial_count)
    radial_t = 0.5 * (nodes + 1.0)
    radial_weights = 0.5 * radial_weights
    points: list[tuple[float, float]] = []
    weights: list[float] = []
    for radial_index, t_value in enumerate(radial_t):
        radius = np.sqrt(t_value)
        for angular_index in range(angular_count):
            angle = 2.0 * np.pi * angular_index / angular_count
            points.append((radius * np.cos(angle), radius * np.sin(angle)))
            weights.append(float(radial_weights[radial_index] / angular_count))
    normalized = np.asarray(weights, dtype=float)
    normalized /= np.sum(normalized)
    return np.asarray(points, dtype=float), normalized


def _unit_disk_samples_with_weights(count: int, distribution: str = "hexapolar", seed: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    if count <= 1:
        return np.array([[0.0, 0.0]], dtype=float), np.ones(1, dtype=float)
    if distribution == "fan_y":
        points = np.column_stack([np.linspace(-1.0, 1.0, count), np.zeros(count)])
        return points, np.full(count, 1.0 / count)
    if distribution == "fan_z":
        points = np.column_stack([np.zeros(count), np.linspace(-1.0, 1.0, count)])
        return points, np.full(count, 1.0 / count)
    if distribution == "random":
        if seed is None:
            raise StructuredOpticsError(
                "optics_value_error",
                "A seed is required for random pupil sampling.",
                params={"pupil_distribution": distribution, "required_parameter": "seed"},
            )
        rng = np.random.default_rng(seed)
        radius = np.sqrt(rng.random(count))
        angle = 2.0 * np.pi * rng.random(count)
        points = np.column_stack([radius * np.cos(angle), radius * np.sin(angle)])
        return points, np.full(count, 1.0 / count)
    if distribution == "sobol":
        if seed is None:
            raise StructuredOpticsError(
                "optics_value_error",
                "A seed is required for sobol pupil sampling.",
                params={"pupil_distribution": distribution, "required_parameter": "seed"},
            )
        uv = _sobol_2d(count, seed)
        radius = np.sqrt(uv[:, 0])
        angle = 2.0 * np.pi * uv[:, 1]
        points = np.column_stack([radius * np.cos(angle), radius * np.sin(angle)])
        return points, np.full(count, 1.0 / count)
    if distribution == "polar":
        return _polar_samples(count), np.full(count, 1.0 / count)
    if distribution == "hexapolar":
        return _hexapolar_samples(count), np.full(count, 1.0 / count)
    if distribution == "gaussian_quadrature":
        return _gaussian_quadrature_samples(count)
    if distribution != "grid":
        raise StructuredOpticsError(
            "optics_value_error",
            "Unknown pupil distribution.",
            params={
                "pupil_distribution": distribution,
                "supported_distributions": ["grid", "fan_y", "fan_z", "random", "sobol", "polar", "hexapolar", "gaussian_quadrature"],
            },
        )

    grid_size = int(np.ceil(np.sqrt(count * 4.0 / np.pi))) + 1
    values = np.linspace(-1.0, 1.0, grid_size)
    pts = np.array([(y, z) for y in values for z in values if y * y + z * z <= 1.0 + 1.0e-12], dtype=float)
    order = np.argsort(np.sum(pts * pts, axis=1))
    pts = pts[order]
    if pts.shape[0] < count:
        angles = np.linspace(0.0, 2.0 * np.pi, count - pts.shape[0], endpoint=False)
        extra = np.column_stack([np.cos(angles), np.sin(angles)])
        pts = np.vstack([pts, extra])
    return pts[:count], np.full(count, 1.0 / count)


def _unit_disk_samples(count: int, distribution: str = "hexapolar", seed: int | None = None) -> np.ndarray:
    return _unit_disk_samples_with_weights(count, distribution, seed)[0]


def _configuration_variables(configuration: dict[str, Any] | None) -> dict[str, Any]:
    variables = (configuration or {}).get("variables", {})
    return variables if isinstance(variables, dict) else {}


def _runtime_iris_radius(configuration: dict[str, Any] | None) -> float | None:
    variables = _configuration_variables(configuration)
    if "iris_radius_mm" not in variables:
        return None
    value = float(variables["iris_radius_mm"])
    if not np.isfinite(value) or value <= 0.0:
        raise StructuredOpticsError(
            "optics_value_error",
            "Iris radius must be a positive finite value.",
            params={"iris_radius_mm": value, "constraint": "finite value > 0"},
        )
    return value


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


def _normalize_vec(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return np.zeros_like(vector, dtype=float) if norm <= 0.0 else vector / norm


def _asphere_sag_and_slope_scalar(r: float, radius_mm: float, conic: float, coefficients: dict[str, float]) -> tuple[float, float]:
    c = 0.0 if abs(radius_mm) < 1.0e-10 else 1.0 / radius_mm
    r2 = r * r
    if abs(c) < 1.0e-10:
        base = 0.0
        base_slope = 0.0
    else:
        q = 1.0 - (1.0 + conic) * c * c * r2
        sqrt_q = float(np.sqrt(max(q, 1.0e-10)))
        base = c * r2 / (1.0 + sqrt_q)
        h = max(1.0e-6, abs(r) * 1.0e-6)
        r_plus = r + h
        r_minus = max(0.0, r - h)
        q_plus = 1.0 - (1.0 + conic) * c * c * r_plus * r_plus
        q_minus = 1.0 - (1.0 + conic) * c * c * r_minus * r_minus
        sag_plus = c * r_plus * r_plus / (1.0 + float(np.sqrt(max(q_plus, 1.0e-10))))
        sag_minus = c * r_minus * r_minus / (1.0 + float(np.sqrt(max(q_minus, 1.0e-10))))
        base_slope = (sag_plus - sag_minus) / max(r_plus - r_minus, 1.0e-10)

    extra = 0.0
    extra_slope = 0.0
    for key, value in coefficients.items():
        if not key.startswith("A"):
            continue
        order = int(key[1:])
        extra += float(value) * (r**order)
        if order > 0:
            extra_slope += order * float(value) * (r ** (order - 1))
    return base + extra, base_slope + extra_slope


def _intersect_surface_scalar(origin: np.ndarray, direction: np.ndarray, surface) -> np.ndarray | None:
    if surface.surface_type == "plane" or (surface.kind not in {"refractive", "mirror"} and surface.surface_type != "aspherical_even"):
        denom = direction[0]
        if abs(denom) <= 1.0e-10:
            return None
        t = -origin[0] / denom
        return origin + direction * t if np.isfinite(t) and t >= -1.0e-8 else None

    radius = float(surface.radius_mm)
    if abs(radius) < 1.0e-10:
        denom = direction[0]
        if abs(denom) <= 1.0e-10:
            return None
        t = -origin[0] / denom
        return origin + direction * t if np.isfinite(t) and t >= -1.0e-8 else None

    center = np.array([radius, 0.0, 0.0], dtype=float)
    oc = origin - center
    b = 2.0 * float(np.dot(oc, direction))
    c = float(np.dot(oc, oc)) - radius * radius
    disc = b * b - 4.0 * c
    if disc < 0.0:
        return None
    sqrt_disc = float(np.sqrt(max(disc, 0.0)))
    t1 = (-b - sqrt_disc) / 2.0
    t2 = (-b + sqrt_disc) / 2.0
    t = t1 if t1 >= -1.0e-8 else t2
    if not np.isfinite(t) or t < -1.0e-8:
        return None

    if surface.surface_type != "aspherical_even":
        return origin + direction * t

    for _ in range(12):
        point = origin + direction * t
        y = float(point[1])
        z = float(point[2])
        r = float(np.sqrt(y * y + z * z))
        sag, slope = _asphere_sag_and_slope_scalar(r, radius, float(surface.conic), surface.asphere_coefficients)
        f = point[0] - sag
        drdt = 0.0 if r <= 1.0e-10 else (y * direction[1] + z * direction[2]) / r
        dfdt = direction[0] - slope * drdt
        if abs(dfdt) <= 1.0e-10:
            return None
        delta = f / dfdt
        t -= delta
        if abs(delta) >= 1.0e6:
            return None
        if abs(delta) < 1.0e-10:
            break
    return origin + direction * t if np.isfinite(t) and t >= -1.0e-8 else None


def _surface_normal_scalar(local_point: np.ndarray, surface) -> np.ndarray:
    if surface.surface_type == "plane" or abs(float(surface.radius_mm)) < 1.0e-10:
        if surface.surface_type != "aspherical_even":
            return np.array([1.0, 0.0, 0.0], dtype=float)
    if surface.surface_type != "aspherical_even":
        return _normalize_vec(local_point - np.array([float(surface.radius_mm), 0.0, 0.0], dtype=float))

    y = float(local_point[1])
    z = float(local_point[2])
    r = float(np.sqrt(y * y + z * z))
    _, slope = _asphere_sag_and_slope_scalar(r, float(surface.radius_mm), float(surface.conic), surface.asphere_coefficients)
    dsdy = 0.0 if r <= 1.0e-10 else slope * y / r
    dsdz = 0.0 if r <= 1.0e-10 else slope * z / r
    return _normalize_vec(np.array([1.0, -dsdy, -dsdz], dtype=float))


def _aperture_pass_scalar(local_point: np.ndarray, surface, surface_idx: int, compiled: CompiledSystem, configuration: dict[str, Any] | None) -> bool:
    radius = float(np.sqrt(local_point[1] * local_point[1] + local_point[2] * local_point[2]))
    runtime_outer = _runtime_iris_radius(configuration) if compiled.aperture_stop_index == surface_idx else None
    if runtime_outer is not None:
        inner = 0.0
        if surface.aperture is not None and surface.aperture.shape == "annulus":
            inner = surface.aperture.inner_semi_diameter_mm or 0.0
        return radius <= runtime_outer + 1.0e-9 and radius >= inner - 1.0e-9
    if surface.aperture is not None:
        aperture = surface.aperture
        if aperture.shape == "annulus":
            outer = aperture.outer_semi_diameter_mm if aperture.outer_semi_diameter_mm is not None else aperture.semi_diameter_mm
            inner = aperture.inner_semi_diameter_mm or 0.0
            return True if outer is None else radius <= outer + 1.0e-9 and radius >= inner - 1.0e-9
        if aperture.shape == "circle":
            outer = aperture.semi_diameter_mm or aperture.outer_semi_diameter_mm or surface.semi_diameter_mm
            return True if outer is None else radius <= outer + 1.0e-9
        raise NotImplementedError("polygon apertures are reserved for a later phase")
    if surface.semi_diameter_mm is None:
        if getattr(surface, "kind", None) == "eye_reference" and getattr(surface, "eye", None) is not None:
            return radius <= surface.eye.pupil_diameter_mm / 2.0 + 1.0e-9
        return True
    return radius <= surface.semi_diameter_mm + 1.0e-9


def _refract_scalar(direction: np.ndarray, normal: np.ndarray, n_before: float, n_after: float) -> np.ndarray | None:
    oriented = normal.copy()
    cos_i = -float(np.dot(oriented, direction))
    if cos_i < 0.0:
        oriented *= -1.0
        cos_i = -float(np.dot(oriented, direction))
    eta = n_before / n_after
    k = 1.0 - eta * eta * (1.0 - cos_i * cos_i)
    if k < -1.0e-12:
        return None
    out = eta * direction + (eta * cos_i - float(np.sqrt(max(k, 0.0)))) * oriented
    return _normalize_vec(out)


def _reflect_scalar(direction: np.ndarray, normal: np.ndarray) -> np.ndarray:
    return _normalize_vec(direction - 2.0 * float(np.dot(direction, normal)) * normal)


def _thin_lens_transform_scalar(local_point: np.ndarray, local_dir: np.ndarray, focal_length_mm: float) -> np.ndarray:
    dx = local_dir[0]
    if abs(dx) <= 1.0e-10:
        return np.zeros(3, dtype=float)
    sign = 1.0 if dx >= 0.0 else -1.0
    return _normalize_vec(
        np.array(
            [
                sign,
                sign * (local_dir[1] / dx - local_point[1] / focal_length_mm),
                sign * (local_dir[2] / dx - local_point[2] / focal_length_mm),
            ],
            dtype=float,
        )
    )


def _material_indices_for_wavelengths(compiled: CompiledSystem, material_id: str | None, wavelengths_nm: np.ndarray) -> np.ndarray:
    material_id = material_id or "AIR"
    if wavelengths_nm.size == 0:
        return np.array([], dtype=float)
    if np.all(wavelengths_nm == wavelengths_nm[0]):
        return np.full(wavelengths_nm.shape, compiled.material_index(material_id, float(wavelengths_nm[0])), dtype=float)
    unique, inverse = np.unique(wavelengths_nm, return_inverse=True)
    values = np.array([compiled.material_index(material_id, float(wavelength)) for wavelength in unique], dtype=float)
    return values[inverse]


def _candidate_batch_eligible(compiled_candidates: list[CompiledSystem]) -> bool:
    if not compiled_candidates:
        return True
    reference = compiled_candidates[0]
    topology = tuple((surface.id, surface.kind, surface.surface_type) for surface in reference.surfaces)
    material_ids = tuple(material.id for material in reference.system.materials)
    material_order = tuple(surface.material_after for surface in reference.surfaces)
    for compiled in compiled_candidates[1:]:
        if tuple((surface.id, surface.kind, surface.surface_type) for surface in compiled.surfaces) != topology:
            return False
        if tuple(material.id for material in compiled.system.materials) != material_ids:
            return False
        if tuple(surface.material_after for surface in compiled.surfaces) != material_order:
            return False
    return True


def _candidate_field_ids(field_ids: list[str] | list[list[str]] | None, candidate_count: int, ray_count: int) -> list[list[str]]:
    if field_ids is None:
        return [["field"] * ray_count for _ in range(candidate_count)]
    if candidate_count and field_ids and isinstance(field_ids[0], str):
        common = [str(value) for value in field_ids]
        if len(common) != ray_count:
            raise ValueError("field_ids must match the ray axis")
        return [common.copy() for _ in range(candidate_count)]
    nested = [[str(value) for value in values] for values in field_ids]
    if len(nested) != candidate_count or any(len(values) != ray_count for values in nested):
        raise ValueError("field_ids must have shape [candidate, ray]")
    return nested


def _stack_candidate_results(results: list[TraceResult], *, batch_eligible: bool, chunk_size: int) -> CandidateTraceResult:
    candidate_count = len(results)
    ray_count = results[0].status.size if results else 0
    return CandidateTraceResult(
        origins=np.stack([result.origins for result in results]) if results else np.empty((0, ray_count, 3)),
        directions=np.stack([result.directions for result in results]) if results else np.empty((0, ray_count, 3)),
        wavelengths_nm=np.stack([result.wavelengths_nm for result in results]) if results else np.empty((0, ray_count)),
        field_ids=[result.field_ids for result in results],
        status=np.stack([result.status for result in results]) if results else np.empty((0, ray_count), dtype=object),
        sensor_y_mm=np.stack([result.sensor_y_mm for result in results]) if results else np.empty((0, ray_count)),
        sensor_z_mm=np.stack([result.sensor_z_mm for result in results]) if results else np.empty((0, ray_count)),
        paths=[result.paths for result in results],
        metadata={
            "batch_eligible": batch_eligible,
            "fallback_used": not batch_eligible,
            "candidate_chunk_size": chunk_size,
            "system_hashes": [result.metadata["system_hash"] for result in results],
        },
        eye_theta_y_deg=np.stack([result.eye_theta_y_deg for result in results]) if results else np.empty((0, ray_count)),
        eye_theta_z_deg=np.stack([result.eye_theta_z_deg for result in results]) if results else np.empty((0, ray_count)),
    )


def _trace_raw_candidates(
    compiled_candidates: list[CompiledSystem],
    origins: np.ndarray,
    directions: np.ndarray,
    wavelengths_nm: np.ndarray,
    *,
    field_ids: list[str] | list[list[str]] | None = None,
    stop_at_surface_index: int | None = None,
    store_path: bool = True,
    configurations: list[dict[str, Any] | None] | None = None,
    candidate_chunk_size: int | None = None,
) -> CandidateTraceResult:
    """Trace equal-topology systems while retaining a dense candidate axis.

    Ineligible candidate sets deliberately use the independent Level 1 path.
    Chunking is candidate ordered and therefore cannot change per-candidate ray
    ordering or numerical reductions.
    """

    candidate_count = len(compiled_candidates)
    origins = np.asarray(origins, dtype=float)
    directions = np.asarray(directions, dtype=float)
    wavelengths_nm = np.asarray(wavelengths_nm, dtype=float)
    if origins.ndim != 3 or origins.shape[-1] != 3:
        raise ValueError("origins must have shape [candidate, ray, 3]")
    if directions.shape != origins.shape:
        raise ValueError("directions must match origins")
    if wavelengths_nm.shape != origins.shape[:2]:
        raise ValueError("wavelengths_nm must have shape [candidate, ray]")
    if origins.shape[0] != candidate_count:
        raise ValueError("candidate inputs must match compiled_candidates")
    ray_count = origins.shape[1]
    candidate_fields = _candidate_field_ids(field_ids, candidate_count, ray_count)
    configurations = configurations or [None] * candidate_count
    if len(configurations) != candidate_count:
        raise ValueError("configurations must match compiled_candidates")
    chunk_size = candidate_count if candidate_chunk_size is None else int(candidate_chunk_size)
    if chunk_size <= 0:
        raise ValueError("candidate_chunk_size must be positive")
    chunk_size = max(1, min(chunk_size, max(candidate_count, 1)))

    eligible = _candidate_batch_eligible(compiled_candidates)
    if not eligible:
        results = []
        for index, compiled in enumerate(compiled_candidates):
            layout = runtime_layout(compiled, configurations[index])
            results.append(
                _trace_raw(
                    compiled,
                    origins[index],
                    directions[index],
                    wavelengths_nm[index],
                    field_ids=candidate_fields[index],
                    stop_at_surface_index=stop_at_surface_index,
                    store_path=store_path,
                    centers_mm=layout.centers_mm,
                    rotations=layout.rotations,
                    configuration=configurations[index],
                )
            )
        return _stack_candidate_results(results, batch_eligible=False, chunk_size=chunk_size)

    current_dirs = normalize(directions.copy())
    current_origins = origins.copy()
    status = np.full((candidate_count, ray_count), STATUS_ALIVE, dtype=object)
    sensor_y = np.full((candidate_count, ray_count), np.nan)
    sensor_z = np.full((candidate_count, ray_count), np.nan)
    eye_theta_y = np.full((candidate_count, ray_count), np.nan)
    eye_theta_z = np.full((candidate_count, ray_count), np.nan)
    current_n = np.empty((candidate_count, ray_count), dtype=float)
    paths: list[list[list[dict[str, Any]]]] = [[[] for _ in range(ray_count)] for _ in range(candidate_count)]
    layouts = [runtime_layout(compiled, configurations[index]) for index, compiled in enumerate(compiled_candidates)]
    surface_count = len(compiled_candidates[0].surfaces) if compiled_candidates else 0
    centers = np.stack([layout.centers_mm for layout in layouts]) if layouts else np.empty((0, 0, 3))
    rotations = np.stack([layout.rotations for layout in layouts]) if layouts else np.empty((0, 0, 3, 3))
    for candidate, compiled in enumerate(compiled_candidates):
        current_n[candidate] = _material_indices_for_wavelengths(compiled, "AIR", wavelengths_nm[candidate])

    for chunk_start in range(0, candidate_count, chunk_size):
        chunk_end = min(chunk_start + chunk_size, candidate_count)
        for surface_idx in range(surface_count):
            for candidate in range(chunk_start, chunk_end):
                compiled = compiled_candidates[candidate]
                surface = compiled.surfaces[surface_idx]
                alive = status[candidate] == STATUS_ALIVE
                if not np.any(alive):
                    continue
                alive_indices = np.where(alive)[0]
                center = centers[candidate, surface_idx]
                rotation = rotations[candidate, surface_idx]
                local_origins = (current_origins[candidate, alive] - center) @ rotation
                local_dirs_alive = current_dirs[candidate, alive] @ rotation
                if surface.kind in {"refractive", "mirror"}:
                    local_points, valid_alive = intersect_surface(local_origins, local_dirs_alive, 0.0, surface)
                else:
                    local_points, valid_alive = intersect_sphere(local_origins, local_dirs_alive, 0.0, 0.0)
                points = local_points @ rotation.T + center
                status[candidate, alive_indices[~valid_alive]] = STATUS_MISSED
                valid_indices = alive_indices[valid_alive]
                if valid_indices.size == 0:
                    continue
                valid_local_points = local_points[valid_alive]
                valid_points = points[valid_alive]
                if store_path:
                    for offset, ray_idx in enumerate(valid_indices):
                        paths[candidate][ray_idx].append(
                            {
                                "surface_id": surface.id,
                                "point_mm": valid_points[offset].tolist(),
                                "local_point_mm": valid_local_points[offset].tolist(),
                                "direction": current_dirs[candidate, ray_idx].tolist(),
                                "status": str(status[candidate, ray_idx]),
                            }
                        )
                passes = _aperture_pass_with_runtime(
                    valid_local_points, surface, surface_idx, compiled, configurations[candidate]
                )
                status[candidate, valid_indices[~passes]] = STATUS_BLOCKED
                valid_indices = valid_indices[passes]
                if valid_indices.size == 0:
                    continue
                valid_local_points = valid_local_points[passes]
                valid_points = valid_points[passes]
                current_origins[candidate, valid_indices] = valid_points
                if stop_at_surface_index is not None and surface_idx == stop_at_surface_index:
                    continue
                if surface.kind == "refractive":
                    normals = surface_normals_for_surface(valid_local_points, 0.0, surface)
                    n_after = _material_indices_for_wavelengths(
                        compiled, surface.material_after, wavelengths_nm[candidate, valid_indices]
                    )
                    local_in_dirs = current_dirs[candidate, valid_indices] @ rotation
                    out_dirs_local, refract_ok = refract(
                        local_in_dirs, normals, current_n[candidate, valid_indices], n_after
                    )
                    status[candidate, valid_indices[~refract_ok]] = STATUS_TIR
                    ok_indices = valid_indices[refract_ok]
                    current_dirs[candidate, ok_indices] = out_dirs_local[refract_ok] @ rotation.T
                    current_n[candidate, ok_indices] = n_after[refract_ok]
                elif surface.kind == "mirror":
                    normals = surface_normals_for_surface(valid_local_points, 0.0, surface)
                    local_in_dirs = current_dirs[candidate, valid_indices] @ rotation
                    current_dirs[candidate, valid_indices] = reflect(local_in_dirs, normals) @ rotation.T
                elif surface.kind == "thin_lens":
                    local_out = thin_lens_transform(
                        valid_local_points,
                        current_dirs[candidate, valid_indices] @ rotation,
                        0.0,
                        float(surface.focal_length_mm),
                    )
                    current_dirs[candidate, valid_indices] = local_out @ rotation.T
                elif surface.kind == "sensor":
                    sensor_y[candidate, valid_indices] = valid_local_points[:, 1]
                    sensor_z[candidate, valid_indices] = valid_local_points[:, 2]
                elif surface.kind == "eye_reference":
                    local_dirs = current_dirs[candidate, valid_indices] @ rotation
                    eye_theta_y[candidate, valid_indices] = np.rad2deg(np.arctan2(local_dirs[:, 1], local_dirs[:, 0]))
                    eye_theta_z[candidate, valid_indices] = np.rad2deg(np.arctan2(local_dirs[:, 2], local_dirs[:, 0]))
            if stop_at_surface_index is not None and surface_idx == stop_at_surface_index:
                break

    return CandidateTraceResult(
        origins=origins,
        directions=current_dirs,
        wavelengths_nm=wavelengths_nm,
        field_ids=candidate_fields,
        status=status,
        sensor_y_mm=sensor_y,
        sensor_z_mm=sensor_z,
        paths=paths,
        metadata={
            "batch_eligible": True,
            "fallback_used": False,
            "candidate_chunk_size": chunk_size,
            "surface_data_shape": list(centers.shape),
            "system_hashes": [compiled.system_hash for compiled in compiled_candidates],
        },
        eye_theta_y_deg=eye_theta_y,
        eye_theta_z_deg=eye_theta_z,
    )


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
    current_n = _material_indices_for_wavelengths(compiled, "AIR", wavelengths_nm)
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

        invalid_indices = alive_indices[~valid_alive]
        status[invalid_indices] = STATUS_MISSED
        valid_indices = alive_indices[valid_alive]
        if valid_indices.size == 0:
            continue
        valid_local_points = local_points_alive[valid_alive]
        valid_points = points_alive[valid_alive]

        if store_path:
            for offset, ray_idx in enumerate(valid_indices):
                paths[ray_idx].append(
                    {
                        "surface_id": surface.id,
                        "point_mm": valid_points[offset].tolist(),
                        "local_point_mm": valid_local_points[offset].tolist(),
                        "direction": current_dirs[ray_idx].tolist(),
                        "status": str(status[ray_idx]),
                    }
                )

        passes = _aperture_pass_with_runtime(valid_local_points, surface, surface_idx, compiled, configuration)
        blocked = valid_indices[~passes]
        status[blocked] = STATUS_BLOCKED
        valid_indices = valid_indices[passes]
        if valid_indices.size == 0:
            continue
        valid_local_points = valid_local_points[passes]
        valid_points = valid_points[passes]

        current_origins[valid_indices] = valid_points

        if stop_at_surface_index is not None and surface_idx == stop_at_surface_index:
            break

        if surface.kind == "refractive":
            normals = surface_normals_for_surface(valid_local_points, x_vertex, surface)
            n_after = _material_indices_for_wavelengths(compiled, surface.material_after, wavelengths_nm[valid_indices])
            local_in_dirs = current_dirs[valid_indices] @ rotation
            out_dirs_local, refract_ok = refract(local_in_dirs, normals, current_n[valid_indices], n_after)
            tir_indices = valid_indices[~refract_ok]
            status[tir_indices] = STATUS_TIR
            ok_indices = valid_indices[refract_ok]
            current_dirs[ok_indices] = out_dirs_local[refract_ok] @ rotation.T
            current_n[ok_indices] = n_after[refract_ok]
        elif surface.kind == "mirror":
            normals = surface_normals_for_surface(valid_local_points, x_vertex, surface)
            local_in_dirs = current_dirs[valid_indices] @ rotation
            current_dirs[valid_indices] = reflect(local_in_dirs, normals) @ rotation.T
            propagation_sign[valid_indices] *= -1
        elif surface.kind == "thin_lens":
            local_out = thin_lens_transform(
                valid_local_points,
                current_dirs[valid_indices] @ rotation,
                x_vertex,
                float(surface.focal_length_mm),
            )
            current_dirs[valid_indices] = local_out @ rotation.T
        elif surface.kind == "sensor":
            sensor_y[valid_indices] = valid_local_points[:, 1]
            sensor_z[valid_indices] = valid_local_points[:, 2]
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


def _trace_to_surface_point(
    compiled: CompiledSystem,
    origin: np.ndarray,
    direction: np.ndarray,
    wavelength_nm: float,
    surface_index: int,
    centers_mm: np.ndarray,
    rotations: np.ndarray,
    configuration: dict[str, Any] | None = None,
) -> np.ndarray | None:
    current_origin = origin.astype(float, copy=True)
    current_dir = _normalize_vec(direction.astype(float, copy=False))
    current_n = compiled.material_index("AIR", wavelength_nm)

    for idx, surface in enumerate(compiled.surfaces[: surface_index + 1]):
        center = centers_mm[idx]
        rotation = rotations[idx]
        local_origin = (current_origin - center) @ rotation
        local_dir = current_dir @ rotation
        local_point = _intersect_surface_scalar(local_origin, local_dir, surface)
        if local_point is None:
            return None
        if not _aperture_pass_scalar(local_point, surface, idx, compiled, configuration):
            return None

        point = local_point @ rotation.T + center
        current_origin = point
        if idx == surface_index:
            return point

        if surface.kind == "refractive":
            normal = _surface_normal_scalar(local_point, surface)
            n_after = compiled.material_index(surface.material_after, wavelength_nm)
            out_dir_local = _refract_scalar(local_dir, normal, current_n, n_after)
            if out_dir_local is None:
                return None
            current_dir = out_dir_local @ rotation.T
            current_n = n_after
        elif surface.kind == "mirror":
            normal = _surface_normal_scalar(local_point, surface)
            current_dir = _reflect_scalar(local_dir, normal) @ rotation.T
        elif surface.kind == "thin_lens":
            current_dir = _thin_lens_transform_scalar(local_point, local_dir, float(surface.focal_length_mm)) @ rotation.T

    return None


def _configuration_hash(configuration: dict[str, Any] | None) -> str:
    payload = json.dumps(configuration or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _aiming_cache_key(
    compiled: CompiledSystem,
    configuration: dict[str, Any] | None,
    field: dict[str, Any],
    wavelength_nm: float,
    stop_outer_mm: float,
    stop_inner_mm: float,
    launch_x: float,
    targets: np.ndarray,
    tolerance_mm: float,
    max_iterations: int,
) -> tuple[Any, ...]:
    canonical_targets = np.ascontiguousarray(targets, dtype=np.float64)
    targets_hash = hashlib.sha256(canonical_targets.tobytes()).hexdigest()
    return (
        compiled.system_hash,
        _configuration_hash(configuration),
        round(float(field.get("theta_y_deg", 0.0)), 12),
        round(float(field.get("theta_z_deg", 0.0)), 12),
        round(float(wavelength_nm), 9),
        compiled.aperture_stop_index,
        round(float(stop_outer_mm), 12),
        round(float(stop_inner_mm), 12),
        round(float(launch_x), 12),
        canonical_targets.shape,
        targets_hash,
        round(float(tolerance_mm), 15),
        int(max_iterations),
    )


def _aim_residual_to_stop(
    compiled: CompiledSystem,
    launch_x: float,
    direction: np.ndarray,
    wavelength_nm: float,
    target: np.ndarray,
    param: np.ndarray,
    centers_mm: np.ndarray,
    rotations: np.ndarray,
    configuration: dict[str, Any] | None = None,
) -> np.ndarray | None:
    if compiled.aperture_stop_index is None:
        return np.zeros(2, dtype=float)
    origin = np.array([launch_x, param[0], param[1]], dtype=float)
    point = _trace_to_surface_point(
        compiled,
        origin,
        direction,
        wavelength_nm,
        compiled.aperture_stop_index,
        centers_mm=centers_mm,
        rotations=rotations,
        configuration=configuration,
    )
    if point is None:
        return None
    return point[1:3] - target[1:3]


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
    initial_param: np.ndarray | None = None,
) -> tuple[np.ndarray, bool, int]:
    stop_idx = compiled.aperture_stop_index
    if stop_idx is None:
        origin = target - direction * ((target[0] - launch_x) / direction[0])
        origin[0] = launch_x
        return origin, True, 0

    stop_x = centers_mm[stop_idx, 0]
    p = (
        np.array(initial_param, dtype=float)
        if initial_param is not None
        else target[1:3] - direction[1:3] * ((stop_x - launch_x) / direction[0])
    )

    def residual(param: np.ndarray) -> np.ndarray | None:
        return _aim_residual_to_stop(
            compiled,
            launch_x,
            direction,
            wavelength_nm,
            target,
            param,
            centers_mm,
            rotations,
            configuration,
        )

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
        if initial_param is None:
            p -= delta
            continue
        if not np.all(np.isfinite(delta)) or np.linalg.norm(delta) > 100.0:
            return np.array([launch_x, p[0], p[1]], dtype=float), False, iterations
        accepted = False
        current_norm = float(np.linalg.norm(res))
        for damping in (1.0, 0.5, 0.25, 0.125, 0.0625):
            candidate = p - damping * delta
            candidate_residual = residual(candidate)
            if candidate_residual is not None and float(np.linalg.norm(candidate_residual)) < current_norm:
                p = candidate
                accepted = True
                break
        if not accepted:
            return np.array([launch_x, p[0], p[1]], dtype=float), False, iterations

    return np.array([launch_x, p[0], p[1]], dtype=float), False, iterations


def _paraxial_launch_origin(launch_x: float, direction: np.ndarray, target: np.ndarray) -> np.ndarray:
    origin = target - direction * ((target[0] - launch_x) / direction[0])
    origin[0] = launch_x
    return origin


def _exact_aim_origins(
    compiled: CompiledSystem,
    launch_x: float,
    direction: np.ndarray,
    wavelength_nm: float,
    targets: np.ndarray,
    centers_mm: np.ndarray,
    rotations: np.ndarray,
    *,
    tolerance_mm: float,
    max_iterations: int,
    configuration: dict[str, Any] | None,
    initial_params: dict[int, np.ndarray] | None = None,
    fallback_flags: list[bool] | None = None,
) -> tuple[list[np.ndarray], list[bool], list[int]]:
    origins: list[np.ndarray] = []
    ok: list[bool] = []
    iterations: list[int] = []
    for target_idx, target in enumerate(targets):
        used_fallback = False
        origin, origin_ok, origin_iterations = _aim_origin_to_stop(
            compiled,
            launch_x,
            direction,
            wavelength_nm,
            target,
            centers_mm,
            rotations,
            tolerance_mm=tolerance_mm,
            max_iterations=max_iterations,
            configuration=configuration,
            initial_param=None if initial_params is None else initial_params.get(target_idx),
        )
        if initial_params is not None and not origin_ok:
            used_fallback = True
            origin, origin_ok, cold_iterations = _aim_origin_to_stop(
                compiled,
                launch_x,
                direction,
                wavelength_nm,
                target,
                centers_mm,
                rotations,
                tolerance_mm=tolerance_mm,
                max_iterations=max_iterations,
                configuration=configuration,
                initial_param=None,
            )
            origin_iterations += cold_iterations
        if fallback_flags is not None:
            fallback_flags.append(used_fallback)
        origins.append(origin)
        ok.append(origin_ok)
        iterations.append(origin_iterations)
    return origins, ok, iterations


def _path_stop_y(path: list[dict[str, Any]], stop_id: str | None) -> float | None:
    entry = (next((item for item in path if stop_id is not None and item.get("surface_id") == stop_id), None)) or (path[0] if path else None)
    if entry is None:
        return None
    local = entry.get("local_point_mm")
    point = entry.get("point_mm")
    value = local[1] if isinstance(local, list) and len(local) > 1 else None
    if value is None and isinstance(point, list) and len(point) > 1:
        value = point[1]
    return float(value) if value is not None and np.isfinite(float(value)) else None


def _layout_baseline_rays(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    wavelengths: list[float],
    launch_x: float,
    centers_mm: np.ndarray,
    rotations: np.ndarray,
    *,
    tolerance_mm: float,
    max_iterations: int,
    configuration: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    stop_idx = compiled.aperture_stop_index
    # A system without an explicit stop still needs stable layout rays.  Its
    # first surface is also the launch reference used by the regular trace.
    reference_idx = 0 if stop_idx is None else stop_idx
    samples = np.array([[0.0, 0.0], [-1.0, 0.0], [1.0, 0.0]], dtype=float)
    roles = ["chief", "marginal_lower", "marginal_upper"]
    targets = _target_points_for_stop_with_layout(compiled, samples, centers_mm, rotations, configuration)
    _, _, stop_inner = _aperture_radius(compiled, configuration)
    if stop_inner > 0.0:
        # The chief ray is defined by the stop center even when an annular
        # obstruction blocks it. Do not relabel the +inner-edge sample as chief.
        targets[0] = centers_mm[reference_idx]
    stop_id = compiled.surfaces[reference_idx].id
    rows: list[dict[str, Any]] = []
    for field_index, field in enumerate(fields):
        direction = field_direction(float(field.get("theta_y_deg", 0.0)), float(field.get("theta_z_deg", 0.0)))
        field_id = str(field.get("id", f"field_{field_index + 1}"))
        for wavelength_index, wavelength in enumerate(wavelengths):
            origins, aiming_ok, aiming_iterations = _exact_aim_origins(
                compiled,
                launch_x,
                direction,
                float(wavelength),
                targets,
                centers_mm,
                rotations,
                tolerance_mm=tolerance_mm,
                max_iterations=max_iterations,
                configuration=configuration,
            )
            trace = _trace_raw(
                compiled,
                np.array(origins, dtype=float),
                np.tile(direction, (len(origins), 1)),
                np.full(len(origins), float(wavelength), dtype=float),
                field_ids=[field_id] * len(origins),
                store_path=True,
                centers_mm=centers_mm,
                rotations=rotations,
                configuration=configuration,
            )
            for ray_index, role in enumerate(roles):
                status = str(trace.status[ray_index])
                if not aiming_ok[ray_index] and not (stop_inner > 0.0 and role == "chief"):
                    status = STATUS_AIMING_FAILED
                rows.append(
                    {
                        "role": role,
                        "field_id": field_id,
                        "field_index": int(field_index),
                        "wavelength_nm": float(wavelength),
                        "wavelength_index": int(wavelength_index),
                        "status": status,
                        "path": trace.paths[ray_index],
                        "stop_y_mm": _path_stop_y(trace.paths[ray_index], stop_id),
                        "aiming_ok": bool(aiming_ok[ray_index]),
                        "aiming_iterations": int(aiming_iterations[ray_index]),
                    }
                )
    return rows


def _aim_origins_for_field_wavelength(
    compiled: CompiledSystem,
    field: dict[str, Any],
    direction: np.ndarray,
    wavelength_nm: float,
    targets: np.ndarray,
    launch_x: float,
    centers_mm: np.ndarray,
    rotations: np.ndarray,
    aiming: dict[str, Any],
    *,
    stop_outer_mm: float,
    stop_inner_mm: float,
    tolerance_mm: float,
    max_iterations: int,
    configuration: dict[str, Any] | None,
    workspace_key: tuple[Any, ...] | None = None,
) -> tuple[list[np.ndarray], list[bool], list[int], dict[str, Any]]:
    strategy = str(aiming.get("strategy", "affine"))
    workspace = aiming.get("_request_local_workspace")
    workspace_role = aiming.get("_workspace_role")
    if compiled.aperture_stop_index is None or strategy == "exact" or targets.shape[0] <= 1:
        initial_params = None
        if workspace is not None and workspace_role == "candidate" and workspace_key is not None:
            cached_origins = workspace.get("base_origins", {}).get(workspace_key)
            if cached_origins is not None and len(cached_origins) == len(targets):
                initial_params = {index: np.asarray(origin, dtype=float)[1:3] for index, origin in enumerate(cached_origins)}
        fallback_flags: list[bool] = []
        origins, ok, iterations = _exact_aim_origins(
            compiled,
            launch_x,
            direction,
            wavelength_nm,
            targets,
            centers_mm,
            rotations,
            tolerance_mm=tolerance_mm,
            max_iterations=max_iterations,
            configuration=configuration,
            initial_params=initial_params,
            fallback_flags=fallback_flags,
        )
        if workspace is not None and workspace_role == "base" and workspace_key is not None:
            workspace.setdefault("base_origins", {})[workspace_key] = np.asarray(origins, dtype=float).copy()
        if workspace is not None:
            workspace.setdefault("diagnostics", []).append(
                {
                    "role": workspace_role,
                    "candidate_id": aiming.get("_candidate_id"),
                    "key": workspace_key,
                    "warm_seeded": initial_params is not None,
                    "origins": np.asarray(origins, dtype=float).copy(),
                    "ok": np.asarray(ok, dtype=bool).copy(),
                    "iterations": np.asarray(iterations, dtype=int).copy(),
                    "cold_fallback": np.asarray(fallback_flags, dtype=bool).copy(),
                    "targets": np.asarray(targets, dtype=float).copy(),
                }
            )
        return origins, ok, iterations, {
            "strategy": "exact",
            "cache_hit": False,
            "affine_refined_count": 0,
            "affine_seed_count": 0,
            "exact_solved_count": targets.shape[0],
            "request_local_warm_start": initial_params is not None,
        }

    cache_key = _aiming_cache_key(
        compiled,
        configuration,
        field,
        wavelength_nm,
        stop_outer_mm,
        stop_inner_mm,
        launch_x,
        targets,
        tolerance_mm,
        max_iterations,
    )
    cached = _AIMING_AFFINE_CACHE.get(cache_key)
    if cached is not None:
        origins = [origin.copy() for origin in np.asarray(cached["origins"], dtype=float)]
        ok = np.asarray(cached["ok"], dtype=bool).tolist()
        return origins, ok, [0] * len(origins), {
            "strategy": "affine",
            "cache_hit": True,
            "affine_refined_count": 0,
            "affine_seed_count": 0,
            "exact_solved_count": 0,
            "cache_payload": "exact_origin_bundle",
        }

    origins, ok, iterations = _exact_aim_origins(
        compiled,
        launch_x,
        direction,
        wavelength_nm,
        targets,
        centers_mm,
        rotations,
        tolerance_mm=tolerance_mm,
        max_iterations=max_iterations,
        configuration=configuration,
    )
    _AIMING_AFFINE_CACHE[cache_key] = {
        "origins": np.array(origins, dtype=float),
        "ok": np.array(ok, dtype=bool),
    }
    return origins, ok, iterations, {
        "strategy": "affine",
        "cache_hit": False,
        "affine_refined_count": 0,
        "affine_seed_count": 0,
        "exact_solved_count": len(origins),
        "cache_payload": "exact_origin_bundle",
    }


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
    include_layout_baseline_rays = bool(options.get("include_layout_baseline_rays", False))
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
    if aiming_mode not in {"off", "paraxial", "full"}:
        raise StructuredOpticsError(
            "optics_value_error",
            "Unknown ray aiming mode.",
            params={"ray_aiming_mode": aiming_mode, "supported_modes": ["off", "paraxial", "full"]},
        )
    tolerance_mm = float(aiming.get("tolerance_mm", 1.0e-6))
    max_iterations = int(aiming.get("max_iterations", 20))
    store_path = bool(options.get("store_path", False))

    seed = int(sampling["seed"]) if "seed" in sampling else None
    samples, sample_weights = _unit_disk_samples_with_weights(samples_per_field, distribution, seed)
    targets = _target_points_for_stop_with_layout(compiled, samples, centers_mm, rotations, configuration)
    first_x = centers_mm[0, 0]
    stop_idx, stop_outer, stop_inner = _aperture_radius(compiled, configuration)
    launch_x = min(first_x, targets[0, 0]) - max(100.0, 10.0 * stop_outer)

    origins: list[np.ndarray] = []
    directions: list[np.ndarray] = []
    ray_wavelengths: list[float] = []
    ray_weights: list[float] = []
    field_ids: list[str] = []
    aiming_ok: list[bool] = []
    aiming_iterations: list[int] = []
    aiming_cache_hits = 0
    aiming_cache_misses = 0
    affine_refined_count = 0
    affine_seed_count = 0
    aiming_exact_solved_count = 0
    aiming_strategy = aiming.get("strategy", "affine") if aiming_mode == "full" else aiming_mode
    aiming_solution_kind = "exact_bundle_cache" if aiming_mode == "full" and aiming_strategy != "exact" else aiming_strategy

    for field in fields:
        if field.get("type", "angular") != "angular":
            raise NotImplementedError("only angular fields are implemented in this v2.1 build")
        direction = field_direction(float(field.get("theta_y_deg", 0.0)), float(field.get("theta_z_deg", 0.0)))
        for wavelength in wavelengths:
            if aiming_mode == "full":
                field_origins, field_ok, field_iterations, field_meta = _aim_origins_for_field_wavelength(
                    compiled,
                    field,
                    direction,
                    float(wavelength),
                    targets,
                    launch_x,
                    centers_mm,
                    rotations,
                    aiming,
                    stop_outer_mm=stop_outer,
                    stop_inner_mm=stop_inner,
                    tolerance_mm=tolerance_mm,
                    max_iterations=max_iterations,
                    configuration=configuration,
                    workspace_key=(
                        str(distribution),
                        int(samples_per_field),
                        str(field.get("id", "field")),
                        round(float(field.get("theta_y_deg", 0.0)), 12),
                        round(float(field.get("theta_z_deg", 0.0)), 12),
                        round(float(wavelength), 9),
                    ),
                )
                if field_meta.get("cache_hit"):
                    aiming_cache_hits += 1
                elif field_meta.get("strategy") == "affine":
                    aiming_cache_misses += 1
                affine_refined_count += int(field_meta.get("affine_refined_count", 0))
                affine_seed_count += int(field_meta.get("affine_seed_count", 0))
                aiming_exact_solved_count += int(field_meta.get("exact_solved_count", 0))
            else:
                field_origins = [_paraxial_launch_origin(launch_x, direction, target) for target in targets]
                field_ok = [True] * len(field_origins)
                field_iterations = [0] * len(field_origins)

            for origin, ok, iterations, sample_weight in zip(field_origins, field_ok, field_iterations, sample_weights):
                origins.append(origin)
                directions.append(direction)
                ray_wavelengths.append(float(wavelength))
                ray_weights.append(float(sample_weight))
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
    result.weights = np.asarray(ray_weights, dtype=float)
    result.metadata.update(
        {
            "ray_aiming_mode": aiming_mode,
            "ray_aiming_strategy": aiming_strategy,
            "aiming_solution_kind": aiming_solution_kind,
            "aiming_failed_count": int(np.sum(~aiming_ok_array)),
            "aiming_iterations_max": int(max(aiming_iterations) if aiming_iterations else 0),
            "aiming_iterations_mean": float(np.mean(aiming_iterations)) if aiming_iterations else 0.0,
            "aiming_cache_hits": int(aiming_cache_hits),
            "aiming_cache_misses": int(aiming_cache_misses),
            "affine_refined_count": int(affine_refined_count),
            "affine_seed_count": int(affine_seed_count),
            "aiming_exact_solved_count": int(aiming_exact_solved_count),
            "samples_per_field": samples_per_field,
            "sampling_seed": seed,
            "pupil_weights": sample_weights.tolist(),
        }
    )
    nominal_stop_radius = None
    if stop_idx is not None:
        stop_surface = compiled.surfaces[stop_idx]
        nominal_stop_radius = stop_surface.semi_diameter_mm
        if stop_surface.aperture is not None:
            nominal_stop_radius = (
                stop_surface.aperture.outer_semi_diameter_mm
                or stop_surface.aperture.semi_diameter_mm
                or nominal_stop_radius
            )
    runtime_iris = _runtime_iris_radius(configuration)
    if runtime_iris is not None and nominal_stop_radius is not None and runtime_iris > nominal_stop_radius:
        result.metadata.setdefault("warnings", []).append(
            {
                "severity": "warning",
                "code": "iris_exceeds_clear_aperture",
                "params": {"iris_radius_mm": runtime_iris, "nominal_clear_radius_mm": float(nominal_stop_radius)},
                "message_en": "Iris radius exceeds the nominal stop clear aperture; downstream surfaces may vignette rays.",
            }
        )
    if include_analysis_metadata:
        from .paraxial import analyze_paraxial

        paraxial = analyze_paraxial(compiled, configuration, wavelengths[0])
        result.metadata.update(
            {
                "pupil_distribution": distribution,
                "wavelengths_nm": [float(wavelength) for wavelength in wavelengths],
                "paraxial": {
                    "paraxial_image_position_mm": paraxial.paraxial_image_position_mm,
                    "principal_plane_positions_mm": list(paraxial.principal_plane_positions_mm),
                },
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
    t_baseline = t_trace
    if store_path and include_layout_baseline_rays:
        result.metadata["layout_baseline_rays"] = _layout_baseline_rays(
            compiled,
            fields,
            [float(wavelength) for wavelength in wavelengths],
            launch_x,
            centers_mm,
            rotations,
            tolerance_mm=tolerance_mm,
            max_iterations=max(max_iterations, 20),
            configuration=configuration,
        )
        t_baseline = time.perf_counter()
    if profiling:
        aiming_ms = (t_generation - t_layout) * 1000.0
        trace_ms = (t_trace - t_generation) * 1000.0
        result.metadata["profiling"] = {
            "validation_ms": (t_validation - t0) * 1000.0,
            "compile_ms": 0.0,
            "compile_cache_hit": None,
            "layout_ms": (t_layout - t_validation) * 1000.0,
            "aiming_ms": aiming_ms,
            "ray_generation_and_aiming_ms": aiming_ms,
            "trace_ms": trace_ms,
            "layout_baseline_rays_ms": (t_baseline - t_trace) * 1000.0,
            "analysis_postprocessing_ms": 0.0,
            "total_ms": (t_baseline - t0) * 1000.0,
            "total_rays": int(result.status.size),
            "cache_hit": None,
            "cache_hits": int(aiming_cache_hits),
            "cache_misses": int(aiming_cache_misses),
            "aiming_failed_count": int(np.sum(~aiming_ok_array)),
            "aiming_iterations_max": int(max(aiming_iterations) if aiming_iterations else 0),
            "aiming_iterations_mean": float(np.mean(aiming_iterations)) if aiming_iterations else 0.0,
            "aiming_cache_hits": int(aiming_cache_hits),
            "aiming_cache_misses": int(aiming_cache_misses),
            "affine_refined_count": int(affine_refined_count),
            "affine_seed_count": int(affine_seed_count),
            "aiming_exact_solved_count": int(aiming_exact_solved_count),
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
