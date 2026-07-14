# R84 ヤコビアンバッチモード実装設計提案

## 文書の位置づけ

本書は`doc/engine_spec.md` 25.7節の実装に向けた**設計提案**であり、実装完了報告ではない。R84ではproduction codeを変更していない。最終的な採否、未規定事項の確定、実装着手は人間とClaudeの判断を要する。

調査対象は主に次の現行実装である。

- `optics_engine/tracing.py`: `_trace_raw()`、`_aim_origin_to_stop()`、`_exact_aim_origins()`、R82 exact-origin-bundle cache
- `optics_engine/optimization.py`: `apply_variables()`、`evaluate_system()`、`evaluate_batch()`
- `optics_engine/configuration.py`: `runtime_layout()`、`validate_configuration()`
- `optics_engine/system.py`: `CompiledSystem`、`compile_system()`、`_SYSTEM_CACHE`
- `optics_engine/api/main.py`、`optics_engine/artifacts.py`: evaluate APIとartifact store
- `tests/golden/test_affine_aiming_cache.py`: R82の決定論回帰

## 要約

推奨案は次の3層を段階導入する方式である。

1. **Correctness oracle**: 現行`evaluate_system()`を使い、基準点と摂動点を独立`strategy=exact`で評価するJacobian coordinatorを先に実装する。API・残差順序・step・fallbackを固定する。
2. **Request-local warm refinement**: 基準点のexact originを同じrequest内だけで摂動点のNewton初期値にし、全rayを既定`tolerance_mm`まで必ず再収束させる。warm-refined解をR82のglobal cacheへ登録しない。
3. **Candidate-axis batch kernel**: 同一トポロジーの候補を`candidate × ray × xyz`配列で処理する専用kernelを追加し、現行`_trace_raw()`とLevel 0をoracleとして残す。

一度に第3層まで実装するbig-bang方式は推奨しない。現行には25.7節だけでなく、25.3の一般残差ベクトル、25.5のpenalty、25.6の全variable bindingに未実装部分があり、Jacobianだけを高速化すると「高速だが微分対象の意味が不完全」になるためである。

## 現状と前提差分

### 利用できる基盤

- `_trace_raw()`は1つの`CompiledSystem`に対するray軸vectorized kernelであり、Level 0とのGolden Testがある。
- `_exact_aim_origins()`はtargetごとのNewton solveを行い、`initial_params`を受け取れる。request-local warm startの入口は既に存在する。
- R82 cache keyは`system_hash`、configuration、field、wavelength、STOP条件、launch位置、target配列hash、tolerance、反復上限を含む。
- artifact storeは任意bytesを保存でき、`.npy`配布に利用できる。
- `evaluate_batch()`はcandidate順を維持し、独立評価の比較基準として使える。

### 先に解消すべき差分

- `apply_variables()`は主に`radius_mm`、`thickness_after_mm`、`focal_length_mm`、`semi_diameter_mm`、`iris_radius_mm`だけを扱う。25.6節の`curvature`、`conic`、偶数次非球面係数、group shiftを網羅しない。
- 25.6節はvariablesをCompiledSystemを壊さないruntime parameterと規定するが、現行はsystemをdeep copyして候補ごとに`compile_system()`する。
- `OperandResult`を返すのは現在`ray_fan_error`と`longitudinal_aberration`だけで、25.2節全metricの安定した残差ベクトルは未統一である。
- 25.5節の`ray_loss_ratio` penalty配列は未実装である。
- `validate_configuration()`は負の軸上gapを検出するが、25.7のfallback判断に必要な全hard constraint、特にsag込みedge thicknessを一元判定する層にはなっていない。

したがって、variable registry、residual vector、constraint classificationをJacobian coordinatorの前提APIとして先に固定することを提案する。

## 1. Trace・aiming構造

### 推奨内部構造

新しい内部責務を次のように分ける。

```text
evaluate_system(..., jacobian=...)
  -> build_evaluation_plan()
       fields / wavelengths / pupil sample IDs / operand order
  -> build_candidate_plan()
       base, +h_i, and optionally -h_i
  -> evaluate_candidate_batch()
       variable binding -> constraints -> aiming -> trace -> residual vector
  -> assemble_jacobian()
  -> EvaluateResult + JacobianResult
```

