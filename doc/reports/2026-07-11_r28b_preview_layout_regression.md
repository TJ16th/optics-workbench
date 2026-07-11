# R28b preview Layout View regression 完了報告

## 実施内容

- P007で`Run Preview`後にLayout Viewが横方向へ圧縮され、S1-S4とSTOPの表示が重なって見える事象を調査した。
- `/v1/education/preview`の実レスポンスを確認し、surface列は`S1`, `S2`, `STOP`, `S3`, `S4`, `IMG`で、R28の`S1 radius_mm=26.0`相当の形状がpreview経路にも反映されていることを確認した。
- preview後の`paraxial_image_position_mm = 476.2092194595895`など、光学系本体から大きく離れた解析マーカー座標がLayout ViewのXスケール計算に混ざり、光学面の描画範囲を圧縮していたことを原因として特定した。
- Layout ViewのXスケールは光学面・物体側延長・必要な像側延長だけで決め、evaluation plane / solved image / paraxial image / principal planeなどの解析マーカーはスケール決定から除外するよう修正した。マーカー自体は同じスケール上に描画されるため、光学レイアウト範囲内にある場合は表示され、遠方にある場合はレイアウトを圧縮しない。
- P001-P007の各プリセットについて、preview前後でLayout Viewのsurface位置・幅・高さが1px未満の差に収まるE2E回帰テストを追加した。

## 検証結果

- `npm.cmd run ui:build`
  - 成功
- `npm.cmd run ui:e2e -- --grep "layout scale stable after preview|P007 fast meniscus|shipped presets keep layout glass"`
  - `3 passed`
- `npm.cmd run ci`
  - `ui:build` ok
  - `i18n:check` ok (`176 keys`)
  - `i18n:coverage` ok
  - `i18n:test` ok
  - `svg:export:test` ok
  - `chart:test` ok
  - `ui:e2e` ok (`24 passed`)

## スクリーンショット

- `doc/images/r28b-p007-preview-layout-fixed.png`
  - P007で`Run Preview`後、S1-S4/STOP/IMGが潰れずに表示されることを確認した。

## 仕様・指示書との差分

- `/v1/education/preview`の別経路・古いcompile cacheが原因ではなかった。previewレスポンス自体は更新済みP007を返しており、UIのLayout Viewスケール計算が原因だった。
- Plotlyや解析チャート側の変更は不要だったため、今回の修正対象外とした。
- P001-P007のpreview/static Layout View一貫性はE2Eで固定した。
