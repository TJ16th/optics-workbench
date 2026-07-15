# R131 push実行報告

## 状態

**Done with noted limitation**。`master`の通常pushとIssue #25の処理は完了したが、push後のGitHub Actionsは`engine`および`pii`ジョブの失敗により赤となった。R131の指示に従い、本タスクでは修正コミットを作成していない。

## push前確認

- push対象HEAD: `b4d0fb15735b0c8eb93b80b8befd2585b86bdc4a`
- R130で確認したmerge commit `170ef68`を履歴に含むことを確認した。
- `origin/master...HEAD`: `0 206`（behind 0 / ahead 206）
- R130報告後に新しい`feat` / `fix`等の実装コミットが増えていないことを確認した。
- 未追跡差分は本R131指示書のみだった。

## push結果

- 実行コマンド: `git push origin master`
- 結果: 成功（`be97d58..b4d0fb1 master -> master`）
- force push、rebase、履歴書き換えは実施していない。
- push直後の`git rev-list --left-right --count origin/master...HEAD`: `0 0`
- GitHub上の`master`先端: `b4d0fb15735b0c8eb93b80b8befd2585b86bdc4a`

## GitHub Actions結果

- Run: [CI 29427984708](https://github.com/TJ16th/optics-workbench/actions/runs/29427984708)
- 対象commit: `b4d0fb15735b0c8eb93b80b8befd2585b86bdc4a`
- 総合結果: `failure`
- `ui`: 成功（`npm run ci`およびpseudo-locale buildを含む）
- `engine`: 失敗（`28 failed, 170 passed, 1 skipped, 1 warning`）
- `pii`: 失敗

### engine失敗の調査結果

失敗した28件はすべて`tests/test_preset_api_smoke.py`の`_shipped_presets()`から起動するNode補助処理で、`subprocess.CalledProcessError`となった。同処理は`require('typescript')`を使うが、CIの`engine`ジョブはPython依存だけを導入し、`actions/setup-node`および`npm ci`を実行していない。一方、ローカルでは既存の`node_modules`を利用できるためR130時点で`198 passed`だった。したがって数値計算の回帰ではなく、engineジョブのNode/TypeScript依存導入条件がローカルと一致していないことが直接原因である。

R131のスコープに従い、workflowやテストの修正は行っていない。

### PII失敗の調査結果

`python scripts/pii_scan.py`が、R130で既知・承認済みだった39件の`workspace_absolute_path` / `codex_runtime_cache`を検出してexit code 1となった。主な対象は`AGENTS.md`、`scripts/sync_cross_workspace_docs.ps1`、過去の作業指示書・報告書である。R130で公開pushの例外は承認されたが、CIスキャナ側に例外設定は追加されていないため、想定どおりジョブは失敗した。

R131のスコープに従い、検出対象やスキャナの修正は行っていない。

## Issue #25

- 対象: [Issue #25](https://github.com/TJ16th/optics-workbench/issues/25)
- push時に参照コミットによって自動的にclose済みであることを確認した（close時刻: `2026-07-15T15:25:01Z`）。
- 実装根拠`5e5160b`、UIジョブ成功、run全体に残る別件の失敗を明記した[コメント](https://github.com/TJ16th/optics-workbench/issues/25#issuecomment-4982368327)を追記した。

## 根拠

- 公開対象先端: `b4d0fb1`（R130公開前監査報告）
- 履歴統合: `170ef68`（R130 merge）
- P004実装: `5e5160b`
- R130ローカル検証: `python -m pytest -q` = `198 passed`、UI CI = `65 passed`、pseudo-locale build成功
- R131リモート検証: GitHub Actions run `29427984708`（`ui`成功、`engine` / `pii`失敗）

## 残件

GitHub Actionsをgreenに戻すには、engineジョブのNode/TypeScript依存導入と、承認済み絶対パスに対するPIIスキャン方針を別タスクで決定・修正する必要がある。
