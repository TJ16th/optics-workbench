from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field as dataclass_field, replace
import hashlib
import io
import json
import math
from typing import Any

import numpy as np

from .aberrations import analyze_distortion, analyze_longitudinal_aberration, analyze_ray_fan
from .analysis import analyze_spot
from .artifacts import ARTIFACT_STORE, artifact_uri
from .chromatic import analyze_chromatic_aberration
from .configuration import surface_gap_values, validate_configuration
from .evaluation_metrics import SUPPORTED_EVALUATE_METRICS
from .field_curvature import analyze_field_curvature, analyze_ms_image_surface
from .models import OpticalSystem, StructuredOpticsError
from .paraxial import analyze_paraxial
from .psf_mtf import analyze_geometric_mtf, analyze_relative_illumination, analyze_white_mtf
from .solves import resolve_configuration_solves
from .system import CompiledSystem, compile_system
from .tracing import CandidateTraceCoordinator, trace_forward
from .variables import apply_variable_bindings, resolve_variable_binding, variable_value


@dataclass(frozen=True)
class MeritResult:
    score: float
    metrics: dict[str, float | None]
    weights: dict[str, float]
    definition: str = "sum_of_squared_residuals_plus_penalties"


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
    one_sided: str | None = None


@dataclass(frozen=True)
class JacobianColumnResult:
    variable: str
    scheme_used: str
    step: float
    violations: list[dict[str, Any]] = dataclass_field(default_factory=list)


@dataclass(frozen=True)
class JacobianResult:
    status: str
    mode: str
    variables: list[str]
    residuals: list[float]
    matrix_shape: list[int]
    matrix: list[list[float | None]] | str
    steps_used: dict[str, float]
    columns: list[JacobianColumnResult]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class EvaluateResult:
    status: str
    merit: MeritResult | None
    metrics: dict[str, Any]
    violations: list[dict[str, Any]]
    metadata: dict[str, Any]
    operands: list[OperandResult] = dataclass_field(default_factory=list)
    configuration_resolved: dict[str, Any] | None = None
    legacy_merit: MeritResult | None = None
    jacobian: JacobianResult | None = None


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
        "operands": [
            {"metric": "rms_spot_radius", "target": 0.0, "tolerance": 1.0, "weight": 1.0},
            {"metric": "relative_illumination", "target": 1.0, "tolerance": 1.0, "weight": 0.25},
            {"metric": "geometric_mtf", "target": 1.0, "tolerance": 1.0, "weight": 0.5},
        ],
        "weights": {"rms_spot_radius": 1.0, "relative_illumination_loss": 0.25, "geometric_mtf_loss": 0.5},
        "ray_sampling": {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        "frequencies_lp_per_mm": [10.0],
    },
    "spot_only": {
        "operands": [{"metric": "rms_spot_radius", "target": 0.0, "tolerance": 1.0, "weight": 1.0}],
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


def _default_operand(metric: str, evaluation: dict[str, Any]) -> dict[str, Any]:
    constraints = evaluation.get("constraints", {})
    constraint_key = {
        "edge_thickness": "min_edge_thickness_mm",
        "min_air_gap": "min_air_gap_mm",
    }.get(metric)
    if constraint_key and constraint_key in constraints:
        tolerance_key = f"{constraint_key.removesuffix('_mm')}_tolerance_mm"
        return {
            "metric": metric,
            "target": float(constraints[constraint_key]),
            "tolerance": float(constraints.get(tolerance_key, 1.0)),
            "weight": 1.0,
            "one_sided": "lower",
        }
    target = 1.0 if metric in {"relative_illumination", "geometric_mtf", "white_mtf"} else 0.0
    return {"metric": metric, "target": target, "tolerance": 1.0, "weight": 1.0}


def _resolve_evaluation(
    evaluation: dict[str, Any] | None,
    ray_sampling: dict[str, Any] | None,
) -> tuple[list[str], list[dict[str, Any]], dict[str, float], dict[str, Any], list[float]]:
    evaluation = dict(evaluation or {})
    preset = evaluation.get("preset")
    preset_data = PRESETS.get(preset, {}) if preset else {}
    if evaluation.get("operands") is not None:
        operands = [dict(operand) for operand in evaluation.get("operands", [])]
    elif preset_data:
        operands = [dict(operand) for operand in preset_data.get("operands", [])]
    else:
        operands = [_default_operand(str(metric), evaluation) for metric in evaluation.get("metrics", ["rms_spot_radius"])]
    metrics = [str(operand.get("metric", "")) for operand in operands]
    weights = dict(preset_data.get("weights", {}))
    weights.update(evaluation.get("weights", {}))
    sampling = dict(preset_data.get("ray_sampling", {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}))
    sampling.update(ray_sampling or {})
    frequencies = list(evaluation.get("frequencies_lp_per_mm", preset_data.get("frequencies_lp_per_mm", [10.0])))
    return metrics, operands, weights, sampling, [float(freq) for freq in frequencies]


def _constraint_penalty(violations: list[dict[str, Any]]) -> float:
    penalty = 0.0
    for violation in violations:
        penalty += 1000.0 if violation.get("severity") == "error" else 10.0
    return penalty


def _derive_merit(operands: list[OperandResult], *, hard_penalty: float = 0.0) -> MeritResult:
    metrics: dict[str, float | None] = {}
    weights: dict[str, float] = {}
    score = float(hard_penalty)
    ray_loss_penalty = 0.0
    continuous_constraint_penalty = 0.0
    for operand in operands:
        metrics[operand.metric] = operand.value
        weights[operand.metric] = operand.weight
        contribution = float(operand.residual or 0.0) ** 2
        score += contribution
        if operand.metric == "ray_loss_ratio":
            ray_loss_penalty += contribution
        elif operand.metric in {"edge_thickness", "min_air_gap"}:
            continuous_constraint_penalty += contribution
    metrics.update(
        {
            "ray_loss_penalty": ray_loss_penalty,
            "continuous_constraint_penalty": continuous_constraint_penalty,
            "hard_penalty": float(hard_penalty),
            "constraint_penalty": float(hard_penalty),
            "score": score,
        }
    )
    return MeritResult(score=score, metrics=metrics, weights=weights)


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
) -> list[OperandResult]:
    results: list[OperandResult] = []
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
        one_sided = operand.get("one_sided")
        if one_sided not in {None, "lower", "upper"}:
            raise StructuredOpticsError(
                "optics_value_error",
                "Operand one_sided must be lower or upper.",
                params={"metric": metric, "one_sided": one_sided, "supported": ["lower", "upper"]},
            )
        if value is None:
            residual = None
        elif one_sided == "lower":
            residual = weight * max(0.0, target - value) / tolerance
        elif one_sided == "upper":
            residual = weight * max(0.0, value - target) / tolerance
        else:
            residual = weight * (value - target) / tolerance
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
                one_sided=one_sided,
            )
        )
    return results


