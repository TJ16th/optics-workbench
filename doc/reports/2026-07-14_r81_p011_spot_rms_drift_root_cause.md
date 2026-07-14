# R81 P011中心spot RMS決定論的ずれ原因調査

## 結論

**Done**。原因コミットは`92008eb6e60fc44dd7c406b12058d67d03e244ef`（`perf(engine): add p0 task4 affine aiming cache`）である。ただし、このコミットはR67の`92c88b4`より前に存在する。指示書が想定した`92c88b4..HEAD`内には値を変えたコミットはなく、R67導入時の期待値自体がcache warm-up順序に依存する値だった。

`_AIMING_AFFINE_CACHE`のkeyにはsystem、configuration、field、wavelength、STOP情報だけが入り、`samples_per_field`、`pupil_distribution`、target集合、tolerance、refinement条件が入らない。先行bundleでfitしたaffine係数が別bundleへ流用され、residualが粗いrefine閾値以下のrayはexact toleranceまで再収束されない。そのため同じ81-ray requestでも、直前に9 raysを実行した場合と25 raysを実行した場合でsensor座標とspot RMSが変わる。

これは意図した性能改善の正当な副作用や許容誤差内の数値揺れではなく、同一requestの決定論を破る**意図しない退行**である。本タスクではコード・期待値を修正していない。

## 作業1: 原因コミット

### 履歴の切り分け

同じPython/NumPy環境と現行P011処方を使い、一時detached worktreeで実測した。

| commit | 状態 | cold 81 | warm9→81 | warm25→81 | exact / Level 0 |
|---|---|---:|---:|---:|---:|
| `8ac9e61660fafad8a6e0eebad165faec2e89ad3a` | cache導入直前 | 0.4653881107408963 | 0.4653881107408963 | 0.4653881107408963 | 0.4653881107408963 |
| `92008eb6e60fc44dd7c406b12058d67d03e244ef` | affine cache導入 | 0.4652888433492106 | 0.4654229601236280 | 0.46544749658602347 | 0.4653881107408963 |
| `92c88b4` | P011/R67導入 | 0.4652888433492106 | 0.4654229601236280 | 0.46544749658602347 | 0.4653881107408963 |
| `8778531` | R80完了後HEAD | 0.4652888433492106 | 0.4654229601236280 | 0.46544749658602347 | 0.4653881107408963 |

R67期待値`0.46542296012362827`はwarm9値と丸め差内で一致する。R80で単独実行したテストは、同じtest内の25-ray throughput traceが先にcacheを作るためwarm25値`0.46544749658602347`になった。`92c88b4`そのものでも単独テストは同じ値で失敗したため、R67以降のUI、R73、R75、R79は原因候補から除外できる。

### full suiteが通る理由

`tests/test_preset_api_smoke.py::test_shipped_preset_apertures_preserve_default_throughput_and_paraxial_results`はP011を`9 rays / hexapolar / full`で先に実行する。その後のP011直接回帰はこのcacheをhitし、R67期待値へ一致する。

- 単独P011回帰を2回: いずれも`1 failed`、actual `0.46544749658602347`
- full suite: `117 passed, 1 skipped, 1 warning in 12.67s`

full suiteのgreenはcache状態を初期化しないテスト順序に依存しており、単独実行可能性と決定論を担保していない。

### コード経路

`92008eb`は`optics_engine/tracing.py`へ次を追加した。

1. `_AIMING_AFFINE_CACHE`
2. `_aiming_cache_key()`
3. target群の一部をexact solveしてaffine係数をfitする`_fit_affine_aiming()`
4. cache hit時にfit済み係数からlaunch originを予測する経路
5. residualが`max(tolerance_mm*10, stop_outer_mm*2.5e-3)`を超える場合だけexact refinementする条件

P011のSTOP半径は`17.75 mm`なので既定refine閾値は`0.044375 mm`であり、full aiming tolerance `1e-6 mm`より約44,000倍粗い。

### 中間計算値

warm9とwarm25のsensor差が最大だった81-ray bundleのray index 80を比較した。

| 値 | exact | warm9 cache | warm25 cache |
|---|---:|---:|---:|
| launch origin Y (mm) | 9.1404087793 | 9.1404091917 | 9.1233262733 |
| launch origin Z (mm) | -16.4527358000 | -16.4527365451 | -16.4219872885 |
| STOP local Y (mm) | 8.0681814652 | 8.0681818182 | 8.0535585865 |
| STOP local Z (mm) | -14.5227266349 | -14.5227272727 | -14.4964054528 |
| sensor Y (mm) | -0.5511091167 | -0.5511093073 | -0.5432601353 |
| sensor Z (mm) | 0.9919964098 | 0.9919967532 | 0.9778682434 |

