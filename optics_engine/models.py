from __future__ import annotations

from typing import Any, Literal

import numpy as np
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class OpticsError(Exception):
    """Base exception for optics engine failures."""


class StructuredOpticsError(OpticsError):
    """Exception carrying the public v2.3 structured error fields."""

    def __init__(
        self,
        code: str,
        message_en: str,
        *,
        params: dict[str, Any] | None = None,
        severity: str = "error",
    ):
        super().__init__(message_en)
        self.code = code
        self.message_en = message_en
        self.params = params or {}
        self.severity = severity


class UnsupportedOpticsError(OpticsError):
    """Raised for spec-reserved features that are not implemented in this build."""


class Material(BaseModel):
    id: str
    type: Literal["constant", "nd_vd", "sellmeier", "catalog", "custom_table"] = "constant"
    n: float | None = None
    nd: float | None = None
    vd: float | None = None
    B: list[float] | None = None
    C: list[float] | None = None
    table: list[dict[str, float] | list[float]] | None = None

    def refractive_index(self, wavelength_nm: float) -> float:
        if self.type == "constant":
            return 1.0 if self.n is None else float(self.n)
        if self.type == "nd_vd":
            nd = float(self.nd if self.nd is not None else (self.n if self.n is not None else 1.5168))
            vd = float(self.vd if self.vd is not None else 64.17)
            lam_f = 486.13 / 1000.0
            lam_d = 587.56 / 1000.0
            lam_c = 656.27 / 1000.0
            delta_fc = (nd - 1.0) / vd
            b = delta_fc / (1.0 / (lam_f * lam_f) - 1.0 / (lam_c * lam_c))
            a = nd - b / (lam_d * lam_d)
            wavelength_um = wavelength_nm / 1000.0
            return a + b / (wavelength_um * wavelength_um)
        if self.type == "sellmeier":
            if not self.B or not self.C or len(self.B) != 3 or len(self.C) != 3:
                raise ValueError(f"Sellmeier material {self.id!r} requires B/C length 3")
            wavelength_um = wavelength_nm / 1000.0
            lam2 = wavelength_um * wavelength_um
            n2_minus_1 = 0.0
            for b_i, c_i in zip(self.B, self.C):
                n2_minus_1 += b_i * lam2 / (lam2 - c_i)
            return (1.0 + n2_minus_1) ** 0.5
        if self.type == "catalog":
            catalog = {
                "N-BK7": Material(
                    id="N-BK7",
                    type="sellmeier",
                    B=[1.03961212, 0.231792344, 1.01046945],
                    C=[0.006000699, 0.0200179144, 103.560653],
                ),
                "BK7": Material(
                    id="BK7",
                    type="sellmeier",
                    B=[1.03961212, 0.231792344, 1.01046945],
                    C=[0.006000699, 0.0200179144, 103.560653],
                ),
            }
            material = catalog.get(self.id)
            if material is None:
                if self.n is not None:
                    return float(self.n)
                raise ValueError(f"catalog material {self.id!r} is not available")
            return material.refractive_index(wavelength_nm)
        if self.type == "custom_table":
            if not self.table:
                raise ValueError(f"custom_table material {self.id!r} requires table entries")
            rows: list[tuple[float, float]] = []
            for item in self.table:
                if isinstance(item, dict):
                    rows.append((float(item.get("wavelength_nm", item.get("wavelength", 0.0))), float(item["n"])))
                else:
                    rows.append((float(item[0]), float(item[1])))
            rows.sort()
            xs = [row[0] for row in rows]
            ys = [row[1] for row in rows]
            return float(np.interp(float(wavelength_nm), xs, ys))
        raise UnsupportedOpticsError(f"material type {self.type!r} is not implemented")


class Wavelengths(BaseModel):
    primary: float = 587.56
    samples: list[float] = Field(default_factory=lambda: [587.56])


class Aperture(BaseModel):
    shape: Literal["circle", "annulus", "polygon"] = "circle"
    semi_diameter_mm: float | None = None
    outer_semi_diameter_mm: float | None = None
    inner_semi_diameter_mm: float | None = None


class Sensor(BaseModel):
    width_mm: float
    height_mm: float
    pixel_pitch_um: float | None = None
    normal: list[float] = Field(default_factory=lambda: [-1.0, 0.0, 0.0])


class EyeReference(BaseModel):
    pupil_diameter_mm: float = 4.0
    position_mode: Literal["at_exit_pupil", "fixed_offset"] = "at_exit_pupil"
    offset_from_last_surface_mm: float | None = None


class Surface(BaseModel):
    id: str
    kind: Literal[
        "refractive",
        "mirror",
        "aperture_stop",
        "mechanical_aperture",
        "thin_lens",
        "sensor",
        "eye_reference",
        "dummy",
    ]
    surface_type: Literal["spherical", "plane", "aspherical_even"] = "spherical"
    radius_mm: float = 0.0
    conic: float = 0.0
    asphere_coefficients: dict[str, float] = Field(default_factory=dict)
    thickness_after_mm: float = 0.0
    material_after: str | None = None
    semi_diameter_mm: float | None = None
    aperture: Aperture | None = None
    sensor: Sensor | None = None
    eye: EyeReference | None = None
    focal_length_mm: float | None = None


class Group(BaseModel):
    id: str
    name: str | None = None
    from_surface: str
    to_surface: str


class GroupPosition(BaseModel):
    shift_x_mm: float = 0.0
    shift_y_mm: float = 0.0
    shift_z_mm: float = 0.0


class ZoomPosition(BaseModel):
    id: str
    focal_length_nominal_mm: float | None = None
    group_positions: dict[str, GroupPosition] = Field(default_factory=dict)


class OpticalSystem(BaseModel):
    name: str = "unnamed"
    units: Literal["mm"] = "mm"
    optical_axis: Literal["+X"] = "+X"
    system_type: Literal["focal", "afocal"] = "focal"
    wavelengths_nm: Wavelengths = Field(default_factory=Wavelengths)
    materials: list[Material] = Field(default_factory=lambda: [Material(id="AIR", n=1.0)])
    surfaces: list[Surface]
    groups: list[Group] = Field(default_factory=list)
    zoom_positions: list[ZoomPosition] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(validation_alias=AliasChoices("code", "type"))
    params: dict[str, Any] = Field(default_factory=dict)
    message_en: str = Field(validation_alias=AliasChoices("message_en", "message"))
    surface_id: str | None = None
    severity: Literal["error", "warning", "info"] = "error"

    @property
    def type(self) -> str:
        return self.code

    @property
    def message(self) -> str:
        return self.message_en


class ValidationResult(BaseModel):
    status: Literal["ok", "error", "warning"]
    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)