def _compute_legacy_merit(metric_values: dict[str, Any], weights: dict[str, float]) -> MeritResult:
    score = 0.0
    flat: dict[str, float | None] = {}
    rms = metric_values.get("rms_spot_radius")
    if rms is not None:
        flat["rms_spot_radius"] = float(rms)
        score += weights.get("rms_spot_radius", 1.0) * float(rms)
    ri = metric_values.get("relative_illumination")
    if ri is not None:
        min_ri = float(ri)
        loss = max(0.0, 1.0 - min_ri)
        flat["relative_illumination_loss"] = loss
        score += weights.get("relative_illumination_loss", 0.0) * loss
    mtf = metric_values.get("geometric_mtf")
    if mtf is not None:
        value = float(mtf)
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
    return MeritResult(score=score, metrics=flat, weights=weights, definition="legacy_linear_weighted_score")


def _legacy_deprecation_metadata() -> dict[str, Any]:
    return {
        "field": "legacy_merit",
        "deprecated": True,
        "replacement": "merit",
        "removal_target_api_schema_version": "2.6.0",
        "message_en": "legacy_merit preserves the deprecated linear weighted score for one compatibility release.",
    }


def evaluate_system(
    system_or_compiled: OpticalSystem | CompiledSystem,
    evaluation: dict[str, Any] | None = None,
    *,
    configuration: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
    ray_sampling: dict[str, Any] | None = None,
    jacobian: dict[str, Any] | None = None,
) -> EvaluateResult:
    if jacobian is not None:
        return _evaluate_with_jacobian(
            system_or_compiled,
            evaluation,
            configuration=configuration,
            variables=variables,
            ray_sampling=ray_sampling,
            jacobian=jacobian,
            warm_refinement=True,
        )
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
        hard_penalty = _constraint_penalty(violations)
        return EvaluateResult(
            status="infeasible",
            merit=_derive_merit([], hard_penalty=hard_penalty),
            metrics={},
            violations=violations,
            metadata={
                "stage": "constraint_check",
                "system_hash": compiled.system_hash,
                "merit_definition": "sum_of_squared_residuals_plus_penalties",
                "deprecations": [_legacy_deprecation_metadata()],
            },
            legacy_merit=MeritResult(
                score=hard_penalty,
                metrics={"constraint_penalty": hard_penalty, "score": hard_penalty},
                weights={},
                definition="legacy_linear_weighted_score",
            ),
        )

    metrics, requested_operands, weights, sampling, frequencies = _resolve_evaluation(evaluation, ray_sampling)
    fields = _fields_from_evaluation(evaluation)
    wavelengths = _wavelengths_from_evaluation(compiled, evaluation)
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
            merit=_derive_merit([], hard_penalty=penalty),
            metrics={},
            violations=violations,
            metadata={
                "stage": "operand_validation",
                "system_hash": compiled.system_hash,
                "merit_definition": "sum_of_squared_residuals_plus_penalties",
                "deprecations": [_legacy_deprecation_metadata()],
            },
            legacy_merit=MeritResult(
                score=penalty,
                metrics={"constraint_penalty": penalty, "score": penalty},
                weights={},
                definition="legacy_linear_weighted_score",
            ),
        )
    analysis_options = {"configuration": configuration}
    operand_results = _evaluate_operands(
        compiled,
        requested_operands,
        fields,
        sampling,
        wavelengths,
        analysis_options,
        frequencies,
        evaluation_data,
    )
    metric_values: dict[str, Any] = {operand.metric: operand.value for operand in operand_results}
    legacy_merit = _compute_legacy_merit(metric_values, weights)
    loss_operands = _ray_loss_operands(compiled, fields, sampling, wavelengths, analysis_options, evaluation_data)
    operand_results.extend(loss_operands)
    constraint_operands = _constraint_operands(compiled, configuration, constraints)
    requested_metric_names = {operand.metric for operand in operand_results}
    constraint_operands = [operand for operand in constraint_operands if operand.metric not in requested_metric_names]
    operand_results.extend(constraint_operands)
    merit = _derive_merit(operand_results)
    return EvaluateResult(
        status="ok",
        merit=merit,
        metrics=metric_values,
        violations=[issue.model_dump(mode="json") for issue in config_validation.issues if issue.severity != "error"],
        metadata={
            "stage": "evaluation",
            "system_hash": compiled.system_hash,
            "metrics": metrics,
            "merit_definition": "sum_of_squared_residuals_plus_penalties",
            "expanded_operands": requested_operands,
            "deprecations": [_legacy_deprecation_metadata()],
            **({"warnings": variable_application.warnings} if variable_application.warnings else {}),
        },
        operands=operand_results,
        configuration_resolved=configuration if solve_results else None,
        legacy_merit=legacy_merit,
    )


