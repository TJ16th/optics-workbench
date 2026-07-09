from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .configuration import runtime_layout
from .paraxial import analyze_paraxial
from .system import CompiledSystem
from .tracing import TraceResult, _unit_disk_samples, trace_forward


@dataclass(frozen=True)
class RayFanPoint:
    field_id: str
    wavelength_nm: float
    pupil_y: float
    pupil_z: float
    sensor_y_mm: float | None
    sensor_z_mm: float | None
    transverse_error_y_mm: float | None
    transverse_error_z_mm: float | None
    status: str


@dataclass(frozen=True)
class RayFanResult:
    points: list[RayFanPoint]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LongitudinalAberrationPoint:
    field_id: str
    wavelength_nm: float
    pupil_y: float
    pupil_z: float
    focus_x_y_mm: float | None
    focus_x_z_mm: float | None
    longitudinal_error_y_mm: float | None
    longitudinal_error_z_mm: float | None
    status: str


@dataclass(frozen=True)
class LongitudinalAberrationResult:
    points: list[LongitudinalAberrationPoint]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DistortionRow:
    field_id: str
    theta_y_deg: float
    theta_z_deg: float
    actual_y_mm: float | None
    actual_z_mm: float | None
    ideal_y_mm: float | None
    ideal_z_mm: float | None
    delta_y_mm: float | None
    delta_z_mm: float | None
    distortion_percent: float | None


@dataclass(frozen=True)
class DistortionResult:
    rows: list[DistortionRow]
    metadata: dict[str, Any]


def _ideal_image_height(compiled: CompiledSystem, field: dict[str, Any], configuration: dict[str, Any] | None = None) -> tuple[float | None, float | None]:
    paraxial = analyze_paraxial(compiled, configuration)
    if paraxial.effective_focal_length_mm is None:
        return None, None
    efl = float(paraxial.effective_focal_length_mm)
    return (
        efl * float(np.tan(np.deg2rad(float(field.get("theta_y_deg", 0.0))))),
        efl * float(np.tan(np.deg2rad(float(field.get("theta_z_deg", 0.0))))),
    )


def _samples_for_trace(sampling: dict[str, Any] | None) -> tuple[np.ndarray, str]:
    sampling = sampling or {}
    count = int(sampling.get("samples_per_field", 21))
    distribution = str(sampling.get("pupil_distribution", "fan_y"))
    return _unit_disk_samples(count, distribution), distribution


