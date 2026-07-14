# R85 engine_spec.md 25章 最適化API仕様準拠監査

## 監査の位置づけ

本書は`doc/engine_spec.md` 25章および指定された関連節の**現状監査報告**である。設計提案・実装・仕様変更は行っていない。production codeの変更はない。

監査対象の実装基準は`10584e126064866f9d2de4740b028b845f56ebb1`である。R83〜R84の後続コミットはベンチ結果・設計提案文書のみで、production codeは同一である。API直接確認時の`GET /v1/meta.build_info.git_commit`も`10584e1`だった。

判定基準:

- **完全**: 節の主要契約がコードとAPIの双方で動作する。
- **部分**: 一部の対象・経路だけ動作し、節全体の契約には不足がある。
- **未実装**: API入力が無視される、endpointがない、または中核アルゴリズムがない。

## 総括

全11監査項目の内訳は、完全1、部分7、未実装3だった。未実装3件のうち25.8は仕様上も将来拡張であり問題ではない。O8-13に対する高ブロッカーは25.2〜25.7と10.3/edge thicknessである。

特に重要な事実は次のとおり。

- 25.2節の23 metricに対し、`evaluate_system()`が値を返すのは5 metricだけである。
- 25.3節のoperand正規化残差は`ray_fan_error`と`longitudinal_aberration`の2 metricだけである。未対応operandはHTTP 200で黙って消える。
- 25.4節の残差二乗和は上記2 operand経路だけで成立する。既存preset/metrics経路は別の線形scoreで、penaltyもない。
- 25.5節の`ray_loss_ratio`疑似operandは未実装。random/sobol seed契約も未実装である。
- 25.6節の`curvature`、`conic`、非球面係数、group shift variableは未実装またはevaluateへ未接続で、unknown keyも黙って無視される。
- 25.7節のJacobianは未実装。R83/R84の結論を再確認した。
- 15.3節の`gaussian_quadrature`、`polar`、`hexapolar`、`sobol`は専用実装ではなく、現状同じgeneric grid点列になる。
- 26.3/26.6節の`/v1/solve/paraxial-image-distance`と`configuration.solves`は未実装である。
- 10.3節は負gap検出のみ実用化されている。有効径干渉、sag込みedge thickness、連続制約値は未実装である。

## 一覧

