from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from optics_engine.api.main import app
from optics_engine.tracing import _unit_disk_samples_with_weights


def system_payload() -> dict:
    return {
        "name": "R89 sampling",
        "materials": [{"id": "AIR", "type": "constant", "n": 1.0}],
        "surfaces": [
            {"id": "STOP", "kind": "aperture_stop", "aperture": {"shape": "circle", "semi_diameter_mm": 5.0}},
            {"id": "TL", "kind": "thin_lens", "focal_length_mm": 50.0, "semi_diameter_mm": 5.0, "thickness_after_mm": 48.0},
            {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 20.0, "height_mm": 20.0}},
        ],
    }


def test_specialized_pupil_distributions_have_distinct_coordinates_and_valid_weights():
    distributions = ["grid", "polar", "hexapolar", "gaussian_quadrature", "sobol"]
    samples = {}
    for distribution in distributions:
        seed = 7 if distribution == "sobol" else None
        points, weights = _unit_disk_samples_with_weights(16, distribution, seed)
        samples[distribution] = points
        assert points.shape == (16, 2)
        assert weights.shape == (16,)
        assert np.all(np.linalg.norm(points, axis=1) <= 1.0 + 1.0e-12)
        assert np.sum(weights) == pytest.approx(1.0, abs=1.0e-15)
    for index, left in enumerate(distributions):
        for right in distributions[index + 1 :]:
            assert not np.array_equal(samples[left], samples[right]), f"{left} unexpectedly equals {right}"

    gaussian_weights = _unit_disk_samples_with_weights(16, "gaussian_quadrature")[1]
    assert np.unique(np.round(gaussian_weights, 15)).size > 1


def test_sampling_api_reports_weights_and_distinct_trace_results():
    client = TestClient(app)
    registration = client.post("/v1/systems/register", json=system_payload())
    assert registration.status_code == 200
    system_id = registration.json()["system_id"]
    sensor_results = {}
    for distribution in ["grid", "polar", "hexapolar", "gaussian_quadrature", "sobol"]:
        sampling = {
            "samples_per_field": 16,
            "pupil_distribution": distribution,
            "ray_aiming": {"mode": "paraxial"},
        }
        if distribution == "sobol":
            sampling["seed"] = 7
        response = client.post(
            "/v1/trace/forward",
            json={
                "system_id": system_id,
                "fields": [{"id": "edge", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0}],
                "ray_sampling": sampling,
                "wavelengths_nm": [587.56],
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["metadata"]["pupil_weights"]) == 16
        sensor_results[distribution] = body["sensor_y_mm"]
    assert len({tuple(values) for values in sensor_results.values()}) == len(sensor_results)


def test_grid_fans_and_seeded_random_remain_deterministic():
    for distribution, seed in (("grid", None), ("fan_y", None), ("fan_z", None), ("random", 11)):
        first = _unit_disk_samples_with_weights(21, distribution, seed)
        second = _unit_disk_samples_with_weights(21, distribution, seed)
        assert np.array_equal(first[0], second[0])
        assert np.array_equal(first[1], second[1])