def _jacobian_error(message_en: str, params: dict[str, Any]) -> StructuredOpticsError:
    return StructuredOpticsError("optics_value_error", message_en, params={"location": "jacobian", **params})


def _resolve_jacobian_plan(
    base_system: OpticalSystem,
    configuration: dict[str, Any] | None,
    variables: dict[str, Any] | None,
    request: dict[str, Any],
) -> tuple[str, list[str], dict[str, float], dict[str, float], list[dict[str, Any]]]:
    unknown_fields = sorted(set(request) - {"mode", "variables", "steps"})
    if unknown_fields:
        raise _jacobian_error("Unknown jacobian request field.", {"unknown_fields": unknown_fields})
    mode = str(request.get("mode", "forward_diff"))
    if mode not in {"forward_diff", "central_diff"}:
        raise _jacobian_error(
            "Unknown jacobian mode.",
            {"mode": mode, "supported_modes": ["forward_diff", "central_diff"]},
        )
    requested_variables = request.get("variables")
    if not isinstance(requested_variables, list) or not requested_variables or not all(
        isinstance(key, str) and key for key in requested_variables
    ):
        raise _jacobian_error("jacobian.variables must be a non-empty string array.", {"variables": requested_variables})
    variable_keys = list(requested_variables)
    duplicates = sorted({key for key in variable_keys if variable_keys.count(key) > 1})
    if duplicates:
        raise _jacobian_error("jacobian.variables must not contain duplicates.", {"duplicate_variables": duplicates})
    request_steps = request.get("steps", {})
    if not isinstance(request_steps, dict):
        raise _jacobian_error("jacobian.steps must be an object.", {"steps": request_steps})
    unknown_steps = sorted(set(request_steps) - set(variable_keys))
    if unknown_steps:
        raise _jacobian_error("jacobian.steps contains an unrequested variable.", {"variables": unknown_steps})

    application = apply_variable_bindings(base_system, variables, configuration)
    base_values: dict[str, float] = {}
    steps_used: dict[str, float] = {}
    adjustments: list[dict[str, Any]] = []
    for key in variable_keys:
        try:
            binding = resolve_variable_binding(application.system, key)
            base = variable_value(application.system, application.configuration, binding)
        except StructuredOpticsError as exc:
            raise _jacobian_error(exc.message_en, {"variable": key, **exc.params}) from exc
        if key in request_steps:
            try:
                step = float(request_steps[key])
            except (TypeError, ValueError) as exc:
                raise _jacobian_error("Jacobian step must be a finite positive number.", {"variable": key, "step": request_steps[key]}) from exc
        else:
            step = binding.default_step(base)
        if not math.isfinite(step) or step <= 0.0:
            raise _jacobian_error("Jacobian step must be a finite positive number.", {"variable": key, "step": step})
        if base + step == base:
            raised = float(np.nextafter(base, math.inf) - base)
            if raised <= 0.0 or not math.isfinite(raised):
                raise _jacobian_error("Jacobian step cannot perturb the base value.", {"variable": key, "base": base, "step": step})
            adjustments.append({"variable": key, "requested_step": step, "used_step": raised, "reason": "machine_spacing"})
            step = raised
        base_values[key] = base
        steps_used[key] = step
    return mode, variable_keys, base_values, steps_used, adjustments


