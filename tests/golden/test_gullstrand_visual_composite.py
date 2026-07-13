import pytest

from optics_engine import analyze_visual_composite, compile_system, gullstrand_visual_composite_demo


def test_gullstrand_visual_composite_prescription_and_golden_trace():
    compiled = compile_system(gullstrand_visual_composite_demo(), use_cache=False)
    prescription = [
        (surface.id, surface.radius_mm, surface.thickness_after_mm, surface.material_after)
        for surface in compiled.surfaces[4:8]
    ]
    assert prescription == [
        ("CORNEA_FRONT", 7.7, 0.5, "CORNEA"),
        ("CORNEA_BACK", 6.8, 3.1, "AQUEOUS_VITREOUS"),
        ("LENS_FRONT", 10.0, 3.6, "LENS_EQ"),
        ("LENS_BACK", -6.0, 17.187, "AQUEOUS_VITREOUS"),
    ]
    assert compiled.surface_positions_mm[compiled.eye_reference_index] == pytest.approx(144.0)

    result = analyze_visual_composite(
        compiled,
        sampling={"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
    )
    assert result.exit_pupil.angular_magnification == pytest.approx(-5.0)
    assert result.exit_pupil.eye_relief_mm == pytest.approx(24.0)
    assert result.instrument.arrived_count == 5
    assert result.retinal.arrived_count == 5
    assert result.retinal.centroid_y_mm == pytest.approx(0.0, abs=1.0e-12)
    assert result.retinal.centroid_z_mm == pytest.approx(0.0, abs=1.0e-12)
    assert result.retinal.rms_radius_mm == pytest.approx(0.022811937099695253, abs=1.0e-12)

    near_axis = analyze_visual_composite(
        compiled,
        field={"id": "near", "type": "angular", "theta_y_deg": 0.1, "theta_z_deg": 0.0},
        sampling={"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
    )
    assert near_axis.instrument.centroid_theta_y_deg == pytest.approx(-0.49998781584508495, abs=1.0e-12)
    assert near_axis.retinal.centroid_y_mm == pytest.approx(-0.14743004040829139, abs=1.0e-12)
    assert near_axis.retinal.rms_radius_mm == pytest.approx(0.022924334291296058, abs=1.0e-12)
