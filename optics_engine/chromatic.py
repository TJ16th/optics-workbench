from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .paraxial import analyze_paraxial
from .system import CompiledSystem


@dataclass(frozen=True)
class ChromaticFocus:
    wavelength_nm: float
    paraxial_image_position_mm: float | None
    back_focal_length_mm: float | None
    effective_focal_length_mm: float | None
    axial_shift_from_primary_mm: float | None


@dataclass(frozen=True)
class ChromaticAberrationResult:
    primary_wavelength_nm: float
    focus_by_wavelength: list[ChromaticFocus]
    axial_color_span_mm: float | None
    lateral_color_by_field: dict[str, dict[str, float | None]]


def analyze_chromatic_aberration(
    compiled: CompiledSystem,
    wavelengths_nm: list[float] | None = None,
    fields: list[dict] | None = None,
) -> ChromaticAberrationResult:
    wavelengths = wavelengths_nm or compiled.system.wavelengths_nm.samples or [compiled.system.wavelengths_nm.primary]
    primary = compiled.system.wavelengths_nm.primary
    primary_result = analyze_paraxial(compiled, wavelength_nm=primary)
    primary_pos = primary_result.paraxial_image_position_mm

    focus_rows: list[ChromaticFocus] = []
    positions: list[float] = []
    for wavelength in wavelengths:
        paraxial = analyze_paraxial(compiled, wavelength_nm=wavelength)
        pos = paraxial.paraxial_image_position_mm
        if pos is not None:
            positions.append(pos)
        focus_rows.append(
            ChromaticFocus(
                wavelength_nm=wavelength,
                paraxial_image_position_mm=pos,
                back_focal_length_mm=paraxial.back_focal_length_mm,
                effective_focal_length_mm=paraxial.effective_focal_length_mm,
                axial_shift_from_primary_mm=None if pos is None or primary_pos is None else pos - primary_pos,
            )
        )

    lateral: dict[str, dict[str, float | None]] = {}
    for field in fields or []:
        field_id = str(field.get("id", "field"))
        theta_y = np.deg2rad(float(field.get("theta_y_deg", 0.0)))
        theta_z = np.deg2rad(float(field.get("theta_z_deg", 0.0)))
        primary_efl = primary_result.effective_focal_length_mm
        primary_y = None if primary_efl is None else primary_efl * np.tan(theta_y)
        primary_z = None if primary_efl is None else primary_efl * np.tan(theta_z)
        max_delta = 0.0
        for wavelength in wavelengths:
            efl = analyze_paraxial(compiled, wavelength_nm=wavelength).effective_focal_length_mm
            if efl is None or primary_y is None or primary_z is None:
                continue
            dy = efl * np.tan(theta_y) - primary_y
            dz = efl * np.tan(theta_z) - primary_z
            max_delta = max(max_delta, float(np.hypot(dy, dz)))
        lateral[field_id] = {"max_lateral_shift_mm": max_delta if primary_efl is not None else None}

    span = None
    if positions:
        span = float(max(positions) - min(positions))
    return ChromaticAberrationResult(
        primary_wavelength_nm=primary,
        focus_by_wavelength=focus_rows,
        axial_color_span_mm=span,
        lateral_color_by_field=lateral,
    )