def _jacobian_sampling(
    ray_sampling: dict[str, Any] | None,
    workspace: dict[str, Any] | None,
    role: str,
    candidate_id: str,
) -> dict[str, Any]:
    sampling = dict(ray_sampling or {})
    aiming = dict(sampling.get("ray_aiming", {}))
    if aiming.get("mode", "paraxial") == "full":
        aiming["strategy"] = "exact"
        if workspace is not None:
            aiming["_request_local_workspace"] = workspace
            aiming["_workspace_role"] = role
            aiming["_candidate_id"] = candidate_id
    sampling["ray_aiming"] = aiming
    return sampling


def _residual_vector(result: EvaluateResult) -> list[float] | None:
    if result.status != "ok":
        return None
    values: list[float] = []
    for operand in result.operands:
        if operand.residual is None or not math.isfinite(float(operand.residual)):
            return None
        values.append(float(operand.residual))
    return values


def _candidate_violation(exc: Exception) -> list[dict[str, Any]]:
    if isinstance(exc, StructuredOpticsError):
        return [{"severity": "error", "code": exc.code, "params": dict(exc.params), "message_en": exc.message_en}]
    return [
        {
            "severity": "error",
            "code": "infeasible",
            "params": {"exception_type": type(exc).__name__, "message": str(exc)},
            "message_en": "Jacobian perturbation is infeasible.",
        }
    ]


