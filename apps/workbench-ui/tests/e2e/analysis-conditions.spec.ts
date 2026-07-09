import { expect, test } from '@playwright/test'

async function mockEngine(
  page: import('@playwright/test').Page,
  options: { failArtifacts?: boolean; previewRequests?: unknown[]; registerRequests?: unknown[] } = {},
) {
  let registeredSurfaceIds = ['STOP', 'S1', 'S2', 'IMG']
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
        build_info: { git_commit: 'test-build', git_dirty: false, started_at: '2026-07-10T00:00:00+00:00' },
        capabilities: {},
        enumerations: { metrics: [], error_codes: [], warning_codes: [], ray_status_codes: [], variable_key_patterns: [] },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/systems/register', async (route) => {
    const request = route.request().postDataJSON()
    options.registerRequests?.push(request)
    const surfaceIds = request.surfaces?.map((surface: { id?: string }) => surface.id).filter(Boolean)
    if (surfaceIds?.length) registeredSurfaceIds = surfaceIds
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
    options.previewRequests?.push(request)
    const fields = request.fields ?? []
    const evaluatedFields =
      request.configuration?.decenters?.length || request.configuration?.tilts?.length
        ? [
            { id: 'field_y-10_z0', type: 'angular', theta_y_deg: -10, theta_z_deg: 0 },
            { id: 'field_y10_z0', type: 'angular', theta_y_deg: 10, theta_z_deg: 0 },
          ]
        : fields
    const wavelengths = request.wavelengths_nm ?? []
    const samples = request.ray_sampling?.samples_per_field ?? 1
    const total = Math.max(1, evaluatedFields.length * wavelengths.length * samples)
    await route.fulfill({
      json: {
        status: Array.from({ length: total }, () => 'alive'),
        sensor_y_mm: Array.from({ length: total }, (_, index) => index / 100),
        sensor_z_mm: Array.from({ length: total }, (_, index) => -index / 100),
        paths: Array.from({ length: total }, (_, index) => {
          const sampleIndex = index % samples
          const midpoint = (samples - 1) / 2
          const y = midpoint > 0 ? ((sampleIndex - midpoint) / midpoint) * 1.5 : 0
          const last = Math.max(1, registeredSurfaceIds.length - 1)
          return registeredSurfaceIds.map((surfaceId, surfaceIndex) => {
            const isImage = surfaceIndex === registeredSurfaceIds.length - 1
            const bend = y * (1 - surfaceIndex / (last + 1))
            const point = [isImage ? 103.5 : surfaceIndex * 3, isImage ? index / 100 : bend, isImage ? -index / 100 : 0]
            return { surface_id: surfaceId, point_mm: point, local_point_mm: [0, point[1], point[2]] }
          })
        }),
        metadata: {
          evaluated_fields: evaluatedFields,
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

async function expectLayoutRayPath(page: import('@playwright/test').Page, pointCount: number) {
  const rayPaths = page.locator('#layout-svg path.ray-line')
  await expect(rayPaths.first()).toBeVisible()
  const d = (await rayPaths.first().getAttribute('d')) ?? ''
  expect(d.split('L')).toHaveLength(pointCount)
  await expect(page.locator('#layout-svg line.ray-line')).toHaveCount(0)
}

async function layoutSurfaceScale(page: import('@playwright/test').Page, surfaceId: string) {
  const surface = page.locator(`#layout-svg [data-surface-id="${surfaceId}"]`)
  await expect(surface).toHaveCount(1)
  return {
    semiDiameterMm: Number(await surface.getAttribute('data-semi-diameter-mm')),
    visualHalfHeightPx: Number(await surface.getAttribute('data-visual-half-height-px')),
    rawHalfHeightPx: Number(await surface.getAttribute('data-raw-half-height-px')),
    clamped: (await surface.getAttribute('data-scale-clamped')) === 'true',
  }
}

async function selectPresetOption(page: import('@playwright/test').Page, label: string) {
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByRole('option', { name: new RegExp(label) }).click()
  await expect(page.getByRole('combobox', { name: 'Preset', exact: true })).toContainText(label)
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

test('group edits mark the optical system dirty and show range warnings', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await page.getByRole('tab', { name: 'System' }).click()
  await expect(page.getByText('Groups').first()).toBeVisible()
  await expect(page.getByTestId('group-row')).toHaveCount(2)
  await expect(page.getByText('Groups FOCUS_G and OIS_G overlap.')).toBeVisible()

  await page.getByRole('button', { name: 'Add group' }).click()
  await expect(page.getByTestId('group-row')).toHaveCount(3)
  await expect(page.getByTestId('system-dirty-status')).toContainText('system dirty')

  await page.locator('#group-from-2').selectOption('S3')
  await page.locator('#group-to-2').selectOption('S1')
  await expect(page.getByText('Group G3 starts after its end surface.')).toBeVisible()

  await page.getByRole('button', { name: 'Remove group' }).last().click()
  await expect(page.getByTestId('group-row')).toHaveCount(2)
})

test('layout view draws spherical surfaces as signed curves', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P002 N-BK7 Biconvex Singlet 50mm Demo').click()
  const p002Profiles = page.locator('#layout-svg path.surface-refractive')
  await expect(p002Profiles).toHaveCount(2)
  await expect(page.locator('#layout-svg path.glass-element')).toHaveCount(1)

  const firstProfile = (await p002Profiles.nth(0).getAttribute('d')) ?? ''
  const secondProfile = (await p002Profiles.nth(1).getAttribute('d')) ?? ''
  const firstNumbers = firstProfile.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? []
  const secondNumbers = secondProfile.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? []
  const firstXs = firstNumbers.filter((_, index) => index % 2 === 0)
  const secondXs = secondNumbers.filter((_, index) => index % 2 === 0)
  expect(firstXs[0]).toBeGreaterThan(firstXs[12])
  expect(secondXs[0]).toBeLessThan(secondXs[12])

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()
  await expect(page.locator('#layout-svg path.surface-refractive')).toHaveCount(3)
  await expect(page.locator('#layout-svg path.glass-element')).toHaveCount(2)
  await expect(page.locator('#layout-svg path.surface-cemented')).toHaveCount(1)
})

test('layout view uses trace path polylines when preview returns surface hits', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P002 N-BK7 Biconvex Singlet 50mm Demo').click()
  await page.getByRole('button', { name: 'Run Preview' }).click()

  await expectLayoutRayPath(page, 4)
})

test('P003 slider preview keeps layout rays on education preview surface paths', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await page.locator('#focus-shift-slider').evaluate((node) => {
    const input = node as HTMLInputElement
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, '1.5')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })

  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThanOrEqual(1)
  const dragPreview = previewRequests[previewRequests.length - 1] as { ray_sampling?: { samples_per_field?: number; ray_aiming?: { mode?: string } } }
  expect(dragPreview.ray_sampling?.samples_per_field).toBe(5)
  expect(dragPreview.ray_sampling?.ray_aiming?.mode).toBe('paraxial')
  await expectLayoutRayPath(page, 5)
  const totalRays = Number(await page.locator('#layout-svg').getAttribute('data-total-rays'))
  const displayedRays = Number(await page.locator('#layout-svg').getAttribute('data-displayed-rays'))
  expect(totalRays).toBeGreaterThan(displayedRays)
  expect(displayedRays).toBeLessThanOrEqual(36)
  const displayed = await page.locator('#layout-svg path.ray-line').evaluateAll((nodes) =>
    nodes.map((node) => ({
      field: Number(node.getAttribute('data-field-index')),
      stopY: Number(node.getAttribute('data-stop-y-mm')),
      role: node.getAttribute('data-sample-role'),
    })),
  )
  const stopYs = displayed.map((item) => item.stopY).filter(Number.isFinite)
  expect(Math.min(...stopYs)).toBeLessThan(0)
  expect(Math.max(...stopYs)).toBeGreaterThan(0)
  expect(Math.abs(Math.min(...stopYs) + Math.max(...stopYs))).toBeLessThan(1.0e-9)
  expect(new Set(displayed.map((item) => item.role))).toEqual(new Set(['lower', 'center', 'upper']))
  const fieldCounts = displayed.reduce<Record<number, number>>((counts, item) => {
    counts[item.field] = (counts[item.field] ?? 0) + 1
    return counts
  }, {})
  expect(new Set(Object.values(fieldCounts))).toEqual(new Set([9]))
  await expect(page.locator('#layout-svg path.ray-line.ray-f').first()).toBeVisible()
  await expect(page.locator('#layout-svg path.ray-line.ray-d').first()).toBeVisible()
  await expect(page.locator('#layout-svg path.ray-line.ray-c').first()).toBeVisible()
  const spotColors = await page.locator('#spot-svg circle.spot-point').evaluateAll((nodes) =>
    nodes.map((node) => ({
      wavelength: node.getAttribute('data-wavelength-nm'),
      fill: getComputedStyle(node).fill,
    })),
  )
  expect(new Set(spotColors.map((item) => item.wavelength))).toEqual(new Set(['486.13', '587.56', '656.27']))
  expect(new Set(spotColors.map((item) => item.fill))).toEqual(new Set(['rgb(15, 98, 254)', 'rgb(138, 116, 0)', 'rgb(218, 30, 40)']))
})

test('debug tab shows connected engine build info', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('tab', { name: 'Debug' }).click()

  const buildPanel = page.locator('.panel').filter({ has: page.getByRole('heading', { name: 'Build Info' }) })
  await expect(buildPanel).toBeVisible()
  await expect(buildPanel.getByText('git_commit', { exact: true })).toBeVisible()
  await expect(buildPanel.getByText('test-build', { exact: true })).toBeVisible()
  await expect(buildPanel.getByText('git_dirty', { exact: true })).toBeVisible()
  await expect(buildPanel.getByText('false', { exact: true })).toBeVisible()
})

