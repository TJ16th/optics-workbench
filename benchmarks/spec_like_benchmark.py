from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import json
import math
import platform
import statistics as stats
import subprocess
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


JST = timezone(timedelta(hours=9), "JST")


def build_spec_like_system() -> dict[str, Any]:
    """Return a 14-surface focal system for performance benchmarking."""

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
    {"id": "pos_y_5", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0},
    {"id": "pos_z_5", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 5.0},
]

FIELDS_5 = FIELDS_3 + [
    {"id": "neg_y_5", "type": "angular", "theta_y_deg": -5.0, "theta_z_deg": 0.0},
    {"id": "neg_z_5", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": -5.0},
]

RI_FIELDS_5 = [
    {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
    {"id": "pos_y_15", "type": "angular", "theta_y_deg": 15.0, "theta_z_deg": 0.0},
    {"id": "neg_y_15", "type": "angular", "theta_y_deg": -15.0, "theta_z_deg": 0.0},
    {"id": "pos_z_15", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 15.0},
    {"id": "neg_z_15", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": -15.0},
]

WAVELENGTHS_3 = [486.13, 587.56, 656.27]

PROFILES = {
    "smoke": {"preview_samples": 9, "spot_samples": 21, "analysis_samples": 64, "warmups": 1, "repeats": 5},
    "default": {"preview_samples": 25, "spot_samples": 64, "analysis_samples": 512, "warmups": 1, "repeats": 5},
    "detail": {"preview_samples": 25, "spot_samples": 512, "analysis_samples": 2048, "warmups": 1, "repeats": 5},
}


def git_value(*args: str, default: str = "unknown") -> str:
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    except Exception:
        return default
    return result.stdout.strip() or default


def git_dirty() -> bool | None:
    try:
        result = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True, check=True)
    except Exception:
        return None
    return bool(result.stdout.strip())


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(percent * len(ordered)) - 1))
    return ordered[index]


def field_angles(fields: list[dict[str, Any]]) -> list[dict[str, float | str]]:
    return [
        {
            "id": str(field.get("id", f"field_{idx + 1}")),
            "theta_y_deg": float(field.get("theta_y_deg", 0.0)),
            "theta_z_deg": float(field.get("theta_z_deg", 0.0)),
        }
        for idx, field in enumerate(fields)
    ]


def ray_count(fields: list[dict[str, Any]], wavelengths: list[float], samples_per_field: int) -> int:
    return len(fields) * len(wavelengths) * int(samples_per_field)


def case_context(
    *,
    fields: list[dict[str, Any]],
    wavelengths: list[float],
    samples_per_field: int,
    surface_count: int,
    ray_aiming_mode: str,
) -> dict[str, Any]:
    rays = ray_count(fields, wavelengths, samples_per_field)
    return {
        "fields": field_angles(fields),
        "field_count": len(fields),
        "wavelengths_nm": [float(wavelength) for wavelength in wavelengths],
        "wavelength_count": len(wavelengths),
        "samples_per_field": int(samples_per_field),
        "total_rays": rays,
        "surface_count": surface_count,
        "surface_ray_count": rays * surface_count,
        "ray_aiming_mode": ray_aiming_mode,
    }


def summarize_trace(trace) -> dict[str, Any]:
    return {
        "rays": int(trace.status.size),
        "arrived": int(trace.arrived_mask.sum()),
        "blocked": int((trace.status == "blocked").sum()),
        "aiming_failed": int(trace.metadata.get("aiming_failed_count", 0)),
        "aiming_iterations_max": int(trace.metadata.get("aiming_iterations_max", 0)),
    }


def summarize_relative_illumination(result) -> dict[str, Any]:
    rows = []
    for row in result.rows:
        measured = float(row.relative_illumination)
        expected = float(row.cos4_factor)
        rows.append(
            {
                "field_id": row.field_id,
                "theta_y_deg": row.theta_y_deg,
                "theta_z_deg": row.theta_z_deg,
                "throughput": row.throughput,
                "cos4_factor": expected,
                "relative_illumination": measured,
                "measured_minus_cos4": measured - expected,
            }
        )
    outer = max(rows, key=lambda item: abs(float(item["theta_y_deg"])) + abs(float(item["theta_z_deg"]))) if rows else None
    return {
        "rows": rows,
        "min_relative_illumination": min((float(row["relative_illumination"]) for row in rows), default=None),
        "outer_field_cos4_check": outer,
    }


