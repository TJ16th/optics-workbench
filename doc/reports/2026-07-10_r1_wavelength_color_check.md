# Wavelength Color Check

Date: 2026-07-10

## Scope

`doc/work_orders/done/codex_r1_wavelength_color_check.md` に基づき、Workbench UIのOptical Layout ViewとSpot Diagramで、複数波長の表示色が実際に反映されているか確認した。

確認対象はP003 achromat preset、F/d/Cの3波長、複数field、education preview由来のray pathとspot previewである。

## Findings

### Optical Layout View

Layout Viewは既存実装で波長別classを付与していた。

- F線相当: `.ray-f`
- d/e線相当: `.ray-d`
- C線相当: `.ray-c`

P003の複数波長previewで、`#layout-svg path.ray-line.ray-f` / `.ray-d` / `.ray-c` がすべて描画されることをE2Eで確認した。

### Spot Diagram

Spot Diagramは修正前、到達spotをすべて同一色の `.spot-point` として描画していた。そのため、trace metadataに複数波長が含まれていても、spot側では波長ごとの色分けが見えなかった。

今回、`trace.metadata.samples_per_field` と `trace.metadata.wavelengths_nm` から各spotの波長indexを復元し、`wavelengthColor()` のパレットで到達spotを塗り分けるよう修正した。

P003で確認したspot色は以下。

| Wavelength | Band | Color |
| --- | --- | --- |
| 486.13 nm | F | `#0f62fe` |
| 587.56 nm | d | `#8a7400` |
| 656.27 nm | C | `#da1e28` |

E2Eでは各spotに `data-wavelength-index` / `data-wavelength-nm` を付与し、DOM上でも波長とcomputed fillを検証している。

### White Light / Wavelength Weights

Workbench UIには、Analysis Conditions内で以下を設定する導線がある。

- F/d/C/eプリセット波長の追加
- 任意波長の追加
- 各波長の `weight` 編集

Preview/analysis requestでは、`wavelengths_nm` と `wavelength_weights` が送信される。

一方で、仕様上のより抽象的な `light_sources`、または名前付き白色光源プロファイルを選ぶUIは現時点では存在しない。現行Workbenchの範囲では、白色光源相当の重み付き複数波長評価は `wavelength_weights` で利用可能と判断する。`light_sources` プロファイルやwhite PSF/MTFの合成表示は、既存バックログの回折PSF/white PSF/MTF系の将来課題に含めて扱う。

## Changes

- `apps/workbench-ui/src/ui/App.tsx`
  - Spot Diagramの点に波長indexと波長値を対応付けた。
  - 到達spotのfillを `wavelengthColor(wavelength_nm)` で設定した。
  - 検証用に `data-wavelength-index` / `data-wavelength-nm` を付与した。
- `apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts`
  - P003 preview E2EでLayout ViewのF/d/C ray classを検証した。
  - Spot Diagramの波長値とcomputed fillを検証した。

## Results

実行済み:

```text
npm.cmd run ui:build
npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "P003 slider preview"
```

結果:

- UI build: passed
- P003 targeted E2E: passed, 1 test

## Spec Gap

今回の確認範囲で、Layout ViewとSpot Diagramの波長色分けに残る不整合はなし。

`light_sources` という名前付き光源プロファイルUIは未実装だが、Workbench ver0.2/現行MVPの操作導線としては `wavelength_weights` 編集・送信が実装済みであり、直近の欠落Issueではなく将来機能扱いとする。
