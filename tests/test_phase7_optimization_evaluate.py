import pytest

from optics_engine import evaluate_batch, evaluate_system, load_system


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