test('layout view fixture draws even-aspheric sag differently from a sphere', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=asphere-layout')

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('F_ASPHERE Asphere Layout Visual Fixture').click()
  const profiles = page.locator('#layout-svg path.surface-refractive')
  await expect(profiles).toHaveCount(2)
  await expect(page.locator('#layout-svg')).toContainText('SPH')
  await expect(page.locator('#layout-svg')).toContainText('ASP')

  const sphericalProfile = (await profiles.nth(0).getAttribute('d')) ?? ''
  const asphericProfile = (await profiles.nth(1).getAttribute('d')) ?? ''
  const sphericalNumbers = sphericalProfile.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? []
  const asphericNumbers = asphericProfile.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? []
  const sphericalXs = sphericalNumbers.filter((_, index) => index % 2 === 0)
  const asphericXs = asphericNumbers.filter((_, index) => index % 2 === 0)
  const sphericalEdgeSagPx = sphericalXs[0] - sphericalXs[12]
  const asphericEdgeSagPx = asphericXs[0] - asphericXs[12]
  expect(asphericEdgeSagPx).toBeGreaterThan(sphericalEdgeSagPx + 8)
})

test('layout view keeps plane boundary elements and warns on negative edge thickness', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=asphere-layout')

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('F_EDGE_CASE Layout Edge Case Fixture').click()

  const glassElements = page.locator('#layout-svg path.glass-element')
  await expect(glassElements).toHaveCount(2)
  await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(1)
  await expect(page.locator('#layout-svg')).toContainText('PP1')
  await expect(page.locator('#layout-svg')).toContainText('PS2')

  const planePlaneElement = (await glassElements.nth(0).getAttribute('d')) ?? ''
  const planeSphereWarning = (await page.locator('#layout-svg path.glass-element-warning').getAttribute('d')) ?? ''
  expect(planePlaneElement).toContain('Z')
  expect(planeSphereWarning).toContain('Z')
})

