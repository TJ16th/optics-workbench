# Aberration Chart Standard Check

Date: 2026-07-10

## Scope

- Work order: `doc/work_orders/done/codex_q6_aberration_chart_standard.md`
- Target UI: Analysis tab chart rendering for P002 and P003.
- Goal: remove collapsed SVG axis labels and align the aberration chart display closer to the common three-panel longitudinal-aberration convention.

## Findings Before Fix

- The UI already rendered individual charts for Ray Fan, Distortion, Field Curvature, Relative Illumination, and MTF.
- The existing chart axes were optimized per chart:
  - Ray Fan: pupil coordinate -> transverse error.
  - Distortion: field angle -> distortion percent.
  - Field Curvature: field angle -> focus shift.
- The API already exposed `/v1/analysis/longitudinal-aberration`, but the UI chart batch did not call it.
- Axis labels were drawn inside the old `360x220` SVG near ticks. This made label/tick crowding more likely in small panels.

## Changes

- Added `LongitudinalAberrationPoint` and `ChartAnalysisResult.longitudinal` to the UI domain types.
- Added `/v1/analysis/longitudinal-aberration` to `runChartAnalyses`.
- Added a new top-level `Longitudinal Aberration Standard Panels` section in the Analysis tab:
  - Longitudinal Aberration: `x = focus shift mm`, `y = pupil coordinate`, color-coded by wavelength.
  - Field Curvature: `x = focus shift mm`, `y = half field deg`, M/S series separated.
  - Distortion: `x = distortion %`, `y = half field deg`.
- Kept the existing individual charts after the standard panel for detailed inspection and backward familiarity.
- Expanded chart SVG viewBox to `390x240`, moved the x label below the plot, and rotated the y label with dedicated left margin.

## Verification

- `npm.cmd run ui:build`: passed.
- `npm.cmd run i18n:coverage`: passed.
- `npm.cmd run ui:e2e -- apps/workbench-ui/tests/e2e/analysis-conditions.spec.ts -g "P002 and P003 analysis charts"`: passed.
- Real UI/API visual check:
  - Preset: P003 Achromat Doublet 100mm Demo.
  - Saved screenshot: `doc/images/aberration-standard-p003.png`.
  - Confirmed standard panel chart IDs:
    - `longitudinal-aberration-chart`
    - `standard-field-curvature-chart`
    - `standard-distortion-chart`
  - Confirmed axis labels:
    - `focus shift mm`
    - `pupil coordinate`
    - `half field deg`
    - `distortion %`

## Remaining Notes

- A fully custom optical-design-house style plot frame is not introduced yet. The current implementation uses the existing SVG chart renderer with corrected axis semantics and label placement.
- No backlog item was added because the requested three-panel view is implemented in this pass.
