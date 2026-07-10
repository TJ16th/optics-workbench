from __future__ import annotations

from typing import Any

import numpy as np

from optics_engine.configuration import runtime_layout, validate_configuration
from optics_engine.core import field_direction
from optics_engine.system import CompiledSystem
from optics_engine.tracing import (
    TraceResult,
    _aim_origin_to_stop,
    _aperture_radius,
    _target_points_for_stop_with_layout,
    _trace_raw,
    _unit_disk_samples,
)


def _combine_single_ray_results(results: list[TraceResult], field_ids: list[str]) -> TraceResult:
    return TraceResult(
        origins=np.vstack([result.origins for result in results]) if results else np.empty((0, 3)),
        directions=np.vstack([result.directions for result in results]) if results else np.empty((0, 3)),
        wavelengths_nm=np.concatenate([result.wavelengths_nm for result in results]) if results else np.empty((0,)),
        field_ids=field_ids,
        status=np.concatenate([result.status for result in results]) if results else np.empty((0,), dtype=object),
        sensor_y_mm=np.concatenate([result.sensor_y_mm for result in results]) if results else np.empty((0,)),
        sensor_z_mm=np.concatenate([result.sensor_z_mm for result in results]) if results else np.empty((0,)),
        paths=[path for result in results for path in result.paths],
        metadata={"kernel": "reference_level0_per_ray"},
        eye_theta_y_deg=np.concatenate([result.eye_theta_y_deg for result in results]) if results and results[0].eye_theta_y_deg is not None else None,
        eye_theta_z_deg=np.concatenate([result.eye_theta_z_deg for result in results]) if results and results[0].eye_theta_z_deg is not None else None,
    )


def trace_forward_reference(
    compiled: CompiledSystem,
    fields: list[dict[str, Any]],
    sampling: dict[str, Any] | None = None,
    wavelengths: list[float] | None = None,
    options: dict[str, Any] | None = None,
) -> TraceResult:
    """Trace rays one-by-one as the Level 0 reference path.

    This intentionally preserves a per-ray execution route so optimized batch
    kernels can be checked for shape-dependent regressions.
    """

    sampling = sampling or {}
    options = options or {}
    configuration = options.get("configuration") or options.get("config") or {}
    config_validation = validate_configuration(compiled, configuration)
    if not config_validation.ok:
        messages = "; ".join(issue.message for issue in config_validation.issues if issue.severity == "error")
        raise ValueError(messages)

    layout = runtime_layout(compiled, configuration)
    centers_mm = layout.centers_mm
    rotations = layout.rotations
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
    _, stop_outer, _ = _aperture_radius(compiled, configuration)
    launch_x = min(first_x, targets[0, 0]) - max(100.0, 10.0 * stop_outer)

    results: list[TraceResult] = []
    field_ids: list[str] = []
    aiming_ok: list[bool] = []
    aiming_iterations: list[int] = []

    for field in fields:
        if field.get("type", "angular") != "angular":
            raise NotImplementedError("only angular fields are implemented in this reference path")
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
                single = _trace_raw(
                    compiled,
                    origin.reshape(1, 3),
                    direction.reshape(1, 3),
                    np.array([float(wavelength)], dtype=float),
                    field_ids=[str(field.get("id", "field"))],
                    store_path=store_path,
                    centers_mm=centers_mm,
                    rotations=rotations,
                    configuration=configuration,
                )
                results.append(single)
                field_ids.append(str(field.get("id", "field")))
                aiming_ok.append(ok)
                aiming_iterations.append(iterations)

    combined = _combine_single_ray_results(results, field_ids)
    aiming_ok_array = np.array(aiming_ok, dtype=bool)
    combined.status[~aiming_ok_array] = "aiming_failed"
    combined.metadata.update(
        {
            "ray_aiming_mode": aiming_mode,
            "aiming_failed_count": int(np.sum(~aiming_ok_array)),
            "aiming_iterations_max": int(max(aiming_iterations) if aiming_iterations else 0),
            "samples_per_field": samples_per_field,
        }
    )
    return combined
