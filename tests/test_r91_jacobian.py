from __future__ import annotations

from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient

from optics_engine import evaluate_system, load_system, trace_forward, compile_system
from optics_engine.api.main import app
from optics_engine.artifacts import ARTIFACT_STORE, ArtifactStore
from optics_engine.evaluation_metrics import SUPPORTED_EVALUATE_METRICS
from optics_engine.optimization import _evaluate_with_jacobian, _matrix_payload
from optics_engine.tracing import _AIMING_AFFINE_CACHE
from optics_engine.variables import resolve_variable_binding


def aspheric_system():
    return load_system(
        {
            "name": "R91 aspheric singlet",
            "wavelengths_nm": {"primary": 587.56, "samples": [587.56]},
            "materials": [
                {"id": "AIR", "type": "constant", "n": 1.0},
                {"id": "GLASS", "type": "constant", "n": 1.5168},
            ],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "surface_type": "plane",
                    "thickness_after_mm": 2.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
                },
                {
                    "id": "S1",
                    "kind": "refractive",
                    "surface_type": "aspherical_even",
                    "radius_mm": 50.0,
                    "conic": -0.25,
                    "asphere_coefficients": {"A4": 1.0e-8, "A6": 1.0e-12, "A8": 1.0e-16},
                    "thickness_after_mm": 5.0,
                    "material_after": "GLASS",
                    "semi_diameter_mm": 10.0,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "radius_mm": -50.0,
                    "thickness_after_mm": 46.5,
                    "material_after": "AIR",
                    "semi_diameter_mm": 10.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
            "groups": [{"id": "LENS", "from_surface": "S1", "to_surface": "S2"}],
        }
    )


def evaluation():
    return {
        "operands": [
            {"metric": "rms_spot_radius", "target": 0.0, "tolerance": 0.1},
            {"metric": "back_focal_length", "target": 48.0, "tolerance": 1.0},
        ],
        "fields": [{"id": "edge", "theta_y_deg": 3.0, "theta_z_deg": 0.0}],
        "wavelengths": [587.56],
        "ray_loss_tolerance": 0.1,
    }


def sampling(samples: int = 9):
    return {
        "samples_per_field": samples,
        "pupil_distribution": "grid",
        "ray_aiming": {"mode": "full", "strategy": "exact", "tolerance_mm": 1.0e-6, "max_iterations": 20},
    }


def request(mode: str = "central_diff"):
    return {
        "mode": mode,
        "variables": ["S1_curvature", "S1_conic", "S1_A4", "LENS_shift_x_mm", "iris_radius_mm"],
    }


def test_jacobian_api_returns_required_shape_and_all_variable_kinds():
    result = evaluate_system(aspheric_system(), evaluation(), ray_sampling=sampling(), jacobian=request())

    assert result.status == "ok"
    assert result.jacobian is not None
    assert result.jacobian.status == "ok"
    assert result.jacobian.mode == "central_diff"
    assert result.jacobian.variables == request()["variables"]
    assert result.jacobian.matrix_shape == [len(result.operands), 5]
    assert isinstance(result.jacobian.matrix, list)
    assert all(column.scheme_used == "central" for column in result.jacobian.columns)
    assert result.jacobian.metadata["strategy"] == "candidate_axis_batch"
    assert result.jacobian.metadata["candidate_batch_trace_calls"] > 0
    assert result.jacobian.metadata["candidate_batch_fallback_calls"] == 0
    assert result.jacobian.metadata["global_cache_write"] is False
    assert result.jacobian.steps_used["S1_A4"] >= 1.0e-12

    payload = aspheric_system().model_dump(mode="json")
    payload.update({"evaluation": evaluation(), "ray_sampling": sampling(), "jacobian": request("forward_diff")})
    response = TestClient(app).post("/v1/optics/evaluate", json=payload)
    assert response.status_code == 200
    body = response.json()["jacobian"]
    assert body["mode"] == "forward_diff"
    assert body["matrix_shape"] == [len(response.json()["operands"]), 5]


def test_warm_refinement_matches_independent_exact_oracle_and_does_not_fill_global_cache():
    _AIMING_AFFINE_CACHE.clear()
    warm = evaluate_system(aspheric_system(), evaluation(), ray_sampling=sampling(), jacobian=request())
    oracle = _evaluate_with_jacobian(
        aspheric_system(),
        evaluation(),
        configuration=None,
        variables=None,
        ray_sampling=sampling(),
        jacobian=request(),
        warm_refinement=False,
    )

    assert len(_AIMING_AFFINE_CACHE) == 0
    assert warm.jacobian.metadata["strategy"] == "candidate_axis_batch"
    assert oracle.jacobian.metadata["strategy"] == "independent_exact"
    assert warm.jacobian.metadata["warm_seeded_solves"] > 0
    assert warm.jacobian.residuals == pytest.approx(oracle.jacobian.residuals, abs=1.0e-6, rel=1.0e-8)
    assert np.asarray(warm.jacobian.matrix) == pytest.approx(
        np.asarray(oracle.jacobian.matrix), abs=1.0e-6, rel=1.0e-3
    )
    assert [column.scheme_used for column in warm.jacobian.columns] == [
        column.scheme_used for column in oracle.jacobian.columns
    ]