test('layout view scales stop, sensor, and eye symbols from physical dimensions', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 8, visualHalfHeightPx: 32, rawHalfHeightPx: 32, clamped: false })
  expect(await layoutSurfaceScale(page, 'IMG')).toMatchObject({ semiDiameterMm: 12, visualHalfHeightPx: 48, rawHalfHeightPx: 48, clamped: false })
  await expect(page.locator('#layout-svg [data-surface-id="IMG"] rect.sensor-plane')).toHaveAttribute('height', '96')

  await selectPresetOption(page, 'P005 Coaxial Cassegrain Telescope Demo')
  expect(await layoutSurfaceScale(page, 'M1')).toMatchObject({ semiDiameterMm: 100, visualHalfHeightPx: 92, rawHalfHeightPx: 400, clamped: true })
  expect(await layoutSurfaceScale(page, 'IMG')).toMatchObject({ semiDiameterMm: 15, visualHalfHeightPx: 60, rawHalfHeightPx: 60, clamped: false })

  await selectPresetOption(page, 'P006 Keplerian Afocal Telescope Demo')
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 25, visualHalfHeightPx: 92, rawHalfHeightPx: 100, clamped: true })
  expect(await layoutSurfaceScale(page, 'EYE')).toMatchObject({ semiDiameterMm: 2, visualHalfHeightPx: 20, rawHalfHeightPx: 8, clamped: true })
})

