from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field as dataclass_field
from typing import Any

import numpy as np

from .aberrations import analyze_distortion, analyze_longitudinal_aberration, analyze_ray_fan
from .analysis import analyze_spot
from .chromatic import analyze_chromatic_aberration
from .configuration import surface_gap_values, validate_configuration
from .evaluation_metrics import SUPPORTED_EVALUATE_METRICS
from .field_curvature import analyze_field_curvature, analyze_ms_image_surface
from .models import OpticalSystem, StructuredOpticsError
from .paraxial import analyze_paraxial
from .psf_mtf import analyze_geometric_mtf, analyze_relative_illumination, analyze_white_mtf
from .solves import resolve_configuration_solves
from .system import CompiledSystem, compile_system
from .tracing import trace_forward
from .variables import apply_variable_bindings


@dataclass(frozen=True)
class MeritResult:
    score: float
    metrics: dict[str, float | None]
    weights: dict[str, float]


@dataclass(frozen=True)
class OperandResult:
    metric: str
    value: float | None
    target: float
    tolerance: float
    weight: float
    residual: float | None
    field_id: str | None = None
    wavelength_nm: float | None = None


@dataclass(frozen=True)
class EvaluateResult:
    status: str
    merit: MeritResult | None
    metrics: dict[str, Any]
    violations: list[dict[str, Any]]
    metadata: dict[str, Any]
    operands: list[OperandResult] = dataclass_field(default_factory=list)
    configuration_resolved: dict[str, Any] | None = None


@dataclass(frozen=True)
class BatchCandidateResult:
    id: str
    result: EvaluateResult


@dataclass(frozen=True)
class BatchEvaluateResult:
    status: str
    candidates: list[BatchCandidateResult]
    metadata: dict[str, Any]


