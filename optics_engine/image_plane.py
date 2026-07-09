from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable

import numpy as np

from .analysis import analyze_spot
from .configuration import runtime_layout
from .models import StructuredOpticsError
from .paraxial import analyze_paraxial
from .psf_mtf import analyze_geometric_mtf
from .system import CompiledSystem
from .tracing import TraceResult, trace_forward

_EVALUATION_PLANE_GROUP = "__EVALUATION_PLANE__"


@dataclass(frozen=True)
class EvaluationPlaneResolution:
    compiled: CompiledSystem
    configuration: dict[str, Any]
    metadata: dict[str, Any]
    focus_curve: list[dict[str, float]] = field(default_factory=list)


def _with_sensor_group(compiled: CompiledSystem) -> CompiledSystem:
    if _EVALUATION_PLANE_GROUP in compiled.group_ranges or compiled.sensor_index is None:
        return compiled
    ranges = dict(compiled.group_ranges)
    ranges[_EVALUATION_PLANE_GROUP] = (compiled.sensor_index, compiled.sensor_index)
    return replace(compiled, group_ranges=ranges)


def _sensor_x_mm(compiled: CompiledSystem, configuration: dict[str, Any] | None = None) -> float:
    if compiled.sensor_index is None:
        raise ValueError("image_plane_policy requires a focal system with a sensor surface")
    return float(runtime_layout(compiled, configuration).centers_mm[compiled.sensor_index, 0])


def _with_evaluation_plane_shift(configuration: dict[str, Any] | None, shift_x_mm: float) -> dict[str, Any]:
    config = dict(configuration or {})
    positions = dict(config.get("group_positions", {}))
    existing = dict(positions.get(_EVALUATION_PLANE_GROUP, {}))
    existing["shift_x_mm"] = float(shift_x_mm)
    positions[_EVALUATION_PLANE_GROUP] = existing
    config["group_positions"] = positions
    return config


def _with_group_shift(configuration: dict[str, Any] | None, group_id: str, shift_x_mm: float) -> dict[str, Any]:
    config = dict(configuration or {})
    positions = dict(config.get("group_positions", {}))
    existing = dict(positions.get(group_id, {}))
    existing["shift_x_mm"] = float(shift_x_mm)
    positions[group_id] = existing
    config["group_positions"] = positions
    return config


def _criteria_wavelengths(policy: dict[str, Any], fallback: list[float]) -> list[tuple[float, float]]:
    criteria = policy.get("criteria") if isinstance(policy.get("criteria"), dict) else {}
    items = criteria.get("wavelengths") or []
    if not items:
        return [(float(wavelength), 1.0) for wavelength in fallback]
    rows: list[tuple[float, float]] = []
    for item in items:
        if isinstance(item, dict):
            rows.append((float(item.get("wavelength_nm", item.get("wavelength", fallback[0]))), float(item.get("weight", 1.0))))
        else:
            rows.append((float(item), 1.0))
    return rows


def _criteria_fields(policy: dict[str, Any], fallback: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
    criteria = policy.get("criteria") if isinstance(policy.get("criteria"), dict) else {}
    items = criteria.get("fields") or []
    if not items:
        return [(field, 1.0) for field in fallback]
    by_id = {str(field.get("id", "field")): field for field in fallback}
    rows: list[tuple[dict[str, Any], float]] = []
    for item in items:
        if isinstance(item, dict):
            field_id = str(item.get("field_id", item.get("id", "")))
            field = by_id.get(field_id)
            if field is not None:
                rows.append((field, float(item.get("weight", 1.0))))
        else:
            field = by_id.get(str(item))
            if field is not None:
                rows.append((field, 1.0))
    return rows or [(field, 1.0) for field in fallback]


def _weighted_average(values: list[tuple[float, float]]) -> float:
    total = sum(weight for _, weight in values)
    if total <= 0.0:
        return float(np.mean([value for value, _ in values]))
    return float(sum(value * weight for value, weight in values) / total)


def _trace_at_shift(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any],
    wavelengths: list[float],
    configuration: dict[str, Any],
    shift_x_mm: float,
) -> TraceResult:
    return trace_forward(
        compiled,
        fields,
        sampling,
        wavelengths,
        {"configuration": _with_evaluation_plane_shift(configuration, shift_x_mm), "include_analysis_metadata": False},
    )


