from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from optics_engine import evaluate_system, load_system
from optics_engine.api.main import app
from optics_engine.optimization import _evaluate_with_jacobian


PRESETS_PATH = ROOT / "apps" / "workbench-ui" / "src" / "domain" / "presets.ts"
NODE_LOADER = r"""
const fs = require('fs');
const ts = require('typescript');
const source = fs.readFileSync(process.argv[1], 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const module = { exports: {} };
new Function('exports', 'module', 'require', js)(module.exports, module, require);
console.log(JSON.stringify(module.exports.presets.map(({ id, system }) => ({ id, system }))));
"""

PRESET_IDS = ("P002", "P007", "P012", "P011")
EVALUATION = {
    "operands": [
        {"metric": "ray_fan_error", "field_id": "center", "wavelength_nm": 587.56, "target": 0.05, "tolerance": 0.02, "weight": 2.0},
        {"metric": "longitudinal_aberration", "field_id": "center", "wavelength_nm": 587.56, "target": 1.0, "tolerance": 0.25, "weight": 0.5},
    ],
    "fields": [{"id": "center", "theta_y_deg": 0.0, "theta_z_deg": 0.0}],
    "wavelengths": [587.56],
}
SAMPLING = {
    "samples_per_field": 9,
    "pupil_distribution": "grid",
    "ray_aiming": {"mode": "full", "strategy": "exact", "tolerance_mm": 1.0e-6, "max_iterations": 20},
}


def shipped_presets() -> dict[str, dict[str, Any]]:
    node = shutil.which("node") or shutil.which("node.exe")
    if node is None:
        raise RuntimeError("Node.js is required to load shipped presets")
    completed = subprocess.run(
        [node, "-e", NODE_LOADER, str(PRESETS_PATH)], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return {row["id"]: row["system"] for row in json.loads(completed.stdout) if row["id"] in PRESET_IDS}


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
        "samples_ms": samples,
    }


def variable_keys(system, count: int) -> list[str]:
    keys: list[str] = []
    for surface in system.surfaces:
        if surface.kind not in {"refractive", "mirror"}:
            continue
        keys.extend([f"{surface.id}_radius_mm", f"{surface.id}_thickness_after_mm"])
    if any(surface.kind == "aperture_stop" for surface in system.surfaces):
        keys.append("iris_radius_mm")
    if len(keys) < count:
        raise RuntimeError(f"system {system.name} has only {len(keys)} benchmark variables")
    return keys[:count]


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
        j3 = measure(lambda: evaluate_system(system, EVALUATION, ray_sampling=SAMPLING, jacobian=request), repeats)
        target = baseline["median_ms"] * 1.25
        rows.append(
            {
                "variable_count": count,
                "variables": variables,
                "baseline_cold": baseline,
                "j2_independent_exact": j2,
                "j3_request_local_warm": j3,
                "j2_over_j3_speedup": j2["median_ms"] / j3["median_ms"],
                "j3_over_baseline": j3["median_ms"] / baseline["median_ms"],
                "target_1_25x_cold_ms": target,
                "j3_over_1_25x_target": j3["median_ms"] / target,
                "meets_1_25x_cold": j3["median_ms"] <= target,
            }
        )
    return rows


def http_row(system, repeats: int) -> dict[str, Any]:
    client = TestClient(app)
    payload = system.model_dump(mode="json")
    payload.update({"evaluation": EVALUATION, "ray_sampling": SAMPLING})
    variable = variable_keys(system, 1)[0]
    baseline = measure(lambda: client.post("/v1/optics/evaluate", json=payload).raise_for_status(), repeats)
    jacobian_payload = {**payload, "jacobian": {"mode": "forward_diff", "variables": [variable]}}
    j3 = measure(lambda: client.post("/v1/optics/evaluate", json=jacobian_payload).raise_for_status(), repeats)
    return {
        "variable": variable,
        "baseline": baseline,
        "j3_request_local_warm": j3,
        "j3_over_baseline": j3["median_ms"] / baseline["median_ms"],
    }


def git_value(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    presets = shipped_presets()
    result: dict[str, Any] = {
        "task": "R91",
        "measured_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source_commit": git_value("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(git_value("status", "--porcelain")),
        "workload": {
            "basis": "R83 ray_fan_error + longitudinal_aberration",
            "fields": 1,
            "wavelengths": 1,
            "samples_per_field": 9,
            "ray_aiming": "full exact",
            "finite_difference": "forward_diff",
        },
        "prior_r83": "bench_results/20260714_134920_r83_optimization_throughput.json",
        "presets": {},
    }
    for preset_id in PRESET_IDS:
        system = load_system(presets[preset_id])
        counts = [1, 5, 10, 20] if preset_id == "P011" else [1]
        result["presets"][preset_id] = {
            "local": local_rows(system, counts, args.repeats),
            "http_one_variable": http_row(system, max(3, args.repeats // 2)),
        }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ROOT / "bench_results" / f"{timestamp}_r91_jacobian.json"
    result["result_file"] = str(path.relative_to(ROOT)).replace("\\", "/")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    for preset_id, preset in result["presets"].items():
        for row in preset["local"]:
            print(
                preset_id,
                row["variable_count"],
                f"J2={row['j2_independent_exact']['median_ms']:.3f}ms",
                f"J3={row['j3_request_local_warm']['median_ms']:.3f}ms",
                f"speedup={row['j2_over_j3_speedup']:.3f}x",
                f"vs1.25cold={row['j3_over_1_25x_target']:.3f}x",
            )


if __name__ == "__main__":
    main()