| 節番号 | 節タイトル | 実装状況 | 根拠（コード・API） | ギャップ | O8-13ブロッカー度 |
|---|---|---|---|---|---|
| 25.1 | 方針 | **完全** | `optimization.py:evaluate_system()`、`evaluate_batch()`、`POST /v1/optics/evaluate(-batch)` | optimizer本体を内蔵せず候補評価を返す境界は仕様どおり。後続節の評価契約は別途不足 | 低 |
| 25.2 | 評価値 | **部分** | `optimization.py:269 evaluate_system()`。23 metric指定APIで返却は5 key | 分析APIがあるmetricもevaluateへ未接続。完全欠落metricもある。meta列挙も実装と不一致 | **高** |
| 25.3 | オペランドと残差 | **部分** | `ABERRATION_OPERAND_METRICS`、`_evaluate_aberration_operands()`。2 operand APIは成功、`rms_spot_radius` operandは消失 | 2 metricだけ式どおり。他21 metric、全operand返却、unsupported検証が欠落 | **高** |
| 25.4 | Merit Function | **部分** | `_evaluate_aberration_operands()`は残差二乗和。`_compute_merit()`は旧線形score。API merit keyは`score/metrics/weights` | 全operand＋penaltyの二乗和へ統一されていない。`total/definition/penalties/constraints`形状もない | **高** |
| 25.5 | 連続ペナルティと決定論 | **部分** | R82 `_aiming_cache_key()`とGolden Testは履歴決定論を固定。`_unit_disk_samples()`、API sampling比較 | `ray_loss_ratio`とpenaltyなし。randomはseed不要・seed無視、sobolなし。専用distributionも不足 | **高** |
| 25.6 | 変数空間とキー体系 | **部分** | `optimization.py:81 apply_variables()`、`metadata.py:VARIABLE_KEY_PATTERNS`。API variable比較 | radius/thickness/focal/semi-diameter/irisの一部だけ。curvature/conic/A4/group shift未対応。runtime injection規約にも不一致 | **高** |
| 25.7 | Jacobian batch | **未実装** | APIへ`jacobian`を送信しても応答に存在しない。R83/R84と一致 | mode、step、matrix、warm start、片側fallbackの全てがない | **高** |
| 25.8 | 将来の勾配提供 | **未実装（仕様どおり）** | autodiff/JAX実装・capabilityなし。25.8本文は「将来拡張」と明記 | 現在実装済みと誤読させる記述はない。監査上の不備なし | 低 |
| 10.3 / 25.2 | 群移動validation・edge_thickness | **部分** | `configuration.py:148 validate_configuration()`、paraxial/evaluate API。edge metric APIは返らない | negative gapは検出。有効径干渉、sag接触、edge thickness warning/value、min gap operandが欠落。`systems/validate`はconfigurationを検査しない | **高** |
| 26.3 / 26.6 | 近軸像距離solve | **未実装** | route一覧にendpointなし。直接POSTは404。evaluateの`configuration.solves`は無視され`configuration_resolved`なし | best-focus/image-plane policyは別機能で、指定面thickness solve契約を満たさない | 中 |
| 15.3 | gaussian_quadrature瞳サンプリング | **部分** | `tracing.py:73 _unit_disk_samples()`、5 distribution API比較 | fan_y/fan_z/randomとgeneric gridのみ。gaussian weights、polar/hexapolar専用配置、sobol、seed契約がない | 中 |

## 25.1 方針

### 判定: 完全

`evaluate_system()`は1候補、`evaluate_batch()`は複数候補の評価値を返し、外部optimizerそのものは実装していない。`POST /v1/optics/evaluate`と`POST /v1/optics/evaluate-batch`がこの境界を公開している。R83の直接確認でもbatchはcandidate評価APIとして動作した。

この節自体は境界方針なので準拠している。ただし「返す評価値」の契約は25.2以降で大きく部分実装である。

ギャップ分類: 文書の古さではなく、後続節のコード不足。25.1単体の追加実装は不要。既存重複はR83/R84。

## 25.2 評価値

### 判定: 部分

23 metricを`evaluation.metrics`で同時指定したAPI確認では、HTTP 200だが返ったのは次の5つだけだった。

```text
geometric_mtf
longitudinal_aberration
ray_fan_error
relative_illumination
rms_spot_radius
```

### 実装の内訳

| 区分 | metric |
|---|---|
| evaluateで値を返す | `rms_spot_radius`, `ray_fan_error`, `longitudinal_aberration`, `relative_illumination`, `geometric_mtf` |
| 個別analysis/paraxialに関連計算はあるがevaluate未接続 | `encircled_energy_radius`相当データ、`distortion`, `field_curvature`, `astigmatism`相当M/S、`lateral_color`, `axial_color`, `white_mtf`, `back_focal_length`, `effective_focal_length`, `f_number` |
| 25.2の評価値として算出経路なし | `geo_spot_radius`, `vignetting_ratio`, `chief_ray_angle`, `total_track_length`, `element_count`, `glass_penalty`, `min_air_gap`, `edge_thickness` |

`metadata.py:METRIC_CODES`は15項目を列挙するが、25.2の23項目ともevaluateの5項目とも一致しない。例えばevaluateが受理する`geometric_mtf`はmetaに無く、実装のない`edge_thickness`はmetaにある。これは単なる報告書の記載漏れではなく、コード欠落とruntime metadata過大列挙の両方である。

O8-13ブロッカー度は高。optimizerが要求したmetricを無通知で欠落させるためである。既存backlogでは`edge_thickness metricのエンジン実装を追加する`が重複する。他metric全体のumbrella項目は見当たらない。

## 25.3 オペランドと残差