`EvaluationPlan`はrequestから一度だけ作るimmutable値とし、field、wavelength、正規化瞳sample、operand index、penalty indexを保持する。candidateごとにsamplingを再生成しない。random/sobolは既存規約どおりseed必須とし、同じsample IDを全候補へ配る。

`CandidatePlan`は必ず決定論的な順序にする。

- forward: `base, +v0, +v1, ...`
- central: `base, +v0, -v0, +v1, -v1, ...`
- variablesはrequest記載順を維持し、重複は構造化エラーにする。

### 現行`_trace_raw()`との統合

段階1・2ではcandidateごとに現行`_trace_raw()`を呼ぶ。これは真のcandidate batchではないが、既存Golden Testをそのままoracleにできる。

段階3で別関数`_trace_raw_candidates()`を追加することを提案する。現行関数を無理に多目的化しない。

```text
origin:      [candidate, ray, 3]
direction:   [candidate, ray, 3]
wavelength:  [candidate, ray]
status:      [candidate, ray]
surface data:[candidate, surface, ...]
```

各candidateは同じsurface topology、surface ID順、material ID順を持つことをbatch適格条件とする。異なるトポロジーは既存の独立評価へfallbackする。面ごとの処理順は現行と同じにし、candidate/rayごとのalive maskを使う。候補間で生存ray数が異なるため、最初はdense maskを推奨する。compact配列の候補横断連結はindex復元とreduction順を複雑にする。

メモリ上限を超える場合はcandidate順の固定chunkへ分割する。chunk sizeは性能だけに影響し、数値順序を変えないよう、各candidate内のray reductionは常に元ray index順に行う。

### Warm startと決定論

基準点は必ずcanonical exact solveとする。最も安全な初期版はglobal cacheを迂回する`strategy=exact`である。R82 cacheを使う場合も、完全signature一致のexact bundleだけをbaseとして認める。

摂動候補は、同じsample IDの基準点origin Y/Zを`_exact_aim_origins(initial_params=...)`へ渡す。ただし次を必須とする。

1. warm originを最終解として採用しない。
2. 摂動候補のgeometry、layout、STOP targetでresidualを再計算する。
3. `norm(stop_hit_yz - target_yz) <= tolerance_mm`までNewton refinementする。
4. residual不能、特異Jacobian、反復上限、過大stepの場合は、そのcandidate/rayだけparaxial seedからcold exactを再実行する。
5. cold fallbackでも失敗したrayは既存どおり`aiming_failed`とし、soft penalty対象にする。
6. warm-refined originをR82のprocess-global exact bundle cacheへ保存しない。

6がR81/R82の再発防止上、特に重要である。別configuration由来の初期値から止まった`tolerance`内の解をglobal cacheへ昇格すると、後の独立evaluateが履歴依存になる。warm解はrequest-local workspaceだけに置き、request終了時に破棄する。

Newtonには固定のdamping/line-search規則とtrust radiusを加えることを提案する。候補ごとに分岐順を固定し、残差が減少しないstepは決められた係数列（例`1, 1/2, 1/4, ...`）だけを試す。これにより別の光路branchへ飛ぶリスクを抑える。

### 精度上の限界を明示する

warm startは反復初期値を変えるため、独立paraxial seedのexact solveと**ビット同一になる保証はない**。両方が`tolerance_mm`内で停止してもoriginや像面座標が末尾bitから最大でtolerance由来の量だけ異なりうる。また多根問題では異なるrootへ収束する可能性がある。

許容設計は「同一requestの履歴非依存bit determinism」と「独立exact oracleとのtolerance-based equivalence」を分ける。

- 同一request: candidate順、seed、反復、reduction順を固定し、外部cache履歴を使わないためbit-identicalを要求する。
- oracle比較: status一致、STOP residual上限、origin/像面/残差/Jacobianの誤差budget内一致を要求する。
- branch guardを外れたcandidateは高速化を諦め、cold exactへfallbackする。

### 代替案と却下理由

