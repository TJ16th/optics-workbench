from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .configuration import runtime_layout
from .image_plane import _project_trace_to_shifted_plane
from .paraxial import analyze_paraxial
from .system import CompiledSystem
from .tracing import TraceResult, trace_forward


@dataclass(frozen=True)
class ThroughFocusMTFPoint:
    field_id: str
    theta_y_deg: float
    theta_z_deg: float
    frequency_lp_per_mm: float
    defocus_mm: float
    mtf_meridional: float
    mtf_sagittal: float


@dataclass(frozen=True)
class ThroughFocusMTFResult:
    points: list[ThroughFocusMTFPoint]
    metadata: dict[str, Any]


def _field_trace(trace: TraceResult, field_id: str) -> TraceResult:
    mask = np.asarray([value == field_id for value in trace.field_ids], dtype=bool)
    indices = np.flatnonzero(mask)
    return TraceResult(
        origins=trace.origins[mask],
        directions=trace.directions[mask],
        wavelengths_nm=trace.wavelengths_nm[mask],
        field_ids=[trace.field_ids[index] for index in indices],
        status=trace.status[mask],
        sensor_y_mm=trace.sensor_y_mm[mask],
        sensor_z_mm=trace.sensor_z_mm[mask],
        weights=None if trace.weights is None else trace.weights[mask],
        paths=[],
        metadata=dict(trace.metadata),
    )


def _meridional_sagittal_mtf(
    trace: TraceResult,
    theta_y_deg: float,
    theta_z_deg: float,
    frequencies_lp_per_mm: list[float],
) -> list[tuple[float, float]]:
    mask = trace.arrived_mask & np.isfinite(trace.sensor_y_mm) & np.isfinite(trace.sensor_z_mm)
    if not np.any(mask):
        return [(0.0, 0.0) for _ in frequencies_lp_per_mm]

    y = np.asarray(trace.sensor_y_mm[mask], dtype=float)
    z = np.asarray(trace.sensor_z_mm[mask], dtype=float)
    if trace.weights is None:
        weights = np.ones(y.size, dtype=float)
    else:
        weights = np.asarray(trace.weights[mask], dtype=float)
    total_weight = float(np.sum(weights))
    weights = weights / total_weight if total_weight > 0.0 else np.full(y.size, 1.0 / y.size)

    field_norm = float(np.hypot(theta_y_deg, theta_z_deg))
    if field_norm <= 1.0e-15:
        meridional_y, meridional_z = 1.0, 0.0
    else:
        meridional_y = theta_y_deg / field_norm
        meridional_z = theta_z_deg / field_norm
    sagittal_y, sagittal_z = -meridional_z, meridional_y

    meridional = y * meridional_y + z * meridional_z
    sagittal = y * sagittal_y + z * sagittal_z
    meridional -= float(np.sum(weights * meridional))
    sagittal -= float(np.sum(weights * sagittal))

    values: list[tuple[float, float]] = []
    for frequency in frequencies_lp_per_mm:
        mtf_m = abs(np.sum(weights * np.exp(-2j * np.pi * frequency * meridional)))
        mtf_s = abs(np.sum(weights * np.exp(-2j * np.pi * frequency * sagittal)))
        values.append((float(mtf_m), float(mtf_s)))
    return values