test('right pane scrolls independently and keeps center pane stable', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  const rightPane = page.locator('.right-pane')
  const centerPane = page.locator('.center-pane')
  await expect(rightPane).toBeVisible()
  await expect(page.locator('#api-base')).toBeHidden()

  const initialRight = await rightPane.evaluate((node) => ({
    clientHeight: node.clientHeight,
    scrollHeight: node.scrollHeight,
    scrollTop: node.scrollTop,
  }))
  expect(initialRight.scrollHeight).toBeGreaterThan(initialRight.clientHeight)

  const before = await centerPane.boundingBox()
  await rightPane.evaluate((node) => {
    node.scrollTop = node.scrollHeight
  })
  const afterRight = await rightPane.evaluate((node) => ({ scrollTop: node.scrollTop }))
  const after = await centerPane.boundingBox()
  expect(afterRight.scrollTop).toBeGreaterThan(initialRight.scrollTop)
  expect(Math.abs((after?.y ?? 0) - (before?.y ?? 0))).toBeLessThan(1)

  await page.getByRole('button', { name: 'API' }).click()
  await expect(page.locator('#api-base')).toBeVisible()
})

test('ray count edits only change samples per field in preview requests', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')
  await page.locator('#pupil-distribution').selectOption('hexapolar')
  await page.locator('#aiming').selectOption('full')

  let fieldSignature = ''
  for (const [index, samples] of [5, 9, 15, 25].entries()) {
    await page.locator('#samples').fill(String(samples))
    await page.getByRole('button', { name: 'Run Preview' }).click()
    await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBe(index + 1)

    const request = previewRequests[index] as {
      fields?: Array<{ id: string; theta_y_deg: number; theta_z_deg: number }>
      wavelengths_nm?: number[]
      ray_sampling?: { samples_per_field?: number; pupil_distribution?: string; ray_aiming?: { mode?: string } }
    }
    expect(request.ray_sampling?.samples_per_field).toBe(samples)
    expect(request.ray_sampling?.pupil_distribution).toBe('hexapolar')
    expect(request.ray_sampling?.ray_aiming?.mode).toBe('full')
    const nextFieldSignature = JSON.stringify(request.fields)
    if (!fieldSignature) fieldSignature = nextFieldSignature
    expect(nextFieldSignature).toBe(fieldSignature)

    const expectedRayCount = (request.fields?.length ?? 0) * (request.wavelengths_nm?.length ?? 0) * samples
    await expect.poll(async () => Number(await page.locator('#layout-svg').getAttribute('data-total-rays')), { timeout: 3_000 }).toBe(expectedRayCount)
  }

  await page.getByRole('tab', { name: 'Debug' }).click()
  const summary = page.getByTestId('request-sampling-panel')
  await expect(summary).toContainText('25')
  await expect(summary).toContainText('hexapolar')
  await expect(summary).toContainText('full')
  await expect(summary).toContainText('center, edge-y, edge-z')
})