def _matrix_payload(
    matrix: list[list[float | None]],
    signature: dict[str, Any],
) -> tuple[list[list[float | None]] | str, dict[str, Any]]:
    rows = len(matrix)
    columns = 0 if rows == 0 else len(matrix[0])
    if rows * columns <= 1000 or any(value is None for row in matrix for value in row):
        return matrix, {"storage": "inline_json", "dtype": "float64"}
    array = np.asarray(matrix, dtype=np.float64)
    stream = io.BytesIO()
    np.save(stream, array, allow_pickle=False)
    content = stream.getvalue()
    canonical = json.dumps(signature, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    artifact_id = "jac_" + hashlib.sha256(content + canonical).hexdigest()
    artifact = ARTIFACT_STORE.put("jacobian", content, content_type="application/x-npy", id=artifact_id)
    return artifact_uri(artifact), {"storage": "artifact_npy", "dtype": "float64", "artifact_id": artifact_id}


def _evaluate_with_jacobian(
    system_or_compiled: OpticalSystem | CompiledSystem,
    evaluation: dict[str, Any] | None,
    *,
    configuration: dict[str, Any] | None,
    variables: dict[str, Any] | None,
    ray_sampling: dict[str, Any] | None,
    jacobian: dict[str, Any],
    warm_refinement: bool,
) -> EvaluateResult:
    if not isinstance(jacobian, dict):
        raise _jacobian_error("jacobian must be an object.", {"jacobian": jacobian})
    base_system = system_or_compiled.system if isinstance(system_or_compiled, CompiledSystem) else system_or_compiled
    mode, variable_keys, base_values, steps_used, step_adjustments = _resolve_jacobian_plan(
        base_system, configuration, variables, jacobian
    )
    workspace: dict[str, Any] | None = {} if warm_refinement else None
    base_result = evaluate_system(
        base_system,
        evaluation,
        configuration=configuration,
        variables=variables,
        ray_sampling=_jacobian_sampling(ray_sampling, workspace, "base", "base"),
    )
    base_residuals = _residual_vector(base_result)
    if base_residuals is None:
        return base_result

    matrix: list[list[float | None]] = [[None for _ in variable_keys] for _ in base_residuals]
    columns: list[JacobianColumnResult] = []
    candidate_count = 0
    batch_calls = 0
    batch_fallback_calls = 0

    def candidate_batch(
        requests: list[tuple[str, str, float]],
    ) -> dict[str, tuple[list[float] | None, list[dict[str, Any]]]]:
        nonlocal candidate_count, batch_calls, batch_fallback_calls
        candidate_count += len(requests)
        answers: dict[str, tuple[list[float] | None, list[dict[str, Any]]]] = {}
        if not warm_refinement:
            for candidate_id, key, value in requests:
                try:
                    result = evaluate_system(
                        base_system,
                        evaluation,
                        configuration=configuration,
                        variables={**(variables or {}), key: value},
                        ray_sampling=_jacobian_sampling(ray_sampling, None, "candidate", candidate_id),
                    )
                except (StructuredOpticsError, ValueError, TypeError) as exc:
                    answers[candidate_id] = (None, _candidate_violation(exc))
                    continue
                residuals = _residual_vector(result)
                violations = list(result.violations) or [
                    {
                        "severity": "error",
                        "code": "infeasible",
                        "params": {"candidate_id": candidate_id},
                        "message_en": "Jacobian candidate did not produce the base residual layout.",
                    }
                ]
                answers[candidate_id] = (
                    residuals if residuals is not None and len(residuals) == len(base_residuals) else None,
                    [] if residuals is not None and len(residuals) == len(base_residuals) else violations,
                )
            return answers
        prepared: list[tuple[str, OpticalSystem, dict[str, Any]]] = []
        constraints = dict((evaluation or {}).get("constraints", {}))
        for candidate_id, key, value in requests:
            candidate_variables = {**(variables or {}), key: value}
            try:
                application = apply_variable_bindings(base_system, candidate_variables, configuration)
                candidate_system, candidate_configuration, _ = resolve_configuration_solves(
                    application.system, application.configuration
                )
                candidate_compiled = compile_system(candidate_system)
                validation = validate_configuration(
                    candidate_compiled,
                    candidate_configuration,
                    min_air_gap_mm=float(constraints.get("min_air_gap_mm", 0.0)),
                    min_edge_thickness_mm=float(constraints.get("min_edge_thickness_mm", 0.0)),
                )
                if not validation.ok:
                    answers[candidate_id] = (
                        None,
                        [issue.model_dump(mode="json") for issue in validation.issues],
                    )
                    continue
                prepared.append((candidate_id, candidate_system, candidate_configuration))
            except (StructuredOpticsError, ValueError, TypeError) as exc:
                answers[candidate_id] = (None, _candidate_violation(exc))

        if not prepared:
            return answers
        coordinator = CandidateTraceCoordinator(len(prepared))

        def run(index_and_candidate: tuple[int, tuple[str, OpticalSystem, dict[str, Any]]]):
            index, (candidate_id, candidate_system, candidate_configuration) = index_and_candidate
            sampling = _jacobian_sampling(ray_sampling, workspace, "candidate", candidate_id)
            aiming = dict(sampling.get("ray_aiming", {}))
            aiming["_candidate_trace_coordinator"] = coordinator
            aiming["_candidate_index"] = index
            sampling["ray_aiming"] = aiming
            try:
                result = evaluate_system(
                    candidate_system,
                    evaluation,
                    configuration=candidate_configuration,
                    ray_sampling=sampling,
                )
            except (StructuredOpticsError, ValueError, TypeError) as exc:
                return candidate_id, None, _candidate_violation(exc)
            residuals = _residual_vector(result)
            if residuals is None or len(residuals) != len(base_residuals):
                violations = list(result.violations) or [
                    {
                        "severity": "error",
                        "code": "infeasible",
                        "params": {"candidate_id": candidate_id},
                        "message_en": "Jacobian candidate did not produce the base residual layout.",
                    }
                ]
                return candidate_id, None, violations
            return candidate_id, residuals, []

        with ThreadPoolExecutor(max_workers=len(prepared)) as pool:
            rows = list(pool.map(run, enumerate(prepared)))
        for candidate_id, residuals, violations in rows:
            answers[candidate_id] = (residuals, violations)
        batch_calls += coordinator.batch_calls
        batch_fallback_calls += coordinator.fallback_calls
        return answers

    plus_requests = [
        (f"{key}:+", key, base_values[key] + steps_used[key])
        for key in variable_keys
    ]
    plus_answers = candidate_batch(plus_requests)
    minus_answers: dict[str, tuple[list[float] | None, list[dict[str, Any]]]] = {}
    if mode == "central_diff":
        minus_answers = candidate_batch(
            [(f"{key}:-", key, base_values[key] - steps_used[key]) for key in variable_keys]
        )
    else:
        fallback_requests = [
            (f"{key}:-fallback", key, base_values[key] - steps_used[key])
            for key in variable_keys
            if plus_answers[f"{key}:+"][0] is None
        ]
        if fallback_requests:
            minus_answers = candidate_batch(fallback_requests)

    for column_index, key in enumerate(variable_keys):
        base_value = base_values[key]
        step = steps_used[key]
        plus, plus_violations = plus_answers[f"{key}:+"]
        minus = None
        minus_violations: list[dict[str, Any]] = []
        scheme = "failed"
        values: list[float] | None = None
        violations: list[dict[str, Any]] = []
        if mode == "forward_diff":
            if plus is not None:
                values = [(plus[row] - base_residuals[row]) / step for row in range(len(base_residuals))]
                scheme = "forward"
            else:
                minus, minus_violations = minus_answers[f"{key}:-fallback"]
                if minus is not None:
                    values = [(base_residuals[row] - minus[row]) / step for row in range(len(base_residuals))]
                    scheme = "backward_fallback"
                else:
                    violations = plus_violations + minus_violations
        else:
            minus, minus_violations = minus_answers[f"{key}:-"]
            if plus is not None and minus is not None:
                values = [(plus[row] - minus[row]) / (2.0 * step) for row in range(len(base_residuals))]
                scheme = "central"
            elif plus is not None:
                values = [(plus[row] - base_residuals[row]) / step for row in range(len(base_residuals))]
                scheme = "forward_fallback"
                violations = minus_violations
            elif minus is not None:
                values = [(base_residuals[row] - minus[row]) / step for row in range(len(base_residuals))]
                scheme = "backward_fallback"
                violations = plus_violations
            else:
                violations = plus_violations + minus_violations
        if values is not None:
            for row_index, value in enumerate(values):
                matrix[row_index][column_index] = float(value)
        columns.append(JacobianColumnResult(key, scheme, step, violations))

    status = "ok" if all(column.scheme_used != "failed" for column in columns) else "partial"
    signature = {
        "system_hash": base_result.metadata.get("system_hash"),
        "evaluation": evaluation or {},
        "configuration": configuration or {},
        "variables": variables or {},
        "ray_sampling": ray_sampling or {},
        "jacobian": jacobian,
    }
    matrix_value, storage_metadata = _matrix_payload(matrix, signature)
    diagnostics = [] if workspace is None else workspace.get("diagnostics", [])
    warm_seeded = sum(1 for row in diagnostics if row.get("warm_seeded"))
    cold_fallbacks = sum(
        int(np.sum(np.asarray(row.get("cold_fallback", []), dtype=bool)))
        for row in diagnostics
        if row.get("warm_seeded")
    )
    jacobian_result = JacobianResult(
        status=status,
        mode=mode,
        variables=variable_keys,
        residuals=base_residuals,
        matrix_shape=[len(base_residuals), len(variable_keys)],
        matrix=matrix_value,
        steps_used=steps_used,
        columns=columns,
        metadata={
            "strategy": "candidate_axis_batch" if warm_refinement else "independent_exact",
            "candidate_evaluations": candidate_count,
            "candidate_batch_trace_calls": batch_calls,
            "candidate_batch_fallback_calls": batch_fallback_calls,
            "warm_seeded_solves": warm_seeded,
            "cold_fallbacks": cold_fallbacks,
            "global_cache_write": False,
            "step_adjustments": step_adjustments,
            **storage_metadata,
        },
    )
    return replace(base_result, jacobian=jacobian_result)


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
