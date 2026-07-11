# R32 P005/P006 NaN JSONシリアライズ修正 完了報告

## 原因と発生時期

- P005（カセグレン）では、遮光された光線の`sensor_y_mm` / `sensor_z_mm`を内部表現の値なしとして`NaN`にしていた。P006（afocal）では、終端が`eye_reference`でセンサー面を持たないため、全光線の同じ座標が`NaN`になる。
- 直接の原因は、HTTP APIがこれらの内部`NaN`をJSONの`null`へ正規化せず、JSONResponseがJSON非準拠値として拒否したことである。光線経路の座標・方向にはNaNは混入していなかった。
- `git blame`では、`_trace_raw`の`NaN`初期化とAPIの浅い`_jsonable`はいずれも初期公開コミット`436babb`から存在する。Q1〜R31で新規に混入した不具合ではない。
- Phase 8の`tests/test_phase8_afocal_visual.py`はライブラリレベルの`trace_forward`とafocal解析を確認していたが、`/v1/trace/forward`・`/v1/education/preview`のJSONシリアライズをP005/P006で横断確認するテストはなかった。afocal/mirror系のAPI境界確認が当初漏れていた。

## 修正内容

- `optics_engine/api/main.py`の`_jsonable`を再帰的なHTTP境界の正規化関数に拡張した。`numpy`配列・スカラー、dataclass、Pydanticモデル、辞書・配列を処理し、有限でないfloatはJSONの`null`として返す。
- `/v1/trace/forward`のレスポンス全体にこの正規化を適用した。`/v1/education/preview`は同エンドポイントを呼ぶため同時に修正される。
- UIの`TraceResponse`を`Array<number | null>`へ更新し、レイアウト図とspot表示では有限な座標だけを描画する型ガードを追加した。
- `tests/test_preset_api_smoke.py`を追加した。実際の`apps/workbench-ui/src/domain/presets.ts`を読み、今後追加される出荷プリセットも自動的に対象にして、`/v1/trace/forward`と`/v1/education/preview`の正常応答およびJSON内に非有限数がないことを確認する。P005/P006は`full` / `paraxial` / `off`の全modeを追加確認する。

## 検証結果

- `tests/test_preset_api_smoke.py` と `tests/test_phase8_afocal_visual.py`
  - `12 passed, 1 warning`
- `python -m pytest -q`
  - `80 passed, 1 skipped, 1 warning`
  - Golden Testを含む既存テストはグリーン。
- `npm.cmd run ui:build`
  - 成功。

## 教訓

- カーネル内部の`NaN`センチネルは計算値として公開せず、API境界で値なしを明示的な`null`へ変換する。
- 新しい特殊系・プリセットは、ライブラリ解析テストに加えて、実際のHTTPレスポンスをJSONシリアライズまで確認する。今回の全プリセット横断スモークテストでこの確認を継続する。

## 実行プロセス確認

- 本タスクのコードコミット後にAPIとUIを再起動し、`/v1/meta`の`build_info.git_commit`がコードコミットのHEADと一致することを確認した。
