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
from dataclasses import dataclass
import json
import re
import subprocess
import sys
from pathlib import Path


ISSUE_HEADER_RE = re.compile(r"^## Issue: (?P<title>.+?)(?:\s*\[issue: #(?P<num>\d+)\])?\s*$")
LABEL_LINE_RE = re.compile(r"^ラベル案:\s*(?P<labels>.+)$")
DEFAULT_LABEL_COLOR = "ededed"


@dataclass
class IssueRunResult:
    created: list[tuple[str, str]]
    skipped: list[tuple[str, str | None]]
    failed: list[tuple[str, str]]


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
    result = run_gh(
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
        ]
    )
    for item in json.loads(result.stdout or "[]"):
        if item["title"].strip() == title:
            return str(item["number"])
    return None


def run_gh(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=True)


def list_labels(repo: str) -> set[str]:
    result = run_gh(
        [
            "gh",
            "label",
            "list",
            "--repo",
            repo,
            "--limit",
            "1000",
            "--json",
            "name",
        ]
    )
    return {item["name"] for item in json.loads(result.stdout or "[]")}


def create_label(repo: str, label: str) -> None:
    run_gh(
        [
            "gh",
            "label",
            "create",
            label,
            "--repo",
            repo,
            "--color",
            DEFAULT_LABEL_COLOR,
        ]
    )


def ensure_labels(repo: str, labels: list[str], known_labels: set[str]) -> None:
    for label in labels:
        if label in known_labels:
            continue
        try:
            create_label(repo, label)
        except subprocess.CalledProcessError:
            # Another workflow run may have created the label after list_labels().
            known_labels.update(list_labels(repo))
            if label not in known_labels:
                raise
        else:
            known_labels.add(label)


def create_issue(repo: str, title: str, body: str, labels: list[str]) -> str:
    command = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for label in labels:
        command += ["--label", label]
    result = run_gh(command)
    output_lines = result.stdout.strip().splitlines()
    if not output_lines:
        raise RuntimeError("gh issue create returned no output")
    return output_lines[-1]


def command_error_message(exc: BaseException) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        return detail or str(exc)
    return str(exc)


def process_issues(repo: str, issues: list[dict], dry_run: bool) -> IssueRunResult:
    result = IssueRunResult(created=[], skipped=[], failed=[])
    known_labels = set() if dry_run else list_labels(repo)

    for item in issues:
        if item["already_created"]:
            result.skipped.append((item["title"], item["issue_number"]))
            print(f"SKIP (already annotated, #{item['issue_number']}): {item['title']}")
            continue
        if dry_run:
            print(f"[dry-run] would create: {item['title']} (labels: {item['labels']})")
            result.created.append((item["title"], "DRYRUN"))
            continue

        try:
            duplicate = issue_exists(repo, item["title"])
            if duplicate:
                print(f"SKIP (duplicate found, #{duplicate}): {item['title']}")
                result.skipped.append((item["title"], duplicate))
                continue
            ensure_labels(repo, item["labels"], known_labels)
            url = create_issue(repo, item["title"], item["body"], item["labels"])
        except (subprocess.CalledProcessError, json.JSONDecodeError, RuntimeError) as exc:
            message = command_error_message(exc)
            print(f"FAILED: {item['title']} -> {message}", file=sys.stderr)
            result.failed.append((item["title"], message))
            continue

        print(f"CREATED: {item['title']} -> {url}")
        result.created.append((item["title"], url))

    return result


def annotate_created_issues(text: str, created: list[tuple[str, str]]) -> str:
    new_text = text
    for title, url in created:
        number = url.rstrip("/").rsplit("/", 1)[-1]
        new_text = new_text.replace(
            f"## Issue: {title}",
            f"## Issue: {title} [issue: #{number}]",
            1,
        )
    return new_text


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

    pending = [issue for issue in issues if not issue["already_created"]]

    print(f"Parsed issues: {len(issues)}")
    print(f"Pending issues: {len(pending)}")

    result = process_issues(args.repo, issues, args.dry_run)

    print("\n=== Summary ===")
    print(
        f"created: {len(result.created)}, "
        f"skipped(existing): {len(result.skipped)}, failed: {len(result.failed)}"
    )
    for title, url in result.created:
        print(f"  + {title}: {url}")
    for title, number in result.skipped:
        print(f"  = {title}: #{number}")
    for title, message in result.failed:
        print(f"  ! {title}: {message}")

    if args.annotate and result.created and not args.dry_run:
        new_text = annotate_created_issues(text, result.created)
        args.file.write_text(new_text, encoding="utf-8")
        print(f"\nAnnotated {args.file} with created issue numbers.")

    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
