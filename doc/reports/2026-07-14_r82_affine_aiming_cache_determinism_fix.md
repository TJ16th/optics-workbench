# R82 affine aiming cache決定論修正

## 状態

**Done**。実装根拠コミットは`10584e126064866f9d2de4740b028b845f56ebb1`（`fix(engine): make aiming cache deterministic (R82)`）である。

R81で特定した、別samplingのaffine係数が同じcache keyで流用される決定論破壊を修正した。修正後はP002/P003/P004/P007/P010/P011/P012で、cold、warm9、warm25、同一bundle cache hit、Level 1 exact、Level 0のorigin・sensor座標・spot RMSがbit-identicalになった。

## 設計方針

R81の2案を比較し、**完全request signatureごとにexact solve済みorigin bundleを保存する方式**を採用した。

### 採用理由

- cache missではLevel 0と同じper-target Newton経路を使うため、coldから厳密解相当になる。
- 同一bundleのcache hitでは解済みoriginと成功状態をそのまま再利用し、bit-identicalかつNewton不要になる。
- 異なる9/25/81-ray target集合は別keyになり、係数や近似解を相互流用しない。
- 「cacheをinitial guessとして全rayをrefineする方式」は、停止条件が`tolerance_mm`なので初期値により最終座標が許容差内で僅かに変わる余地がある。bit-identicalを直接保証できるbundle再利用を優先した。
- cache無効化は選ばず、同一requestの反復性能を維持した。

trade-offとして、異なるtarget集合間のaffine warm startは失われ、cache valueは係数3×2個からray数分のoriginへ増える。ただし、既存cacheも無制限process-local dictionaryであり、本タスクの代表条件では性能・メモリとも実用範囲だった。cache上限設計は本修正の対象外とした。

## 実装

### cache key

従来のsystem/configuration/field/wavelength/STOP情報に加えて、次を含めた。

- `launch_x`
- target配列のshapeとSHA-256
- `tolerance_mm`
- `max_iterations`

`samples_per_field`と`pupil_distribution`は生成後target配列のhashへ反映される。configurationとSTOP径は従来どおり独立keyである。

### cache valueと実行経路

- miss: 全targetを`_exact_aim_origins()`でsolveし、`origins`と`ok`を保存する。
- hit: 保存済みbundleをcopyして返し、iteration数は0とする。
- `strategy=exact`: 従来どおりcacheを迂回してLevel 0相当経路を使う。
- 旧affine fit、粗いrefine threshold、preview時のrefinement省略を削除した。

互換性のため`_AIMING_AFFINE_CACHE`、`ray_aiming_strategy=affine`、既存metadata keyは維持した。実際の解法を明示する`aiming_solution_kind=exact_bundle_cache`と、miss時のsolve本数`aiming_exact_solved_count`を追加した。

## 決定論・精度検証

中心81 rays、`hexapolar / full / 587.56 nm`を使用した。各presetでLevel 1 exactを基準に、cacheをclearしたcold、9 rays実行後、25 rays実行後、同じ81-ray requestのcache hit、Level 0を比較した。

| preset | RMS (mm) | exact/cold差 | exact/warm9差 | exact/warm25差 | exact/cache hit差 | exact/Level 0差 |
|---|---:|---:|---:|---:|---:|---:|
| P002 | 0.046658187933190584 | 0 | 0 | 0 | 0 | 0 |
| P003 | 0.4143644154740728 | 0 | 0 | 0 | 0 | 0 |
| P004 | 0.48432273992330394 | 0 | 0 | 0 | 0 | 0 |
| P007 | 2.737888823333736 | 0 | 0 | 0 | 0 | 0 |
| P010 | 0.4646328343540561 | 0 | 0 | 0 | 0 | 0 |
| P011 | 0.4653881107408963 | 0 | 0 | 0 | 0 | 0 |
| P012 | 0.036968052965618795 | 0 | 0 | 0 | 0 | 0 |

表の差はRMSだけでなく、origin Y/Zとsensor Y/Zを横断した最大絶対差で、すべて`0.0 mm`だった。