PRESETS: dict[str, dict[str, Any]] = {
    "fast_design_score": {
        "metrics": ["rms_spot_radius", "relative_illumination", "geometric_mtf"],
        "weights": {"rms_spot_radius": 1.0, "relative_illumination_loss": 0.25, "geometric_mtf_loss": 0.5},
        "ray_sampling": {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        "frequencies_lp_per_mm": [10.0],
    },
    "spot_only": {
        "metrics": ["rms_spot_radius"],
        "weights": {"rms_spot_radius": 1.0},
        "ray_sampling": {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
    },
}

def apply_variables(system: OpticalSystem, variables: dict[str, Any] | None) -> OpticalSystem:
    return apply_variable_bindings(system, variables).system


def _fields_from_evaluation(evaluation: dict[str, Any] | None) -> list[dict[str, Any]]:
    evaluation = evaluation or {}
    fields = evaluation.get("fields")
    if fields:
        return [
            {
                "id": field.get("id", f"field_{idx}"),
                "type": "angular",
                "theta_y_deg": float(field.get("theta_y_deg", 0.0)),
                "theta_z_deg": float(field.get("theta_z_deg", 0.0)),
            }
            for idx, field in enumerate(fields)
        ]
    return [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]


def _wavelengths_from_evaluation(compiled: CompiledSystem, evaluation: dict[str, Any] | None) -> list[float]:
    evaluation = evaluation or {}
    wavelengths = evaluation.get("wavelengths")
    if wavelengths:
        return [float(item.get("wavelength_nm", item)) if isinstance(item, dict) else float(item) for item in wavelengths]
    return [compiled.system.wavelengths_nm.primary]


def _resolve_evaluation(evaluation: dict[str, Any] | None, ray_sampling: dict[str, Any] | None) -> tuple[list[str], dict[str, float], dict[str, Any], list[float]]:
    evaluation = dict(evaluation or {})
    preset = evaluation.get("preset")
    preset_data = PRESETS.get(preset, {}) if preset else {}
    operand_metrics = [str(operand.get("metric", "")) for operand in evaluation.get("operands", [])]
    metrics = list(evaluation.get("metrics", operand_metrics or preset_data.get("metrics", ["rms_spot_radius"])))
    weights = dict(preset_data.get("weights", {}))
    weights.update(evaluation.get("weights", {}))
    sampling = dict(preset_data.get("ray_sampling", {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}))
    sampling.update(ray_sampling or {})
    frequencies = list(evaluation.get("frequencies_lp_per_mm", preset_data.get("frequencies_lp_per_mm", [10.0])))
    return metrics, weights, sampling, [float(freq) for freq in frequencies]


def _constraint_penalty(violations: list[dict[str, Any]]) -> float:
    penalty = 0.0
    for violation in violations:
        penalty += 1000.0 if violation.get("severity") == "error" else 10.0
    return penalty


def _rms_finite(values: list[float | None]) -> float | None:
    finite = np.asarray([float(value) for value in values if value is not None and np.isfinite(value)], dtype=float)
    if finite.size == 0:
        return None
    return float(np.sqrt(np.mean(np.square(finite))))


def _representative_value(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None and np.isfinite(value)]
    if not finite:
        return None
    if len(finite) == 1:
        return finite[0]
    return _rms_finite(finite)


def _validate_metric_names(metrics: list[str], operands: list[dict[str, Any]]) -> None:
    supported = set(SUPPORTED_EVALUATE_METRICS)
    for location, names in (
        ("evaluation.metrics", metrics),
        ("evaluation.operands", [str(operand.get("metric", "")) for operand in operands]),
    ):
        for metric in names:
            if metric not in supported:
                raise StructuredOpticsError(
                    "optics_value_error",
                    "Unsupported evaluate metric.",
                    params={"metric": metric, "location": location, "supported_metrics": list(SUPPORTED_EVALUATE_METRICS)},
                )


def _metric_scalar_value(
    compiled: CompiledSystem,
    metric: str,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any],
    wavelengths: list[float],
    options: dict[str, Any],
    frequencies: list[float],
    evaluation: dict[str, Any],
) -> float | None:
    configuration = options.get("configuration", {})
    if metric == "rms_spot_radius":
        trace = trace_forward(compiled, fields, sampling, wavelengths, options)
        return analyze_spot(trace).rms_radius_mm
    if metric == "relative_illumination":
        result = analyze_relative_illumination(compiled, fields, sampling, wavelengths, options)
        return min((row.relative_illumination for row in result.rows), default=None)
    if metric == "geometric_mtf":
        trace = trace_forward(compiled, fields, sampling, wavelengths, options)
        result = analyze_geometric_mtf(trace, frequencies)
        return None if not result.points else result.points[-1].mtf_radial
    if metric == "ray_fan_error":
        fan_y = analyze_ray_fan(compiled, fields, {**sampling, "pupil_distribution": "fan_y"}, wavelengths, options)
        fan_z = analyze_ray_fan(compiled, fields, {**sampling, "pupil_distribution": "fan_z"}, wavelengths, options)
        return _rms_finite(
            [point.transverse_error_y_mm for point in fan_y.points if point.status == "alive"]
            + [point.transverse_error_z_mm for point in fan_z.points if point.status == "alive"]
        )
    if metric == "longitudinal_aberration":
        longitudinal = analyze_longitudinal_aberration(
            compiled,
            fields,
            {**sampling, "pupil_distribution": "fan_y"},
            wavelengths,
            options,
        )
        return _rms_finite(
            [point.longitudinal_error_y_mm for point in longitudinal.points if point.status == "alive"]
        )
    if metric == "distortion":
        result = analyze_distortion(compiled, fields, wavelengths, options)
        return _representative_value([row.distortion_percent for row in result.rows])
    if metric == "field_curvature":
        result = analyze_field_curvature(
            compiled,
            fields,
            configuration,
            search_mm=float(evaluation.get("field_curvature_search_mm", 5.0)),
            method=evaluation.get("field_curvature_method"),
        )
        return _representative_value([row.best_focus_shift_mm for row in result.rows])
    if metric == "astigmatism":
        result = analyze_ms_image_surface(
            compiled,
            fields,
            configuration,
            search_mm=float(evaluation.get("field_curvature_search_mm", 5.0)),
            method=evaluation.get("field_curvature_method"),
        )
        return _representative_value(
            [row.tangential_focus_shift_mm - row.sagittal_focus_shift_mm for row in result.rows]
        )
    if metric in {"lateral_color", "axial_color"}:
        result = analyze_chromatic_aberration(compiled, wavelengths, fields)
        if metric == "axial_color":
            return result.axial_color_span_mm
        return _rms_finite(
            [row.get("max_lateral_shift_mm") for row in result.lateral_color_by_field.values()]
        )
    if metric == "white_mtf":
        configured_weights = evaluation.get("wavelength_weights")
        weights = (
            {float(wavelength): float(weight) for wavelength, weight in configured_weights.items()}
            if configured_weights
            else {float(wavelength): 1.0 for wavelength in wavelengths}
        )
        result = analyze_white_mtf(compiled, fields, sampling, weights, frequencies, options)
        return None if not result.mtf.points else result.mtf.points[-1].mtf_radial
    if metric in {"back_focal_length", "effective_focal_length", "f_number"}:
        wavelength = wavelengths[0] if wavelengths else None
        result = analyze_paraxial(compiled, configuration, wavelength_nm=wavelength)
        return {
            "back_focal_length": result.back_focal_length_mm,
            "effective_focal_length": result.effective_focal_length_mm,
            "f_number": result.f_number,
        }[metric]
    if metric == "ray_loss_ratio":
        trace = trace_forward(compiled, fields, sampling, wavelengths, options)
        loss_statuses = set(evaluation.get("ray_loss_statuses", ["total_internal_reflection", "missed", "aiming_failed"]))
        return float(np.mean(np.isin(trace.status, sorted(loss_statuses)))) if trace.status.size else None
    if metric in {"edge_thickness", "min_air_gap"}:
        medium_is_air = metric == "min_air_gap"
        values = [
            row.edge_gap_mm if row.edge_gap_mm is not None else row.vertex_gap_mm
            for row in surface_gap_values(compiled, configuration)
            if (row.medium_id == "AIR") == medium_is_air
        ]
        return None if not values else float(min(values))
    raise AssertionError(f"unhandled evaluate metric: {metric}")


def _ray_loss_operands(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any],
    wavelengths: list[float],
    options: dict[str, Any],
    evaluation: dict[str, Any],
) -> list[OperandResult]:
    tolerance = float(evaluation.get("ray_loss_tolerance", 0.1))
    if tolerance <= 0.0:
        raise StructuredOpticsError(
            "optics_value_error",
            "ray_loss_tolerance must be positive.",
            params={"ray_loss_tolerance": tolerance, "constraint": "value > 0"},
        )
    requested = set(evaluation.get("ray_loss_statuses", ["total_internal_reflection", "missed_surface", "aiming_failed", "numerical_error"]))
    aliases = {"missed_surface": "missed"}
    supported = {"total_internal_reflection", "missed", "missed_surface", "aiming_failed", "blocked", "numerical_error"}
    unknown = sorted(requested - supported)
    if unknown:
        raise StructuredOpticsError(
            "optics_value_error",
            "Unknown ray loss status.",
            params={"ray_loss_statuses": unknown, "supported_statuses": sorted(supported)},
        )
    statuses = {aliases.get(status, status) for status in requested}
    trace = trace_forward(compiled, fields, sampling, wavelengths, options)
    results: list[OperandResult] = []
    for field in fields:
        field_id = str(field.get("id", "field"))
        for wavelength in wavelengths:
            mask = np.asarray(
                [trace.field_ids[index] == field_id and abs(float(trace.wavelengths_nm[index]) - wavelength) <= 1.0e-9 for index in range(trace.status.size)],
                dtype=bool,
            )
            if not np.any(mask):
                value = 0.0
            else:
                weights = np.ones(int(np.sum(mask)), dtype=float) if trace.weights is None else np.asarray(trace.weights[mask], dtype=float)
                total = float(np.sum(weights))
                value = 0.0 if total <= 0.0 else float(np.sum(weights[np.isin(trace.status[mask], sorted(statuses))]) / total)
            results.append(
                OperandResult(
                    metric="ray_loss_ratio",
                    value=value,
                    target=0.0,
                    tolerance=tolerance,
                    weight=1.0,
                    residual=value / tolerance,
                    field_id=field_id,
                    wavelength_nm=float(wavelength),
                )
            )
    return results


