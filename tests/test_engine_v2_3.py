from __future__ import annotations

import subprocess
import time

import pytest

from optics_engine import load_system, validate_system
from optics_engine.artifacts import ArtifactStore
from optics_engine.api import main as api_main
from optics_engine.metadata import ERROR_CODES, IMAGE_PLANE_POLICY_MODES, METRIC_CODES, RAY_STATUS_CODES, VARIABLE_KEY_PATTERNS, WARNING_CODES, meta_payload
from optics_engine.models import ValidationIssue


def system_without_stop():
    return load_system(
        {
            "name": "no stop",
            "surfaces": [
                {"id": "TL", "kind": "thin_lens", "surface_type": "plane", "focal_length_mm": 50.0, "thickness_after_mm": 50.0},
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def thin_lens_system():
    return load_system(
        {
            "name": "capability lens",
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 0.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
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
        }
    )


def test_validation_issue_accepts_legacy_inputs_but_serializes_v2_3_shape():
    issue = ValidationIssue(
        type="negative_air_gap",
        params={"surface_ids": ["S4", "S5"], "gap_mm": -0.35},
        message="Air gap between S4 and S5 is negative (-0.35 mm).",
        severity="error",
    )

    assert issue.code == "negative_air_gap"
    assert issue.type == "negative_air_gap"
    assert issue.message == issue.message_en

    payload = issue.model_dump(mode="json")
    assert payload["code"] == "negative_air_gap"
    assert payload["message_en"] == "Air gap between S4 and S5 is negative (-0.35 mm)."
    assert payload["params"]["gap_mm"] == pytest.approx(-0.35)
    assert "type" not in payload
    assert "message" not in payload


def test_validate_system_issues_are_code_based_with_structured_params():
    result = validate_system(system_without_stop())
    assert result.status == "warning"
    issue = result.issues[0]
    assert issue.code == "missing_aperture_stop"
    assert issue.severity == "warning"
    payload = result.model_dump(mode="json")
    assert payload["issues"][0]["code"] == "missing_aperture_stop"
    assert payload["issues"][0]["message_en"]
    assert "type" not in payload["issues"][0]
    assert "message" not in payload["issues"][0]


def test_meta_v2_3_enumerations_cover_stable_engine_identifiers():
    meta = meta_payload()
    assert meta["api_schema_version"] == "2.3.0"
    assert meta["result_schema_version"] == "2.3.0"
    build_info = meta["build_info"]
    expected_commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    assert build_info["git_commit"] == expected_commit
    assert isinstance(build_info["git_dirty"], bool)
    assert build_info["started_at"]
    capabilities = meta["capabilities"]
    assert capabilities["image_plane_policy_modes"] == IMAGE_PLANE_POLICY_MODES
    assert capabilities["artifacts"]["enabled"] is True
    assert capabilities["artifacts"]["ttl_seconds"] == pytest.approx(api_main.ARTIFACT_STORE.ttl_seconds)
    enumerations = meta["enumerations"]
    assert enumerations["metrics"] == METRIC_CODES
    assert enumerations["error_codes"] == ERROR_CODES
    assert enumerations["warning_codes"] == WARNING_CODES
    assert enumerations["ray_status_codes"] == RAY_STATUS_CODES
    assert enumerations["variable_key_patterns"] == VARIABLE_KEY_PATTERNS


def test_http_api_validation_and_error_responses_use_v2_3_error_shape():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    client = TestClient(app)
    validation = client.post("/v1/systems/validate", json=system_without_stop().model_dump(mode="json"))
    assert validation.status_code == 200
    issue = validation.json()["issues"][0]
    assert issue["code"] == "missing_aperture_stop"
    assert issue["message_en"]
    assert issue["severity"] == "warning"
    assert "type" not in issue
    assert "message" not in issue

    missing = client.post(
        "/v1/trace/forward",
        json={
            "system_id": "sha256:missing",
            "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        },
    )
    assert missing.status_code == 404
    assert missing.json() == {
        "severity": "error",
        "code": "system_not_found",
        "params": {"system_id": "sha256:missing"},
        "message_en": "Unknown or expired system_id.",
    }

    registered = client.post("/v1/systems/register", json=system_without_stop().model_dump(mode="json")).json()
    bad_policy = client.post(
        "/v1/analysis/spot",
        json={
            "system_id": registered["system_id"],
            "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
            "image_plane_policy": {"mode": "not_a_mode"},
        },
    )
    assert bad_policy.status_code == 400
    assert bad_policy.json()["code"] == "optics_value_error"
    assert bad_policy.json()["message_en"] == "unknown image_plane_policy mode 'not_a_mode'"

    afocal = client.post(
        "/v1/analysis/spot",
        json={
            "name": "afocal",
            "system_type": "afocal",
            "surfaces": [
                {"id": "TL1", "kind": "thin_lens", "focal_length_mm": 100.0, "thickness_after_mm": 150.0},
                {"id": "TL2", "kind": "thin_lens", "focal_length_mm": 50.0, "thickness_after_mm": 50.0},
                {"id": "EYE", "kind": "eye_reference", "eye": {"pupil_diameter_mm": 4.0}},
            ],
            "image_plane_policy": {"mode": "best_focus_rms"},
        },
    )
    assert afocal.status_code == 400
    assert afocal.json()["code"] == "image_plane_policy_not_applicable"
    assert afocal.json()["params"] == {"system_type": "afocal"}


def test_artifact_http_lifecycle_content_types_and_expiry(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    store = ArtifactStore(ttl_seconds=0.02, root_dir=tmp_path)
    monkeypatch.setattr(api_main, "ARTIFACT_STORE", store)
    client = TestClient(app)

    json_artifact = store.put("json", b"{\"ok\":true}", content_type="application/json", id="result")
    png_artifact = store.put("image", b"\x89PNG\r\n\x1a\n", content_type="image/png", id="plot")
    npy_artifact = store.put("array", b"\x93NUMPY", content_type="application/octet-stream", id="grid")

    for category, artifact_id, content_type in [
        (json_artifact.category, json_artifact.id, "application/json"),
        (png_artifact.category, png_artifact.id, "image/png"),
        (npy_artifact.category, npy_artifact.id, "application/octet-stream"),
    ]:
        response = client.get(f"/v1/artifacts/{category}/{artifact_id}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(content_type)
        assert "x-artifact-expires-at" in response.headers

    time.sleep(0.03)
    expired = client.get("/v1/artifacts/json/result")
    assert expired.status_code == 404
    assert expired.json()["code"] == "artifact_expired"

    missing = client.get("/v1/artifacts/json/missing")
    assert missing.status_code == 404
    assert missing.json()["code"] == "artifact_not_found"


def test_meta_image_plane_policy_modes_are_executable_http_capabilities():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    client = TestClient(app)
    system_id = client.post("/v1/systems/register", json=thin_lens_system().model_dump(mode="json")).json()["system_id"]
    modes = client.get("/v1/meta").json()["capabilities"]["image_plane_policy_modes"]

    for mode in modes:
        policy = {"mode": mode, "search": {"range_mm": 1.0, "tolerance_mm": 1.0e-3}}
        if mode == "custom_offset":
            policy["offset_mm"] = 0.25
        response = client.post(
            "/v1/analysis/spot",
            json={
                "system_id": system_id,
                "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
                "ray_sampling": {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
                "wavelengths_nm": [587.56],
                "image_plane_policy": policy,
            },
        )
        assert response.status_code == 200, (mode, response.text)
        evaluation_plane = response.json()["metadata"]["evaluation_plane"]
        assert evaluation_plane["policy_mode"] == mode