def _sub_trace(trace: TraceResult, mask: np.ndarray) -> TraceResult:
    indices = np.where(mask)[0]
    return TraceResult(
        origins=trace.origins[mask],
        directions=trace.directions[mask],
        wavelengths_nm=trace.wavelengths_nm[mask],
        field_ids=[trace.field_ids[idx] for idx in indices],
        status=trace.status[mask],
        sensor_y_mm=trace.sensor_y_mm[mask],
        sensor_z_mm=trace.sensor_z_mm[mask],
        paths=[],
        metadata=dict(trace.metadata),
    )


def _project_trace_to_shifted_plane(
    trace: TraceResult,
    compiled: CompiledSystem,
    configuration: dict[str, Any],
    shift_x_mm: float,
) -> TraceResult:
    if compiled.sensor_index is None:
        return trace
    layout = runtime_layout(compiled, configuration)
    sensor_center = layout.centers_mm[compiled.sensor_index]
    sensor_rotation = layout.rotations[compiled.sensor_index]
    normal = sensor_rotation[0]
    shifted_center = sensor_center + float(shift_x_mm) * normal

    y = np.full_like(trace.sensor_y_mm, np.nan, dtype=float)
    z = np.full_like(trace.sensor_z_mm, np.nan, dtype=float)
    mask = trace.arrived_mask
    if np.any(mask):
        local_sensor_points = np.column_stack(
            [
                np.zeros(int(np.sum(mask)), dtype=float),
                trace.sensor_y_mm[mask],
                trace.sensor_z_mm[mask],
            ]
        )
        global_points = local_sensor_points @ sensor_rotation.T + sensor_center
        dirs = trace.directions[mask]
        denom = dirs @ normal
        valid = np.abs(denom) > 1.0e-12
        projected = np.full_like(global_points, np.nan)
        if np.any(valid):
            t = ((shifted_center - global_points[valid]) @ normal) / denom[valid]
            projected[valid] = global_points[valid] + dirs[valid] * t[:, None]
        local_projected = (projected - shifted_center) @ sensor_rotation
        mask_indices = np.where(mask)[0]
        y[mask_indices[valid]] = local_projected[valid, 1]
        z[mask_indices[valid]] = local_projected[valid, 2]

    return TraceResult(
        origins=trace.origins,
        directions=trace.directions,
        wavelengths_nm=trace.wavelengths_nm,
        field_ids=list(trace.field_ids),
        status=trace.status.copy(),
        sensor_y_mm=y,
        sensor_z_mm=z,
        paths=[],
        metadata=dict(trace.metadata),
    )


def _metric_value_from_trace(
    trace: TraceResult,
    compiled: CompiledSystem,
    fields: list[tuple[dict[str, Any], float]],
    wavelengths: list[tuple[float, float]],
    mode: str,
    frequency_lpmm: float,
    merit_metrics: list[dict[str, Any]] | None = None,
) -> float:
    values: list[tuple[float, float]] = []
    for wavelength, wavelength_weight in wavelengths:
        for field, field_weight in fields:
            mask = np.array(
                [
                    field_id == str(field.get("id", "field")) and np.isclose(trace.wavelengths_nm[idx], wavelength)
                    for idx, field_id in enumerate(trace.field_ids)
                ],
                dtype=bool,
            )
            sub_trace = _sub_trace(trace, mask)
            if mode == "best_focus_mtf":
                mtf = analyze_geometric_mtf(sub_trace, [frequency_lpmm]).points[0].mtf_radial
                value = -float(mtf)
            elif mode == "best_focus_merit":
                spot = analyze_spot(sub_trace)
                rms = float("inf") if spot.rms_radius_mm is None else float(spot.rms_radius_mm)
                mtf = analyze_geometric_mtf(sub_trace, [frequency_lpmm]).points[0].mtf_radial
                metrics = merit_metrics or [
                    {"metric": "rms_spot_radius", "weight": 1.0},
                    {"metric": "geometric_mtf_loss", "weight": 1.0},
                ]
                value = 0.0
                for metric in metrics:
                    name = str(metric.get("metric", metric.get("name", "rms_spot_radius")))
                    weight = float(metric.get("weight", 1.0))
                    if name in {"rms_spot_radius", "spot_rms"}:
                        value += weight * rms
                    elif name in {"geometric_mtf", "mtf"}:
                        value += weight * (1.0 - mtf)
                    elif name in {"geometric_mtf_loss", "mtf_loss"}:
                        value += weight * max(0.0, 1.0 - mtf)
            else:
                spot = analyze_spot(sub_trace)
                value = float("inf") if spot.rms_radius_mm is None else float(spot.rms_radius_mm)
            values.append((value, field_weight * wavelength_weight))
    return _weighted_average(values)


