# 光学エンジン Phase 1-8 実装状況・仕様差分・ベンチマークまとめ

## 1. 概要

本リポジトリでは、`doc/optical_engine_spec_v2.md` のMVP実装順序に沿って、Phase 1からPhase 8までの基礎実装を追加した。

現在の実装は、商用光学設計ソフト相当の厳密性を目指した完成版ではなく、仕様書の各Phaseに対応する動作可能なMVPである。単体・機能テストはPhase別に整備済みで、現時点の全テストは通過している。

検証コマンド:

```powershell
<python> -m pytest -q
```

検証結果:

```text
36 passed in 0.49s
```

構文確認:

```powershell
$files = Get-ChildItem -Recurse -File optics_engine -Filter *.py | ForEach-Object { $_.FullName }
<python> -m py_compile @files
```

結果: 成功。

## 2. 実装済み範囲

| Phase | 状況 | 主な実装 |
|---|---|---|
| Phase 1 | 完了 | `+X` 光軸、3D ray、平面・球面、屈折、反射、センサー交差、有効径判定、近軸 y-nu 計算 |
| Phase 2 | 完了 | `circle` / `annulus` 絞り、薄レンズ、ray aiming、pupil sampling、spot、CompiledSystemキャッシュ、最小HTTP API |
| Phase 3 | 完了 | Sellmeier材料、波長別屈折率、偶数次非球面交点・法線、軸上/倍率色収差解析 |
| Phase 4 | 完了 | 群定義、`zoom_positions`、群X移動、decenter/shift、群移動バリデーション |
| Phase 5 | 完了 | チルト、ローカル回転座標、±field helper、像面湾曲、M/S像面のRMS探索 |
| Phase 6 | 完了 | 幾何PSF、Encircled Energy、幾何MTF、白色PSF/MTFの基礎、Relative Illumination |
| Phase 7 | 完了 | `evaluate_system`、`evaluate_batch`、merit/preset、candidate variables、infeasible即時棄却 |
| Phase 8 | 完了 | `afocal` / `eye_reference`、角度spot、射出瞳、アイボックス、角度MTF、双眼アライメント、望遠鏡サマリ |

主要モジュール:

- `optics_engine/core.py`
- `optics_engine/tracing.py`
- `optics_engine/paraxial.py`
- `optics_engine/chromatic.py`
- `optics_engine/configuration.py`
- `optics_engine/field_curvature.py`
- `optics_engine/psf_mtf.py`
- `optics_engine/optimization.py`
- `optics_engine/visual.py`
- `optics_engine/api/main.py`

Phase別テスト:

- `tests/test_core_acceptance.py`
- `tests/test_phase3_material_asphere_chromatic.py`
- `tests/test_phase4_groups_configuration.py`
- `tests/test_phase5_tilt_asymmetric_ms.py`
- `tests/test_phase6_psf_mtf_illumination.py`
- `tests/test_phase7_optimization_evaluate.py`
- `tests/test_phase8_afocal_visual.py`

## 3. 仕様書からの乖離・簡略化

現状はPhase 1-8のMVPとして動作するが、仕様書v2の完全実装とは以下の乖離がある。

### 3.1 実装構成

- 仕様書28章の細かいモジュール階層は、そのままのディレクトリ構造では実装していない。
- 現状は少数のモジュールへ機能を集約している。
- `axis_convention.py` 相当の外部Z軸光軸系とのインポート/エクスポート変換は未実装。

### 3.2 APIとキャッシュ

- `CompiledSystem` のインメモリキャッシュは実装済み。
- `/v1/systems/register` は `system_hash` を返すが、APIエンドポイント側で `system_id` のみを受けて登録済みsystemを参照する本格運用形にはなっていない。
- 常駐ワーカー、共有メモリ、プロセス間キャッシュは未実装。

### 3.3 Ray Aiming

- `ray_aiming: full` は実装済み。
- ただし仕様16.3節の「主光線 + 絞り縁4点/8点から瞳アフィン写像を作り、中間点を補間する」方式は未実装。
- 現状は瞳サンプルごとにNewton反復と途中トレースを行うため、仕様寄りの複数field/波長/非球面系では大きなボトルネックになっている。
- warm start、field別/波長別aiming解キャッシュも未実装。

### 3.4 非球面

- 偶数次非球面のsag、交点Newton反復、法線計算は実装済み。
- 法線計算の一部は数値微分ベースで、最適化済みの解析微分・Numba化は未実装。
- 収束失敗ログやデバッグ出力はまだ限定的。

### 3.5 近軸・M/S像面

- 近軸 y-nu トレースは実装済み。
- M/S像面はRMS探索ベースの基礎実装。
- 仕様21.2節のCoddington方程式の本格実装、およびCoddington方式とRMS探索方式の厳密な相互検証は未実装。

### 3.6 PSF / MTF

- 現状は幾何PSFと幾何MTF。
- 回折PSF、波面収差、瞳関数FFT、白色回折PSF/MTFは未実装。
- 白色PSF/MTFは、波長別幾何トレースを重み付き結合する基礎実装。

### 3.7 Relative Illumination

- 現状は通過率と `cos^4` 因子を組み合わせる簡易モデル。
- 仕様16.5節の等立体角サンプリングと厳密な放射量論的重み付けは完全実装ではない。

### 3.8 Phase 7最適化

