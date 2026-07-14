from __future__ import annotations

import argparse
import cProfile
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import pstats
import statistics
import subprocess
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optics_engine import evaluate_system, load_system
from optics_engine.optimization import _evaluate_with_jacobian

from benchmarks.r91_jacobian_benchmark import EVALUATION, PRESET_IDS, SAMPLING, shipped_presets, variable_keys


def measure(fn: Callable[[], Any], repeats: int) -> dict[str, Any]:
    fn()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return {
        "count": repeats,
        "mean_ms": statistics.mean(samples),
        "median_ms": statistics.median(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
        "stddev_ms": statistics.pstdev(samples),
        "samples_ms": samples,
    }


def profile_text(fn: Callable[[], Any]) -> str:
    profiler = cProfile.Profile()
    profiler.enable()
    fn()
    profiler.disable()
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(25)
    return stream.getvalue()


def local_rows(system, counts: list[int], repeats: int) -> list[dict[str, Any]]:
    baseline = measure(lambda: evaluate_system(system, EVALUATION, ray_sampling=SAMPLING), repeats)
    rows = []
    for count in counts:
        variables = variable_keys(system, count)
        request = {"mode": "forward_diff", "variables": variables}
        j2 = measure(
            lambda: _evaluate_with_jacobian(
                system,
                EVALUATION,
                configuration=None,
                variables=None,
                ray_sampling=SAMPLING,
                jacobian=request,
                warm_refinement=False,
            ),
            repeats,
        )
        j4 = measure(lambda: evaluate_system(system, EVALUATION, ray_sampling=SAMPLING, jacobian=request), repeats)
        target = baseline["median_ms"] * 1.25
        rows.append(
            {
                "variable_count": count,
                "variables": variables,
                "baseline_cold": baseline,
                "j2_independent_exact": j2,
                "j4_candidate_axis_batch": j4,
                "j2_over_j4_speedup": j2["median_ms"] / j4["median_ms"],
                "j4_over_baseline": j4["median_ms"] / baseline["median_ms"],
                "target_1_25x_cold_ms": target,
                "j4_over_1_25x_target": j4["median_ms"] / target,
                "meets_1_25x_cold": j4["median_ms"] <= target,
            }
        )
    return rows


def git_value(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    if args.repeats < 10:
        raise ValueError("R93 requires at least 10 repetitions")
    presets = shipped_presets()
    result: dict[str, Any] = {
        "task": "R93-work2",
        "measured_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source_commit": git_value("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(git_value("status", "--porcelain")),
        "repeats": args.repeats,
        "workload": {
            "basis": "R83/R91 ray_fan_error + longitudinal_aberration",
            "fields": 1,
            "wavelengths": 1,
            "samples_per_field": 9,
            "ray_aiming": "full exact",
            "finite_difference": "forward_diff",
        },
        "prior_r91": "bench_results/20260714_230137_r91_jacobian.json",
        "presets": {},
    }
    unmet: list[tuple[str, int, Any]] = []
    for preset_id in PRESET_IDS:
        system = load_system(presets[preset_id])
        counts = [1, 5, 10, 20] if preset_id == "P011" else [1]
        rows = local_rows(system, counts, args.repeats)
        result["presets"][preset_id] = {"local": rows}
        unmet.extend((preset_id, row["variable_count"], system) for row in rows if not row["meets_1_25x_cold"])

    if unmet:
        preset_id, count, system = max(unmet, key=lambda item: item[1])
        request = {"mode": "forward_diff", "variables": variable_keys(system, count)}
        result["profiling"] = {
            "preset_id": preset_id,
            "variable_count": count,
            "sort": "cumulative",
            "top_25": profile_text(lambda: evaluate_system(system, EVALUATION, ray_sampling=SAMPLING, jacobian=request)),
        }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ROOT / "bench_results" / f"{timestamp}_r93_jacobian.json"
    result["result_file"] = str(path.relative_to(ROOT)).replace("\\", "/")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    for preset_id, preset in result["presets"].items():
        for row in preset["local"]:
            print(
                preset_id,
                row["variable_count"],
                f"J2={row['j2_independent_exact']['median_ms']:.3f}ms",
                f"J4={row['j4_candidate_axis_batch']['median_ms']:.3f}ms",
                f"speedup={row['j2_over_j4_speedup']:.3f}x",
                f"vs1.25cold={row['j4_over_1_25x_target']:.3f}x",
                f"meets={row['meets_1_25x_cold']}",
            )


if __name__ == "__main__":
    main()
