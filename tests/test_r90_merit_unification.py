from __future__ import annotations

from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from optics_engine import evaluate_batch, evaluate_system, load_system, meta_payload
from optics_engine.api.main import app
from optics_engine.optimization import PRESETS


def system():
    return load_system(
        {
            "name": "R90 merit fixture",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 4.0},
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "focal_length_mm": 100.0,
                    "semi_diameter_mm": 5.0,
                    "thickness_after_mm": 95.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
            "groups": [{"id": "LENS", "from_surface": "TL", "to_surface": "TL"}],
        }
    )


def derived_score(result) -> float:
    return sum(float(operand.residual or 0.0) ** 2 for operand in result.operands) + float(
        result.merit.metrics["hard_penalty"]
    )


@pytest.mark.parametrize("preset", sorted(PRESETS))
def test_all_presets_expand_to_operands_and_share_merit_derivation(preset: str):
    result = evaluate_system(system(), {"preset": preset})

    assert result.status == "ok"
    assert result.merit.definition == "sum_of_squared_residuals_plus_penalties"
    assert result.merit.score == pytest.approx(derived_score(result), abs=1.0e-15)
    assert result.metadata["expanded_operands"] == PRESETS[preset]["operands"]
    assert result.legacy_merit is not None
    assert result.legacy_merit.definition == "legacy_linear_weighted_score"
    assert result.metadata["deprecations"][0]["field"] == "legacy_merit"


def test_evaluate_and_batch_use_identical_merit_derivation():
    evaluation = {
        "operands": [{"metric": "rms_spot_radius", "target": 0.0, "tolerance": 0.5, "weight": 2.0}],
        "ray_loss_tolerance": 0.2,
    }
    direct = evaluate_system(system(), evaluation, variables={"TL_focal_length_mm": 90.0})
    batch = evaluate_batch(
        system(),
        [{"id": "candidate", "variables": {"TL_focal_length_mm": 90.0}}],
        evaluation,
    ).candidates[0].result

    assert asdict(direct) == asdict(batch)
    assert direct.merit.score == pytest.approx(derived_score(direct), abs=1.0e-15)


def test_infeasible_ray_loss_and_constraint_penalties_follow_common_derivation():
    infeasible = evaluate_system(
        system(),
        {"preset": "spot_only"},
        configuration={"group_positions": {"LENS": {"shift_x_mm": -10.0}}},
    )
    assert infeasible.status == "infeasible"
    assert infeasible.merit.score == infeasible.merit.metrics["hard_penalty"]
    assert infeasible.merit.metrics["constraint_penalty"] > 0.0

    penalized = evaluate_system(
        system(),
        {
            "operands": [
                {"metric": "rms_spot_radius", "target": 0.0, "tolerance": 1.0},
                {"metric": "min_air_gap", "target": 1.0, "tolerance": 0.5, "one_sided": "lower"},
            ],
            "ray_loss_statuses": ["blocked"],
            "ray_loss_tolerance": 0.1,
        },
        ray_sampling={"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "off"}},
    )
    assert penalized.merit.metrics["ray_loss_penalty"] >= 0.0
    assert penalized.merit.metrics["continuous_constraint_penalty"] > 0.0
    assert penalized.merit.score == pytest.approx(derived_score(penalized), abs=1.0e-15)


def test_http_evaluate_and_batch_expose_legacy_merit_and_schema_transition():
    payload = system().model_dump(mode="json")
    payload["evaluation"] = {"preset": "spot_only"}
    direct = TestClient(app).post("/v1/optics/evaluate", json=payload)
    assert direct.status_code == 200
    assert direct.json()["legacy_merit"]["definition"] == "legacy_linear_weighted_score"

    batch = TestClient(app).post(
        "/v1/optics/evaluate-batch",
        json={"base_system": system().model_dump(mode="json"), "evaluation": {"preset": "spot_only"}, "candidates": [{"id": "a"}]},
    )
    assert batch.status_code == 200
    assert batch.json()["candidates"][0]["result"]["legacy_merit"] is not None
    assert meta_payload()["api_schema_version"] == "2.5.0"


def test_one_sided_operand_is_zero_on_satisfied_side():
    result = evaluate_system(
        system(),
        {
            "operands": [
                {
                    "metric": "back_focal_length",
                    "target": 90.0,
                    "tolerance": 1.0,
                    "weight": 2.0,
                    "one_sided": "lower",
                }
            ]
        },
    )
    assert result.operands[0].value >= 90.0
    assert result.operands[0].residual == 0.0
