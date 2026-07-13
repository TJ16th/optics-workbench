import numpy as np
import pytest

from optics_engine import (
    analyze_field_curvature,
    analyze_ms_image_surface,
    compile_system,
    load_system,
    runtime_layout,
    symmetric_fields,
    trace_forward,
    validate_configuration,
)


def phase5_system():
    return load_system(
        {
            "name": "phase5_tilt",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 6.0},
                    "thickness_after_mm": 20.0,
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "focal_length_mm": 80.0,
                    "semi_diameter_mm": 8.0,
                    "thickness_after_mm": 80.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 50.0, "height_mm": 40.0}},
            ],
            "groups": [
                {"id": "LENS_G", "from_surface": "TL", "to_surface": "TL"},
                {"id": "SENSOR_G", "from_surface": "IMG", "to_surface": "IMG"},
            ],
        }
    )


def test_tilt_configuration_rotates_group_layout_and_trace_changes_spot():
    compiled = compile_system(phase5_system())
    config = {"tilts": [{"group": "LENS_G", "tilt_y_deg": 2.0}]}
    result = validate_configuration(compiled, config)
    assert result.ok
    layout = runtime_layout(compiled, config)
    lens_idx = compiled.surface_index("TL")
    assert layout.rotations[lens_idx, 0, 2] != pytest.approx(0.0)

    untilted = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    tilted = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
        {"configuration": config},
    )
    assert np.nanmean(tilted.sensor_z_mm) != pytest.approx(np.nanmean(untilted.sensor_z_mm))


def test_symmetric_fields_expands_to_plus_minus_field_set():
    fields = symmetric_fields([{"id": "edge", "type": "angular", "theta_y_deg": 3.0, "theta_z_deg": 4.0}])
    pairs = {(field["theta_y_deg"], field["theta_z_deg"]) for field in fields}
    assert pairs == {(-3.0, -4.0), (-3.0, 4.0), (3.0, -4.0), (3.0, 4.0)}


def test_invalid_tilt_target_is_reported():
    compiled = compile_system(phase5_system())
    result = validate_configuration(compiled, {"tilts": [{"group": "NOPE", "tilt_y_deg": 1.0}]})
    assert not result.ok
    assert any(issue.type == "unknown_tilt_target" for issue in result.issues)


def test_field_curvature_and_ms_image_surface_return_focus_rows():
    compiled = compile_system(phase5_system())
    fields = [{"id": "upper", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 3.0}]
    curvature = analyze_field_curvature(compiled, fields, search_mm=2.0)
    assert len(curvature.rows) == 1
    assert curvature.rows[0].best_focus_shift_mm is not None

    ms = analyze_ms_image_surface(compiled, fields, search_mm=2.0)
    assert len(ms.rows) == 1
    assert ms.rows[0].tangential_focus_shift_mm is not None
    assert ms.rows[0].sagittal_focus_shift_mm is not None
    assert ms.rows[0].method == "coddington"
    assert ms.metadata["method"] == "coddington"
