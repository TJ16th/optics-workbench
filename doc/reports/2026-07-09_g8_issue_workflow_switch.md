# G8 Issueバックログ運用切り替え報告

作業日: 2026-07-09

## 概要

Issue作成をCodexが直接 `gh issue create` で行う方式から、人間がGitHub Actionsの `Create Issues From Backlog` ワークフローを手動起動し、リポジトリ組み込みの `GITHUB_TOKEN` で作成する方式へ切り替えた。

## 配置ファイル

- `scripts/create_issues_from_backlog.py`
- `.github/workflows/create-issues.yml`

G8付属ファイルは `doc/work_orders/g8/` に配置されていた。実行用ファイルは上記の正規配置先へ追加した。

## issues_backlog.md フォーマット確認

`doc/reports/issues_backlog.md` の既存Issue草案は10件。すべて以下の想定フォーマットに一致していたため、本文・見出し配置とも変更していない。

- `## Issue: <タイトル>`
- `ラベル案: ...`
- `### 背景`
- `### 対応案`
- `### 受け入れ条件`

## dry-run結果

`gh` CLIはこの環境では見つからなかったため、実Issue作成やGitHubへの書き込みは行っていない。ローカルdry-runはIssue作成を伴わないパース確認として実行した。

実行コマンド:

```bash
python scripts/create_issues_from_backlog.py --repo TJ16th/optics-workbench --file doc/reports/issues_backlog.md --dry-run
```

結果:

```text
Parsed issues: 10
Pending issues: 10
[dry-run] would create: Snapshot zip exportを実装する (labels: ['ui'])
[dry-run] would create: Snapshot比較をチャート重ね合わせまで拡張する (labels: ['ui'])
[dry-run] would create: Raw JSON/YAML advanced editorを実装する (labels: ['ui', 'good-first-issue'])
[dry-run] would create: PNG exportの画像比較テストを追加する (labels: ['ui', 'testing', 'good-first-issue'])
[dry-run] would create: 高密度spot/散布表示のPlotly scattergl対応 (labels: ['ui', 'performance'])
[dry-run] would create: supplement glossaryを本体用語集へ統合する (labels: ['ui', 'docs'])
[dry-run] would create: axis_convention import/exportを実装する (labels: ['engine', 'docs'])
[dry-run] would create: 回折PSF・波面収差・FFT瞳関数を追加する (labels: ['engine'])
[dry-run] would create: 視覚系のプリズム・正立像モデルを拡張する (labels: ['engine'])
[dry-run] would create: 長時間解析向けjob/WebSocketセッションを検討する (labels: ['engine', 'ui'])

=== Summary ===
created: 10, skipped(existing): 0
```

## AGENTS.md 整合確認

`AGENTS.md` に「GitHub Issue運用」節を追加し、以下が実物と一致することを確認した。

- backlog: `doc/reports/issues_backlog.md`
- workflow: `.github/workflows/create-issues.yml`
- workflow name: `Create Issues From Backlog`
- script: `scripts/create_issues_from_backlog.py`
- 認証方式: workflow内の `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`
- Codex自身は `gh issue create` を実行しない

## 検証

| Command | Result |
| --- | --- |
| `python scripts/create_issues_from_backlog.py --repo TJ16th/optics-workbench --file doc/reports/issues_backlog.md --dry-run` | Passed: 10件を認識 |
| `python -m py_compile scripts/create_issues_from_backlog.py` | Passed |
| `python scripts/pii_scan.py` | Passed |

## 残作業

実際のIssue作成はG8指示どおり人間側作業。GitHub Actionsタブから `Create Issues From Backlog` ワークフローを手動起動する。
