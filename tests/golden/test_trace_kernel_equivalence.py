from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

from benchmarks.spec_like_benchmark import build_spec_like_system
from optics_engine import compile_system, load_system, trace_forward
from optics_engine.reference import trace_forward_reference

sys.path.insert(0, str(Path(__file__).parent))
from systems import WAVELENGTHS, achromat_doublet_100mm, cassegrain_v2_3  # noqa: E402


def _max_sensor_error_mm(actual, expected) -> float:
    actual_y = np.asarray(actual.sensor_y_mm, dtype=float)
    actual_z = np.asarray(actual.sensor_z_mm, dtype=float)
    expected_y = np.asarray(expected.sensor_y_mm, dtype=float)
    expected_z = np.asarray(expected.sensor_z_mm, dtype=float)
    mask = np.isfinite(actual_y) & np.isfinite(actual_z) & np.isfinite(expected_y) & np.isfinite(expected_z)
    if not np.any(mask):
        return 0.0
    errors = np.sqrt((actual_y[mask] - expected_y[mask]) ** 2 + (actual_z[mask] - expected_z[mask]) ** 2)
    return float(np.max(errors))


def _assert_level1_matches_level0(system, fields, sampling, wavelengths, tolerance_mm: float) -> float:
    compiled = compile_system(system, use_cache=False)
    level1 = trace_forward(compiled, fields, sampling, wavelengths)
    level0 = trace_forward_reference(compiled, fields, sampling, wavelengths)

    assert level1.status.tolist() == level0.status.tolist()
    assert level1.arrived_mask.tolist() == level0.arrived_mask.tolist()
    max_error = _max_sensor_error_mm(level1, level0)
    assert max_error <= tolerance_mm
    return max_error


@pytest.mark.parametrize(
    ("system_factory", "fields", "sampling", "wavelengths", "tolerance_mm"),
    [
        (
            achromat_doublet_100mm,
            [
                {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
                {"id": "pos_y_1", "type": "angular", "theta_y_deg": 1.0, "theta_z_deg": 0.0},
            ],
            {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
            WAVELENGTHS,
            1.0e-9,
        ),
        (
            cassegrain_v2_3,
            [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
            {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
            [587.56],
            1.0e-9,
        ),
    ],
)
def test_level1_batch_trace_matches_level0_reference_for_golden_systems(system_factory, fields, sampling, wavelengths, tolerance_mm):
    _assert_level1_matches_level0(system_factory(), fields, sampling, wavelengths, tolerance_mm)


def test_level1_batch_trace_matches_level0_reference_for_spec_like_asphere_system():
    system = load_system(build_spec_like_system())
    fields = [
        {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
        {"id": "pos_y_5", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0},
    ]
    sampling = {"samples_per_field": 21, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}

    _assert_level1_matches_level0(system, fields, sampling, WAVELENGTHS, 1.0e-8)