def analyze_through_focus_mtf(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None = None,
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
    *,
    frequencies_lp_per_mm: list[float] | None = None,
    defocus_range_mm: float | None = None,
    defocus_points: int = 21,
    depth_of_focus_multiplier: float = 4.0,
) -> ThroughFocusMTFResult:
    if compiled.system.system_type != "focal" or compiled.sensor_index is None:
        raise ValueError("through-focus MTF requires a focal system with a sensor surface")
    frequencies = [float(value) for value in (frequencies_lp_per_mm or [10.0, 30.0])]
    if not frequencies or any(value < 0.0 or not np.isfinite(value) for value in frequencies):
        raise ValueError("frequencies_lp_per_mm must contain finite non-negative values")
    if not 3 <= int(defocus_points) <= 201:
        raise ValueError("defocus_points must be between 3 and 201")
    if depth_of_focus_multiplier <= 0.0 or not np.isfinite(depth_of_focus_multiplier):
        raise ValueError("depth_of_focus_multiplier must be finite and positive")

    evaluated_fields = fields or [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    evaluated_wavelengths = [float(value) for value in (wavelengths or [compiled.system.wavelengths_nm.primary])]
    configuration = dict((options or {}).get("configuration") or (options or {}).get("config") or {})
    paraxial = analyze_paraxial(compiled, configuration, compiled.system.wavelengths_nm.primary)
    if paraxial.f_number is None or paraxial.f_number <= 0.0:
        raise ValueError("through-focus MTF requires a finite positive paraxial F-number")

    primary_wavelength_mm = float(compiled.system.wavelengths_nm.primary) * 1.0e-6
    diffraction_depth_of_focus_mm = 2.0 * primary_wavelength_mm * paraxial.f_number**2
    active_sensor_x_mm = float(runtime_layout(compiled, configuration).centers_mm[compiled.sensor_index, 0])
    paraxial_focus_offset_mm = (
        0.0
        if paraxial.paraxial_image_position_mm is None
        else float(paraxial.paraxial_image_position_mm) - active_sensor_x_mm
    )
    range_source = "request"
    if defocus_range_mm is None:
        focus_margin_mm = diffraction_depth_of_focus_mm * float(depth_of_focus_multiplier)
        half_range_mm = abs(paraxial_focus_offset_mm) + focus_margin_mm
        range_source = "paraxial_focus_offset_plus_diffraction_depth_of_focus"
    else:
        half_range_mm = float(defocus_range_mm)
    if half_range_mm <= 0.0 or not np.isfinite(half_range_mm):
        raise ValueError("defocus_range_mm must be finite and positive")

    sampling_plain = dict(sampling or {"samples_per_field": 4096, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}})
    trace = trace_forward(
        compiled,
        evaluated_fields,
        sampling_plain,
        evaluated_wavelengths,
        {**(options or {}), "configuration": configuration, "store_path": False, "include_analysis_metadata": False},
    )
    defocus_values = np.linspace(-half_range_mm, half_range_mm, int(defocus_points))
    points: list[ThroughFocusMTFPoint] = []
    for field in evaluated_fields:
        field_id = str(field.get("id", "field"))
        theta_y_deg = float(field.get("theta_y_deg", 0.0))
        theta_z_deg = float(field.get("theta_z_deg", 0.0))
        base_field_trace = _field_trace(trace, field_id)
        for defocus_mm in defocus_values:
            projected = _project_trace_to_shifted_plane(base_field_trace, compiled, configuration, float(defocus_mm))
            mtf_values = _meridional_sagittal_mtf(projected, theta_y_deg, theta_z_deg, frequencies)
            for frequency, (mtf_m, mtf_s) in zip(frequencies, mtf_values):
                points.append(
                    ThroughFocusMTFPoint(
                        field_id=field_id,
                        theta_y_deg=theta_y_deg,
                        theta_z_deg=theta_z_deg,
                        frequency_lp_per_mm=frequency,
                        defocus_mm=float(defocus_mm),
                        mtf_meridional=mtf_m,
                        mtf_sagittal=mtf_s,
                    )
                )

    return ThroughFocusMTFResult(
        points=points,
        metadata={
            "method": "geometric_empirical_characteristic_function",
            "projection_method": "single_trace_final_ray_projection",
            "diffraction_included": False,
            "frequency_units": "lp/mm",
            "defocus_units": "mm",
            "defocus_reference": "active_evaluation_plane",
            "defocus_range_mm": half_range_mm,
            "defocus_points": int(defocus_points),
            "range_source": range_source,
            "depth_of_focus_formula": "2 * primary_wavelength_mm * f_number^2",
            "depth_of_focus_multiplier": float(depth_of_focus_multiplier),
            "diffraction_depth_of_focus_mm": diffraction_depth_of_focus_mm,
            "paraxial_focus_offset_mm": paraxial_focus_offset_mm,
            "primary_wavelength_nm": float(compiled.system.wavelengths_nm.primary),
            "f_number": float(paraxial.f_number),
            "field_count": len(evaluated_fields),
            "frequency_count": len(frequencies),
            "wavelength_count": len(evaluated_wavelengths),
            "traced_ray_count": int(trace.status.size),
            "arrived_count": int(np.sum(trace.arrived_mask)),
            "samples_per_field": int(sampling_plain.get("samples_per_field", 4096)),
            "pupil_distribution": str(sampling_plain.get("pupil_distribution", "grid")),
            "ray_aiming_mode": str((sampling_plain.get("ray_aiming") or {}).get("mode", "paraxial")),
        },
    )