### 判定: 部分

`ABERRATION_OPERAND_METRICS = {"ray_fan_error", "longitudinal_aberration"}`で対象が固定される。この2 metricについては次の式がコードにあり、R73テストとAPIで値・target・tolerance・weight・residualを確認できる。

```text
residual = weight * (value - target) / tolerance
```

一方、`rms_spot_radius` operandを送るとHTTP 200、`operands: []`となり、通常metricとしてRMSだけが計算された。unsupported operandの構造化エラーもない。仕様の「全オペランドについてvalue/residualを配列で返す」を満たさない。

O8-13ブロッカー度は高。DLSへ渡す残差ベクトルの行が入力によって黙って消えるためである。R73作業5は2 metricの部分実装として重複し、R84は全operand残差層をJacobian前提として指摘済み。

## 25.4 Merit Function

### 判定: 部分

2種類のoperand経路では`score += residual * residual`で正しい。一方、operandを使わないpreset/metrics経路の`_compute_merit()`は、RMS値、光量loss、MTF loss等の重み付き線形和であり、25.4節の定義ではない。

API応答は次の実体だった。

```text
merit keys: metrics, score, weights
```

仕様例の`merit.total`、`definition`、`penalties`、`constraints`はない。penalty自体も未実装なので、残差二乗和＋penalty二乗和の統一定義になっていない。

O8-13ブロッカー度は高。旧scoreとDLS meritが同じ`merit`名で併存する。既存backlogの直接重複は見当たらず、R84の前提差分に記録済み。

## 25.5 光線破綻ペナルティと決定論

### 判定: 部分

### 実装済み

- R82によりfull aimingの同一request signatureはexact origin bundleを再利用し、履歴条件を変えてもbit-identicalになるGolden Testがある。
- grid系の現行点列、fan、固定seed 0のrandomは実行ごとには決定論的である。
- `evaluate_batch()`は`pool.map()`でcandidate出力順を維持する。

### 欠落

- `ray_loss_ratio(field, wavelength)`の計算がない。
- penalty疑似operandと`ray_loss_tolerance`がない。
- penalty対象statusの選択がない。
- randomはseedなしでHTTP 200となる。seed 1と2も同一結果で、request seedを参照していない。
- sobol専用実装がなく、seedなしでもHTTP 200となる。
- reduction順を契約として固定する最適化残差テストがない。

O8-13ブロッカー度は高。病的候補で連続勾配を失う。R82は決定論のaiming部分だけと重複し、penaltyの既存backlog項目は見当たらない。

## 25.6 変数空間とキー体系

### 判定: 部分

`apply_variables()`が実際に扱うsuffixは次の4種とirisである。

```text
_radius_mm
_thickness_after_mm
_focal_length_mm
_semi_diameter_mm
iris_radius_mm
```

API確認では`S1_radius_mm=55`だけがsystem hashとRMSを変えた。`S1_curvature`、`S1_conic`、`S1_A4`、`UNKNOWN`はすべてHTTP 200で、基準系と同じsystem hash・RMSだった。

`metadata.py:VARIABLE_KEY_PATTERNS`は`curvature`とgroup shiftを列挙するため、runtime metadata上は使えるように見える。逆に仕様にある`conic`と`A4/A6/...`はmetaにもない。configurationの`group_positions`/`decenters`はruntime layoutで動くが、25.6のvariable keyとしてevaluateへ接続されていない。

また、surface variableはsystem deep copy後に再compileされ、25.6/26.2の「CompiledSystem構造を壊さないruntime injection」ではない。

O8-13ブロッカー度は高。variable指定が無通知で無効になる。既存backlog`variable binding registryをCompiledSystemに保持する`と直接重複し、R84でも前提層として確認済み。

## 25.7 Jacobian batch

### 判定: 未実装

コードに`jacobian` requestのparse、結果型、step、matrix、candidate軸trace、片側fallbackはない。APIへforward diffを送ってもHTTP 200で無視され、応答keyは次だけだった。

