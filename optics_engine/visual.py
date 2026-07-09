from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .system import CompiledSystem
from .tracing import TraceResult, trace_forward


@dataclass(frozen=True)
class AfocalEvaluationResult:
    field_id: str
    arrived_count: int
    centroid_theta_y_deg: float | None
    centroid_theta_z_deg: float | None
    angular_rms_deg: float | None
    residual_divergence_diopter: float | None


@dataclass(frozen=True)
class ExitPupilResult:
    angular_magnification: float | None
    exit_pupil_diameter_mm: float | None
    eye_relief_mm: float | None


@dataclass(frozen=True)
class EyeBoxSample:
    offset_y_mm: float
    offset_z_mm: float
    throughput: float


@dataclass(frozen=True)
class EyeBoxResult:
    samples: list[EyeBoxSample]


@dataclass(frozen=True)
class AngularMTFPoint:
    frequency_cycles_per_degree: float
    mtf: float


@dataclass(frozen=True)
class AngularMTFResult:
    points: list[AngularMTFPoint]


@dataclass(frozen=True)
class BinocularAlignmentResult:
    delta_theta_y_deg: float | None
    delta_theta_z_deg: float | None
    angular_separation_deg: float | None


@dataclass(frozen=True)
class TelescopeResult:
    magnification: float | None
    exit_pupil_diameter_mm: float | None
    eye_relief_mm: float | None
    true_field_deg: float | None
    apparent_field_deg: float | None


def _thin_lenses(compiled: CompiledSystem):
    return [surface for surface in compiled.surfaces if surface.kind == "thin_lens" and surface.focal_length_mm is not None]


def angular_magnification(compiled: CompiledSystem) -> float | None:
    lenses = _thin_lenses(compiled)
    if len(lenses) < 2:
        return None
    return -float(lenses[0].focal_length_mm) / float(lenses[-1].focal_length_mm)


def _aperture_diameter(compiled: CompiledSystem) -> float | None:
    if compiled.aperture_stop_index is None:
        return None
    stop = compiled.surfaces[compiled.aperture_stop_index]
    radius = stop.semi_diameter_mm
    if stop.aperture is not None:
        radius = stop.aperture.semi_diameter_mm or stop.aperture.outer_semi_diameter_mm or radius
    return None if radius is None else 2.0 * float(radius)


def _eye_relief(compiled: CompiledSystem) -> float | None:
    eye_idx = next((idx for idx, surface in enumerate(compiled.surfaces) if surface.kind == "eye_reference"), None)
    if eye_idx is None:
        return None
    powered = [idx for idx, surface in enumerate(compiled.surfaces) if surface.kind in {"thin_lens", "refractive", "mirror"}]
    if not powered:
        return None
    return float(compiled.surface_positions_mm[eye_idx] - compiled.surface_positions_mm[powered[-1]])


def analyze_exit_pupil(compiled: CompiledSystem) -> ExitPupilResult:
    mag = angular_magnification(compiled)
    aperture = _aperture_diameter(compiled)
    exit_diameter = None if mag in (None, 0.0) or aperture is None else aperture / abs(mag)
    return ExitPupilResult(mag, exit_diameter, _eye_relief(compiled))


def analyze_afocal(
    compiled: CompiledSystem,
    field: dict[str, Any] | None = None,
    sampling: dict[str, Any] | None = None,
    configuration: dict[str, Any] | None = None,
) -> AfocalEvaluationResult:
    field = field or {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}
    trace = trace_forward(
        compiled,
        [field],
        sampling or {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [compiled.system.wavelengths_nm.primary],
        {"configuration": configuration or {}},
    )
    return afocal_from_trace(trace, str(field.get("id", "field")))


def afocal_from_trace(trace: TraceResult, field_id: str = "field") -> AfocalEvaluationResult:
    mask = trace.eye_arrived_mask
    if not np.any(mask):
        return AfocalEvaluationResult(field_id, 0, None, None, None, None)
    theta_y = trace.eye_theta_y_deg[mask]
    theta_z = trace.eye_theta_z_deg[mask]
    cy = float(np.mean(theta_y))
    cz = float(np.mean(theta_z))
    rms = float(np.sqrt(np.mean((theta_y - cy) ** 2 + (theta_z - cz) ** 2)))
    return AfocalEvaluationResult(
        field_id=field_id,
        arrived_count=int(np.sum(mask)),
        centroid_theta_y_deg=cy,
        centroid_theta_z_deg=cz,
        angular_rms_deg=rms,
        residual_divergence_diopter=float(np.tan(np.deg2rad(rms)) * 1000.0),
    )


def analyze_eye_box(
    compiled: CompiledSystem,
    offsets_yz_mm: list[tuple[float, float]],
    field: dict[str, Any] | None = None,
    sampling: dict[str, Any] | None = None,
    eye_group_id: str = "EYE_G",
) -> EyeBoxResult:
    samples: list[EyeBoxSample] = []
    for offset_y, offset_z in offsets_yz_mm:
        config = {"group_positions": {eye_group_id: {"shift_y_mm": offset_y, "shift_z_mm": offset_z}}}
        trace = trace_forward(
            compiled,
            [field or {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
            sampling or {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
            [compiled.system.wavelengths_nm.primary],
            {"configuration": config},
        )
        throughput = float(np.mean(trace.eye_arrived_mask)) if trace.status.size else 0.0
        samples.append(EyeBoxSample(float(offset_y), float(offset_z), throughput))
    return EyeBoxResult(samples)


def analyze_angular_mtf(trace: TraceResult, frequencies_cycles_per_degree: list[float]) -> AngularMTFResult:
    mask = trace.eye_arrived_mask
    if not np.any(mask):
        return AngularMTFResult([AngularMTFPoint(float(freq), 0.0) for freq in frequencies_cycles_per_degree])
    theta = trace.eye_theta_z_deg[mask] - np.mean(trace.eye_theta_z_deg[mask])
    points: list[AngularMTFPoint] = []
    for freq in frequencies_cycles_per_degree:
        value = float(abs(np.mean(np.exp(-2j * np.pi * freq * theta))))
        points.append(AngularMTFPoint(float(freq), value))
    return AngularMTFResult(points)


def analyze_binocular_alignment(left: AfocalEvaluationResult, right: AfocalEvaluationResult) -> BinocularAlignmentResult:
    if left.centroid_theta_y_deg is None or right.centroid_theta_y_deg is None:
        return BinocularAlignmentResult(None, None, None)
    dy = right.centroid_theta_y_deg - left.centroid_theta_y_deg
    dz = right.centroid_theta_z_deg - left.centroid_theta_z_deg
    return BinocularAlignmentResult(dy, dz, float(np.hypot(dy, dz)))


def analyze_telescope(compiled: CompiledSystem, true_field_deg: float | None = None) -> TelescopeResult:
    exit_pupil = analyze_exit_pupil(compiled)
    mag = exit_pupil.angular_magnification
    apparent = None if true_field_deg is None or mag is None else abs(mag) * true_field_deg
    return TelescopeResult(
        magnification=mag,
        exit_pupil_diameter_mm=exit_pupil.exit_pupil_diameter_mm,
        eye_relief_mm=exit_pupil.eye_relief_mm,
        true_field_deg=true_field_deg,
        apparent_field_deg=apparent,
    )
