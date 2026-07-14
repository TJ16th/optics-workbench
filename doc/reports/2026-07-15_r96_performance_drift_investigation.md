# R96 spec-like smoke性能ドリフト調査

## 結論

R82以降の永続的な性能増加として再現したのは`fast_design_score`である。cleanなR82機能コミット`10584e1`比で現行`0bac84b`は`19.633 ms`から`31.538 ms`へ`+60.6%`だった。最大の段差はR89-1で、`ray_loss_ratio`の自動追加により独立したtraceが1回増えたことが主因である。R90ではoperand統一に伴いRMSとMTFのtrace共有が失われ、さらに1回の重複traceが加わった。

`preview full`は`+4.6%`で3系列の範囲が重なり、`high-count trace`は`-4.9%`だった。R93報告時の`+24.2%`、`+3.9%`は今回の同一環境・複数系列では再現せず、コミット固有の永続的回帰とは特定できなかった。

本タスクは調査のみであり、製品コードは変更していない。

## 基準点の補正

既存の`bench_results/20260714_132336_33457c8.json`は`source_commit=33457c8`だが、`git_dirty=true`であり、Pythonは`3.14.3`だった。R82報告書にも、このJSONはR82実装差分を未コミット状態で測定したと明記されている。

`33457c8`をclean checkoutすると、R82のexact origin bundle cacheがまだ存在せず、3系列中央値は`preview full=31.152 ms`、`fast_design_score=67.153 ms`となった。したがって性能比較の正しいR82基準は、R82機能コミット`10584e126064866f9d2de4740b028b845f56ebb1`とした。

## 測定方法

- 専用detached worktreeで各機能コミットをcheckoutした。
- `python benchmarks/spec_like_benchmark.py --profile smoke`を使用した。
- 各実行は既存設定どおりwarmup 1回、repeat 5回。
- 13比較点を正順・逆順・再正順の3系列で測定し、各JSONのmedianのさらに中央値を代表値とした。
- 共通環境はWindows 11、Python `3.12.13`。
- 生成した42件のJSONは`bench_results/20260715_004*.json`へ保存した。
- 2系列目以降のJSONの`git_dirty=true`は、一時worktree内に先行測定の未追跡JSONが残ったためである。各回のtracked sourceは指定コミットをdetached checkoutしており、製品コード差分はない。

## 実測結果

単位はms。値は3系列のmedianの中央値、括弧内はclean R82比。

| 時点 | commit | preview full | high-count trace | fast_design_score |
|---|---|---:|---:|---:|
| R82 | `10584e1` | 5.227 (基準) | 121.544 (基準) | 19.633 (基準) |
| R87 | `6b82162` | 4.872 (-6.8%) | 131.646 (+8.3%) | 16.773 (-14.6%) |
| R88 | `1ebcdf8` | 5.858 (+12.1%) | 113.714 (-6.4%) | 18.344 (-6.6%) |
| R89-1 | `7bafc84` | 5.269 (+0.8%) | 133.615 (+9.9%) | 30.624 (+56.0%) |
| R89-2 | `3446fa9` | 4.934 (-5.6%) | 120.650 (-0.7%) | 22.659 (+15.4%) |
| R89-3 | `19867e2` | 5.452 (+4.3%) | 128.359 (+5.6%) | 27.845 (+41.8%) |
| R89-4 | `c6e447c` | 5.696 (+9.0%) | 120.733 (-0.7%) | 27.127 (+38.2%) |
| R90 | `b0644b9` | 8.025 (+53.5%) | 150.643 (+23.9%) | 32.815 (+67.1%) |
| R91 | `f8d47b3` | 5.565 (+6.5%) | 111.264 (-8.5%) | 35.043 (+78.5%) |
| R93 work 1 | `5fd9f81` | 7.638 (+46.1%) | 111.640 (-8.1%) | 34.590 (+76.2%) |
| R93 work 2 | `30ed59c` | 5.600 (+7.1%) | 111.898 (-7.9%) | 31.641 (+61.2%) |
| R93 work 3 | `68b5465` | 5.864 (+12.2%) | 116.042 (-4.5%) | 33.731 (+71.8%) |
| 現行 | `0bac84b` | 5.466 (+4.6%) | 115.602 (-4.9%) | 31.538 (+60.6%) |

測定範囲は現行で、`preview full=5.17-5.89 ms`、`high-count trace=113.76-118.07 ms`、`fast_design_score=30.60-46.31 ms`だった。R90やR93 work 1のpreviewの一時的な上昇は次コミットで戻り、コード差分の適用範囲とも整合しないため、永続的な原因とは判定しない。

## 原因判定

### preview full

現行はR82比`+4.6%`で測定範囲が重なる。R89-2の専用瞳sampling導入直後はR82比`-5.6%`であり、既定gridパスを重くした証拠はない。R87、R88、R93の変更についても永続的な段差は再現しなかった。

判定: **問題となる性能ドリフトは再現せず**。追加最適化は不要。

### high-count trace

現行はR82比`-4.9%`で、R93報告の`+3.9%`は今回再現しなかった。10000 rays測定はOS負荷による系列間変動が大きく、単一JSON間の数%差は原因帰属に使えない。

判定: **回帰なし**。追加最適化は不要。

### fast_design_score

R89-1でR88比`+66.9%`の最大段差が発生した。`_ray_loss_operands()`が仕様上必須の`ray_loss_ratio`を算出するため、既存のmetric traceとは別に`trace_forward()`を実行する変更と一致する。ray loss評価は正しさのために必要だが、同一field・wavelength・sampling・configurationのtraceを再利用せず再計算することまでは必要ではない。

R90ではR89-4比`+21.0%`だった。R90以前のpreset経路はRMSとMTFで1つのtraceを共有したが、R90以降は`_evaluate_operands()`がoperandごとに`_metric_scalar_value()`を呼び、RMSとMTFが各1回traceする。relative illuminationとray lossを含め、現行presetは概ね4回traceする。これはmerit統一の正しさには不要な重複計算である。

判定:

- `ray_loss_ratio`自体: **正しさのための必要コスト**。
- ray loss用の独立再trace: **最適化余地のある非効率**。
- R90後のRMS/MTF別trace: **最適化余地のある非効率**。
- 修正規模: **中**。request-local評価コンテキストでtraceをcacheし、sampling・field・wavelength・configuration・optionsが一致するoperandだけ共有する必要がある。

この残件は`doc/reports/issues_backlog.md`へ「evaluate内の同一条件traceをoperand間で再利用する」として追加した。Issue化には`Create Issues From Backlog`ワークフローの手動起動が必要である。

## 性能ガード

現行3指標はすべて`0.2秒`未満で、R71のRun Charts `30秒`ガードから十分離れている。現行API/UIに対して`npm.cmd run ui:e2e -- run-charts-performance.spec.ts`を再実行した。

- P007 Run Charts: `4.0s`
- P009 Run Charts: `4.7s`
- 合計: `4 passed (11.3s)`

R71性能ガードへの抵触はない。

## 完了根拠

- 調査対象source HEAD: `0bac84b3f754266c1409f7d2ca1fc663380cafc4`
- ベンチ: `benchmarks/spec_like_benchmark.py --profile smoke`、13比較点、各3系列
- 結果: `bench_results/20260715_004*.json` 42件
- UI性能回帰: `apps/workbench-ui/tests/e2e/run-charts-performance.spec.ts`、`4 passed (11.3s)`
- 製品コード変更: なし