def _constraint_operands(
    compiled: CompiledSystem,
    configuration: dict[str, Any],
    constraints: dict[str, Any],
) -> list[OperandResult]:
    results: list[OperandResult] = []
    rows = surface_gap_values(compiled, configuration)
    for metric, key, medium_is_air in (
        ("min_air_gap", "min_air_gap_mm", True),
        ("edge_thickness", "min_edge_thickness_mm", False),
    ):
        if key not in constraints:
            continue
        values = [
            row.edge_gap_mm if row.edge_gap_mm is not None else row.vertex_gap_mm
            for row in rows
            if (row.medium_id == "AIR") == medium_is_air
        ]
        value = None if not values else float(min(values))
        target = float(constraints[key])
        tolerance = float(constraints.get(f"{key.removesuffix('_mm')}_tolerance_mm", 1.0))
        if tolerance <= 0.0:
            raise StructuredOpticsError(
                "optics_value_error",
                "Constraint tolerance must be positive.",
                params={"constraint": key, "tolerance": tolerance, "required": "value > 0"},
            )
        residual = None if value is None else max(0.0, target - value) / tolerance
        results.append(
            OperandResult(
                metric=metric,
                value=value,
                target=target,
                tolerance=tolerance,
                weight=1.0,
                residual=residual,
            )
        )
    return results


