from copy import deepcopy
from dataclasses import asdict

import optics_engine.optimization as optimization
from optics_engine import evaluate_system, load_system


FIELDS = [
    {"id": "center", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
    {"id": "edge", "theta_y_deg": 2.0, "theta_z_deg": 0.0},
]
SAMPLING = {
    "samples_per_field": 9,
    "pupil_distribution": "grid",
    "ray_aiming": {"mode": "full"},
}
EVALUATION = {
    "preset": "fast_design_score",
    "fields": FIELDS,
    "wavelengths": [587.56],
}


def trace_sharing_system():
    return load_system(
        {
            "name": "R102 trace sharing",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
                    "thickness_after_mm": 0.0,
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "focal_length_mm": 100.0,
                    "semi_diameter_mm": 5.0,
                    "thickness_after_mm": 95.0,
                },
                {
                    "id": "IMG",
                    "kind": "sensor",
                    "sensor": {"width_mm": 40.0, "height_mm": 30.0},
                },
            ],
        }
    )


def test_fast_design_score_shares_rms_mtf_and_ray_loss_trace(monkeypatch):
    calls = 0
    original = optimization.trace_forward

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(optimization, "trace_forward", counted)
    result = evaluate_system(trace_sharing_system(), EVALUATION, ray_sampling=SAMPLING)

    assert result.status == "ok"
    assert calls == 1


def test_trace_cache_reuses_only_completely_identical_conditions(monkeypatch):
    calls = 0
    sentinel = object()

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return sentinel

    monkeypatch.setattr(optimization, "trace_forward", counted)
    context = optimization._EvaluationTraceContext()
    compiled = optimization.compile_system(trace_sharing_system())
    base = (compiled, FIELDS, SAMPLING, [587.56], {"configuration": {}})

    assert context.trace(*base) is sentinel
    assert context.trace(*(deepcopy(item) for item in base)) is sentinel
    context.trace(compiled, [{**FIELDS[0], "theta_y_deg": 1.0}], SAMPLING, [587.56], {"configuration": {}})
    context.trace(compiled, FIELDS, {**SAMPLING, "samples_per_field": 10}, [587.56], {"configuration": {}})
    context.trace(compiled, FIELDS, SAMPLING, [486.13], {"configuration": {}})
    context.trace(compiled, FIELDS, SAMPLING, [587.56], {"configuration": {"zoom_position": 1}})
    context.trace(
        compiled,
        FIELDS,
        {**SAMPLING, "ray_aiming": {"mode": "paraxial"}},
        [587.56],
        {"configuration": {}},
    )

    assert calls == 6


def test_cached_evaluate_result_is_bit_identical_to_uncached(monkeypatch):
    cached = evaluate_system(trace_sharing_system(), EVALUATION, ray_sampling=SAMPLING)
    original = optimization.trace_forward

    def uncached(self, compiled, fields, sampling, wavelengths, options):
        return original(compiled, fields, sampling, wavelengths, options)

    monkeypatch.setattr(optimization._EvaluationTraceContext, "trace", uncached)
    uncached_result = evaluate_system(trace_sharing_system(), EVALUATION, ray_sampling=SAMPLING)

    assert asdict(cached) == asdict(uncached_result)


def test_jacobian_candidates_do_not_reuse_base_trace(monkeypatch):
    cached = evaluate_system(
        trace_sharing_system(),
        EVALUATION,
        ray_sampling=SAMPLING,
        jacobian={"mode": "forward_diff", "variables": ["TL_focal_length_mm"], "steps": {"TL_focal_length_mm": 1.0}},
    )
    original = optimization.trace_forward

    def uncached(self, compiled, fields, sampling, wavelengths, options):
        return original(compiled, fields, sampling, wavelengths, options)

    monkeypatch.setattr(optimization._EvaluationTraceContext, "trace", uncached)
    uncached_result = evaluate_system(
        trace_sharing_system(),
        EVALUATION,
        ray_sampling=SAMPLING,
        jacobian={"mode": "forward_diff", "variables": ["TL_focal_length_mm"], "steps": {"TL_focal_length_mm": 1.0}},
    )

    assert cached.jacobian is not None
    assert uncached_result.jacobian is not None
    assert cached.operands == uncached_result.operands
    assert cached.jacobian.residuals == uncached_result.jacobian.residuals
    assert cached.jacobian.matrix == uncached_result.jacobian.matrix
    assert cached.jacobian.columns == uncached_result.jacobian.columns
    assert any(abs(float(row[0])) > 0.0 for row in cached.jacobian.matrix)