def test_warm_origins_status_targets_and_sensor_coordinates_match_cold_exact():
    base_workspace = {}
    base_sampling = sampling()
    base_sampling["ray_aiming"] = {
        **base_sampling["ray_aiming"],
        "_request_local_workspace": base_workspace,
        "_workspace_role": "base",
        "_candidate_id": "base",
    }
    trace_forward(
        compile_system(aspheric_system()),
        evaluation()["fields"],
        base_sampling,
        [587.56],
    )
    perturbed = aspheric_system()
    next(surface for surface in perturbed.surfaces if surface.id == "S1").radius_mm = 49.95

    warm_sampling = sampling()
    warm_sampling["ray_aiming"] = {
        **warm_sampling["ray_aiming"],
        "_request_local_workspace": base_workspace,
        "_workspace_role": "candidate",
        "_candidate_id": "warm",
    }
    warm_trace = trace_forward(compile_system(perturbed), evaluation()["fields"], warm_sampling, [587.56])

    cold_workspace = {}
    cold_sampling = sampling()
    cold_sampling["ray_aiming"] = {
        **cold_sampling["ray_aiming"],
        "_request_local_workspace": cold_workspace,
        "_workspace_role": "base",
        "_candidate_id": "cold",
    }
    cold_trace = trace_forward(compile_system(perturbed), evaluation()["fields"], cold_sampling, [587.56])
    warm_diag = base_workspace["diagnostics"][-1]
    cold_diag = cold_workspace["diagnostics"][-1]

    assert np.array_equal(warm_trace.status, cold_trace.status)
    assert np.array_equal(warm_diag["ok"], cold_diag["ok"])
    assert np.array_equal(warm_diag["targets"], cold_diag["targets"])
    assert np.allclose(warm_trace.origins[:, 1:3], cold_trace.origins[:, 1:3], atol=2.0e-6, rtol=0.0)
    assert np.allclose(warm_trace.sensor_y_mm, cold_trace.sensor_y_mm, atol=2.0e-6, rtol=0.0, equal_nan=True)
    assert np.allclose(warm_trace.sensor_z_mm, cold_trace.sensor_z_mm, atol=2.0e-6, rtol=0.0, equal_nan=True)


def test_invalid_warm_seed_falls_back_per_ray_to_cold_exact():
    workspace = {}
    base_sampling = sampling()
    base_sampling["ray_aiming"] = {
        **base_sampling["ray_aiming"],
        "_request_local_workspace": workspace,
        "_workspace_role": "base",
        "_candidate_id": "base",
    }
    compiled = compile_system(aspheric_system())
    trace_forward(compiled, evaluation()["fields"], base_sampling, [587.56])
    for origins in workspace["base_origins"].values():
        origins[:, 1:3] += 1000.0

    warm_sampling = sampling()
    warm_sampling["ray_aiming"] = {
        **warm_sampling["ray_aiming"],
        "_request_local_workspace": workspace,
        "_workspace_role": "candidate",
        "_candidate_id": "bad-seed",
    }
    recovered = trace_forward(compiled, evaluation()["fields"], warm_sampling, [587.56])
    cold = trace_forward(compiled, evaluation()["fields"], sampling(), [587.56])
    diagnostic = workspace["diagnostics"][-1]
    assert np.any(diagnostic["cold_fallback"])
    assert np.array_equal(recovered.status, cold.status)
    assert np.array_equal(recovered.origins, cold.origins)
    assert np.array_equal(recovered.sensor_y_mm, cold.sensor_y_mm)
    assert np.array_equal(recovered.sensor_z_mm, cold.sensor_z_mm)


def test_jacobian_is_bit_identical_across_cache_histories():
    def run():
        return evaluate_system(aspheric_system(), evaluation(), ray_sampling=sampling(), jacobian=request("forward_diff"))

    _AIMING_AFFINE_CACHE.clear()
    cold = run()
    for count in (9, 25, 81):
        trace_forward(
            compile_system(aspheric_system()),
            [{"id": "other", "theta_y_deg": 1.0, "theta_z_deg": 0.5}],
            sampling(count),
            [587.56],
            {"configuration": {"variables": {"iris_radius_mm": 4.5}}},
        )
    changed_history = run()
    repeated = run()

    assert asdict(cold.jacobian) == asdict(changed_history.jacobian) == asdict(repeated.jacobian)