def _evaluate_operands(
    compiled: CompiledSystem,
    operands: list[dict[str, Any]],
    fields: list[dict[str, Any]],
    sampling: dict[str, Any],
    wavelengths: list[float],
    options: dict[str, Any],
    frequencies: list[float],
    evaluation: dict[str, Any],
) -> tuple[list[OperandResult], MeritResult]:
    results: list[OperandResult] = []
    natural_values: dict[str, float | None] = {}
    score = 0.0
    weights: dict[str, float] = {}
    for operand in operands:
        metric = str(operand.get("metric", ""))
        field_id = str(operand["field_id"]) if operand.get("field_id") is not None else None
        wavelength_nm = float(operand["wavelength_nm"]) if operand.get("wavelength_nm") is not None else None
        operand_fields = fields if field_id is None else [field for field in fields if str(field.get("id")) == field_id]
        operand_wavelengths = wavelengths if wavelength_nm is None else [value for value in wavelengths if abs(value - wavelength_nm) <= 1.0e-9]
        value = (
            _metric_scalar_value(
                compiled,
                metric,
                operand_fields,
                sampling,
                operand_wavelengths,
                options,
                frequencies,
                evaluation,
            )
            if operand_fields and operand_wavelengths
            else None
        )
        target = float(operand.get("target", 0.0))
        tolerance = float(operand.get("tolerance", 1.0))
        weight = float(operand.get("weight", 1.0))
        residual = None if value is None else weight * (value - target) / tolerance
        if residual is not None:
            score += residual * residual
        natural_values[metric] = value
        weights[metric] = weight
        results.append(
            OperandResult(
                metric=metric,
                value=value,
                target=target,
                tolerance=tolerance,
                weight=weight,
                residual=residual,
                field_id=field_id,
                wavelength_nm=wavelength_nm,
            )
        )
    natural_values["score"] = score
    return results, MeritResult(score=score, metrics=natural_values, weights=weights)


