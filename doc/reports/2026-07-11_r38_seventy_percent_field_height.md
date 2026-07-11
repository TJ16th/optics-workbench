# R38 7割像高field・評価値組み込み 完了報告

## 実施内容

- R39で確定した像高ベースの70% mid-fieldを確認した。focalプリセットでは`theta_mid = atan(0.7 * tan(theta_edge))`を使用し、画角の単純な0.7倍ではない。
- focalプリセットP001、P002、P003、P005、P007の`mid-y`へ`preset_label: image_height_70pct`を付与した。
- Field ID入力のラベルをja/enで`70%像高field ID` / `70% Image Height Field ID`として表示するようにした。IDそのもの`mid-y`はAPI・snapshotで使う識別子として維持した。
- P006はafocal系で像高を評価量としないため、70%像高ラベルの対象外とした。true fieldの中間角0.5 degを維持する。

## 既存評価APIへの接続

- P001の推奨field（`center` / `mid-y` / `edge-y`）を`/v1/education/preview`へ送信し、`metadata.evaluated_fields`に同じ3 fieldが返ることを確認した。
- 同一fieldセットを`/v1/analysis/spot`へ送信し、正常なspot結果（`arrived_count > 0`）を得た。
- 既存のspot・MTF等の解析はリクエストのfield一覧をそのまま使うため、新規APIは不要である。

## 回帰防止

- E2Eのプリセット切替テストに、focal系では70%像高ラベル、P006では通常のField IDラベルとなることを追加した。
- Python APIスモークテストに、7割像高fieldがpreviewとspot解析を通過することを追加した。

## 検証結果

- `python -m pytest -q`
  - `85 passed, 1 skipped, 1 warning`
- `npm.cmd run ci`
  - `i18n:check ok (196 keys)`
  - `i18n:coverage ok`
  - `ui:e2e`: `27 passed`

## 実行プロセス確認

- 本タスクのコードコミット後にAPIとUIを再起動し、`/v1/meta`の`build_info.git_commit`がコードコミットのHEADと一致することを確認した。
