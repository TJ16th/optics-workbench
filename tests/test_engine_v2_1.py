import math
import os
import time

import numpy as np
import pytest

from optics_engine import (
    analyze_paraxial,
    analyze_distortion,
    analyze_longitudinal_aberration,
    analyze_ray_fan,
    analyze_spot,
    compile_system,
    health_payload,
    load_system,
    meta_payload,
    resolve_image_plane_policy,
    trace_forward,
    trace_reverse,
)
from optics_engine.artifacts import ARTIFACT_STORE, ArtifactStore
from optics_engine.models import Material


def thin_lens_system(focal_length=100.0, sensor_x=95.0):
    return load_system(
        {
            "name": "v2_1_thin_lens",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "thickness_after_mm": 0.0,
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "focal_length_mm": focal_length,
                    "semi_diameter_mm": 5.0,
                    "thickness_after_mm": sensor_x,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def cassegrain_v2_1_system():
    return load_system(
        {
            "name": "v2_1_cassegrain",
            "surfaces": [
                {
                    "id": "M1",
                    "kind": "mirror",
                    "radius_mm": -2000.0,
                    "thickness_after_mm": -650.0,
                    "semi_diameter_mm": 100.0,
                },
                {
                    "id": "M2",
                    "kind": "mirror",
                    "radius_mm": -1050.0,
                    "thickness_after_mm": 1050.0,
                    "semi_diameter_mm": 40.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 30.0, "height_mm": 30.0}},
            ],
        }
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
                    "semi_diameter_mm": 15.0,
                },
                {
                    "id": "S2",
                    "kind": "refractive",
                    "surface_type": "spherical",
                    "radius_mm": -50.0,
                    "thickness_after_mm": 46.5,
                    "material_after": "AIR",
                    "semi_diameter_mm": 15.0,
                },
                {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
        }
    )


def p003_achromat_system():
    return load_system(
        {
            "name": "P003 Achromat Doublet 100mm",
            "units": "mm",
            "optical_axis": "+X",
            "system_type": "focal",
            "wavelengths_nm": {"primary": 587.56, "samples": [486.13, 587.56, 656.27]},
            "materials": [
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
            ],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "surface_type": "plane",
                    "thickness_after_mm": 1.5,
                    "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0},
                    "aperture": {"shape": "circle", "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0}},
                },
                {"id": "S1", "kind": "refractive", "surface_type": "spherical", "radius_mm": 62.5, "thickness_after_mm": 4.0, "material_after": "N-BK7", "semi_diameter_mm": 14.0},
                {"id": "S2", "kind": "refractive", "surface_type": "spherical", "radius_mm": -43.0, "thickness_after_mm": 2.0, "material_after": "N-F2", "semi_diameter_mm": 14.0},
                {"id": "S3", "kind": "refractive", "surface_type": "spherical", "radius_mm": -125.0, "thickness_after_mm": 96.0, "material_after": "AIR", "semi_diameter_mm": 14.0},
                {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
            ],
            "groups": [
                {"id": "FOCUS_G", "name": "Focus group", "from_surface": "S1", "to_surface": "S3"},
                {"id": "OIS_G", "name": "OIS decenter/tilt group", "from_surface": "S1", "to_surface": "S3"},
            ],
            "zoom_positions": [
                {"id": "infinity", "focal_length_nominal_mm": 100.0, "group_positions": {"FOCUS_G": {"shift_x_mm": 0.0}}},
                {"id": "close_focus", "focal_length_nominal_mm": 100.0, "group_positions": {"FOCUS_G": {"shift_x_mm": 2.0}}},
            ],
        }
    )


def test_p003_ois_group_moves_full_cemented_doublet():
    compiled = compile_system(p003_achromat_system())
    assert compiled.group_ranges["FOCUS_G"] == (1, 3)
    assert compiled.group_ranges["OIS_G"] == (1, 3)


def path_segment_slopes_y(path):
    points = [entry["point_mm"] for entry in path]
    return [(right[1] - left[1]) / (right[0] - left[0]) for left, right in zip(points, points[1:])]