`tests/golden/test_affine_aiming_cache.py`へ次を固定した。

- default affine/cache missとexactのbit-identical比較
- 同一bundle hitとcoldのbit-identical比較
- warm9/warm25履歴後の81-rayとexactのbit-identical比較
- configuration/iris変更時のcache miss維持

## 期待値更新

旧full suite順序で9-ray cacheを先に作っていた期待値を、Level 0とbit-identicalな値へ更新した。

| preset | 旧期待値 (mm) | Level 0 / 新期待値 (mm) |
|---|---:|---:|
| P004 | 0.4834598215345252 | 0.48432273992330394 |
| P010 | 0.46463283438394304 | 0.4646328343540561 |
| P011 | 0.46542296012362827 | 0.4653881107408963 |
| P012 | 0.03686279799887928 | 0.036968052965618795 |

P011単独回帰を含む対象テストは`4 passed`、全pytestは`118 passed, 1 skipped, 1 warning in 13.72s`だった。

P011の`aiming_failed 12`はexactでも残るR81確認済みの独立問題であり、本タスクでは変更していない。

## 性能

### 同条件before/after

14面spec-like、3 fields × 3 wavelengths × 21 rays、7反復中央値を同じ環境で比較した。

| 状態 | 修正前 (ms) | 修正後 (ms) | 比率 |
|---|---:|---:|---:|
| cold | 763.889 | 372.636 | 0.49x |
| same-bundle warm | 223.999 | 7.103 | 0.032x |

coldは約51%、warmは約97%短縮した。旧affine fitと全ray residual判定を削除し、missは単純なexact Newton、hitはorigin bundle再利用になったため、この条件では精度向上と高速化を同時に達成した。

### 公式smoke benchmark

結果は`bench_results/20260714_132336_33457c8.json`へ保存した。ファイル名のhashは計測時HEADで、`git_dirty=true`のR82実装差分を含む。

P0タスク4報告値との比較:

| case | P0 task4 (ms) | R82 (ms) | 改善 |
|---|---:|---:|---:|
| preview full aiming 3×3×9 | 24.494 | 4.420 | 5.54x |
| spot full aiming 5×3×21 | 87.658 | 6.947 | 12.62x |
| relative illumination full aiming | 196.906 | 23.661 | 8.32x |
| evaluate fast_design_score full aiming | 55.960 | 17.547 | 3.19x |

benchmarkは1回warm-up後の中央値であり、exact bundle cache hit性能を測る構成である。

## Run Charts・UI検証

機能コミット`10584e1`後にAPI/UIを再起動した。

- `GET /v1/health`: `ok`
- UI `http://127.0.0.1:5173/`: HTTP 200
- HEAD: `10584e1`
- `/v1/meta.build_info.git_commit`: `10584e1`
- 一致判定: `true`
- `build_info.git_dirty=true`: R82指示書と既存の未追跡active同期ファイルによる

R71性能ガード単独実行は`3 passed in 11.5s`で、P007テスト所要4.6秒、P009 5.1秒だった。全E2E再実行でもP007 19.1秒、P009 5.5秒で30秒budget内だった。

`npm run ci`はbuild、i18n、SVG、chart、R71性能ガードを通過したが、39 E2Eの既存decenter/tilt sliderテストが3-worker並列時に1回だけ`tilt_z_deg=undefined`で失敗した。このテストは`paraxial` previewでR82経路外である。単独再実行は`1 passed`、続く全E2E再実行は`39 passed in 1.3m`だったため、並列タイミングフレークとして記録し、スコープ外のUI変更は行っていない。

## 完了根拠

- 実装: `10584e126064866f9d2de4740b028b845f56ebb1`
- 新規・更新テスト: `tests/golden/test_affine_aiming_cache.py`、`tests/test_preset_api_smoke.py`
- エンジン: `118 passed, 1 skipped`
- P011単独を含む対象: `4 passed`
- R71性能ガード: `3 passed`
- 最終全UI E2E: `39 passed`
- `git diff --check`: pass
- 機能コミット直後の再起動とmeta/HEAD一致を確認済み
