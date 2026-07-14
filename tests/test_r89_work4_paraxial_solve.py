from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from optics_engine import evaluate_system, load_system
from optics_engine.api.main import app


def system_payload() -> dict:
    return {
        "name": "R89 paraxial solve",
        "surfaces": [
            {"id": "STOP", "kind": "aperture_stop", "aperture": {"shape": "circle", "semi_diameter_mm": 5.0}},
            {"id": "TL", "kind": "thin_lens", "focal_length_mm": 50.0, "semi_diameter_mm": 5.0, "thickness_after_mm": 40.0},
            {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 20.0, "height_mm": 20.0}},
        ],
    }


def test_paraxial_image_distance_endpoint_solves_final_air_gap():
    client = TestClient(app)
    registration = client.post("/v1/systems/register", json=system_payload())
    assert registration.status_code == 200
    response = client.post(
        "/v1/solve/paraxial-image-distance",
        json={"system_id": registration.json()["system_id"], "thickness_of": "TL"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["previous_thickness_after_mm"] == pytest.approx(40.0)
    assert body["thickness_after_mm"] == pytest.approx(50.0)
    assert body["sensor_position_mm"] == pytest.approx(body["paraxial_image_position_mm"], abs=1.0e-12)
    assert body["converged"] is True


def test_evaluate_resolves_configuration_solve_before_tracing():
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
    unsolved = evaluate_system(load_system(system_payload()), {"metrics": ["rms_spot_radius"]}, ray_sampling=sampling)
    solved = evaluate_system(
        load_system(system_payload()),
        {"metrics": ["rms_spot_radius"]},
        configuration={"solves": [{"type": "paraxial_image_distance", "thickness_of": "TL"}]},
        ray_sampling=sampling,
    )
    assert solved.metrics["rms_spot_radius"] < unsolved.metrics["rms_spot_radius"]
    assert solved.configuration_resolved is not None
    assert solved.configuration_resolved["variables"]["TL_thickness_after_mm"] == pytest.approx(50.0)
    assert solved.configuration_resolved["resolved_solves"][0]["converged"] is True


def test_unknown_or_nonfinal_solve_target_returns_structured_400():
    client = TestClient(app)
    registration = client.post("/v1/systems/register", json=system_payload())
    system_id = registration.json()["system_id"]
    for thickness_of in ("NOPE", "STOP"):
        response = client.post(
            "/v1/solve/paraxial-image-distance",
            json={"system_id": system_id, "thickness_of": thickness_of},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "optics_value_error"
