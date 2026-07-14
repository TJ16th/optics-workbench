from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
import re
from typing import Any

from .models import OpticalSystem, StructuredOpticsError


@dataclass(frozen=True)
class VariableBindingRule:
    pattern: str
    kind: str
    unit: str | None
    default_step_floor: float


VARIABLE_BINDING_REGISTRY = (
    VariableBindingRule("iris_radius_mm", "iris", "mm", 1.0e-4),
    VariableBindingRule("{surface_id}_curvature", "curvature", "1/mm", 1.0e-6),
    VariableBindingRule("{surface_id}_radius_mm", "radius", "mm", 1.0e-4),
    VariableBindingRule("{surface_id}_thickness_after_mm", "surface_attribute", "mm", 1.0e-4),
    VariableBindingRule("{surface_id}_focal_length_mm", "surface_attribute", "mm", 1.0e-4),
    VariableBindingRule("{surface_id}_semi_diameter_mm", "surface_attribute", "mm", 1.0e-4),
    VariableBindingRule("{surface_id}_conic", "conic", None, 1.0e-4),
    VariableBindingRule("{surface_id}_A{even_order}", "asphere_coefficient", None, 1.0e-12),
    VariableBindingRule("{group_id}_shift_x_mm", "group_shift", "mm", 1.0e-4),
    VariableBindingRule("{group_id}_shift_y_mm", "group_shift", "mm", 1.0e-4),
    VariableBindingRule("{group_id}_shift_z_mm", "group_shift", "mm", 1.0e-4),
)


def variable_key_patterns() -> list[str]:
    return [rule.pattern for rule in VARIABLE_BINDING_REGISTRY]


@dataclass(frozen=True)
class VariableBinding:
    key: str
    kind: str
    unit: str | None
    target_id: str | None
    parameter: str
    default_step_floor: float

    def default_step(self, value: float) -> float:
        return max(abs(float(value)) * 1.0e-4, self.default_step_floor)


@dataclass(frozen=True)
class VariableApplication:
    system: OpticalSystem
    configuration: dict[str, Any]
    warnings: list[dict[str, Any]] = field(default_factory=list)


_SURFACE_SUFFIXES = {
    "_thickness_after_mm": "thickness_after_mm",
    "_focal_length_mm": "focal_length_mm",
    "_semi_diameter_mm": "semi_diameter_mm",
}
_GROUP_SUFFIXES = ("shift_x_mm", "shift_y_mm", "shift_z_mm")
_ASPHERE_RE = re.compile(r"^(?P<surface_id>.+)_A(?P<order>[0-9]+)$")


def _unknown_variable(key: str) -> StructuredOpticsError:
    return StructuredOpticsError(
        "optics_value_error",
        "Unknown or inapplicable variable key.",
        params={"variable_key": key, "supported_patterns": variable_key_patterns()},
    )


