from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .configuration import runtime_layout, validate_configuration
from .system import CompiledSystem


@dataclass(frozen=True)
class ParaxialResult:
    effective_focal_length_mm: float | None
    back_focal_length_mm: float | None
    front_focal_length_mm: float | None
    f_number: float | None
    entrance_pupil_position_mm: float | None
    entrance_pupil_diameter_mm: float | None
    exit_pupil_position_mm: float | None
    exit_pupil_diameter_mm: float | None
    paraxial_image_position_mm: float | None
    paraxial_magnification: float | None
    angular_magnification: float | None
    principal_plane_positions_mm: tuple[float | None, float | None]
    paraxial_reference: str = "coaxial_baseline"


def _last_powered_surface(compiled: CompiledSystem) -> int | None:
    powered = {"refractive", "mirror", "thin_lens"}
    for idx in range(len(compiled.surfaces) - 1, -1, -1):
        if compiled.surfaces[idx].kind in powered:
            return idx
    return None


def _trace_paraxial_ray(
    compiled: CompiledSystem,
    y0: float,
    u0: float,
    wavelength_nm: float,
    positions_mm: np.ndarray | None = None,
) -> tuple[float, float, int | None]:
    last_power = _last_powered_surface(compiled)
    if last_power is None:
        return y0, u0, None
    if positions_mm is None:
        positions_mm = np.array(compiled.surface_positions_mm, dtype=float)

    y = float(y0)
    u = float(u0)
    n_current = compiled.material_index("AIR", wavelength_nm)

    for idx, surface in enumerate(compiled.surfaces[: last_power + 1]):
        if surface.kind == "refractive":
            n_after = compiled.material_index(surface.material_after, wavelength_nm)
            c = 0.0 if surface.radius_mm == 0 else 1.0 / surface.radius_mm
            u = (n_current * u - y * c * (n_after - n_current)) / n_after
            n_current = n_after
        elif surface.kind == "thin_lens":
            u = u - y / float(surface.focal_length_mm)
        elif surface.kind == "mirror":
            if surface.radius_mm == 0:
                u = -u
            else:
                u = -u - 2.0 * y / surface.radius_mm

        if idx < last_power:
            y = y + (positions_mm[idx + 1] - positions_mm[idx]) * u

    return y, u, last_power


def analyze_paraxial(compiled: CompiledSystem, configuration=None, wavelength_nm: float | None = None) -> ParaxialResult:
    config_validation = validate_configuration(compiled, configuration)
    if not config_validation.ok:
        messages = "; ".join(issue.message for issue in config_validation.issues if issue.severity == "error")
        raise ValueError(messages)
    layout = runtime_layout(compiled, configuration)
    positions_mm = layout.centers_mm[:, 0]
    wavelength = compiled.system.wavelengths_nm.primary if wavelength_nm is None else wavelength_nm
    y_m, u_m, last_power = _trace_paraxial_ray(compiled, 1.0, 0.0, wavelength, positions_mm)

    efl = None
    bfl = None
    image_position = None
    principal_planes = (None, None)
    if last_power is not None and abs(u_m) > 1.0e-12:
        efl = -1.0 / u_m
        bfl = -y_m / u_m
        image_position = positions_mm[last_power] + bfl
        second_principal = positions_mm[last_power] + bfl - efl
        principal_planes = (None, second_principal)

    entrance_pupil_position = None
    entrance_pupil_diameter = None
    exit_pupil_position = None
    exit_pupil_diameter = None
    f_number = None
    if compiled.aperture_stop_index is not None:
        stop = compiled.surfaces[compiled.aperture_stop_index]
        stop_x = positions_mm[compiled.aperture_stop_index]
        radius = stop.semi_diameter_mm or 1.0
        if stop.aperture is not None:
            radius = stop.aperture.semi_diameter_mm or stop.aperture.outer_semi_diameter_mm or radius
        entrance_pupil_position = stop_x - positions_mm[0]
        entrance_pupil_diameter = 2.0 * radius
        exit_pupil_position = stop_x - (positions_mm[last_power] if last_power is not None else 0.0)
        exit_pupil_diameter = 2.0 * radius
        if efl is not None and entrance_pupil_diameter > 0:
            f_number = abs(efl) / entrance_pupil_diameter

    return ParaxialResult(
        effective_focal_length_mm=efl,
        back_focal_length_mm=bfl,
        front_focal_length_mm=None if efl is None else abs(efl),
        f_number=f_number,
        entrance_pupil_position_mm=entrance_pupil_position,
        entrance_pupil_diameter_mm=entrance_pupil_diameter,
        exit_pupil_position_mm=exit_pupil_position,
        exit_pupil_diameter_mm=exit_pupil_diameter,
        paraxial_image_position_mm=image_position,
        paraxial_magnification=None,
        angular_magnification=None,
        principal_plane_positions_mm=principal_planes,
    )


def ideal_image_height_mm(compiled: CompiledSystem, theta_y_deg: float, theta_z_deg: float) -> tuple[float, float]:
    paraxial = analyze_paraxial(compiled)
    if paraxial.effective_focal_length_mm is None:
        return (np.nan, np.nan)
    return (
        paraxial.effective_focal_length_mm * np.tan(np.deg2rad(theta_y_deg)),
        paraxial.effective_focal_length_mm * np.tan(np.deg2rad(theta_z_deg)),
    )
