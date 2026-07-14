# R87：最適化API基盤層の実装（変数バインディング統一・残差ベクトル拡張・未対応入力の構造化エラー化） 指示書（Codex向け）

## 背景

R84（ヤコビアンバッチモード設計提案）・R85（25章全体の仕様準拠監査）で、`doc/engine_spec.md` 25章の実装状況が判明した。R84自身が提案した段階導入（J0〜J5）のうち、J1「前提層」（variable registry・残差ベクトル・constraint分類）は、ヤコビアンバッチモードに限らず、O8-13全体（最適化API群）の土台として必要と確認されている。

R85で判明した最重要の問題は、以下の「未対応入力を送ってもエラーにならず黙って無視・無効化される」パターンである。

- `apply_variables()`が`_radius_mm`/`_thickness_after_mm`/`_focal_length_mm`/`_semi_diameter_mm`/`iris_radius_mm`のみを扱い、`S1_curvature`・`S1_conic`・`S1_A4`等の未対応キーはHTTP 200・system不変のまま黙って無視される。
- `evaluate`のoperandに`rms_spot_radius`等の未対応operandを送るとHTTP 200・`operands: []`となり、エラーにも警告にもならない。
- `metadata.py`の`METRIC_CODES`（15項目）・`VARIABLE_KEY_PATTERNS`が、実装済みの範囲とも仕様（25.2/25.6）とも一致しない。

本タスクは、R85が「高ブロッカー」と判定した項目のうち、**変数バインディングの統一と、既に個別実装済みだが`evaluate`へ未接続の指標の接続、および未対応入力の構造化エラー化**に限定して実装する。R85で見つかった他の高ブロッカー項目（25.4 merit統一、25.5 ray_loss_ratio、10.3 edge_thickness/constraint、26.3/26.6 paraxial image distance solve、15.3 gaussian_quadrature等の瞳分布実装）は、それぞれ別タスクとして扱うため本タスクの対象外とする。

## 作業

### 1. VariableBinding registryの導入

1. `apply_variables()`の文字列suffix分岐を、単一の`VariableBinding`registry（key／kind／unit／get_value／apply_value／既定step等を1箇所で解決する構造）へ置き換える。
2. 25.6節に記載された変数キー体系を網羅する：`curvature`（`c=0`のとき`radius_mm=0`、それ以外`radius_mm=1/c`として面へ適用）、`radius_mm`（互換用、平面近傍で警告）、`conic`、非球面係数（`A4`/`A6`/`A8`/`A10`等、既存の非球面プリセットP009/P010が使う次数を最低限カバーする）、group shift（既存のconfiguration runtime layoutへの適用経路を再利用）、`iris_radius_mm`（既存の絞り半径適用経路を再利用）。
3. registryに存在しない未知のキーを`variables`へ渡した場合、**HTTP 200で黙って無視せず、構造化エラー（4xx、既存のエラーコード規約に沿ったcode）を返す**ようにする。
4. `metadata.py`の`VARIABLE_KEY_PATTERNS`を、このregistryから動的に生成する（手書きの重複リストを廃止し、実装との不一致を構造的に防ぐ）。

### 2. 残差ベクトル・evaluate接続の拡張

1. R85で「個別analysis/paraxialに関連計算はあるがevaluate未接続」と分類された指標（`distortion`、`field_curvature`、`astigmatism`相当のM/S、`lateral_color`、`axial_color`、`white_mtf`、`back_focal_length`、`effective_focal_length`、`f_number`）について、既存の個別analysis/paraxial計算経路を呼び出し、`evaluate`のmetrics/operands経路へ接続する。
2. 新規の物理計算・アルゴリズムは実装しない（既存の個別APIが返す値をそのまま`evaluate`からも取得できるようにする接続作業に限定する）。
3. 接続した各指標について、`evaluate`経由で得た値と、既存の個別analysis API（例：`/v1/analysis/distortion`）が同一条件で返す値が一致することを実測で確認する。
4. `ray_fan_error`・`longitudinal_aberration`と同様、25.3節のoperand残差式（`residual = weight * (value - target) / tolerance`、既存実装を踏襲）を、接続した指標にも適用し、`operands`配列で返せるようにする。
5. `metadata.py`の`METRIC_CODES`を、実際にevaluateが返せる指標一覧と一致するよう更新する。

### 3. 未対応operand・metricの構造化エラー化

1. `evaluate`のoperandまたはmetricsに、未対応・存在しない名前が指定された場合、**HTTP 200で黙って結果から消す・無視するのではなく、構造化エラーを返す**（既存のエラーコード規約に沿った新規codeを追加、または既存`optics_value_error`にparamsを拡張するかは実装時の判断でよいが、根拠を報告書に明記する）。
2. どの指標が対応済みかを`/v1/meta`から取得できるようにし、対応済み一覧がこの実装後の実態と一致することを確認する。

### 4. 決定論・回帰確認

1. R82で確立したfull aiming aiming cacheの決定論（同一request signatureでbit-identical）に、本タスクの変更が影響しないことを確認する。
2. 新規追加した各指標の`evaluate`経由の値が、複数回の呼び出しで安定していることを確認する。
3. 既存のR73作業5（`ray_fan_error`・`longitudinal_aberration`）の回帰テストが引き続きグリーンであることを確認する。

## 完了条件

- `VariableBinding`registryが実装され、25.6節記載の主要キー（curvature/radius/conic/aspheric/group shift/iris）を解決できることが、複数プリセットでのAPI直接確認で示されている。
- 未知の変数キーが構造化エラーを返すことが確認されている（黙って無視されない）。
- R85で「未接続」と分類された指標が`evaluate`から取得可能になり、既存の個別analysis APIとの値の一致が実測で確認されている。
- 未対応operand・metricが構造化エラーを返すことが確認されている。
- `metadata.py`の`METRIC_CODES`・`VARIABLE_KEY_PATTERNS`が実装の実態と一致することが確認されている。
- R82の決定論・既存のR73作業5回帰テストに影響がないことを確認している。
- 新規動作を固定する回帰テストが追加され、既存テストとあわせて全てグリーンである。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 注意

- 25.4節のmerit統一、25.5節のray_loss_ratio、10.3節のedge_thickness/constraint、26.3/26.6節のparaxial image distance solve、15.3節のgaussian_quadrature等の瞳分布実装は、本タスクの対象外（別タスクで扱う）。
- 新規の物理計算・アルゴリズムの実装は最小限にとどめ、既存の個別analysis/paraxial計算経路の再利用・接続を優先する。
- 「接続した」「一致する」という主張は、目視ではなく必ず複数条件での実測比較・数値で裏付けること。
