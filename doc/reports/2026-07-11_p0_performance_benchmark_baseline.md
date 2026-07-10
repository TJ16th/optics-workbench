# P0 性能計測基盤修正と初回ベンチ 完了報告

## 概要

`doc/work_orders/active/codex_p0-7_performance_work_order.md` のタスク0のみを実施した。
同指示書はタスク1-7を含むため、今回は `active/` に残し、次タスクへは進めていない。

## 修正内容

- `benchmarks/spec_like_benchmark.py` をタスク0仕様に合わせて更新した。
  - repeatを5回にし、warmup 1回を統計から除外するようにした。
  - median / p95 / mean / min / max を出力するようにした。
  - すべてのケースに field角、field数、波長、総ray数、面数、surface-ray数、ray aiming mode を記録するようにした。
  - median基準の `per_ray_us_median` と `per_surface_ray_us_median` を自動計算するようにした。
  - 同一14面系で `ray_aiming: full` / `paraxial` / `off` の3条件を比較するケースを追加した。
  - relative illuminationケースの外側fieldを15 degにし、`cos^4(theta)` との比較値を出力するようにした。
  - 実行ごとに `bench_results/{timestamp}_{git_short}.json` へ履歴を保存するようにした。
- `benchmarks/report.py` を追加した。
  - `bench_results/*.json` を読み、ケース別の時系列と表を含む静的HTMLを生成する。
  - matplotlibが利用できる場合はbase64 PNGグラフを埋め込み、利用できない場合もHTML生成自体は継続する。
- 初回履歴として `bench_results/20260711_010244_4abf145.json` を追加した。

## ベンチ結果

実行コマンド:

```bash
python benchmarks/spec_like_benchmark.py --profile smoke
```

共通条件:

- 14 surfaces / 12 refractive surfaces / 2 aspheres
- 3 wavelengths: 486.13 / 587.56 / 656.27 nm
- profile: `smoke`
- warmups: 1
- repeats: 5

主な結果:

| case | median ms | p95 ms | us/ray | us/surface-ray |
|---|---:|---:|---:|---:|
| trace preview full aiming | 818.740 | 830.075 | 10107.902 | 721.993 |
| trace preview paraxial aiming | 4.884 | 5.274 | 60.294 | 4.307 |
| trace preview off aiming | 4.880 | 6.347 | 60.249 | 4.304 |
| trace spot full aiming | 3257.043 | 3350.699 | 10339.819 | 738.559 |
| geometric PSF from 64-ray trace | 0.279 | 0.296 | 4.358 | 0.311 |
| geometric MTF from 64-ray trace | 0.133 | 0.164 | 2.086 | 0.149 |
| relative illumination full aiming | 1414.282 | 1446.737 | 10476.161 | 748.297 |
| evaluate fast_design_score full aiming | 1628.536 | 1659.252 | 20105.381 | 1436.099 |

## 考察

- `paraxial` / `off` のpreview traceは約4.88 msで、81 rays換算では約60 us/ray。
- `full` aimingはpreviewでも約818.74 ms、約10.1 ms/rayで、タスク指示書の前提どおり現時点の主ボトルネックはray aimingである。
- `trace spot full aiming` と `relative illumination full aiming` も約10 ms/ray水準で、面交差そのものよりも aiming 反復の増幅が支配的に見える。
- relative illuminationの15 deg外側fieldは `cos^4(theta)=0.8705127018922199`、測定RIも同値で、今回のsynthetic系では周辺遮光なしの理論値どおりだった。
- schema 2のspec-likeベンチとしては初回履歴のため、前回比は未計算。

## 確認結果

- `python -m py_compile benchmarks/spec_like_benchmark.py benchmarks/report.py`: Passed
- `python benchmarks/spec_like_benchmark.py --profile smoke`: Passed、`bench_results/20260711_010244_4abf145.json` を生成
- `python benchmarks/report.py`: Passed、`bench_results/report.html` を生成
- `python -m pytest -q`: `63 passed, 1 skipped`

## 備考

ベンチJSONの `git_dirty` は `true`。これはベンチ実行時点で本タスクの未コミット変更が作業ツリーに存在していたため。
本タスクはベンチ/ドキュメント変更のみであり、エンジンAPI・UIプロセスの再起動確認は対象外。
