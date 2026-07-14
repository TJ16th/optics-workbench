from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .configuration import runtime_layout
from .models import OpticalSystem, StructuredOpticsError
from .paraxial import analyze_paraxial
from .system import CompiledSystem, compile_system


@dataclass(frozen=True)
class ParaxialImageDistanceSolveResult:
    type: str
    thickness_of: str
    previous_thickness_after_mm: float
    thickness_after_mm: float
    paraxial_image_position_mm: float
    sensor_position_mm: float
    converged: bool


def solve_paraxial_image_distance(
    compiled: CompiledSystem,
    thickness_of: str,
    configuration: dict[str, Any] | None = None,
) -> tuple[OpticalSystem, ParaxialImageDistanceSolveResult]:
    if compiled.sensor_index is None:
        raise StructuredOpticsError(
            "optics_value_error",
            "Paraxial image-distance solve requires a sensor.",
            params={"solve_type": "paraxial_image_distance", "required": "sensor"},
        )
    try:
        surface_index = compiled.surface_index(thickness_of)
    except KeyError as exc:
        raise StructuredOpticsError(
            "optics_value_error",
            "Unknown solve thickness surface.",
            params={"solve_type": "paraxial_image_distance", "thickness_of": thickness_of},
        ) from exc
    if surface_index != compiled.sensor_index - 1:
        raise StructuredOpticsError(
            "optics_value_error",
            "Paraxial image-distance solve currently requires the final air gap before the sensor.",
            params={
                "solve_type": "paraxial_image_distance",
                "thickness_of": thickness_of,
                "required_surface_id": compiled.surfaces[compiled.sensor_index - 1].id,
            },
        )
    surface = compiled.surfaces[surface_index]
    if (surface.material_after or "AIR") != "AIR":
        raise StructuredOpticsError(
            "optics_value_error",
            "Paraxial image-distance solve requires an air gap.",
            params={"solve_type": "paraxial_image_distance", "thickness_of": thickness_of, "material_after": surface.material_after},
        )
    paraxial = analyze_paraxial(compiled, configuration)
    image_position = paraxial.paraxial_image_position_mm
    if image_position is None:
        raise StructuredOpticsError(
            "optics_value_error",
            "Paraxial image position is unavailable for this system.",
            params={"solve_type": "paraxial_image_distance", "thickness_of": thickness_of},
        )
    layout = runtime_layout(compiled, configuration)
    sensor_position = float(layout.centers_mm[compiled.sensor_index, 0])
    previous = float(surface.thickness_after_mm)
    resolved = previous + float(image_position) - sensor_position
    if resolved < 0.0:
        raise StructuredOpticsError(
            "infeasible",
            "Solved paraxial image distance would make the final air gap negative.",
            params={"thickness_of": thickness_of, "thickness_after_mm": resolved},
        )
    updated = OpticalSystem.model_validate(compiled.system.model_dump(mode="json"))
    updated.surfaces[surface_index].thickness_after_mm = resolved
    solved_compiled = compile_system(updated)
    solved_layout = runtime_layout(solved_compiled, configuration)
    solved_paraxial = analyze_paraxial(solved_compiled, configuration)
    solved_sensor = float(solved_layout.centers_mm[solved_compiled.sensor_index, 0])
    solved_image = float(solved_paraxial.paraxial_image_position_mm)
    result = ParaxialImageDistanceSolveResult(
        type="paraxial_image_distance",
        thickness_of=thickness_of,
        previous_thickness_after_mm=previous,
        thickness_after_mm=resolved,
        paraxial_image_position_mm=solved_image,
        sensor_position_mm=solved_sensor,
        converged=abs(solved_sensor - solved_image) <= 1.0e-9,
    )
    return updated, result


def resolve_configuration_solves(
    system: OpticalSystem,
    configuration: dict[str, Any] | None,
) -> tuple[OpticalSystem, dict[str, Any], list[ParaxialImageDistanceSolveResult]]:
    resolved_configuration = deepcopy(configuration or {})
    solve_requests = list(resolved_configuration.get("solves", []))
    results: list[ParaxialImageDistanceSolveResult] = []
    updated = system
    for solve in solve_requests:
        solve_type = str(solve.get("type", ""))
        if solve_type != "paraxial_image_distance":
            raise StructuredOpticsError(
                "optics_value_error",
                "Unknown configuration solve type.",
                params={"solve_type": solve_type, "supported_solve_types": ["paraxial_image_distance"]},
            )
        updated, result = solve_paraxial_image_distance(
            compile_system(updated),
            str(solve.get("thickness_of", "")),
            resolved_configuration,
        )
        results.append(result)
    if results:
        variables = dict(resolved_configuration.get("variables", {}))
        for result in results:
            variables[f"{result.thickness_of}_thickness_after_mm"] = result.thickness_after_mm
        resolved_configuration["variables"] = variables
        resolved_configuration["resolved_solves"] = [result.__dict__ for result in results]
    return updated, resolved_configuration, results
