from __future__ import annotations

from collections import Counter
from pathlib import Path

from scripts.pii_scan import evaluate_findings, load_baseline, scan_file, scan_tree


def test_approved_pii_baseline_matches_repository() -> None:
    unexpected, stale, approved_count = evaluate_findings(scan_tree(), load_baseline())

    assert unexpected == []
    assert stale == Counter()
    assert approved_count == 39


def test_new_pii_finding_is_not_covered_by_baseline(tmp_path: Path) -> None:
    candidate = tmp_path / "new.txt"
    candidate.write_text("F:\\vscode\\unapproved", encoding="utf-8")

    findings = scan_file(candidate, tmp_path)
    unexpected, stale, approved_count = evaluate_findings(findings, Counter())

    assert [finding.pattern for finding in unexpected] == ["workspace_absolute_path"]
    assert stale == Counter()
    assert approved_count == 0


def test_baseline_occurrence_count_does_not_allow_duplicates(tmp_path: Path) -> None:
    candidate = tmp_path / "duplicate.txt"
    candidate.write_text("F:\\vscode\\approved", encoding="utf-8")
    finding = scan_file(candidate, tmp_path)[0]

    unexpected, stale, approved_count = evaluate_findings(
        [finding, finding], Counter({finding.key: 1})
    )

    assert unexpected == [finding]
    assert stale == Counter()
    assert approved_count == 1
