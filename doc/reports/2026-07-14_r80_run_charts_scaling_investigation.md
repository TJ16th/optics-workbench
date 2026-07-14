# R80 Run Charts面数・複数configurationスケーリング調査

## 結論

**Done with noted limitation**。調査対象はHEAD `1031997`、直近の機能コミットは`b655a3a`（R79）である。実API計測では、Run Charts時間は面数に明確に依存し、今回の3点では概ね線形だった。複数configurationは一括評価に未対応で、position数だけ同じRun Chartsを再実行するため、合計時間はほぼ完全にposition数へ比例した。

P011の既知問題も`alive 213 / aiming_failed 12`で再現し、`doc/reports/issues_backlog.md`へ独立項目を追加した。本タスクでは製品コード・挙動・性能を変更していない。

## 計測方法

実UI `http://127.0.0.1:5173/`からViteの現行プリセット定義を読み、Playwrightのrequest contextで実API `http://127.0.0.1:8000`へ直接送信した。`/v1/meta`の`build_info.git_commit`は`b655a3a`、Python 3.12.13、NumPy 2.3.5、`numba_enabled=false`だった。

Run Chartsの現行`runChartAnalyses()`と同じ並列fan-outを使用した。論理解析はRay Fan、Longitudinal Aberration、Distortion、Field Curvature、M/S Image Surface、Relative Illumination、MTFの7種で、HTTP要求はRay Fan 2本とfield別MTF 3本を含む計10本である。現行Run ChartsはSpot endpointを呼ばない。

比較条件は全プリセットで固定した。

- fields: `0 / 0.75 / 1.5 deg`の3点
- wavelength: `587.56 nm`の1波長
- 共通sampling: `9 rays / grid / paraxial`
- Relative Illumination: `1000 rays / grid / paraxial`
- MTF: `4096 rays / grid / paraxial`、`0〜80 lp/mm`を2.5刻みの33点
- system登録と1回のwarm-up後に5回測定し、代表値は中央値

API要求は並列なので、各endpoint時間にはCPU競合と待ち時間が含まれる。内訳の合計はRun Charts全体時間と一致しない。

## 作業1: 面数依存

指示書はP012を「8面+STOP」と記載しているが、現行プリセット実体は屈折面7面、STOP 1面、sensor 1面の計9 surface entryである。以下では実装上の屈折面数`2 / 4 / 7`と、追跡対象entry数`4 / 6 / 9`を併記した。

| preset | 屈折面 | STOP/sensor込み | 5回のRun Charts (ms) | 中央値 (ms) | P002比 |
|---|---:|---:|---|---:|---:|
| P002 | 2 | 4 | 923.7, 831.4, 714.7, 654.2, 644.2 | 714.7 | 1.00 |
| P007 | 4 | 6 | 991.7, 1091.9, 975.9, 1041.4, 988.9 | 991.7 | 1.39 |
| P012 | 7 | 9 | 1649.5, 1751.5, 1661.4, 1607.8, 1545.1 | 1649.5 | 2.31 |

屈折面数`x=[2,4,7]`、中央値`y`の最小二乗回帰は概算で`y = 189.5x + 297.4 ms`、`R² = 0.987`である。3点だけの探索的回帰だが、仮説「面数に依存する」は**肯定**、今回範囲で超線形というより固定費を持つ概ね線形な増加と判断する。

### 解析別内訳

Ray FanはY/Zの遅い方、MTFは3 fieldの遅い方を代表値とした。

| 論理解析 | P002 (ms) | P007 (ms) | P012 (ms) | P012/P002 |
|---|---:|---:|---:|---:|
| Ray Fan | 141.6 | 209.4 | 337.7 | 2.38 |
| Longitudinal Aberration | 108.3 | 122.7 | 171.8 | 1.59 |
| Distortion | 253.4 | 562.9 | 1052.6 | 4.15 |
| Field Curvature | 246.6 | 473.4 | 804.2 | 3.26 |
| M/S Image Surface | 251.0 | 491.2 | 797.2 | 3.18 |
| Relative Illumination | 714.6 | 992.2 | 1649.6 | 2.31 |
| MTF | 527.2 | 697.0 | 1021.7 | 1.94 |