- `evaluate` / `evaluate-batch`、merit preset、candidate variables、infeasible即時棄却は実装済み。
- 変数注入は `surface_id_radius_mm`、`surface_id_thickness_after_mm`、`surface_id_focal_length_mm`、`iris_radius_mm` などの限定的なキーに対応。
- 粗密2段階評価、常駐ワーカー、詳細なprofiling metadataは未実装。

### 3.9 Phase 8視覚系

- `afocal`、`eye_reference`、角度spot、射出瞳、アイボックス、角度MTF、双眼アライメント、望遠鏡サマリは実装済み。
- ポロプリズム/ダハプリズム、像の正立化、実眼モデル、双眼鏡の詳細な左右チャンネルモデルは未実装。
- ディオプター評価は角度RMSからの簡易換算。

### 3.10 Golden Test

- 仕様30.5節のGolden Testは未実装。
- 教科書ダブレット、特許ダブルガウス、カセグレン、外部OSS突き合わせ、Level 0参照実装との比較は今後の課題。

## 4. ベンチマークテスト概要

仕様に近い負荷を見るため、以下のベンチマークを追加した。

ファイル:

- `benchmarks/spec_like_benchmark.py`

実行例:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
<python> benchmarks/spec_like_benchmark.py --profile smoke
```

ベンチ対象の合成光学系:

| 項目 | 内容 |
|---|---|
| surfaces | 14 |
| refractive surfaces | 12 |
| aspheres | 2 |
| materials | `AIR`, `N-BK7`, `N-F2` |
| material model | Sellmeier |
| aperture stop | 内部stop |
| wavelengths | 486.13 nm, 587.56 nm, 656.27 nm |
| ray aiming | `full` |
| fields | 3〜5 fields |

プロファイル:

| profile | 用途 | 設定 |
|---|---|---|
| `smoke` | 短めの動作確認 | preview 9 rays、spot 21 rays、analysis 64 rays、repeat 2 |
| `default` | 普段の性能確認 | preview 25 rays、spot 64 rays、analysis 512 rays、repeat 3 |
| `detail` | 重い確認 | preview 25 rays、spot 512 rays、analysis 2048 rays、repeat 1 |

## 5. ベンチマーク結果

実測環境:

- Python: Codex同梱Python
- 呼び出し: ライブラリ直呼び
- HTTPサーバー経由ではない
- profile: `smoke`

実測結果:

| ケース | median | mean | details |
|---|---:|---:|---|
| trace preview full aiming: 3 fields × 3 wavelengths × 9 rays | 843.374 ms | 843.374 ms | 81 rays, arrived 81, aiming_failed 0, max_iter 3 |
| trace spot full aiming: 5 fields × 3 wavelengths × 21 rays | 3351.669 ms | 3351.669 ms | 315 rays, arrived 315, aiming_failed 0, max_iter 3 |
| geometric PSF from 64-ray full-aim trace | 0.278 ms | 0.278 ms | total_energy 64, grid 32×32 |
| geometric MTF from 64-ray full-aim trace | 0.131 ms | 0.131 ms | 4 frequency points |
| relative illumination full aiming: 5 fields × 3 wavelengths | 1358.639 ms | 1358.639 ms | 5 rows, min RI 0.984865 |
| evaluate fast_design_score full aiming | 1623.608 ms | 1623.608 ms | status ok, score 8.4815 |

## 6. ベンチ結果の解釈

軽量な薄レンズ系では、previewやevaluateはミリ秒級で動作していた。一方で、仕様に近い「10〜20面、非球面あり、複数field/波長、ray aiming full」では、速度の支配要因が明確に `full ray aiming` へ移った。

特に現状の `full` aiming は、各瞳サンプルに対して以下を行う。

1. stop面まで途中トレース
2. 残差計算
3. 数値ヤコビアン計算
4. Newton更新
5. 収束後に全系トレース

そのため、サンプル数、field数、波長数にほぼ比例して重くなる。

仕様27章の性能目標と比較すると、軽量モデルでは十分速いが、仕様寄りベンチの `full ray aiming` では未達である。

| 仕様目標 | 現状の仕様寄りベンチ |
|---|---|
| 教育preview 50〜100 ms | smokeでも約843 ms |
| Spot簡易解析 1秒以内 | 315 raysで約3.35秒 |
| 最適化粗評価 100〜500 ms | full aiming evaluateで約1.62秒 |

PSF/MTFの後処理そのものは軽い。性能改善の第一候補はトレース後処理ではなく、ray aimingである。

## 7. 推奨される次の改善

優先度順:

1. 仕様16.3節の瞳アフィン写像を実装する  
   主光線と絞り縁4点/8点のみ厳密aimingし、中間瞳点はアフィン近似で生成する。

2. aiming解のwarm startとキャッシュを入れる  
   keyは `system_id + configuration + field + wavelength + stop radius` 程度が妥当。

3. aiming残差計算を軽量化する  
   現在は途中トレース結果取得に `paths` を使っているため、stop面到達点だけを返す専用関数へ分離する。

4. 非球面交点とaiming反復をNumba化する  
   仕様27.4節のLevel 2相当。

5. performance benchmarkをCIの任意ジョブにする  
   `smoke` は通常確認用、`default` / `detail` は手動または夜間向け。

## 8. 現時点の結論

Phase 1-8のMVP機能は実装・検証済みである。

ただし、仕様書の性能目標に対しては、仕様寄り条件で `full ray aiming` が大きなボトルネックになっている。今後の性能改善では、まず瞳アフィン写像とaimingキャッシュを実装するのが最も効果が大きい。
