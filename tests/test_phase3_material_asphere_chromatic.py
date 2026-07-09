import math

import numpy as np
import pytest

from optics_engine import analyze_chromatic_aberration, compile_system, load_system, trace_forward, validate_system
from optics_engine.core import intersect_asphere, surface_normals_for_surface
from optics_engine.models import Surface


def bk7_sellmeier_material():
    return {
        "id": "N-BK7",
        "type": "sellmeier",
        "B": [1.03961212, 0.231792344, 1.01046945],
        "C": [0.00600069867, 0.0200179144, 103.560653],
    }


def dispersive_lens_system():
    return load_system(
        {
            "name": "phase3_dispersive_lens",
            "wavelengths_nm": {"primary": 587.56, "samples": [486.13, 587.56, 656.27]},
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}, bk7_sellmeier_material()],
            "surfaces": [
                {
                    "id": "S1",
                    "kind": "refractive",
                    "radius_mm": 50.0,
                    "material_after": "N-BK7",
                    "semi_diameter_mm": 8.0,
                    "thickness_after_mm": 0.0,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "radius_mm": -50.0,
                    "material_after": "AIR",
                    "semi_diameter_mm": 8.0,
                    "thickness_after_mm": 0.0,
                },
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 8.0},
                    "thickness_after_mm": 50.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def test_sellmeier_bk7_refractive_index_at_d_line():
    system = dispersive_lens_system()
    compiled = compile_system(system)
    assert compiled.material_index("N-BK7", 587.56) == pytest.approx(1.5168, abs=5e-4)
    assert compiled.material_index("N-BK7", 486.13) > compiled.material_index("N-BK7", 656.27)


def test_even_asphere_intersection_and_normal_follow_sag():
    surface = Surface(
        id="ASP",
        kind="refractive",
        surface_type="aspherical_even",
        radius_mm=0.0,
        asphere_coefficients={"A4": 1.0e-5},
        material_after="AIR",
    )
    origins = np.array([[-10.0, 10.0, 0.0]])
    directions = np.array([[1.0, 0.0, 0.0]])
    points, valid = intersect_asphere(origins, directions, 0.0, surface.radius_mm, surface.conic, surface.asphere_coefficients)
    assert valid[0]
    assert points[0, 0] == pytest.approx(0.1, abs=1e-10)
    normal = surface_normals_for_surface(points, 0.0, surface)[0]
    assert normal[0] > 0.99
    assert normal[1] < 0.0


def test_aspherical_refractive_surface_is_traceable():
    system = load_system(
        {
            "name": "asphere_trace",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}, {"id": "GLASS", "type": "constant", "n": 1.5}],
            "surfaces": [
                {
                    "id": "S1",
                    "kind": "refractive",
                    "surface_type": "aspherical_even",
                    "radius_mm": 50.0,
                    "asphere_coefficients": {"A4": 1.0e-7},
                    "material_after": "GLASS",
                    "semi_diameter_mm": 8.0,
                    "thickness_after_mm": 2.0,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "radius_mm": -50.0,
                    "material_after": "AIR",
                    "semi_diameter_mm": 8.0,
                    "thickness_after_mm": 8.0,
                },
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 4.0},
                    "thickness_after_mm": 40.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )
    assert validate_system(system).ok
    trace = trace_forward(
        compile_system(system),
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 5, "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    assert np.sum(trace.arrived_mask) >= 1


def test_chromatic_aberration_reports_axial_and_lateral_color():
    compiled = compile_system(dispersive_lens_system())
    result = analyze_chromatic_aberration(
        compiled,
        [486.13, 587.56, 656.27],
        [{"id": "edge", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0}],
    )
    assert len(result.focus_by_wavelength) == 3
    assert result.axial_color_span_mm is not None
    assert result.axial_color_span_mm > 0.0
    shifts = [row.axial_shift_from_primary_mm for row in result.focus_by_wavelength]
    assert any(abs(shift or 0.0) > 0.0 for shift in shifts)
    assert result.lateral_color_by_field["edge"]["max_lateral_shift_mm"] > 0.0