def test_central_difference_uses_forward_fallback_at_hard_boundary():
    result = evaluate_system(
        aspheric_system(),
        evaluation(),
        ray_sampling=sampling(),
        jacobian={"mode": "central_diff", "variables": ["S1_semi_diameter_mm"], "steps": {"S1_semi_diameter_mm": 11.0}},
    )
    assert result.jacobian.status == "ok"
    assert result.jacobian.columns[0].scheme_used == "forward_fallback"
    assert result.jacobian.columns[0].violations
    assert all(row[0] is not None for row in result.jacobian.matrix)


def test_both_hard_infeasible_sides_return_partial_failed_column_without_nan():
    bounded = aspheric_system()
    next(surface for surface in bounded.surfaces if surface.id == "STOP").thickness_after_mm = 0.5
    next(surface for surface in bounded.surfaces if surface.id == "S2").thickness_after_mm = 0.5
    result = evaluate_system(
        bounded,
        evaluation(),
        ray_sampling=sampling(),
        jacobian={"mode": "central_diff", "variables": ["LENS_shift_x_mm"], "steps": {"LENS_shift_x_mm": 1.0}},
    )
    assert result.status == "ok"
    assert result.jacobian.status == "partial"
    assert result.jacobian.columns[0].scheme_used == "failed"
    assert result.jacobian.columns[0].violations
    assert all(row[0] is None for row in result.jacobian.matrix)


def test_soft_vignetting_status_change_remains_a_differentiable_ray_loss_column():
    vignetted = aspheric_system()
    next(surface for surface in vignetted.surfaces if surface.id == "S1").semi_diameter_mm = 4.5
    result = evaluate_system(
        vignetted,
        {**evaluation(), "ray_loss_statuses": ["blocked"]},
        ray_sampling=sampling(25),
        jacobian={"mode": "central_diff", "variables": ["S1_semi_diameter_mm"], "steps": {"S1_semi_diameter_mm": 0.75}},
    )
    ray_loss_rows = [index for index, operand in enumerate(result.operands) if operand.metric == "ray_loss_ratio"]
    assert result.jacobian.columns[0].scheme_used == "central"
    assert ray_loss_rows
    assert any(abs(result.jacobian.matrix[index][0]) > 0.0 for index in ray_loss_rows)


def test_tir_boundary_status_change_remains_a_soft_ray_loss_column():
    tir_system = aspheric_system()
    next(surface for surface in tir_system.surfaces if surface.id == "S2").radius_mm = -6.0
    result = evaluate_system(
        tir_system,
        {
            **evaluation(),
            "fields": [{"id": "edge", "theta_y_deg": 10.0, "theta_z_deg": 0.0}],
            "ray_loss_statuses": ["total_internal_reflection"],
        },
        ray_sampling=sampling(25),
        jacobian={"mode": "central_diff", "variables": ["S2_radius_mm"], "steps": {"S2_radius_mm": 0.5}},
    )
    ray_loss_rows = [index for index, operand in enumerate(result.operands) if operand.metric == "ray_loss_ratio"]
    assert result.status == "ok"
    assert result.jacobian.columns[0].scheme_used == "central"
    assert ray_loss_rows
    assert any(abs(result.jacobian.matrix[index][0]) > 0.0 for index in ray_loss_rows)