def _metric_value(
    compiled: CompiledSystem,
    fields: list[tuple[dict[str, Any], float]],
    sampling: dict[str, Any],
    wavelengths: list[tuple[float, float]],
    configuration: dict[str, Any],
    shift_x_mm: float,
    mode: str,
    frequency_lpmm: float,
    merit_metrics: list[dict[str, Any]] | None = None,
) -> float:
    plain_fields = [field for field, _ in fields]
    plain_wavelengths = sorted({float(wavelength) for wavelength, _ in wavelengths})
    trace = _trace_at_shift(compiled, plain_fields, sampling, plain_wavelengths, configuration, shift_x_mm)
    return _metric_value_from_trace(trace, compiled, fields, wavelengths, mode, frequency_lpmm, merit_metrics)


def _direct_best_focus_rms_offset(
    base_trace: TraceResult,
    compiled: CompiledSystem,
    configuration: dict[str, Any],
    fields: list[tuple[dict[str, Any], float]],
    wavelengths: list[tuple[float, float]],
    low: float,
    high: float,
) -> float | None:
    weights = np.zeros(base_trace.status.shape, dtype=float)
    for field, field_weight in fields:
        field_id = str(field.get("id", "field"))
        for wavelength, wavelength_weight in wavelengths:
            mask = np.array(
                [
                    ray_field_id == field_id and np.isclose(base_trace.wavelengths_nm[idx], wavelength)
                    for idx, ray_field_id in enumerate(base_trace.field_ids)
                ],
                dtype=bool,
            )
            weights[mask] += float(field_weight) * float(wavelength_weight)
    mask = base_trace.arrived_mask & (weights > 0.0)
    if int(np.sum(mask)) < 2:
        return None

    trace0 = _project_trace_to_shifted_plane(base_trace, compiled, configuration, 0.0)
    trace1 = _project_trace_to_shifted_plane(base_trace, compiled, configuration, 1.0)
    y0 = trace0.sensor_y_mm[mask]
    z0 = trace0.sensor_z_mm[mask]
    dy_ds = trace1.sensor_y_mm[mask] - y0
    dz_ds = trace1.sensor_z_mm[mask] - z0
    w = weights[mask]
    w_sum = float(np.sum(w))
    if w_sum <= 0.0:
        return None

    y0_centered = y0 - float(np.sum(w * y0) / w_sum)
    z0_centered = z0 - float(np.sum(w * z0) / w_sum)
    dy_centered = dy_ds - float(np.sum(w * dy_ds) / w_sum)
    dz_centered = dz_ds - float(np.sum(w * dz_ds) / w_sum)
    numerator = float(np.sum(w * (y0_centered * dy_centered + z0_centered * dz_centered)))
    denominator = float(np.sum(w * (dy_centered * dy_centered + dz_centered * dz_centered)))
    if denominator <= 1.0e-18:
        return None
    return float(np.clip(-numerator / denominator, low, high))


def _golden_section_minimize(objective: Callable[[float], float], low: float, high: float, tolerance: float, max_iter: int = 64) -> tuple[float, float, int, bool]:
    gr = (np.sqrt(5.0) - 1.0) / 2.0
    c = high - gr * (high - low)
    d = low + gr * (high - low)
    fc = objective(c)
    fd = objective(d)
    iterations = 0
    while abs(high - low) > tolerance and iterations < max_iter:
        iterations += 1
        if fc < fd:
            high = d
            d = c
            fd = fc
            c = high - gr * (high - low)
            fc = objective(c)
        else:
            low = c
            c = d
            fc = fd
            d = low + gr * (high - low)
            fd = objective(d)
    x = (low + high) / 2.0
    converged = abs(high - low) <= tolerance
    return float(x), float(objective(x)), iterations, converged


