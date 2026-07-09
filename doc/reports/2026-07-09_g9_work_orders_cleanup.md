# G9 doc/work_orders整理報告

作業日: 2026-07-09

## 概要

`doc/work_orders/` 直下にあった規約外ファイルと `g8/` フォルダを整理し、直下を `active/` / `done/` のみの状態に戻した。`README.md` は存在しなかったため対象外。

## 作業前インベントリ

`doc/work_orders/` 直下で `active/` / `done/` / `README.md` 以外に存在したもの:

| 種別 | パス |
| --- | --- |
| file | `doc/work_orders/codex_g6_finalize_and_push.md` |
| file | `doc/work_orders/codex_g7_ci_failure_investigation.md` |
| directory | `doc/work_orders/g8/` |
| file | `doc/work_orders/g8/AGENTS.md` |
| file | `doc/work_orders/g8/codex_g8_issue_workflow_switch.md` |
| file | `doc/work_orders/g8/create_issues_from_backlog.py` |
| file | `doc/work_orders/g8/github_workflows_create_issues.yml` |

追加で、既に完了済みだった `doc/work_orders/active/codex_g8_push_pending_changes.md` と、最新版指示書として `doc/archive/codex_g9_work_orders_cleanup.md` も整理対象に含めた。

## 移動・削除対応表

| 旧パス | 新パス / 処理 | 理由 |
| --- | --- | --- |
| `doc/work_orders/codex_g6_finalize_and_push.md` | `doc/work_orders/done/codex_g6_finalize_and_push.md` | G6完了報告 `doc/reports/2026-07-09_g6_public_release.md` が存在するため |
| `doc/work_orders/codex_g7_ci_failure_investigation.md` | `doc/work_orders/done/codex_g7_ci_failure_investigation.md` | G7完了報告 `doc/reports/2026-07-09_g7_ci_failure_investigation.md` が存在するため |
| `doc/work_orders/g8/codex_g8_issue_workflow_switch.md` | `doc/work_orders/done/codex_g8_issue_workflow_switch.md` | G8完了報告 `doc/reports/2026-07-09_g8_issue_workflow_switch.md` が存在するため |
| `doc/work_orders/active/codex_g8_push_pending_changes.md` | `doc/work_orders/done/codex_g8_push_pending_changes.md` | G8-pushは実行・push済みのため |
| `doc/archive/codex_g9_work_orders_cleanup.md` | `doc/work_orders/done/codex_g9_work_orders_cleanup.md` | ユーザー追加の最新版G9指示書であり、archiveに残さないため |
| `doc/work_orders/g8/AGENTS.md` | 削除 | ルート `AGENTS.md` より古いコピー。G8のIssue運用は反映済みで、G7のPlaywright CI注意書き等が欠けていたため |
| `doc/work_orders/g8/create_issues_from_backlog.py` | 削除 | 正規配置先 `scripts/create_issues_from_backlog.py` が存在し、dry-run挙動を改善した実装済み版を採用しているため |
| `doc/work_orders/g8/github_workflows_create_issues.yml` | 削除 | 正規配置先 `.github/workflows/create-issues.yml` が存在するため |

`github_pat_setup_memo.md` やPAT方式の旧Markdown指示書は存在しなかった。不明ファイルもなかった。

## AGENTS.md更新

G9指示書では、`doc/work_orders/` 直下に `active/`・`done/`・`README.md` 以外を置かない旨が明記済みとされていたが、実ファイルでは明示行が不足していた。そのため `AGENTS.md` の「正本ドキュメントと参照ルール」に以下を追記した。

```text
`doc/work_orders/` 直下には `active/`・`done/`・`README.md` 以外を置かない。
```

## 最終確認

作業後の `doc/work_orders/` 直下:

```text
active/
done/
```

`doc/work_orders/active/` に残る指示書:

```text
codex_github_publication_work_order.md
codex_performance_work_order.md
```

`doc/work_orders/done/` にはG6/G7/G8/G8-push/G9の完了済み指示書を集約した。

## 検証

| Command | Result |
| --- | --- |
| `Get-ChildItem -LiteralPath doc\work_orders -Force` | 直下は `active/` と `done/` のみ |
| `git diff --cached --name-status` | 移動・削除対象を確認 |

