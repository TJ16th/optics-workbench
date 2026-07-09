import pytest

from optics_engine import (
    analyze_afocal,
    analyze_angular_mtf,
    analyze_binocular_alignment,
    analyze_exit_pupil,
    analyze_eye_box,
    analyze_telescope,
    compile_system,
    load_system,
    trace_forward,
    validate_system,
)


def telescope_system(eye_pupil=4.0):
    return load_system(
        {
            "name": "phase8_telescope",
            "system_type": "afocal",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 25.0},
                    "thickness_after_mm": 0.0,
                },
                {
                    "id": "OBJ",
                    "kind": "thin_lens",
                    "focal_length_mm": 100.0,
                    "semi_diameter_mm": 25.0,
                    "thickness_after_mm": 120.0,
                },
                {
                    "id": "EYEPIECE",
                    "kind": "thin_lens",
                    "focal_length_mm": 20.0,
                    "semi_diameter_mm": 10.0,
                    "thickness_after_mm": 20.0,
                },
                {
                    "id": "EYE",
                    "kind": "eye_reference",
                    "eye": {"pupil_diameter_mm": eye_pupil, "position_mode": "fixed_offset"},
                },
            ],
            "groups": [
                {"id": "EYE_G", "from_surface": "EYE", "to_surface": "EYE"},
                {"id": "RIGHT_ALIGN", "from_surface": "EYEPIECE", "to_surface": "EYEPIECE"},
            ],
        }
    )


def test_afocal_system_with_eye_reference_validates_and_traces_angles():
    system = telescope_system()
    assert validate_system(system).ok
    compiled = compile_system(system)
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    assert trace.eye_arrived_mask.any()
    result = analyze_afocal(compiled)
    assert result.arrived_count > 0
    assert abs(result.centroid_theta_y_deg) < 1e-9
    assert abs(result.centroid_theta_z_deg) < 1e-9
    assert result.residual_divergence_diopter < 1e-9


def test_exit_pupil_and_telescope_summary_for_keplerian_pair():
    compiled = compile_system(telescope_system())
    exit_pupil = analyze_exit_pupil(compiled)
    assert exit_pupil.angular_magnification == pytest.approx(-5.0)
    assert exit_pupil.exit_pupil_diameter_mm == pytest.approx(10.0)
    assert exit_pupil.eye_relief_mm == pytest.approx(20.0)

    telescope = analyze_telescope(compiled, true_field_deg=2.0)
    assert telescope.magnification == pytest.approx(-5.0)
    assert telescope.apparent_field_deg == pytest.approx(10.0)


def test_eye_box_throughput_drops_when_eye_is_decentered():
    compiled = compile_system(telescope_system(eye_pupil=4.0))
    result = analyze_eye_box(compiled, [(0.0, 0.0), (8.0, 0.0)])
    assert len(result.samples) == 2
    assert result.samples[0].throughput > result.samples[1].throughput


def test_angular_mtf_uses_eye_angle_units():
    compiled = compile_system(telescope_system())
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    mtf = analyze_angular_mtf(trace, [0.0, 5.0])
    assert mtf.points[0].mtf == pytest.approx(1.0)
    assert mtf.points[1].frequency_cycles_per_degree == pytest.approx(5.0)


def test_binocular_alignment_reports_pose_tilt_difference():
    left = compile_system(telescope_system())
    right = compile_system(telescope_system())
    field = {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}
    left_eval = analyze_afocal(left, field)
    right_eval = analyze_afocal(right, field, configuration={"tilts": [{"group": "RIGHT_ALIGN", "tilt_y_deg": 0.5}]})
    alignment = analyze_binocular_alignment(left_eval, right_eval)
    assert alignment.angular_separation_deg > 0.0