def time_case(
    name: str,
    fn: Callable[[], Any],
    warmups: int,
    repeats: int,
    context: dict[str, Any],
    extra: Callable[[Any], dict[str, Any]],
) -> tuple[dict[str, Any], Any]:
    for _ in range(warmups):
        fn()

    elapsed_ms: list[float] = []
    last_result = None
    for _ in range(repeats):
        start = time.perf_counter()
        last_result = fn()
        elapsed_ms.append((time.perf_counter() - start) * 1000.0)

    total_rays = max(1, int(context.get("total_rays", 1)))
    surface_ray_count = max(1, int(context.get("surface_ray_count", total_rays)))
    row = {
        "name": name,
        "median_ms": stats.median(elapsed_ms),
        "p95_ms": percentile(elapsed_ms, 0.95),
        "mean_ms": stats.mean(elapsed_ms),
        "min_ms": min(elapsed_ms),
        "max_ms": max(elapsed_ms),
        "warmups": warmups,
        "repeats": repeats,
        "samples_ms": elapsed_ms,
        "per_ray_us_median": stats.median(elapsed_ms) * 1000.0 / total_rays,
        "per_surface_ray_us_median": stats.median(elapsed_ms) * 1000.0 / surface_ray_count,
        "context": context,
        "details": extra(last_result),
    }
    return row, last_result


