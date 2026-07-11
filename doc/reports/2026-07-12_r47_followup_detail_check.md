# R47 follow-up 詳細確認報告

## 1. R47開始時点のP005 STOP定義

R47開始直前のコミット`356cf10`における生データ相当は次の通りである。

```ts
{
  id: 'STOP',
  kind: 'aperture_stop',
  surface_type: 'plane',
  thickness_after_mm: 80,
  semi_diameter_mm: 100,
  aperture: {
    shape: 'annulus',
    inner_semi_diameter_mm: 40,
    outer_semi_diameter_mm: 100,
  },
}
```

したがって、「R47開始時点では`shape: circle`だった」という理解は正しくない。R47開始時点ですでに`shape: annulus`だった。

annulus STOP自体はR40のコミット`6dde9e9`で追加された。R40より前のP005にはcircle STOPがあったのではなく、STOP面自体が存在せず、面列はM1、M2、IMGの3面だった。

## 2. R47での修正内容

R47はP005のaperture定義を変更していない。R47前`356cf10`とR47コミット`1b6bed7`の`apps/workbench-ui/src/domain/presets.ts`には差分がない。

R47後の生データも次の通りで、修正前と同一である。

```json
{
  "id": "STOP",
  "kind": "aperture_stop",
  "surface_type": "plane",
  "thickness_after_mm": 80,
  "semi_diameter_mm": 100,
  "aperture": {
    "shape": "annulus",
    "inner_semi_diameter_mm": 40,
    "outer_semi_diameter_mm": 100
  }
}
```

R47で実装したのは、既存のannulus値をSystemタブへ表示・編集するUIである。

- Outer編集: `aperture.outer_semi_diameter_mm`と互換用`surface.semi_diameter_mm`を同期
- Inner編集: `aperture.inner_semi_diameter_mm`を更新
- 編集後: system dirty化、登録済みsystem ID・trace・解析結果を無効化
- annulus以外: 従来の単一Semi-Diameter表示を維持

`inner=40`と`outer=100`を決めたのはR47ではなくR40である。R40の変更コメントと履歴では、inner `40 mm`は副鏡M2の`semi_diameter_mm=40`に合わせ、outer `100 mm`は主鏡M1の`semi_diameter_mm=100`に合わせている。これはR42/R44/R45で再確認された方針と一致する。

## 3. 光線追跡への影響

R47前からP005はannulusだったため、「R47前はinner側の光線がcircleとして誤通過していた」という状態ではない。R47はUI編集経路だけを追加し、trace kernelやP005既定値を変更していない。

2026-07-12にP005実値で`aperture_pass`を直接再計測した結果は次の通りだった。

| 半径 r (mm) | 通過 |
|---:|:---:|
| 0 | false |
| 39.999 | false |
| 40.0 | true |
| 70.0 | true |
| 100.0 | true |
| 100.001 | false |

つまり、`r < 40`は中央遮蔽、`40 <= r <= 100`は通過、`r > 100`は外径遮光として動作している。

既存のP005テストは、full ray aimingで生成した9本すべてのSTOP到達半径が`40..100 mm`内にあること、Layout baseline rayの`abs(stop_y_mm)`が`40 mm`以上であることを検証している。一般annulusテストも中心点を遮光し、annulus内の点を通過させる。

## 4. Systemタブの表示・編集

実装済みである。P005のSTOP行ではOuter `100`、Inner `40`を2つの`NumberInput`として同時表示し、双方を編集できる。2026-07-12の対象E2E再実行は`1 passed (3.2s)`だった。

![P005 System tab annulus radius editor](screenshots/2026-07-11_r47_annulus_inner_radius_ui_visibility_1.png)

スクリーンショットはR47完了時にR46規約の`doc/reports/screenshots/`へ保存済みであり、本follow-upでは同じ実装状態を参照している。

## 5. 既存テスト・近軸値への影響

R47はsystem定義を変更していないため、Golden Test、annulus遮光、近軸値、面間隔の計算結果は変わらない。2026-07-12に次の3テストを再実行し、`3 passed in 1.12s`を確認した。

- `tests/test_core_acceptance.py::test_circle_and_annulus_aperture_checks`
- `tests/test_preset_api_smoke.py::test_p005_annular_stop_blocks_the_secondary_mirror_central_obscuration`
- `tests/test_preset_api_smoke.py::test_p005_mirror_reflections_match_the_vector_reflection_law`

P005のコンパイル済み面位置と面間隔は次の値で固定されている。

```text
STOP = 0 mm
M1   = 80 mm
M2   = -570 mm
IMG  = 480 mm
M1 -> M2 = -650 mm
M2 -> IMG = +1050 mm
```

R47完了時の全体検証は`python -m pytest -q: 87 passed, 1 skipped`、`npm run ci: 28 passed`である。

## 根拠

- annulus導入: `6dde9e9`（R40）
- R47直前: `356cf10`
- R47実装: `1b6bed7`
- R47後続表示整理: `2093dd8`（R48）
- 対象UIテスト: `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
- 対象エンジンテスト: `tests/test_core_acceptance.py`、`tests/test_preset_api_smoke.py`

本follow-upは確認・報告のみであり、エンジン、UI、プリセット、正本仕様の変更は行っていない。
