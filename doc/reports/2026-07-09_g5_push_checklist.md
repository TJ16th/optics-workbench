# G5 Issue Backlog / Push前チェックリスト

作成日: 2026-07-09

## 実施内容

- `doc/reports/issues_backlog.md` をG5用のIssue草案として整理した。
- active指示書でカバー済みの項目と、Issue化する項目を分離した。
- `gh` CLIの有無を確認した。
- push前チェックリストを実行した。
- push自体は行っていない。

## gh CLI

`gh` CLIはこの環境では利用不可。

結果:

```text
gh: command not found
```

そのため、Issue一括登録スクリプトは作成せず、`doc/reports/issues_backlog.md` を人間がGitHub Issueへ転記・登録する前提とした。

## Issue Backlog

作成・更新ファイル:

```text
doc/reports/issues_backlog.md
```

Issue草案:

- Snapshot zip exportを実装する
- Snapshot比較をチャート重ね合わせまで拡張する
- Raw JSON/YAML advanced editorを実装する
- PNG exportの画像比較テストを追加する
- 高密度spot/散布表示のPlotly scattergl対応
- supplement glossaryを本体用語集へ統合する
- axis_convention import/exportを実装する
- 回折PSF・波面収差・FFT瞳関数を追加する
- 視覚系のプリズム・正立像モデルを拡張する
- 長時間解析向けjob/WebSocketセッションを検討する

Issue化しない項目:

- 性能改善・Golden Test・batch kernel・aiming cache・profiling metadata・Numba条件付き対応は `doc/work_orders/active/codex_performance_work_order.md` でカバー済み。
- `<REPO_NAME>` / `<COPYRIGHT_HOLDER>`、GitHub repo作成、pushは人間側作業。

## Push前チェックリスト

| 項目 | 結果 | 証跡 |
|---|---|---|
| G1スキャン再実行でゼロ件（履歴含む） | OK | `python scripts/pii_scan.py`: `pii:scan ok`; current-file rg: no findings; `git log --all -p` scan: no findings |
| `git status` クリーン、.gitignoreが生成物・キャプチャを除外 | OK予定 | G5コミット後に再確認する。`.gitignore` は `node_modules/`, `dist/`, `.pytest_cache/`, `test-results/`, `capture-*.png`, `*.egg-info/` 等を除外 |
| LICENSE / NOTICE / README / AGENTS.md 配置済み、プレースホルダ提示 | OK | 4ファイル存在確認済み |
| CI相当のコマンドが全てローカルグリーン | OK | 下記参照 |
| doc/archive/ 以外に旧版仕様が存在しない | OK | `doc/` 直下の旧仕様・旧指示書・旧report名検索で該当なし |
| bench_results/ に環境依存の個人情報が含まれない | OK | `bench_results/*.json` スキャンで該当なし |

## 残置プレースホルダ

人間側で確定する項目:

- `README.md`: `<REPO_NAME>`
- `NOTICE`: `<REPO_NAME>`
- `NOTICE`: `<COPYRIGHT_HOLDER>`

## ローカル検証結果

```text
python scripts/pii_scan.py: passed
python -m pytest -q: 57 passed, 1 warning
npm.cmd run ui:build:pseudo: passed
npx.cmd playwright ... -g "image-plane policy": 1 passed
npm.cmd run ci: passed, Playwright 6 passed
python benchmarks/spec_like_benchmark.py --profile smoke --json: passed
```

補足:

- `npm.cmd run ci` は一度、image-plane policy E2Eのpreset切替直後のselect待ち不足で失敗した。
- `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts` にpreset切替完了待ちを追加し、該当E2Eと全CIを再実行して通過を確認した。
- Viteの `"use client" directive ignored` 警告は依存パッケージ由来で、ビルドは成功。
- Python pytestのStarletteDeprecationWarningは既知警告で、テストは成功。

## Push

指示書どおり、pushは行っていない。

G5完了後は人間の最終確認待ち。
