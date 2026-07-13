import pytest

from optics_engine import evaluate_batch, evaluate_system, load_system, meta_payload


def phase7_system(sensor_x=100.0):
    return load_system(
        {
            "name": "phase7_eval",
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
                    "thickness_after_mm": sensor_x,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 40.0, "height_mm": 30.0}},
            ],
            "groups": [{"id": "LENS_G", "from_surface": "TL", "to_surface": "TL"}],
        }
    )


def p002_singlet_system():
    return load_system(
        {
            "name": "P002 N-BK7 Biconvex Singlet",
            "wavelengths_nm": {"primary": 587.56, "samples": [587.56]},
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
                    "semi_diameter_mm": 8.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 8.0},
                },
                {
                    "id": "S1",
                    "kind": "refractive",
                    "surface_type": "spherical",
                    "radius_mm": 50.0,
                    "thickness_after_mm": 5.0,
                    "material_after": "N-BK7",
                    "semi_diameter_mm": 15.0,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "surface_type": "spherical",
                    "radius_mm": -50.0,
                    "thickness_after_mm": 46.5,
                    "material_after": "AIR",
                    "semi_diameter_mm": 15.0,
                },
                {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def test_evaluate_system_fast_design_score_returns_merit_metrics():
    result = evaluate_system(
        phase7_system(sensor_x=95.0),
        {
            "preset": "fast_design_score",
            "fields": [{"theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        },
    )
    assert result.status == "ok"
    assert result.merit is not None
    assert result.merit.score >= 0.0
    assert "rms_spot_radius" in result.merit.metrics
    assert "geometric_mtf" in result.metrics
    assert "relative_illumination" in result.metrics


def test_evaluate_variables_can_change_candidate_score():
    base = phase7_system(sensor_x=100.0)
    focused = evaluate_system(base, {"metrics": ["rms_spot_radius"]})
    defocused = evaluate_system(base, {"metrics": ["rms_spot_radius"]}, variables={"TL_focal_length_mm": 80.0})
    assert focused.status == "ok"
    assert defocused.status == "ok"
    assert focused.merit.score < defocused.merit.score


def test_evaluate_infeasible_configuration_returns_penalty_without_trace():
    result = evaluate_system(
        phase7_system(),
        {"preset": "spot_only"},
        configuration={"group_positions": {"LENS_G": {"shift_x_mm": -10.0}}},
    )
    assert result.status == "infeasible"
    assert result.violations
    assert result.merit.metrics["constraint_penalty"] > 0.0
    assert result.metadata["stage"] == "constraint_check"


def test_evaluate_batch_scores_candidates_and_supports_parallel_workers():
    result = evaluate_batch(
        phase7_system(),
        [
            {"id": "focused", "variables": {"TL_focal_length_mm": 100.0}},
            {"id": "defocused", "variables": {"TL_focal_length_mm": 85.0}},
        ],
        {"preset": "spot_only"},
        parallel_workers=2,
    )
    assert result.status == "ok"
    assert result.metadata["candidate_count"] == 2
    scores = {row.id: row.result.merit.score for row in result.candidates}
    assert scores["focused"] < scores["defocused"]


def test_p002_ray_fan_and_longitudinal_merit_metrics_match_reference_trace_values():
    result = evaluate_system(
        p002_singlet_system(),
        {
            "operands": [
                {
                    "metric": "ray_fan_error",
                    "field_id": "center",
                    "wavelength_nm": 587.56,
                    "target": 0.05,
                    "tolerance": 0.02,
                    "weight": 2.0,
                },
                {
                    "metric": "longitudinal_aberration",
                    "field_id": "center",
                    "wavelength_nm": 587.56,
                    "target": 1.0,
                    "tolerance": 0.25,
                    "weight": 0.5,
                },
            ],
            "fields": [{"id": "center", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
            "wavelengths": [587.56],
        },
        ray_sampling={"samples_per_field": 9, "ray_aiming": {"mode": "paraxial"}},
    )

    assert result.status == "ok"
    assert result.metrics["ray_fan_error"] == pytest.approx(0.08744014142832597, abs=1.0e-12)
    assert result.metrics["longitudinal_aberration"] == pytest.approx(1.1449306743921865, abs=1.0e-12)
    assert result.merit is not None
    assert result.merit.metrics["ray_fan_error"] == pytest.approx(result.metrics["ray_fan_error"])
    assert result.merit.metrics["longitudinal_aberration"] == pytest.approx(result.metrics["longitudinal_aberration"])
    assert [operand.metric for operand in result.operands] == ["ray_fan_error", "longitudinal_aberration"]
    assert result.operands[0].value == pytest.approx(0.08744014142832597, abs=1.0e-12)
    expected_ray_fan_residual = 2.0 * (0.08744014142832597 - 0.05) / 0.02
    assert result.operands[0].residual == pytest.approx(expected_ray_fan_residual, abs=1.0e-12)
    assert result.operands[1].value == pytest.approx(1.1449306743921865, abs=1.0e-12)
    expected_longitudinal_residual = 0.5 * (1.1449306743921865 - 1.0) / 0.25
    assert result.operands[1].residual == pytest.approx(expected_longitudinal_residual, abs=1.0e-12)
    assert result.merit.score == pytest.approx(expected_ray_fan_residual**2 + expected_longitudinal_residual**2, abs=1.0e-12)
    assert {"ray_fan_error", "longitudinal_aberration"} <= set(meta_payload()["enumerations"]["metrics"])


def test_aberration_operand_rejects_non_positive_tolerance_as_structured_violation():
    result = evaluate_system(
        phase7_system(),
        {"operands": [{"metric": "ray_fan_error", "target": 0.0, "tolerance": 0.0}]},
    )

    assert result.status == "infeasible"
    assert result.metadata["stage"] == "operand_validation"
    assert result.violations == [
        {
            "severity": "error",
            "code": "optics_value_error",
            "params": {
                "operand_index": 0,
                "metric": "ray_fan_error",
                "tolerance": 0.0,
                "constraint": "tolerance > 0",
            },
            "message_en": "Operand tolerance must be positive.",
        }
    ]
