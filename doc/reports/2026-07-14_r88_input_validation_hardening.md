# R88 主要API入力検証強化 実装報告

## 結果

R88は完了した。機能実装の根拠コミットは`1ebcdf8`（`fix(engine): harden API input validation (R88)`）。

## 修正内容

- system登録時に未知`material_after`を`unknown_material`、非正の`semi_diameter_mm`を`invalid_semi_diameter`の構造化HTTP 400として拒否するようにした。
- 波長は正の有限値を必須とした。`nd_vd`・`sellmeier`・`catalog`は200〜2500 nm、`custom_table`はテーブル範囲内に制限し、範囲外を`optics_value_error`で返す。
- `ray_aiming.mode`はUI仕様にある`off`・`paraxial`・`full`だけを許可し、`teleport`等を構造化HTTP 400とした。
- Analysis系に未定義のトップレベル`metric`・`view`が渡された場合、無視せず構造化HTTP 400とした。
- `configuration.variables.iris_radius_mm`とpreviewの`controls.iris_radius_mm`で非正値を構造化HTTP 400とした。
- 正本仕様26.5に従い、previewの`controls.iris_radius_mm`をconfiguration runtimeへ接続した。
- nominal clear apertureを超えるirisは可変絞り用途を考慮して許容し、`iris_exceeds_clear_aperture` warningをmetadataへ追加した。後続面のvignettingを結果から確認できるため、固定上限による拒否は採用していない。

## R86入力の再実測

`tests/test_r88_input_validation.py`でR86と同じ異常入力をAPIへ直接送信した。

| 入力 | 修正後 |
|---|---|
| `material_after=UNOBTANIUM` | HTTP 400 `unknown_material`。後続HTTP 500経路を解消 |
| `semi_diameter_mm=-2` | HTTP 400 `invalid_semi_diameter` |
| wavelength `-587.56`, `0`, `10000` | HTTP 400 `optics_value_error` |
| `ray_aiming.mode=teleport` | HTTP 400 `optics_value_error` |
| analysis `metric=banana_metric` / `view=impossible_view` | HTTP 400 `optics_value_error` |
| configuration/controls iris `-3` | HTTP 400 `optics_value_error` |
| controls iris `2` | baselineと異なるtrace結果となり、接続を確認 |
| controls iris `1000` | HTTP 200、`iris_exceeds_clear_aperture` warning |

## 検証

- `python -m pytest -q`: `143 passed, 1 skipped, 1 warning in 14.69s`
- R88対象＋主要API回帰: `43 passed, 1 skipped, 1 warning in 1.58s`
- `git diff --check`: pass
- 既存UIの`off` aiming回帰も全テストで確認した。

## 実行環境反映

機能コミット直後にAPI・UIプロセスを再起動した。

- `HEAD`: `1ebcdf8`
- `GET /v1/meta`の`build_info.git_commit`: `1ebcdf8`
- UI `http://127.0.0.1:5173/`: HTTP 200
- `build_info.git_dirty`: `true`（未追跡のactive指示書が存在するため）
