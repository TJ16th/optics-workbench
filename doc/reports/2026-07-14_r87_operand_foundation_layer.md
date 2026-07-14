# R87 最適化API基盤層 実装報告

## 結果

R87は完了した。機能実装の根拠コミットは`6b82162ef46aecf118f8ef3c98b0cb91c3366b31`（`feat(engine): add operand foundation layer (R87)`）。

## 実装内容

- `VariableBindingRule` / `VariableBinding`による単一registryを追加し、`curvature`、互換`radius_mm`、`conic`、`A4`以降の偶数次非球面係数、group shift、`iris_radius_mm`を共通経路で解決するようにした。
- `curvature=0`を`radius_mm=0`、それ以外を`radius_mm=1/curvature`として適用する。
- group shiftとirisは既存のconfiguration runtime layoutへ統合し、surface変数は候補systemへ適用する。
- 未知または対象面へ適用不能なvariable keyを、`optics_value_error`の構造化4xxとして返すようにした。
- `VARIABLE_KEY_PATTERNS`をregistryから生成するようにし、手書き一覧との乖離をなくした。
- evaluateのmetrics/operandsへ、既存解析を再利用して次を接続した。
  - `rms_spot_radius`
  - `relative_illumination`
  - `geometric_mtf`
  - `ray_fan_error`
  - `longitudinal_aberration`
  - `distortion`
  - `field_curvature`
  - `astigmatism`（tangential - sagittal）
  - `lateral_color`
  - `axial_color`
  - `white_mtf`
  - `back_focal_length`
  - `effective_focal_length`
  - `f_number`
- operand residualを`weight * (value - target) / tolerance`で全対応metricへ適用した。
- 未知metric/operandを`optics_value_error`の構造化4xxとし、`METRIC_CODES`を実際のevaluate対応一覧から生成するようにした。

## 検証

- 全エンジンテスト: `132 passed, 1 skipped, 1 warning in 13.55s`
- R87対象テスト: `14 passed, 23 deselected, 1 warning in 1.52s`
- `tests/test_r87_operand_foundation.py`でvariable適用、未知入力、metadata一致、個別analysis/paraxialとの数値一致、residual、決定論を固定した。
- `tests/test_preset_api_smoke.py::test_r87_aspheric_preset_variables_are_accepted_by_evaluate_api`でP009/P010の`curvature`、`conic`、`A4/A6/A8/A10`、irisをevaluate APIへ直接投入し、HTTP 200と`status=ok`を確認した。
- 既存`tests/test_phase7_optimization_evaluate.py`のR73 operand値・residual回帰、および`tests/golden/test_affine_aiming_cache.py`を含む全テストがグリーンである。

## 実行環境反映

機能コミット直後にローカルAPI・UIプロセスを再起動した。確認値は以下の通り。

- `HEAD`: `6b82162`
- `GET /v1/meta`の`build_info.git_commit`: `6b82162`
- UI `http://127.0.0.1:5173/`: HTTP 200
- `build_info.git_dirty`: `true`（R87指示書と未追跡のactive指示書が存在するため。機能コミットとの一致判定は上記commit値で確認済み）

## スコープ外

指示書どおり、25.4節のmerit統一、`ray_loss_ratio`、edge thickness/constraint、paraxial image distance solve、`gaussian_quadrature`は変更していない。これらをDoneとは扱わない。