**現行`_trace_raw()`へ全候補rayを単純連結する案**は却下する。`_trace_raw()`は単一`CompiledSystem`、単一surface列を前提とし、候補ごとにradius/layoutが異なるため正しくない。

**warm originをそのまま摂動候補の解にする案**は却下する。STOP residualが未検証で、R81と同種の近似解流用になる。

**warm-refined解をglobal R82 cacheへ保存する案**も初期実装では却下する。異なるseedで得たtolerance内解が独立cold結果と異なる場合、後続requestの値が履歴依存になる。

## 2. 有限差分とJacobian

### Variable binding registry

文字列suffixの分岐を増やすのではなく、`VariableBinding` registryを導入することを提案する。

```text
key / kind / unit / get_value / apply_value / default_step / feasibility_scope
```

registryは25.6節の全keyを1か所で解決し、unknown key、対象surface/group不在、型不正、非有限値を構造化エラーにする。主な変換は次のとおり。

- `curvature`: `c=0 -> radius_mm=0`、それ以外は`radius_mm=1/c`
- `radius_mm`: 互換用。平面近傍警告を返す
- `conic`, `A4/A6/...`: surface値へ適用
- group shift: configuration runtime layoutへ適用
- iris: configuration runtime apertureへ適用

初期版でsystem deep copyを使ってもよいが、外部契約はregistryに固定する。段階3で同じbindingからcandidate parameter arrayを作れるようにする。

### Step解決

`resolve_step(binding, base_value, request_steps)`を1か所に置く。

- request指定値は有限かつ正でなければエラー。
- 省略時は25.7節の式をkindごとに適用する。
- 実際に使用した値を`steps_used`へ必ず返す。
- `base + h == base`となる浮動小数点stepはmachine spacing以上へ引き上げ、引き上げをmetadataへ記録する。

非球面係数の「次数ごとのfloor」は仕様に数値表がないため、実装前に人間側で値を確定する必要がある。

### Forward difference

通常列は次で計算する。

```text
J[:, i] = (r(base + h_i) - r(base)) / h_i
```

`base + h`がhard infeasibleなら`base - h`を追加評価し、次へfallbackする。

```text
J[:, i] = (r(base) - r(base - h_i)) / h_i
```

### Central difference

通常列は次で計算する。

```text
J[:, i] = (r(base + h_i) - r(base - h_i)) / (2 h_i)
```

片側だけhard infeasibleなら、baseとfeasible側でforward/backward差分へfallbackする。両側infeasibleなら微分不能であり、ゼロ列やNaNを返さない。`status=partial`と列失敗情報を返すか、request全体を構造化エラーにするかはAPIの未規定事項として人間判断を求める。

### Hard infeasible判定

各候補はtrace前に同じ順序で検証する。

1. variable適用・有限値
2. system validation
3. runtime layoutと群交差/負gap
4. sag込みedge thickness等のhard constraint
5. operand前提の存在確認

baseがhard infeasibleならJacobianを作らず通常の`status=infeasible`を返す。摂動だけがhard infeasibleなら上記片側fallbackを行う。TIR、blocked、missed、aiming failureはhard infeasibleにせず、25.5節の固定順penalty residualへ含める。

### Residual vectorの固定

Jacobianの行はrequestのoperand順、その後にpenaltyを`field index -> wavelength index -> penalty type`の固定順で並べる。candidateによりray failureが0でもpenalty行自体は省略せず値0を置く。候補ごとに行数や意味が変わる実装は禁止する。

各candidateの自然値を先に計算し、同じoperand定義からresidualを作る。reductionはray index順の固定pairwise sum、または逐次和にする。

### 代替案と却下理由

**外部optimizerへn+1回呼び出しを任せる案**はcorrectness oracleとしては残すが、最終実装にはしない。HTTP、sampling生成、compile、aimingを共有できず25.7節の目的を満たさない。

**自動微分/JAXを先に導入する案**は却下する。25.8節の将来候補であり、現行NumPy kernel、分岐status、artifact/APIを同時に置換する規模になる。有限差分契約を先に固定した方が移行oracleを得られる。

**infeasible列をゼロにする案**は却下する。optimizerへ「感度なし」という誤情報を渡すためである。

