from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field as dataclass_field
from typing import Any

import numpy as np

from .aberrations import analyze_longitudinal_aberration, analyze_ray_fan
from .analysis import analyze_spot
from .configuration import validate_configuration
from .models import OpticalSystem
from .psf_mtf import analyze_geometric_mtf, analyze_relative_illumination
from .system import CompiledSystem, compile_system
from .tracing import trace_forward


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

ABERRATION_OPERAND_METRICS = {"ray_fan_error", "longitudinal_aberration"}


def _copy_system(system: OpticalSystem) -> OpticalSystem:
    return OpticalSystem.model_validate(system.model_dump(mode="json"))


def apply_variables(system: OpticalSystem, variables: dict[str, Any] | None) -> OpticalSystem:
    if not variables:
        return system
    updated = _copy_system(system)
    by_id = {surface.id: surface for surface in updated.surfaces}
    stop = next((surface for surface in updated.surfaces if surface.kind == "aperture_stop"), None)
    for key, raw_value in variables.items():
        value = float(raw_value)
        if key == "iris_radius_mm" and stop is not None:
            if stop.aperture is not None:
                stop.aperture.semi_diameter_mm = value
                if stop.aperture.outer_semi_diameter_mm is not None:
                    stop.aperture.outer_semi_diameter_mm = value
            else:
                stop.semi_diameter_mm = value
            continue
        for suffix, attr in {
            "_radius_mm": "radius_mm",
            "_thickness_after_mm": "thickness_after_mm",
            "_focal_length_mm": "focal_length_mm",
            "_semi_diameter_mm": "semi_diameter_mm",
        }.items():
            if key.endswith(suffix):
                surface_id = key[: -len(suffix)]
                if surface_id in by_id:
                    setattr(by_id[surface_id], attr, value)
                break
    return updated


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
    operand_metrics = [
        str(operand.get("metric"))
        for operand in evaluation.get("operands", [])
        if operand.get("metric") in ABERRATION_OPERAND_METRICS
    ]
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


def _aberration_metric_value(
    compiled: CompiledSystem,
    metric: str,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any],
    wavelengths: list[float],
    options: dict[str, Any],
) -> float | None:
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
    return None


def _evaluate_aberration_operands(
    compiled: CompiledSystem,
    operands: list[dict[str, Any]],
    fields: list[dict[str, Any]],
    sampling: dict[str, Any],
    wavelengths: list[float],
    options: dict[str, Any],
) -> tuple[list[OperandResult], MeritResult]:
    results: list[OperandResult] = []
    natural_values: dict[str, float | None] = {}
    score = 0.0
    weights: dict[str, float] = {}
    for operand in operands:
        metric = str(operand.get("metric", ""))
        if metric not in ABERRATION_OPERAND_METRICS:
            continue
        field_id = str(operand["field_id"]) if operand.get("field_id") is not None else None
        wavelength_nm = float(operand["wavelength_nm"]) if operand.get("wavelength_nm") is not None else None
        operand_fields = fields if field_id is None else [field for field in fields if str(field.get("id")) == field_id]
        operand_wavelengths = wavelengths if wavelength_nm is None else [value for value in wavelengths if abs(value - wavelength_nm) <= 1.0e-9]
        value = _aberration_metric_value(compiled, metric, operand_fields, sampling, operand_wavelengths, options) if operand_fields and operand_wavelengths else None
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
    for metric in ("ray_fan_error", "longitudinal_aberration"):
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
    if isinstance(system_or_compiled, CompiledSystem):
        system = apply_variables(system_or_compiled.system, variables)
    else:
        system = apply_variables(system_or_compiled, variables)
    compiled = compile_system(system)
    config_validation = validate_configuration(compiled, configuration)
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
    requested_operands = [
        operand
        for operand in (evaluation or {}).get("operands", [])
        if operand.get("metric") in ABERRATION_OPERAND_METRICS
    ]
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
    if any(metric in metrics for metric in ("rms_spot_radius", "geometric_mtf")):
        trace = trace_forward(compiled, fields, sampling, wavelengths, {"configuration": configuration or {}})
    metric_values: dict[str, Any] = {}
    if "rms_spot_radius" in metrics:
        assert trace is not None
        metric_values["rms_spot_radius"] = analyze_spot(trace).rms_radius_mm
    if "relative_illumination" in metrics:
        metric_values["relative_illumination"] = analyze_relative_illumination(compiled, fields, sampling, wavelengths, {"configuration": configuration or {}})
    if "geometric_mtf" in metrics:
        assert trace is not None
        metric_values["geometric_mtf"] = analyze_geometric_mtf(trace, frequencies)
    analysis_options = {"configuration": configuration or {}}
    if "ray_fan_error" in metrics and not requested_operands:
        metric_values["ray_fan_error"] = _aberration_metric_value(
            compiled, "ray_fan_error", fields, sampling, wavelengths, analysis_options
        )
    if "longitudinal_aberration" in metrics and not requested_operands:
        metric_values["longitudinal_aberration"] = _aberration_metric_value(
            compiled, "longitudinal_aberration", fields, sampling, wavelengths, analysis_options
        )

    if requested_operands:
        operand_results, merit = _evaluate_aberration_operands(
            compiled,
            requested_operands,
            fields,
            sampling,
            wavelengths,
            analysis_options,
        )
        metric_values.update({operand.metric: operand.value for operand in operand_results})
    else:
        operand_results = []
        merit = _compute_merit(metric_values, weights)
    return EvaluateResult(
        status="ok",
        merit=merit,
        metrics=metric_values,
        violations=[],
        metadata={"stage": "evaluation", "system_hash": compiled.system_hash, "metrics": metrics},
        operands=operand_results,
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
