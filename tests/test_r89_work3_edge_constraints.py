from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from optics_engine import compile_system, evaluate_system, load_system
from optics_engine.api.main import app
from optics_engine.configuration import surface_gap_values, validate_configuration


def system(thickness_mm: float = 5.0):
    return load_system(
        {
            "name": "R89 edge thickness",
            "materials": [
                {"id": "AIR", "type": "constant", "n": 1.0},
                {"id": "GLASS", "type": "constant", "n": 1.5},
            ],
            "surfaces": [
                {"id": "STOP", "kind": "aperture_stop", "thickness_after_mm": 2.0, "aperture": {"shape": "circle", "semi_diameter_mm": 5.0}},
                {"id": "S1", "kind": "refractive", "radius_mm": 50.0, "thickness_after_mm": thickness_mm, "material_after": "GLASS", "semi_diameter_mm": 5.0},
                {"id": "S2", "kind": "refractive", "radius_mm": -50.0, "thickness_after_mm": 45.0, "material_after": "AIR", "semi_diameter_mm": 5.0},
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 20.0, "height_mm": 20.0}},
            ],
        }
    )


def expected_edge(thickness_mm: float) -> float:
    sag = 50.0 - math.sqrt(50.0**2 - 5.0**2)
    return thickness_mm - 2.0 * sag


def test_surface_gap_uses_smaller_clear_radius_and_both_surface_sags():
    rows = surface_gap_values(compile_system(system()))
    glass = next(row for row in rows if row.surface_ids == ("S1", "S2"))
    assert glass.radial_height_mm == pytest.approx(5.0)
    assert glass.edge_gap_mm == pytest.approx(expected_edge(5.0), abs=1.0e-12)


def test_edge_thickness_metric_and_continuous_constraint_operand():
    result = evaluate_system(
        system(),
        {
            "metrics": ["edge_thickness", "min_air_gap"],
            "constraints": {"min_edge_thickness_mm": 5.0, "min_edge_thickness_tolerance_mm": 0.5, "min_air_gap_mm": 1.0},
        },
        ray_sampling={"samples_per_field": 3, "pupil_distribution": "grid", "ray_aiming": {"mode": "off"}},
    )
    assert result.metrics["edge_thickness"] == pytest.approx(expected_edge(5.0), abs=1.0e-12)
    entrance_air_gap = 2.0 + (50.0 - math.sqrt(50.0**2 - 5.0**2))
    assert result.metrics["min_air_gap"] == pytest.approx(entrance_air_gap)
    edge_operand = next(row for row in result.operands if row.metric == "edge_thickness")
    assert edge_operand.value == pytest.approx(expected_edge(5.0), abs=1.0e-12)
    assert edge_operand.residual == pytest.approx((5.0 - expected_edge(5.0)) / 0.5)
    assert any(issue["code"] == "edge_thickness_below_min" for issue in result.violations)


def test_sag_interference_is_a_structured_warning_and_negative_vertex_stays_error():
    compiled = compile_system(system(0.1))
    validation = validate_configuration(compiled)
    interference = next(issue for issue in validation.issues if issue.code == "surface_interference")
    assert interference.severity == "warning"
    assert interference.params["edge_gap_mm"] < 0.0

    shifted = load_system(
        {
            **system().model_dump(mode="json"),
            "groups": [{"id": "LENS", "from_surface": "S1", "to_surface": "S2"}],
        }
    )
    bad = validate_configuration(compile_system(shifted), {"group_positions": {"LENS": {"shift_x_mm": -10.0}}})
    assert any(issue.code == "negative_air_gap" and issue.severity == "error" for issue in bad.issues)


def test_edge_thickness_is_available_through_evaluate_api():
    payload = system().model_dump(mode="json")
    payload["evaluation"] = {"operands": [{"metric": "edge_thickness", "target": 4.0, "tolerance": 1.0}]}
    payload["ray_sampling"] = {"samples_per_field": 3, "pupil_distribution": "grid", "ray_aiming": {"mode": "off"}}
    response = TestClient(app).post("/v1/optics/evaluate", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["operands"][0]["value"] == pytest.approx(expected_edge(5.0), abs=1.0e-12)
