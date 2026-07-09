import numpy as np
import pytest

from optics_engine import (
    analyze_paraxial,
    compile_system,
    load_system,
    runtime_layout,
    trace_forward,
    validate_configuration,
    validate_system,
)


def phase4_system():
    return load_system(
        {
            "name": "phase4_groups",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
                    "thickness_after_mm": 20.0,
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "focal_length_mm": 100.0,
                    "semi_diameter_mm": 8.0,
                    "thickness_after_mm": 100.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
            "groups": [
                {"id": "STOP_G", "from_surface": "STOP", "to_surface": "STOP"},
                {"id": "FOCUS_G", "from_surface": "TL", "to_surface": "TL"},
            ],
            "zoom_positions": [
                {"id": "near", "group_positions": {"FOCUS_G": {"shift_x_mm": 10.0}}},
                {"id": "wide", "group_positions": {"FOCUS_G": {"shift_x_mm": 0.0}}},
            ],
        }
    )


def test_zoom_position_moves_group_x_and_updates_paraxial_image_position():
    compiled = compile_system(phase4_system())
    nominal = analyze_paraxial(compiled)
    shifted = analyze_paraxial(compiled, {"zoom_position": "near"})
    assert shifted.paraxial_image_position_mm == pytest.approx(nominal.paraxial_image_position_mm + 10.0)
    layout = runtime_layout(compiled, {"zoom_position": "near"})
    assert layout.centers_mm[compiled.surface_index("TL"), 0] == pytest.approx(30.0)


def test_decentered_stop_group_changes_global_hit_but_keeps_local_stop_coordinates():
    compiled = compile_system(phase4_system())
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 1, "ray_aiming": {"mode": "full"}},
        [587.56],
        {"store_path": True, "configuration": {"decenters": [{"group": "STOP_G", "shift_y_mm": 2.0}]}},
    )
    assert trace.metadata["aiming_failed_count"] == 0
    stop_hit = trace.paths[0][0]
    assert stop_hit["surface_id"] == "STOP"
    assert stop_hit["point_mm"][1] == pytest.approx(2.0, abs=1e-6)
    assert stop_hit["local_point_mm"][1] == pytest.approx(0.0, abs=1e-6)


def test_group_configuration_validation_catches_unknown_group_and_negative_gap():
    compiled = compile_system(phase4_system())
    unknown = validate_configuration(compiled, {"decenters": [{"group": "NOPE", "shift_y_mm": 1.0}]})
    assert not unknown.ok
    assert any(issue.type == "unknown_group" for issue in unknown.issues)

    bad_gap = validate_configuration(compiled, {"group_positions": {"FOCUS_G": {"shift_x_mm": -25.0}}})
    assert not bad_gap.ok
    assert any(issue.type == "negative_air_gap" for issue in bad_gap.issues)


def test_static_group_and_zoom_definitions_are_validated():
    bad = load_system(
        {
            "name": "bad_group",
            "surfaces": [
                {"id": "STOP", "kind": "aperture_stop", "aperture": {"shape": "circle", "semi_diameter_mm": 3.0}, "thickness_after_mm": 10.0},
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 10.0, "height_mm": 10.0}},
            ],
            "groups": [{"id": "G1", "from_surface": "MISSING", "to_surface": "IMG"}],
            "zoom_positions": [{"id": "z1", "group_positions": {"NOPE": {"shift_x_mm": 1.0}}}],
        }
    )
    result = validate_system(bad)
    assert not result.ok
    assert any(issue.type == "unknown_group_surface" for issue in result.issues)
    assert any(issue.type == "unknown_zoom_group" for issue in result.issues)
