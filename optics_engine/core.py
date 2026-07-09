from __future__ import annotations

import numpy as np

EPS = 1.0e-10


def normalize(v: np.ndarray, axis: int = -1) -> np.ndarray:
    norm = np.linalg.norm(v, axis=axis, keepdims=True)
    return np.divide(v, norm, out=np.zeros_like(v, dtype=float), where=norm > 0)


def field_direction(theta_y_deg: float, theta_z_deg: float) -> np.ndarray:
    theta_y = np.deg2rad(theta_y_deg)
    theta_z = np.deg2rad(theta_z_deg)
    return normalize(np.array([1.0, np.tan(theta_y), np.tan(theta_z)], dtype=float))


def intersect_plane(origins: np.ndarray, directions: np.ndarray, x_vertex: float) -> tuple[np.ndarray, np.ndarray]:
    denom = directions[:, 0]
    t = np.divide(
        x_vertex - origins[:, 0],
        denom,
        out=np.full(origins.shape[0], np.nan),
        where=np.abs(denom) > EPS,
    )
    valid = np.isfinite(t) & (t >= -1.0e-8)
    points = origins + directions * t[:, None]
    return points, valid


def intersect_sphere(
    origins: np.ndarray,
    directions: np.ndarray,
    x_vertex: float,
    radius_mm: float,
) -> tuple[np.ndarray, np.ndarray]:
    if abs(radius_mm) < EPS:
        return intersect_plane(origins, directions, x_vertex)

    center = np.array([x_vertex + radius_mm, 0.0, 0.0], dtype=float)
    oc = origins - center
    b = 2.0 * np.sum(oc * directions, axis=1)
    c = np.sum(oc * oc, axis=1) - radius_mm * radius_mm
    disc = b * b - 4.0 * c
    valid_disc = disc >= 0.0
    sqrt_disc = np.sqrt(np.maximum(disc, 0.0))
    t1 = (-b - sqrt_disc) / 2.0
    t2 = (-b + sqrt_disc) / 2.0
    t = np.where(t1 >= -1.0e-8, t1, t2)
    valid = valid_disc & (t >= -1.0e-8)
    points = origins + directions * t[:, None]
    return points, valid


