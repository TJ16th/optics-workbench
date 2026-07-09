import { expect, test } from '@playwright/test'

async function mockEngine(page: import('@playwright/test').Page, options: { failArtifacts?: boolean } = {}) {
  await page.route('http://127.0.0.1:8000/v1/health', async (route) => {
    await route.fulfill({ json: { status: 'ok' } })
  })
  await page.route('http://127.0.0.1:8000/v1/meta', async (route) => {
    await route.fulfill({
      json: {
        engine_version: 'test',
        api_schema_version: '2.3.0',
        result_schema_version: '2.3.0',
        material_catalog_version: 'test',
        preset_version: 'test',
        capabilities: {},
        enumerations: { metrics: [], error_codes: [], warning_codes: [], ray_status_codes: [], variable_key_patterns: [] },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/systems/register', async (route) => {
    await route.fulfill({ json: { system_id: 'system-test', system_hash: 'hash-test' } })
  })
  await page.route('http://127.0.0.1:8000/v1/solve/best-focus', async (route) => {
    const request = route.request().postDataJSON()
    const mode = request.image_plane_policy?.mode ?? 'best_focus_rms'
    const focusCurve = [
      { offset_from_sensor_mm: -0.2, metric: 0.018 },
      { offset_from_sensor_mm: 0.0, metric: 0.012 },
      { offset_from_sensor_mm: 0.42, metric: 0.004 },
      { offset_from_sensor_mm: 0.8, metric: 0.013 },
    ]
    await route.fulfill({
      json: {
        evaluation_plane: {
          policy_mode: mode,
          apply_to: request.image_plane_policy?.apply_to ?? 'evaluation_plane',
          evaluation_plane_x_mm: 53.92,
          sensor_x_mm: 53.5,
          offset_from_sensor_mm: 0.42,
          solved_evaluation_plane_x_mm: 53.92,
          solved_offset_from_sensor_mm: 0.42,
          solved_focus_group_shift_mm: null,
          solve_status: 'converged',
          solve_metric: 0.004,
          focus_curve: focusCurve,
        },
        focus_curve: focusCurve,
        artifacts: { focus_curve: 'artifact://focus/focus-test' },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/artifacts/*/*', async (route) => {
    if (options.failArtifacts) {
      await route.fulfill({
        status: 404,
        json: { code: 'artifact_expired', params: { category: 'focus', id: 'focus-test' }, message_en: 'Artifact has expired.', severity: 'error' },
      })
      return
    }
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([
        { offset_from_sensor_mm: -0.2, metric: 0.018 },
        { offset_from_sensor_mm: 0.42, metric: 0.004 },
      ]),
    })
  })
  await page.route('http://127.0.0.1:8000/v1/education/preview', async (route) => {
    const request = route.request().postDataJSON()
    const fields = request.fields ?? []
    const wavelengths = request.wavelengths_nm ?? []
    const samples = request.ray_sampling?.samples_per_field ?? 1
    const total = Math.max(1, fields.length * wavelengths.length * samples)
    await route.fulfill({
      json: {
        status: Array.from({ length: total }, () => 'alive'),
        sensor_y_mm: Array.from({ length: total }, (_, index) => index / 100),
        sensor_z_mm: Array.from({ length: total }, (_, index) => -index / 100),
        metadata: {
          evaluated_fields: fields,
          wavelengths_nm: wavelengths,
          samples_per_field: samples,
          pupil_distribution: request.ray_sampling?.pupil_distribution,
          ray_aiming_mode: request.ray_sampling?.ray_aiming?.mode,
          profiling: { trace_ms: 1.25, total_rays: total },
        },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/ray-fan', async (route) => {
    const request = route.request().postDataJSON()
    const fields = request.fields ?? []
    const wavelengths = request.wavelengths_nm ?? [587.56]
    await route.fulfill({
      json: {
        points: fields.flatMap((field: { id: string }, fieldIndex: number) =>
          wavelengths.flatMap((wavelength: number) =>
            [-1, 0, 1].map((pupil) => ({
              field_id: field.id,
              wavelength_nm: wavelength,
              pupil_y: pupil,
              pupil_z: pupil,
              sensor_y_mm: fieldIndex + pupil / 10,
              sensor_z_mm: fieldIndex - pupil / 10,
              transverse_error_y_mm: pupil * 0.02 + fieldIndex * 0.01,
              transverse_error_z_mm: -pupil * 0.015,
              status: 'alive',
            })),
          ),
        ),
        metadata: { pupil_distribution: 'fan_y' },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/distortion', async (route) => {
    const fields = route.request().postDataJSON().fields ?? []
    await route.fulfill({
      json: {
        rows: fields.map((field: { id: string; theta_y_deg: number; theta_z_deg: number }, index: number) => ({
          field_id: field.id,
          theta_y_deg: field.theta_y_deg,
          theta_z_deg: field.theta_z_deg,
          ideal_y_mm: index,
          ideal_z_mm: 0,
          distortion_percent: index * 0.2,
        })),
        metadata: { reference: 'paraxial_efl' },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/field-curvature', async (route) => {
    const fields = route.request().postDataJSON().fields ?? []
    await route.fulfill({
      json: {
        rows: fields.map((field: { id: string; theta_y_deg: number; theta_z_deg: number }, index: number) => ({
          field_id: field.id,
          theta_y_deg: field.theta_y_deg,
          theta_z_deg: field.theta_z_deg,
          best_focus_shift_mm: index * 0.1,
          rms_radius_mm: 0.01,
        })),
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/ms-image-surface', async (route) => {
    const fields = route.request().postDataJSON().fields ?? []
    await route.fulfill({
      json: {
        rows: fields.map((field: { id: string }, index: number) => ({
          field_id: field.id,
          tangential_focus_shift_mm: index * 0.1,
          sagittal_focus_shift_mm: index * 0.12,
          method: 'mock',
        })),
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/relative-illumination', async (route) => {
    const fields = route.request().postDataJSON().fields ?? []
    await route.fulfill({
      json: {
        rows: fields.map((field: { id: string; theta_y_deg: number; theta_z_deg: number }, index: number) => ({
          field_id: field.id,
          theta_y_deg: field.theta_y_deg,
          theta_z_deg: field.theta_z_deg,
          throughput: 1,
          cos4_factor: 1 - index * 0.05,
          relative_illumination: 1 - index * 0.05,
        })),
        metadata: { method: 'mock' },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/mtf', async (route) => {
    const frequencies = route.request().postDataJSON().frequencies_lp_per_mm ?? [0, 10, 20]
    await route.fulfill({
      json: {
        points: frequencies.map((frequency: number) => ({
          frequency_lp_per_mm: frequency,
          mtf_y: Math.max(0, 1 - frequency / 100),
          mtf_z: Math.max(0, 1 - frequency / 120),
          mtf_radial: Math.max(0, 1 - frequency / 110),
        })),
      },
    })
  })
}

test('analysis condition edits mark dirty and rerun preview with updated results', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await expect(page.getByText('Optics Workbench')).toBeVisible()
  await expect(page.getByTestId('analysis-dirty-status')).toContainText('clean')

  await page.getByRole('button', { name: 'Add field' }).click()
  await expect(page.getByTestId('field-row')).toHaveCount(4)
  await expect(page.getByTestId('analysis-dirty-status')).toContainText('analysis dirty')

  await page.getByTestId('field-row').last().getByRole('button', { name: 'Remove field' }).click()
  await expect(page.getByTestId('field-row')).toHaveCount(3)

  await page.locator('#field-0-theta-y').fill('4')
  await page.locator('#wavelength-preset').selectOption('486.13')
  await page.getByRole('button', { name: 'Add preset' }).click()
  await expect(page.getByTestId('wavelength-row')).toHaveCount(2)
  await page.locator('#samples').fill('11')
  await page.locator('#pupil-distribution').selectOption('hexapolar')
  await page.locator('#aiming').selectOption('full')

  await page.getByRole('button', { name: 'Run Preview' }).click()
  await expect(page.getByTestId('analysis-dirty-status')).toContainText('clean')
  await expect(page.getByTestId('evaluated-fields')).toContainText('center')
  await expect(page.getByTestId('evaluated-fields')).toContainText('4.000')
  await expect(page.getByText('66').first()).toBeVisible()
  await expect(page.getByText('full').first()).toBeVisible()
})

test('P003 analysis charts render with glossary labels and geometric MTF note', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await page.getByRole('tab', { name: 'Analysis' }).click()
  await page.getByRole('button', { name: 'Run Charts' }).click()

  await expect(page.getByTestId('analysis-chart-grid')).toBeVisible()
  await expect(page.getByText('Ray Fan').first()).toBeVisible()
  await expect(page.getByText('Distortion').first()).toBeVisible()
  await expect(page.getByText('Field Curvature').first()).toBeVisible()
  await expect(page.getByText('Relative Illumination').first()).toBeVisible()
  await expect(page.getByText('MTF').first()).toBeVisible()
  await expect(page.getByText('Diffraction included: false')).toBeVisible()
})

test('image-plane policy solves focus, writes back sensor, and disables for afocal preset', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P002 N-BK7 Biconvex Singlet 50mm Demo').click()
  await page.locator('#image-plane-policy-mode').selectOption('best_focus_rms')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()

  await expect(page.getByTestId('evaluation-plane-metadata')).toContainText('best_focus_rms')
  await expect(page.getByTestId('evaluation-plane-metadata')).toContainText('0.4200')
  await expect(page.getByTestId('focus-curve-chart')).toBeVisible()
  await expect(page.getByText('best focus').first()).toBeVisible()

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByTestId('write-back-sensor').click()
  await expect(page.getByTestId('system-dirty-status')).toContainText('system dirty')
  await page.getByRole('tab', { name: 'Debug' }).click()
  await expect(page.getByText('"thickness_after_mm": 46.92')).toBeVisible()

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P006 Keplerian Afocal Telescope Demo').click()
  await expect(page.locator('#image-plane-policy-mode')).toBeDisabled()
  await expect(page.getByTestId('image-plane-policy-panel')).toContainText('Image-plane policy applies only to focal systems with a sensor.')
})

test('snapshots embed artifacts and compare two saved conditions', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await page.getByRole('tab', { name: 'Analysis' }).click()
  await page.locator('#image-plane-policy-mode').selectOption('sweep')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()
  await expect(page.locator('.snapshot-row').filter({ hasText: 'snapshot-1' })).toBeVisible()

  await page.getByRole('tab', { name: 'Analysis' }).click()
  await page.locator('#field-0-theta-y').fill('3')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()

  await expect(page.getByTestId('compare-view')).toContainText('Condition Diff')
  await expect(page.getByTestId('compare-view')).toContainText('Result Compare')
  await expect(page.getByText('Comparison guard')).toBeVisible()
  await expect(page.getByText('focus curve').first()).toBeVisible()
})

test('partial snapshots fall back when embedded artifact retrieval fails', async ({ page }) => {
  await mockEngine(page, { failArtifacts: true })
  await page.goto('/?lng=en')
  await page.getByRole('tab', { name: 'Analysis' }).click()
  await page.locator('#image-plane-policy-mode').selectOption('sweep')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()
  await page.getByRole('tab', { name: 'Analysis' }).click()
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()

  await expect(page.getByText('partial').first()).toBeVisible()
  await expect(page.getByText('Partial Snapshot')).toBeVisible()
  await expect(page.getByText('Comparison falls back to summary data')).toBeVisible()
})
