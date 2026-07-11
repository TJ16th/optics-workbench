from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
PRESETS_PATH = ROOT / "apps" / "workbench-ui" / "src" / "domain" / "presets.ts"
NODE_PRESET_LOADER = r"""
const fs = require('fs');
const ts = require('typescript');
const source = fs.readFileSync(process.argv[1], 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const module = { exports: {} };
new Function('exports', 'module', 'require', js)(module.exports, module, require);
console.log(JSON.stringify(module.exports.presets.map(({ id, system }) => ({ id, system }))));
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