def asphere_sag_and_slope(r: np.ndarray, radius_mm: float, conic: float, coefficients: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    c = 0.0 if abs(radius_mm) < EPS else 1.0 / radius_mm
    r2 = r * r
    if abs(c) < EPS:
        base = np.zeros_like(r)
        base_slope = np.zeros_like(r)
    else:
        q = 1.0 - (1.0 + conic) * c * c * r2
        sqrt_q = np.sqrt(np.maximum(q, EPS))
        denom = 1.0 + sqrt_q
        base = c * r2 / denom
        # Numerical derivative keeps the formula compact and stable enough for
        # the Phase 3 reference implementation.
        h = np.maximum(1.0e-6, np.abs(r) * 1.0e-6)
        r_plus = r + h
        r_minus = np.maximum(0.0, r - h)
        q_plus = 1.0 - (1.0 + conic) * c * c * r_plus * r_plus
        q_minus = 1.0 - (1.0 + conic) * c * c * r_minus * r_minus
        sag_plus = c * r_plus * r_plus / (1.0 + np.sqrt(np.maximum(q_plus, EPS)))
        sag_minus = c * r_minus * r_minus / (1.0 + np.sqrt(np.maximum(q_minus, EPS)))
        base_slope = (sag_plus - sag_minus) / np.maximum(r_plus - r_minus, EPS)

    extra = np.zeros_like(r)
    extra_slope = np.zeros_like(r)
    for key, value in coefficients.items():
        if not key.startswith("A"):
            continue
        order = int(key[1:])
        extra += value * np.power(r, order)
        if order > 0:
            extra_slope += order * value * np.power(r, order - 1)
    return base + extra, base_slope + extra_slope


def intersect_asphere(
    origins: np.ndarray,
    directions: np.ndarray,
    x_vertex: float,
    radius_mm: float,
    conic: float,
    coefficients: dict[str, float],
    max_iterations: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    points, valid = intersect_sphere(origins, directions, x_vertex, radius_mm)
    t = np.divide(
        points[:, 0] - origins[:, 0],
        directions[:, 0],
        out=np.zeros(origins.shape[0], dtype=float),
        where=np.abs(directions[:, 0]) > EPS,
    )
    valid &= np.isfinite(t)
    for _ in range(max_iterations):
        p = origins + directions * t[:, None]
        y = p[:, 1]
        z = p[:, 2]
        r = np.sqrt(y * y + z * z)
        sag, slope = asphere_sag_and_slope(r, radius_mm, conic, coefficients)
        f = p[:, 0] - (x_vertex + sag)
        drdt = np.divide(y * directions[:, 1] + z * directions[:, 2], r, out=np.zeros_like(r), where=r > EPS)
        dfdt = directions[:, 0] - slope * drdt
        delta = np.divide(f, dfdt, out=np.zeros_like(f), where=np.abs(dfdt) > EPS)
        t -= delta
        valid &= np.abs(delta) < 1.0e6
        if np.nanmax(np.abs(delta)) < 1.0e-10:
            break
    points = origins + directions * t[:, None]
    valid &= np.isfinite(t) & (t >= -1.0e-8)
    return points, valid


def intersect_surface(origins: np.ndarray, directions: np.ndarray, x_vertex: float, surface) -> tuple[np.ndarray, np.ndarray]:
    if surface.surface_type == "aspherical_even":
        return intersect_asphere(origins, directions, x_vertex, surface.radius_mm, surface.conic, surface.asphere_coefficients)
    if surface.surface_type == "plane":
        return intersect_plane(origins, directions, x_vertex)
    return intersect_sphere(origins, directions, x_vertex, surface.radius_mm)


def surface_normals(points: np.ndarray, x_vertex: float, radius_mm: float) -> np.ndarray:
    if abs(radius_mm) < EPS:
        normals = np.tile(np.array([1.0, 0.0, 0.0]), (points.shape[0], 1))
    else:
        center = np.array([x_vertex + radius_mm, 0.0, 0.0], dtype=float)
        normals = normalize(points - center)
    return normals


def surface_normals_for_surface(points: np.ndarray, x_vertex: float, surface) -> np.ndarray:
    if surface.surface_type != "aspherical_even":
        radius = 0.0 if surface.surface_type == "plane" else surface.radius_mm
        return surface_normals(points, x_vertex, radius)
    y = points[:, 1]
    z = points[:, 2]
    r = np.sqrt(y * y + z * z)
    _, slope = asphere_sag_and_slope(r, surface.radius_mm, surface.conic, surface.asphere_coefficients)
    dsdy = np.divide(slope * y, r, out=np.zeros_like(r), where=r > EPS)
    dsdz = np.divide(slope * z, r, out=np.zeros_like(r), where=r > EPS)
    return normalize(np.column_stack([np.ones(points.shape[0]), -dsdy, -dsdz]))


def refract(directions: np.ndarray, normals: np.ndarray, n_before: np.ndarray, n_after: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    oriented = normals.copy()
    cos_i = -np.sum(oriented * directions, axis=1)
    flip = cos_i < 0.0
    oriented[flip] *= -1.0
    cos_i = -np.sum(oriented * directions, axis=1)

    eta = n_before / n_after
    k = 1.0 - eta * eta * (1.0 - cos_i * cos_i)
    valid = k >= -1.0e-12
    sqrt_k = np.sqrt(np.maximum(k, 0.0))
    out = eta[:, None] * directions + (eta * cos_i - sqrt_k)[:, None] * oriented
    return normalize(out), valid


def reflect(directions: np.ndarray, normals: np.ndarray) -> np.ndarray:
    return normalize(directions - 2.0 * np.sum(directions * normals, axis=1)[:, None] * normals)


def thin_lens_transform(points: np.ndarray, directions: np.ndarray, x_vertex: float, focal_length_mm: float) -> np.ndarray:
    dx = directions[:, 0]
    slopes_y = np.divide(directions[:, 1], dx, out=np.zeros_like(dx), where=np.abs(dx) > EPS)
    slopes_z = np.divide(directions[:, 2], dx, out=np.zeros_like(dx), where=np.abs(dx) > EPS)
    y = points[:, 1]
    z = points[:, 2]
    sign = np.where(dx >= 0.0, 1.0, -1.0)
    out = np.column_stack(
        [
            sign,
            sign * (slopes_y - y / focal_length_mm),
            sign * (slopes_z - z / focal_length_mm),
        ]
    )
    return normalize(out)


def aperture_pass(points: np.ndarray, surface) -> np.ndarray:
    r = np.sqrt(points[:, 1] * points[:, 1] + points[:, 2] * points[:, 2])
    if surface.aperture is not None:
        aperture = surface.aperture
        if aperture.shape == "annulus":
            outer = aperture.outer_semi_diameter_mm
            inner = aperture.inner_semi_diameter_mm or 0.0
            if outer is None:
                outer = aperture.semi_diameter_mm
            if outer is None:
                return np.ones(points.shape[0], dtype=bool)
            return (r <= outer + 1.0e-9) & (r >= inner - 1.0e-9)
        if aperture.shape == "circle":
            radius = aperture.semi_diameter_mm or aperture.outer_semi_diameter_mm
            if radius is None:
                radius = surface.semi_diameter_mm
            if radius is None:
                return np.ones(points.shape[0], dtype=bool)
            return r <= radius + 1.0e-9
        raise NotImplementedError("polygon apertures are reserved for a later phase")
    if surface.semi_diameter_mm is None:
        if getattr(surface, "kind", None) == "eye_reference" and getattr(surface, "eye", None) is not None:
            return r <= surface.eye.pupil_diameter_mm / 2.0 + 1.0e-9
        return np.ones(points.shape[0], dtype=bool)
    return r <= surface.semi_diameter_mm + 1.0e-9