def _compute_merit(metric_values: dict[str, Any], weights: dict[str, float]) -> MeritResult:
    score = 0.0
    flat: dict[str, float | None] = {}
    rms = metric_values.get("rms_spot_radius")
    if rms is not None:
        flat["rms_spot_radius"] = float(rms)
        score += weights.get("rms_spot_radius", 1.0) * float(rms)
    ri = metric_values.get("relative_illumination")
    if ri is not None:
        min_ri = min(row.relative_illumination for row in ri.rows) if ri.rows else 0.0
        loss = max(0.0, 1.0 - min_ri)
        flat["relative_illumination_loss"] = loss
        score += weights.get("relative_illumination_loss", 0.0) * loss
    mtf = metric_values.get("geometric_mtf")
    if mtf is not None and mtf.points:
        value = mtf.points[-1].mtf_radial
        loss = max(0.0, 1.0 - value)
        flat["geometric_mtf_loss"] = loss
        score += weights.get("geometric_mtf_loss", 0.0) * loss
    for metric in SUPPORTED_EVALUATE_METRICS:
        if metric in {"rms_spot_radius", "relative_illumination", "geometric_mtf"}:
            continue
        value = metric_values.get(metric)
        if value is not None:
            flat[metric] = float(value)
            score += weights.get(metric, 1.0) * float(value)
    flat["score"] = score
    return MeritResult(score=score, metrics=flat, weights=weights)


