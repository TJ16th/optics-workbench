from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .core import field_direction
from .system import CompiledSystem
from .tracing import TraceResult, trace_forward


DEFAULT_RELATIVE_ILLUMINATION_SAMPLING: dict[str, Any] = {
    "samples_per_field": 1000,
    "pupil_distribution": "grid",
    "ray_aiming": {"mode": "paraxial"},
}


@dataclass(frozen=True)
class EncircledEnergyPoint:
    radius_mm: float
    energy_fraction: float


@dataclass(frozen=True)
class GeometricPSFResult:
    grid: list[list[float]]
    y_edges_mm: list[float]
    z_edges_mm: list[float]
    centroid_y_mm: float | None
    centroid_z_mm: float | None
    total_energy: float
    encircled_energy: list[EncircledEnergyPoint]


@dataclass(frozen=True)
class MTFPoint:
    frequency_lp_per_mm: float
    mtf_y: float
    mtf_z: float
    mtf_radial: float


@dataclass(frozen=True)
class GeometricMTFResult:
    points: list[MTFPoint]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelativeIlluminationRow:
    field_id: str
    theta_y_deg: float
    theta_z_deg: float
    throughput: float
    cos4_factor: float
    relative_illumination: float


@dataclass(frozen=True)
class RelativeIlluminationResult:
    rows: list[RelativeIlluminationRow]
    normalization_field_id: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class WhitePSFResult:
    psf: GeometricPSFResult
    wavelength_weights: dict[float, float]


@dataclass(frozen=True)
class WhiteMTFResult:
    mtf: GeometricMTFResult
    wavelength_weights: dict[float, float]
    metadata: dict[str, Any] = field(default_factory=dict)


def _arrived_points(trace_result: TraceResult) -> tuple[np.ndarray, np.ndarray]:
    mask = trace_result.arrived_mask
    return trace_result.sensor_y_mm[mask], trace_result.sensor_z_mm[mask]


def encircled_energy(trace_result: TraceResult, radii_mm: list[float] | None = None) -> list[EncircledEnergyPoint]:
    y, z = _arrived_points(trace_result)
    if y.size == 0:
        return []
    cy = float(np.mean(y))
    cz = float(np.mean(z))
    rr = np.sqrt((y - cy) ** 2 + (z - cz) ** 2)
    if radii_mm is None:
        max_r = float(np.max(rr))
        radii = np.linspace(0.0, max_r, 8).tolist() if max_r > 0.0 else [0.0]
    else:
        radii = radii_mm
    return [EncircledEnergyPoint(float(radius), float(np.mean(rr <= radius))) for radius in radii]


def analyze_geometric_psf(
    trace_result: TraceResult,
    *,
    grid_size: int = 32,
    extent_mm: float | None = None,
    encircled_radii_mm: list[float] | None = None,
) -> GeometricPSFResult:
    y, z = _arrived_points(trace_result)
    if y.size == 0:
        return GeometricPSFResult([], [], [], None, None, 0.0, [])

    cy = float(np.mean(y))
    cz = float(np.mean(z))
    if extent_mm is None:
        half = float(max(np.max(np.abs(y - cy)), np.max(np.abs(z - cz)), 1.0e-9))
        extent_mm = 2.0 * half
    half_extent = extent_mm / 2.0
    y_edges = np.linspace(cy - half_extent, cy + half_extent, grid_size + 1)
    z_edges = np.linspace(cz - half_extent, cz + half_extent, grid_size + 1)
    hist, y_edges, z_edges = np.histogram2d(y, z, bins=[y_edges, z_edges])
    total = float(np.sum(hist))
    if total > 0:
        hist = hist / total
    return GeometricPSFResult(
        grid=hist.tolist(),
        y_edges_mm=y_edges.tolist(),
        z_edges_mm=z_edges.tolist(),
        centroid_y_mm=cy,
        centroid_z_mm=cz,
        total_energy=total,
        encircled_energy=encircled_energy(trace_result, encircled_radii_mm),
    )


def analyze_geometric_mtf(
    trace_result: TraceResult,
    frequencies_lp_per_mm: list[float],
) -> GeometricMTFResult:
    y, z = _arrived_points(trace_result)
    metadata = {
        "method": "empirical_characteristic_function",
        "psf_representation": "geometric_ray_hit_point_cloud",
        "psf_grid_size": None,
        "samples_per_field": trace_result.metadata.get("samples_per_field"),
        "pupil_distribution": trace_result.metadata.get("pupil_distribution"),
        "ray_aiming_mode": trace_result.metadata.get("ray_aiming_mode"),
        "traced_ray_count": int(trace_result.metadata.get("traced_ray_count", trace_result.status.size)),
        "arrived_count": int(trace_result.metadata.get("arrived_count", y.size)),
        "wavelength_count": int(trace_result.metadata.get("wavelength_count", np.unique(trace_result.wavelengths_nm).size)),
        "diffraction_included": False,
    }
    if "combined_weighted_point_count" in trace_result.metadata:
        metadata["combined_weighted_point_count"] = int(trace_result.metadata["combined_weighted_point_count"])
    if y.size == 0:
        return GeometricMTFResult([MTFPoint(float(freq), 0.0, 0.0, 0.0) for freq in frequencies_lp_per_mm], metadata)
    y = y - np.mean(y)
    z = z - np.mean(z)
    radial = np.sqrt(y * y + z * z)
    points: list[MTFPoint] = []
    for freq in frequencies_lp_per_mm:
        phase_y = np.exp(-2j * np.pi * freq * y)
        phase_z = np.exp(-2j * np.pi * freq * z)
        phase_r = np.exp(-2j * np.pi * freq * radial)
        mtf_y = float(abs(np.mean(phase_y)))
        mtf_z = float(abs(np.mean(phase_z)))
        mtf_r = float(abs(np.mean(phase_r)))
        points.append(MTFPoint(float(freq), mtf_y, mtf_z, mtf_r))
    return GeometricMTFResult(points, metadata)


