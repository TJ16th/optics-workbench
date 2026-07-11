from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from optics_engine import analyze_paraxial, compile_system, load_system, trace_forward


ROOT = Path(__file__).resolve().parents[1]
PRESETS_PATH = ROOT / "apps" / "workbench-ui" / "src" / "domain" / "presets.ts"
NODE_PRESET_LOADER = r"""
const fs = require('fs');
const ts = require('typescript');
const source = fs.readFileSync(process.argv[1], 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const module = { exports: {} };
new Function('exports', 'module', 'require', js)(module.exports, module, require);
console.log(JSON.stringify(module.exports.presets.map(({ id, system, recommendedFields }) => ({ id, system, recommendedFields }))));
"""


def _shipped_presets() -> list[dict[str, Any]]:
    node = shutil.which("node") or shutil.which("node.exe")
    if node is None:
        pytest.skip("Node.js is required to load the shipped UI preset catalog")
    completed = subprocess.run(
        [node, "-e", NODE_PRESET_LOADER, str(PRESETS_PATH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _assert_json_finite_or_null(value: Any) -> None:
    if isinstance(value, float):
        assert math.isfinite(value)
    elif isinstance(value, dict):
        for item in value.values():
            _assert_json_finite_or_null(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_finite_or_null(item)


def _trace_payload(system_id: str, wavelengths_nm: list[float], aiming_mode: str = "paraxial") -> dict[str, Any]:
    return {
        "system_id": system_id,
        "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        "wavelengths_nm": wavelengths_nm,
        "ray_sampling": {
            "samples_per_field": 9,
            "pupil_distribution": "hexapolar",
            "ray_aiming": {"mode": aiming_mode},
        },
        "options": {"store_path": True},
    }


def test_shipped_presets_trace_and_preview_return_json_safe_payloads():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    client = TestClient(app)
    presets = _shipped_presets()
    assert presets
    for preset in presets:
        registered = client.post("/v1/systems/register", json=preset["system"])
        assert registered.status_code == 200, f"{preset['id']} register: {registered.text}"
        payload = _trace_payload(registered.json()["system_id"], preset["system"]["wavelengths_nm"]["samples"])
        for endpoint in ("/v1/trace/forward", "/v1/education/preview"):
            response = client.post(endpoint, json=payload)
            assert response.status_code == 200, f"{preset['id']} {endpoint}: {response.text}"
            _assert_json_finite_or_null(response.json())


@pytest.mark.parametrize("preset_id", ["P005", "P006"])
@pytest.mark.parametrize("aiming_mode", ["full", "paraxial", "off"])
def test_p005_p006_trace_and_preview_support_all_aiming_modes_without_nan(preset_id: str, aiming_mode: str):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    preset = next(item for item in _shipped_presets() if item["id"] == preset_id)
    client = TestClient(app)
    registered = client.post("/v1/systems/register", json=preset["system"])
    assert registered.status_code == 200, f"{preset_id} register: {registered.text}"
    payload = _trace_payload(registered.json()["system_id"], preset["system"]["wavelengths_nm"]["samples"], aiming_mode)
    for endpoint in ("/v1/trace/forward", "/v1/education/preview"):
        response = client.post(endpoint, json=payload)
        assert response.status_code == 200, f"{preset_id} {aiming_mode} {endpoint}: {response.text}"
        body = response.json()
        _assert_json_finite_or_null(body)
        assert all(value is None or math.isfinite(value) for value in body["sensor_y_mm"])
        assert all(value is None or math.isfinite(value) for value in body["sensor_z_mm"])


@pytest.mark.parametrize(
    ("preset_id", "center_path"),
    [
        ("P005", ["M1", "M2", "IMG"]),
        ("P006", ["STOP", "OBJ", "EYEPIECE", "EYE"]),
    ],
)
def test_p005_p006_preview_returns_visible_baseline_paths(preset_id: str, center_path: list[str]):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    preset = next(item for item in _shipped_presets() if item["id"] == preset_id)
    client = TestClient(app)
    registered = client.post("/v1/systems/register", json=preset["system"])
    assert registered.status_code == 200, f"{preset_id} register: {registered.text}"
    payload = _trace_payload(registered.json()["system_id"], preset["system"]["wavelengths_nm"]["samples"], "full")
    payload["fields"] = [
        {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
        {"id": "edge-y", "type": "angular", "theta_y_deg": 10.0, "theta_z_deg": 0.0},
        {"id": "edge-z", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 10.0},
    ]
    payload["options"]["include_layout_baseline_rays"] = True
    response = client.post("/v1/education/preview", json=payload)
    assert response.status_code == 200, f"{preset_id} preview: {response.text}"
    baseline = response.json()["metadata"]["layout_baseline_rays"]
    assert len(baseline) == 9
    center = [ray for ray in baseline if ray["field_id"] == "center"]
    assert {ray["role"] for ray in center} == {"chief", "marginal_lower", "marginal_upper"}
    assert all([hit["surface_id"] for hit in ray["path"]] == center_path for ray in center)
    _assert_json_finite_or_null(baseline)


def test_shipped_preset_apertures_preserve_default_throughput_and_paraxial_results():
    expected_statuses = {
        "P001": {"alive": 27},
        "P002": {"alive": 81},
        "P003": {"alive": 81},
        "P005": {"alive": 9, "blocked": 18},
        "P006": {"alive": 1, "blocked": 26},
        "P007": {"alive": 81},
    }
    expected_paraxial = {
        "P001": (50.0, 50.0, 4.0),
        "P002": (49.21298867869991, 47.53621678328241, 3.0758117924187443),
        "P003": (93.14346592275818, 90.43162704589228, 4.657173296137909),
        "P005": (3000.0, 1050.0, None),
        "P006": (None, None, None),
        "P007": (519.6281203750518, 452.04242770474303, 19.682883347539843),
    }
    fields = [
        {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
        {"id": "edge-y", "type": "angular", "theta_y_deg": 10.0, "theta_z_deg": 0.0},
        {"id": "edge-z", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 10.0},
    ]
    for preset in _shipped_presets():
        compiled = compile_system(load_system(preset["system"]))
        trace = trace_forward(
            compiled,
            fields,
            {"samples_per_field": 9, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
            preset["system"]["wavelengths_nm"]["samples"],
        )
        statuses = {str(status): trace.status.tolist().count(status) for status in set(trace.status.tolist())}
        assert statuses == expected_statuses[preset["id"]]
        paraxial = analyze_paraxial(compiled)
        actual = (paraxial.effective_focal_length_mm, paraxial.back_focal_length_mm, paraxial.f_number)
        for value, expected in zip(actual, expected_paraxial[preset["id"]]):
            if expected is None:
                assert value is None
            else:
                assert value == pytest.approx(expected)


def test_shipped_focal_preset_mid_fields_use_seventy_percent_image_height():
    for preset in _shipped_presets():
        fields = preset["recommendedFields"]
        assert all(field["theta_z_deg"] == pytest.approx(0.0) for field in fields)
        if preset["id"] == "P006":
            assert fields[1]["theta_y_deg"] == pytest.approx(0.5)
            continue
        center, midpoint, edge = fields
        assert center["theta_y_deg"] == pytest.approx(0.0)
        expected_midpoint = math.degrees(math.atan(0.7 * math.tan(math.radians(edge["theta_y_deg"]))))
        assert midpoint["theta_y_deg"] == pytest.approx(expected_midpoint, abs=1.0e-6)


def test_seventy_percent_image_height_field_flows_through_preview_and_spot():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    preset = next(item for item in _shipped_presets() if item["id"] == "P001")
    client = TestClient(app)
    registered = client.post("/v1/systems/register", json=preset["system"])
    assert registered.status_code == 200, registered.text
    payload = _trace_payload(registered.json()["system_id"], preset["system"]["wavelengths_nm"]["samples"], "full")
    payload["fields"] = preset["recommendedFields"]

    preview = client.post("/v1/education/preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert [field["id"] for field in preview.json()["metadata"]["evaluated_fields"]] == ["center", "mid-y", "edge-y"]

    spot = client.post("/v1/analysis/spot", json=payload)
    assert spot.status_code == 200, spot.text
    assert spot.json()["arrived_count"] > 0
