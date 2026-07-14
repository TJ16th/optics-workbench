# R93 作業2 J3統合・ベンチマーク 中間実施記録

## 状態

- R93全体: **Partial**
- 作業1: 完了（`5fd9f815c40f44e9cc6551252aa0aad445d5a34a`）
- 作業2: 完了
- 作業3（J5運用固め）: 未着手
- R94: 未着手

本書はR93全体の完了報告ではない。指示書の「作業1〜3は1つずつ完了報告する」に従った作業2の中間実施記録であり、R93指示書は `doc/work_orders/active/` に保持する。

## 実装内容

- Jacobianのforward差分ではplus candidate群、central差分ではplus/minus candidate群をcandidate軸traceへ統合した。
- candidate workerが同じtrace地点へ到達した時点でray bundleを集約し、`_trace_raw_candidates()`で一括処理する `CandidateTraceCoordinator` を追加した。
- 制約違反candidateは事前検証でbatch対象外とし、既存の構造化violationを返す。
- topology・surface ID順・material ID順が不一致の場合は、作業1で実装した独立 `_trace_raw()` fallbackを維持する。
- `warm_refinement=False` のJ2 oracleは独立評価のまま維持した。
- Jacobian metadataへ `candidate_batch_trace_calls` と `candidate_batch_fallback_calls` を追加した。

## 実装根拠

- 機能コミット: `30ed59c436ec56531cf22eee6010da3eecf7d2a3`
- 主な回帰テスト: `tests/test_r91_jacobian.py`
- Goldenテスト: `tests/golden/test_r93_candidate_trace_kernel.py`
- ベンチスクリプト: `benchmarks/r93_jacobian_benchmark.py`
- 結果JSON: `bench_results/20260715_000148_r93_jacobian.json`

検証結果:

```text
python -m pytest -q tests/test_r91_jacobian.py tests/golden/test_r93_candidate_trace_kernel.py
22 passed, 1 warning in 1.91s

python -m pytest -q
188 passed, 1 skipped, 1 warning in 17.46s
```

既存のJ2/J3精度budget、境界fallback、収束次数、同一requestのbit-identical性は上記テストで維持されている。

## 10反復ベンチマーク

R83/R91と同じ `ray_fan_error + longitudinal_aberration`、1 field、1 wavelength、9 rays、`full exact` aiming、forward差分で測定した。P002/P007/P012は1変数、P011は1/5/10/20変数である。

| Preset | 変数 | J4 median ms | min ms | max ms | stddev ms | J2/J4 | J4/(1.25×cold) | 判定 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| P002 | 1 | 14.746 | 13.109 | 19.633 | 1.846 | 0.847x | 1.899x | 未達 |
| P007 | 1 | 82.692 | 74.357 | 96.932 | 7.775 | 1.001x | 1.675x | 未達 |
| P012 | 1 | 98.539 | 94.271 | 107.985 | 4.659 | 1.093x | 1.305x | 未達 |
| P011 | 1 | 109.122 | 101.861 | 131.030 | 7.770 | 1.094x | 1.473x | 未達 |
| P011 | 5 | 491.917 | 442.304 | 530.902 | 28.580 | 0.784x | 6.641x | 未達 |
| P011 | 10 | 1021.979 | 865.044 | 1176.638 | 96.383 | 0.678x | 13.796x | 未達 |
| P011 | 20 | 1395.172 | 1285.084 | 1568.965 | 97.093 | 0.921x | 18.834x | 未達 |

`J2/J4` は1より大きいほどJ4が高速である。全7条件でR83の保守的目標 `1.25×cold` を達成しなかった。1変数ではP012/P011で約1.09xのJ2比改善が見られたが、P011 5/10/20変数ではJ2より遅い。

## Profiling結果

最大規模の未達条件P011・20変数をcProfileで測定した。支配要因は次のとおりだった。

- `full exact` aimingの `_aim_origins_for_field_wavelength()` / `_exact_aim_origins()` / `_aim_origin_to_stop()`
- candidate workerのthread join・condition待ち
- 各candidate評価で自動付加される `_ray_loss_operands()` の追加trace
- 作業1カーネルがdense candidate配列を保持する一方、surface演算自体はcandidateごとのhelper呼び出しであり、GIL下のthread並行化で相殺できない

指示書に従い、この時点では追加最適化を行っていない。目標未達は作業3のcapability・仕様記述で正確に扱う必要がある。

## 実行環境

機能コミット後にAPI・UI開発サーバーを再起動した。

- `HEAD`: `30ed59c436ec56531cf22eee6010da3eecf7d2a3`
- `GET /v1/meta` の `build_info.git_commit`: `30ed59c`
- `build_info.git_dirty`: `true`（bench結果、active指示書、本中間記録を含むため）
- UI `http://127.0.0.1:5173/`: HTTP 200

## 次の区切り

次回はR93作業3としてcapabilities、artifact concurrency/TTL、`doc/engine_spec.md` 25.7節、full pytest・spec-like benchmark・UI E2Eを確認する。R93作業3完了前にR94へ進まない。