## 3. API・レスポンス

### `/v1/optics/evaluate`への追加

25.7節のrequest/response形状は変更しない。API層は`payload.jacobian`を明示的にparseし、coreの`evaluate_with_jacobian()`へ渡す。未知fieldを黙って無視する現状は解消し、mode、variables、stepsを検証する。

coreには次の結果型を追加する案とする。

```text
JacobianResult
  mode
  variables
  residuals              # base residual vector
  matrix: np.ndarray      # library利用者向け
  steps_used
  column diagnostics     # internal/API serialization用
```

既存`EvaluateResult`へoptional `jacobian`を加える。Jacobian未指定時のJSONは現状から変えない。

### Matrix返却

- 要素数`<=1000`: row-majorのJSON nested arrayを`matrix`へinlineする。
- 要素数`>1000`: `np.save(..., allow_pickle=False)`の`.npy`を`ARTIFACT_STORE`へ保存し、`artifact://jacobian/<id>`を返す。
- dtypeは初期版`float64`固定、shapeは`matrix_shape`と一致させる。
- artifact IDはmatrix bytesとcanonical request signatureのSHA-256から決定論的に作る。現在のUUID既定をそのまま使うと同一requestの応答文字列が変わる。

artifact TTLは既存storeに従い、取得時の`Content-Type`は`application/x-npy`とする。同じIDへの並行putを安全にするatomic write/lockも実装時に必要である。

### Fallback diagnostics

25.7節はinfeasible列の片側fallbackを「応答にフラグ」と規定するが、フラグのfield名を例示していない。required形状を維持したadditive diagnosticsとして、各variableの`scheme_used`（`forward`, `central`, `backward_fallback`, `forward_fallback`, `failed`）とviolationsを返す設計が必要である。正確なfield名は実装指示前に人間側で確定する。

### `evaluate-batch`との関係

置き換えず併存を推奨する。

- `evaluate-batch`: 任意candidate集合のscore比較、異なる変数組合せ、並列worker向け
- `evaluate` + `jacobian`: 1つのbaseと規則的な有限差分候補、共有sampling/warm start向け

内部では両者が将来`evaluate_candidate_batch()`を共有できるが、公開APIの意味は統合しない。`evaluate-batch`へ暗黙にJacobian挙動を入れると、既存のcandidate独立性とparallel_workersの意味が変わる。

### 構造化エラー

新codeを追加する場合は`/v1/meta.enumerations`へ同時追加する。候補は`jacobian_invalid_request`、`jacobian_unsupported_variable`、`jacobian_column_infeasible`だが、既存`optics_value_error`へparamsを増やす方針も可能である。code粒度は人間判断事項とする。

### 代替案と却下理由

**新しい`/v1/optics/jacobian` endpointを作る案**は却下する。25.7節は`evaluate`の`jacobian`として契約を凍結している。

**`evaluate-batch`をJacobian APIへ置き換える案**は却下する。任意candidate評価と有限差分は入力・fallback・出力行列の意味が異なる。

**常にartifactにする案**は小行列でHTTP往復を増やすため却下する。逆に常にJSON inlineも大行列のserialization負荷が大きい。

## 4. 精度・決定論の検証

### Oracle

同じcandidate planを、cacheをclearした独立プロセスまたは`strategy=exact`で1候補ずつ評価した結果をoracleとする。Jacobian batch自身の関数を独立モードで再利用せず、既存`evaluate_system()`とLevel 0 traceを基準にする。

検証は「最終matrixだけ」でなく、各段階を比較する。

1. candidate値と`steps_used`
2. hard/soft status
3. pupil targetとaiming success
4. launch origin、STOP hit residual、sensor coordinate
5. operand自然値、penalty、residual vector
6. Jacobian matrix、merit

### 提案する受け入れ基準

同一requestの履歴条件を変えた実行では次をbit-identicalとする。

- JSON inline数値、status、steps、residuals、matrix
- cold、同一request反復、別sampling実行後、別configuration実行後
- candidate chunk size変更後
- `parallel_workers=1`と許可された並列数。reduction順は固定する

warm batchと独立exact oracleの比較は、初期の代表Golden系で次を出発基準とする。

