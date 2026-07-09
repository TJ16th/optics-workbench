from __future__ import annotations

from .models import OpticalSystem, ValidationIssue, ValidationResult


def validate_system(system: OpticalSystem) -> ValidationResult:
    issues: list[ValidationIssue] = []

    stop_count = sum(1 for surface in system.surfaces if surface.kind == "aperture_stop")
    if stop_count > 1:
        issues.append(
            ValidationIssue(
                type="multiple_aperture_stops",
                params={"count": stop_count},
                message="a system may contain at most one aperture_stop",
                severity="error",
            )
        )
    if stop_count == 0:
        issues.append(
            ValidationIssue(
                type="missing_aperture_stop",
                params={},
                message="no aperture_stop was supplied; ray aiming will fall back to the first surface",
                severity="warning",
            )
        )

    if system.system_type == "focal":
        if not system.surfaces or system.surfaces[-1].kind != "sensor":
            issues.append(
                ValidationIssue(
                    type="missing_terminal_sensor",
                    params={"system_type": system.system_type},
                    message="focal systems must end with a sensor surface",
                    severity="error",
                )
            )
    if system.system_type == "afocal":
        if not system.surfaces or system.surfaces[-1].kind != "eye_reference":
            issues.append(
                ValidationIssue(
                    type="missing_terminal_eye_reference",
                    params={"system_type": system.system_type},
                    message="afocal systems must end with an eye_reference surface",
                    severity="error",
                )
            )

    surface_ids = set()
    propagation_sign = 1
    for surface in system.surfaces:
        if surface.id in surface_ids:
            issues.append(
                ValidationIssue(
                    type="duplicate_surface_id",
                    params={"surface_id": surface.id},
                    message=f"duplicate surface id {surface.id!r}",
                    surface_id=surface.id,
                    severity="error",
                )
            )
        surface_ids.add(surface.id)

        if surface.surface_type == "aspherical_even" and surface.kind not in {"refractive", "mirror"}:
            issues.append(
                ValidationIssue(
                    type="invalid_asphere_surface",
                    params={"surface_id": surface.id, "kind": surface.kind, "surface_type": surface.surface_type},
                    message="aspherical_even is only valid for refractive or mirror surfaces",
                    surface_id=surface.id,
                    severity="error",
                )
            )
        if surface.kind == "eye_reference" and surface.eye is None:
            issues.append(
                ValidationIssue(
                    type="missing_eye_reference",
                    params={"surface_id": surface.id},
                    message="eye_reference surface requires eye settings",
                    surface_id=surface.id,
                    severity="error",
                )
            )
        if surface.kind == "thin_lens" and not surface.focal_length_mm:
            issues.append(
                ValidationIssue(
                    type="missing_focal_length",
                    params={"surface_id": surface.id},
                    message="thin_lens requires focal_length_mm",
                    surface_id=surface.id,
                    severity="error",
                )
            )
        if surface.kind == "sensor" and surface.sensor is None:
            issues.append(
                ValidationIssue(
                    type="missing_sensor",
                    params={"surface_id": surface.id},
                    message="sensor surface requires sensor dimensions",
                    surface_id=surface.id,
                    severity="error",
                )
            )

        if surface.kind == "mirror":
            propagation_sign *= -1
        if abs(surface.thickness_after_mm) > 0.0:
            expected_sign = 1 if surface.thickness_after_mm > 0 else -1
            if expected_sign != propagation_sign:
                issues.append(
                    ValidationIssue(
                        type="mirror_thickness_sign",
                        params={"surface_id": surface.id, "thickness_sign": expected_sign, "propagation_sign": propagation_sign},
                        message=(
                            f"thickness_after_mm on {surface.id!r} has sign {expected_sign}, "
                            f"but propagation_sign is {propagation_sign}"
                        ),
                        surface_id=surface.id,
                        severity="error",
                    )
                )

    for group in system.groups:
        if group.from_surface not in surface_ids:
            issues.append(
            ValidationIssue(
                type="unknown_group_surface",
                params={"group_id": group.id, "surface_id": group.from_surface, "role": "from_surface"},
                message=f"group {group.id!r} references unknown from_surface {group.from_surface!r}",
                severity="error",
            )
            )
        if group.to_surface not in surface_ids:
            issues.append(
            ValidationIssue(
                type="unknown_group_surface",
                params={"group_id": group.id, "surface_id": group.to_surface, "role": "to_surface"},
                message=f"group {group.id!r} references unknown to_surface {group.to_surface!r}",
                severity="error",
            )
            )
        if group.from_surface in surface_ids and group.to_surface in surface_ids:
            ids = [surface.id for surface in system.surfaces]
            if ids.index(group.from_surface) > ids.index(group.to_surface):
                issues.append(
                    ValidationIssue(
                        type="invalid_group_range",
                        params={"group_id": group.id, "from_surface": group.from_surface, "to_surface": group.to_surface},
                        message=f"group {group.id!r} from_surface must precede to_surface",
                        severity="error",
                    )
                )

    group_ids = {group.id for group in system.groups}
    for zoom in system.zoom_positions:
        for group_id in zoom.group_positions:
            if group_id not in group_ids:
                issues.append(
                    ValidationIssue(
                        type="unknown_zoom_group",
                        params={"zoom_position_id": zoom.id, "group_id": group_id},
                        message=f"zoom_position {zoom.id!r} references unknown group {group_id!r}",
                        severity="error",
                    )
                )

    status = "ok"
    if any(issue.severity == "error" for issue in issues):
        status = "error"
    elif issues:
        status = "warning"
    return ValidationResult(status=status, issues=issues)
