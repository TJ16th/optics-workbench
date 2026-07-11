# R37 プリセットfield推奨値・センサーY/Z軸規約 完了報告

## 実施内容

### プリセットfield

- `Preset`に任意の`recommendedFields`を追加し、出荷済みのP001、P002、P003、P005、P006、P007へcenter / mid-y / edge-yの3点を設定した。
- 初期表示と異なるプリセットへの切替時に、解析条件のfieldをそのプリセットの推奨値へリセットするよう変更した。
- 同一プリセットを選択し続ける間の手動field編集は保持される。切替時だけリセットする。
- P005は狭角の反射望遠鏡として0 / 0.15 / 0.28 deg、P006はafocal評価として0 / 0.5 / 1.0 degを採用した。その他のfocalプリセットはEFL・センサー寸法に見合う近軸的なY方向fieldを設定した。
- P004は現行の出荷プリセット一覧に存在しないため対象外である。既存のP004追加バックログが残る。

### センサーY/Z軸

- 正本`doc/engine_spec.md`の6.5節へ、`width_mm`はY軸方向（面内水平）、`height_mm`はZ軸方向（面内垂直）の全長であることを明記した。
- `doc/ui_spec.md`のsensor編集説明にも同じ規約を追記した。
- Layout Viewのsensor表示はY方向の寸法として`width_mm / 2`を使うよう修正した。P002の36 x 24 mmセンサーは、Y方向半径18 mmとして描画される。
- R36報告では逆向きの規約案を記していたが、R37指示書で指定された`width_mm -> Y`、`height_mm -> Z`を正本規約として採用し、UI表示もこれへ統一した。

## 回帰防止

- E2E `shipped preset selection resets fields to recommended values`を追加し、全出荷プリセットへの切替でfield IDとmid/edge角が推奨値へ更新されることを固定した。
- 既存のray sampling requestテストを新しいfield ID列へ更新した。
- Layout Viewのsensor物理寸法テストを、新規Y軸規約に対応する36 mm幅・半径18 mmの期待値へ更新した。

## 検証結果

- `python -m pytest -q`
  - `83 passed, 1 skipped, 1 warning`
- `npm.cmd run ci`
  - `i18n:check ok (195 keys)`
  - `i18n:coverage ok`
  - `ui:e2e`: `27 passed`

## 実行プロセス確認

- 本タスクのコードコミット後にAPIとUIを再起動し、`/v1/meta`の`build_info.git_commit`がコードコミットのHEADと一致することを確認した。
