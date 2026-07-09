# UI Phase 3 follow-up3: speed test stability and iris variable behavior

## 対象

`doc/work_orders/active/codex_ui_phase3_followup3.md` に対応した。

## 確認1: 速度比テストの安定性

該当テスト:

- `tests/test_engine_v2_1.py::test_image_plane_policy_best_focus_rms_is_within_fixed_sensor_speed_budget`

内容:

- aperture runtime化の速度比較ではなく、既存の `image_plane_policy` best-focus solve が fixed sensor trace に対して極端に遅くなっていないことを確認する性能テスト。
- 閾値は絶対時間ではなく相対倍率で、`best_focus_seconds / fixed_seconds < 3.0`。

評価:

- 短時間の壁時計測定を通常pytestに含めていたため、GitHub Actionsなどの共有runnerでは負荷でフレーキーになる可能性がある。
- 実際にローカルでも一度だけ失敗し、再実行では成功した。

対応:

- `performance` pytest markerを追加。
- 該当テストを `OPTICS_RUN_PERF_TESTS=1` が指定されたときだけ実行するようにした。
- 通常の `python -m pytest` ではskipされ、性能回帰はbench/report系または明示実行で扱う方針にした。

## 確認2: `iris_radius_mm` variable正規化と適用経路

register/compile時の保持:

- `semi_diameter_mm: { variable: "iris_radius_mm", default: 10 }` は、Pydantic model load時に `default` の数値へ正規化される。
- `CompiledSystem` 内では `semi_diameter_mm=10.0` として保持され、`variable` という参照情報は残らない。

trace/preview時の適用経路:

- UIは `configuration.variables.iris_radius_mm` を送る。
- エンジンは `trace_forward()` 内で `configuration` を受け取り、`_runtime_iris_radius()` で `iris_radius_mm` を読む。
- 瞳サンプリングは `_target_points_for_stop_with_layout(..., configuration)` から `_aperture_radius(compiled, configuration)` を通り、runtime値でstop target半径を決める。
- 有効径判定は `_trace_raw(..., configuration)` から `_aperture_pass_with_runtime()` を通り、runtime値でaperture_stopの遮光判定を行う。
- そのため、CompiledSystemはdefault値を持つだけでも、trace/previewごとに送られたruntime値が反映される。

追加テスト:

- `test_runtime_iris_radius_variable_defaults_and_overrides_are_stateless`
  - variable形式がCompiledSystem内でdefault値10へ正規化されること。
  - 未指定では10、`iris_radius_mm=3` では3、再度未指定では10、`iris_radius_mm=8` では8になること。
  - 同一CompiledSystemで前回値が残留しないこと。
- `test_runtime_iris_radius_variable_controls_aperture_blocking`
  - 同じ入射光線が `iris_radius_mm=3` ではblocked、`iris_radius_mm=8` ではaliveになること。

## 将来変数への見解

現方式は `iris_radius_mm` 専用のMVPとしては問題ない。ただし `variable` メタデータがCompiledSystemに残らないため、`S1_curvature` など25.6節の一般変数へ広げるには、variable binding registryをCompiledSystem側に保持する設計が必要になる。ad hocにruntime keyを増やすだけでは、検証・UI表示・最適化APIとの整合が弱くなる。

## 検証

- `python -m pytest tests/test_engine_v2_1.py -q`
  - `16 passed, 1 skipped, 1 warning`
- `python -m pytest`
  - `58 passed, 1 skipped, 1 warning`
- `OPTICS_RUN_PERF_TESTS=1 python -m pytest tests/test_engine_v2_1.py::test_image_plane_policy_best_focus_rms_is_within_fixed_sensor_speed_budget -q`
  - `1 passed`

warningは既存のFastAPI TestClient由来の `StarletteDeprecationWarning`。
