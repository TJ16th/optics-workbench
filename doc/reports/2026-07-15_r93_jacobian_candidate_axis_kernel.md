# R93 ヤコビアンcandidate軸trace kernel 完了報告

## 結論

R93の作業1〜3を完了した。Jacobian有限差分candidate群をcandidate軸traceへ統合し、同一topologyの適格条件、独立exact fallback、chunk決定論、capability、artifact並行運用、正本仕様を実装・検証した。

性能面では **Done with noted limitation** とする。R83の`1.25×cold`目標は10反復ベンチの全7条件で未達であり、candidate batchが高速化を保証するとは主張しない。

## 実装根拠

| 作業 | コミット | 内容 |
|---|---|---|
| 作業1 | `5fd9f815c40f44e9cc6551252aa0aad445d5a34a` | `_trace_raw_candidates()`、dense mask、chunk、Golden等価性、fallback |
| 作業2 | `30ed59c436ec56531cf22eee6010da3eecf7d2a3` | J3統合、candidate coordinator、J2 oracle温存、10反復ベンチ |
| 作業3 | `68b546524947d29d82edfb5337eeb783935bf6d1` | meta capability、artifact並行/TTLテスト、仕様25.7、最終検証 |

関連記録:

- `doc/reports/2026-07-14_r93_work1_candidate_axis_kernel.md`
- `doc/reports/2026-07-15_r93_work2_jacobian_batch_benchmark.md`
- `bench_results/20260715_000148_r93_jacobian.json`
- `bench_results/20260715_000607_222f6ad.json`

## Capabilityとfallback

`/v1/meta.capabilities.jacobian`へ以下を追加した。

- `candidate_axis_batch: true`
- `batch_requires_same_topology: true`
- `ineligible_candidate_fallback: independent_exact`

batch適格条件はsurface topology、surface ID順、material ID順、surfaceのmaterial参照順が全candidateで一致することである。不一致、ray shape不一致、store-path条件不一致では安全な独立経路を使う。

## 検証結果

```text
targeted pytest
24 passed, 1 warning in 2.32s

python -m pytest -q
189 passed, 1 skipped, 1 warning in 17.62s

npm run ci
build / i18n / SVG / chart tests: passed
Playwright: 40 passed (52.9s)
```

candidate batchの4並行呼び出しがbit-identicalであること、artifactの並行atomic writeとTTL expiryが維持されることを `tests/test_r91_jacobian.py` で直接確認した。Level 0・従来 `_trace_raw()` との等価性は `tests/golden/test_r93_candidate_trace_kernel.py` で固定している。

## 性能結果

10反復の正式結果は `bench_results/20260715_000148_r93_jacobian.json` に保存した。全7条件で`1.25×cold`目標は未達だった。J2比ではP012/P011の1変数条件で約`1.09x`改善したが、P011の5/10/20変数ではJ2より遅かった。

profileでは、`full exact` aiming、candidate workerの同期待ち、自動付加されるray-loss operandの追加trace、candidateごとのsurface helper処理が支配的だった。指示書に従い、作業2以降の追加最適化は行っていない。

spec-like smokeは `bench_results/20260715_000607_222f6ad.json` に保存した。前回 `20260714_132336_33457c8.json` 比ではpreview full `+24.2%`、high-count trace `+3.9%`、fast_design_score `+88.0%`だった。ただし両測定間にはR93以外の複数コミットが介在するため、R93単独の性能差とは断定しない。

## 実行環境確認

機能・仕様コミット後にAPI・UIプロセスを再起動した。

- `HEAD`: `68b546524947d29d82edfb5337eeb783935bf6d1`
- `GET /v1/meta` の `build_info.git_commit`: `68b5465`
- `GET /v1/meta` の `capabilities.jacobian.candidate_axis_batch`: `true`
- UI `http://127.0.0.1:5173/`: HTTP 200
- `build_info.git_dirty`: `true`（完了報告と未追跡active指示書を含むため）

R93指示書は本報告と同じコミットで `doc/work_orders/active/` から `doc/work_orders/done/` へ移動する。
