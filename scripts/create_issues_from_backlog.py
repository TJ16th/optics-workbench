#!/usr/bin/env python3
"""Create GitHub Issues from doc/reports/issues_backlog.md.

The expected Markdown structure is:

    ## Issue: <title>

    ラベル案: `label1`, `label2`

    ### 背景
    ...
    ### 対応案
    ...
    ### 受け入れ条件
    ...

Entries already marked with ``[issue: #123]`` in the heading are skipped.
When run in GitHub Actions, pass ``GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ISSUE_HEADER_RE = re.compile(r"^## Issue: (?P<title>.+?)(?:\s*\[issue: #(?P<num>\d+)\])?\s*$")
LABEL_LINE_RE = re.compile(r"^ラベル案:\s*(?P<labels>.+)$")


def parse_backlog(text: str) -> list[dict]:
    lines = text.splitlines()
    issues: list[dict] = []
    current: dict | None = None
    body_lines: list[str] = []

    def flush() -> None:
        if current is not None:
            current["body"] = "\n".join(body_lines).strip()
            issues.append(current)

    for line in lines:
        match = ISSUE_HEADER_RE.match(line)
        if match:
            flush()
            current = {
                "title": match.group("title").strip(),
                "already_created": match.group("num") is not None,
                "issue_number": match.group("num"),
                "labels": [],
            }
            body_lines = []
            continue
        if current is None:
            continue
        label_match = LABEL_LINE_RE.match(line.strip())
        if label_match:
            labels = [item.strip(" `") for item in label_match.group("labels").split(",")]
            current["labels"] = [label for label in labels if label]
            continue
        body_lines.append(line)
    flush()
    return issues


def issue_exists(repo: str, title: str) -> str | None:
    """Return an existing issue number if an all-state issue has the same title."""
    result = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--search",
            f'"{title}" in:title',
            "--json",
            "number,title",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    for item in json.loads(result.stdout or "[]"):
        if item["title"].strip() == title:
            return str(item["number"])
    return None


def create_issue(repo: str, title: str, body: str, labels: list[str]) -> str:
    command = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for label in labels:
        command += ["--label", label]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout.strip().splitlines()[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--annotate",
        action="store_true",
        help="After successful creation, append [issue: #N] markers to backlog headings.",
    )
    args = parser.parse_args()

    text = args.file.read_text(encoding="utf-8")
    issues = parse_backlog(text)
    if not issues:
        print("No '## Issue: ...' entries found.")
        return 0

    created: list[tuple[str, str]] = []
    skipped: list[tuple[str, str | None]] = []
    pending = [issue for issue in issues if not issue["already_created"]]

    print(f"Parsed issues: {len(issues)}")
    print(f"Pending issues: {len(pending)}")

    for item in issues:
        if item["already_created"]:
            skipped.append((item["title"], item["issue_number"]))
            print(f"SKIP (already annotated, #{item['issue_number']}): {item['title']}")
            continue
        if args.dry_run:
            print(f"[dry-run] would create: {item['title']} (labels: {item['labels']})")
            created.append((item["title"], "DRYRUN"))
            continue
        duplicate = issue_exists(args.repo, item["title"])
        if duplicate:
            print(f"SKIP (duplicate found, #{duplicate}): {item['title']}")
            skipped.append((item["title"], duplicate))
            continue
        url = create_issue(args.repo, item["title"], item["body"], item["labels"])
        print(f"CREATED: {item['title']} -> {url}")
        created.append((item["title"], url))

    print("\n=== Summary ===")
    print(f"created: {len(created)}, skipped(existing): {len(skipped)}")
    for title, url in created:
        print(f"  + {title}: {url}")
    for title, number in skipped:
        print(f"  = {title}: #{number}")

    if args.annotate and created and not args.dry_run:
        new_text = text
        for title, url in created:
            number = url.rstrip("/").rsplit("/", 1)[-1]
            new_text = new_text.replace(
                f"## Issue: {title}",
                f"## Issue: {title} [issue: #{number}]",
                1,
            )
        args.file.write_text(new_text, encoding="utf-8")
        print(f"\nAnnotated {args.file} with created issue numbers.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
