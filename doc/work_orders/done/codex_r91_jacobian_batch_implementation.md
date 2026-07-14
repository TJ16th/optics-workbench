# R91：ヤコビアンバッチモード実装（J2: correctness-first + J3: request-local warm refinement） 指示書（Codex向け）

## 背景

R84でヤコビアンバッチモード（`doc/engine_spec.md` 25.7節）の実装設計案（J0〜J5の段階導入）が提案され、R85で25章全体の仕様準拠監査が行われ、R87・R89でJ1相当の前提層（VariableBinding registry、残差ベクトル拡張、ray_loss_ratioペナルティ、edge_thickness/constraint、専用瞳サンプリング）が実装済みとなった。本タスクは、R84の段階導入のうちJ2（correctness-first Jacobian API）とJ3（request-local warm refinement）を実装する。

R84はJ0〜J3を先行実装し、**J3完了時にR83のベンチマーク手法を再実行してから、J4（candidate軸の完全ベクトル化）への投資を判断する**ことを推奨しており、本タスクもこの方針に従う。**J4（`_trace_raw_candidates()`によるcandidate軸バッチkernel）は本タスクの対象外**とする。

## 決定済み事項（R84が提起した未決定事項への回答）

実装着手前にR84が挙げた8つの未決定事項について、以下の方針で進めること。疑問が残る場合は報告書で明記してよい。

1. **非球面係数のdefault step floor**：既存プリセット（P009/P010）が使う非球面係数の実際の値域を調査し、次数ごとに`base + h != base`が浮動小数点上成立する妥当なfloor値を導出する。導出根拠を報告書に明記する。
2. **両側hard infeasible列の扱い**：`status=partial`とし、該当変数列を明示的なcolumn失敗として返す（request全体を構造化エラーにはしない）。部分的なJacobianでも外部optimizerには有用なため。
3. **fallback flagの field名**：R84自身の提案どおり、各変数に`scheme_used`（`forward`/`central`/`backward_fallback`/`forward_fallback`/`failed`）を付与する形式を採用する。
4. **初期公開の対応operand範囲**：R87で`evaluate`へ接続済みの全operand（13指標）を初期リリースから対応対象とする（2 operandへの限定は不要）。
5. **Jacobian用aiming tolerance**：通常のfull aimingと同じ`tolerance_mm`を使う（Jacobian専用の別toleranceは導入しない）。
6. **精度受け入れ値**：R84提案の初期値を採用する（origin/sensor座標`atol <= max(2 * tolerance_mm, 1e-9 mm)`、normalized residual`atol<=1e-6`/`rtol<=1e-8`、Jacobian`atol<=1e-6`/`rtol<=1e-3`）。実装時のGolden実測で必要に応じて厳しくする。
7. **artifact ID・並行アクセス**：R84提案どおり、matrix bytesとcanonical request signatureのSHA-256から決定論的artifact IDを生成する。同一IDへの並行putに対するatomic write/lockを実装する。
8. **J4の投資判断**：本タスクでは判断しない。J3完了後にR83と同条件のベンチマークを再実行し、その結果を踏まえて別途判断する。

## 作業

### J2：Correctness-first Jacobian API

1. `/v1/optics/evaluate`が`jacobian`パラメータ（25.7節）を受理し、無視せず構造化検証（mode/variables/steps）を行うようにする。
2. 基準点＋n摂動点（forward_diff）または基準点＋2n摂動点（central_diff）を、それぞれ独立した`strategy=exact`相当の評価（現行の`_exact_aim_origins()`をそのまま使う、warm start等の高速化は導入しない）で計算する。この段階では速度最適化を主張しない。
3. R84が提案した`VariableBinding`registry（R87で実装済み）を使って、25.6節の変数キー（curvature/radius/conic/非球面係数/group shift/iris）を摂動対象にできるようにする。
4. hard infeasibleな摂動候補（apply後のsystem検証・R89で追加したconstraint検証等に失敗するもの）は、決定済み事項2・3に従い片側fallbackまたはcolumn失敗として扱う。
5. レスポンスへ`jacobian: {mode, variables, residuals, matrix_shape, matrix, steps_used}`を実装する。`matrix`は要素数1000以下ならJSONインライン、超える場合は決定論的artifact IDでArtifactStoreへ保存する。
6. `evaluate-batch`は変更しない（既存の独立評価のまま維持する）。

### J3：Request-local warm refinement

1. 基準点のexact origin（Y,Z）を、同一request内でのみ摂動点のNewton初期値として使う。`_exact_aim_origins()`に初期値を外部から渡せるオプションを追加する。
2. warm start適用後も、必ず既定`tolerance_mm`・`max_iterations`まで収束計算を行う（初期値が違うだけで停止条件は変えない）。
3. Newtonには固定のdamping/line-search（例：`1, 1/2, 1/4, ...`の係数列）を導入し、別の光路branchへ収束するリスクを抑える。
4. residual不能・特異Jacobian・反復上限・過大stepの場合は、そのcandidate/rayだけparaxial seedからのcold exact解法へ自動fallbackする。
5. **warm-refined originはR82のprocess-global exact bundle cacheへ保存しない**（request-local workspaceのみで完結させ、request終了時に破棄する）。これはR81/R82の再発防止として必須の非交渉条件である。

## 決定論・精度の検証（必須）

1. **同一request内の履歴非依存bit決定論**：candidate順・seed・反復・reduction順を固定し、同一jacobianリクエストを異なる履歴条件（cache clear後、9/25/81 samples先行実行後、別configuration/iris/field/wavelength先行実行後等）で複数回実行し、結果がbit-identicalであることを確認する。
2. **独立exact oracleとの誤差バジェット照合**：J2の独立評価版をoracleとし、J3のwarm-refined結果が決定済み事項6の許容誤差内で一致することを確認する。origin/sensor座標だけでなく、candidate値・status・pupil target・aiming success・residual vector・Jacobian matrixの各段階を比較する。
3. **境界ケースの重点テスト**：ケラレ境界・TIR境界近傍のfieldを含む系で、摂動によってray statusが変化する（aliveからblocked/aiming_failedへ、またはその逆）不連続なケースを意図的に含めたテストを追加する。
4. **収束次数テスト**：固定方向・小係数に対する方向微分近似の誤差が、forward_diffで概ね一次、central_diffで概ね二次で減少することを確認する。
5. R82の既存Golden Test、R87〜R89で追加した回帰テストに影響がないことを確認する。

## 完了条件

- J2（独立評価によるJacobian API）が実装され、複数プリセット・複数変数でAPI実測により動作確認されている。
- J3（request-local warm refinement）が実装され、J2との誤差バジェット照合、および同一request内のbit決定論が実測で確認されている。
- 境界ケース（ケラレ/TIR境界近傍の摂動）を含む重点テストが追加されている。
- warm-refined originがR82のグローバルcacheへ保存されないことがコード・テストで確認されている。
- R83と同条件のベンチマークを再実行し、J3導入による実際の速度改善を実測している（R83の`1.25×cold`という保守的仮定との比較を含む）。
- 既存テストが全てグリーンである。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- J4（candidate軸の完全ベクトル化trace kernel）は本タスクの対象外。J3完了後のベンチマーク結果を踏まえ、別途判断する。
- 「決定論的」「厳密解と一致する」という主張は、目視ではなく必ず複数履歴条件・複数プリセットでの実測比較・数値で裏付けること。
- warm-refined originをR82グローバルcacheへ保存しないことは、R81/R82の再発防止上の非交渉条件である。この制約を緩める提案をする場合も、実装前に必ず報告・確認すること。
