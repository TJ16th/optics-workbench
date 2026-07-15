from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "scripts" / "pii_baseline.json"

EXCLUDED_DIRS = {
    ".git",
    ".i18n-parser",
    ".pytest_cache",
    ".test-build",
    "__pycache__",
    "dist",
    "htmlcov",
    "node_modules",
    "playwright-report",
    "test-results",
}

EXCLUDED_FILES = {
    "package-lock.json",
}

EXCLUDED_SUFFIXES = {
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".png",
    ".webp",
}

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("windows_user_path", re.compile(r"C:\\" + r"Users\\|C:/" + r"Users/", re.IGNORECASE)),
    ("workspace_absolute_path", re.compile(r"F:\\" + r"vscode|F:/" + r"vscode", re.IGNORECASE)),
    ("codex_runtime_cache", re.compile(r"App" + r"Data|codex-" + r"runtimes", re.IGNORECASE)),
    ("openai_token", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
]


@dataclass(frozen=True)
class Finding:
    path: str
    line_number: int
    pattern: str
    line_sha256: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.path, self.pattern, self.line_sha256)

    def display(self) -> str:
        return f"{self.path}:{self.line_number}: {self.pattern}"


def should_skip(path: Path, root: Path = ROOT) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    if path.name in EXCLUDED_FILES:
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def scan_file(path: Path, root: Path = ROOT) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        path=path.relative_to(root).as_posix(),
                        line_number=line_number,
                        pattern=name,
                        line_sha256=hashlib.sha256(line.encode("utf-8")).hexdigest(),
                    )
                )
    return findings


def scan_tree(root: Path = ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for path in root.rglob("*"):
        if path.is_file() and not should_skip(path, root):
            findings.extend(scan_file(path, root))
    return findings


def load_baseline(path: Path = BASELINE_PATH) -> Counter[tuple[str, str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("PII baseline must contain an entries list")

    baseline: Counter[tuple[str, str, str]] = Counter()
    for entry in entries:
        key = (entry["path"], entry["pattern"], entry["line_sha256"])
        occurrences = entry.get("occurrences", 1)
        if not isinstance(occurrences, int) or occurrences < 1:
            raise ValueError(f"Invalid PII baseline occurrence count for {key}")
        baseline[key] += occurrences
    return baseline


def evaluate_findings(
    findings: list[Finding], baseline: Counter[tuple[str, str, str]]
) -> tuple[list[Finding], Counter[tuple[str, str, str]], int]:
    remaining = baseline.copy()
    unexpected: list[Finding] = []
    approved_count = 0
    for finding in findings:
        if remaining[finding.key] > 0:
            remaining[finding.key] -= 1
            approved_count += 1
        else:
            unexpected.append(finding)
    stale = Counter({key: count for key, count in remaining.items() if count > 0})
    return unexpected, stale, approved_count


def main() -> int:
    try:
        baseline = load_baseline()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"PII baseline load failed: {error}", file=sys.stderr)
        return 1

    unexpected, stale, approved_count = evaluate_findings(scan_tree(), baseline)
    if unexpected or stale:
        print("PII/secret scan failed:", file=sys.stderr)
        if unexpected:
            print("Unexpected findings:", file=sys.stderr)
            print("\n".join(finding.display() for finding in unexpected), file=sys.stderr)
        if stale:
            print("Stale baseline entries:", file=sys.stderr)
            for (path, pattern, line_sha256), count in sorted(stale.items()):
                print(f"{path}: {pattern}: {line_sha256} x{count}", file=sys.stderr)
        return 1
    print(f"pii:scan ok ({approved_count} approved baseline findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