```text
merit, metadata, metrics, operands, status, violations
```

O8-13ブロッカー度は高。R83で性能実測、R84で実装設計提案まで完了しており、本監査はその位置づけを再確認した。

## 25.8 将来の勾配提供

### 判定: 未実装（仕様どおり）

JAX/autodiff kernel、`mode=autodiff`、capability列挙はいずれもない。25.8本文は「将来拡張として」と明記し、25.7実装後もAPI形状を維持する方針を述べている。現在実装済みと誤読させる表現ではない。

O8-13ブロッカー度は低。未実装自体が仕様に合致する。ギャップ修正対象ではなく、既存backlog追加も不要。

## 10.3 / 25.2 edge_thickness

### 判定: 部分

`validate_configuration()`はruntime layout後の隣接面X gapを確認し、負なら`negative_air_gap`、指定min未満なら`min_air_gap`を生成する。`analyze_paraxial()`、`trace_forward()`、`evaluate_system()`はこの検証を呼ぶ。

APIではFOCUS_Gを-25 mm移動した系について次を確認した。

- `POST /v1/analysis/paraxial`: HTTP 400、gap -5 mm
- `POST /v1/optics/evaluate`: HTTP 200、`status=infeasible`、violation `negative_air_gap`
- `POST /v1/systems/validate`: configurationを付けてもHTTP 200、`status=ok`。routeがsystem構造だけをvalidateしconfigurationを渡さない

欠落しているのは、有効径の干渉、sag量による面接触、sag込みedge thickness warning/value、ユーザー指定min gapのevaluate operand、連続constraint値である。`edge_thickness`を23 metricに含めてもAPIのmetricsには返らなかった。

これはコード欠落であり、O8-13ブロッカー度は高。hard/soft constraintとedge thickness operandが有限差分候補判定に必要になる。既存backlog`edge_thickness metricのエンジン実装を追加する`と直接重複する。Q1/R2でも既知。

## 26.3 / 26.6 近軸像距離solve

### 判定: 未実装

`optics_engine/api/main.py`には`POST /v1/solve/best-focus`はあるが、`POST /v1/solve/paraxial-image-distance` routeはない。直接POSTはHTTP 404だった。

`configuration.solves=[{"type":"paraxial_image_distance",...}]`をevaluateへ送るとHTTP 200になるが、入力は参照されず、応答に`configuration_resolved`がない。`image_plane_policy.mode=paraxial_image`は評価面を動かす別機能であり、「指定面のthickness_after_mmを解決する」26.6契約ではない。

これは文書の誤記ではなくコード欠落。O8-13ブロッカー度は中。最適化は像面距離を外部変数として扱えば進められるが、仕様どおりの変数削減と等式制約除去はできない。既存backlog・過去Rタスクの直接重複は見当たらない。

## 15.3 gaussian_quadrature瞳サンプリング

### 判定: 部分

`_unit_disk_samples()`の専用分岐は`fan_y`、`fan_z`、`random`だけである。それ以外は同じ矩形grid生成へ入る。

APIで9 samplesを比較すると、`grid`、`polar`、`hexapolar`、`gaussian_quadrature`、`sobol`のsensor Y/Z配列がすべて完全一致した。これは名前だけ受理され、仕様の配置を実装していないことを示す。gaussian quadratureの積分weightを保持するデータ構造もない。

randomは固定seed 0で、seed未指定、seed 1、seed 2がすべて同じだった。sobolも専用系列を生成しない。

O8-13ブロッカー度は中。gridで最適化機能自体は構築できるが、仕様が最適化既定とする少数ray高精度積分は利用できない。既存backlog・過去Rタスクの直接重複は見当たらない。

## API直接確認一覧

確認日は2026-07-14、localhostの`http://127.0.0.1:8000`を使用した。

