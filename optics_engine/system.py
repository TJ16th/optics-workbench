from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .models import Material, OpticalSystem, Surface
from .validation import validate_system


def _model_dump_jsonable(system: OpticalSystem) -> dict:
    return system.model_dump(mode="json", exclude_none=True)


def normalized_system_hash(system: OpticalSystem) -> str:
    normalized = json.dumps(
        _model_dump_jsonable(system),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CompiledSystem:
    system: OpticalSystem
    system_hash: str
    surfaces: tuple[Surface, ...]
    surface_positions_mm: tuple[float, ...]
    materials: dict[str, Material]
    aperture_stop_index: int | None
    sensor_index: int | None
    eye_reference_index: int | None
    group_ranges: dict[str, tuple[int, int]]

    def surface_index(self, surface_id: str) -> int:
        for idx, surface in enumerate(self.surfaces):
            if surface.id == surface_id:
                return idx
        raise KeyError(surface_id)

    def material_index(self, material_id: str | None, wavelength_nm: float) -> float:
        if material_id is None:
            material_id = "AIR"
        material = self.materials.get(material_id)
        if material is None:
            raise KeyError(f"unknown material {material_id!r}")
        return material.refractive_index(wavelength_nm)

    def group_indices(self, group_id: str) -> range:
        start, end = self.group_ranges[group_id]
        return range(start, end + 1)


_SYSTEM_CACHE: dict[str, CompiledSystem] = {}


def _exit_pupil_position(system: OpticalSystem, positions: list[float], eye_idx: int, stop_idx: int | None) -> float:
    if stop_idx is None or stop_idx >= eye_idx:
        return positions[eye_idx]
    wavelength = system.wavelengths_nm.primary
    materials = {material.id: material for material in system.materials}
    # Image the aperture plane with its axial basis ray (B/D of the
    # paraxial transfer matrix), then intersect that ray with the axis.
    y = 0.0
    u = 1.0
    n_current = 1.0
    previous_x = positions[stop_idx]
    last_x = previous_x
    for idx in range(stop_idx + 1, eye_idx):
        surface = system.surfaces[idx]
        y += (positions[idx] - previous_x) * u
        previous_x = positions[idx]
        if surface.kind == "refractive":
            material = materials.get(surface.material_after or "AIR")
            n_after = 1.0 if material is None else material.refractive_index(wavelength)
            curvature = 0.0 if surface.radius_mm == 0 else 1.0 / surface.radius_mm
            u = (n_current * u - y * curvature * (n_after - n_current)) / n_after
            n_current = n_after
            last_x = positions[idx]
        elif surface.kind == "thin_lens":
            u -= y / float(surface.focal_length_mm)
            last_x = positions[idx]
        elif surface.kind == "mirror":
            u = -u if surface.radius_mm == 0 else -u - 2.0 * y / surface.radius_mm
            last_x = positions[idx]
    if abs(u) <= 1.0e-12:
        return positions[eye_idx]
    return float(last_x - y / u)


def compile_system(system: OpticalSystem, *, use_cache: bool = True) -> CompiledSystem:
    validation = validate_system(system)
    if not validation.ok:
        messages = "; ".join(issue.message for issue in validation.issues if issue.severity == "error")
        raise ValueError(messages)

    system_hash = normalized_system_hash(system)
    if use_cache and system_hash in _SYSTEM_CACHE:
        return _SYSTEM_CACHE[system_hash]

    positions: list[float] = []
    x_pos = 0.0
    for surface in system.surfaces:
        positions.append(x_pos)
        x_pos += surface.thickness_after_mm

    eye_reference_index = next((idx for idx, surface in enumerate(system.surfaces) if surface.kind == "eye_reference"), None)
    if eye_reference_index is not None and system.surfaces[eye_reference_index].eye is not None:
        eye = system.surfaces[eye_reference_index].eye
        original = positions[eye_reference_index]
        if eye.position_mode == "at_exit_pupil":
            resolved = _exit_pupil_position(system, positions, eye_reference_index, next((idx for idx, surface in enumerate(system.surfaces) if surface.kind == "aperture_stop"), None))
        elif eye.offset_from_last_surface_mm is not None and eye_reference_index > 0:
            resolved = positions[eye_reference_index - 1] + eye.offset_from_last_surface_mm
        else:
            resolved = original
        shift = resolved - original
        for idx in range(eye_reference_index, len(positions)):
            positions[idx] += shift

    materials = {material.id: material for material in system.materials}
    materials.setdefault("AIR", Material(id="AIR", type="constant", n=1.0))

    aperture_stop_index = None
    sensor_index = None
    for idx, surface in enumerate(system.surfaces):
        if surface.kind == "aperture_stop":
            aperture_stop_index = idx
        if surface.kind == "sensor":
            sensor_index = idx

    group_ranges: dict[str, tuple[int, int]] = {}
    id_to_index = {surface.id: idx for idx, surface in enumerate(system.surfaces)}
    for group in system.groups:
        if group.from_surface in id_to_index and group.to_surface in id_to_index:
            start = id_to_index[group.from_surface]
            end = id_to_index[group.to_surface]
            if start <= end:
                group_ranges[group.id] = (start, end)

    compiled = CompiledSystem(
        system=system,
        system_hash=system_hash,
        surfaces=tuple(system.surfaces),
        surface_positions_mm=tuple(positions),
        materials=materials,
        aperture_stop_index=aperture_stop_index,
        sensor_index=sensor_index,
        eye_reference_index=eye_reference_index,
        group_ranges=group_ranges,
    )
    if use_cache:
        _SYSTEM_CACHE[system_hash] = compiled
    return compiled


def get_cached_system(system_hash: str) -> CompiledSystem | None:
    return _SYSTEM_CACHE.get(system_hash)
