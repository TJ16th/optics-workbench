from __future__ import annotations

import argparse
import json
import statistics as stats
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from optics_engine.api.main import app  # noqa: E402


COMMON_MATERIALS: list[dict[str, Any]] = [
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
]

FIELDS_3 = [
    {"id": "center", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 0.0},
    {"id": "mid_y", "type": "angular", "theta_y_deg": 5.0, "theta_z_deg": 0.0},
    {"id": "mid_z", "type": "angular", "theta_y_deg": 0.0, "theta_z_deg": 5.0},
]

WAVELENGTHS_3 = [486.13, 587.56, 656.27]


def source_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def p002_system() -> dict[str, Any]:
    return {
        "name": "P002 N-BK7 Biconvex Singlet",
        "units": "mm",
        "optical_axis": "+X",
        "system_type": "focal",
        "wavelengths_nm": {"primary": 587.56, "samples": WAVELENGTHS_3},
        "materials": COMMON_MATERIALS,
        "surfaces": [
            {"id": "STOP", "kind": "aperture_stop", "surface_type": "plane", "thickness_after_mm": 2.0, "semi_diameter_mm": 8.0, "aperture": {"shape": "circle", "semi_diameter_mm": 8.0}},
            {"id": "S1", "kind": "refractive", "surface_type": "spherical", "radius_mm": 50.0, "thickness_after_mm": 5.0, "material_after": "N-BK7", "semi_diameter_mm": 15.0},
            {"id": "S2", "kind": "refractive", "surface_type": "spherical", "radius_mm": -50.0, "thickness_after_mm": 46.5, "material_after": "AIR", "semi_diameter_mm": 15.0},
            {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
        ],
    }


def p003_system() -> dict[str, Any]:
    return {
        "name": "P003 Achromat Doublet 100mm",
        "units": "mm",
        "optical_axis": "+X",
        "system_type": "focal",
        "wavelengths_nm": {"primary": 587.56, "samples": WAVELENGTHS_3},
        "materials": COMMON_MATERIALS,
        "surfaces": [
            {
                "id": "STOP",
                "kind": "aperture_stop",
                "surface_type": "plane",
                "thickness_after_mm": 1.5,
                "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0},
                "aperture": {"shape": "circle", "semi_diameter_mm": {"variable": "iris_radius_mm", "default": 10.0}},
            },
            {"id": "S1", "kind": "refractive", "surface_type": "spherical", "radius_mm": 62.5, "thickness_after_mm": 4.0, "material_after": "N-BK7", "semi_diameter_mm": 14.0},
            {"id": "S2", "kind": "refractive", "surface_type": "spherical", "radius_mm": -43.0, "thickness_after_mm": 2.0, "material_after": "N-F2", "semi_diameter_mm": 14.0},
            {"id": "S3", "kind": "refractive", "surface_type": "spherical", "radius_mm": -125.0, "thickness_after_mm": 96.0, "material_after": "AIR", "semi_diameter_mm": 14.0},
            {"id": "IMG", "kind": "sensor", "surface_type": "plane", "sensor": {"width_mm": 36.0, "height_mm": 24.0}},
        ],
        "groups": [
            {"id": "FOCUS_G", "name": "Focus group", "from_surface": "S1", "to_surface": "S3"},
            {"id": "OIS_G", "name": "OIS decenter/tilt group", "from_surface": "S2", "to_surface": "S3"},
        ],
        "zoom_positions": [
            {"id": "infinity", "focal_length_nominal_mm": 100.0, "group_positions": {"FOCUS_G": {"shift_x_mm": 0.0}}},
            {"id": "close_focus", "focal_length_nominal_mm": 100.0, "group_positions": {"FOCUS_G": {"shift_x_mm": 2.0}}},
        ],
    }


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((pct / 100.0) * (len(ordered) - 1))))
    return ordered[index]