def run_benchmark(profile: str) -> dict[str, Any]:
    settings = PROFILES[profile]
    system = load_system(build_spec_like_system())
    compiled = compile_system(system)
    surface_count = len(system.surfaces)
    warmups = int(settings["warmups"])
    repeats = int(settings["repeats"])

    cases: list[tuple[str, Callable[[], Any], dict[str, Any], Callable[[Any], dict[str, Any]]]] = []
    for mode in ["full", "paraxial", "off"]:
        preview_samples = int(settings["preview_samples"])
        context = case_context(
            fields=FIELDS_3,
            wavelengths=WAVELENGTHS_3,
            samples_per_field=preview_samples,
            surface_count=surface_count,
            ray_aiming_mode=mode,
        )
        cases.append(
            (
                f"trace preview {mode} aiming: 3 fields x 3 wavelengths x {preview_samples} rays",
                lambda mode=mode, preview_samples=preview_samples: trace_forward(
                    compiled,
                    FIELDS_3,
                    {"samples_per_field": preview_samples, "pupil_distribution": "grid", "ray_aiming": {"mode": mode}},
                    WAVELENGTHS_3,
                ),
                context,
                summarize_trace,
            )
        )

    spot_samples = int(settings["spot_samples"])
    cases.append(
        (
            f"trace spot full aiming: 5 fields x 3 wavelengths x {spot_samples} rays",
            lambda: trace_forward(
                compiled,
                FIELDS_5,
                {"samples_per_field": spot_samples, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
                WAVELENGTHS_3,
            ),
            case_context(
                fields=FIELDS_5,
                wavelengths=WAVELENGTHS_3,
                samples_per_field=spot_samples,
                surface_count=surface_count,
                ray_aiming_mode="full",
            ),
            summarize_trace,
        )
    )

    analysis_samples = int(settings["analysis_samples"])
    analysis_context = case_context(
        fields=[FIELDS_3[0]],
        wavelengths=[587.56],
        samples_per_field=analysis_samples,
        surface_count=surface_count,
        ray_aiming_mode="full",
    )
    analysis_trace = trace_forward(
        compiled,
        [FIELDS_3[0]],
        {"samples_per_field": analysis_samples, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
        [587.56],
    )
    cases.append(
        (
            f"geometric PSF from {analysis_samples}-ray full-aim trace",
            lambda: analyze_geometric_psf(analysis_trace, grid_size=32),
            analysis_context,
            lambda result: {"total_energy": result.total_energy, "grid": [len(result.grid), len(result.grid[0]) if result.grid else 0]},
        )
    )
    cases.append(
        (
            f"geometric MTF from {analysis_samples}-ray full-aim trace",
            lambda: analyze_geometric_mtf(analysis_trace, [0.0, 10.0, 20.0, 40.0]),
            analysis_context,
            lambda result: {"points": len(result.points), "mtf40_radial": result.points[-1].mtf_radial if result.points else None},
        )
    )

    ri_samples = int(settings["preview_samples"])
    cases.append(
        (
            "relative illumination full aiming: 5 fields x 3 wavelengths, 15 deg outer fields",
            lambda: analyze_relative_illumination(
                compiled,
                RI_FIELDS_5,
                {"samples_per_field": ri_samples, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
                WAVELENGTHS_3,
            ),
            case_context(
                fields=RI_FIELDS_5,
                wavelengths=WAVELENGTHS_3,
                samples_per_field=ri_samples,
                surface_count=surface_count,
                ray_aiming_mode="full",
            ),
            summarize_relative_illumination,
        )
    )

    evaluate_samples = int(settings["preview_samples"])
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
                ray_sampling={"samples_per_field": evaluate_samples, "pupil_distribution": "grid", "ray_aiming": {"mode": "full"}},
            ),
            case_context(
                fields=FIELDS_3,
                wavelengths=WAVELENGTHS_3,
                samples_per_field=evaluate_samples,
                surface_count=surface_count,
                ray_aiming_mode="full",
            ),
            lambda result: {"status": result.status, "score": result.merit.score if result.merit else None},
        )
    )

    results = []
    for name, fn, context, extra in cases:
        timing, _ = time_case(name, fn, warmups, repeats, context, extra)
        results.append(timing)

    measured_at = datetime.now(JST)
    git_short = git_value("rev-parse", "--short", "HEAD")
    return {
        "benchmark_schema": 2,
        "profile": profile,
        "measured_at_jst": measured_at.isoformat(timespec="seconds"),
        "source_commit": git_short,
        "git_dirty": git_dirty(),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "system": {
            "name": system.name,
            "surfaces": surface_count,
            "refractive_surfaces": sum(1 for surface in system.surfaces if surface.kind == "refractive"),
            "aspheres": sum(1 for surface in system.surfaces if surface.surface_type == "aspherical_even"),
            "wavelengths": WAVELENGTHS_3,
        },
        "settings": settings,
        "results": results,
    }


def save_result(result: dict[str, Any]) -> Path:
    out_dir = ROOT / "bench_results"
    out_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    commit = str(result.get("source_commit") or "unknown")
    path = out_dir / f"{timestamp}_{commit}.json"
    result["result_file"] = str(path.relative_to(ROOT)).replace("\\", "/")
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def print_summary(result: dict[str, Any], saved_path: Path | None) -> None:
    system = result["system"]
    print(
        "Spec-like benchmark: "
        f"{system['surfaces']} surfaces, {system['refractive_surfaces']} refractive, "
        f"{system['aspheres']} aspheres, {len(system['wavelengths'])} wavelengths"
    )
    print(f"Profile: {result['profile']}  Settings: {result['settings']}")
    if saved_path is not None:
        print(f"Saved: {saved_path.relative_to(ROOT)}")
    for row in result["results"]:
        print(
            f"- {row['name']}: median={row['median_ms']:.3f}ms "
            f"p95={row['p95_ms']:.3f}ms "
            f"per_ray={row['per_ray_us_median']:.3f}us "
            f"per_surface_ray={row['per_surface_ray_us_median']:.3f}us "
            f"details={row['details']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a spec-like full-ray-aiming optical engine benchmark.")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="default")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--no-save", action="store_true", help="Do not append a bench_results JSON history file.")
    args = parser.parse_args()

    result = run_benchmark(args.profile)
    saved_path = None if args.no_save else save_result(result)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return

    print_summary(result, saved_path)


if __name__ == "__main__":
    main()