def analyze_ray_fan(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None = None,
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> RayFanResult:
    sampling = dict(sampling or {"samples_per_field": 21, "pupil_distribution": "fan_y", "ray_aiming": {"mode": "paraxial"}})
    wavelengths = [float(w) for w in (wavelengths or [compiled.system.wavelengths_nm.primary])]
    fields = fields or [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    options = dict(options or {})
    trace = trace_forward(compiled, fields, sampling, wavelengths, options)
    samples, distribution = _samples_for_trace(sampling)
    points: list[RayFanPoint] = []
    idx = 0
    for field in fields:
        ideal_y, ideal_z = _ideal_image_height(compiled, field, options.get("configuration"))
        for wavelength in wavelengths:
            for sample in samples:
                sy = None if not np.isfinite(trace.sensor_y_mm[idx]) else float(trace.sensor_y_mm[idx])
                sz = None if not np.isfinite(trace.sensor_z_mm[idx]) else float(trace.sensor_z_mm[idx])
                points.append(
                    RayFanPoint(
                        field_id=str(field.get("id", "field")),
                        wavelength_nm=float(wavelength),
                        pupil_y=float(sample[0]),
                        pupil_z=float(sample[1]),
                        sensor_y_mm=sy,
                        sensor_z_mm=sz,
                        transverse_error_y_mm=None if sy is None or ideal_y is None else sy - ideal_y,
                        transverse_error_z_mm=None if sz is None or ideal_z is None else sz - ideal_z,
                        status=str(trace.status[idx]),
                    )
                )
                idx += 1
    return RayFanResult(points=points, metadata={"pupil_distribution": distribution, "samples_per_field": int(sampling.get("samples_per_field", 21))})


def analyze_longitudinal_aberration(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None = None,
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> LongitudinalAberrationResult:
    sampling = dict(sampling or {"samples_per_field": 21, "pupil_distribution": "fan_y", "ray_aiming": {"mode": "paraxial"}})
    wavelengths = [float(w) for w in (wavelengths or [compiled.system.wavelengths_nm.primary])]
    fields = fields or [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    options = {**dict(options or {}), "store_path": True}
    trace = trace_forward(compiled, fields, sampling, wavelengths, options)
    samples, distribution = _samples_for_trace(sampling)
    layout = runtime_layout(compiled, options.get("configuration"))
    paraxial = analyze_paraxial(compiled, options.get("configuration"))
    reference_x = paraxial.paraxial_image_position_mm
    points: list[LongitudinalAberrationPoint] = []
    idx = 0
    for field in fields:
        for wavelength in wavelengths:
            for sample in samples:
                focus_y = None
                focus_z = None
                if trace.paths and trace.paths[idx] and str(trace.status[idx]) == "alive":
                    sensor_point = np.array(trace.paths[idx][-1]["point_mm"], dtype=float)
                    direction = trace.directions[idx]
                    if abs(direction[1]) > 1.0e-12:
                        focus_y = float(sensor_point[0] - sensor_point[1] * direction[0] / direction[1])
                    if abs(direction[2]) > 1.0e-12:
                        focus_z = float(sensor_point[0] - sensor_point[2] * direction[0] / direction[2])
                    if focus_y is None and abs(sensor_point[1]) <= 1.0e-12:
                        focus_y = float(layout.centers_mm[compiled.sensor_index, 0]) if compiled.sensor_index is not None else None
                    if focus_z is None and abs(sensor_point[2]) <= 1.0e-12:
                        focus_z = float(layout.centers_mm[compiled.sensor_index, 0]) if compiled.sensor_index is not None else None
                points.append(
                    LongitudinalAberrationPoint(
                        field_id=str(field.get("id", "field")),
                        wavelength_nm=float(wavelength),
                        pupil_y=float(sample[0]),
                        pupil_z=float(sample[1]),
                        focus_x_y_mm=focus_y,
                        focus_x_z_mm=focus_z,
                        longitudinal_error_y_mm=None if focus_y is None or reference_x is None else focus_y - float(reference_x),
                        longitudinal_error_z_mm=None if focus_z is None or reference_x is None else focus_z - float(reference_x),
                        status=str(trace.status[idx]),
                    )
                )
                idx += 1
    return LongitudinalAberrationResult(points=points, metadata={"pupil_distribution": distribution, "reference_x_mm": reference_x})


def analyze_distortion(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> DistortionResult:
    fields = fields or [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    wavelength = float((wavelengths or [compiled.system.wavelengths_nm.primary])[0])
    options = dict(options or {})
    sampling = {"samples_per_field": 1, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}}
    trace = trace_forward(compiled, fields, sampling, [wavelength], options)
    rows: list[DistortionRow] = []
    for idx, field in enumerate(fields):
        actual_y = None if not np.isfinite(trace.sensor_y_mm[idx]) else float(trace.sensor_y_mm[idx])
        actual_z = None if not np.isfinite(trace.sensor_z_mm[idx]) else float(trace.sensor_z_mm[idx])
        ideal_y, ideal_z = _ideal_image_height(compiled, field, options.get("configuration"))
        distortion = None
        delta_y = None if actual_y is None or ideal_y is None else actual_y - ideal_y
        delta_z = None if actual_z is None or ideal_z is None else actual_z - ideal_z
        if actual_y is not None and actual_z is not None and ideal_y is not None and ideal_z is not None:
            h_actual = float(np.hypot(actual_y, actual_z))
            h_ideal = float(np.hypot(ideal_y, ideal_z))
            distortion = None if h_ideal <= 1.0e-12 else 100.0 * (h_actual - h_ideal) / h_ideal
        rows.append(
            DistortionRow(
                field_id=str(field.get("id", "field")),
                theta_y_deg=float(field.get("theta_y_deg", 0.0)),
                theta_z_deg=float(field.get("theta_z_deg", 0.0)),
                actual_y_mm=actual_y,
                actual_z_mm=actual_z,
                ideal_y_mm=ideal_y,
                ideal_z_mm=ideal_z,
                delta_y_mm=delta_y,
                delta_z_mm=delta_z,
                distortion_percent=distortion,
            )
        )
    return DistortionResult(rows=rows, metadata={"reference": "paraxial_efl", "wavelength_nm": wavelength})