def resolve_variable_binding(system: OpticalSystem, key: str) -> VariableBinding:
    surfaces = {surface.id: surface for surface in system.surfaces}
    groups = {group.id for group in system.groups}
    if key == "iris_radius_mm":
        if any(surface.kind == "aperture_stop" for surface in system.surfaces):
            rule = VARIABLE_BINDING_REGISTRY[0]
            return VariableBinding(key, rule.kind, rule.unit, None, "iris_radius_mm", rule.default_step_floor)
        raise _unknown_variable(key)

    for suffix, parameter in (("_curvature", "curvature"), ("_radius_mm", "radius_mm"), ("_conic", "conic")):
        if key.endswith(suffix) and key[: -len(suffix)] in surfaces:
            surface_id = key[: -len(suffix)]
            surface = surfaces[surface_id]
            if parameter in {"curvature", "radius_mm"} and surface.kind not in {"refractive", "mirror"}:
                raise _unknown_variable(key)
            if parameter == "conic" and surface.surface_type != "aspherical_even":
                raise _unknown_variable(key)
            rule = next(rule for rule in VARIABLE_BINDING_REGISTRY if rule.kind == ("curvature" if parameter == "curvature" else "radius" if parameter == "radius_mm" else "conic"))
            return VariableBinding(key, rule.kind, rule.unit, surface_id, parameter, rule.default_step_floor)

    match = _ASPHERE_RE.match(key)
    if match:
        surface_id = match.group("surface_id")
        order = int(match.group("order"))
        surface = surfaces.get(surface_id)
        if surface is not None and surface.surface_type == "aspherical_even" and order >= 4 and order % 2 == 0:
            rule = next(rule for rule in VARIABLE_BINDING_REGISTRY if rule.kind == "asphere_coefficient")
            return VariableBinding(key, rule.kind, rule.unit, surface_id, f"A{order}", rule.default_step_floor * 1.0e-4 ** max(0, (order - 4) // 2))
        raise _unknown_variable(key)

    for suffix, parameter in _SURFACE_SUFFIXES.items():
        if key.endswith(suffix) and key[: -len(suffix)] in surfaces:
            surface_id = key[: -len(suffix)]
            rule = next(rule for rule in VARIABLE_BINDING_REGISTRY if rule.pattern.endswith(suffix))
            return VariableBinding(key, rule.kind, rule.unit, surface_id, parameter, rule.default_step_floor)

    for parameter in _GROUP_SUFFIXES:
        suffix = f"_{parameter}"
        if key.endswith(suffix) and key[: -len(suffix)] in groups:
            rule = next(rule for rule in VARIABLE_BINDING_REGISTRY if rule.pattern.endswith(suffix))
            return VariableBinding(key, rule.kind, rule.unit, key[: -len(suffix)], parameter, rule.default_step_floor)
    raise _unknown_variable(key)


def _number(key: str, raw_value: Any) -> float:
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise StructuredOpticsError(
            "optics_value_error",
            "Variable value must be a finite number.",
            params={"variable_key": key, "value": raw_value, "constraint": "finite number"},
        ) from exc
    if not math.isfinite(value):
        raise StructuredOpticsError(
            "optics_value_error",
            "Variable value must be a finite number.",
            params={"variable_key": key, "value": raw_value, "constraint": "finite number"},
        )
    return value


def apply_variable_bindings(
    system: OpticalSystem,
    variables: dict[str, Any] | None,
    configuration: dict[str, Any] | None = None,
) -> VariableApplication:
    config = deepcopy(configuration or {})
    if not variables:
        return VariableApplication(system, config)
    updated = OpticalSystem.model_validate(system.model_dump(mode="json"))
    warnings: list[dict[str, Any]] = []
    for key, raw_value in variables.items():
        binding = resolve_variable_binding(updated, str(key))
        value = _number(str(key), raw_value)
        if binding.kind == "iris":
            if value <= 0.0:
                raise StructuredOpticsError(
                    "optics_value_error",
                    "Iris radius must be positive.",
                    params={"variable_key": key, "value": value, "constraint": "value > 0"},
                )
            config.setdefault("variables", {})["iris_radius_mm"] = value
            continue
        if binding.kind == "group_shift":
            config.setdefault("group_positions", {}).setdefault(binding.target_id, {})[binding.parameter] = value
            continue
        surface = next(surface for surface in updated.surfaces if surface.id == binding.target_id)
        if binding.kind == "curvature":
            surface.radius_mm = 0.0 if value == 0.0 else 1.0 / value
        elif binding.kind == "radius":
            surface.radius_mm = value
            if value == 0.0 or abs(value) >= 1.0e6:
                warnings.append(
                    {
                        "severity": "warning",
                        "code": "radius_key_deprecated",
                        "params": {"variable_key": key, "radius_mm": value},
                        "message_en": "Use curvature for stable optimization near a plane surface.",
                    }
                )
        elif binding.kind == "conic":
            surface.conic = value
        elif binding.kind == "asphere_coefficient":
            surface.asphere_coefficients[binding.parameter] = value
        else:
            setattr(surface, binding.parameter, value)
    return VariableApplication(updated, config, warnings)