def test_forward_and_central_difference_show_expected_convergence_order():
    smooth_evaluation = {
        "operands": [{"metric": "back_focal_length", "target": 48.0, "tolerance": 1.0}],
        "fields": [{"id": "center", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        "wavelengths": [587.56],
    }

    def derivative(mode: str, step: float) -> float:
        result = evaluate_system(
            aspheric_system(),
            smooth_evaluation,
            ray_sampling={"samples_per_field": 3, "ray_aiming": {"mode": "paraxial"}},
            jacobian={"mode": mode, "variables": ["S1_curvature"], "steps": {"S1_curvature": step}},
        )
        return float(result.jacobian.matrix[0][0])

    reference = derivative("central_diff", 1.0e-7)
    forward_errors = [abs(derivative("forward_diff", step) - reference) for step in (1.0e-4, 5.0e-5)]
    central_errors = [abs(derivative("central_diff", step) - reference) for step in (1.0e-4, 5.0e-5)]
    assert forward_errors[1] < 0.65 * forward_errors[0]
    assert central_errors[1] < 0.4 * central_errors[0]


def test_asphere_default_step_floors_cover_p009_and_p010_value_ranges():
    values = {"A4": [-2.4992e-6, -1.0e-4], "A6": [5.0e-7], "A8": [-5.0e-10]}
    system = aspheric_system()
    for coefficient, coefficient_values in values.items():
        binding = resolve_variable_binding(system, f"S1_{coefficient}")
        for value in coefficient_values:
            step = binding.default_step(value)
            assert value + step != value
            assert step >= binding.default_step_floor


def test_all_connected_operand_metrics_are_available_to_jacobian():
    operands = [
        {
            "metric": metric,
            "target": 1.0 if metric in {"relative_illumination", "geometric_mtf", "white_mtf"} else 0.0,
            "tolerance": 1.0,
        }
        for metric in SUPPORTED_EVALUATE_METRICS
    ]
    result = evaluate_system(
        aspheric_system(),
        {
            "operands": operands,
            "fields": [{"id": "edge", "theta_y_deg": 2.0, "theta_z_deg": 0.0}],
            "wavelengths": [486.13, 587.56, 656.27],
            "frequencies_lp_per_mm": [10.0],
            "field_curvature_method": "rms_search",
        },
        ray_sampling={"samples_per_field": 3, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        jacobian={"mode": "forward_diff", "variables": ["S1_curvature"]},
    )
    assert result.jacobian.status == "ok"
    assert {operand.metric for operand in result.operands} >= set(SUPPORTED_EVALUATE_METRICS)
    assert result.jacobian.matrix_shape == [len(result.operands), 1]
    assert all(row[0] is not None for row in result.jacobian.matrix)


@pytest.mark.parametrize(
    "jacobian",
    [
        {"mode": "bad", "variables": ["S1_curvature"]},
        {"variables": []},
        {"variables": ["S1_curvature", "S1_curvature"]},
        {"variables": ["S1_unknown"]},
        {"variables": ["S1_curvature"], "unknown": True},
    ],
)
def test_invalid_jacobian_requests_are_structured_400(jacobian):
    payload = aspheric_system().model_dump(mode="json")
    payload.update({"evaluation": evaluation(), "ray_sampling": sampling(), "jacobian": jacobian})
    response = TestClient(app).post("/v1/optics/evaluate", json=payload)
    assert response.status_code == 400
    assert response.json()["code"] == "optics_value_error"
    assert response.json()["params"]["location"] == "jacobian"


def test_nonfinite_jacobian_step_is_rejected_by_library_validation():
    with pytest.raises(Exception) as error:
        evaluate_system(
            aspheric_system(),
            evaluation(),
            ray_sampling=sampling(),
            jacobian={"variables": ["S1_curvature"], "steps": {"S1_curvature": float("nan")}},
        )
    assert getattr(error.value, "code", None) == "optics_value_error"
    assert error.value.params["location"] == "jacobian"


def test_large_matrix_artifact_is_content_addressed_and_concurrent_put_is_safe():
    matrix = [[float(index)] for index in range(1001)]
    signature = {"request": "same"}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: _matrix_payload(matrix, signature), range(8)))
    uris = {result[0] for result in results}
    assert len(uris) == 1
    uri = next(iter(uris))
    assert uri.startswith("artifact://jacobian/jac_")
    artifact = ARTIFACT_STORE.get("jacobian", uri.rsplit("/", 1)[-1])
    assert artifact is not None
    loaded = np.load(io.BytesIO(artifact.content), allow_pickle=False)
    assert loaded.shape == (1001, 1)
    assert np.array_equal(loaded[:, 0], np.arange(1001, dtype=float))
    response = TestClient(app).get(f"/v1/artifacts/jacobian/{artifact.id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-npy")


def test_candidate_batch_parallel_calls_and_artifact_ttl_remain_safe(tmp_path):
    def evaluate():
        return evaluate_system(
            aspheric_system(),
            evaluation(),
            ray_sampling=sampling(),
            jacobian={"mode": "forward_diff", "variables": ["S1_curvature", "S1_conic", "S1_A4"]},
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: evaluate(), range(4)))
    payloads = [asdict(result.jacobian) for result in results]
    assert payloads[1:] == [payloads[0]] * 3
    assert all(result.jacobian.metadata["candidate_batch_trace_calls"] > 0 for result in results)

    store = ArtifactStore(ttl_seconds=0.1, root_dir=tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        artifacts = list(
            pool.map(
                lambda index: store.put("jacobian", f"matrix-{index}".encode(), id=f"batch-{index}"),
                range(4),
            )
        )
    assert all(store.get(artifact.category, artifact.id) is not None for artifact in artifacts)
    import time

    time.sleep(0.15)
    assert all(store.get_with_status(artifact.category, artifact.id)[1] == "expired" for artifact in artifacts)
