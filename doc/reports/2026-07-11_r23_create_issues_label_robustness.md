# R23 Create Issues From Backlog ラベル堅牢化 完了報告

## 概要

`Create Issues From Backlog` ワークフローで、未作成ラベルにより `gh issue create --label ...` が失敗する問題へ対応した。
方針確認どおり、`architecture` ラベルは正式タクソノミーへ追加せず、既定の `engine` ラベルに統一した。

## 修正内容

- `scripts/create_issues_from_backlog.py` に、Issue作成前のラベル存在確認と自動作成を追加した。
  - `gh label list --json name` で既存ラベルを取得する。
  - 不足ラベルは `gh label create <name> --color ededed` で作成する。
  - ラベル作成直前に別実行で作成された場合に備え、作成失敗時はラベル一覧を再取得して存在すれば続行する。
- 1件のIssue処理失敗で全体が停止しないよう、pending Issueごとに例外を記録して後続処理を継続するようにした。
  - 成功分は従来どおり `--annotate` 時に `[issue: #N]` を付与する。
  - 失敗が1件以上ある場合は、全件処理後に終了コード `1` を返す。
- `doc/reports/issues_backlog.md` の `architecture` ラベル2箇所を `engine` に統一した。
- `tests/test_create_issues_from_backlog.py` を追加し、ラベル自動作成、部分継続、`architecture` ラベル非使用を固定した。

## 確認結果

- `python -m py_compile scripts/create_issues_from_backlog.py`: Passed
- `python -m pytest tests/test_create_issues_from_backlog.py -q`: `3 passed`
- `python -m pytest -q`: `63 passed, 1 skipped`
- `python scripts/create_issues_from_backlog.py --repo TJ16th/optics-workbench --file doc/reports/issues_backlog.md --dry-run`:
  - `Parsed issues: 25`
  - `Pending issues: 15`
  - `failed: 0`
  - `variable binding registry` と `multi-configuration` のラベルが `engine` のみに変わっていることを確認した。

## 備考

本タスクはスクリプト/ドキュメント変更のみであり、エンジンAPI・UIプロセスの再起動確認は対象外。
