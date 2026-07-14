from __future__ import annotations

import numpy as np

from benchmarks.spec_like_benchmark import build_spec_like_system
from optics_engine import compile_system, load_system, trace_forward
from optics_engine.tracing import _AIMING_AFFINE_CACHE


FIELDS = [
    {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
    {"id": "pos_y_5", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0},
]


def _max_sensor_error_mm(actual, expected) -> float:
    mask = actual.arrived_mask & expected.arrived_mask
    if not np.any(mask):
        return 0.0
    errors = np.sqrt((actual.sensor_y_mm[mask] - expected.sensor_y_mm[mask]) ** 2 + (actual.sensor_z_mm[mask] - expected.sensor_z_mm[mask]) ** 2)
    return float(np.max(errors))


def test_affine_aiming_matches_exact_full_aiming_for_spec_like_bundle():
    _AIMING_AFFINE_CACHE.clear()
    compiled = compile_system(load_system(build_spec_like_system()), use_cache=False)
    exact = trace_forward(
        compiled,
        FIELDS,
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "full", "strategy": "exact"}},
        [587.56],
    )
    affine = trace_forward(
        compiled,
        FIELDS,
        {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
        [587.56],
    )

    assert affine.status.tolist() == exact.status.tolist()
    assert np.array_equal(affine.origins, exact.origins)
    assert np.array_equal(affine.sensor_y_mm, exact.sensor_y_mm)
    assert np.array_equal(affine.sensor_z_mm, exact.sensor_z_mm)
    assert _max_sensor_error_mm(affine, exact) == 0.0
    assert affine.metadata["ray_aiming_strategy"] == "affine"
    assert affine.metadata["aiming_solution_kind"] == "exact_bundle_cache"
    assert affine.metadata["aiming_exact_solved_count"] == len(FIELDS) * 9


def test_affine_aiming_cache_warm_starts_repeated_field_wavelength_solution():
    _AIMING_AFFINE_CACHE.clear()
    compiled = compile_system(load_system(build_spec_like_system()), use_cache=False)
    sampling = {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}}

    cold = trace_forward(compiled, [FIELDS[0]], sampling, [587.56])
    warm = trace_forward(compiled, [FIELDS[0]], sampling, [587.56])
    changed_iris = trace_forward(compiled, [FIELDS[0]], sampling, [587.56], {"configuration": {"variables": {"iris_radius_mm": 6.0}}})

    assert cold.metadata["aiming_cache_misses"] == 1
    assert cold.metadata["aiming_cache_hits"] == 0
    assert warm.metadata["aiming_cache_hits"] == 1
    assert warm.metadata["aiming_cache_misses"] == 0
    assert warm.metadata["affine_seed_count"] == 0
    assert warm.metadata["aiming_exact_solved_count"] == 0
    assert np.array_equal(warm.origins, cold.origins)
    assert np.array_equal(warm.sensor_y_mm, cold.sensor_y_mm)
    assert np.array_equal(warm.sensor_z_mm, cold.sensor_z_mm)
    assert changed_iris.metadata["aiming_cache_misses"] == 1
    assert changed_iris.metadata["aiming_cache_hits"] == 0


def test_exact_origin_bundle_cache_is_independent_of_prior_sample_count():
    compiled = compile_system(load_system(build_spec_like_system()), use_cache=False)
    field = [FIELDS[0]]

    def trace(samples_per_field: int, strategy: str = "affine"):
        return trace_forward(
            compiled,
            field,
            {"samples_per_field": samples_per_field, "pupil_distribution": "grid", "ray_aiming": {"mode": "full", "strategy": strategy}},
            [587.56],
        )

    _AIMING_AFFINE_CACHE.clear()
    exact = trace(81, "exact")

    histories = []
    for warm_samples in (None, 9, 25):
        _AIMING_AFFINE_CACHE.clear()
        if warm_samples is not None:
            trace(warm_samples)
        histories.append(trace(81))

    repeated = trace(81)
    for result in [*histories, repeated]:
        assert result.status.tolist() == exact.status.tolist()
        assert np.array_equal(result.origins, exact.origins)
        assert np.array_equal(result.sensor_y_mm, exact.sensor_y_mm)
        assert np.array_equal(result.sensor_z_mm, exact.sensor_z_mm)

    assert histories[0].metadata["aiming_cache_misses"] == 1
    assert histories[1].metadata["aiming_cache_misses"] == 1
    assert histories[2].metadata["aiming_cache_misses"] == 1
    assert repeated.metadata["aiming_cache_hits"] == 1