| API呼び出し | 結果 |
|---|---|
| `POST /v1/optics/evaluate`、2 supported operands | HTTP 200、2 operand、merit score `14.1016615032496` |
| 同、`rms_spot_radius` operand | HTTP 200、`operands=[]`、RMS metricだけ返却 |
| 同、25.2の23 metrics | HTTP 200、5 metricだけ返却 |
| 同、radius/curvature/conic/A4/unknown variables | radiusのみhash・RMS変化。他4つは同一hash・値 |
| 同、`jacobian.forward_diff` | HTTP 200、jacobian keyなし |
| 同、`configuration.solves` | HTTP 200、`configuration_resolved`なし |
| `POST /v1/solve/paraxial-image-distance` | HTTP 404 |
| `POST /v1/trace/forward`、5 distributions | 全てHTTP 200、grid/polar/hexapolar/gaussian/sobolが同一配列 |
| 同、random seedなし/1/2 | 全てHTTP 200、3結果が同一 |
| `POST /v1/systems/validate`、negative-gap configuration | HTTP 200、`status=ok` |
| `POST /v1/analysis/paraxial`、同configuration | HTTP 400、`optics_value_error` |
| `POST /v1/optics/evaluate`、同configuration | HTTP 200、`status=infeasible`、`negative_air_gap` |
| `GET /v1/meta` | metrics 15項目、variable patterns 9項目、build commit `10584e1` |

## ギャップ分類と優先度

### 高: O8-13前提

1. **25.2 metric coverageとmeta整合**: 実装欠落＋metadata過大/不一致。optimizerが要求metricを確認できない。
2. **25.3 residual vector**: 実装欠落。未対応operandのsilent ignoreを含む。
3. **25.4 merit統一**: 旧線形scoreと残差二乗和が混在。
4. **25.5 ray loss penalty**: 実装欠落。病的候補の連続感度がない。
5. **25.6 variable binding**: 実装欠落＋metadata過大列挙。unknown keyもsilent ignore。
6. **25.7 Jacobian batch**: 完全未実装。
7. **10.3 edge/constraint**: negative gap以外の接触・edge厚・連続constraintが未実装。

### 中: 並行または後続可能

1. **26.3/26.6 paraxial image distance solve**: 未実装。外部変数で代替可能だが仕様契約は満たさない。
2. **15.3 gaussian quadrature等**: 部分実装。grid代替は可能だが性能・積分精度目標を満たさない。

### 低

- 25.1の外部optimizer境界は準拠。
- 25.8 autodiffは将来拡張として正しく未実装。

## 既存記録との重複

| ギャップ | 既存記録 |
|---|---|
| 2つの収差operandだけ実装 | R73作業5 |
| exact aiming cache決定論 | R81/R82 |
| Jacobian未実装・性能 | R83 |
| Jacobian設計と前提差分 | R84 |
| variable binding | `issues_backlog.md`の`variable binding registryをCompiledSystemに保持する` |
| edge thickness | `issues_backlog.md`の`edge_thickness metricのエンジン実装を追加する`、Q1、R2 |
| multi-configuration最適化 | `issues_backlog.md`に別途登録済み。今回の単一configuration監査とは隣接するが同一ギャップではない |
| metric全体、ray loss penalty、paraxial solve、gaussian quadrature | 直接一致する既存backlog項目は確認できなかった |

本監査では修正方針を提案せず、backlogの新規登録も行っていない。上記未登録項目を個別Issueに分けるか、O8-13前提タスク群へ統合するかは人間とClaudeの次判断事項である。

## 完了根拠

- production実装基準: `10584e126064866f9d2de4740b028b845f56ebb1`
- R83監査・計測: `796210d`
- R84設計提案: `95a7ba6`
- 主なコード参照: `optics_engine/optimization.py`、`tracing.py`、`configuration.py`、`metadata.py`、`api/main.py`
- 主なテスト参照: `tests/test_phase7_optimization_evaluate.py`、`tests/golden/test_affine_aiming_cache.py`、`tests/test_phase4_groups_configuration.py`
- production code差分: なし
- `python -m pytest -q`: `118 passed, 1 skipped, 1 warning in 14.95s`
- `git diff --check`: pass