def test_health_and_meta_payloads_advertise_v2_3_capabilities_and_enumerations():
    assert health_payload() == {"status": "ok"}
    meta = meta_payload()
    assert meta["api_schema_version"] == "2.3.0"
    assert meta["result_schema_version"] == "2.3.0"
    assert "best_focus_rms" in meta["capabilities"]["image_plane_policy_modes"]
    assert meta["capabilities"]["artifact_store"] is True
    assert meta["capabilities"]["artifacts"]["enabled"] is True
    assert meta["capabilities"]["artifacts"]["ttl_seconds"] > 0.0
    assert "enumerations" in meta
    assert "rms_spot_radius" in meta["enumerations"]["metrics"]
    assert "negative_air_gap" in meta["enumerations"]["error_codes"]
    assert "missing_aperture_stop" in meta["enumerations"]["warning_codes"]
    assert "aiming_failed" in meta["enumerations"]["ray_status_codes"]
    assert "{surface_id}_curvature" in meta["enumerations"]["variable_key_patterns"]


def test_trace_paths_include_singlet_surface_hits_and_refraction_slopes():
    compiled = compile_system(p002_singlet_system())
    trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 3, "pupil_distribution": "fan_y", "ray_aiming": {"mode": "paraxial"}},
        [587.56],
        {"store_path": True},
    )
    marginal = trace.paths[2]
    assert [entry["surface_id"] for entry in marginal] == ["STOP", "S1", "S2", "IMG"]
    assert [entry["point_mm"][0] for entry in marginal] == pytest.approx([0.0, 2.644149, 6.388831, 53.5], abs=1.0e-6)

    slopes = path_segment_slopes_y(marginal)
    assert slopes[0] == pytest.approx(0.0, abs=1.0e-12)
    assert slopes[1] == pytest.approx(-0.05506437, abs=1.0e-6)
    assert slopes[2] == pytest.approx(-0.16916736, abs=1.0e-6)
    assert abs(slopes[1]) > abs(slopes[0])
    assert abs(slopes[2]) > abs(slopes[1])


def _runtime_iris_system():
    return load_system(
        {
            "name": "runtime iris variable",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "surface_type": "plane",
                    "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0},
                    "aperture": {"shape": "circle", "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0}},
                    "thickness_after_mm": 50.0,
                },
                {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 30.0, "height_mm": 30.0}},
            ],
        }
    )


def _trace_stop_y_extent(compiled, configuration=None):
    result = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": 3, "pupil_distribution": "fan_y"},
        [587.56],
        {"store_path": True, "configuration": configuration or {}},
    )
    stop_points = [entry["local_point_mm"] for path in result.paths for entry in path if entry["surface_id"] == "STOP"]
    return max(abs(point[1]) for point in stop_points), result


def test_runtime_iris_radius_variable_defaults_and_overrides_are_stateless():
    system = _runtime_iris_system()
    compiled = compile_system(system)

    assert compiled.surfaces[0].semi_diameter_mm == pytest.approx(10.0)
    assert compiled.surfaces[0].aperture.semi_diameter_mm == pytest.approx(10.0)

    default_extent, default_result = _trace_stop_y_extent(compiled)
    small_extent, small_result = _trace_stop_y_extent(compiled, {"variables": {"iris_radius_mm": 3.0}})
    default_again_extent, _ = _trace_stop_y_extent(compiled)
    large_extent, large_result = _trace_stop_y_extent(compiled, {"variables": {"iris_radius_mm": 8.0}})

    assert default_extent == pytest.approx(10.0)
    assert small_extent == pytest.approx(3.0)
    assert default_again_extent == pytest.approx(10.0)
    assert large_extent == pytest.approx(8.0)
    assert default_result.status.tolist() == ["alive", "alive", "alive"]
    assert small_result.status.tolist() == ["alive", "alive", "alive"]
    assert large_result.status.tolist() == ["alive", "alive", "alive"]


def test_runtime_iris_radius_variable_controls_aperture_blocking():
    system = load_system(
        {
            "name": "runtime iris blocking",
            "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "surface_type": "plane",
                    "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0},
                    "aperture": {"shape": "circle", "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0}},
                    "thickness_after_mm": 50.0,
                },
                {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 30.0, "height_mm": 30.0}},
            ],
        }
    )
    compiled = compile_system(system)

    from optics_engine.tracing import _trace_raw

    origins = np.array([[-10.0, 5.0, 0.0]], dtype=float)
    directions = np.array([[1.0, 0.0, 0.0]], dtype=float)
    wavelengths = np.array([587.56], dtype=float)

    blocked = _trace_raw(
        compiled,
        origins,
        directions,
        wavelengths,
        store_path=True,
        configuration={"variables": {"iris_radius_mm": 3.0}},
    )
    passed = _trace_raw(
        compiled,
        origins,
        directions,
        wavelengths,
        store_path=True,
        configuration={"variables": {"iris_radius_mm": 8.0}},
    )
    assert blocked.status.tolist() == ["blocked"]
    assert passed.status.tolist() == ["alive"]


