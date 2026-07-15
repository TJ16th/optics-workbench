# R126 解析進捗UI・非ブロッキング化 実装報告

- 着手前見積もり: 中規模（計測、複数endpoint進捗、キャンセル、E2Eを含め3〜5時間）
- 状態: **Done with noted limitation**
- 機能コミット: `9b383aa` (`feat(ui): add analysis progress and cancellation (R126)`)
- 対象: Run ChartsのUI側MVP
- エンジン／サーバーAPI変更: なし

## 原因調査と計測

Run Chartsは`runChartAnalyses`から固定7リクエスト（ray fan Y/Z、longitudinal、distortion、field curvature、mean-sphere image surface、relative illumination）と、field数分のMTFリクエストを`Promise.all`で送っていた。HTTP待ちは非同期だが、従来は全リクエスト完了までUIへ途中経過が返らず、完了後に全chart dataを同時反映していた。

したがって、体感上の「フリーズ」は次の組合せだった。

1. 複数の長いHTTP待ちに途中表示がない。
2. 全結果を同時にstateへ設定し、SVG chartをまとめてre-renderする。
3. 単一endpoint内部のray batch進捗を同期HTTP契約から取得できない。

遅延付き10リクエストを使うE2Eで、実装後の解析中System遷移は単独実行`148 ms`、全CI実行`184 ms`だった。Long Tasks APIで観測した最大long taskは単独実行`168 ms`、全CI実行`149 ms`。ナビゲーション受け入れ条件は`750 ms`未満として固定した。

## 実装内容

- `runChartAnalyses`へ`AbortSignal`と`onProgress(completed, total)`を追加した。
- 分母は`7 + max(1, field数)`とし、各HTTP requestのsettle時に完了数を単調増加させる。
- Analysis上部に「N件中M件完了」と全体経過秒数を表示する。
- R117 workspaceの各panelへCarbon `InlineLoading`と当該runの経過秒数を表示する。
- loading領域は`min-height: 220px`で固定し、開始／終了時のpanel寸法変化を抑えた。
- Cancelボタンから`AbortController.abort()`を呼び、残リクエストを中断する。
- キャンセルは構造化`analysis_cancelled`（`completed`／`total` params）として保持する。
- chart結果反映をReact transitionへ入れ、ナビゲーション等の操作を優先する。
- System／Preview／Compare／Debugのナビゲーションは解析中も無効化しない。

## 真のパーセント表示に関する提案

今回の`M/N`はendpoint完了数であり、単一MTF endpointが何%進んだかは示さない。真の進捗にはエンジン側job契約が必要である。

長時間候補:

- `/v1/analysis/mtf`
- `/v1/analysis/white-mtf`
- `/v1/analysis/mtf/through-focus`
- PSF系endpoint
- 大量fieldの`/v1/analysis/relative-illumination`
- 最適化系endpoint

進捗粒度候補はray batch、field／wavelength、focus sweep step、optimizer iterationである。job状態には`phase`、単調増加する`completed`／`total`、cancel状態、最終artifact URIを含め、polling型HTTP job APIとWebSocketを比較する。再接続後の状態取得と既存artifact TTLとの関連付けも必要になる。

この内容を`doc/reports/issues_backlog.md`の「長時間解析向けjob/WebSocketセッションを検討する [issue: #10]」へ追記した。

## テスト結果

- 対象E2E: `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - `R126 keeps navigation responsive while chart panels report progress and cancellation`
- R126単独: `1 passed (4.4s)`
- `npm run ci`: `62 passed (1.6m)`、`i18n:check ok (323 keys)`、build／coverage／unit／SVG／chart test成功
- `npm run ui:build:pseudo`: 成功

E2Eで固定した内容:

- 4 panelすべてにloadingが表示される。
- 完了カウンタが0から1以上へ進む。
- 実行中にSystemへ遷移し、Analysisへ戻れる。
- 完了後にchartが表示される。
- 2回目のrunをCancelし、loadingとCancel操作が終了する。

## 稼働確認

機能コミット`9b383aa`の直後にAPI／UIを再起動して確認した。

- `GET /v1/meta`: `build_info.git_commit = 9b383aa`
- `git rev-parse --short HEAD`: `9b383aa`
- UI `http://127.0.0.1:5173/`: HTTP 200
- API `127.0.0.1:8000`、UI `127.0.0.1:5173`各1 listener
- `build_info.git_dirty = true`はR126報告書、スクリーンショット、active指示書等の文書差分による

## スクリーンショット

1. [Run Charts開始直後のpanel loadingと0/10表示](screenshots/2026-07-15_r126_analysis_progress_ui_1.png)
2. [1/10へ進んだカウンタと経過時間](screenshots/2026-07-15_r126_analysis_progress_ui_2.png)

## 制限

- 表示する進捗はendpoint完了数であり、単一endpoint内部の真のパーセントではない。
- AbortControllerはHTTP client側中断であり、サーバー側計算停止を保証するjob cancel契約ではない。
- React transitionで結果描画を低優先度化したが、SVG大量描画のlong taskを完全には除去していない。
