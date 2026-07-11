# P0 タスク5 profiling metadata 実装報告

## 対象

- 指示書: `doc/work_orders/done/codex_p0_task5_kickoff.md`
- 親指示書: `doc/work_orders/active/codex_p0-7_performance_work_order.md`
- 実装対象: タスク5「profiling metadata」
- ベースコミット: `92008eb`（P0 タスク4完了時点）

## 実装内容

- `trace_forward(..., options={"profiling": True})` の `TraceResult.metadata["profiling"]` を拡張した。
  - `compile_ms`
  - `compile_cache_hit`
  - `aiming_ms`
  - `analysis_postprocessing_ms`
  - `cache_hits`
  - `cache_misses`
  - 既存互換の `ray_generation_and_aiming_ms` / `trace_ms` / `total_ms` / `total_rays` / aiming統計も維持
- `/v1/trace/forward` で `options.profiling: true` の場合、API側のcompile/cache lookup時間とHTTP総時間をmetadataへ合流するようにした。
  - `compile_ms`
  - `compile_cache_hit`
  - `engine_total_ms`
  - `http_total_ms`
- `/v1/analysis/spot` で `options.profiling: true` の場合、trace後の `analyze_spot` 時間を `analysis_postprocessing_ms` として返すようにした。
- `benchmarks/spec_like_benchmark.py` にFastAPI `TestClient` 経由のHTTP benchmark caseを追加した。
  - `http trace preview full aiming: 3 fields x 3 wavelengths x 9 rays`
  - detailsに `profiling_ms` と `compile_cache_hit` を保存する。
- `tests/test_engine_v2_1.py` にprofiling schemaの直接テストとHTTPテストを追加した。

## ベンチマーク結果

実行コマンド:

```bash
python benchmarks/spec_like_benchmark.py --profile smoke
```

保存ファイル:

- `bench_results/20260711_093554_92008eb.json`

direct vs HTTP:

| case | median_ms | p95_ms |
| --- | ---: | ---: |
| direct `trace preview full aiming: 3 fields x 3 wavelengths x 9 rays` | `29.035` | `48.881` |
| HTTP `http trace preview full aiming: 3 fields x 3 wavelengths x 9 rays` | `34.634` | `39.695` |

HTTP caseのprofiling内訳（最後の計測サンプル由来）:

| field | value |
| --- | ---: |
| `compile_ms` | `0.001200009137392044` |
| `validation_ms` | `0.08490000618621707` |
| `aiming_ms` | `22.63580000726506` |
| `trace_ms` | `3.9613000117242336` |
| `analysis_postprocessing_ms` | `0.0` |
| `total_ms` | `26.70280000893399` |
| `http_total_ms` | `26.941000018268824` |
| `compile_cache_hit` | `True` |

参考: 同一smokeでの主要ケース:

| case | median_ms |
| --- | ---: |
| `trace high-count off aiming: 1 field x 1 wavelength x 10000 rays` | `109.277` |
| `education preview direct paraxial: 3 fields x 1 wavelength x 25 rays` | `3.903` |
| `trace spot full aiming: 5 fields x 3 wavelengths x 21 rays` | `89.282` |
| `evaluate fast_design_score full aiming` | `83.283` |

## 検証

```bash
python -m py_compile optics_engine/tracing.py optics_engine/api/main.py benchmarks/spec_like_benchmark.py
python -m pytest tests/test_engine_v2_1.py::test_ray_fan_longitudinal_distortion_and_profiling_are_available tests/test_engine_v2_1.py::test_http_api_v2_1_smoke_with_artifact_fetch -q
python -m pytest -q
```

結果:

- 関連pytest: `2 passed, 1 warning`
- 全体pytest: `72 passed, 1 skipped, 1 warning`

warningは既存の `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`。

## 残件・制限

- API側のprofiling合流は `/v1/trace/forward` と `/v1/analysis/spot` を対象に実装した。PSF/MTF等のpostprocessing内訳は、必要になった時点で同じ形式に拡張できる。
- `compile_cache_hit` はHTTPで `system_id` / `system_hash` を使う場合は `True`、inline system payloadの場合はcompile前のsystem cache有無を示す。
