from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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


def should_skip(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    if path.name in EXCLUDED_FILES:
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(f"{path.relative_to(ROOT)}:{line_number}: {name}")
    return findings


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and not should_skip(path):
            findings.extend(scan_file(path))
    if findings:
        print("PII/secret scan failed:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("pii:scan ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
