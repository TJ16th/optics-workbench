from __future__ import annotations

import numpy as np
import pytest

from optics_engine import compile_system, evaluate_system, load_system, trace_forward
from optics_engine.models import StructuredOpticsError


def system():
    return load_system(
        {
            "name": "R89 ray loss",
            "surfaces": [
                {
                    "id": "STOP",
                    "kind": "aperture_stop",
                    "surface_type": "plane",
                    "aperture": {"shape": "circle", "semi_diameter_mm": 5.0},
                },
                {
                    "id": "TL",
                    "kind": "thin_lens",
                    "surface_type": "plane",
                    "focal_length_mm": 50.0,
                    "semi_diameter_mm": 5.0,
                    "thickness_after_mm": 50.0,
                },
                {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 20.0, "height_mm": 20.0}},
            ],
        }
    )


FIELDS = [{"id": "edge", "type": "angular", "theta_y_deg": 8.0, "theta_z_deg": 0.0}]


@pytest.mark.parametrize("distribution", ["random", "sobol"])
def test_stochastic_distributions_require_seed_and_use_it(distribution: str):
    compiled = compile_system(system())
    base = {"samples_per_field": 17, "pupil_distribution": distribution, "ray_aiming": {"mode": "paraxial"}}
    with pytest.raises(StructuredOpticsError) as error:
        trace_forward(compiled, FIELDS, base, [587.56])
    assert error.value.params["required_parameter"] == "seed"

    first = trace_forward(compiled, FIELDS, {**base, "seed": 1}, [587.56])
    repeated = trace_forward(compiled, FIELDS, {**base, "seed": 1}, [587.56])
    changed = trace_forward(compiled, FIELDS, {**base, "seed": 2}, [587.56])
    assert np.array_equal(first.origins, repeated.origins)
    assert np.array_equal(first.sensor_y_mm, repeated.sensor_y_mm, equal_nan=True)
    assert not np.array_equal(first.origins, changed.origins)


def test_ray_loss_ratio_is_automatic_per_field_and_wavelength():
    result = evaluate_system(
        system(),
        {
            "metrics": ["back_focal_length"],
            "fields": FIELDS,
            "wavelengths": [486.13, 587.56],
            "ray_loss_tolerance": 0.2,
            "ray_loss_statuses": ["blocked"],
        },
        configuration={"variables": {"iris_radius_mm": 1000.0}},
        ray_sampling={"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
    )
    losses = [operand for operand in result.operands if operand.metric == "ray_loss_ratio"]
    assert [(row.field_id, row.wavelength_nm) for row in losses] == [("edge", 486.13), ("edge", 587.56)]
    assert all(row.value is not None and row.value > 0.0 for row in losses)
    assert all(row.residual == pytest.approx(row.value / 0.2) for row in losses)
    assert result.merit.metrics["ray_loss_penalty"] == pytest.approx(sum(row.residual**2 for row in losses))


def test_blocked_rays_are_excluded_by_default_but_can_be_selected():
    payload = {
        "metrics": ["back_focal_length"],
        "fields": FIELDS,
        "wavelengths": [587.56],
    }
    default = evaluate_system(
        system(),
        payload,
        ray_sampling={"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "off"}},
    )
    selected = evaluate_system(
        system(),
        {**payload, "ray_loss_statuses": ["blocked"]},
        ray_sampling={"samples_per_field": 9, "pupil_distribution": "grid", "ray_aiming": {"mode": "off"}},
    )
    default_loss = next(row.value for row in default.operands if row.metric == "ray_loss_ratio")
    selected_loss = next(row.value for row in selected.operands if row.metric == "ray_loss_ratio")
    assert default_loss == 0.0
    assert selected_loss >= default_loss