def test_image_plane_policy_paraxial_image_moves_evaluation_plane_without_mutating_system():
    compiled = compile_system(thin_lens_system(focal_length=100.0, sensor_x=95.0))
    fields = [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}

    fixed_trace = trace_forward(compiled, fields, sampling, [587.56])
    fixed_spot = analyze_spot(fixed_trace)
    assert fixed_spot.rms_radius_mm is not None
    assert fixed_spot.rms_radius_mm > 0.0

    resolution = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {"mode": "paraxial_image", "apply_to": "evaluation_plane"},
    )
    focused_trace = trace_forward(
        resolution.compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": resolution.configuration},
    )
    focused_spot = analyze_spot(focused_trace)
    assert resolution.metadata["sensor_x_mm"] == pytest.approx(95.0)
    assert resolution.metadata["evaluation_plane_x_mm"] == pytest.approx(100.0)
    assert focused_spot.rms_radius_mm == pytest.approx(0.0, abs=1e-9)

    unchanged = analyze_paraxial(compiled)
    assert unchanged.paraxial_image_position_mm == pytest.approx(100.0)


def test_image_plane_policy_best_focus_rms_and_sweep_report_metadata():
    compiled = compile_system(thin_lens_system(focal_length=100.0, sensor_x=95.0))
    fields = [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}

    resolution = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {"mode": "best_focus_rms", "search": {"range_mm": 1.0, "tolerance_mm": 1.0e-4}},
    )
    assert resolution.metadata["solve_status"] == "converged"
    assert resolution.metadata["evaluation_plane_x_mm"] == pytest.approx(100.0, abs=1.0e-3)

    sweep = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {"mode": "sweep", "search": {"range_mm": 1.0, "steps": 5}},
    )
    assert sweep.metadata["solve_status"] == "swept"
    assert len(sweep.metadata["focus_curve"]) == 5
    best_from_sweep = min(sweep.metadata["focus_curve"], key=lambda row: row["metric"])
    assert best_from_sweep["offset_from_sensor_mm"] == pytest.approx(sweep.metadata["solved_offset_from_sensor_mm"])


def test_image_plane_policy_modes_and_nonconvergence_warning():
    compiled = compile_system(thin_lens_system(focal_length=100.0, sensor_x=95.0))
    fields = [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}

    paraxial = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {"mode": "paraxial_image", "apply_to": "report_only"},
    )
    assert paraxial.metadata["solved_evaluation_plane_x_mm"] == pytest.approx(100.0)
    assert paraxial.metadata["evaluation_plane_x_mm"] == pytest.approx(paraxial.metadata["sensor_x_mm"])

    custom = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {"mode": "custom_offset", "offset_mm": 2.5},
    )
    assert custom.metadata["offset_from_sensor_mm"] == pytest.approx(2.5)

    mtf = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {"mode": "best_focus_mtf", "search": {"range_mm": 1.0, "tolerance_mm": 1.0e-3}},
    )
    assert mtf.metadata["solve_status"] == "converged"
    assert mtf.metadata["evaluation_plane_x_mm"] == pytest.approx(100.0, abs=1.0e-2)

    not_converged = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {"mode": "best_focus_mtf", "search": {"range_mm": 1.0, "tolerance_mm": 1.0e-12, "max_iterations": 0}},
    )
    assert not_converged.metadata["solve_status"] == "not_converged"
    assert not_converged.metadata["warnings"][0]["code"] == "solve_not_converged"


