import json
from pathlib import Path

import pytest

from optics_engine import analyze_paraxial, analyze_spot, compile_system, load_system, trace_forward


GOLDEN_PATH = Path(__file__).with_name("golden_values.json")
WAVELENGTHS = [486.13, 587.56, 656.27]


def glass_materials():
    return [
        {"id": "AIR", "type": "constant", "n": 1.0},
        {
            "id": "N-BK7",
            "type": "sellmeier",
            "B": [1.03961212, 0.231792344, 1.01046945],
            "C": [0.00600069867, 0.0200179144, 103.560653],
        },
        {
            "id": "N-F2",
            "type": "sellmeier",
            "B": [1.34533359, 0.209073176, 0.937357162],
            "C": [0.00997743871, 0.0470450767, 111.886764],
        },
    ]


def achromat_doublet_100mm():
    return load_system(
        {
            "name": "golden_bk7_f2_achromat_doublet_100mm",
            "wavelengths_nm": {"primary": 587.56, "samples": WAVELENGTHS},
            "materials": glass_materials(),
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 5.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 12.5},
                },
                {
                    "id": "S1",
                    "kind": "refractive",
                    "radius_mm": 49.35032280917523,
                    "material_after": "N-BK7",
                    "thickness_after_mm": 7.5,
                    "semi_diameter_mm": 12.5,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "radius_mm": -37.89173520260854,
                    "material_after": "N-F2",
                    "thickness_after_mm": 3.0,
                    "semi_diameter_mm": 12.5,
                },
                {
                    "id": "S3",
                    "kind": "refractive",
                    "radius_mm": -273.82424779569635,
                    "material_after": "AIR",
                    "thickness_after_mm": 93.33699484632511,
                    "semi_diameter_mm": 12.5,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def cassegrain_v2_3():
    return load_system(
        {
            "name": "golden_cassegrain_v2_3",
            "surfaces": [
                {"id": "M1", "kind": "mirror", "radius_mm": -2000.0, "thickness_after_mm": -650.0, "semi_diameter_mm": 100.0},
                {"id": "M2", "kind": "mirror", "radius_mm": -1050.0, "thickness_after_mm": 1050.0, "semi_diameter_mm": 40.0},
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 30.0, "height_mm": 30.0}},
            ],
        }
    )


def golden_values():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def paraxial_metrics(compiled, wavelength_nm):
    result = analyze_paraxial(compiled, wavelength_nm=wavelength_nm)
    return {
        "effective_focal_length_mm": float(result.effective_focal_length_mm),
        "back_focal_length_mm": float(result.back_focal_length_mm),
        "paraxial_image_position_mm": float(result.paraxial_image_position_mm),
        "f_number": None if result.f_number is None else float(result.f_number),
        "principal_plane_2_mm": None if result.principal_plane_positions_mm[1] is None else float(result.principal_plane_positions_mm[1]),
    }


def center_spot_metrics(compiled):
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    spot = analyze_spot(trace)
    return {
        "arrived_count": spot.arrived_count,
        "blocked_count": spot.blocked_count,
        "failed_count": spot.failed_count,
        "centroid_y_mm": spot.centroid_y_mm,
        "centroid_z_mm": spot.centroid_z_mm,
        "rms_radius_mm": spot.rms_radius_mm,
    }


def assert_close_dict(actual, expected, *, abs_tol=1e-9):
    assert actual.keys() == expected.keys()
    for key, expected_value in expected.items():
        actual_value = actual[key]
        if expected_value is None:
            assert actual_value is None
        elif isinstance(expected_value, int):
            assert actual_value == expected_value
        else:
            assert actual_value == pytest.approx(expected_value, abs=abs_tol, rel=1e-12)


def test_achromat_doublet_physical_sanity():
    compiled = compile_system(achromat_doublet_100mm(), use_cache=False)
    by_wavelength = {wavelength: paraxial_metrics(compiled, wavelength) for wavelength in WAVELENGTHS}
    d_line = by_wavelength[587.56]
    f_line = by_wavelength[486.13]
    c_line = by_wavelength[656.27]

    assert 95.0 <= d_line["effective_focal_length_mm"] <= 105.0
    assert d_line["back_focal_length_mm"] > 0.0
    assert d_line["f_number"] == pytest.approx(d_line["effective_focal_length_mm"] / 25.0, rel=1e-12)
    assert abs(f_line["paraxial_image_position_mm"] - c_line["paraxial_image_position_mm"]) < 0.001 * d_line["effective_focal_length_mm"]


def test_cassegrain_physical_sanity_matches_spec_section_6_3():
    compiled = compile_system(cassegrain_v2_3(), use_cache=False)
    paraxial = paraxial_metrics(compiled, 587.56)

    assert paraxial["effective_focal_length_mm"] == pytest.approx(3000.0, rel=1e-12)
    assert paraxial["back_focal_length_mm"] == pytest.approx(1050.0, rel=1e-12)
    assert paraxial["paraxial_image_position_mm"] == pytest.approx(400.0, rel=1e-12)

    marginal_height_at_m2_mm = 100.0 - 0.1 * 650.0
    assert marginal_height_at_m2_mm == pytest.approx(35.0)
    assert marginal_height_at_m2_mm < 40.0


def test_achromat_doublet_frozen_regression_values():
    compiled = compile_system(achromat_doublet_100mm(), use_cache=False)
    expected = golden_values()["systems"]["achromat_doublet_100mm"]

    for wavelength_text, expected_metrics in expected["paraxial_by_wavelength_nm"].items():
        assert_close_dict(paraxial_metrics(compiled, float(wavelength_text)), expected_metrics)
    assert_close_dict(center_spot_metrics(compiled), expected["spot_587_56_center_9_rays"], abs_tol=1e-10)


def test_cassegrain_frozen_regression_values():
    compiled = compile_system(cassegrain_v2_3(), use_cache=False)
    expected = golden_values()["systems"]["cassegrain_v2_3"]

    assert_close_dict(paraxial_metrics(compiled, 587.56), expected["paraxial_by_wavelength_nm"]["587.56"])
    assert_close_dict(center_spot_metrics(compiled), expected["spot_587_56_center_9_rays"], abs_tol=1e-12)
