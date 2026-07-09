# UI Phase 3 follow-up: Layout View curvature check

## 対象

`doc/work_orders/active/codex_ui_phase3_followup_check.md` の確認1に対応した。

## 確認結果

- 参照されていた `codex_ui_layout_curvature_fix.md` は、現時点のリポジトリ内では見つからなかった。
- 原因はエンジンではなくUI側だった。P002/P003のsurface定義には `radius_mm` が入っていたが、`LayoutView` は全surfaceをSVGの `<line>` として描いていた。
- P3-2〜P3-5で追加した group shift / aperture / decenter / tilt は、直線描画のままでも位置移動・破線・赤マーカーは見えるため、操作追従そのものへの実害は小さい。
- ただし、レンズ形状の凸/凹、曲率符号、非球面形状は見えなかったため、教育用途・設計確認としての実害はあった。

## 修正内容

- `apps/workbench-ui/src/ui/App.tsx`
  - spherical / aspherical_even surfaceを `radius_mm` に基づくSVG pathで描画するように変更。
  - `radius_mm = 0` または plane surfaceは従来どおり直線描画。
  - `R > 0` は +X側へ、`R < 0` は -X側へsagが出るようにした。
  - `aspherical_even` はエンジン仕様の conic + A4/A6/A8... sag式を使う。
  - decenter / tiltの既存visual transformはpathにも適用。
- `apps/workbench-ui/src/domain/types.ts`
  - UIの `Surface` 型に `conic` と `asphere_coefficients` を追加。
- `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - P002で2つのrefractive面がpathになり、正負半径の向きが逆になることを確認。
  - P003で3つのrefractive面がpathになることを確認。

## スクリーンショット

- P002: `doc/images/phase3-followup-p002-layout-curvature.png`
- P003: `doc/images/phase3-followup-p003-layout-curvature.png`

## 検証

- `npm.cmd run ui:build`
  - 成功。Viteの既存警告のみ。
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - 成功。10 passed。

## 未対応・注意

- 現行プリセットには `aspherical_even` のUI表示確認用プリセットがないため、今回のスクリーンショットは球面のみ。非球面sag式の描画コードは追加済みだが、将来の非球面プリセット追加時にvisual fixtureを追加するとよい。
- follow-up指示の優先順位どおり、確認2のaperture runtime configuration化はまだ未着手。確認1の報告後に進める。
