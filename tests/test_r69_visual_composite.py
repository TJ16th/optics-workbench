import pytest

from optics_engine import (
    analyze_exit_pupil,
    analyze_visual_composite,
    compile_system,
    load_system,
    validate_system,
)


def visual_composite_system(position_mode="at_exit_pupil", offset=None):
    eye = {"pupil_diameter_mm": 4.0, "position_mode": position_mode}
    if offset is not None:
        eye["offset_from_last_surface_mm"] = offset
    return load_system(
        {
            "name": "r69_visual_composite",
            "system_type": "afocal",
            "visual_evaluation": {
                "mode": "instrument_and_retinal",
                "eye_model": "gullstrand_simplified_relaxed",
            },
            "materials": [
                {"id": "AIR", "type": "constant", "n": 1.0},
                {"id": "EYE_GLASS", "type": "constant", "n": 1.4},
            ],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 10.0},
                },
                {"id": "OBJ", "kind": "thin_lens", "focal_length_mm": 100.0, "semi_diameter_mm": 10.0, "thickness_after_mm": 120.0},
                {"id": "EYEPIECE", "kind": "thin_lens", "focal_length_mm": 20.0, "semi_diameter_mm": 10.0, "thickness_after_mm": 20.0},
                {"id": "EYE", "kind": "eye_reference", "eye": eye},
                {"id": "CORNEA", "kind": "refractive", "radius_mm": 8.0, "material_after": "EYE_GLASS", "semi_diameter_mm": 6.0, "thickness_after_mm": 4.0},
                {"id": "LENS_BACK", "kind": "refractive", "radius_mm": -8.0, "material_after": "AIR", "semi_diameter_mm": 6.0, "thickness_after_mm": 12.0},
                {"id": "RETINA", "kind": "sensor", "sensor": {"width_mm": 24.0, "height_mm": 24.0}},
            ],
        }
    )


def test_visual_composite_validates_and_keeps_boundary_index():
    system = visual_composite_system()
    assert validate_system(system).ok
    compiled = compile_system(system, use_cache=False)
    assert compiled.eye_reference_index == 3
    assert compiled.sensor_index == 6


def test_at_exit_pupil_resolves_compiled_position_and_shifts_retinal_section():
    compiled = compile_system(visual_composite_system(), use_cache=False)
    assert compiled.surface_positions_mm[3] == pytest.approx(144.0)
    assert compiled.surface_positions_mm[4] == pytest.approx(144.0)
    assert compiled.surface_positions_mm[6] == pytest.approx(160.0)


def test_fixed_offset_resolves_from_last_instrument_surface():
    compiled = compile_system(visual_composite_system("fixed_offset", 12.5), use_cache=False)
    assert compiled.surface_positions_mm[3] == pytest.approx(132.5)
    assert compiled.surface_positions_mm[6] == pytest.approx(148.5)


def test_instrument_metrics_exclude_powered_eye_surfaces():
    compiled = compile_system(visual_composite_system(), use_cache=False)
    exit_pupil = analyze_exit_pupil(compiled)
    assert exit_pupil.angular_magnification == pytest.approx(-5.0)
    assert exit_pupil.eye_relief_mm == pytest.approx(24.0)


def test_visual_composite_returns_separate_instrument_and_retinal_results():
    compiled = compile_system(visual_composite_system(), use_cache=False)
    result = analyze_visual_composite(
        compiled,
        sampling={"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
    )
    assert result.instrument.arrived_count > 0
    assert result.retinal.arrived_count > 0
    assert result.retinal.rms_radius_mm is not None
    assert result.exit_pupil.angular_magnification == pytest.approx(-5.0)


def test_visual_composite_requires_retina_and_fixed_offset_value():
    system = visual_composite_system("fixed_offset")
    result = validate_system(system)
    assert not result.ok
    assert "missing_eye_reference_offset" in {issue.code for issue in result.issues}

    payload = visual_composite_system().model_dump(mode="json")
    payload["surfaces"] = payload["surfaces"][:-1]
    result = validate_system(load_system(payload))
    assert not result.ok
    assert "missing_terminal_retina_sensor" in {issue.code for issue in result.issues}
