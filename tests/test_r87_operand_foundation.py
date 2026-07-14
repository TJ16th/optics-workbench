from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from optics_engine import (
    analyze_chromatic_aberration,
    analyze_distortion,
    analyze_field_curvature,
    analyze_ms_image_surface,
    analyze_paraxial,
    analyze_white_mtf,
    compile_system,
    evaluate_system,
    load_system,
    meta_payload,
)
from optics_engine.api.main import app
from optics_engine.evaluation_metrics import SUPPORTED_EVALUATE_METRICS
from optics_engine.models import StructuredOpticsError
from optics_engine.variables import apply_variable_bindings, variable_key_patterns


def optical_system():
    return load_system(
        {
            "name": "R87 aspheric singlet",
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
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
                },
                {
                    "id": "S1",
                    "kind": "refractive",
                    "surface_type": "aspherical_even",
                    "radius_mm": 50.0,
                    "conic": -0.25,
                    "asphere_coefficients": {"A4": 1.0e-8},
                    "thickness_after_mm": 5.0,
                    "material_after": "N-BK7",
                    "semi_diameter_mm": 10.0,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "surface_type": "spherical",
                    "radius_mm": -50.0,
                    "thickness_after_mm": 46.5,
                    "material_after": "AIR",
                    "semi_diameter_mm": 10.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
            "groups": [{"id": "LENS_G", "from_surface": "S1", "to_surface": "S2"}],
        }
    )


def evaluation(metric: str, **extra):
    data = {
        "operands": [{"metric": metric, "target": 0.0, "tolerance": 2.0, "weight": 3.0}],
        "fields": [{"id": "edge", "theta_y_deg": 3.0, "theta_z_deg": 0.0}],
        "wavelengths": [486.13, 587.56, 656.27],
        "frequencies_lp_per_mm": [10.0],
        "field_curvature_method": "rms_search",
    }
    data.update(extra)
    return data


def test_variable_binding_registry_applies_surface_runtime_group_and_iris_variables():
    result = apply_variable_bindings(
        optical_system(),
        {
            "S1_curvature": 0.01,
            "S1_conic": -1.0,
            "S1_A4": 2.0e-8,
            "S1_A6": 3.0e-12,
            "S1_A8": 4.0e-16,
            "S1_A10": 5.0e-20,
            "LENS_G_shift_x_mm": 0.25,
            "iris_radius_mm": 4.0,
        },
    )
    surface = next(surface for surface in result.system.surfaces if surface.id == "S1")
    assert surface.radius_mm == pytest.approx(100.0)
    assert surface.conic == pytest.approx(-1.0)
    assert surface.asphere_coefficients == pytest.approx(
        {"A4": 2.0e-8, "A6": 3.0e-12, "A8": 4.0e-16, "A10": 5.0e-20}
    )
    assert result.configuration["group_positions"]["LENS_G"]["shift_x_mm"] == pytest.approx(0.25)
    assert result.configuration["variables"]["iris_radius_mm"] == pytest.approx(4.0)

    plane = apply_variable_bindings(optical_system(), {"S1_curvature": 0.0})
    assert next(surface for surface in plane.system.surfaces if surface.id == "S1").radius_mm == 0.0


def test_unknown_variable_and_metric_are_structured_400_errors():
    with pytest.raises(StructuredOpticsError) as variable_error:
        evaluate_system(optical_system(), {"metrics": ["rms_spot_radius"]}, variables={"S1_unknown": 1.0})
    assert variable_error.value.code == "optics_value_error"
    assert variable_error.value.params["variable_key"] == "S1_unknown"

    with pytest.raises(StructuredOpticsError) as metric_error:
        evaluate_system(optical_system(), {"metrics": ["not_a_metric"]})
    assert metric_error.value.params["metric"] == "not_a_metric"

    payload = optical_system().model_dump(mode="json")
    payload["evaluation"] = {"operands": [{"metric": "not_an_operand"}]}
    response = TestClient(app).post("/v1/optics/evaluate", json=payload)
    assert response.status_code == 400
    assert response.json()["code"] == "optics_value_error"
    assert response.json()["params"]["metric"] == "not_an_operand"


def test_metadata_is_generated_from_actual_registries():
    enumerations = meta_payload()["enumerations"]
    assert enumerations["metrics"] == list(SUPPORTED_EVALUATE_METRICS)
    assert enumerations["variable_key_patterns"] == variable_key_patterns()
    assert "{surface_id}_A{even_order}" in enumerations["variable_key_patterns"]


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        ("back_focal_length", lambda c, f, w: analyze_paraxial(c, wavelength_nm=w[0]).back_focal_length_mm),
        ("effective_focal_length", lambda c, f, w: analyze_paraxial(c, wavelength_nm=w[0]).effective_focal_length_mm),
        ("f_number", lambda c, f, w: analyze_paraxial(c, wavelength_nm=w[0]).f_number),
        ("distortion", lambda c, f, w: analyze_distortion(c, f, w).rows[0].distortion_percent),
        ("field_curvature", lambda c, f, w: analyze_field_curvature(c, f, method="rms_search").rows[0].best_focus_shift_mm),
        (
            "astigmatism",
            lambda c, f, w: (
                analyze_ms_image_surface(c, f, method="rms_search").rows[0].tangential_focus_shift_mm
                - analyze_ms_image_surface(c, f, method="rms_search").rows[0].sagittal_focus_shift_mm
            ),
        ),
        (
            "lateral_color",
            lambda c, f, w: analyze_chromatic_aberration(c, w, f).lateral_color_by_field["edge"]["max_lateral_shift_mm"],
        ),
        ("axial_color", lambda c, f, w: analyze_chromatic_aberration(c, w, f).axial_color_span_mm),
    ],
)
def test_evaluate_operands_match_individual_analysis_values(metric, expected):
    system = optical_system()
    compiled = compile_system(system)
    fields = [{"id": "edge", "type": "angular", "theta_y_deg": 3.0, "theta_z_deg": 0.0}]
    wavelengths = [486.13, 587.56, 656.27]
    result = evaluate_system(system, evaluation(metric), ray_sampling={"samples_per_field": 9})
    value = expected(compiled, fields, wavelengths)
    assert result.operands[0].value == pytest.approx(value, abs=1.0e-12)
    assert result.operands[0].residual == pytest.approx(3.0 * value / 2.0, abs=1.0e-12)


def test_white_mtf_operand_matches_white_mtf_api_and_is_deterministic():
    system = optical_system()
    fields = [{"id": "edge", "type": "angular", "theta_y_deg": 3.0, "theta_z_deg": 0.0}]
    weights = {486.13: 1.0, 587.56: 2.0, 656.27: 1.0}
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
    direct = analyze_white_mtf(compile_system(system), fields, sampling, weights, [10.0])
    request = evaluation("white_mtf", wavelength_weights=weights)
    first = evaluate_system(system, request, ray_sampling=sampling)
    second = evaluate_system(system, request, ray_sampling=sampling)
    assert first.operands[0].value == pytest.approx(direct.mtf.points[-1].mtf_radial, abs=1.0e-12)
    assert first == second
