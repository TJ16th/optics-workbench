import { expect, test, type Page } from '@playwright/test'

import { presets } from '../../src/domain/presets'

const RUN_CHARTS_BUDGET_MS = 30_000
const chartEndpoints = [
  '/v1/analysis/ray-fan',
  '/v1/analysis/longitudinal-aberration',
  '/v1/analysis/distortion',
  '/v1/analysis/field-curvature',
  '/v1/analysis/ms-image-surface',
  '/v1/analysis/relative-illumination',
  '/v1/analysis/mtf',
]

export function assertRunChartsWithinBudget(elapsedMs: number, budgetMs = RUN_CHARTS_BUDGET_MS) {
  if (elapsedMs > budgetMs) {
    throw new Error(`Run Charts exceeded ${budgetMs} ms budget: ${elapsedMs} ms`)
  }
}

async function selectCatalogPreset(page: Page, presetId: 'P007' | 'P009') {
  const preset = presets.find((item) => item.id === presetId)
  if (!preset) throw new Error(`Missing preset catalog entry: ${presetId}`)

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  const option = page.getByRole('option', { name: new RegExp(`^${presetId}\\s`) })
  await expect(option).toHaveText(`${preset.id} ${preset.name}`)
  await option.click()
  await expect(page.getByRole('combobox', { name: 'Preset', exact: true })).toContainText(`${preset.id} ${preset.name}`)
}

for (const presetId of ['P007', 'P009'] as const) {
  test(`${presetId} Run Charts completes within 30 seconds against the real API`, async ({ page }) => {
    test.setTimeout(45_000)
    // The Playwright page fixture owns context/browser cleanup, including assertion and timeout failures.
    await page.goto('/?lng=en')
    await selectCatalogPreset(page, presetId)
    await page.getByRole('tab', { name: 'Analysis', exact: true }).click()

    const responses = Promise.all(
      chartEndpoints.map((endpoint) =>
        page.waitForResponse(
          (response) => new URL(response.url()).pathname === endpoint,
          { timeout: RUN_CHARTS_BUDGET_MS },
        ),
      ),
    )
    const startedAt = performance.now()
    await page.getByRole('button', { name: 'Run Charts' }).click()
    const completedResponses = await responses
    await expect(page.getByTestId('analysis-chart-grid')).toBeVisible({ timeout: RUN_CHARTS_BUDGET_MS })
    const elapsedMs = performance.now() - startedAt

    for (const response of completedResponses) expect(response.ok(), `${response.url()} returned ${response.status()}`).toBe(true)
    assertRunChartsWithinBudget(elapsedMs)
    await expect(page.getByTestId('analysis-chart-grid').locator('svg.analysis-chart')).toHaveCount(9)
    await expect(page.getByTestId('analysis-chart-grid').locator('circle')).not.toHaveCount(0)
    await test.info().attach(`${presetId}-run-charts-timing.json`, {
      body: JSON.stringify({ preset_id: presetId, elapsed_ms: elapsedMs, budget_ms: RUN_CHARTS_BUDGET_MS }, null, 2),
      contentType: 'application/json',
    })
  })
}

test('Run Charts performance guard rejects an over-budget duration', () => {
  expect(() => assertRunChartsWithinBudget(RUN_CHARTS_BUDGET_MS + 1)).toThrow(
    'Run Charts exceeded 30000 ms budget: 30001 ms',
  )
})