def test_image_plane_policy_afocal_error_uses_v2_3_code():
    afocal = load_system(
        {
            "name": "afocal",
            "system_type": "afocal",
            "surfaces": [
                {"id": "TL1", "kind": "thin_lens", "focal_length_mm": 100.0, "thickness_after_mm": 150.0},
                {"id": "TL2", "kind": "thin_lens", "focal_length_mm": 50.0, "thickness_after_mm": 50.0},
                {"id": "EYE", "kind": "eye_reference", "eye": {"pupil_diameter_mm": 4.0}},
            ],
        }
    )
    compiled = compile_system(afocal)
    with pytest.raises(Exception) as excinfo:
        resolve_image_plane_policy(
            compiled,
            [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
            {"samples_per_field": 1},
            [587.56],
            {"configuration": {}},
            {"mode": "best_focus_rms"},
        )
    assert getattr(excinfo.value, "code", None) == "image_plane_policy_not_applicable"


@pytest.mark.performance
@pytest.mark.skipif(os.environ.get("OPTICS_RUN_PERF_TESTS") != "1", reason="timing-sensitive performance check; run with OPTICS_RUN_PERF_TESTS=1")
def test_image_plane_policy_best_focus_rms_is_within_fixed_sensor_speed_budget():
    compiled = compile_system(thin_lens_system(focal_length=100.0, sensor_x=95.0))
    fields = [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}

    for _ in range(3):
        trace_forward(compiled, fields, sampling, [587.56])
        resolve_image_plane_policy(
            compiled,
            fields,
            sampling,
            [587.56],
            {"configuration": {}},
            {"mode": "best_focus_rms", "search": {"range_mm": 1.0, "tolerance_mm": 1.0e-3}},
        )

    iterations = 30
    start = time.perf_counter()
    for _ in range(iterations):
        trace_forward(compiled, fields, sampling, [587.56])
    fixed_seconds = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(iterations):
        resolve_image_plane_policy(
            compiled,
            fields,
            sampling,
            [587.56],
            {"configuration": {}},
            {"mode": "best_focus_rms", "search": {"range_mm": 1.0, "tolerance_mm": 1.0e-3}},
        )
    best_focus_seconds = time.perf_counter() - start

    assert best_focus_seconds / fixed_seconds < 3.0


def test_image_plane_policy_focus_group_and_merit_modes_report_solution():
    system = thin_lens_system(focal_length=100.0, sensor_x=95.0).model_dump(mode="json")
    system["groups"] = [{"id": "FOCUS", "from_surface": "TL", "to_surface": "TL"}]
    compiled = compile_system(load_system(system))
    fields = [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}]
    sampling = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}

    focused = resolve_image_plane_policy(
        compiled,
        fields,
        sampling,
        [587.56],
        {"configuration": {}},
        {
            "mode": "best_focus_merit",
            "apply_to": "focus_group",
            "focus_group_id": "FOCUS",
            "criteria": {"metrics": [{"metric": "rms_spot_radius", "weight": 1.0}]},
            "search": {"range_mm": 4.0, "tolerance_mm": 1.0e-3},
        },
    )
    assert focused.metadata["solve_status"] == "converged"
    assert focused.metadata["solved_focus_group_shift_mm"] is not None
    assert focused.metadata["evaluation_plane_x_mm"] == pytest.approx(focused.metadata["sensor_x_mm"])


def test_ray_fan_longitudinal_distortion_and_profiling_are_available():
    compiled = compile_system(thin_lens_system(focal_length=100.0, sensor_x=100.0))
    fields = [{"id": "edge", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0}]
    sampling = {"samples_per_field": 7, "pupil_distribution": "fan_y", "ray_aiming": {"mode": "paraxial"}}

    fan = analyze_ray_fan(compiled, fields, sampling, [587.56])
    assert len(fan.points) == 7
    assert fan.metadata["pupil_distribution"] == "fan_y"

    longitudinal = analyze_longitudinal_aberration(compiled, fields, sampling, [587.56])
    assert len(longitudinal.points) == 7
    assert longitudinal.metadata["reference_x_mm"] == pytest.approx(100.0)

    distortion = analyze_distortion(compiled, fields, [587.56])
    assert len(distortion.rows) == 1
    assert distortion.rows[0].ideal_y_mm == pytest.approx(100.0 * math.tan(math.radians(5.0)))

    trace = trace_forward(compiled, fields, sampling, [587.56], {"profiling": True})
    assert trace.metadata["profiling"]["total_rays"] == 7
    assert trace.metadata["profiling"]["compile_ms"] == 0.0
    assert trace.metadata["profiling"]["compile_cache_hit"] is None
    assert trace.metadata["profiling"]["aiming_ms"] >= 0.0
    assert trace.metadata["profiling"]["trace_ms"] >= 0.0
    assert trace.metadata["profiling"]["analysis_postprocessing_ms"] == 0.0
    assert trace.metadata["profiling"]["cache_hits"] >= 0
    assert trace.metadata["profiling"]["cache_misses"] >= 0
    assert "aiming_iterations_mean" in trace.metadata["profiling"]
    assert trace.metadata["evaluated_fields"][0]["id"] == "edge"
    assert trace.metadata["wavelengths_nm"] == [587.56]
    assert trace.metadata["pupil_distribution"] == "fan_y"


