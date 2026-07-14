from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from optics_engine.api.main import app


CLIENT = TestClient(app)


def system_payload() -> dict:
    return {
        "name": "R88 validation system",
        "wavelengths_nm": {"primary": 587.56, "samples": [486.13, 587.56, 656.27]},
        "materials": [
            {"id": "AIR", "type": "constant", "n": 1.0},
            {
                "id": "N-BK7",
                "type": "sellmeier",
                "B": [1.03961212, 0.231792344, 1.01046945],
                "C": [0.00600069867, 0.0200179144, 103.560653],
            },
        ],
        "surfaces": [
            {
                "id": "STOP",
                "kind": "aperture_stop",
                "surface_type": "plane",
                "thickness_after_mm": 2.0,
                "semi_diameter_mm": 5.0,
                "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
            },
            {
                "id": "S1",
                "kind": "refractive",
                "radius_mm": 50.0,
                "thickness_after_mm": 5.0,
                "material_after": "N-BK7",
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
    }


def registered_id() -> str:
    response = CLIENT.post("/v1/systems/register", json=system_payload())
    assert response.status_code == 200
    return response.json()["system_id"]


def trace_payload() -> dict:
    return {
        "system_id": registered_id(),
        "fields": [{"id": "edge", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0}],
        "ray_sampling": {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        "wavelengths_nm": [587.56],
    }


def assert_structured_400(response, *, code: str = "optics_value_error") -> dict:
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["severity"] == "error"
    assert body["code"] == code
    assert isinstance(body["params"], dict)
    assert body["message_en"]
    return body


def test_register_rejects_unknown_material_before_trace():
    payload = system_payload()
    payload["surfaces"][1]["material_after"] = "UNOBTANIUM"
    body = assert_structured_400(CLIENT.post("/v1/systems/register", json=payload), code="unknown_material")
    assert body["params"] == {"surface_id": "S1", "material_id": "UNOBTANIUM"}


def test_register_rejects_non_positive_surface_semi_diameter():
    payload = system_payload()
    payload["surfaces"][1]["semi_diameter_mm"] = -2.0
    body = assert_structured_400(CLIENT.post("/v1/systems/register", json=payload), code="invalid_semi_diameter")
    assert body["params"]["surface_id"] == "S1"


@pytest.mark.parametrize("wavelength_nm", [-587.56, 0.0, 10000.0])
def test_trace_rejects_invalid_or_unsupported_wavelength(wavelength_nm: float):
    payload = trace_payload()
    payload["wavelengths_nm"] = [wavelength_nm]
    body = assert_structured_400(CLIENT.post("/v1/trace/forward", json=payload))
    assert body["params"]["wavelength_nm"] == wavelength_nm


def test_unknown_ray_aiming_mode_is_not_silently_recorded():
    payload = trace_payload()
    payload["ray_sampling"]["ray_aiming"]["mode"] = "teleport"
    body = assert_structured_400(CLIENT.post("/v1/trace/forward", json=payload))
    assert body["params"]["ray_aiming_mode"] == "teleport"


@pytest.mark.parametrize(("key", "value"), [("metric", "banana_metric"), ("view", "impossible_view")])
def test_analysis_rejects_unknown_top_level_metric_and_view(key: str, value: str):
    payload = trace_payload()
    payload[key] = value
    body = assert_structured_400(CLIENT.post("/v1/analysis/spot", json=payload))
    assert body["params"]["parameter"] == key


@pytest.mark.parametrize(
    "configuration_key",
    ["configuration", "controls"],
)
def test_preview_rejects_negative_iris_from_both_supported_paths(configuration_key: str):
    payload = trace_payload()
    if configuration_key == "configuration":
        payload["configuration"] = {"variables": {"iris_radius_mm": -3.0}}
    else:
        payload["controls"] = {"iris_radius_mm": -3.0}
    body = assert_structured_400(CLIENT.post("/v1/education/preview", json=payload))
    assert body["params"]["iris_radius_mm"] == -3.0


def test_preview_controls_iris_is_connected_and_large_value_warns():
    baseline = trace_payload()
    baseline["options"] = {"store_path": True}
    default = CLIENT.post("/v1/education/preview", json=baseline)
    assert default.status_code == 200

    small = deepcopy(baseline)
    small["controls"] = {"iris_radius_mm": 2.0}
    changed = CLIENT.post("/v1/education/preview", json=small)
    assert changed.status_code == 200
    assert changed.json()["sensor_y_mm"] != default.json()["sensor_y_mm"]

    large = deepcopy(baseline)
    large["controls"] = {"iris_radius_mm": 1000.0}
    accepted = CLIENT.post("/v1/education/preview", json=large)
    assert accepted.status_code == 200
    warnings = accepted.json()["metadata"]["warnings"]
    assert any(warning["code"] == "iris_exceeds_clear_aperture" for warning in warnings)
