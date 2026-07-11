# R28 preset order / P007 Layout View回帰 完了報告

## 実施内容

- UIのプリセット選択リストを `id` の自然順で表示するようにした。
  - 表示順は `P001`, `P002`, `P003`, `P005`, `P006`, `P007`。
- P007のLayout View破綻原因を調査した。
- P007のS1球面データを修正した。
  - 修正前: `S1 radius_mm = 14.0`, `semi_diameter_mm = 18`
  - 修正後: `S1 radius_mm = 26.0`, `semi_diameter_mm = 18`
- プリセット順序とP007/全プリセットLayout Viewの回帰E2Eを追加した。

## 原因

P007のS1は `semi_diameter_mm = 18` が `radius_mm = 14` を超えており、球面として物理的に成立しない値だった。
このため、Layout ViewではS1プロファイル端が潰れ、S1-S2ガラス領域が `glass-element-warning` になる負のエッジ厚として描画されていた。

Q1のglass fill / clear aperture boundaryロジック自体は、P007の破綻を警告として正しく可視化していた。今回は描画ロジックではなく、P007プリセット値の粗さが原因だった。

## 修正方針

- S1のclear apertureは維持し、球面半径だけを `26.0 mm` に変更した。
- これによりS1の `semi_diameter_mm = 18` が球面半径内に収まり、S1-S2のエッジ厚warningも解消した。
- STOP径やS2/S3/S4のclear apertureは変更していない。

## 回帰テスト

追加・更新したE2E:

- `preset selector lists shipped presets in natural id order`
- `P007 fast meniscus pair preset renders strong positive and negative curvature`
  - `glass-element-warning` が出ないことを追加確認。
- `shipped presets keep layout glass fills free of edge-thickness warnings`
  - P001/P002/P003/P005/P006/P007を横断確認。

## 検証結果

- `npm.cmd run ui:build`
  - 成功
- `npm.cmd run ui:e2e -- --grep "preset selector lists|P007 fast meniscus|shipped presets keep layout"`
  - `3 passed`
- `npm.cmd run ci`
  - `ui:build` ok
  - `i18n:check` ok (`176 keys`)
  - `i18n:coverage` ok
  - `i18n:test` ok
  - `svg:export:test` ok
  - `chart:test` ok
  - `ui:e2e` ok (`23 passed`)

## 注意点

- P007はデモプリセットであり、今回の修正はLayout View上の物理的な形状破綻を解消するための値修正。
- 光学性能値の参照式やベンチマーク目標を更新する変更ではない。
- 完了報告前のプロセス再起動と `/v1/meta build_info.git_commit` 照合は、R28コミット作成後に最終応答で結果を示す。
