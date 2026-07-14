from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

from optics_engine import compile_system
from optics_engine.configuration import runtime_layout
from optics_engine.core import field_direction
from optics_engine.reference import trace_forward_reference
from optics_engine.tracing import _trace_raw, _trace_raw_candidates

sys.path.insert(0, str(Path(__file__).parent))
from systems import achromat_doublet_100mm  # noqa: E402


FIELDS = [{"id": "edge", "type": "angular", "theta_y_deg": 1.25, "theta_z_deg": -0.5}]
SAMPLING = {"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}}
WAVELENGTHS = [486.13, 587.56]


def _candidate_systems():
    systems = []
    for delta in (0.0, 0.02, -0.015):
        system = achromat_doublet_100mm().model_copy(deep=True)
        system.surfaces[1].radius_mm += delta
        systems.append(system)
    return systems


def _raw_inputs(compiled_candidates):
    references = [
        trace_forward_reference(compiled, FIELDS, SAMPLING, WAVELENGTHS, {"store_path": True})
        for compiled in compiled_candidates
    ]
    origins = np.stack([reference.origins for reference in references])
    direction = field_direction(1.25, -0.5)
    directions = np.tile(direction, (len(compiled_candidates), origins.shape[1], 1))
    wavelengths = np.stack([reference.wavelengths_nm for reference in references])
    field_ids = [reference.field_ids for reference in references]
    return references, origins, directions, wavelengths, field_ids


def _assert_trace_equal(actual, expected):
    assert np.array_equal(actual.origins, expected.origins)
    assert np.array_equal(actual.directions, expected.directions)
    assert np.array_equal(actual.wavelengths_nm, expected.wavelengths_nm)
    assert actual.field_ids == expected.field_ids
    assert np.array_equal(actual.status, expected.status)
    assert np.array_equal(actual.sensor_y_mm, expected.sensor_y_mm, equal_nan=True)
    assert np.array_equal(actual.sensor_z_mm, expected.sensor_z_mm, equal_nan=True)
    assert np.array_equal(actual.eye_theta_y_deg, expected.eye_theta_y_deg, equal_nan=True)
    assert np.array_equal(actual.eye_theta_z_deg, expected.eye_theta_z_deg, equal_nan=True)
    assert actual.paths == expected.paths


def test_candidate_axis_kernel_matches_independent_raw_and_level0_golden():
    compiled_candidates = [compile_system(system, use_cache=False) for system in _candidate_systems()]
    references, origins, directions, wavelengths, field_ids = _raw_inputs(compiled_candidates)

    batch = _trace_raw_candidates(
        compiled_candidates,
        origins,
        directions,
        wavelengths,
        field_ids=field_ids,
        store_path=True,
        candidate_chunk_size=2,
    )

    assert batch.origins.shape == (3, 18, 3)
    assert batch.directions.shape == (3, 18, 3)
    assert batch.wavelengths_nm.shape == (3, 18)
    assert batch.status.shape == (3, 18)
    assert batch.metadata["surface_data_shape"] == [3, len(compiled_candidates[0].surfaces), 3]
    assert batch.metadata["batch_eligible"] is True
    assert batch.metadata["fallback_used"] is False
    for index, compiled in enumerate(compiled_candidates):
        layout = runtime_layout(compiled)
        independent = _trace_raw(
            compiled,
            origins[index],
            directions[index],
            wavelengths[index],
            field_ids=field_ids[index],
            store_path=True,
            centers_mm=layout.centers_mm,
            rotations=layout.rotations,
        )
        _assert_trace_equal(batch.candidate(index), independent)
        _assert_trace_equal(batch.candidate(index), references[index])


def test_candidate_chunk_size_is_bit_identical():
    compiled_candidates = [compile_system(system, use_cache=False) for system in _candidate_systems()]
    _, origins, directions, wavelengths, field_ids = _raw_inputs(compiled_candidates)
    single = _trace_raw_candidates(
        compiled_candidates, origins, directions, wavelengths, field_ids=field_ids, candidate_chunk_size=1
    )
    all_at_once = _trace_raw_candidates(
        compiled_candidates, origins, directions, wavelengths, field_ids=field_ids, candidate_chunk_size=3
    )

    assert np.array_equal(single.directions, all_at_once.directions)
    assert np.array_equal(single.status, all_at_once.status)
    assert np.array_equal(single.sensor_y_mm, all_at_once.sensor_y_mm, equal_nan=True)
    assert np.array_equal(single.sensor_z_mm, all_at_once.sensor_z_mm, equal_nan=True)
    assert single.paths == all_at_once.paths


def test_ineligible_material_order_uses_independent_fallback():
    systems = _candidate_systems()[:2]
    systems[1].materials = list(reversed(systems[1].materials))
    compiled_candidates = [compile_system(system, use_cache=False) for system in systems]
    references, origins, directions, wavelengths, field_ids = _raw_inputs(compiled_candidates)

    batch = _trace_raw_candidates(compiled_candidates, origins, directions, wavelengths, field_ids=field_ids)

    assert batch.metadata["batch_eligible"] is False
    assert batch.metadata["fallback_used"] is True
    for index, reference in enumerate(references):
        _assert_trace_equal(batch.candidate(index), reference)
