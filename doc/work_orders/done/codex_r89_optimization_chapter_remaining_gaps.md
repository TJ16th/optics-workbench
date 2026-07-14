# R89：25章（最適化API）残る高ブロッカー項目の実装 指示書（Codex向け）

## 背景

R85（25章仕様準拠監査）で見つかった高ブロッカー項目のうち、変数バインディング・残差ベクトル拡張・未対応入力の構造化エラー化はR87で完了した。本タスクは、残る高ブロッカー項目5件を扱う。

- 25.5節：`ray_loss_ratio`疑似operand、random/sobolのseed契約
- 15.3節：`gaussian_quadrature`・`polar`・`hexapolar`・`sobol`の専用瞳サンプリング実装（現状は全てgeneric gridの別名）
- 10.3節：edge_thickness/constraint（sag込み判定、有効径干渉、連続制約値）
- 26.3/26.6節：近軸像距離solve（`/v1/solve/paraxial-image-distance`エンドポイント、`configuration.solves`の実装）
- 25.4節：Merit Function統一（新残差二乗和と旧線形scoreの併存解消）

これらは各々ある程度独立した作業であるため、**1タスクずつ完了報告を受けてから次へ進む**（バッチ実行はしない）。作業5（merit統一）は既存UIへの影響可能性があるため、実装ではなく調査・提案までに留める。

## 作業

### 作業1：25.5節 ray_loss_ratioと決定論的sampling seed

1. `ray_loss_ratio(field, wavelength)`を、TIR・ケラレ・aiming失敗によるray損失比率として実装し、25.5節に沿った疑似operandとしてresidualベクトルへ自動追加する。
2. `random`・`sobol`のsampling distributionで、`seed`パラメータが実際に結果へ反映されるようにする（現状はseed未指定・seed=1・seed=2が全て同一結果になっており、seedが無視されている）。
3. penalty対象となるray status（TIR/vignetting/aiming_failed等）の選択が、25.5節の記載と一致することを確認する。
4. 既存のR82決定論（同一request signatureでbit-identical）に影響しないことを確認する。

### 作業2：15.3節 専用瞳サンプリング実装

1. `gaussian_quadrature`・`polar`・`hexapolar`・`sobol`それぞれについて、現状のgeneric gridとの別名状態を解消し、15.3節が意図する専用配置（`gaussian_quadrature`は積分weight付き配置等）を実装する。
2. 5種の瞳分布名を指定した場合に、実際に異なる配置・座標が返ることをAPI実測で確認する（R85/R86で確認された「全て同一配列」状態を解消する）。
3. 既存のgrid/fan_y/fan_z/random分布の既存挙動・既存テストに影響しないことを確認する。

### 作業3：10.3節 edge_thickness/constraint

1. `edge_thickness`を実際に算出するevaluate operand・metricとして実装する（隣接面間の周縁厚、両面の有効半径の小さい方の位置でsagを加味して評価、10.3節の定義に従う）。
2. 有効径干渉（隣接面の有効径が物理的に重なる場合）、sag量による面接触の検出を追加する。
3. ユーザー指定の`min_air_gap`等の連続constraint値をoperandとして返せるようにする。
4. 既存の`validate_configuration()`による負gap検出（既存動作）を壊さないことを確認する。

### 作業4：26.3/26.6節 近軸像距離solve

1. `POST /v1/solve/paraxial-image-distance`エンドポイントを新規実装する（26.3節の契約に従う）。
2. `configuration.solves=[{"type":"paraxial_image_distance",...}]`をevaluateが実際に解決し、応答に`configuration_resolved`を含めるようにする（現状は入力が無視され、応答にも含まれない）。
3. 既存の`best-focus` solve・`image_plane_policy`機能とは別の契約であることを踏まえ、混同・重複実装がないようにする。

### 作業5：25.4節 Merit Function統一（調査・提案のみ、実装は行わない）

1. 現行UIが、`evaluate`応答の`merit.score`・`merit.metrics`・`merit.weights`（旧線形score形式）に依存している箇所があるかを、UIコードの参照有無で確認する。
2. 新しい残差二乗和＋penalty形式（25.4節）へ統一する場合の移行方針案（旧形式を残しつつ新形式を追加する／旧形式を廃止する／両方を別フィールドで返す等）を、UI依存の有無を踏まえて複数提示する。
3. 本作業は実装せず、調査結果と移行方針案を報告書としてまとめる（R84と同様の「提案書」形式）。

## 完了条件（作業1〜4共通）

- 各節の主要契約が実装され、API実測でR85が指摘したギャップが解消されたことが確認されている。
- 既存のR82決定論・R87で追加した回帰テスト・既存テスト全体に影響がないことを確認している。
- 新規動作を固定する回帰テストが追加されている。
- 完了報告前にプロセスを再起動し、`build_info.git_commit`がHEADと一致することを断定形で記載する（未来形で締めない）。
- **各作業の完了報告の実装根拠には、コミットメッセージだけでなく実際のコミットハッシュ値を必ず併記する。**

## 完了条件（作業5）

- UI依存の有無が具体的なコード参照（ファイル・関数）で確認されている。
- 複数の移行方針案が、それぞれのメリット・デメリットとともに提示されている。
- production codeは変更しない。

## 注意

- 作業1〜4は独立して完了報告すること。1つの作業が完了したら報告し、次の作業へ進む前に停止する（人間の確認を待つ必要はないが、報告と実装を作業単位で区切ること）。
- 作業5は実装ではなく提案である。「統一しました」ではなく「このように統一することを提案します」というトーンで書くこと。
- 各作業の主張（「実装した」「一致する」等）は、目視ではなく必ず実測・API直接確認で裏付けること。
