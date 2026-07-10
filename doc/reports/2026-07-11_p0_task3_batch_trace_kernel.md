# P0 タスク3 バッチ配列トレースカーネル 実装報告

## 対象

- 指示書: `doc/work_orders/done/codex_p0_task3_kickoff.md`
- 親指示書: `doc/work_orders/active/codex_p0-7_performance_work_order.md`
- 実装対象: タスク3「バッチ配列トレースカーネル」
- ベースコミット: `85eea4a`（P0 タスク2完了時点）

## 実装内容

- `optics_engine/tracing.py` のLevel 1 `_trace_raw` を、面ごとの全ray処理で有効rayだけのcompact配列を使う形に整理した。
- 波長ごとの媒質屈折率取得を `_material_indices_for_wavelengths` に集約し、同一波長値の繰り返し計算を抑制した。
- 既存のper-ray参照経路を削除せず、`optics_engine/reference/` にLevel 0参照実装として移設・保持した。
- Golden Test用の2系統（achromat doublet / cassegrain）を `tests/golden/systems.py` に共通化した。
- `tests/golden/test_trace_kernel_equivalence.py` を追加し、Level 0参照経路とLevel 1 batch経路のセンサー到達座標を比較するGolden等価性テストを追加した。
- `benchmarks/spec_like_benchmark.py` のsmoke profileに、P0タスク3の判定対象である以下2ケースを追加した。
  - `trace high-count off aiming: 1 field x 1 wavelength x 10000 rays`
  - `education preview direct paraxial: 3 fields x 1 wavelength x 25 rays`

## 等価性テスト結果

追加テスト:

- `tests/golden/test_trace_kernel_equivalence.py`

最大誤差:

| system | rays | arrived | tolerance | max_error_mm | 判定 |
| --- | ---: | ---: | ---: | ---: | --- |
| `achromat_doublet_100mm` | 54 | 54 | `1e-9 mm` | `0` | Pass |
| `cassegrain_v2_3` | 9 | 9 | `1e-9 mm` | `0` | Pass |
| `spec_like_asphere_14_surface` | 126 | 126 | `1e-8 mm` | `4.6221693139614217e-11` | Pass |

## ベンチマーク結果

実行コマンド:

```bash
python benchmarks/spec_like_benchmark.py --profile smoke
```

保存ファイル:

- `bench_results/20260711_015541_85eea4a.json`

主要結果:

| case | median_ms | p95_ms | 判定 |
| --- | ---: | ---: | --- |
| `trace high-count off aiming: 1 field x 1 wavelength x 10000 rays` | `98.387` | `119.414` | 必須目標 `<=200ms` Pass / 努力目標 `<=50ms` 未達 |
| `education preview direct paraxial: 3 fields x 1 wavelength x 25 rays` | `3.638` | `4.187` | 目標 `<=100ms` Pass |

参考として、タスク2完了直後の手元計測では14面10k offが約 `236.537ms`、教育preview directが約 `6.048ms` だった。今回の実装後はそれぞれ `98.387ms`、`3.638ms` まで改善した。

## 検証

```bash
python -m py_compile optics_engine/tracing.py optics_engine/reference/tracing.py benchmarks/spec_like_benchmark.py
python -m pytest tests/golden -q
python -m pytest -q
```

結果:

- `tests/golden`: `7 passed`
- 全体pytest: `70 passed, 1 skipped, 1 warning`

## 残件・制限

- full ray aimingのNewton反復は、タスク2で導入した軽量residual経路を継続使用している。本タスクでは全field×wavelength chief rayを同時に解く専用の完全vector Newton実装までは追加していない。
- 14面10k offの必須目標 `<=200ms` は達成したが、努力目標 `<=50ms` は未達。Numba等を使う追加高速化は親指示書の後続タスクに委ねる。