def test_reverse_trace_runs_from_sensor_to_object_side():
    compiled = compile_system(thin_lens_system(focal_length=100.0, sensor_x=100.0))
    reverse = trace_reverse(compiled, [{"y_mm": 0.0, "z_mm": 0.0}], wavelengths=[587.56])
    assert reverse.status.tolist() == ["alive"]
    assert reverse.metadata["method"] == "reverse_surface_sequence"
    assert reverse.directions.shape == (1, 3)


def test_v2_1_material_models_are_available():
    nd_vd = Material(id="approx", type="nd_vd", nd=1.6, vd=50.0)
    assert nd_vd.refractive_index(587.56) == pytest.approx(1.6)
    assert nd_vd.refractive_index(486.13) > nd_vd.refractive_index(656.27)

    table = Material(
        id="table",
        type="custom_table",
        table=[{"wavelength_nm": 500.0, "n": 1.5}, {"wavelength_nm": 600.0, "n": 1.6}],
    )
    assert table.refractive_index(550.0) == pytest.approx(1.55)

    catalog = Material(id="N-BK7", type="catalog")
    assert catalog.refractive_index(587.56) == pytest.approx(1.5168, rel=1.0e-4)


def test_cassegrain_v2_1_paraxial_values_match_spec():
    paraxial = analyze_paraxial(compile_system(cassegrain_v2_1_system()))
    assert paraxial.effective_focal_length_mm == pytest.approx(3000.0, rel=1e-12)
    assert paraxial.back_focal_length_mm == pytest.approx(1050.0, rel=1e-12)
    assert paraxial.paraxial_image_position_mm == pytest.approx(400.0, rel=1e-12)


def test_artifact_store_round_trips_bytes():
    artifact = ARTIFACT_STORE.put("json", b"{\"ok\":true}", content_type="application/json", id="unit-test")
    loaded = ARTIFACT_STORE.get("json", "unit-test")
    assert loaded is not None
    assert loaded.content == b"{\"ok\":true}"
    assert artifact.expires_at == loaded.expires_at


def test_artifact_store_uses_temp_files_and_reports_expiry(tmp_path):
    store = ArtifactStore(ttl_seconds=0.01, root_dir=tmp_path)
    artifact = store.put("json", b"{\"ok\":true}", content_type="application/json", id="short")
    assert artifact.path.startswith(str(tmp_path))
    assert store.get_with_status("json", "short")[1] == "ok"

    time.sleep(0.02)
    loaded, status = store.get_with_status("json", "short")
    assert loaded is None
    assert status == "expired"
    assert not (tmp_path / "json" / "short").exists()
    assert store.get_with_status("json", "short")[1] == "not_found"


def test_api_helpers_support_system_id_and_artifact_endpoint():
    pytest.importorskip("fastapi")
    from optics_engine.api import main as api

    registered = api.register(thin_lens_system().model_dump(mode="json"))
    paraxial = api.paraxial({"system_id": registered["system_id"]})
    assert paraxial["paraxial_image_position_mm"] == pytest.approx(100.0)
    assert api.health() == {"status": "ok"}
    assert api.meta()["api_schema_version"] == "2.3.0"

    ARTIFACT_STORE.put("json", b"{\"from_api\":true}", content_type="application/json", id="api-unit-test")
    response = api.artifact("json", "api-unit-test")
    assert response.media_type == "application/json"
    assert response.body == b"{\"from_api\":true}"


