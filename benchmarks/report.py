from __future__ import annotations

import argparse
import base64
from io import BytesIO
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_results(results_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if "results" not in data:
            continue
        data["_source_file"] = str(path.relative_to(ROOT)).replace("\\", "/")
        rows.append(data)
    return rows


def html_escape(value: object) -> str:
    text = str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_chart(results: list[dict[str, Any]]) -> str:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return "<p>matplotlib is unavailable; chart generation was skipped.</p>"

    spec_runs = [result for result in results if result.get("benchmark_schema") == 2]
    if not spec_runs:
        return "<p>No schema 2 spec-like benchmark rows were found.</p>"

    case_names = sorted({row["name"] for result in spec_runs for row in result.get("results", [])})
    fig, ax = plt.subplots(figsize=(12, max(4, 0.35 * len(case_names))))
    for idx, name in enumerate(case_names):
        points = []
        labels = []
        for result in spec_runs:
            match = next((row for row in result.get("results", []) if row.get("name") == name), None)
            if match is None:
                continue
            points.append(float(match.get("median_ms", 0.0)))
            labels.append(str(result.get("source_commit", "?")))
        if points:
            ax.plot(points, [idx] * len(points), marker="o", linewidth=1.5, label=name if idx == 0 else None)
            for x, label in zip(points, labels):
                ax.annotate(label, (x, idx), textcoords="offset points", xytext=(4, 2), fontsize=7)
    ax.set_yticks(range(len(case_names)))
    ax.set_yticklabels(case_names, fontsize=8)
    ax.set_xlabel("median ms")
    ax.set_title("Spec-like benchmark history")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f'<img alt="Spec-like benchmark history" src="data:image/png;base64,{encoded}">'


def result_table(results: list[dict[str, Any]]) -> str:
    body = []
    for result in results:
        for row in result.get("results", []):
            context = row.get("context", {})
            body.append(
                "<tr>"
                f"<td>{html_escape(result.get('measured_at_jst', ''))}</td>"
                f"<td>{html_escape(result.get('source_commit', ''))}</td>"
                f"<td>{html_escape(result.get('profile', ''))}</td>"
                f"<td>{html_escape(row.get('name', ''))}</td>"
                f"<td>{float(row.get('median_ms', 0.0)):.3f}</td>"
                f"<td>{float(row.get('p95_ms', row.get('max_ms', 0.0))):.3f}</td>"
                f"<td>{float(row.get('per_ray_us_median', 0.0)):.3f}</td>"
                f"<td>{float(row.get('per_surface_ray_us_median', 0.0)):.3f}</td>"
                f"<td>{html_escape(context.get('total_rays', ''))}</td>"
                f"<td>{html_escape(context.get('surface_count', ''))}</td>"
                f"<td>{html_escape(result.get('_source_file', ''))}</td>"
                "</tr>"
            )
    return "\n".join(body)


def build_html(results: list[dict[str, Any]]) -> str:
    chart = build_chart(results)
    table = result_table(results)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Optics Engine Benchmark History</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; color: #1f2933; }}
    h1 {{ font-size: 24px; }}
    img {{ max-width: 100%; height: auto; border: 1px solid #d9e2ec; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 24px; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f0f4f8; }}
    td:nth-child(5), td:nth-child(6), td:nth-child(7), td:nth-child(8) {{ text-align: right; }}
  </style>
</head>
<body>
  <h1>Optics Engine Benchmark History</h1>
  <p>Static report generated from <code>bench_results/*.json</code>.</p>
  {chart}
  <table>
    <thead>
      <tr>
        <th>measured_at_jst</th>
        <th>commit</th>
        <th>profile</th>
        <th>case</th>
        <th>median ms</th>
        <th>p95 ms</th>
        <th>us/ray</th>
        <th>us/surface-ray</th>
        <th>rays</th>
        <th>surfaces</th>
        <th>source</th>
      </tr>
    </thead>
    <tbody>
      {table}
    </tbody>
  </table>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a static benchmark history HTML report.")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "bench_results")
    parser.add_argument("--output", type=Path, default=ROOT / "bench_results" / "report.html")
    args = parser.parse_args()

    results = load_results(args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(results), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
