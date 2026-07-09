import math

import numpy as np

from optics_engine import (
    analyze_paraxial,
    analyze_spot,
    compile_system,
    load_system,
    trace_forward,
    validate_system,
)
from optics_engine.core import aperture_pass, field_direction, intersect_sphere, refract
from optics_engine.models import Aperture, Surface
from optics_engine.system import get_cached_system


def base_materials():
    return [
        {"id": "AIR", "type": "constant", "n": 1.0},
        {"id": "GLASS", "type": "constant", "n": 1.5},
    ]


def thin_lens_system(focal_length=100.0, sensor_x=100.0):
    return load_system(
        {
            "name": "thin_lens",
            "materials": base_materials(),
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 0.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 10.0},
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "focal_length_mm": focal_length,
                    "semi_diameter_mm": 10.0,
                    "thickness_after_mm": sensor_x,
                },
                {
                    "id": "IMG",
                    "kind": "sensor",
                    "sensor": {"width_mm": 36.0, "height_mm": 24.0},
                },
            ],
        }
    )


def test_field_direction_uses_tan_based_composition():
    direction = field_direction(10.0, -5.0)
    assert np.allclose(direction / direction[0], [1.0, math.tan(math.radians(10)), math.tan(math.radians(-5))])


def test_plane_refraction_matches_snell_law():
    incident_angle = math.radians(30)
    directions = np.array([[math.cos(incident_angle), math.sin(incident_angle), 0.0]])
    normals = np.array([[1.0, 0.0, 0.0]])
    out, ok = refract(directions, normals, np.array([1.0]), np.array([1.5]))
    assert ok[0]
    transmitted = math.asin(out[0, 1])
    assert transmitted == pytest_approx(math.asin(math.sin(incident_angle) / 1.5), abs=1e-12)


def test_spherical_surface_intersection_matches_expected_vertex_hit():
    origins = np.array([[-100.0, 0.0, 0.0], [-100.0, 3.0, 4.0]])
    directions = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    points, valid = intersect_sphere(origins, directions, x_vertex=0.0, radius_mm=50.0)
    assert valid.tolist() == [True, True]
    assert points[0, 0] == pytest_approx(0.0)
    assert points[1, 0] == pytest_approx(50.0 - math.sqrt(50.0**2 - 5.0**2))


def test_sensor_intersection_and_spot_for_thin_lens():
    compiled = compile_system(thin_lens_system())
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    assert np.all(trace.status == "alive")
    assert np.nanmax(np.abs(trace.sensor_y_mm)) < 1e-9
    assert np.nanmax(np.abs(trace.sensor_z_mm)) < 1e-9
    spot = analyze_spot(trace)
    assert spot.arrived_count == 9
    assert spot.rms_radius_mm < 1e-9


def test_spherical_mirror_paraxial_focus_is_r_over_two():
    system = load_system(
        {
            "name": "mirror",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 50.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 10.0},
                },
                {"id": "M1", "kind": "mirror", "radius_mm": -200.0, "semi_diameter_mm": 20.0, "thickness_after_mm": -100.0},
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 20.0, "height_mm": 20.0}},
            ],
        }
    )
    compiled = compile_system(system)
    paraxial = analyze_paraxial(compiled)
    assert abs(paraxial.back_focal_length_mm) == pytest_approx(100.0)


def test_thin_lens_paraxial_formula():
    compiled = compile_system(thin_lens_system(focal_length=75.0, sensor_x=75.0))
    paraxial = analyze_paraxial(compiled)
    assert paraxial.effective_focal_length_mm == pytest_approx(75.0)
    assert paraxial.back_focal_length_mm == pytest_approx(75.0)
    assert paraxial.f_number == pytest_approx(75.0 / 20.0)


def test_circle_and_annulus_aperture_checks():
    points = np.array([[0.0, 0.0, 0.0], [0.0, 3.0, 4.0], [0.0, 8.0, 0.0]])
    circle = Surface(id="A", kind="aperture_stop", aperture=Aperture(shape="circle", semi_diameter_mm=5.0))
    annulus = Surface(
        id="B",
        kind="aperture_stop",
        aperture=Aperture(shape="annulus", inner_semi_diameter_mm=2.0, outer_semi_diameter_mm=6.0),
    )
    assert aperture_pass(points, circle).tolist() == [True, True, False]
    assert aperture_pass(points, annulus).tolist() == [False, True, False]


def test_refractive_single_lens_paraxial_matches_lensmaker_thin_limit():
    system = load_system(
        {
            "name": "thin_refractive_lens",
            "materials": base_materials(),
            "surfaces": [
                {
                    "id": "S1",
                    "kind": "refractive",
                    "radius_mm": 50.0,
                    "material_after": "GLASS",
                    "semi_diameter_mm": 10.0,
                    "thickness_after_mm": 0.0,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "radius_mm": -50.0,
                    "material_after": "AIR",
                    "semi_diameter_mm": 10.0,
                    "thickness_after_mm": 0.0,
                },
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 50.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 10.0},
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )
    paraxial = analyze_paraxial(compile_system(system))
    assert paraxial.effective_focal_length_mm == pytest_approx(50.0)


def test_small_angle_real_trace_converges_to_paraxial_image_height():
    compiled = compile_system(thin_lens_system(focal_length=100.0, sensor_x=100.0))
    theta = 1.0
    trace = trace_forward(
        compiled,
        [{"id": "edge", "type": "angular", "theta_y_deg": theta, "theta_z_deg": 0.0}],
        {"samples_per_field": 1, "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    expected_y = 100.0 * math.tan(math.radians(theta))
    assert trace.sensor_y_mm[0] == pytest_approx(expected_y, abs=1e-9)


def test_full_ray_aiming_hits_stop_center_and_cache_reuses_compiled_system():
    system = thin_lens_system()
    compiled = compile_system(system)
    again = compile_system(system)
    assert again is compiled
    assert get_cached_system(compiled.system_hash) is compiled

    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {
            "samples_per_field": 1,
            "ray_aiming": {"mode": "full", "tolerance_mm": 1e-6, "max_iterations": 5},
        },
        [587.56],
        {"store_path": True},
    )
    assert trace.metadata["aiming_failed_count"] == 0
    first_path = trace.paths[0][0]
    assert first_path["surface_id"] == "STOP"
    assert abs(first_path["point_mm"][1]) <= 1e-6
    assert abs(first_path["point_mm"][2]) <= 1e-6


def test_validation_reports_mirror_thickness_sign_errors():
    system = load_system(
        {
            "name": "bad_mirror",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 10.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
                },
                {"id": "M1", "kind": "mirror", "radius_mm": -200.0, "thickness_after_mm": 100.0},
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 20.0, "height_mm": 20.0}},
            ],
        }
    )
    result = validate_system(system)
    assert not result.ok
    assert any(issue.type == "mirror_thickness_sign" for issue in result.issues)


def pytest_approx(*args, **kwargs):
    import pytest

    return pytest.approx(*args, **kwargs)