warm25のSTOP交点はwarm9相当targetから約`0.0301 mm`ずれるが、`0.044375 mm`のrefine閾値内なのでexact solveされない。81-ray全体のwarm9/warm25最大sensor座標差は`0.0141285097 mm`だった。aggregate metadataもwarm9が`aiming_iterations_mean=0.7778 / affine_refined_count=21`、warm25が`1.4815 / 40`で異なる。

## 作業2: 変化の性質

Level 1 `strategy=exact`とLevel 0 per-ray referenceは、RMS `0.4653881107408963 mm`、全sensor座標ともビット同一で、最大差`0.0 mm`だった。cache導入直前`8ac9e61`もこの値と一致する。

したがって物理的・数値的な基準はexact/Level 0値である。R67期待値warm9とR80観測値warm25はどちらもaffine近似cacheの履歴依存値であり、どちらかを新しい正解として期待値更新すべきではない。

- warm9 - exact: `+3.4849382732e-5 mm`
- warm25 - exact: `+5.9385845127e-5 mm`
- warm25 - warm9: `+2.4536462395e-5 mm`

修正規模は**中**と見積もる。cache keyへsample数だけを追加しても、同一81-ray requestのcold pathは9本のexact seedをそのまま出力し、cache hit pathは全rayをaffine予測するため、bit-identicalにはならない。target signature、distribution、sampling、tolerance、refinement条件をkeyへ含めたうえで解済みoriginを同じ順序で再利用するか、cacheをinitial guess専用にして全rayを同じtoleranceまでrefineする必要がある。性能回帰と決定論の直接テストも必要である。

## 作業3: 影響範囲

現行HEADで各プリセットの中心81-rayをLevel 0と一致するexact、cold affine、warm9、warm25で比較した。cache導入直前`8ac9e61`では全列がexact値と一致し、warm9/warm25最大sensor差は全presetで`0.0 mm`だった。

| preset | exact RMS (mm) | cold affine | warm9 | warm25 | warm9-exact (mm) | warm25-exact (mm) | warm9/25最大sensor差 (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|
| P002 | 0.0466581879332 | 0.0466581879332 | 0.0466581879332 | 0.0466581879332 | 3.82e-16 | 1.32e-16 | 4.44e-15 |
| P003 | 0.414364415474 | 0.414364415474 | 0.414364415474 | 0.414364415474 | 0 | -1.11e-16 | 3.55e-15 |
| P007 | 2.73788882333 | 2.73788882333 | 2.73788880619 | 2.73788870594 | -1.71e-8 | -1.17e-7 | 5.79e-7 |
| P011 | 0.465388110741 | 0.465288843349 | 0.465422960124 | 0.465447496586 | 3.48e-5 | 5.94e-5 | 1.41e-2 |
| P012 | 0.0369680529656 | 0.0369507496703 | 0.0368627979989 | 0.0369460446189 | -1.05e-4 | -2.20e-5 | 3.79e-4 |

P002/P003は機械精度レベル、P007は微小だが非ゼロ、P011/P012は明確な差がある。結論は「P011単体ではなくfull aiming affine cache全般に及ぶ。感度は処方とSTOP前の非線形性に依存する」である。

## P011 aiming_failed backlogとの関係

P011の`3 fields × 3 wavelengths × 25 rays`を比較すると、exact、cold affine、warm9、warm25のすべてで`alive 213 / aiming_failed 12 / blocked 0`だった。したがって、R80で登録した周辺fieldの12件はaffine cache履歴が原因ではなく、R81の決定論問題とは独立している。

修正時は二つを分離する。

- R81由来: affine cacheの決定論とexact整合を回復する。
- 既存P011 backlog: exact strategyでも残る12件の収束失敗を別途調査する。

## 検証記録

- 一時worktree: `8ac9e61`、`92008eb`、`92c88b4`を実測比較後に削除
- 現行比較HEAD: `8778531`
- `python -m pytest -q`: `117 passed, 1 skipped, 1 warning in 12.67s`
- P011単独回帰: 2回ともspot RMSで`1 failed`
- Level 1 exact vs Level 0: RMS・sensor座標とも最大差`0.0 mm`
- 製品コード変更なしのため`npm run ci`とプロセス再起動は対象外