def register(client: TestClient, system: dict[str, Any]) -> str:
    response = client.post("/v1/systems/register", json=system)
    response.raise_for_status()
    return response.json()["system_id"]


def preview_payload(system_id: str, *, samples: int, configuration: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "system_id": system_id,
        "fields": FIELDS_3,
        "ray_sampling": {"samples_per_field": samples, "pupil_distribution": "grid", "ray_aiming": {"mode": "paraxial"}},
        "wavelengths_nm": WAVELENGTHS_3,
        "configuration": configuration or {},
        "options": {"profiling": True},
    }


def time_preview(client: TestClient, name: str, payload: dict[str, Any], repeats: int) -> dict[str, Any]:
    elapsed_ms: list[float] = []
    last_json: dict[str, Any] = {}
    last_size = 0
    for _ in range(repeats):
        start = time.perf_counter()
        response = client.post("/v1/education/preview", json=payload)
        elapsed_ms.append((time.perf_counter() - start) * 1000.0)
        response.raise_for_status()
        last_size = len(response.content)
        last_json = response.json()

    paths = last_json.get("paths") or []
    alive_path = next((path for path, status in zip(paths, last_json.get("status", [])) if status == "alive"), [])
    profiling = (last_json.get("metadata") or {}).get("profiling") or {}
    return {
        "name": name,
        "repeats": repeats,
        "median_http_ms": round(stats.median(elapsed_ms), 3),
        "p95_http_ms": round(percentile(elapsed_ms, 95), 3),
        "min_http_ms": round(min(elapsed_ms), 3),
        "max_http_ms": round(max(elapsed_ms), 3),
        "response_bytes": last_size,
        "paths_present": "paths" in last_json,
        "path_count": len(paths),
        "first_alive_path_surface_ids": [entry["surface_id"] for entry in alive_path],
        "rays": len(last_json.get("status", [])),
        "arrived": sum(1 for status in last_json.get("status", []) if status == "alive"),
        "last_engine_profiling_ms": profiling,
    }


def run(repeats: int) -> dict[str, Any]:
    client = TestClient(app)
    p002_id = register(client, p002_system())
    p003_id = register(client, p003_system())
    debounce_ms = 70
    cases = [
        ("p002_run_preview_paths", preview_payload(p002_id, samples=5)),
        ("p003_group_shift_drag_preview_paths", preview_payload(p003_id, samples=5, configuration={"group_positions": {"FOCUS_G": {"shift_x_mm": 1.5}}})),
        ("p003_aperture_drag_preview_paths", preview_payload(p003_id, samples=5, configuration={"variables": {"iris_radius_mm": 5.0}})),
        (
            "p003_decenter_tilt_drag_preview_paths",
            preview_payload(
                p003_id,
                samples=5,
                configuration={
                    "decenters": [{"group": "OIS_G", "shift_y_mm": 1.2}],
                    "tilts": [{"group": "OIS_G", "tilt_z_deg": 2.0, "rotation_center": {"reference": "from_surface_vertex"}}],
                },
            ),
        ),
    ]
    results = []
    for name, payload in cases:
        row = time_preview(client, name, payload, repeats)
        row["effective_ui_median_ms"] = round(debounce_ms + row["median_http_ms"], 3)
        row["effective_ui_p95_ms"] = round(debounce_ms + row["p95_http_ms"], 3)
        results.append(row)
    return {
        "task": "education_preview_paths_fix",
        "measured_at_jst": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source_commit": source_commit(),
        "api_surface": "/v1/education/preview via FastAPI TestClient",
        "previous_ui_debounce_ms": 70,
        "notes": [
            "Preview endpoint forces store_path=True and now serializes paths through the shared forward response.",
            "Measurements include in-process FastAPI/TestClient request and JSON response serialization.",
            "Each drag-preview case uses 3 fields x 3 wavelengths x 5 rays = 45 rays.",
        ],
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure /v1/education/preview latency with returned paths.")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.repeats)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
