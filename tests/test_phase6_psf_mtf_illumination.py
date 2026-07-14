import math
import time

import pytest

from optics_engine import (
    analyze_geometric_mtf,
    analyze_geometric_psf,
    analyze_relative_illumination,
    analyze_through_focus_mtf,
    analyze_white_mtf,
    analyze_white_psf,
    compile_system,
    load_system,
    trace_forward,
)


def phase6_thin_lens(sensor_x=95.0, aperture=5.0):
    return load_system(
        {
            "name": "phase6_thin_lens",
            "wavelengths_nm": {"primary": 587.56, "samples": [486.13, 587.56, 656.27]},
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "aperture": {"shape": "circle", "semi_diameter_mm": aperture},
                    "thickness_after_mm": 0.0,
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "focal_length_mm": 100.0,
                    "semi_diameter_mm": aperture,
                    "thickness_after_mm": sensor_x,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 40.0, "height_mm": 30.0}},
            ],
        }
    )


def phase6_trace(sensor_x=95.0):
    compiled = compile_system(phase6_thin_lens(sensor_x=sensor_x))
    return compiled, trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 49, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )


def p002_singlet_system():
    return load_system(
        {
            "name": "P002 N-BK7 Biconvex Singlet",
            "wavelengths_nm": {"primary": 587.56, "samples": [587.56]},
            "materials": [
                {"id": "AIR", "type": "constant", "n": 1.0},
                {
                    "id": "N-BK7",
                    "type": "sellmeier",
                    "B": [1.03961212, 0.231792344, 1.01046945],
                    "C": [0.00600069867, 0.0200179144, 103.560653],
                },
            ],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "surface_type": "plane",
                    "thickness_after_mm": 2.0,
                    "semi_diameter_mm": 8.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 8.0},
                },
                {
                    "id": "S1",
                    "kind": "refractive",
                    "surface_type": "spherical",
                    "radius_mm": 50.0,
                    "thickness_after_mm": 5.0,
                    "material_after": "N-BK7",
                    "semi_diameter_mm": 9.5,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "surface_type": "spherical",
                    "radius_mm": -50.0,
                    "thickness_after_mm": 46.5,
                    "material_after": "AIR",
                    "semi_diameter_mm": 9.75,
                },
                {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def test_geometric_psf_is_normalized_and_encircled_energy_is_monotonic():
    _, trace = phase6_trace()
    psf = analyze_geometric_psf(trace, grid_size=16)
    assert psf.total_energy > 0
    assert sum(sum(row) for row in psf.grid) == pytest.approx(1.0)
    energies = [point.energy_fraction for point in psf.encircled_energy]
    assert energies == sorted(energies)
    assert energies[-1] == pytest.approx(1.0)


def test_geometric_mtf_has_unity_zero_frequency_and_rolls_off_for_blur():
    _, trace = phase6_trace(sensor_x=90.0)
    mtf = analyze_geometric_mtf(trace, [0.0, 10.0])
    assert mtf.points[0].mtf_y == pytest.approx(1.0)
    assert mtf.points[0].mtf_z == pytest.approx(1.0)
    assert mtf.points[1].mtf_radial < 1.0


def test_through_focus_mtf_matches_zero_defocus_and_forms_focus_peak():
    compiled = compile_system(p002_singlet_system())
    fields = [
        {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
        {"id": "mid-y", "type": "angular", "theta_y_deg": 9.900092, "theta_z_deg": 0.0},
        {"id": "edge-y", "type": "angular", "theta_y_deg": 14.0, "theta_z_deg": 0.0},
    ]
    sampling = {"samples_per_field": 1024, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
    start = time.perf_counter()
    result = analyze_through_focus_mtf(compiled, fields, sampling, [587.56], frequencies_lp_per_mm=[10.0, 30.0])
    elapsed = time.perf_counter() - start

    assert len(result.points) == 21 * 3 * 2
    assert result.metadata["projection_method"] == "single_trace_final_ray_projection"
    assert result.metadata["range_source"] == "paraxial_focus_offset_plus_diffraction_depth_of_focus"
    assert elapsed < 30.0

    zero = [point for point in result.points if point.field_id == "center" and point.defocus_mm == pytest.approx(0.0)]
    direct_trace = trace_forward(compiled, [fields[0]], sampling, [587.56])
    direct = analyze_geometric_mtf(direct_trace, [10.0, 30.0])
    assert [point.mtf_meridional for point in zero] == pytest.approx([point.mtf_y for point in direct.points])
    assert [point.mtf_sagittal for point in zero] == pytest.approx([point.mtf_z for point in direct.points])

    center_10 = [point.mtf_meridional for point in result.points if point.field_id == "center" and point.frequency_lp_per_mm == 10.0]
    assert max(center_10) > center_10[0]
    assert max(center_10) > center_10[-1]


def test_through_focus_mtf_rotates_meridional_axis_for_theta_z_field():
    compiled = compile_system(p002_singlet_system())
    sampling = {"samples_per_field": 256, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
    field_y = {"id": "field-y", "type": "angular", "theta_y_deg": 8.0, "theta_z_deg": 0.0}
    field_z = {"id": "field-z", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 8.0}
    result = analyze_through_focus_mtf(
        compiled,
        [field_y, field_z],
        sampling,
        [587.56],
        frequencies_lp_per_mm=[10.0],
        defocus_range_mm=0.01,
        defocus_points=3,
    )
    y_zero = next(point for point in result.points if point.field_id == "field-y" and point.defocus_mm == pytest.approx(0.0))
    z_zero = next(point for point in result.points if point.field_id == "field-z" and point.defocus_mm == pytest.approx(0.0))
    assert z_zero.mtf_meridional == pytest.approx(y_zero.mtf_meridional, abs=2.0e-3)
    assert z_zero.mtf_sagittal == pytest.approx(y_zero.mtf_sagittal, abs=2.0e-3)


def test_geometric_mtf_dense_pupil_sampling_suppresses_coarse_recurrence():
    compiled = compile_system(p002_singlet_system())
    fields = [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    frequencies = [index * 2.5 for index in range(33)]
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}

    coarse = analyze_geometric_mtf(trace_forward(compiled, fields, sampling, [587.56]), frequencies)
    dense_sampling = {**sampling, "samples_per_field": 4096}
    dense = analyze_geometric_mtf(trace_forward(compiled, fields, dense_sampling, [587.56]), frequencies)
    reference_sampling = {**sampling, "samples_per_field": 10000}
    reference = analyze_geometric_mtf(trace_forward(compiled, fields, reference_sampling, [587.56]), frequencies)

    coarse_high = max(point.mtf_radial for point in coarse.points if point.frequency_lp_per_mm >= 20.0)
    dense_high = max(point.mtf_radial for point in dense.points if point.frequency_lp_per_mm >= 20.0)
    max_dense_reference_error = max(abs(point.mtf_radial - reference.points[index].mtf_radial) for index, point in enumerate(dense.points))
    assert coarse_high > 0.7
    assert dense_high < 0.25
    assert max_dense_reference_error < 0.03
    assert dense.metadata["method"] == "empirical_characteristic_function"
    assert dense.metadata["psf_grid_size"] is None
    assert dense.metadata["samples_per_field"] == 4096
    assert dense.metadata["arrived_count"] == 4096


def test_relative_illumination_matches_cos4_for_unvignetted_thin_lens():
    compiled = compile_system(phase6_thin_lens(sensor_x=100.0, aperture=10.0))
    fields = [
        {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
        {"id": "edge", "type": "angular", "theta_y_deg": 10.0, "theta_z_deg": 0.0},
    ]
    result = analyze_relative_illumination(
        compiled,
        fields,
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
    )
    assert result.rows[0].relative_illumination == pytest.approx(1.0)
    expected = math.cos(math.radians(10.0)) ** 4
    assert result.rows[1].relative_illumination == pytest.approx(expected, rel=1e-6)
    assert result.metadata["method"] == "ray_throughput_times_cos4"


def test_relative_illumination_default_sampling_is_accurate_for_partial_vignetting():
    compiled = compile_system(p002_singlet_system())
    fields = [
        {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
        {"id": "partial", "type": "angular", "theta_y_deg": 40.0, "theta_z_deg": 0.0},
    ]
    sampling_9 = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
    sampling_1000 = {**sampling_9, "samples_per_field": 1000}
    sampling_10000 = {**sampling_9, "samples_per_field": 10000}

    coarse = analyze_relative_illumination(compiled, fields, sampling_9, [587.56])
    default = analyze_relative_illumination(compiled, fields, None, [587.56])
    explicit_default = analyze_relative_illumination(compiled, fields, sampling_1000, [587.56])
    reference = analyze_relative_illumination(compiled, fields, sampling_10000, [587.56])

    coarse_value = coarse.rows[1].relative_illumination
    default_value = default.rows[1].relative_illumination
    reference_value = reference.rows[1].relative_illumination
    assert default_value == explicit_default.rows[1].relative_illumination
    assert abs(default_value - reference_value) < abs(coarse_value - reference_value)
    assert abs(default_value / reference_value - 1.0) < 0.01
    assert abs(coarse_value / reference_value - 1.0) > 0.1
    assert default.metadata == {
        "method": "ray_throughput_times_cos4",
        "radiometric_basis": "weighted_pupil_plane",
        "weighting_method": "equal_pupil_samples_times_field_cos4",
        "samples_per_field": 1000,
        "pupil_distribution": "grid",
        "ray_aiming_mode": "paraxial",
        "ray_aiming_strategy": "paraxial",
        "wavelength_count": 1,
    }


def test_relative_illumination_api_uses_default_sampling_and_reports_metadata():
    from fastapi.testclient import TestClient

    from optics_engine.api.main import app

    client = TestClient(app)
    system_id = client.post("/v1/systems/register", json=p002_singlet_system().model_dump(mode="json")).json()["system_id"]
    response = client.post(
        "/v1/analysis/relative-illumination",
        json={
            "system_id": system_id,
            "fields": [
                {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
                {"id": "partial", "type": "angular", "theta_y_deg": 40.0, "theta_z_deg": 0.0},
            ],
            "wavelengths_nm": [587.56],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["samples_per_field"] == 1000
    assert payload["metadata"]["pupil_distribution"] == "grid"
    assert payload["metadata"]["ray_aiming_mode"] == "paraxial"
    assert payload["metadata"]["weighting_method"] == "equal_pupil_samples_times_field_cos4"
    assert payload["rows"][1]["relative_illumination"] == pytest.approx(0.3099262601)


def test_mtf_apis_report_geometric_ray_sampling_metadata():
    from fastapi.testclient import TestClient

    from optics_engine.api.main import app

    client = TestClient(app)
    system_id = client.post("/v1/systems/register", json=p002_singlet_system().model_dump(mode="json")).json()["system_id"]
    request = {
        "system_id": system_id,
        "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        "ray_sampling": {"samples_per_field": 25, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        "wavelengths_nm": [587.56],
        "frequencies_lp_per_mm": [0.0, 10.0],
    }

    mono_response = client.post("/v1/analysis/mtf", json=request)
    assert mono_response.status_code == 200
    mono_metadata = mono_response.json()["metadata"]
    assert mono_metadata == {
        "method": "empirical_characteristic_function",
        "psf_representation": "geometric_ray_hit_point_cloud",
        "psf_grid_size": None,
        "samples_per_field": 25,
        "pupil_distribution": "grid",
        "ray_aiming_mode": "paraxial",
        "traced_ray_count": 25,
        "arrived_count": 25,
        "wavelength_count": 1,
        "diffraction_included": False,
    }

    white_response = client.post(
        "/v1/analysis/white-mtf",
        json={**request, "wavelength_weights": {"486.13": 1.0, "656.27": 1.0}},
    )
    assert white_response.status_code == 200
    white_payload = white_response.json()
    white_metadata = white_payload["metadata"]
    assert white_metadata["method"] == "empirical_characteristic_function"
    assert white_metadata["psf_grid_size"] is None
    assert white_metadata["samples_per_field"] == 25
    assert white_metadata["pupil_distribution"] == "grid"
    assert white_metadata["traced_ray_count"] == 50
    assert white_metadata["arrived_count"] == 50
    assert white_metadata["wavelength_count"] == 2
    assert white_metadata["combined_weighted_point_count"] == 2500
    assert white_payload["mtf"]["metadata"] == white_metadata


def test_through_focus_mtf_api_returns_field_frequency_defocus_grid():
    from fastapi.testclient import TestClient

    from optics_engine.api.main import app

    client = TestClient(app)
    system_id = client.post("/v1/systems/register", json=p002_singlet_system().model_dump(mode="json")).json()["system_id"]
    fields = [
        {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
        {"id": "edge-y", "type": "angular", "theta_y_deg": 14.0, "theta_z_deg": 0.0},
    ]
    request = {
        "system_id": system_id,
        "fields": fields,
        "ray_sampling": {"samples_per_field": 64, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        "wavelengths_nm": [587.56],
        "frequencies_lp_per_mm": [10.0, 30.0],
        "defocus_range_mm": 0.05,
        "defocus_points": 5,
    }
    response = client.post("/v1/analysis/mtf/through-focus", json=request)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["points"]) == 2 * 2 * 5
    assert payload["metadata"]["defocus_range_mm"] == pytest.approx(0.05)
    assert payload["metadata"]["defocus_points"] == 5
    assert payload["metadata"]["field_count"] == 2
    assert payload["metadata"]["frequency_count"] == 2
    assert payload["metadata"]["diffraction_included"] is False
    assert {point["field_id"] for point in payload["points"]} == {"center", "edge-y"}
    assert {point["frequency_lp_per_mm"] for point in payload["points"]} == {10.0, 30.0}
    assert sorted({point["defocus_mm"] for point in payload["points"]}) == pytest.approx([-0.05, -0.025, 0.0, 0.025, 0.05])


def test_white_psf_and_white_mtf_normalize_wavelength_weights():
    compiled = compile_system(phase6_thin_lens(sensor_x=95.0))
    fields = [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
    weights = {486.13: 1.0, 587.56: 2.0, 656.27: 1.0}

    white_psf = analyze_white_psf(compiled, fields, sampling, weights)
    assert sum(white_psf.wavelength_weights.values()) == pytest.approx(1.0)
    assert white_psf.psf.total_energy > 0

    white_mtf = analyze_white_mtf(compiled, fields, sampling, weights, [0.0, 5.0])
    assert sum(white_mtf.wavelength_weights.values()) == pytest.approx(1.0)
    assert white_mtf.mtf.points[0].mtf_radial == pytest.approx(1.0)