- status/aiming success/行順: 完全一致
- 各STOP residual: `<= tolerance_mm`
- origin Y/Zとsensor Y/Z: `atol <= max(2 * tolerance_mm, 1e-9 mm)`
- normalized residual: `atol <= 1e-6`, `rtol <= 1e-8`
- Jacobian: `atol <= 1e-6`, `rtol <= 1e-3`

これは提案初期値であり、実装時にP002/P007/P009/P011/P012、spec-like 14面、annulus、asphere、decenter/tiltで実測して厳しくできる側へ確定する。上限を緩めないと通らない系は、そのcandidateをcold exactへfallbackさせる。

Jacobian誤差はstepで増幅されるため、さらに方向微分テストを行う。固定方向`d`と小係数`alpha`に対し、`r(x+alpha d)`と`r(x)+alpha Jd`の誤差が、forwardではstep縮小に伴い概ね一次、centralでは概ね二次で減少することを確認する。

### 履歴回帰matrix

R82のテストをJacobianへ拡張する。

| 履歴 | 期待 |
|---|---|
| cache clear後に同一Jacobianを2回 | bit-identical |
| 9/25/81 samplesを先に実行 | 影響なし |
| 別iris、別field、別wavelengthを先に実行 | 影響なし |
| variables順を変えた別requestを先に実行 | 影響なし |
| forward後central、central後forward | 各request内で同一 |
| candidate chunk 1/4/all | bit-identical |
| artifact inline境界1000/1001要素 | shape/content一致 |

artifact URIまで同一にするには前述のcontent-addressed IDが必要である。

### 失敗系テスト

- base infeasible: traceせず`infeasible`
- +h infeasible: backward fallback
- -h infeasible: forward fallback
- central片側infeasible: baseを使う片側差分
- 両側infeasible: 明示的なcolumn failure
- warm Newton非収束/特異: cold exact fallback
- cold exactも失敗: soft ray penaltyまたはcolumn failureを仕様区分どおり返す
- NaN/Inf step、unknown variable、重複variable: 構造化エラー
- random/sobol seedなし: 構造化エラー

### 代替案と却下理由

**warmとoracleのbit-identicalを全ケースで要求する案**は最終的な理想だが、異なるNewton seedとtolerance停止を許す設計とは一般に両立しない。これを必須にするならwarm後にcanonical cold solveが必要となり、高速化を失う。履歴非依存bit determinismとoracleへの誤差budgetを分離する方が現実的である。

**merit scalarだけを比較する案**は却下する。残差の符号違い、行ずれ、誤ったfallback列を見逃す。

**通常pytestだけで決定論を確認する案**も不十分である。cache履歴、chunk、並列、別sample countを明示的に並べ替えるGolden Testが必要である。

## 5. 規模感と段階導入

### 規模見積り

| 段階 | 規模 | 概算 | 根拠 |
|---|---|---:|---|
| A. variable registry・residual vector・constraint分類 | 中 | 5–9人日 | 25.3/25.5/25.6の前提差分、既存evaluate回帰 |
| B. correctness-first Jacobian API | 中 | 5–8人日 | mode/step/fallback、結果型、inline/artifact、APIテスト |
| C. request-local warm refinement | 中 | 5–9人日 | Newton guard、cold fallback、R82履歴Golden、精度bench |
| D. candidate-axis trace kernel | 大 | 12–20人日 | compiled parameter配列、candidate mask、全surface kind、Level 0等価性 |
| E. 性能調整・運用固め | 中 | 4–7人日 | chunk、artifact concurrency、spec-like benchmark、CI |
| 合計 | 大 | 31–53人日 | 仕様前提の不足を含むproduction品質見積り |

既存2 operand、forward diff、独立評価、inline matrixだけに限定したvertical sliceなら小〜中（3–5人日）で可能だが、25.7節完全対応とは主張できない。

### 推奨ロードマップ

#### J0: 契約fixtureとoracle

- 25.7 request/response fixtureを追加
- variable/operand/penaltyの対応表を確定
- 独立exact有限差分benchmarkを固定
- production挙動はまだ変えない

