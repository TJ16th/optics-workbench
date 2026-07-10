import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "create_issues_from_backlog.py"


def load_module():
    spec = importlib.util.spec_from_file_location("create_issues_from_backlog", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def issue(title, labels=None, already_created=False, number=None):
    return {
        "title": title,
        "body": f"body for {title}",
        "labels": labels or [],
        "already_created": already_created,
        "issue_number": number,
    }


def test_ensure_labels_creates_missing_labels(monkeypatch):
    module = load_module()
    created_labels = []
    created_issues = []

    monkeypatch.setattr(module, "list_labels", lambda repo: {"ui"})
    monkeypatch.setattr(module, "issue_exists", lambda repo, title: None)

    def fake_create_label(repo, label):
        created_labels.append((repo, label))

    def fake_create_issue(repo, title, body, labels):
        created_issues.append((repo, title, body, labels))
        return f"https://github.com/{repo}/issues/123"

    monkeypatch.setattr(module, "create_label", fake_create_label)
    monkeypatch.setattr(module, "create_issue", fake_create_issue)

    result = module.process_issues(
        "owner/repo",
        [issue("needs engine label", ["ui", "engine"])],
        dry_run=False,
    )

    assert result.failed == []
    assert result.created == [("needs engine label", "https://github.com/owner/repo/issues/123")]
    assert created_labels == [("owner/repo", "engine")]
    assert created_issues[0][3] == ["ui", "engine"]


def test_process_issues_continues_after_single_failure(monkeypatch):
    module = load_module()
    created_titles = []

    monkeypatch.setattr(module, "list_labels", lambda repo: {"engine"})

    def fake_issue_exists(repo, title):
        if title == "first fails":
            raise subprocess.CalledProcessError(
                1,
                ["gh", "issue", "list"],
                stderr="temporary gh failure",
            )
        return None

    def fake_create_issue(repo, title, body, labels):
        created_titles.append(title)
        return f"https://github.com/{repo}/issues/456"

    monkeypatch.setattr(module, "issue_exists", fake_issue_exists)
    monkeypatch.setattr(module, "create_issue", fake_create_issue)

    result = module.process_issues(
        "owner/repo",
        [issue("first fails", ["engine"]), issue("second succeeds", ["engine"])],
        dry_run=False,
    )

    assert created_titles == ["second succeeds"]
    assert result.created == [("second succeeds", "https://github.com/owner/repo/issues/456")]
    assert len(result.failed) == 1
    assert result.failed[0][0] == "first fails"
    assert "temporary gh failure" in result.failed[0][1]


def test_backlog_uses_supported_label_taxonomy():
    text = (Path(__file__).resolve().parents[1] / "doc" / "reports" / "issues_backlog.md").read_text(
        encoding="utf-8"
    )

    assert "`architecture`" not in text