def evaluate_system(
    system_or_compiled: OpticalSystem | CompiledSystem,
    evaluation: dict[str, Any] | None = None,
    *,
    configuration: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
    ray_sampling: dict[str, Any] | None = None,
) -> EvaluateResult:
    base_system = system_or_compiled.system if isinstance(system_or_compiled, CompiledSystem) else system_or_compiled
    variable_application = apply_variable_bindings(base_system, variables, configuration)
    system = variable_application.system
    configuration = variable_application.configuration
    system, configuration, solve_results = resolve_configuration_solves(system, configuration)
    compiled = compile_system(system)
    evaluation_data = dict(evaluation or {})
    constraints = dict(evaluation_data.get("constraints", {}))
    config_validation = validate_configuration(
        compiled,
        configuration,
        min_air_gap_mm=float(constraints.get("min_air_gap_mm", 0.0)),
        min_edge_thickness_mm=float(constraints.get("min_edge_thickness_mm", 0.0)),
    )
    if not config_validation.ok:
        violations = [issue.model_dump(mode="json") for issue in config_validation.issues]
        return EvaluateResult(
            status="infeasible",
            merit=MeritResult(score=_constraint_penalty(violations), metrics={"constraint_penalty": _constraint_penalty(violations)}, weights={}),
            metrics={},
            violations=violations,
            metadata={"stage": "constraint_check", "system_hash": compiled.system_hash},
        )

    metrics, weights, sampling, frequencies = _resolve_evaluation(evaluation, ray_sampling)
    fields = _fields_from_evaluation(evaluation)
    wavelengths = _wavelengths_from_evaluation(compiled, evaluation)
    requested_operands = list(evaluation_data.get("operands", []))
    _validate_metric_names(metrics, requested_operands)
    invalid_tolerances = [
        (index, operand)
        for index, operand in enumerate(requested_operands)
        if float(operand.get("tolerance", 1.0)) <= 0.0
    ]
    if invalid_tolerances:
        violations = [
            {
                "severity": "error",
                "code": "optics_value_error",
                "params": {
                    "operand_index": index,
                    "metric": str(operand.get("metric")),
                    "tolerance": float(operand.get("tolerance", 1.0)),
                    "constraint": "tolerance > 0",
                },
                "message_en": "Operand tolerance must be positive.",
            }
            for index, operand in invalid_tolerances
        ]
        penalty = _constraint_penalty(violations)
        return EvaluateResult(
            status="infeasible",
            merit=MeritResult(score=penalty, metrics={"constraint_penalty": penalty}, weights={}),
            metrics={},
            violations=violations,
            metadata={"stage": "operand_validation", "system_hash": compiled.system_hash},
        )
    trace = None
    if not requested_operands and any(metric in metrics for metric in ("rms_spot_radius", "geometric_mtf")):
        trace = trace_forward(compiled, fields, sampling, wavelengths, {"configuration": configuration})
    metric_values: dict[str, Any] = {}
    if "rms_spot_radius" in metrics and not requested_operands:
        assert trace is not None
        metric_values["rms_spot_radius"] = analyze_spot(trace).rms_radius_mm
    if "relative_illumination" in metrics and not requested_operands:
        metric_values["relative_illumination"] = analyze_relative_illumination(compiled, fields, sampling, wavelengths, {"configuration": configuration})
    if "geometric_mtf" in metrics and not requested_operands:
        assert trace is not None
        metric_values["geometric_mtf"] = analyze_geometric_mtf(trace, frequencies)
    analysis_options = {"configuration": configuration}
    if not requested_operands:
        for metric in metrics:
            if metric in {"rms_spot_radius", "relative_illumination", "geometric_mtf"}:
                continue
            metric_values[metric] = _metric_scalar_value(
                compiled,
                metric,
                fields,
                sampling,
                wavelengths,
                analysis_options,
                frequencies,
                evaluation_data,
            )

    if requested_operands:
        operand_results, merit = _evaluate_operands(
            compiled,
            requested_operands,
            fields,
            sampling,
            wavelengths,
            analysis_options,
            frequencies,
            evaluation_data,
        )
        metric_values.update({operand.metric: operand.value for operand in operand_results})
    else:
        operand_results = []
        merit = _compute_merit(metric_values, weights)
    loss_operands = _ray_loss_operands(compiled, fields, sampling, wavelengths, analysis_options, evaluation_data)
    operand_results.extend(loss_operands)
    loss_penalty = sum(float(operand.residual or 0.0) ** 2 for operand in loss_operands)
    constraint_operands = _constraint_operands(compiled, configuration, constraints)
    operand_results.extend(constraint_operands)
    constraint_penalty = sum(float(operand.residual or 0.0) ** 2 for operand in constraint_operands)
    if merit is not None:
        merit_metrics = dict(merit.metrics)
        merit_metrics["ray_loss_penalty"] = loss_penalty
        merit_metrics["continuous_constraint_penalty"] = constraint_penalty
        merit_metrics["score"] = merit.score + loss_penalty + constraint_penalty
        merit = MeritResult(score=merit.score + loss_penalty + constraint_penalty, metrics=merit_metrics, weights=dict(merit.weights))
    return EvaluateResult(
        status="ok",
        merit=merit,
        metrics=metric_values,
        violations=[issue.model_dump(mode="json") for issue in config_validation.issues if issue.severity != "error"],
        metadata={
            "stage": "evaluation",
            "system_hash": compiled.system_hash,
            "metrics": metrics,
            **({"warnings": variable_application.warnings} if variable_application.warnings else {}),
        },
        operands=operand_results,
        configuration_resolved=configuration if solve_results else None,
    )


def evaluate_batch(
    base_system: OpticalSystem,
    candidates: list[dict[str, Any]],
    evaluation: dict[str, Any] | None = None,
    *,
    configuration: dict[str, Any] | None = None,
    ray_sampling: dict[str, Any] | None = None,
    parallel_workers: int = 1,
) -> BatchEvaluateResult:
    def run(candidate: dict[str, Any]) -> BatchCandidateResult:
        result = evaluate_system(
            base_system,
            evaluation,
            configuration={**(configuration or {}), **candidate.get("configuration", {})},
            variables=candidate.get("variables", {}),
            ray_sampling=ray_sampling,
        )
        return BatchCandidateResult(id=str(candidate.get("id", "candidate")), result=result)

    if parallel_workers > 1 and len(candidates) > 1:
        with ThreadPoolExecutor(max_workers=parallel_workers) as pool:
            rows = list(pool.map(run, candidates))
    else:
        rows = [run(candidate) for candidate in candidates]
    status = "ok" if all(row.result.status == "ok" for row in rows) else "partial"
    return BatchEvaluateResult(status=status, candidates=rows, metadata={"candidate_count": len(rows), "parallel_workers": parallel_workers})
