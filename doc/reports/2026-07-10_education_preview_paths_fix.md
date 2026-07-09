# /v1/education/preview paths 欠落確認と固定

日付: 2026-07-10

## 対象

`doc/work_orders/active/codex_education_preview_paths_fix.md` に基づき、`/v1/education/preview` のレスポンスに `paths` が含まれるかを確認し、Phase 3 のスライダー操作時に Layout View が実 trace path を描画することをテストで固定した。

## 確認結果

- 現在の `optics_engine/api/main.py` では、`/v1/education/preview` は `forward(...)` を呼び、`options.store_path=True` を強制している。
- そのため、前回の `fix(ui): render traced ray paths` で `/v1/trace/forward` の共有レスポンスに `paths` を追加した後は、`education/preview` にも `paths` が返る構造になっていた。
- 元の欠落は意図的な軽量化ではなく、`forward` レスポンスが `TraceResult.paths` を JSON に含めていなかったことによる共有レスポンスの実装漏れだった。
- 今回の見落とし原因は、前回完了条件の確認時に `/v1/trace/forward` を直接テストし、Phase 3 UI が実際に使う `/v1/education/preview` を横断テストしていなかったこと。

## 修正内容

- `tests/test_engine_v2_1.py`
  - P003 Achromat fixture を追加。
  - P002/P003 の両方で `/v1/education/preview` を直接呼び、レスポンスに `paths` が含まれることを検証。
  - P002 は `STOP -> S1 -> S2 -> IMG`、P003 は `STOP -> S1 -> S2 -> S3 -> IMG` の surface hit path を確認。
- `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - mock engine の `paths` を登録された system の surface ID に合わせて生成するように変更。
  - P002 の通常 preview で `path.ray-line` が描画され、旧 `line.ray-line` に戻らないことを確認。
  - P003 の focus slider drag preview 後にも、5点の surface path に基づく `path.ray-line` が描画されることを確認。
- `benchmarks/education_preview_paths_benchmark.py`
  - `/v1/education/preview` の paths 返却つき latency 測定スクリプトを追加。
- `bench_results/2026-07-10_education_preview_paths_latency.json`
  - P002/P003 preview paths の測定結果を追加。
- `AGENTS.md`
  - 同種レスポンス項目を持つ複数エンドポイントは横断確認し、直接テストで固定する旨を追記。

## レイテンシ結果

測定ファイル: `bench_results/2026-07-10_education_preview_paths_latency.json`

測定条件:

- `/v1/education/preview` via FastAPI TestClient
- 3 fields x 3 wavelengths x 5 rays = 45 rays
- `ray_aiming.mode=paraxial`
- `options.profiling=True`
- UI debounce は 70 ms として effective latency を算出

| Case | Median HTTP ms | P95 HTTP ms | Effective median ms | Paths |
| --- | ---: | ---: | ---: | --- |
| p002_run_preview_paths | 8.908 | 11.801 | 78.908 | 45 paths, `STOP/S1/S2/IMG` |
| p003_group_shift_drag_preview_paths | 12.755 | 17.227 | 82.755 | 45 paths, `STOP/S1/S2/S3/IMG` |
| p003_aperture_drag_preview_paths | 10.346 | 12.049 | 80.346 | 45 paths, `STOP/S1/S2/S3/IMG` |
| p003_decenter_tilt_drag_preview_paths | 10.889 | 12.147 | 80.889 | 45 paths, `STOP/S1/S2/S3/IMG` |

前回 P3-5 のローカルHTTP測定とは TestClient / HTTP サーバーの違いがあるため厳密な同条件比較ではないが、現在の paths 返却つき preview は中央値 8.9-12.8 ms、P95 11.8-17.3 ms に収まっており、70 ms debounce込みでも約 79-83 ms だった。Phase 3 の drag preview 用途では大きな悪化は見られない。

## テスト結果

- `python -m pytest tests/test_engine_v2_1.py -q`
  - 17 passed, 1 skipped, 1 warning
- `npm.cmd run ui:build`
  - passed
  - Vite の既存 warning あり: `"use client"` directive ignored, chunk size warning
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "trace path|P003 slider preview"`
  - 2 passed
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - 13 passed

## 状態

完了。`/v1/education/preview` は `paths` を返すことが直接APIテストで固定され、P002/P003 の Layout View は preview response の surface hit path に基づく折れ線を描画することが E2E で確認された。