def resolve_image_plane_policy(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None,
    wavelengths: list[float] | None,
    options: dict[str, Any] | None,
    image_plane_policy: dict[str, Any] | None,
) -> EvaluationPlaneResolution:
    options = options or {}
    base_configuration = dict(options.get("configuration") or options.get("config") or {})
    if image_plane_policy is None:
        image_plane_policy = {"mode": "fixed_sensor", "apply_to": "evaluation_plane"}
    if compiled.system.system_type == "afocal":
        raise StructuredOpticsError(
            "image_plane_policy_not_applicable",
            "image_plane_policy is not applicable to afocal systems.",
            params={"system_type": compiled.system.system_type},
        )

    mode = str(image_plane_policy.get("mode", "fixed_sensor"))
    apply_to = str(image_plane_policy.get("apply_to", "evaluation_plane"))
    if apply_to == "sensor_surface":
        raise ValueError("apply_to=sensor_surface is a client-side write-back operation")
    if apply_to not in {"evaluation_plane", "focus_group", "report_only"}:
        raise ValueError(f"unknown image_plane_policy apply_to {apply_to!r}")
    focus_group_id = image_plane_policy.get("focus_group_id")
    if apply_to == "focus_group":
        if not focus_group_id:
            raise ValueError("apply_to=focus_group requires focus_group_id")
        if str(focus_group_id) not in compiled.group_ranges:
            raise ValueError(f"unknown focus_group_id {focus_group_id!r}")

    compiled_with_sensor_group = _with_sensor_group(compiled)
    sensor_x = _sensor_x_mm(compiled_with_sensor_group, base_configuration)
    wavelengths_plain = [float(w) for w in (wavelengths or [compiled.system.wavelengths_nm.primary])]
    sampling_plain = dict(sampling or {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}})
    fields_plain = fields or [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    solved_offset = 0.0
    solved_focus_group_shift = None
    solve_status = "fixed"
    solve_metric: float | None = None
    focus_curve: list[dict[str, float]] = []
    warnings: list[dict[str, Any]] = []

    if mode == "fixed_sensor":
        solved_offset = 0.0
    elif mode == "custom_offset":
        solved_offset = float(image_plane_policy.get("offset_mm", image_plane_policy.get("offset_from_sensor_mm", 0.0)))
        solve_status = "solved"
    elif mode == "paraxial_image":
        paraxial = analyze_paraxial(compiled_with_sensor_group, base_configuration)
        if paraxial.paraxial_image_position_mm is None:
            solve_status = "no_paraxial_image"
        else:
            solved_offset = float(paraxial.paraxial_image_position_mm) - sensor_x
            solve_status = "solved"
    elif mode in {"best_focus_rms", "best_focus_mtf", "best_focus_merit", "sweep"}:
        search = image_plane_policy.get("search") if isinstance(image_plane_policy.get("search"), dict) else {}
        search_range = float(search.get("range_mm", 5.0))
        tolerance = float(search.get("tolerance_mm", 0.001))
        max_iterations = int(search.get("max_iterations", 64))
        initial_offset = 0.0
        if apply_to != "focus_group" and search.get("initial", "paraxial_image") == "paraxial_image":
            paraxial = analyze_paraxial(compiled_with_sensor_group, base_configuration)
            if paraxial.paraxial_image_position_mm is not None:
                initial_offset = float(paraxial.paraxial_image_position_mm) - sensor_x
        frequency_lpmm = float(
            image_plane_policy.get("frequency_lpmm")
            or (image_plane_policy.get("criteria") or {}).get("frequency_lpmm", 20.0)
        )
        fields_weighted = _criteria_fields(image_plane_policy, fields_plain)
        wavelengths_weighted = _criteria_wavelengths(image_plane_policy, wavelengths_plain)

        objective_mode = mode if mode in {"best_focus_mtf", "best_focus_merit"} else "best_focus_rms"
        merit_metrics = (image_plane_policy.get("criteria") or {}).get("metrics")
        base_trace: TraceResult | None = None
        if apply_to != "focus_group":
            base_trace = trace_forward(
                compiled_with_sensor_group,
                [field for field, _ in fields_weighted],
                sampling_plain,
                sorted({float(wavelength) for wavelength, _ in wavelengths_weighted}),
                {"configuration": base_configuration},
            )

        def objective(offset: float) -> float:
            objective_configuration = (
                _with_group_shift(base_configuration, str(focus_group_id), offset)
                if apply_to == "focus_group"
                else base_configuration
            )
            objective_plane_offset = 0.0 if apply_to == "focus_group" else offset
            try:
                if base_trace is not None:
                    projected = _project_trace_to_shifted_plane(
                        base_trace,
                        compiled_with_sensor_group,
                        base_configuration,
                        objective_plane_offset,
                    )
                    return _metric_value_from_trace(
                        projected,
                        compiled_with_sensor_group,
                        fields_weighted,
                        wavelengths_weighted,
                        objective_mode,
                        frequency_lpmm,
                        merit_metrics,
                    )
                return _metric_value(
                    compiled_with_sensor_group,
                    fields_weighted,
                    sampling_plain,
                    wavelengths_weighted,
                    objective_configuration,
                    objective_plane_offset,
                    objective_mode,
                    frequency_lpmm,
                    merit_metrics,
                )
            except ValueError:
                return float("inf")

        if mode == "sweep":
            steps = int(search.get("steps", 11))
            offsets = np.linspace(initial_offset - search_range, initial_offset + search_range, max(2, steps))
            values = [(float(offset), float(objective(float(offset)))) for offset in offsets]
            focus_curve = [{"offset_from_sensor_mm": offset, "metric": value} for offset, value in values]
            solved_offset, solve_metric = min(values, key=lambda item: item[1])
            solve_status = "swept"
        else:
            low = initial_offset - search_range
            high = initial_offset + search_range
            direct_offset = (
                _direct_best_focus_rms_offset(
                    base_trace,
                    compiled_with_sensor_group,
                    base_configuration,
                    fields_weighted,
                    wavelengths_weighted,
                    low,
                    high,
                )
                if base_trace is not None and mode == "best_focus_rms"
                else None
            )
            if direct_offset is not None:
                solved_offset = direct_offset
                solve_metric = float(objective(solved_offset))
                iterations = 0
                converged = np.isfinite(solve_metric)
            else:
                solved_offset, solve_metric, iterations, converged = _golden_section_minimize(objective, low, high, tolerance, max_iterations)
            solve_status = "converged" if converged and np.isfinite(solve_metric) else "not_converged"
            if solve_status == "not_converged":
                warnings.append(
                    {
                        "severity": "warning",
                        "code": "solve_not_converged",
                        "params": {
                            "mode": mode,
                            "iterations": iterations,
                            "range_mm": search_range,
                            "tolerance_mm": tolerance,
                        },
                        "message_en": f"image_plane_policy {mode!r} did not converge within {iterations} iterations.",
                    }
                )
    else:
        raise ValueError(f"unknown image_plane_policy mode {mode!r}")

    if apply_to == "focus_group":
        solved_focus_group_shift = solved_offset
        evaluation_shift = 0.0
        configuration = _with_group_shift(base_configuration, str(focus_group_id), solved_offset)
    else:
        evaluation_shift = 0.0 if apply_to == "report_only" else solved_offset
        configuration = _with_evaluation_plane_shift(base_configuration, evaluation_shift)
    metadata = {
        "policy_mode": mode,
        "apply_to": apply_to,
        "evaluation_plane_x_mm": sensor_x + evaluation_shift,
        "sensor_x_mm": sensor_x,
        "offset_from_sensor_mm": evaluation_shift,
        "solved_evaluation_plane_x_mm": sensor_x + solved_offset,
        "solved_offset_from_sensor_mm": solved_offset,
        "solved_focus_group_shift_mm": solved_focus_group_shift,
        "solve_status": solve_status,
    }
    if solve_metric is not None:
        metadata["solve_metric"] = solve_metric
    if focus_curve:
        metadata["focus_curve"] = focus_curve
    if warnings:
        metadata["warnings"] = warnings
    return EvaluationPlaneResolution(compiled_with_sensor_group, configuration, metadata, focus_curve)
