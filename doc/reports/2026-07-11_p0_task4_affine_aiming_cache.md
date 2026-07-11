# P0 タスク4 瞳アフィン近似とwarm startキャッシュ 実装報告

## 対象

- 指示書: `doc/work_orders/done/codex_p0_task4_kickoff.md`
- 親指示書: `doc/work_orders/active/codex_p0-7_performance_work_order.md`
- 実装対象: タスク4「瞳アフィン近似とwarm startキャッシュ」
- ベースコミット: `8ac9e61`（P0 タスク3完了時点）

## 実装内容

- `ray_aiming.mode: full` の既定strategyを `affine` とし、従来の全点Newtonは `ray_aiming.strategy: exact` で保持した。
- field×wavelengthごとに、中心・上下左右・対角方向の最大9点を厳密aimingし、絞り面target `(y, z)` からlaunch `(y, z)` へのアフィン写像を構築するようにした。
- 通常解析では、アフィン近似で生成したrayの絞り面到達残差を確認し、既定閾値（絞り半径の約0.25%）を超えたrayのみNewtonで追加補正するようにした。
- 教育previewでは `preview_mode` を渡し、追加補正を省略するようにした。
- プロセス内warm start cacheを追加した。キーは `system_hash + configuration_hash + field + wavelength + stop index + stop radius` で、configurationや絞り径変更時は別キーとして扱う。
- `TraceResult.metadata` に以下を追加した。
  - `ray_aiming_strategy`
  - `aiming_iterations_mean`
  - `aiming_cache_hits`
  - `aiming_cache_misses`
  - `affine_refined_count`
  - `affine_seed_count`
- `tests/golden/test_affine_aiming_cache.py` を追加し、affine/exact比較とwarm start cacheのhit/miss、iris radius変更時のcache missを固定した。

## 精度確認

追加テスト:

- `tests/golden/test_affine_aiming_cache.py`

テスト内の9-sample bundleでは、`strategy: exact` と既定 `affine` のセンサー座標差を `<= 2e-6 mm` で確認した。

追加の手元計測:

| 条件 | max_error_mm | mean_error_mm |
| --- | ---: | ---: |
| 14面spec-like / 3 fields / 3 wavelengths / 21 rays / affine vs exact | `0.021191871121117867` | `0.009380703180828882` |

この差はアフィン近似による意図した近似誤差であり、Level 0/Level 1の同一性テストとは別扱いにした。Level 0/Level 1のGolden等価性テストは継続して通過している。

## warm start確認

14面spec-like / 3 fields / 3 wavelengths / 21 rays / full aiming:

| 状態 | elapsed_ms | cache_hits | cache_misses | affine_seed_count | aiming_iterations_mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| cold | `163.569` | `0` | `9` | `81` | `1.253968253968254` |
| warm | `51.464` | `9` | `0` | `0` | `0.0` |

## ベンチマーク結果

実行コマンド:

```bash
python benchmarks/spec_like_benchmark.py --profile smoke
```

保存ファイル:

- `bench_results/20260711_092519_8ac9e61.json`

P0 タスク3結果（`bench_results/20260711_015541_85eea4a.json`）との比較:

| case | task3 median_ms | task4 median_ms | 比率 |
| --- | ---: | ---: | ---: |
| `trace preview full aiming: 3 fields x 3 wavelengths x 9 rays` | `139.745` | `24.494` | `5.70x` |
| `trace spot full aiming: 5 fields x 3 wavelengths x 21 rays` | `560.380` | `87.658` | `6.39x` |
| `relative illumination full aiming: 5 fields x 3 wavelengths, 15 deg outer fields` | `252.806` | `196.906` | `1.28x` |
| `evaluate fast_design_score full aiming` | `291.321` | `55.960` | `5.21x` |
| `trace high-count off aiming: 1 field x 1 wavelength x 10000 rays` | `98.387` | `98.140` | `1.00x` |
| `education preview direct paraxial: 3 fields x 1 wavelength x 25 rays` | `3.638` | `3.526` | `1.03x` |

追加の目標確認:

| 条件 | median_ms | p95_ms | 判定 |
| --- | ---: | ---: | --- |
| spot trace full aiming / 1 field × 3 wavelengths × 512 rays | `859.191` | `865.976` | 目標 `<=1000ms` Pass |
| spot trace full aiming / 3 fields × 3 wavelengths × 512 rays | `2719.435` | `2812.186` | 参考値。単field目標より重い条件 |
| evaluate fast_design_score full aiming / 3 fields × 3 wavelengths × 25 rays | `273.712` | `286.404` | 目標 `<=500ms` Pass |

P0 タスク3の努力目標だった14面1万本off aiming `<=50ms` は、本タスクの主対象ではないため未達のまま。最終smokeでは `98.140ms`。

## 検証

```bash
python -m py_compile optics_engine/tracing.py optics_engine/api/main.py tests/golden/test_affine_aiming_cache.py
python -m pytest tests/golden -q
python -m pytest -q
```

結果:

- `tests/golden`: `9 passed`
- 全体pytest: `72 passed, 1 skipped, 1 warning`

## 残件・制限

- アフィン近似は厳密aimingと完全一致しない。より厳密な中間点精度が必要な用途では `ray_aiming.strategy: exact` を使う。
- 3 fields × 3 wavelengths × 512 rays のfull aimingは約2.7秒であり、単field目標より重い条件では1秒を超える。
- 今回は純NumPy/Python実装の範囲で完了した。非球面NewtonのNumba化などは後続タスクの判断対象。
