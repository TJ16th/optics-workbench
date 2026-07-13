# R73 作業2 Analysis専用View仕様追記 完了報告

## 状態

Done。`doc/ui_spec.md` 17章へ、現行実装とR73作業1の修正結果に基づく4つの専用View仕様を追加した。R73作業3〜6は未着手であり、指示書は`doc/work_orders/active/`に残している。

## 実装根拠

- 仕様コミット: `49b3b4b017666584123ede0fe2054ab5c3ac5a91`
- コミットメッセージ: `docs(ui): specify analysis chart views (R73 task 2)`
- 変更ファイル: `doc/ui_spec.md`

## 追記内容

| 節 | 主な規定 | 実装根拠 |
|---|---|---|
| 17.7 Ray Fan View | Y/Z独立panel、`Py/Pz`、横収差`mm`、`field id + wavelength` series、alive/finite点 | `runChartAnalyses()`、`seriesFromRayFan()`、`ChartSvg()` |
| 17.8 Longitudinal Aberration View | 焦点ずれ`mm`対正規化瞳座標、軸上field、波長別series、瞳順結線、主波長近軸焦点基準 | `analyze_longitudinal_aberration()`、`seriesFromLongitudinal()`、R73作業1コミット`1afa3a9` |
| 17.9 Field Curvature / M-S Image Surface View | 標準/個別panelの軸、field ID結合、M/S series、best focus fallback | `runChartAnalyses()`、`seriesFromFieldCurvatureStandard()`、`seriesFromFieldCurvature()` |
| 17.10 Distortion View | 標準/個別panelの軸、近軸EFL基準、軸上null除外、単一series | `analyze_distortion()`、`seriesFromDistortionStandard()`、`seriesFromDistortion()` |

各節には、未実行時、実行済みだがplot可能な点がない場合、API errorの場合の状態も記載した。Ray Fanには点数別marker調整とDOM metadata保持も明記した。

## 正本変更範囲

人間正本である`doc/ui_spec.md`のうち、指示された17.7〜17.10の新設だけを行った。既存17.1〜17.6、章構成、他の文言は変更していない。17章内に見出し番号の重複がないことを確認した。

## テスト

- `python -m pytest -q`: `105 passed, 1 skipped, 1 warning in 11.32s`
- `npm run ci`: success
  - `i18n:check ok (214 keys)`
  - `i18n:coverage ok`
  - `i18n:test ok`
  - `svg-export-readback ok`
  - `chart-theme:test ok`
  - Playwright E2E `36 passed (48.1s)`

本作業は仕様書のみの変更であり、エンジン/API/UIプロセスの実行コードは変更していない。そのためプロセス再起動と`build_info.git_commit`再確認は対象外である。
