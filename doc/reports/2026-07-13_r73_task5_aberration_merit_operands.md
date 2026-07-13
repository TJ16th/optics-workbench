# R73 作業5 ray_fan_error / longitudinal_aberration merit operand

## 状態

**Done**

- 実装コミット: `434748c7121ebbeaee3ef7e38c4dd702c5f279df`
- 直接テスト: `tests/test_phase7_optimization_evaluate.py`
- 関連テスト: `6 passed`
- エンジン全検証: `python -m pytest -q` -> `107 passed, 1 skipped, 1 warning`
- UI全検証: `npm run ci` -> `38 passed`

## 実装内容

- `ray_fan_error`と`longitudinal_aberration`を`evaluate_system`の評価metricとして実装した。
- 既存の`evaluation.metrics`＋`weights`形式を維持しつつ、正本仕様25.3節の`evaluation.operands`形式にも接続した。
- operandの`field_id`、`wavelength_nm`、`target`、`tolerance`、`weight`を解釈する。
- 残差は仕様式`weight * (value - target) / tolerance`、meritは残差二乗和で算出する。
- operand結果を`OperandResult`として公開し、`EvaluateResult.operands`へvalue・residual・条件を返す。
- operand評価では不要な基礎traceと同一収差の二重traceを避け、field・波長で絞った計算結果を`metrics`へ再利用する。
- `tolerance <= 0`は例外を送出せず、既存error code`optics_value_error`、`severity / code / params / message_en`を持つ構造化violationとして`status=infeasible`を返す。
- `/v1/meta`の`enumerations.metrics`へ2 metricを追加した。
- `ray_fan_error`を日英supplement用語集へ追加し、正本glossaryは変更していない。

## Metric定義

| metric | 集約方法 | 単位 |
|---|---|---|
| `ray_fan_error` | `fan_y`の`transverse_error_y_mm`と`fan_z`の`transverse_error_z_mm`を、`status=alive`かつ有限の点だけでRMS集約 | mm |
| `longitudinal_aberration` | 標準縦収差図と同じ`fan_y`の`longitudinal_error_y_mm`を、`status=alive`かつ有限の点だけでRMS集約 | mm |

縦収差のゼロ基準はR73作業1で修正・固定した主波長近軸焦点である。

## P002基準値

条件は`center field / 587.56 nm / 9 rays / paraxial aiming`。

| metric | 実光線追跡値 |
|---|---:|
| `ray_fan_error` | `0.08744014142832597 mm` |
| `longitudinal_aberration` | `1.1449306743921865 mm` |

テストでは非自明なtarget・tolerance・weightも指定し、次を確認した。

| metric | target | tolerance | weight | residual |
|---|---:|---:|---:|---:|
| `ray_fan_error` | 0.05 | 0.02 | 2.0 | `3.744014142832597` |
| `longitudinal_aberration` | 1.0 | 0.25 | 0.5 | `0.2898613487843731` |

残差二乗和は`14.1016615032496`。

## 実API確認

最終再起動後、`POST /v1/optics/evaluate`へ上記P002とspec形式の2 operandsを送信した。

- HTTP status: `200`
- response status: `ok`
- values: `[0.08744014142832597, 1.1449306743921865]`
- residuals: `[3.744014142832597, 0.2898613487843731]`
- merit score: `14.1016615032496`

## 実行プロセス

- 確認対象コードコミット: `434748c7121ebbeaee3ef7e38c4dd702c5f279df`
- `GET /v1/meta`の`build_info.git_commit`: `434748c`
- 最新HEADとの一致: 一致
- `/v1/meta`の`enumerations.metrics`: `ray_fan_error`と`longitudinal_aberration`を含む
- UI `http://127.0.0.1:5173/`: HTTP `200`
- `build_info.git_dirty`: `true`。確認時点の未コミット内訳は人間配置の`doc/work_orders/active/`未追跡指示書であり、実装コード差分ではない。