def analyze_relative_illumination(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None = None,
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> RelativeIlluminationResult:
    requested_sampling = sampling or {}
    sampling = {
        **DEFAULT_RELATIVE_ILLUMINATION_SAMPLING,
        **requested_sampling,
        "ray_aiming": {
            **DEFAULT_RELATIVE_ILLUMINATION_SAMPLING["ray_aiming"],
            **requested_sampling.get("ray_aiming", {}),
        },
    }
    rows_raw: list[tuple[dict[str, Any], float, float]] = []
    for field in fields:
        trace = trace_forward(compiled, [field], sampling, wavelengths, options)
        throughput = float(np.mean(trace.arrived_mask)) if trace.status.size else 0.0
        direction = field_direction(float(field.get("theta_y_deg", 0.0)), float(field.get("theta_z_deg", 0.0)))
        cos4 = float(max(direction[0], 0.0) ** 4)
        rows_raw.append((field, throughput, cos4))

    reference = rows_raw[0][1] * rows_raw[0][2] if rows_raw else 0.0
    rows: list[RelativeIlluminationRow] = []
    for field, throughput, cos4 in rows_raw:
        value = 0.0 if reference <= 0.0 else throughput * cos4 / reference
        rows.append(
            RelativeIlluminationRow(
                field_id=str(field.get("id", "field")),
                theta_y_deg=float(field.get("theta_y_deg", 0.0)),
                theta_z_deg=float(field.get("theta_z_deg", 0.0)),
                throughput=throughput,
                cos4_factor=cos4,
                relative_illumination=float(value),
            )
        )
    aiming_mode = str(sampling["ray_aiming"].get("mode", "paraxial"))
    aiming_strategy = str(sampling["ray_aiming"].get("strategy", "affine")) if aiming_mode == "full" else aiming_mode
    return RelativeIlluminationResult(
        rows=rows,
        normalization_field_id=None if not rows else rows[0].field_id,
        metadata={
            "method": "ray_throughput_times_cos4",
            "radiometric_basis": "weighted_pupil_plane",
            "weighting_method": "equal_pupil_samples_times_field_cos4",
            "samples_per_field": int(sampling["samples_per_field"]),
            "pupil_distribution": str(sampling["pupil_distribution"]),
            "ray_aiming_mode": aiming_mode,
            "ray_aiming_strategy": aiming_strategy,
            "wavelength_count": len(wavelengths or [compiled.system.wavelengths_nm.primary]),
        },
    )


def _combine_traces(trace_results: list[TraceResult], weights: list[float]) -> TraceResult:
    if not trace_results:
        raise ValueError("at least one trace result is required")
    y_values: list[np.ndarray] = []
    z_values: list[np.ndarray] = []
    wavelengths: list[np.ndarray] = []
    statuses: list[np.ndarray] = []
    directions: list[np.ndarray] = []
    origins: list[np.ndarray] = []
    field_ids: list[str] = []
    for trace, weight in zip(trace_results, weights):
        repeat = max(1, int(round(weight * 100)))
        y_values.extend([trace.sensor_y_mm] * repeat)
        z_values.extend([trace.sensor_z_mm] * repeat)
        wavelengths.extend([trace.wavelengths_nm] * repeat)
        statuses.extend([trace.status] * repeat)
        directions.extend([trace.directions] * repeat)
        origins.extend([trace.origins] * repeat)
        field_ids.extend(trace.field_ids * repeat)
    metadata = dict(trace_results[0].metadata)
    metadata.update(
        {
            "combined": "white",
            "wavelength_count": len(trace_results),
            "traced_ray_count": int(sum(trace.status.size for trace in trace_results)),
            "arrived_count": int(sum(np.sum(trace.arrived_mask) for trace in trace_results)),
            "combined_weighted_point_count": int(sum(array.size for array in statuses)),
        }
    )
    return TraceResult(
        origins=np.concatenate(origins),
        directions=np.concatenate(directions),
        wavelengths_nm=np.concatenate(wavelengths),
        field_ids=field_ids,
        status=np.concatenate(statuses),
        sensor_y_mm=np.concatenate(y_values),
        sensor_z_mm=np.concatenate(z_values),
        paths=[],
        metadata=metadata,
    )


def analyze_white_psf(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None,
    wavelength_weights: dict[float, float],
    options: dict[str, Any] | None = None,
) -> WhitePSFResult:
    total = sum(wavelength_weights.values()) or 1.0
    normalized = {float(wl): float(weight) / total for wl, weight in wavelength_weights.items()}
    traces = [trace_forward(compiled, fields, sampling, [wl], options) for wl in normalized]
    combined = _combine_traces(traces, list(normalized.values()))
    return WhitePSFResult(analyze_geometric_psf(combined), normalized)


def analyze_white_mtf(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None,
    wavelength_weights: dict[float, float],
    frequencies_lp_per_mm: list[float],
    options: dict[str, Any] | None = None,
) -> WhiteMTFResult:
    total = sum(wavelength_weights.values()) or 1.0
    normalized = {float(wl): float(weight) / total for wl, weight in wavelength_weights.items()}
    traces = [trace_forward(compiled, fields, sampling, [wl], options) for wl in normalized]
    combined = _combine_traces(traces, list(normalized.values()))
    mtf = analyze_geometric_mtf(combined, frequencies_lp_per_mm)
    return WhiteMTFResult(mtf, normalized, dict(mtf.metadata))