出口: API形状、行順、step、failure表が人間レビュー済み。

#### J1: 前提層

- `VariableBinding` registry
- 全対応operandの固定残差ベクトル
- penaltyとhard constraint分類
- 現行evaluate互換テスト

出口: 1 candidateから安定した`residuals`を作れる。

#### J2: Correctness-first Jacobian

- `/v1/optics/evaluate`で`jacobian`を受理
- 独立exact候補でforward/central/fallback
- `<=1000` inline、`>1000` deterministic artifact

出口: 外部n+1 evaluate oracleと規定誤差内一致。性能改善はまだ主張しない。

#### J3: Request-local warm refinement

- base exact originをcandidate seedへ使用
- toleranceまで必ずrefine
- branch guard、cold fallback、global cache非昇格
- R82型履歴Golden

出口: J2と規定誤差内、同一request bit-identical、R83条件で明確な短縮。

#### J4: Candidate-axis kernel

- `CompiledTemplate`とcandidate parameter arrays
- `_trace_raw_candidates()`
- candidate chunk、固定reduction
- 現行`_trace_raw()`/Level 0とのGolden等価性

出口: 5/10/20変数でR83の`1.25 × cold`仮定を実測評価。未達ならprofile後に次判断。

#### J5: Harden・公開

- artifact concurrency/TTL
- capabilities/enumerations更新
- full pytest、spec benchmark、HTTP benchmark
- docsと実装状況更新

出口: 実際に動作する機能だけをcapabilitiesへ公開。

### 代替案と却下理由

**J1〜J4を一括実装する案**は却下する。残差契約、warm精度、candidate kernelのどこで差が出たか分離できず、R81のような履歴バグを見つけにくい。

**candidate-axis kernelを最初に作る案**も却下する。独立Jacobian oracleと固定residual rowがない状態では、高速な誤答を検出できない。

**J2の独立exact版を最終版とする案**はAPI価値はあるが、25.7節の共有性能目標を満たさないため中間段階に限定する。

## 判断が必要な論点

実装指示書の発注前に、次を人間とClaude側で確定する必要がある。

1. 非球面係数`A4/A6/...`の次数別default step floor。
2. 両側hard infeasible列の公開挙動: `status=partial`かrequest errorか。
3. 25.7節が要求するfallback flagの正式field名と形状。
4. 初期公開で対応必須とするoperand範囲。現行2 operandだけのPartial公開を許すか。
5. Jacobian向けaiming toleranceを通常traceと同値にするか、微分ノイズ対策でより厳しくするか。
6. 精度受け入れ値`residual atol=1e-6`, `Jacobian rtol=1e-3`の妥当性。実装時Golden実測で確定する必要がある。
7. deterministic artifact IDとTTL更新時の同時アクセス規約。
8. J4の性能出口をR83中央仮定`<=1.25 × cold`にするか、段階別の現実的目標を設定するか。

## 最終提案

J0〜J3を先行発注し、J3完了時にR83 benchmarkを再実行してからJ4への投資を判断することを推奨する。request-local warm refinementだけで十分な速度が得られる可能性があり、candidate-axis kernelは効果を実測してから着手できる。

採用上の非交渉条件は次の3点である。

- warm startは初期値に限定し、摂動候補自身の`tolerance_mm`まで必ず再収束する。
- warm-refined解はglobal R82 cacheへ昇格させず、同一requestの結果を外部履歴から隔離する。
- 独立exact oracle、履歴順序Golden、固定reductionを実装と同時に入れ、速度だけで完了判定しない。

この条件を守れば、R82で回復した決定論を維持しながら、R83で示された4.8〜16.8倍の理論余地を段階的に取りに行ける。

## 完了根拠

- 対象機能コミット: `10584e126064866f9d2de4740b028b845f56ebb1`
- R83計測コミット: `796210d`
- 参照テスト: `tests/golden/test_affine_aiming_cache.py`、`tests/golden/test_trace_kernel_equivalence.py`、`tests/test_phase7_optimization_evaluate.py`
- R84 production code差分: なし
- `python -m pytest -q`: `118 passed, 1 skipped, 1 warning in 13.99s`
- `git diff --check`: pass
