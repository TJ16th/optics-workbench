# R40 P005 annulus中央遮蔽の確認・修正

## 結論

原因は指示書の分類 (a) であった。P005には `aperture_stop` が存在せず、既存エンジンのannulus判定は実装済みでも、P005の中央遮蔽には適用されていなかった。

P005へ `STOP` を追加し、`inner_semi_diameter_mm: 40`、`outer_semi_diameter_mm: 100` のannulusとして定義した。STOPは主鏡 `M1` の手前10 mmに置き、主鏡外縁のsagよりも入射側にあるため、全有効口径の光線がSTOPを先に通過する。

## 実装内容

- `apps/workbench-ui/src/domain/presets.ts`
  - P005に `STOP` を追加した。
  - 外半径100 mmは主鏡の有効半径、内半径40 mmは副鏡 `M2` の有効半径に対応する。
- `apps/workbench-ui/src/ui/App.tsx` と `apps/workbench-ui/src/styles.css`
  - annulus STOPの中心遮蔽部をLayout View上に `stop-obscuration` として表示するようにした。
  - STOPマーカー、外径、および中心遮蔽が画面上で同時に確認できる。
- `tests/test_preset_api_smoke.py`
  - P005のannulus定義、STOP通過半径、基準光線経路、F値を回帰テストで固定した。
- `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - P005のSTOP外径、内半径40 mm、および中心遮蔽マーカーの描画を検証するE2Eを追加した。

## 確認結果

中心field、`fan_y` 3本、full ray aimingでのP005実トレース結果は次のとおり。

- STOP通過Y座標: `-100`, `40`, `100 mm`
- 基準光線のSTOP通過Y座標: `40`, `-100`, `100 mm`
- 基準光線の経路: すべて `STOP -> M1 -> M2 -> IMG`
- STOP通過半径は回帰テストで全9本について `40 <= r <= 100 mm` を確認した。

近軸量は `EFL = 3000 mm`、`BFL = 1050 mm`、`F/# = 15` となった。周辺光線の実経路では、M1後の `dy/dx` は約 `-0.1004`、M2後は約 `-0.0335` であり、仕様6.3節の検算例の傾き変化と整合する。

## 検証

- `python -m pytest -q`: `86 passed, 1 skipped`
- `tests/test_preset_api_smoke.py`: `13 passed`
- `npm run ci`: `27 passed`

既存のannulus開口判定・瞳サンプリング写像に不具合はなかった。今回の修正はP005プリセットの実装漏れと、Layout Viewにおける中央遮蔽の視認性を解消するものである。
