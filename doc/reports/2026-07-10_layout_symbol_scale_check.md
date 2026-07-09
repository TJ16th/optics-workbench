# Layout Symbol Scale Check

Date: 2026-07-10

## Scope

`doc/work_orders/active/codex_layout_symbol_scale_check.md` に基づき、Optical Layout View上のSTOP、sensor、eye_referenceなどの記号サイズが、固定pxではなく光学系データの実寸から決まっているか確認した。

## Findings

修正前の状態:

- 一般のrefractive / mirror / thin_lens面は `semi_diameter_mm` を使って描画半高を決めていた。
- aperture_stop面そのものの縦線は `semi_diameter_mm` / runtime `iris_radius_mm` に追従していた。
- sensorは赤い `rect.sensor-plane` が固定 `height=124px` で、`sensor.height_mm` を反映していなかった。
- eye_referenceは専用寸法を見ておらず、fallback半径 `8mm` 相当で描画されていた。
- Layout ViewのSVGに、実寸半径や描画半高を直接検証するDOM属性がなかった。

## Changes

- `surfaceSemiDiameter()` を拡張した。
  - `sensor`: `sensor.height_mm / 2` をX-Y断面の描画半径として使用。
  - `eye_reference`: `eye.pupil_diameter_mm / 2` を使用。
  - `aperture_stop` / `mechanical_aperture`: annulus外径 `outer_semi_diameter_mm` を優先し、circleは `semi_diameter_mm` を使用。
  - `aperture_stop`: runtime `configuration.variables.iris_radius_mm` があればそれを優先。
- sensorの赤い矩形を固定 `124px` から、同じ実寸スケール由来の `height={h * 2}` に変更した。
- surfaceのSVG groupに検証用属性を追加した。
  - `data-surface-id`
  - `data-surface-kind`
  - `data-semi-diameter-mm`
  - `data-visual-half-height-px`
  - `data-raw-half-height-px`
  - `data-scale-clamped`
- STOP中心dotは実寸半高に軽く追従するようにしつつ、記号として読める最小・最大範囲にクランプした。

## Verification

追加E2E:

- `layout view scales stop, sensor, and eye symbols from physical dimensions`
  - P002: STOP `8mm -> 32px`、IMG `sensor.height=24mm -> semi=12mm -> 48px`、sensor rect height `96px`
  - P005: M1 `100mm -> raw 400px -> visual 92px` として大口径クランプを確認、IMG `30mm height -> semi=15mm -> 60px`
  - P006: STOP `25mm -> raw 100px -> visual 92px`、EYE `pupil_diameter=4mm -> semi=2mm -> visual 20px` として最小クランプを確認
- `aperture slider updates stop radius through debounced preview`
  - P003のruntime irisで、STOPが `10mm -> 40px` から `5mm -> 20px` へ追従することを確認。

実行済み:

```text
npm.cmd run ui:build
npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "layout view scales|aperture slider"
```

結果:

- UI build: passed
- Targeted E2E: passed, 2 tests

## Notes

現在のLayout Viewは縦方向の断面表示として、sensorの実寸は `height_mm / 2` を使う。極端に小さい/大きい径は既存の見やすさ制約に合わせて `20px..92px` にクランプし、クランプ有無は `data-scale-clamped` で確認できる。

annulus apertureを持つWorkbench UIプリセットは現時点では存在しないため、今回の実UI検証はP002/P003/P005/P006で行った。annulus外径優先のコードパスは実装済みで、将来のannulus UIプリセット追加時に同じDOM属性でE2E固定できる。
