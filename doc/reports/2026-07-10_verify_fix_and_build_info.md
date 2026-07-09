# 修正内容の整合確認と build_info 導入

日付: 2026-07-10

## 対象

`doc/work_orders/active/codex_verify_fix_and_build_info.md` に基づき、`/v1/education/preview` の `paths` 報告と実ブラウザ確認の食い違い原因を確認し、`/v1/meta` に実行中エンジン識別用の `build_info` を追加した。

## 食い違い原因

確認コマンド:

- `git log --oneline -- optics_engine/api/main.py`
- `git show --stat --name-only 61ca956`
- `git show --stat --name-only 7924eec`

確認結果:

- `optics_engine/api/main.py` を変更した最新コミットは `7924eec fix(ui): render traced ray paths`。
- `7924eec` で `/v1/trace/forward` の共有レスポンスに `paths` が追加された。
- `61ca956 fix(ui): verify education preview paths` では `optics_engine/api/main.py` は変更されていない。内容はテスト、ベンチ、AGENTS、報告書の追加だった。
- 現在の `education/preview` は `forward(...)` を呼び、`store_path=True` を付けているため、`7924eec` 以降のプロセスであれば `paths` が返る構造。

結論:

- 前回報告の「`education/preview` にも共有レスポンス経由で `paths` が返る構造」は、現在コードに対しては正しい。
- 人間がNetworkタブで `paths` なしを確認した時点では、`7924eec` 以前の古いエンジンプロセスが起動したままだった可能性が高い。
- 直接の問題は実装経路の誤認ではなく、コード変更後に実行中プロセスが再起動されているかを識別する手段が無かったこと。

## 修正内容

- `optics_engine/metadata.py`
  - プロセス起動時に `BUILD_INFO` を作成。
  - `git rev-parse --short HEAD` で `git_commit` を取得。
  - `git status --porcelain` で `git_dirty` を取得。
  - 起動時刻 `started_at` をISO8601で保存。
  - `/v1/meta` の `meta_payload()` に `build_info` を追加。
- `tests/test_engine_v2_3.py`
  - `build_info.git_commit` が現在のHEAD短縮ハッシュと一致することを検証。
  - `git_dirty` がboolean、`started_at` が存在することを検証。
- `apps/workbench-ui/src/domain/types.ts`
  - `EngineMeta.build_info` 型を追加。
- `apps/workbench-ui/src/ui/App.tsx`
  - Debugタブに接続先エンジンの `Build Info` パネルを追加。
  - `git_commit` / `git_dirty` / `started_at` を表示。
- `apps/workbench-ui/src/i18n/locales/{ja,en}/common.json`
  - Debug表示用のi18nキーを追加。
- `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - mock `/v1/meta` に `build_info` を追加。
  - Debugタブにbuild infoが表示されるE2Eを追加。
- `AGENTS.md`
  - 実環境確認時は `/v1/meta` の `build_info.git_commit` と報告コミットを照合し、不一致ならプロセス再起動が必要である旨を追記。
  - 起動中プロセスにはコード変更が反映されないため、Network確認前に必要に応じて再起動する旨を追記。

## 直接確認

`/v1/meta` を FastAPI TestClient 経由で確認した。

結果:

- `build_info.git_commit`: `61ca956`
- `HEAD`: `61ca956`
- `build_info.git_dirty`: `true`

この時点では未コミットの今回差分があるため、`git_dirty=true` は期待通り。

## テスト結果

- `python -m pytest tests/test_engine_v2_3.py tests/test_engine_v2_1.py -q`
  - 23 passed, 1 skipped, 1 warning
- `npm.cmd run ui:build`
  - passed
  - Vite の既存 warning あり: `"use client"` directive ignored, chunk size warning
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "debug tab shows connected engine build info"`
  - 1 passed
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - 14 passed
- `npm.cmd run i18n:coverage`
  - passed
- `npm.cmd run i18n:check`
  - failed
  - 失敗理由は既存の unused key: `surfaceTable:surfaceTable.groups.issue_error` / `issue_warning` / `duplicate_id` / `unknown_surface` / `invalid_range` / `overlap`。今回追加したDebugキーではない。

## 状態

`/v1/meta` は `build_info` を返すようになり、UI Debugタブでも接続先エンジンのcommitを確認できる。今後、ブラウザで修正反映を確認する際は、まず `build_info.git_commit` と報告コミットを照合する。