この条件のクリティカルパスは全3系統でRelative Illuminationだった。Distortion、Field Curvature、M/S Image Surfaceは面数増加の影響が大きく、Longitudinal Aberrationは小さい。並列競合を含むため、Distortionの4.15倍だけをアルゴリズム固有の超線形性とは断定しない。

## 作業2: 複数configuration

### API・UIの現状

- Analysis系endpointはrequestの`configuration`を1件だけ受け取る。複数configuration配列や一括Run Charts endpointはない。
- `/v1/optics/evaluate-batch`は複数candidate変数を評価する最適化用で、複数configurationのRun Charts一括評価ではない。
- UIでzoom/focusを変えると`runtimeConfiguration`を更新し、debounce付き低解像度previewと確定previewを実行する。処方自体を編集していなければ`system_id`は保持される。
- Run Charts時の`ensureRegisteredSystem()`は既存`system_id`を返すため再登録しない。各解析は同じCompiledSystem cacheを取得し、変更後configurationで全解析を再計算する。
- system登録が必要なのは未登録時または処方編集でsystemがdirtyになった場合である。

### P003実測

P003の`FOCUS_G.shift_x_mm`を有効範囲`0〜2 mm`で1/3/5点選び、positionごとにRun Chartsを順次実行した。system登録は各シナリオ外で1回だけ行い、登録時間は`2.48 ms`だった。各シナリオは3回測定した。

| position数 | 使用位置 (mm) | 3回の合計 (ms) | 中央値 (ms) | position当たり中央値 (ms) |
|---:|---|---|---:|---:|
| 1 | 0 | 719.4, 789.6, 769.8 | 769.8 | 769.0 |
| 3 | 0, 1, 2 | 2275.1, 2409.8, 2293.2 | 2293.2 | 776.4 |
| 5 | 0, 0.5, 1, 1.5, 2 | 3916.0, 3839.3, 4062.6 | 3916.0 | 775.9 |

回帰は`y = 786.6N - 33.3 ms`、`R² = 0.9997`だった。3位置は1位置の2.98倍、5位置は5.09倍であり、仮説「position数に単純比例」は**肯定**する。position切替固有の固定費やsystem再登録による上振れは測定上認められず、主要コストは解析本体の反復である。

### R5との関係

通常Analysisと最適化APIは別の呼び出し系統なので、同一コード上の一つの欠陥ではない。ただし「公開requestが単一configurationを前提とし、複数位置をまとめる契約と実行計画がない」という設計上の欠落は共通する。既存R5 backlogは最適化operandのmulti-configuration化を対象としており、通常Analysisの一括化は別API設計になる。

単なるbatch endpoint追加は中規模で、HTTP往復とUI orchestrationを整理できるが、実測上の計算量はほぼposition数倍のまま残る。CompiledSystemは既に再利用されているため、position間のtrace共有・vectorizeまで行う性能改善は大規模となる。本タスクでは実装しない。

## 作業3: P011再現

R67と同じP011、3 fields × 3 wavelengths × 25 samples、`hexapolar / full`で実API previewを再実行した。

| 項目 | 結果 |
|---|---:|
| total | 225 |
| alive | 213 |
| aiming_failed | 12 |
| blocked | 0 |
| client経過時間 | 237.0 ms |
| engine profiling total | 149.0 ms |
| aiming | 127.8 ms |
| compile_cache_hit | `true` |

到達数の既知値を完全に再現した。原因調査・修正は行わず、backlogへ登録した。

追加の既存直接回帰テストでは、上記到達数assertまでは通過したが、中心81-ray spot RMSが期待値`0.46542296012362827 mm`に対して`0.46544749658602347 mm`となり2回とも失敗した。P011処方とtracing系にはR67の期待値追加コミット`92c88b4`以降の差分がなく、R80の文書変更が原因ではない。原因未確定のため期待値を更新せず、同じbacklog項目へ残件として記録した。

## 検証記録

- 実測コマンド: `node scripts/r80_measure_tmp.mjs`（調査用一時ファイルは完了時に削除）
- API/UI疎通: `/v1/meta` HTTP 200、UI HTTP 200
- 製品コード変更なしのため`npm run ci`、プロセス再起動は対象外
- 既存R67直接回帰: `python -m pytest -q tests/test_preset_api_smoke.py::test_p011_planar_double_gauss_has_six_positive_thickness_elements`を2回実行し、いずれも到達数assert通過後のspot RMSで`1 failed`
- `git diff --check`: pass
