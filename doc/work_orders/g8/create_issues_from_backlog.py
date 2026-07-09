#!/usr/bin/env python3
"""doc/reports/issues_backlog.md を読み、GitHub Issueとして未登録の項目を作成する。

想定するMarkdown構造:

    ## Issue: <タイトル>

    ラベル案: `label1`, `label2`

    ### 背景
    ...
    ### 対応案
    ...
    ### 受け入れ条件
    ...

すでに `[issue: #123]` のマーカーが見出し行に付いている項目はスキップする
（このマーカーは本スクリプトが作成後に自動付与する）。

実行にはローカル環境の `gh` CLI（GITHUB_TOKEN 認証済み）が必要。
GitHub Actions上では `env: GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` を渡して実行する。
"""
from __future__ import annotations

import argparse
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

    def flush():
        if current is not None:
            current["body"] = "\n".join(body_lines).strip()
            issues.append(current)

    for line in lines:
        m = ISSUE_HEADER_RE.match(line)
        if m:
            flush()
            current = {
                "title": m.group("title").strip(),
                "already_created": m.group("num") is not None,
                "issue_number": m.group("num"),
                "labels": [],
            }
            body_lines = []
            continue
        if current is None:
            continue
        lm = LABEL_LINE_RE.match(line.strip())
        if lm:
            labels = [x.strip(" `") for x in lm.group("labels").split(",")]
            current["labels"] = [l for l in labels if l]
            continue
        body_lines.append(line)
    flush()
    return issues


def issue_exists(repo: str, title: str) -> str | None:
    """タイトル完全一致のオープンIssueが既にあればその番号を返す。"""
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", "all",
         "--search", f'"{title}" in:title', "--json", "number,title"],
        capture_output=True, text=True, check=True,
    )
    import json
    for item in json.loads(result.stdout or "[]"):
        if item["title"].strip() == title:
            return str(item["number"])
    return None


def create_issue(repo: str, title: str, body: str, labels: list[str], dry_run: bool) -> str:
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for label in labels:
        cmd += ["--label", label]
    if dry_run:
        print(f"[dry-run] would create: {title} (labels: {labels})")
        return "DRYRUN"
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    url = result.stdout.strip().splitlines()[-1]
    return url


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--annotate", action="store_true",
                     help="作成成功後、backlogファイルの見出しに [issue: #N] を書き戻す")
    args = ap.parse_args()

    text = args.file.read_text(encoding="utf-8")
    issues = parse_backlog(text)
    if not issues:
        print("No '## Issue: ...' entries found.")
        return 0

    created = []
    skipped = []
    for item in issues:
        if item["already_created"]:
            skipped.append((item["title"], item["issue_number"]))
            continue
        dup = issue_exists(args.repo, item["title"])
        if dup:
            print(f"SKIP (duplicate found, #{dup}): {item['title']}")
            skipped.append((item["title"], dup))
            continue
        url_or_dryrun = create_issue(args.repo, item["title"], item["body"], item["labels"], args.dry_run)
        print(f"CREATED: {item['title']} -> {url_or_dryrun}")
        created.append((item["title"], url_or_dryrun))

    print("\n=== Summary ===")
    print(f"created: {len(created)}, skipped(existing): {len(skipped)}")
    for title, url in created:
        print(f"  + {title}: {url}")
    for title, num in skipped:
        print(f"  = {title}: #{num}")

    if args.annotate and created and not args.dry_run:
        new_text = text
        for title, url in created:
            num = url.rstrip("/").rsplit("/", 1)[-1]
            new_text = new_text.replace(
                f"## Issue: {title}",
                f"## Issue: {title} [issue: #{num}]",
                1,
            )
        args.file.write_text(new_text, encoding="utf-8")
        print(f"\nAnnotated {args.file} with created issue numbers.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