def test_http_api_v2_1_smoke_with_artifact_fetch():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from optics_engine.api.main import app

    client = TestClient(app)
    assert client.get("/v1/health").json() == {"status": "ok"}
    meta = client.get("/v1/meta").json()
    assert meta["api_schema_version"] == "2.3.0"
    assert "enumerations" in meta

    system_payload = thin_lens_system(focal_length=100.0, sensor_x=95.0).model_dump(mode="json")
    registered = client.post("/v1/systems/register", json=system_payload)
    assert registered.status_code == 200
    system_id = registered.json()["system_id"]

    spot = client.post(
        "/v1/analysis/spot",
        json={
            "system_id": system_id,
            "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
            "ray_sampling": {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
            "image_plane_policy": {"mode": "paraxial_image"},
            "options": {"profiling": True},
        },
    )
    assert spot.status_code == 200
    spot_json = spot.json()
    assert spot_json["metadata"]["evaluation_plane"]["evaluation_plane_x_mm"] == pytest.approx(100.0)
    spot_profile = spot_json["metadata"]["profiling"]
    assert spot_profile["compile_cache_hit"] is True
    assert spot_profile["compile_ms"] >= 0.0
    assert spot_profile["analysis_postprocessing_ms"] >= 0.0
    assert spot_profile["http_total_ms"] >= spot_profile["total_ms"]
    assert spot_json["metadata"]["artifact_expires_at"]["spot_points"] > time.time()
    artifact_uri = spot_json["artifacts"]["spot_points"]
    category, artifact_id = artifact_uri.removeprefix("artifact://").split("/")
    artifact = client.get(f"/v1/artifacts/{category}/{artifact_id}")
    assert artifact.status_code == 200
    assert artifact.headers["content-type"].startswith("application/json")

    p002_payload = p002_singlet_system().model_dump(mode="json")
    p002_id = client.post("/v1/systems/register", json=p002_payload).json()["system_id"]
    trace = client.post(
        "/v1/trace/forward",
        json={
            "system_id": p002_id,
            "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
            "ray_sampling": {"samples_per_field": 3, "pupil_distribution": "fan_y", "ray_aiming": {"mode": "paraxial"}},
            "wavelengths_nm": [587.56],
            "options": {"store_path": True, "profiling": True},
        },
    )
    assert trace.status_code == 200
    trace_json = trace.json()
    assert [entry["surface_id"] for entry in trace_json["paths"][2]] == ["STOP", "S1", "S2", "IMG"]
    trace_profile = trace_json["metadata"]["profiling"]
    assert trace_profile["compile_cache_hit"] is True
    assert trace_profile["compile_ms"] >= 0.0
    assert trace_profile["aiming_ms"] >= 0.0
    assert trace_profile["trace_ms"] >= 0.0
    assert trace_profile["analysis_postprocessing_ms"] == 0.0
    assert trace_profile["total_rays"] == 3
    assert trace_profile["http_total_ms"] >= trace_profile["total_ms"]

    for system, expected_surfaces in [
        (p002_singlet_system(), ["STOP", "S1", "S2", "IMG"]),
        (p003_achromat_system(), ["STOP", "S1", "S2", "S3", "IMG"]),
    ]:
        registered_preview = client.post("/v1/systems/register", json=system.model_dump(mode="json"))
        assert registered_preview.status_code == 200
        preview = client.post(
            "/v1/education/preview",
            json={
                "system_id": registered_preview.json()["system_id"],
                "fields": [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
                "ray_sampling": {"samples_per_field": 5, "pupil_distribution": "fan_y"},
                "wavelengths_nm": [587.56],
                "options": {"profiling": True},
            },
        )
        assert preview.status_code == 200
        preview_json = preview.json()
        assert "paths" in preview_json
        assert len(preview_json["paths"]) == len(preview_json["status"])
        alive_path = next(path for path, status in zip(preview_json["paths"], preview_json["status"]) if status == "alive")
        assert [entry["surface_id"] for entry in alive_path] == expected_surfaces
        assert "trace_ms" in preview_json["metadata"]["profiling"]

    material = client.post(
        "/v1/materials/refractive-index",
        json={"id": "N15", "type": "constant", "n": 1.5, "wavelengths_nm": [486.1, 587.56]},
    )
    assert material.status_code == 200
    assert [row["n"] for row in material.json()["samples"]] == [1.5, 1.5]
