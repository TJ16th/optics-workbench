from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import numpy as np

from optics_engine import analyze_afocal, analyze_angular_mtf, analyze_exit_pupil, analyze_paraxial, analyze_spot, compile_system, load_system, trace_forward
from optics_engine.core import asphere_sag_and_slope, reflect, surface_normals_for_surface


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
    return [preset for preset in json.loads(completed.stdout) if preset["id"].startswith("P")]


def _assert_json_finite_or_null(value: Any) -> None:
    if isinstance(value, float):
        assert math.isfinite(value)
    elif isinstance(value, dict):
        for item in value.values():
            _assert_json_finite_or_null(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_finite_or_null(item)


@pytest.mark.parametrize("preset_id", ["P009", "P010"])
def test_r87_aspheric_preset_variables_are_accepted_by_evaluate_api(preset_id: str):
    from fastapi.testclient import TestClient

    from optics_engine.api.main import app

    preset = next(item for item in _shipped_presets() if item["id"] == preset_id)
    variables = {
        "ASP1_curvature": 1.0 / 52.0,
        "ASP1_conic": -0.9,
        "ASP1_A4": -2.0e-6,
        "ASP1_A6": 1.0e-9,
        "ASP1_A8": -1.0e-12,
        "ASP1_A10": 1.0e-15,
        "iris_radius_mm": 7.5,
    }
    payload = {
        **preset["system"],
        "variables": variables,
        "evaluation": {
            "metrics": ["rms_spot_radius"],
            "fields": [preset["recommendedFields"][0]],
            "wavelengths": [587.56],
        },
        "ray_sampling": {"samples_per_field": 9, "ray_aiming": {"mode": "paraxial"}},
    }
    response = TestClient(app).post("/v1/optics/evaluate", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"


def test_r69_keeps_p006_p008_afocal_metrics_bit_identical():
    expected = {
        "P006": (-5.0, 10.0, 20.0, 5, 3.722743809616492e-15, 6.497413668604473e-14, 1.0),
        "P008": (-4.999999999909559, 2.400000000043412, 20.0, 21, 0.014371311382372567, 0.2508267067119125, 0.8131422715654928),
    }
    field = {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}
    sampling = {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
    for preset in (item for item in _shipped_presets() if item["id"] in expected):
        compiled = compile_system(load_system(preset["system"]), use_cache=False)
        pupil = analyze_exit_pupil(compiled)
        afocal = analyze_afocal(compiled, field, sampling)
        trace = trace_forward(compiled, [field], sampling, [587.56])
        mtf = analyze_angular_mtf(trace, [0.0, 10.0])
        actual = (
            pupil.angular_magnification,
            pupil.exit_pupil_diameter_mm,
            pupil.eye_relief_mm,
            afocal.arrived_count,
            afocal.angular_rms_deg,
            afocal.residual_divergence_diopter,
            mtf.points[1].mtf,
        )
        assert actual == expected[preset["id"]]


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
        ("P005", ["STOP", "M1", "M2", "IMG"]),
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
    if preset_id == "P005":
        by_role = {ray["role"]: ray for ray in center}
        assert [hit["surface_id"] for hit in by_role["chief"]["path"]] == ["STOP"]
        assert by_role["chief"]["status"] == "blocked"
        assert all(
            [hit["surface_id"] for hit in by_role[role]["path"]] == center_path
            for role in ("marginal_lower", "marginal_upper")
        )
    else:
        assert all([hit["surface_id"] for hit in ray["path"]] == center_path for ray in center)
    _assert_json_finite_or_null(baseline)


def test_shipped_preset_apertures_preserve_default_throughput_and_paraxial_results():
    expected_statuses = {
        "P001": {"alive": 27},
        "P002": {"alive": 81},
        "P003": {"alive": 81},
        "P004": {"alive": 81},
        "P005": {"alive": 9, "blocked": 18},
        "P006": {"alive": 1, "blocked": 26},
        "P007": {"alive": 81},
        "P008": {"alive": 27, "blocked": 54},
        "P009": {"alive": 81},
        "P010": {"alive": 81},
        "P011": {"alive": 81},
        "P012": {"alive": 81},
    }
    expected_paraxial = {
        "P001": (50.0, 50.0, 4.0),
        "P002": (49.21298867869991, 47.53621678328241, 3.0758117924187443),
        "P003": (93.14346592275818, 90.43162704589228, 4.657173296137909),
        "P004": (49.97771165851465, 36.88883243846924, 1.407822863620131),
        "P005": (3000.0, 1050.0, 15.0),
        "P006": (None, None, None),
        "P007": (47.953755611726336, 26.948477258301352, 1.816430136807816),
        "P008": (None, None, None),
        "P009": (49.21298867869991, 47.53621678328241, 3.0758117924187443),
        "P010": (49.21298867869991, 47.53621678328241, 3.0758117924187443),
        "P011": (49.98319335121228, 35.36298255546046, 1.4079772774989374),
        "P012": (49.9824925346071, 40.22239204035907, 2.8001396377931145),
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
            {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
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


def test_p008_real_achromatic_afocal_preset_metrics_and_throughput():
    preset = next(item for item in _shipped_presets() if item["id"] == "P008")
    system = preset["system"]
    powered = [surface for surface in system["surfaces"] if surface["kind"] in {"refractive", "thin_lens"}]
    assert len(powered) == 6
    assert all(surface["kind"] == "refractive" for surface in powered)
    assert {surface.get("material_after") for surface in powered} == {"AIR", "N-BK7", "N-F2"}

    compiled = compile_system(load_system(system))
    exit_pupil = analyze_exit_pupil(compiled)
    assert exit_pupil.angular_magnification == pytest.approx(-5.0, abs=1.0e-8)
    assert exit_pupil.exit_pupil_diameter_mm == pytest.approx(2.4, abs=1.0e-8)
    assert exit_pupil.eye_relief_mm == pytest.approx(20.0, abs=1.0e-9)

    afocal = analyze_afocal(
        compiled,
        preset["recommendedFields"][0],
        {"samples_per_field": 25, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
    )
    assert afocal.arrived_count == 25
    assert afocal.residual_divergence_diopter == pytest.approx(0.36818659544890275)

    trace = trace_forward(
        compiled,
        preset["recommendedFields"],
        {"samples_per_field": 25, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        system["wavelengths_nm"]["samples"],
        {"store_path": True},
    )
    assert trace.status.tolist() == ["alive"] * 225
    assert all([hit["surface_id"] for hit in path] == ["STOP", "O1", "O2", "O3", "E1", "E2", "E3", "EYE"] for path in trace.paths)


def test_p004_double_gauss_meets_fast_paraxial_target_and_positive_edge_thickness():
    preset = next(item for item in _shipped_presets() if item["id"] == "P004")
    compiled = compile_system(load_system(preset["system"]))
    paraxial = analyze_paraxial(compiled)
    assert paraxial.effective_focal_length_mm == pytest.approx(49.97771165851465)
    assert paraxial.back_focal_length_mm == pytest.approx(36.88883243846924)
    assert paraxial.f_number == pytest.approx(1.407822863620131)

    surfaces = {surface["id"]: surface for surface in preset["system"]["surfaces"]}

    def sag(radius: float, height: float) -> float:
        return radius - math.copysign(math.sqrt(radius * radius - height * height), radius)

    edge_thicknesses = []
    for first_id, second_id in (("S1", "S2"), ("S3", "S4"), ("S5", "S6"), ("S7", "S8")):
        first = surfaces[first_id]
        second = surfaces[second_id]
        height = min(float(first["semi_diameter_mm"]), float(second["semi_diameter_mm"]))
        edge_thicknesses.append(
            float(first["thickness_after_mm"])
            + sag(float(second["radius_mm"]), height)
            - sag(float(first["radius_mm"]), height)
        )
    assert edge_thicknesses == pytest.approx([1.8793140234, 0.5260050299, 1.0458656956, 2.8279097129], abs=1.0e-9)
    assert min(edge_thicknesses) > 0.5

    trace = trace_forward(
        compiled,
        preset["recommendedFields"],
        {"samples_per_field": 25, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        preset["system"]["wavelengths_nm"]["samples"],
    )
    assert trace.status.tolist().count("blocked") == 0
    assert trace.status.tolist().count("alive") == 219
    assert trace.status.tolist().count("aiming_failed") == 6

    center_trace = trace_forward(
        compiled,
        [preset["recommendedFields"][0]],
        {"samples_per_field": 81, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
        [587.56],
    )
    assert analyze_spot(center_trace).rms_radius_mm == pytest.approx(0.48432273992330394)


def test_p011_planar_double_gauss_has_six_positive_thickness_elements():
    preset = next(item for item in _shipped_presets() if item["id"] == "P011")
    compiled = compile_system(load_system(preset["system"]))
    paraxial = analyze_paraxial(compiled)
    assert paraxial.effective_focal_length_mm == pytest.approx(49.98319335121228)
    assert paraxial.back_focal_length_mm == pytest.approx(35.36298255546046)
    assert paraxial.f_number == pytest.approx(1.4079772774989374)

    surfaces = {surface["id"]: surface for surface in preset["system"]["surfaces"]}

    def sag(radius: float, height: float) -> float:
        return radius - math.copysign(math.sqrt(radius * radius - height * height), radius)

    pairs = (("S1", "S2"), ("S3", "C1"), ("C1", "S4"), ("S5", "C2"), ("C2", "S6"), ("S7", "S8"))
    edge_thicknesses = []
    for first_id, second_id in pairs:
        first = surfaces[first_id]
        second = surfaces[second_id]
        height = min(float(first["semi_diameter_mm"]), float(second["semi_diameter_mm"]))
        edge_thicknesses.append(
            float(first["thickness_after_mm"])
            + sag(float(second["radius_mm"]), height)
            - sag(float(first["radius_mm"]), height)
        )
    assert edge_thicknesses == pytest.approx(
        [1.9536128020, 2.2554058371, 0.3172397450, 0.8519806271, 2.1887196149, 2.8883476069],
        abs=1.0e-9,
    )
    assert min(edge_thicknesses) > 0.3

    trace = trace_forward(
        compiled,
        preset["recommendedFields"],
        {"samples_per_field": 25, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        preset["system"]["wavelengths_nm"]["samples"],
    )
    assert trace.status.tolist().count("blocked") == 0
    assert trace.status.tolist().count("alive") == 213
    assert trace.status.tolist().count("aiming_failed") == 12

    center_trace = trace_forward(
        compiled,
        [preset["recommendedFields"][0]],
        {"samples_per_field": 81, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
        [587.56],
    )
    assert center_trace.status.tolist() == ["alive"] * 81
    assert analyze_spot(center_trace).rms_radius_mm == pytest.approx(0.4653881107408963)


def test_p012_tessar_meets_f28_target_with_four_positive_thickness_elements():
    preset = next(item for item in _shipped_presets() if item["id"] == "P012")
    compiled = compile_system(load_system(preset["system"]))
    paraxial = analyze_paraxial(compiled)
    assert paraxial.effective_focal_length_mm == pytest.approx(49.9824925346071)
    assert paraxial.back_focal_length_mm == pytest.approx(40.22239204035907)
    assert paraxial.f_number == pytest.approx(2.8001396377931145)

    surfaces = {surface["id"]: surface for surface in preset["system"]["surfaces"]}

    def sag(radius: float, height: float) -> float:
        return radius - math.copysign(math.sqrt(radius * radius - height * height), radius)

    pairs = (("S1", "S2"), ("S3", "S4"), ("S5", "C1"), ("C1", "S6"))
    edge_thicknesses = []
    for first_id, second_id in pairs:
        first = surfaces[first_id]
        second = surfaces[second_id]
        height = min(float(first["semi_diameter_mm"]), float(second["semi_diameter_mm"]))
        edge_thicknesses.append(
            float(first["thickness_after_mm"])
            + sag(float(second["radius_mm"]), height)
            - sag(float(first["radius_mm"]), height)
        )
    assert edge_thicknesses == pytest.approx(
        [3.9114640350, 2.6019935228, 2.6316735242, 3.3170410440],
        abs=1.0e-9,
    )
    assert min(edge_thicknesses) > 2.5

    trace = trace_forward(
        compiled,
        preset["recommendedFields"],
        {"samples_per_field": 25, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        preset["system"]["wavelengths_nm"]["samples"],
    )
    assert trace.status.tolist() == ["alive"] * 225

    center_trace = trace_forward(
        compiled,
        [preset["recommendedFields"][0]],
        {"samples_per_field": 81, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
        [587.56],
    )
    assert center_trace.status.tolist() == ["alive"] * 81
    assert analyze_spot(center_trace).rms_radius_mm == pytest.approx(0.036968052965618795)


def test_p007_fast_meniscus_preserves_bright_paraxial_target_and_positive_edge_thickness():
    preset = next(item for item in _shipped_presets() if item["id"] == "P007")
    compiled = compile_system(load_system(preset["system"]))
    paraxial = analyze_paraxial(compiled)
    assert paraxial.effective_focal_length_mm == pytest.approx(47.953755611726336)
    assert paraxial.back_focal_length_mm == pytest.approx(26.948477258301352)
    assert paraxial.f_number == pytest.approx(1.816430136807816)

    s1, s2 = preset["system"]["surfaces"][:2]
    height = min(float(s1["semi_diameter_mm"]), float(s2["semi_diameter_mm"]))
    sag1 = float(s1["radius_mm"]) - math.sqrt(float(s1["radius_mm"]) ** 2 - height**2)
    sag2 = float(s2["radius_mm"]) - math.sqrt(float(s2["radius_mm"]) ** 2 - height**2)
    edge_thickness = float(s1["thickness_after_mm"]) + sag2 - sag1
    assert float(s1["radius_mm"]) > height
    assert edge_thickness == pytest.approx(1.1190132933115944)
    assert edge_thickness > 1.0

    trace = trace_forward(
        compiled,
        preset["recommendedFields"],
        {"samples_per_field": 9, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        preset["system"]["wavelengths_nm"]["samples"],
    )
    assert trace.status.tolist() == ["alive"] * 81


def test_p007_p008_clear_apertures_match_marginal_ray_review():
    presets = _shipped_presets()
    p007 = next(item for item in presets if item["id"] == "P007")
    p008 = next(item for item in presets if item["id"] == "P008")
    assert {surface["id"]: surface.get("semi_diameter_mm") for surface in p007["system"]["surfaces"]} == {
        "S1": 14.5,
        "S2": 14.5,
        "STOP": 13.2,
        "S3": 11.5,
        "S4": 10.25,
        "IMG": None,
    }
    assert {surface["id"]: surface.get("semi_diameter_mm") for surface in p008["system"]["surfaces"]} == {
        "STOP": 6.0,
        "O1": 6.75,
        "O2": 6.5,
        "O3": 6.5,
        "E1": 2.5,
        "E2": 2.5,
        "E3": 2.5,
        "EYE": None,
    }


def test_p009_aspheric_singlet_reduces_primary_wavelength_spherical_spot():
    presets = _shipped_presets()
    spherical = next(item for item in presets if item["id"] == "P002")
    aspheric = next(item for item in presets if item["id"] == "P009")
    asp1 = next(surface for surface in aspheric["system"]["surfaces"] if surface["id"] == "ASP1")
    assert asp1["surface_type"] == "aspherical_even"
    assert asp1["conic"] == pytest.approx(-1.1792)
    assert asp1["asphere_coefficients"] == {"A4": pytest.approx(-2.4992e-6)}

    sampling = {"samples_per_field": 81, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}}
    field = [aspheric["recommendedFields"][0]]
    spherical_trace = trace_forward(compile_system(load_system(spherical["system"])), field, sampling, [587.56])
    aspheric_trace = trace_forward(compile_system(load_system(aspheric["system"])), field, sampling, [587.56])
    spherical_rms = analyze_spot(spherical_trace).rms_radius_mm
    aspheric_rms = analyze_spot(aspheric_trace).rms_radius_mm
    assert spherical_rms == pytest.approx(0.04665818793319052)
    assert aspheric_rms == pytest.approx(0.0228093022785783)
    assert aspheric_rms < spherical_rms * 0.5

    throughput = trace_forward(
        compile_system(load_system(aspheric["system"])),
        aspheric["recommendedFields"],
        {"samples_per_field": 25, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        aspheric["system"]["wavelengths_nm"]["samples"],
    )
    assert throughput.status.tolist() == ["alive"] * 225


def test_p010_high_order_asphere_has_two_curvature_reversals_and_full_throughput():
    preset = next(item for item in _shipped_presets() if item["id"] == "P010")
    surface = next(item for item in preset["system"]["surfaces"] if item["id"] == "ASP1")
    assert surface["conic"] == pytest.approx(-1.0)
    assert surface["asphere_coefficients"] == {
        "A4": pytest.approx(-1.0e-4),
        "A6": pytest.approx(5.0e-7),
        "A8": pytest.approx(-5.0e-10),
    }

    radii = np.array([4.0, 5.0, 8.0, 8.5], dtype=float)
    delta = 1.0e-4
    _, slope_plus = asphere_sag_and_slope(
        radii + delta, surface["radius_mm"], surface["conic"], surface["asphere_coefficients"]
    )
    _, slope_minus = asphere_sag_and_slope(
        radii - delta, surface["radius_mm"], surface["conic"], surface["asphere_coefficients"]
    )
    curvature = (slope_plus - slope_minus) / (2.0 * delta)
    assert curvature.tolist() == pytest.approx([0.0045252852, -0.0010625122, -0.0027000317, 0.0010407135], abs=1.0e-9)

    compiled = compile_system(load_system(preset["system"]))
    paraxial = analyze_paraxial(compiled)
    assert paraxial.effective_focal_length_mm == pytest.approx(49.21298867869991)
    assert paraxial.back_focal_length_mm == pytest.approx(47.53621678328241)
    assert paraxial.f_number == pytest.approx(3.0758117924187443)

    trace = trace_forward(
        compiled,
        preset["recommendedFields"],
        {"samples_per_field": 25, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        preset["system"]["wavelengths_nm"]["samples"],
    )
    assert trace.status.tolist() == ["alive"] * 225
    assert np.nanmax(np.abs(trace.sensor_y_mm)) <= 12.0
    assert np.nanmax(np.abs(trace.sensor_z_mm)) <= 18.0

    center_trace = trace_forward(
        compiled,
        [preset["recommendedFields"][0]],
        {"samples_per_field": 81, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
        [587.56],
    )
    assert analyze_spot(center_trace).rms_radius_mm == pytest.approx(0.4646328343540561)


def test_p005_annular_stop_blocks_the_secondary_mirror_central_obscuration():
    preset = next(item for item in _shipped_presets() if item["id"] == "P005")
    stop = preset["system"]["surfaces"][0]
    assert stop["id"] == "STOP"
    assert stop["kind"] == "aperture_stop"
    assert stop["aperture"] == {
        "shape": "annulus",
        "inner_semi_diameter_mm": 40,
        "outer_semi_diameter_mm": 100,
    }

    compiled = compile_system(load_system(preset["system"]))
    assert compiled.surface_positions_mm == pytest.approx((0.0, 80.0, -570.0, 480.0))
    assert compiled.surface_positions_mm[2] - compiled.surface_positions_mm[1] == pytest.approx(-650.0)
    assert compiled.surface_positions_mm[3] - compiled.surface_positions_mm[2] == pytest.approx(1050.0)
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 9, "pupil_distribution": "hexapolar", "ray_aiming": {"mode": "full"}},
        [587.56],
        {"store_path": True, "include_layout_baseline_rays": True},
    )
    stop_points = [
        entry["local_point_mm"]
        for path in trace.paths
        for entry in path
        if entry["surface_id"] == "STOP"
    ]
    stop_radii = [math.hypot(point[1], point[2]) for point in stop_points]
    assert len(stop_radii) == 9
    assert all(40.0 - 1.0e-6 <= radius <= 100.0 + 1.0e-6 for radius in stop_radii)

    baseline = trace.metadata["layout_baseline_rays"]
    by_role = {ray["role"]: ray for ray in baseline}
    assert by_role["chief"]["stop_y_mm"] == pytest.approx(0.0, abs=1.0e-9)
    assert by_role["chief"]["status"] == "blocked"
    assert by_role["marginal_lower"]["stop_y_mm"] == pytest.approx(-100.0, abs=1.0e-6)
    assert by_role["marginal_upper"]["stop_y_mm"] == pytest.approx(100.0, abs=1.0e-6)
    assert [hit["surface_id"] for hit in by_role["chief"]["path"]] == ["STOP"]
    assert all(
        [hit["surface_id"] for hit in by_role[role]["path"]][:2] == ["STOP", "M1"]
        for role in ("marginal_lower", "marginal_upper")
    )


def test_p005_mirror_reflections_match_the_vector_reflection_law():
    preset = next(item for item in _shipped_presets() if item["id"] == "P005")
    compiled = compile_system(load_system(preset["system"]))
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 3, "pupil_distribution": "fan_y", "ray_aiming": {"mode": "full"}},
        [587.56],
        {"store_path": True},
    )
    for path in trace.paths:
        for path_index, surface_id in ((1, "M1"), (2, "M2")):
            surface_index = compiled.surface_index(surface_id)
            surface = compiled.surfaces[surface_index]
            point = np.asarray([path[path_index]["point_mm"]], dtype=float)
            radial_height = np.hypot(point[:, 1], point[:, 2])
            sag, _ = asphere_sag_and_slope(radial_height, surface.radius_mm, surface.conic, surface.asphere_coefficients)
            assert point[0, 0] == pytest.approx(compiled.surface_positions_mm[surface_index] + sag[0], abs=1.0e-9)
            incoming = np.asarray(path[path_index]["direction"], dtype=float)
            outgoing = np.asarray(path[path_index + 1]["direction"], dtype=float)
            normal = surface_normals_for_surface(point, compiled.surface_positions_mm[surface_index], surface)
            expected = reflect(incoming[None, :], normal)[0]
            assert outgoing == pytest.approx(expected, abs=1.0e-12)


def test_shipped_focal_preset_mid_fields_use_seventy_percent_image_height():
    for preset in _shipped_presets():
        fields = preset["recommendedFields"]
        assert all(field["theta_z_deg"] == pytest.approx(0.0) for field in fields)
        if preset["system"]["system_type"] == "afocal":
            assert fields[0]["theta_y_deg"] == pytest.approx(0.0)
            assert 0.0 < fields[1]["theta_y_deg"] < fields[2]["theta_y_deg"]
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