test('group motion sliders send runtime configuration through debounced preview', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await expect(page.getByText('Group Motion')).toBeVisible()
  await expect(page.locator('#focus-group')).toHaveValue('FOCUS_G')
  await page.locator('#focus-shift-slider').evaluate((node) => {
    const input = node as HTMLInputElement
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, '1.5')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })

  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThanOrEqual(1)
  const dragPreview = previewRequests[previewRequests.length - 1] as {
    configuration?: { zoom_position?: string; group_positions?: Record<string, { shift_x_mm?: number }> }
    ray_sampling?: { samples_per_field?: number; ray_aiming?: { mode?: string } }
  }
  expect(dragPreview.configuration?.zoom_position).toBe('infinity')
  expect(dragPreview.configuration?.group_positions?.FOCUS_G?.shift_x_mm).toBeCloseTo(1.5)
  expect(dragPreview.ray_sampling?.samples_per_field).toBe(5)
  expect(dragPreview.ray_sampling?.ray_aiming?.mode).toBe('paraxial')

  await page.locator('#focus-shift-slider').dispatchEvent('mouseup')
  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThanOrEqual(2)
  const commitPreview = previewRequests[previewRequests.length - 1] as {
    configuration?: { group_positions?: Record<string, { shift_x_mm?: number }> }
    ray_sampling?: { samples_per_field?: number }
  }
  expect(commitPreview.configuration?.group_positions?.FOCUS_G?.shift_x_mm).toBeCloseTo(1.5)
  expect(commitPreview.ray_sampling?.samples_per_field).toBe(9)
  await expect(page.getByTestId('analysis-dirty-status')).toContainText('clean')
})

test('aperture slider updates stop radius through debounced preview', async ({ page }) => {
  const previewRequests: unknown[] = []
  const registerRequests: unknown[] = []
  await mockEngine(page, { previewRequests, registerRequests })
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await page.getByRole('button', { name: 'Run Preview' }).click()
  await expect.poll(() => registerRequests.length, { timeout: 3_000 }).toBe(1)
  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThanOrEqual(1)
  const registeredSystem = registerRequests[0] as {
    surfaces?: Array<{ id?: string; aperture?: { semi_diameter_mm?: { variable?: string; default?: number } }; semi_diameter_mm?: { variable?: string; default?: number } }>
  }
  const registeredStop = registeredSystem.surfaces?.find((surface) => surface.id === 'STOP')
  expect(registeredStop?.semi_diameter_mm?.variable).toBe('iris_radius_mm')
  expect(registeredStop?.semi_diameter_mm?.default).toBeCloseTo(10)
  expect(registeredStop?.aperture?.semi_diameter_mm?.variable).toBe('iris_radius_mm')
  const initialPreviewCount = previewRequests.length
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 10, visualHalfHeightPx: 40, rawHalfHeightPx: 40, clamped: false })

  await expect(page.locator('#iris-radius-slider')).toBeVisible()
  await page.locator('#iris-radius-slider').evaluate((node) => {
    const input = node as HTMLInputElement
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, '5')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })

  await expect.poll(async () => (await layoutSurfaceScale(page, 'STOP')).visualHalfHeightPx, { timeout: 3_000 }).toBe(20)
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 5, visualHalfHeightPx: 20, rawHalfHeightPx: 20, clamped: false })
  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThan(initialPreviewCount)
  const dragPreview = previewRequests[previewRequests.length - 1] as {
    configuration?: { variables?: Record<string, number> }
    ray_sampling?: { samples_per_field?: number; ray_aiming?: { mode?: string } }
  }
  expect(dragPreview.configuration?.variables?.iris_radius_mm).toBeCloseTo(5)
  expect(dragPreview.ray_sampling?.samples_per_field).toBe(5)
  expect(dragPreview.ray_sampling?.ray_aiming?.mode).toBe('paraxial')
  expect(registerRequests.length).toBe(1)
  const dragPreviewCount = previewRequests.length

  await page.locator('#iris-radius-slider').dispatchEvent('mouseup')
  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThan(dragPreviewCount)
  const commitPreview = previewRequests[previewRequests.length - 1] as { configuration?: { variables?: Record<string, number> }; ray_sampling?: { samples_per_field?: number } }
  expect(commitPreview.configuration?.variables?.iris_radius_mm).toBeCloseTo(5)
  expect(commitPreview.ray_sampling?.samples_per_field).toBe(9)
  expect(registerRequests.length).toBe(1)
  await expect(page.getByTestId('system-dirty-status')).toHaveCount(0)
  await expect(page.getByTestId('analysis-dirty-status')).toContainText('clean')
})

