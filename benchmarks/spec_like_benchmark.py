from __future__ import annotations

import argparse
import json
import statistics as stats
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optics_engine import (  # noqa: E402
    analyze_geometric_mtf,
    analyze_geometric_psf,
    analyze_relative_illumination,
    compile_system,
    evaluate_system,
    load_system,
    trace_forward,
)


def build_spec_like_system() -> dict[str, Any]:
    """Return a 14-surface focal system for performance benchmarking.

    The design is intentionally synthetic, but it exercises the current engine
    in the ways the v2 spec cares about for Phase 1-8 performance work:
    multiple refractive elements, Sellmeier dispersion, two even aspheres,
    an internal aperture stop, a final sensor, and enough surfaces before the
    stop to make ``ray_aiming: full`` meaningful.
    """

    return {
        "name": "spec_like_12_refractive_asphere_lens",
        "wavelengths_nm": {"primary": 587.56, "samples": [486.13, 587.56, 656.27]},
        "materials": [
            {"id": "AIR", "type": "constant", "n": 1.0},
            {
                "id": "N-BK7",
                "type": "sellmeier",
                "B": [1.03961212, 0.231792344, 1.01046945],
                "C": [0.00600069867, 0.0200179144, 103.560653],
            },
            {
                "id": "N-F2",
                "type": "sellmeier",
                "B": [1.34533359, 0.209073176, 0.937357162],
                "C": [0.00997743871, 0.0470450767, 111.886764],
            },
        ],
        "surfaces": [
            {"id": "S1", "kind": "refractive", "radius_mm": 55.0, "material_after": "N-BK7", "semi_diameter_mm": 24.0, "thickness_after_mm": 4.0},
            {"id": "S2", "kind": "refractive", "radius_mm": -90.0, "material_after": "AIR", "semi_diameter_mm": 23.0, "thickness_after_mm": 2.0},
            {
                "id": "S3",
                "kind": "refractive",
                "surface_type": "aspherical_even",
                "radius_mm": 44.0,
                "conic": -0.35,
                "asphere_coefficients": {"A4": 1.0e-8, "A6": -1.0e-12},
                "material_after": "N-F2",
                "semi_diameter_mm": 22.0,
                "thickness_after_mm": 3.5,
            },
            {"id": "S4", "kind": "refractive", "radius_mm": 78.0, "material_after": "AIR", "semi_diameter_mm": 21.0, "thickness_after_mm": 4.0},
            {"id": "S5", "kind": "refractive", "radius_mm": -64.0, "material_after": "N-BK7", "semi_diameter_mm": 20.0, "thickness_after_mm": 4.0},
            {"id": "S6", "kind": "refractive", "radius_mm": 48.0, "material_after": "AIR", "semi_diameter_mm": 19.0, "thickness_after_mm": 1.5},
            {"id": "STOP", "kind": "aperture_stop", "aperture": {"shape": "circle", "semi_diameter_mm": 7.5}, "thickness_after_mm": 6.0},
            {"id": "S7", "kind": "refractive", "radius_mm": 82.0, "material_after": "N-F2", "semi_diameter_mm": 18.0, "thickness_after_mm": 3.0},
            {
                "id": "S8",
                "kind": "refractive",
                "surface_type": "aspherical_even",
                "radius_mm": -46.0,
                "conic": -0.2,
                "asphere_coefficients": {"A4": -8.0e-9, "A6": 8.0e-13},
                "material_after": "AIR",
                "semi_diameter_mm": 17.0,
                "thickness_after_mm": 2.0,
            },
            {"id": "S9", "kind": "refractive", "radius_mm": 68.0, "material_after": "N-BK7", "semi_diameter_mm": 17.0, "thickness_after_mm": 4.0},
            {"id": "S10", "kind": "refractive", "radius_mm": -38.0, "material_after": "AIR", "semi_diameter_mm": 16.0, "thickness_after_mm": 1.0},
            {"id": "S11", "kind": "refractive", "radius_mm": 120.0, "material_after": "N-F2", "semi_diameter_mm": 15.0, "thickness_after_mm": 3.0},
            {"id": "S12", "kind": "refractive", "radius_mm": -76.0, "material_after": "AIR", "semi_diameter_mm": 15.0, "thickness_after_mm": 42.0},
            {"id": "IMG", "kind": "sensor", "sensor": {"width_mm": 36.0, "height_mm": 24.0, "pixel_pitch_um": 4.0}},
        ],
    }


