# R71 Analysis Run Chartsタイムアウト調査・性能回帰テスト

## 完了状態

Done with corrected premise。R70で報告された製品タイムアウトは検証スクリプトの誤検知であり、製品コードの性能修正は行っていない。代わりに、同種の誤検知と将来の性能回帰を防ぐ実API E2Eを通常CIへ追加した。

実装根拠コミットは`aa3c527`（`test(ui): guard Run Charts performance (R71 task 2)`）。作業1の原因調査コミットは`c2fd489`。

## 原因と訂正

R70の300秒/180秒タイムアウトは、存在しないプリセット表示名をPlaywrightで指定し、例外後にbrowserをcloseしなかったことが原因だった。

- P007正名: `P007 Fast Positive-Negative Meniscus Pair 50mm Demo`
- P009正名: `P009 N-BK7 Aspheric Singlet 50mm Demo`

正しい実UI計測ではP007が`1078 ms`、P009が`582 ms`で、30秒目標を大幅に下回った。Run Chartsは7 endpointを`Promise.all`で並列実行済みであり、既定条件は`9 rays / grid / paraxial`。spot endpointと`full` aimingはRun Charts既定処理に含まれない。

詳細は[作業1報告](2026-07-13_r71_task1_run_charts_root_cause.md)を参照。

## 追加した回帰テスト

`apps/workbench-ui/tests/e2e/run-charts-performance.spec.ts`を追加した。

- preset catalogを一次情報としてP007/P009の表示名を組み立て、実optionの全文と照合する。
- 実APIの7 endpointがすべてHTTP成功することを確認する。
- Run Charts開始から結果表示までを計測し、`30000 ms`超過時に`assertRunChartsWithinBudget()`が明示的に失敗する。
- `30001 ms`を与えるguardテストでfailure-pathを固定した。
- chart DOMが`9 SVG`かつ非空であることを確認する。
- Playwrightの`page` fixtureにbrowser/context lifecycleを委譲する。fixtureはassertion失敗・timeoutを含めて確実に解放するため、手動browser起動とclose漏れを発生させない。
- performance test全体のtimeoutは`45000 ms`、Run Charts budgetは`30000 ms`として分離した。

## CI組み込み

- `.github/workflows/ci.yml`のUI jobにPython 3.12と`.[api]`のinstallを追加。
- UI CI前に`uvicorn`を起動し、`/v1/health`成功を最大30秒待つ。
- 新specは既存`npm run ui:e2e`に自動包含されるため、通常の`npm run ci`およびGitHub Actions UI jobで常時実行される。
- Playwright test serverを、API CORSで既に許可済みの`127.0.0.1:5174`へ変更した。製品APIのCORS設定は変更していない。

## テスト結果

- 新規spec単体: `3 passed (5.4s)`
  - P007: test duration約`1.5s`
  - P009: test duration約`1.6s`
  - over-budget guard: `3ms`
- 全UI CI: `36 passed (49.7s)`
- `npm run ui:build`: success
- `i18n:check ok (214 keys)`
- `i18n:coverage ok`
- `i18n:test ok`
- `svg-export-readback ok`
- `chart-theme:test ok`

初回実行ではテスト用Vite port `5177`がAPI CORS許可外のためRun Charts buttonがdisabledとなり、30秒で明示失敗した。テスト基盤を許可済み`5174`へ合わせた後、上記結果でグリーンになった。これにより30秒超過時の実環境failureも確認した。

## 実行プロセス

実装コミット`aa3c527`でAPI/UIを再起動した。完了報告作成直前に以下を確認済み。

- `HEAD`: `aa3c527`
- `GET /v1/meta build_info.git_commit`: `aa3c527`
- UI `http://127.0.0.1:5173/`: HTTP 200
- `build_info.git_dirty=true`は、R71指示書および他の未追跡active指示書が存在するため。

本タスクでは`App.tsx`、光学エンジン、正本仕様を変更していない。R71注意事項に列挙された他の収差・MTF機能には着手していない。