test('decenter tilt sliders send configuration and expose evaluated symmetric fields', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await expect(page.locator('#decenter-tilt-group')).toHaveValue('OIS_G')
  await page.locator('#shift-y-slider').evaluate((node) => {
    const input = node as HTMLInputElement
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, '1.2')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await page.locator('#tilt-z-slider').evaluate((node) => {
    const input = node as HTMLInputElement
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, '2')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })

  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThanOrEqual(1)
  const dragPreview = previewRequests[previewRequests.length - 1] as {
    configuration?: {
      decenters?: Array<{ group?: string; shift_y_mm?: number }>
      tilts?: Array<{ group?: string; tilt_z_deg?: number; rotation_center?: { reference?: string } }>
    }
    ray_sampling?: { samples_per_field?: number; ray_aiming?: { mode?: string } }
  }
  expect(dragPreview.configuration?.decenters?.[0]?.group).toBe('OIS_G')
  expect(dragPreview.configuration?.decenters?.[0]?.shift_y_mm).toBeCloseTo(1.2)
  expect(dragPreview.configuration?.tilts?.[0]?.tilt_z_deg).toBeCloseTo(2)
  expect(dragPreview.configuration?.tilts?.[0]?.rotation_center?.reference).toBe('from_surface_vertex')
  expect(dragPreview.ray_sampling?.samples_per_field).toBe(5)
  expect(dragPreview.ray_sampling?.ray_aiming?.mode).toBe('paraxial')

  await page.locator('#tilt-z-slider').dispatchEvent('mouseup')
  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThanOrEqual(2)
  const commitPreview = previewRequests[previewRequests.length - 1] as { ray_sampling?: { samples_per_field?: number } }
  expect(commitPreview.ray_sampling?.samples_per_field).toBe(9)
  await expect(page.locator('#layout-svg .configured-dot')).toHaveCount(3)
  await expect(page.getByTestId('evaluated-fields')).toContainText('field_y-10_z0')
  await expect(page.getByTestId('evaluated-fields')).toContainText('field_y10_z0')
  await expect(page.getByTestId('analysis-dirty-status')).toContainText('clean')
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
  await expect(page.getByText('P002 N-BK7 Biconvex Singlet').first()).toBeVisible()
  await page.locator('#image-plane-policy-mode').selectOption('best_focus_rms')
  await expect(page.locator('#image-plane-policy-mode')).toHaveValue('best_focus_rms')
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
  await expect(page.locator('#image-plane-policy-mode')).toHaveValue('sweep')
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
  await expect(page.locator('#image-plane-policy-mode')).toHaveValue('sweep')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()
  await page.getByRole('tab', { name: 'Analysis' }).click()
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()

  await expect(page.getByText('partial').first()).toBeVisible()
  await expect(page.getByText('Partial Snapshot')).toBeVisible()
  await expect(page.getByText('Comparison falls back to summary data')).toBeVisible()
})