FIELDS_3 = [
    {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
    {"id": "mid_y", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0},
    {"id": "mid_z", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 5.0},
]

FIELDS_5 = FIELDS_3 + [
    {"id": "neg_y", "type": "angular", "theta_y_deg": -5.0, "theta_z_deg": 0.0},
    {"id": "neg_z", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": -5.0},
]

WAVELENGTHS_3 = [486.13, 587.56, 656.27]

PROFILES = {
    "smoke": {"preview_samples": 9, "spot_samples": 21, "analysis_samples": 64, "warmups": 1, "repeats": 2},
    "default": {"preview_samples": 25, "spot_samples": 64, "analysis_samples": 512, "warmups": 1, "repeats": 3},
    "detail": {"preview_samples": 25, "spot_samples": 512, "analysis_samples": 2048, "warmups": 1, "repeats": 1},
}


def summarize_trace(trace) -> dict[str, Any]:
    return {
        "rays": int(trace.status.size),
        "arrived": int(trace.arrived_mask.sum()),
        "blocked": int((trace.status == "blocked").sum()),
        "aiming_failed": int(trace.metadata.get("aiming_failed_count", 0)),
        "aiming_iterations_max": int(trace.metadata.get("aiming_iterations_max", 0)),
    }


def time_case(name: str, fn: Callable[[], Any], warmups: int, repeats: int) -> tuple[dict[str, Any], Any]:
    for _ in range(warmups):
        fn()
    elapsed_ms: list[float] = []
    last_result = None
    for _ in range(repeats):
        start = time.perf_counter()
        last_result = fn()
        elapsed_ms.append((time.perf_counter() - start) * 1000.0)
    return (
        {
            "name": name,
            "median_ms": stats.median(elapsed_ms),
            "mean_ms": stats.mean(elapsed_ms),
            "min_ms": min(elapsed_ms),
            "max_ms": max(elapsed_ms),
            "repeats": repeats,
        },
        last_result,
    )


def run_benchmark(profile: str) -> dict[str, Any]:
    settings = PROFILES[profile]
    system = load_system(build_spec_like_system())
    compiled = compile_system(system)
    warmups = settings["warmups"]
    repeats = settings["repeats"]

    cases: list[tuple[str, Callable[[], Any], Callable[[Any], dict[str, Any]]]] = []
    cases.append(
        (
            f"trace preview full aiming: 3 fields x 3 wavelengths x {settings['preview_samples']} rays",
            lambda: trace_forward(
                compiled,
                FIELDS_3,
                {"samples_per_field": settings["preview_samples"], "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
                WAVELENGTHS_3,
            ),
            summarize_trace,
        )
    )
    cases.append(
        (
            f"trace spot full aiming: 5 fields x 3 wavelengths x {settings['spot_samples']} rays",
            lambda: trace_forward(
                compiled,
                FIELDS_5,
                {"samples_per_field": settings["spot_samples"], "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
                WAVELENGTHS_3,
            ),
            summarize_trace,
        )
    )
    analysis_trace = trace_forward(
        compiled,
        [{"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
        {"samples_per_field": settings["analysis_samples"], "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
        [587.56],
    )
    cases.append(
        (
            f"geometric PSF from {settings['analysis_samples']}-ray full-aim trace",
            lambda: analyze_geometric_psf(analysis_trace, grid_size=32),
            lambda result: {"total_energy": result.total_energy, "grid": [len(result.grid), len(result.grid[0]) if result.grid else 0]},
        )
    )
    cases.append(
        (
            f"geometric MTF from {settings['analysis_samples']}-ray full-aim trace",
            lambda: analyze_geometric_mtf(analysis_trace, [0.0, 10.0, 20.0, 40.0]),
            lambda result: {"points": len(result.points), "mtf40_radial": result.points[-1].mtf_radial if result.points else None},
        )
    )
    cases.append(
        (
            "relative illumination full aiming: 5 fields x 3 wavelengths",
            lambda: analyze_relative_illumination(
                compiled,
                FIELDS_5,
                {"samples_per_field": settings["preview_samples"], "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
                WAVELENGTHS_3,
            ),
            lambda result: {"rows": len(result.rows), "min_relative_illumination": min(row.relative_illumination for row in result.rows)},
        )
    )
    cases.append(
        (
            "evaluate fast_design_score full aiming",
            lambda: evaluate_system(
                system,
                {
                    "preset": "fast_design_score",
                    "fields": FIELDS_3,
                    "wavelengths": [{"wavelength_nm": wl} for wl in WAVELENGTHS_3],
                },
                ray_sampling={"samples_per_field": settings["preview_samples"], "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
            ),
            lambda result: {"status": result.status, "score": result.merit.score if result.merit else None},
        )
    )

    results = []
    for name, fn, extra in cases:
        timing, result = time_case(name, fn, warmups, repeats)
        timing["details"] = extra(result)
        results.append(timing)

    return {
        "profile": profile,
        "system": {
            "surfaces": len(system.surfaces),
            "refractive_surfaces": sum(1 for surface in system.surfaces if surface.kind == "refractive"),
            "aspheres": sum(1 for surface in system.surfaces if surface.surface_type == "aspherical_even"),
            "wavelengths": WAVELENGTHS_3,
        },
        "settings": settings,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a spec-like full-ray-aiming optical engine benchmark.")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="default")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()

    result = run_benchmark(args.profile)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    system = result["system"]
    print(
        "Spec-like benchmark: "
        f"{system['surfaces']} surfaces, {system['refractive_surfaces']} refractive, "
        f"{system['aspheres']} aspheres, {len(system['wavelengths'])} wavelengths"
    )
    print(f"Profile: {result['profile']}  Settings: {result['settings']}")
    for row in result["results"]:
        print(
            f"- {row['name']}: median={row['median_ms']:.3f}ms "
            f"mean={row['mean_ms']:.3f}ms min={row['min_ms']:.3f}ms max={row['max_ms']:.3f}ms "
            f"details={row['details']}"
        )


if __name__ == "__main__":
    main()
