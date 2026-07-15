import { expect, test } from '@playwright/test'

const expectedMtfFrequencies = Array.from({ length: 33 }, (_, index) => index * 2.5)
const expectedMtfSampling = {
  samples_per_field: 4096,
  pupil_distribution: 'grid',
  ray_aiming: { mode: 'paraxial' },
}

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
        api_schema_version: '2.5.0',
        result_schema_version: '2.5.0',
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
    const baselineRays = evaluatedFields.flatMap((field: { id?: string }, fieldIndex: number) =>
      wavelengths.flatMap((wavelength: number, wavelengthIndex: number) =>
        [
          { role: 'chief', y: 0 },
          { role: 'marginal_lower', y: -1.5 },
          { role: 'marginal_upper', y: 1.5 },
        ].map(({ role, y }) => {
          const last = Math.max(1, registeredSurfaceIds.length - 1)
          const blocked = registeredSurfaceIds.includes('M1') && role === 'marginal_upper'
          const pathSurfaceIds = blocked ? registeredSurfaceIds.slice(0, 2) : registeredSurfaceIds
          return {
            role,
            field_id: field.id ?? `field-${fieldIndex}`,
            field_index: fieldIndex,
            wavelength_nm: wavelength,
            wavelength_index: wavelengthIndex,
            status: blocked ? 'blocked' : role === 'chief' ? 'alive' : 'aiming_failed',
            stop_y_mm: y,
            aiming_ok: role === 'chief',
            aiming_iterations: 2,
            path: pathSurfaceIds.map((surfaceId, surfaceIndex) => {
              const isImage = surfaceIndex === pathSurfaceIds.length - 1 && !blocked
              const bend = y * (1 - surfaceIndex / (last + 1))
              const point = [isImage ? 103.5 : surfaceIndex * 3, isImage ? y / 3 : bend, 0]
              return { surface_id: surfaceId, point_mm: point, local_point_mm: [0, surfaceIndex === 0 ? y : point[1], 0], direction: [1, 0, 0] }
            }),
          }
        }),
      ),
    )
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
            return { surface_id: surfaceId, point_mm: point, local_point_mm: [0, point[1], point[2]], direction: [1, 0, 0] }
          })
        }),
        metadata: {
          evaluated_fields: evaluatedFields,
          wavelengths_nm: wavelengths,
          samples_per_field: samples,
          pupil_distribution: request.ray_sampling?.pupil_distribution,
          ray_aiming_mode: request.ray_sampling?.ray_aiming?.mode,
          layout_baseline_rays: request.options?.include_layout_baseline_rays ? baselineRays : [],
          paraxial: { paraxial_image_position_mm: 100, principal_plane_positions_mm: [null, 50] },
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
              status: request.ray_sampling?.ray_aiming?.mode === 'full' && pupil === -1 ? 'aiming_failed' : 'alive',
            })),
          ),
        ),
        metadata: { pupil_distribution: request.ray_sampling?.pupil_distribution },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/longitudinal-aberration', async (route) => {
    const request = route.request().postDataJSON()
    const fields = request.fields ?? []
    const wavelengths = request.wavelengths_nm ?? [587.56]
    await route.fulfill({
      json: {
        points: fields.flatMap((field: { id: string }) =>
          wavelengths.flatMap((wavelength: number, wavelengthIndex: number) =>
            [-1, 0, 1].map((pupil) => ({
              field_id: field.id,
              wavelength_nm: wavelength,
              pupil_y: pupil,
              pupil_z: 0,
              focus_x_y_mm: 100 + pupil * 0.03 + wavelengthIndex * 0.005,
              focus_x_z_mm: 100 + pupil * 0.02,
              longitudinal_error_y_mm: pupil * 0.03 + wavelengthIndex * 0.005,
              longitudinal_error_z_mm: pupil * 0.02,
              status: request.ray_sampling?.ray_aiming?.mode === 'full' && pupil === -1 ? 'aiming_failed' : 'alive',
            })),
          ),
        ),
        metadata: { pupil_distribution: 'fan_y', reference_x_mm: 100 },
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
  await page.route('http://127.0.0.1:8000/v1/analysis/mtf/through-focus', async (route) => {
    const request = route.request().postDataJSON()
    const fields = request.fields ?? []
    const frequencies = request.frequencies_lp_per_mm ?? [10, 30]
    const offsets = Array.from({ length: request.defocus_points ?? 21 }, (_, index) => -0.1 + index * 0.01)
    await route.fulfill({
      json: {
        points: fields.flatMap((field: { id: string; theta_y_deg: number; theta_z_deg: number }, fieldIndex: number) =>
          offsets.flatMap((defocus: number) => frequencies.map((frequency: number) => ({
            field_id: field.id,
            theta_y_deg: field.theta_y_deg,
            theta_z_deg: field.theta_z_deg,
            frequency_lp_per_mm: frequency,
            defocus_mm: defocus,
            mtf_meridional: Math.max(0, 0.9 - Math.abs(defocus - fieldIndex * 0.01) * 4 - frequency / 200),
            mtf_sagittal: Math.max(0, 0.86 - Math.abs(defocus + fieldIndex * 0.01) * 3 - frequency / 220),
          }))),
        ),
        metadata: { defocus_range_mm: 0.1, defocus_points: 21, diffraction_included: false },
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/white-mtf', async (route) => {
    const request = route.request().postDataJSON()
    const frequencies = request.frequencies_lp_per_mm ?? [0, 10, 20]
    const totalWeight = Object.values(request.wavelength_weights ?? {}).reduce((sum: number, weight) => sum + Number(weight), 0) || 1
    const wavelengthWeights = Object.fromEntries(Object.entries(request.wavelength_weights ?? {}).map(([wavelength, weight]) => [wavelength, Number(weight) / totalWeight]))
    await route.fulfill({
      json: {
        mtf: {
          points: frequencies.map((frequency: number) => ({
            frequency_lp_per_mm: frequency,
            mtf_y: Math.max(0, 1 - frequency / 95),
            mtf_z: Math.max(0, 1 - frequency / 115),
            mtf_radial: Math.max(0, 1 - frequency / 105),
          })),
        },
        wavelength_weights: wavelengthWeights,
      },
    })
  })
  await page.route('http://127.0.0.1:8000/v1/analysis/visual-composite', async (route) => {
    await route.fulfill({
      json: {
        instrument: { field_id: 'center', arrived_count: 5, centroid_theta_y_deg: 0, centroid_theta_z_deg: 0, angular_rms_deg: 0.001, residual_divergence_diopter: 0.01 },
        exit_pupil: { angular_magnification: -5, exit_pupil_diameter_mm: 10, eye_relief_mm: 24 },
        angular_mtf: { points: [{ frequency_cycles_per_degree: 0, mtf: 1 }, { frequency_cycles_per_degree: 10, mtf: 0.9 }] },
        retinal: { arrived_count: 5, blocked_count: 4, failed_count: 0, centroid_y_mm: -0.14743, centroid_z_mm: 0, rms_radius_mm: 0.022812 },
        retinal_psf: { total_energy: 5, centroid_y_mm: -0.14743, centroid_z_mm: 0, grid: [[1]] },
        retinal_mtf: { points: [{ frequency_lp_per_mm: 0, mtf_y: 1, mtf_z: 1, mtf_radial: 1 }] },
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

async function layoutSurfaceVertexX(page: import('@playwright/test').Page, surfaceId: string) {
  const surface = page.locator(`#layout-svg [data-surface-id="${surfaceId}"]`)
  await expect(surface).toHaveCount(1)
  return Number(await surface.getAttribute('data-vertex-x-mm'))
}

async function selectPresetOption(page: import('@playwright/test').Page, label: string) {
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByRole('option', { name: new RegExp(label) }).click()
  await expect(page.getByTestId('preset-selected-name')).toContainText(label)
}

async function openRuntimeControls(page: import('@playwright/test').Page) {
  const toggle = page.getByRole('button', { name: 'Runtime controls' })
  if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click()
}

test('visual composite switches between instrument and retinal results', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'V001 Simplified Gullstrand Eye Composite')
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.getByRole('button', { name: 'Run eye evaluation' }).click()
  const results = page.getByTestId('visual-composite-results')
  await expect(results.getByText('Angular spot RMS')).toBeVisible()
  await expect(results.getByText('24.0000 mm')).toBeVisible()
  await results.getByRole('tab', { name: 'Retinal' }).click()
  await expect(results.getByText('Retinal spot RMS')).toBeVisible()
  await expect(results.getByText('22.8120 µm')).toBeVisible()
})

async function layoutSurfaceBoxes(page: import('@playwright/test').Page) {
  return page.locator('#layout-svg [data-surface-id]').evaluateAll((nodes) =>
    nodes.map((node) => {
      const box = node.getBoundingClientRect()
      return {
        id: node.getAttribute('data-surface-id'),
        x: Number(box.x.toFixed(3)),
        width: Number(box.width.toFixed(3)),
        height: Number(box.height.toFixed(3)),
      }
    }),
  )
}

test('preset selector groups shipped presets by catalog metadata and id', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  const optionTexts = await page.getByRole('option').allTextContents()
  const presetIds = optionTexts.map((text) => /P\d{3}/.exec(text)?.[0]).filter((id): id is string => Boolean(id))
  expect(presetIds).toEqual(['P004', 'P007', 'P011', 'P012', 'P013', 'P001', 'P002', 'P003', 'P009', 'P010', 'P006', 'P008'])
  expect(optionTexts.join(' ')).not.toContain('P005')
})

test('preset ComboBox searches metadata, exposes categories, and supports keyboard selection', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  const combo = page.getByRole('combobox', { name: 'Preset', exact: true })
  await combo.fill('両凸単レンズ')
  await expect(page.getByRole('option', { name: /P002/ })).toBeVisible()
  await combo.press('Escape')

  await combo.fill('focus group')
  await expect(page.getByRole('option', { name: /P013/ })).toBeVisible()
  await expect(page.getByText('Photographic', { exact: true })).toBeVisible()
  await combo.press('ArrowDown')
  await combo.press('Enter')
  await expect(page.getByTestId('preset-selected-name')).toContainText('P013')
  await combo.press('Escape')
  await expect(page.getByRole('option').first()).toBeHidden()
})

test('preset full name remains readable in English, Japanese, and pseudo locales', async ({ page }) => {
  await mockEngine(page)
  for (const language of ['en', 'ja', 'pseudo']) {
    await page.goto(`/?lng=${language}`)
    const combo = page.locator('#preset')
    await combo.fill('P013')
    await page.getByRole('option', { name: /P013/ }).click()
    const size = await page.getByTestId('preset-selected-name').evaluate((node) => ({
      clientWidth: node.clientWidth,
      scrollWidth: node.scrollWidth,
      text: node.textContent ?? '',
    }))
    expect(size.text).toContain('P013')
    expect(size.scrollWidth).toBeLessThanOrEqual(size.clientWidth + 1)
  }
})

test('right pane context reduces R99 scroll excess on every workbench screen', async ({ page }) => {
  await mockEngine(page)
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/?lng=en')
  const r99Baseline: Record<string, number> = { System: 2379, Preview: 2387, Analysis: 2387, Compare: 2387, Debug: 2387 }

  const measured: Record<string, number> = {}
  for (const screen of Object.keys(r99Baseline)) {
    await page.getByRole('button', { name: screen, exact: true }).click()
    const excess = await page.locator('.right-pane').evaluate((node) => node.scrollHeight - node.clientHeight)
    measured[screen] = excess
    expect(excess, `${screen} right-pane excess`).toBeLessThan(r99Baseline[screen])
  }
  console.info('R100 right-pane scroll excess', measured)
  await test.info().attach('r100-right-pane-scroll.json', { body: JSON.stringify({ r99Baseline, measured }, null, 2), contentType: 'application/json' })
})

test('theme follows explicit selection, keeps contrast and wavelength identity, and persists', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  const contrastReport = async () => page.evaluate(() => {
    const root = document.querySelector('.app-theme') as HTMLElement
    const style = getComputedStyle(root)
    const parse = (value: string) => {
      const match = value.match(/#([0-9a-f]{6})/i)
      if (match) return [0, 2, 4].map((offset) => Number.parseInt(match[1].slice(offset, offset + 2), 16))
      return (value.match(/[\d.]+/g) ?? []).slice(0, 3).map(Number)
    }
    const luminance = (rgb: number[]) => {
      const linear = rgb.map((component) => {
        const value = component / 255
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    }
    const contrast = (left: string, right: string) => {
      const values = [luminance(parse(left)), luminance(parse(right))].sort((a, b) => b - a)
      return (values[0] + 0.05) / (values[1] + 0.05)
    }
    const bg = style.getPropertyValue('--ow-panel').trim()
    const text = style.getPropertyValue('--ow-text').trim()
    const waves = ['--ow-wave-f', '--ow-wave-d', '--ow-wave-e', '--ow-wave-c'].map((token) => style.getPropertyValue(token).trim())
    return { textContrast: contrast(text, bg), waveContrast: waves.map((color) => contrast(color, bg)), waves: waves.map(parse) }
  })

  await page.locator('#theme-preference').selectOption('dark')
  await expect(page.locator('html')).toHaveAttribute('data-color-scheme', 'dark')
  const dark = await contrastReport()
  expect(dark.textContrast).toBeGreaterThanOrEqual(4.5)
  dark.waveContrast.forEach((value) => expect(value).toBeGreaterThanOrEqual(3))
  expect(dark.waves[0][2]).toBeGreaterThan(dark.waves[0][0])
  expect(dark.waves[1][0]).toBeGreaterThan(dark.waves[1][2])
  expect(dark.waves[2][1]).toBeGreaterThan(dark.waves[2][0])
  expect(dark.waves[3][0]).toBeGreaterThan(dark.waves[3][1])

  await page.reload()
  await expect(page.locator('#theme-preference')).toHaveValue('dark')
  await expect(page.locator('html')).toHaveAttribute('data-color-scheme', 'dark')
  await page.locator('#theme-preference').selectOption('light')
  const light = await contrastReport()
  expect(light.textContrast).toBeGreaterThanOrEqual(4.5)
  light.waveContrast.forEach((value) => expect(value).toBeGreaterThanOrEqual(3))
})

test('R109 dark theme uses stronger semantic glass, air, and cemented-surface tokens', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')
  await selectPresetOption(page, 'P003 Achromat Doublet 100mm Demo')

  const readLayoutStyles = () => page.evaluate(() => {
    const root = document.querySelector('.app-theme') as HTMLElement
    const glass = document.querySelector('#layout-svg .glass-element') as SVGPathElement
    const cemented = document.querySelector('#layout-svg .surface-cemented') as SVGPathElement
    const layout = document.querySelector('#layout-svg') as SVGElement
    const style = getComputedStyle(root)
    return {
      glassFill: getComputedStyle(glass).fill,
      glassStroke: getComputedStyle(glass).stroke,
      cementedStroke: getComputedStyle(cemented).stroke,
      airFill: getComputedStyle(layout).backgroundColor,
      airStrokeToken: style.getPropertyValue('--ow-air-stroke').trim(),
    }
  })

  await page.locator('#theme-preference').selectOption('light')
  const light = await readLayoutStyles()
  expect(light).toEqual({
    glassFill: 'rgba(15, 98, 254, 0.08)',
    glassStroke: 'rgba(15, 98, 254, 0.36)',
    cementedStroke: 'rgb(69, 137, 255)',
    airFill: 'rgb(250, 250, 250)',
    airStrokeToken: '#8d8d8d',
  })

  await page.locator('#theme-preference').selectOption('dark')
  const dark = await readLayoutStyles()
  expect(dark).toEqual({
    glassFill: 'rgba(120, 169, 255, 0.22)',
    glassStroke: 'rgba(166, 200, 255, 0.78)',
    cementedStroke: 'rgb(166, 200, 255)',
    airFill: 'rgb(53, 53, 53)',
    airStrokeToken: '#a8a8a8',
  })
})

test('navigation and context defaults follow the R101 viewport thresholds', async ({ page }) => {
  await mockEngine(page)
  const assertShell = async (width: number, expanded: boolean, contextMode: 'fixed' | 'drawer') => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/?lng=en')
    await page.evaluate(() => window.localStorage.removeItem('optics-workbench-navigation-expanded'))
    await page.reload()
    const shell = page.locator('.workbench-grid')
    await expect(shell).toHaveAttribute('data-navigation-expanded', String(expanded))
    await expect(shell).toHaveAttribute('data-context-mode', contextMode)
  }

  await assertShell(1920, true, 'fixed')
  await assertShell(1440, true, 'fixed')
  await assertShell(1439, false, 'fixed')
  await assertShell(1367, false, 'fixed')
  await assertShell(1366, false, 'drawer')

  const rightPane = page.locator('.right-pane')
  await expect(rightPane).toHaveAttribute('aria-hidden', 'true')
  await page.getByRole('button', { name: 'Open context panel' }).click()
  await expect(rightPane).toHaveClass(/context-drawer-open/)
  await expect(rightPane).toHaveAttribute('aria-hidden', 'false')
})

test('navigation collapse persists across reload and keeps all views reachable', async ({ page }) => {
  await mockEngine(page)
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/?lng=en')
  await page.evaluate(() => window.localStorage.removeItem('optics-workbench-navigation-expanded'))
  await page.reload()

  await page.getByRole('button', { name: 'Collapse navigation' }).click()
  await expect(page.locator('.workbench-grid')).toHaveAttribute('data-navigation-expanded', 'false')
  for (const view of ['System', 'Preview', 'Analysis', 'Compare', 'Debug']) {
    await page.getByRole('button', { name: view, exact: true }).click()
    await expect(page.getByRole('button', { name: view, exact: true })).toHaveAttribute('aria-current', 'page')
  }

  await page.reload()
  await expect(page.locator('.workbench-grid')).toHaveAttribute('data-navigation-expanded', 'false')
})

test('navigation and context drawer transitions keep layout and chart dimensions stable', async ({ page }) => {
  await mockEngine(page)
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.goto('/?lng=en')
  await page.evaluate(() => window.localStorage.removeItem('optics-workbench-navigation-expanded'))
  await page.reload()

  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.getByRole('button', { name: 'Run Charts' }).click()
  const chart = page.getByTestId('longitudinal-aberration-chart')
  await expect(chart).toBeVisible()
  await page.getByRole('button', { name: 'Collapse navigation' }).click()
  await page.waitForTimeout(220)
  const chartAfter = await chart.boundingBox()
  await page.waitForTimeout(220)
  const chartSettled = await chart.boundingBox()
  expect(chartAfter).not.toBeNull()
  expect(chartSettled).toEqual(chartAfter)
  expect(chartSettled?.width ?? 0).toBeGreaterThan(200)
  expect(chartSettled?.height ?? 0).toBeGreaterThan(100)

  await page.setViewportSize({ width: 1366, height: 900 })
  await page.getByRole('button', { name: 'Preview', exact: true }).click()
  const layout = page.locator('#layout-svg')
  const beforeDrawer = await layout.boundingBox()
  await page.getByRole('button', { name: 'Open context panel' }).click()
  await page.waitForTimeout(220)
  const afterDrawer = await layout.boundingBox()
  expect(beforeDrawer).toEqual(afterDrawer)
  expect(afterDrawer?.width ?? 0).toBeGreaterThan(400)
})

test('R103 System workspace links row selection and debounced preview to the live mini layout', async ({ page }) => {
  const previewRequests: unknown[] = []
  const registerRequests: unknown[] = []
  await mockEngine(page, { previewRequests, registerRequests })
  await page.goto('/?lng=en&fixture=all-presets')
  await selectPresetOption(page, 'P005 Coaxial Cassegrain Telescope Demo')
  await page.getByRole('button', { name: 'System', exact: true }).click()

  const workspace = page.getByTestId('system-workspace')
  const miniLayout = page.locator('#system-mini-layout-svg')
  await expect(workspace).toBeVisible()
  await page.getByTestId('surface-row').filter({ hasText: 'M1' }).click()
  await expect(miniLayout.locator('[data-surface-id="M1"]')).toHaveAttribute('data-selected', 'true')

  const requestCount = previewRequests.length
  await page.locator('#surface-STOP-annulus-inner').fill('42')
  await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBeGreaterThan(requestCount)
  await expect(page.getByRole('button', { name: 'System', exact: true })).toHaveAttribute('aria-current', 'page')
  await expect(miniLayout.locator('[data-surface-id="STOP"]')).toHaveAttribute('data-selected', 'true')
  expect(registerRequests.at(-1)).toMatchObject({ surfaces: expect.arrayContaining([expect.objectContaining({ id: 'STOP' })]) })
})

test('R103 layout legend overlays without resizing the layout and result strip stays compact', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  const layout = page.locator('#layout-svg')
  const before = await layout.boundingBox()
  const legend = page.getByTestId('layout-legend-toggle')
  await legend.click()
  await expect(legend).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByTestId('layout-legend')).toBeVisible()
  const after = await layout.boundingBox()
  expect(after).toEqual(before)
  await expect(page.getByTestId('compact-result-strip')).toBeVisible()
  const strip = await page.getByTestId('compact-result-strip').boundingBox()
  expect(strip?.height ?? 0).toBeLessThan(190)
  await legend.click()
  await expect(legend).toHaveAttribute('aria-expanded', 'false')
})

test('R103 snapshot save stays in place and toast action opens Compare', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('button', { name: 'Run Preview' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()

  await expect(page.getByRole('button', { name: 'Preview', exact: true })).toHaveAttribute('aria-current', 'page')
  const toast = page.getByTestId('snapshot-toast')
  await expect(toast).toContainText('snapshot-1')
  await toast.getByRole('button', { name: 'Open in Compare' }).click()
  await expect(page.getByRole('button', { name: 'Compare', exact: true })).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('.snapshot-row').filter({ hasText: 'snapshot-1' })).toBeVisible()
})

test('R110 expanded spot modal preserves layout size and distinguishes fields and wavelengths', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')
  await selectPresetOption(page, 'P003 Achromat Doublet 100mm Demo')
  await page.getByRole('button', { name: 'Run Preview' }).click()

  const layout = page.locator('#layout-svg')
  const compactSpot = page.locator('#spot-svg')
  const before = await layout.boundingBox()
  const compactBox = await compactSpot.boundingBox()
  await page.getByTestId('expand-spot-button').click()

  const expanded = page.getByTestId('spot-expanded-content')
  await expect(expanded).toBeVisible()
  const expandedBox = await page.locator('#spot-svg-expanded').boundingBox()
  expect(expandedBox?.width ?? 0).toBeGreaterThan((compactBox?.width ?? 0) * 2)
  expect(expandedBox?.width ?? 0).toBeGreaterThan(500)
  await expect(expanded.getByTestId('spot-field-legend-item')).toHaveCount(3)
  await expect(expanded.getByTestId('spot-wavelength-legend-item')).toHaveCount(3)
  await expect(expanded.locator('#spot-svg-expanded .spot-field-0')).not.toHaveCount(0)
  await expect(expanded.locator('#spot-svg-expanded .spot-field-1')).not.toHaveCount(0)
  await expect(expanded.locator('#spot-svg-expanded .spot-field-2')).not.toHaveCount(0)
  expect(await layout.boundingBox()).toEqual(before)

  await page.getByRole('button', { name: 'Close', exact: true }).click()
  await expect(expanded).toBeHidden()
  expect(await layout.boundingBox()).toEqual(before)
})

test('shipped preset selection resets fields to recommended values', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')

  await page.locator('#field-2-theta-y').fill('20')
  const expected = [
    ['P002 N-BK7 Biconvex Singlet 50mm Demo', '9.900092', '14'],
    ['P001 Ideal Thin Lens 50mm F4', '12.813585', '18'],
    ['P003 Achromat Doublet 100mm Demo', '7.036366', '10'],
    ['P004 Double Gauss 50mm F1.4 Demo', '7.036366', '10'],
    ['P005 Coaxial Cassegrain Telescope Demo', '0.196001', '0.28'],
    ['P006 Keplerian Afocal Telescope Demo', '0.5', '1'],
    ['P007 Fast Positive-Negative Meniscus Pair 50mm Demo', '1.050122', '1.5'],
  ]
  for (const [presetName, middle, edge] of expected) {
    await selectPresetOption(page, presetName)
    await expect(page.locator('#field-0-id')).toHaveValue('center')
    await expect(page.locator('#field-1-id')).toHaveValue('mid-y')
    await expect(page.locator('#field-2-id')).toHaveValue('edge-y')
    await expect(page.locator('#field-1-theta-y')).toHaveValue(middle)
    await expect(page.locator('#field-2-theta-y')).toHaveValue(edge)
    const expectedMidLabel = presetName.includes('P006') ? 'Field ID' : '70% Image Height Field ID'
    await expect(page.locator('label[for="field-1-id"]')).toHaveText(expectedMidLabel)
  }
})

test('P005 System table displays and edits annulus outer and inner radii', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')
  await selectPresetOption(page, 'P005 Coaxial Cassegrain Telescope Demo')
  await page.getByRole('button', { name: 'System', exact: true }).click()

  const editor = page.getByTestId('annulus-radius-editor')
  await expect(editor).toHaveCount(1)
  await expect(page.locator('#surface-STOP-annulus-outer')).toHaveValue('100')
  await expect(page.locator('#surface-STOP-annulus-inner')).toHaveValue('40')
  await page.locator('#surface-STOP-annulus-inner').fill('42')
  await expect(page.getByTestId('system-dirty-status')).toContainText('dirty')
  await expect(page.locator('#surface-STOP-annulus-inner')).toHaveValue('42')

  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')
  await expect(page.getByTestId('annulus-radius-editor')).toHaveCount(0)
})

test('P009 System table displays configured conic and asphere coefficients', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P009 N-BK7 Aspheric Singlet 50mm Demo')
  await page.getByRole('button', { name: 'System', exact: true }).click()

  const table = page.locator('table.surface-table')
  await expect(table.locator('thead')).toContainText('Asphere')
  const asp1 = table.locator('tbody tr').filter({ hasText: 'ASP1' })
  await expect(asp1.locator('[data-column-id="asphere"]')).toHaveText('k=-1.1792, A4=-0.0000024992')
  const spherical = table.locator('tbody tr').filter({ hasText: 'S2' })
  await expect(spherical.locator('[data-column-id="asphere"]')).toHaveText('-')
})

test('analysis condition edits mark dirty and rerun preview with updated results', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await expect(page.getByText('Optics Workbench')).toBeVisible()
  await expect(page.getByTestId('analysis-dirty-status')).toContainText('clean')
  await expect(page.getByText('Theta Y and Theta Z specify directions to objects at infinity.')).toBeVisible()

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

  await page.getByRole('button', { name: 'System', exact: true }).click()
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

test('R114 surface labels stay bounded and stable across ten preview redraws', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en&fixture=all-presets')
  await selectPresetOption(page, 'P004 Double Gauss 50mm F1.4 Demo')
  await page.getByRole('button', { name: 'Preview', exact: true }).click()

  const readLabelCoordinates = () => page.locator('#layout-svg [data-surface-id] .surface-label').evaluateAll((nodes) =>
    nodes.map((node) => ({
      id: node.parentElement?.getAttribute('data-surface-id'),
      row: Number(node.getAttribute('data-label-row')),
      y: Number(node.getAttribute('data-label-y')),
    })),
  )
  const initial = await readLabelCoordinates()
  expect(Math.max(...initial.map((label) => label.row))).toBeLessThanOrEqual(2)
  expect(Math.max(...initial.map((label) => label.y))).toBeLessThan(340)

  for (let redraw = 0; redraw < 10; redraw += 1) {
    const requestCount = previewRequests.length
    await page.getByRole('button', { name: 'Run Preview' }).click()
    await expect.poll(() => previewRequests.length).toBeGreaterThan(requestCount)
    expect(await readLabelCoordinates()).toEqual(initial)
  }
})

test('layout view uses trace path polylines when preview returns surface hits', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P002 N-BK7 Biconvex Singlet 50mm Demo').click()
  await page.getByRole('button', { name: 'Run Preview' }).click()

  await expectLayoutRayPath(page, 5)
  await expect(page.getByTestId('layout-paraxial-image-marker')).toBeVisible()
  await expect(page.getByTestId('layout-principal-plane-marker')).toHaveCount(1)
})

test('layout view legend explains ray, wavelength, element, and marker styles', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')

  await page.getByTestId('layout-legend-toggle').click()
  const legend = page.getByTestId('layout-legend')
  await expect(legend).toBeVisible()
  await expect(legend).toContainText('Chief ray')
  await expect(legend).toContainText('Marginal ray')
  await expect(legend).toContainText('Density ray')
  await expect(legend).toContainText('F line')
  await expect(legend).toContainText('d/e line')
  await expect(legend).toContainText('C line')
  await expect(legend).toContainText('Glass region')
  await expect(legend).toContainText('Air gap')
  await expect(legend).toContainText('Cemented surface')
  await expect(legend).toContainText('Reflecting surface')
  await expect(legend).toContainText("F' focus marker")
  await expect(legend).toContainText('H1/H2 principal plane')
  await expect(legend).toContainText('STOP')
  await expect(legend.locator('.legend-stop')).toHaveCount(1)
  await expect(legend.locator('.legend-annulus')).toHaveCount(0)
  await expect(legend).toContainText('IMG')
  await expect(legend.locator('.legend-line.ray-f')).toHaveCSS('border-top-color', 'rgb(15, 98, 254)')
  await expect(legend.locator('.legend-line.ray-d')).toHaveCSS('border-top-color', 'rgb(25, 128, 56)')
  await expect(legend.locator('.legend-line.ray-c')).toHaveCSS('border-top-color', 'rgb(218, 30, 40)')

  await selectPresetOption(page, 'P005 Coaxial Cassegrain Telescope Demo')
  await expect(legend).toContainText('Annulus STOP (secondary-mirror central obstruction)')
  await expect(legend.locator('.legend-stop')).toHaveCount(0)
  await expect(legend.locator('.legend-annulus')).toHaveCount(1)
})

test('P005 preview renders baseline paths through both mirrors and the image plane', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P005 Coaxial Cassegrain Telescope Demo').click()
  await page.getByRole('button', { name: 'Run Preview' }).click()
  const baseline = page.locator('#layout-svg path[data-ray-layer="baseline"]')
  await expect(baseline).toHaveCount(9)
  await expect(baseline.first()).toHaveCSS('stroke-width', '2.1px')
  const blockedPaths = page.locator('#layout-svg path[data-ray-layer="baseline"][data-baseline-status="blocked"]')
  await expect(blockedPaths).toHaveCount(3)
  await expect(blockedPaths.first()).toHaveCSS('stroke', 'rgb(111, 111, 111)')
  await expect(blockedPaths.first()).toHaveCSS('stroke-dasharray', '3px, 2px')
  await expect(page.locator('#layout-svg [data-ray-end-marker="blocked"]')).toHaveCount(3)
  await page.getByTestId('layout-legend-toggle').click()
  await expect(page.getByTestId('layout-legend')).toContainText('Vignetted ray')
  const paths = await baseline.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('d') ?? ''))
  expect(paths.every((path) => (path.match(/L/g) ?? []).length >= 2)).toBe(true)
  expect(paths.every((path) => path.startsWith('M 36 '))).toBe(true)
  await expect(page.locator('#layout-svg')).toHaveAttribute('data-object-plane-x-mm', '-780')
  const mirrors = page.locator('#layout-svg path.surface-mirror')
  await expect(mirrors).toHaveCount(3)
  const m1Segments = page.locator('#layout-svg [data-surface-id="M1"] path.surface-mirror')
  await expect(m1Segments).toHaveCount(2)
  const m1Widths = await m1Segments.evaluateAll((nodes) => nodes.map((node) => node.getBBox().width))
  expect(m1Widths.every((width) => width > 1 && width < 1.2)).toBe(true)
  const m1SegmentBoxes = await m1Segments.evaluateAll((nodes) => nodes
    .map((node) => {
      const box = node.getBBox()
      return { y: box.y, height: box.height }
    })
    .sort((a, b) => a.y - b.y))
  expect(m1SegmentBoxes[1].y - (m1SegmentBoxes[0].y + m1SegmentBoxes[0].height)).toBeGreaterThan(70)
  const m2Profile = page.locator('#layout-svg [data-surface-id="M2"] path.surface-mirror')
  await expect(m2Profile).toHaveCount(1)
  expect((await m2Profile.evaluate((node) => node.getBBox().width))).toBeGreaterThan(0.35)
  expect((await m2Profile.evaluate((node) => node.getBBox().width))).toBeLessThan(0.45)
  await expect(page.locator('#layout-svg [data-surface-id="M1"]')).toHaveAttribute('data-radius-mm', '-2000')
  await expect(page.locator('#layout-svg [data-surface-id="M1"]')).toHaveAttribute('data-mirror-incident-sign', '1')
  await expect(page.locator('#layout-svg [data-surface-id="M2"]')).toHaveAttribute('data-radius-mm', '-1050')
  await expect(page.locator('#layout-svg [data-surface-id="M2"]')).toHaveAttribute('data-mirror-incident-sign', '-1')
  const lengths = await baseline.evaluateAll((nodes) => nodes.map((node) => (node as SVGPathElement).getTotalLength()))
  expect(lengths.every((length) => length > 0)).toBe(true)
})

test('P003 slider preview keeps layout rays on education preview surface paths', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()
  await page.locator('#show-density-rays').setChecked(true, { force: true })

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
  await expectLayoutRayPath(page, 6)
  const totalRays = Number(await page.locator('#layout-svg').getAttribute('data-total-rays'))
  const densityRays = Number(await page.locator('#layout-svg').getAttribute('data-density-rays'))
  expect(totalRays).toBeGreaterThan(densityRays)
  expect(densityRays).toBeLessThanOrEqual(36)
  const displayed = await page.locator('#layout-svg path[data-ray-layer="density"]').evaluateAll((nodes) =>
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
  const spot = page.locator('#spot-svg')
  const spotPointCount = Number(await spot.getAttribute('data-point-count'))
  const expectedMarker = spotPointCount <= 6 ? { radius: 2.7, opacity: 0.85 }
    : spotPointCount <= 24 ? { radius: 2.2, opacity: 0.78 }
      : spotPointCount <= 60 ? { radius: 1.7, opacity: 0.68 }
        : { radius: 1.3, opacity: 0.58 }
  await expect(spot).toHaveAttribute('data-marker-radius', String(expectedMarker.radius))
  await expect(spot).toHaveAttribute('data-marker-opacity', String(expectedMarker.opacity))
})

test('debug tab shows connected engine build info', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('button', { name: 'Debug', exact: true }).click()

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
  await page.goto('/?lng=en&fixture=all-presets')

  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 8, visualHalfHeightPx: 32, rawHalfHeightPx: 32, clamped: false })
  const circleMarker = page.locator('#layout-svg [data-surface-id="STOP"] .stop-circle-marker')
  await expect(circleMarker).toHaveCount(1)
  await expect(circleMarker).toHaveAttribute('data-stop-min-visual-length-px', '4')
  const circleSegments = circleMarker.locator('.stop-aperture-segment')
  await expect(circleSegments).toHaveCount(2)
  const circleRanges = await circleSegments.evaluateAll((nodes) => nodes.map((node) => {
    const line = node as SVGLineElement
    return {
      sign: Number(line.dataset.stopSign),
      innerRadiusPx: Number(line.dataset.stopInnerRadiusPx),
      outerRadiusPx: Number(line.dataset.stopOuterRadiusPx),
      minY: Math.min(line.y1.baseVal.value, line.y2.baseVal.value),
      maxY: Math.max(line.y1.baseVal.value, line.y2.baseVal.value),
    }
  }))
  expect(circleRanges.find((item) => item.sign === -1)).toMatchObject({ innerRadiusPx: 0, outerRadiusPx: 32, minY: 138, maxY: 170 })
  expect(circleRanges.find((item) => item.sign === 1)).toMatchObject({ innerRadiusPx: 0, outerRadiusPx: 32, minY: 170, maxY: 202 })
  await expect(circleMarker.locator('.stop-dot')).toHaveCount(1)
  expect(await layoutSurfaceScale(page, 'IMG')).toMatchObject({ semiDiameterMm: 18, visualHalfHeightPx: 72, rawHalfHeightPx: 72, clamped: false })
  await expect(page.locator('#layout-svg [data-surface-id="IMG"] rect.sensor-plane')).toHaveAttribute('height', '144')

  await selectPresetOption(page, 'P005 Coaxial Cassegrain Telescope Demo')
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 100, visualHalfHeightPx: 92, rawHalfHeightPx: 400, clamped: true })
  await expect(page.locator('#layout-svg [data-surface-id="STOP"]')).toHaveAttribute('data-annulus-inner-semi-diameter-mm', '40')
  await expect(page.locator('#layout-svg [data-surface-id="STOP"] .stop-obscuration')).toHaveCount(0)
  await expect(page.locator('#layout-svg [data-surface-id="STOP"] .stop-annulus-marker')).toHaveCount(1)
  await expect(page.locator('#layout-svg [data-surface-id="STOP"] .stop-annulus-marker')).toHaveAttribute('data-stop-min-visual-length-px', '4')
  const annulusSegments = page.locator('#layout-svg [data-surface-id="STOP"] .stop-aperture-segment')
  await expect(annulusSegments).toHaveCount(2)
  await expect(page.locator('#layout-svg [data-surface-id="STOP"] .stop-dot')).toHaveCount(0)
  await expect(page.locator('#layout-svg [data-surface-id="STOP"] .surface-aperture_stop')).toHaveCount(0)
  await page.getByTestId('layout-legend-toggle').click()
  await expect(page.getByTestId('layout-legend').locator('.legend-stop')).toHaveCount(0)
  await expect(page.getByTestId('layout-legend')).toContainText('Annulus STOP')
  expect(await layoutSurfaceVertexX(page, 'STOP')).toBe(0)
  expect(await layoutSurfaceVertexX(page, 'M1')).toBe(80)
  expect(await layoutSurfaceVertexX(page, 'M2')).toBe(-570)
  expect(await layoutSurfaceVertexX(page, 'IMG')).toBe(480)
  expect(Number(await page.locator('#layout-svg').getAttribute('data-ray-y-scale'))).toBeCloseTo(0.92)
  expect(await layoutSurfaceScale(page, 'M1')).toMatchObject({ semiDiameterMm: 100, visualHalfHeightPx: 92, rawHalfHeightPx: 400, clamped: true })
  await expect(page.locator('#layout-svg [data-surface-id="M1"]')).toHaveAttribute('data-central-hole-semi-diameter-mm', '40')
  const p005M2Scale = await layoutSurfaceScale(page, 'M2')
  expect(p005M2Scale).toMatchObject({ semiDiameterMm: 40, rawHalfHeightPx: 160, clamped: true })
  expect(p005M2Scale.visualHalfHeightPx).toBeCloseTo(36.8)
  const p005Stop = page.locator('#layout-svg [data-surface-id="STOP"]')
  expect(Number(await p005Stop.getAttribute('data-annulus-inner-radius-px'))).toBeCloseTo(p005M2Scale.visualHalfHeightPx)
  expect(Number(await p005Stop.getAttribute('data-annulus-outer-radius-px'))).toBeCloseTo(92)
  const stopSegments = await annulusSegments.evaluateAll((nodes) => nodes.map((node) => {
    const line = node as SVGLineElement
    return {
      sign: Number(line.dataset.stopSign),
      innerRadiusPx: Number(line.dataset.stopInnerRadiusPx),
      outerRadiusPx: Number(line.dataset.stopOuterRadiusPx),
      physicalLengthPx: Number(line.dataset.stopPhysicalLengthPx),
      visualLengthPx: Number(line.dataset.stopVisualLengthPx),
      minY: Math.min(line.y1.baseVal.value, line.y2.baseVal.value),
      maxY: Math.max(line.y1.baseVal.value, line.y2.baseVal.value),
      height: Math.abs(line.y2.baseVal.value - line.y1.baseVal.value),
    }
  }))
  expect(stopSegments.map((item) => item.sign).sort()).toEqual([-1, 1])
  stopSegments.forEach((item) => {
    expect(item.innerRadiusPx).toBeCloseTo(36.8)
    expect(item.outerRadiusPx).toBeCloseTo(92)
    expect(item.physicalLengthPx).toBeCloseTo(55.2)
    expect(item.visualLengthPx).toBeCloseTo(55.2)
    expect(item.height).toBeCloseTo(55.2)
  })
  const negativeAnnulusSegment = stopSegments.find((item) => item.sign === -1)
  const positiveAnnulusSegment = stopSegments.find((item) => item.sign === 1)
  expect(negativeAnnulusSegment?.minY).toBeCloseTo(78)
  expect(negativeAnnulusSegment?.maxY).toBeCloseTo(133.2)
  expect(positiveAnnulusSegment?.minY).toBeCloseTo(206.8)
  expect(positiveAnnulusSegment?.maxY).toBeCloseTo(262)
  expect(await layoutSurfaceScale(page, 'IMG')).toMatchObject({ semiDiameterMm: 15, visualHalfHeightPx: 20, rawHalfHeightPx: 60, clamped: true })

  await selectPresetOption(page, 'P006 Keplerian Afocal Telescope Demo')
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 25, visualHalfHeightPx: 92, rawHalfHeightPx: 100, clamped: true })
  expect(await layoutSurfaceScale(page, 'EYE')).toMatchObject({ semiDiameterMm: 2, visualHalfHeightPx: 20, rawHalfHeightPx: 8, clamped: true })
})

test('P007 fast meniscus pair preset renders strong positive and negative curvature', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P007 Fast Positive-Negative Meniscus Pair 50mm Demo')

  const profiles = page.locator('#layout-svg path.surface-refractive')
  await expect(profiles).toHaveCount(4)
  await expect(page.locator('#layout-svg path.glass-element')).toHaveCount(2)
  await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(0)
  await expect(page.locator('#layout-svg')).toContainText('S1')
  await expect(page.locator('#layout-svg')).toContainText('S4')
  expect(await layoutSurfaceScale(page, 'STOP')).toMatchObject({ semiDiameterMm: 13.2, visualHalfHeightPx: 52.8, rawHalfHeightPx: 52.8, clamped: false })

  const positiveProfile = (await profiles.nth(0).getAttribute('d')) ?? ''
  const negativeProfile = (await profiles.nth(2).getAttribute('d')) ?? ''
  const positiveXs = positiveProfile.match(/-?\d+(?:\.\d+)?/g)?.map(Number).filter((_, index) => index % 2 === 0) ?? []
  const negativeXs = negativeProfile.match(/-?\d+(?:\.\d+)?/g)?.map(Number).filter((_, index) => index % 2 === 0) ?? []
  expect(positiveXs[0]).toBeGreaterThan(positiveXs[12])
  expect(negativeXs[0]).toBeLessThan(negativeXs[12])

  await page.getByRole('button', { name: 'Run Preview' }).click()
  await expectLayoutRayPath(page, 7)
  expect(Number(await page.locator('#layout-svg').getAttribute('data-total-rays'))).toBe(81)
})

test('P004 Double Gauss renders eight powered surfaces and traces to the image plane', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P004 Double Gauss 50mm F1.4 Demo')

  await expect(page.locator('#layout-svg path.surface-refractive')).toHaveCount(8)
  await expect(page.locator('#layout-svg path.glass-element')).toHaveCount(4)
  await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(0)
  await page.getByRole('button', { name: 'Run Preview' }).click()
  await expectLayoutRayPath(page, 11)
  expect(Number(await page.locator('#layout-svg').getAttribute('data-total-rays'))).toBe(81)
})

test('P011 Planar Double Gauss renders six elements with two cemented interfaces', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P011 Planar-Type 6-Element Double Gauss 50mm F1.4 Demo')

  await expect(page.locator('#layout-svg path.surface-refractive')).toHaveCount(10)
  await expect(page.locator('#layout-svg path.surface-cemented')).toHaveCount(2)
  await expect(page.locator('#layout-svg path.glass-element')).toHaveCount(6)
  await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(0)
  await page.getByRole('button', { name: 'Run Preview' }).click()
  await expectLayoutRayPath(page, 13)
  expect(Number(await page.locator('#layout-svg').getAttribute('data-total-rays'))).toBe(81)
})

test('P012 Tessar renders four elements in three groups and traces without vignetting', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P012 Tessar-Type 50mm F2.8 Demo')

  await expect(page.locator('#layout-svg path.surface-refractive')).toHaveCount(7)
  await expect(page.locator('#layout-svg path.surface-cemented')).toHaveCount(1)
  await expect(page.locator('#layout-svg path.glass-element')).toHaveCount(4)
  await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(0)
  await page.getByRole('button', { name: 'Run Preview' }).click()
  await expectLayoutRayPath(page, 10)
  expect(Number(await page.locator('#layout-svg').getAttribute('data-total-rays'))).toBe(81)
})

test('P013 focused Double Gauss renders seven elements and traces to the image plane', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P013 7-Element Modified Double Gauss 50mm F1.4 Focus Demo')

  await expect(page.locator('#layout-svg path.surface-refractive')).toHaveCount(13)
  await expect(page.locator('#layout-svg path.surface-cemented')).toHaveCount(1)
  await expect(page.locator('#layout-svg path.glass-element')).toHaveCount(7)
  await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(0)
  await page.getByRole('button', { name: 'Run Preview' }).click()
  await expectLayoutRayPath(page, 16)
  expect(Number(await page.locator('#layout-svg').getAttribute('data-total-rays'))).toBe(81)
})

test('shipped presets keep layout glass fills free of edge-thickness warnings', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')

  const labels = [
    'P001 Ideal Thin Lens 50mm F4',
    'P002 N-BK7 Biconvex Singlet 50mm Demo',
    'P003 Achromat Doublet 100mm Demo',
    'P005 Coaxial Cassegrain Telescope Demo',
    'P006 Keplerian Afocal Telescope Demo',
    'P007 Fast Positive-Negative Meniscus Pair 50mm Demo',
  ]
  for (const label of labels) {
    await selectPresetOption(page, label)
    await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(0)
  }
})

test('shipped presets keep layout scale stable after preview response', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en&fixture=all-presets')

  const labels = [
    'P001 Ideal Thin Lens 50mm F4',
    'P002 N-BK7 Biconvex Singlet 50mm Demo',
    'P003 Achromat Doublet 100mm Demo',
    'P005 Coaxial Cassegrain Telescope Demo',
    'P006 Keplerian Afocal Telescope Demo',
    'P007 Fast Positive-Negative Meniscus Pair 50mm Demo',
  ]
  for (const label of labels) {
    await selectPresetOption(page, label)
    const before = await layoutSurfaceBoxes(page)
    await page.getByRole('button', { name: 'Run Preview' }).click()
    await expect.poll(async () => Number(await page.locator('#layout-svg').getAttribute('data-total-rays')), { timeout: 3_000 }).toBeGreaterThan(0)
    const after = await layoutSurfaceBoxes(page)
    expect(after.map((item) => item.id)).toEqual(before.map((item) => item.id))
    for (const [index, afterBox] of after.entries()) {
      expect(Math.abs(afterBox.x - before[index].x)).toBeLessThan(1)
      expect(Math.abs(afterBox.width - before[index].width)).toBeLessThan(1)
      expect(Math.abs(afterBox.height - before[index].height)).toBeLessThan(1)
    }
    await expect(page.locator('#layout-svg path.glass-element-warning')).toHaveCount(0)
  }
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

  await page.getByRole('button', { name: 'Debug', exact: true }).click()
  const summary = page.getByTestId('request-sampling-panel')
  await expect(summary).toContainText('25')
  await expect(summary).toContainText('hexapolar')
  await expect(summary).toContainText('full')
  await expect(summary).toContainText('center, mid-y, edge-y')
})

test('layout baseline chief and marginal rays are stable across ray counts', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')

  const signatures: string[] = []
  for (const [index, samples] of [5, 9, 15, 25].entries()) {
    await page.locator('#samples').fill(String(samples))
    await page.getByRole('button', { name: 'Run Preview' }).click()
    await expect.poll(() => previewRequests.length, { timeout: 3_000 }).toBe(index + 1)

    const request = previewRequests[index] as { options?: { include_layout_baseline_rays?: boolean } }
    expect(request.options?.include_layout_baseline_rays).toBe(true)
    await expect.poll(async () => Number(await page.locator('#layout-svg').getAttribute('data-baseline-rays')), { timeout: 3_000 }).toBeGreaterThan(0)

    const baseline = await page.locator('#layout-svg path[data-ray-layer="baseline"]').evaluateAll((nodes) =>
      nodes.map((node) => ({
        role: node.getAttribute('data-baseline-role'),
        status: node.getAttribute('data-baseline-status'),
        field: Number(node.getAttribute('data-field-index')),
        wavelength: Number(node.getAttribute('data-wavelength-index')),
        stopY: Number(node.getAttribute('data-stop-y-mm')),
      })),
    )
    expect(new Set(baseline.map((item) => item.role))).toEqual(new Set(['chief', 'marginal_lower', 'marginal_upper']))
    expect(new Set(baseline.map((item) => item.status))).toEqual(new Set(['alive', 'aiming_failed']))
    expect(baseline.filter((item) => item.role?.startsWith('marginal_')).length).toBeGreaterThan(0)
    signatures.push(JSON.stringify(baseline))
  }

  expect(new Set(signatures).size).toBe(1)
  await expect(page.locator('#show-density-rays')).not.toBeChecked()
  await expect(page.locator('#layout-svg path[data-ray-layer="density"]')).toHaveCount(0)
  await page.getByRole('button', { name: 'System', exact: true }).click()
  await expect(page.locator('#system-mini-layout-svg')).toHaveAttribute('data-density-rays', '0')
  await expect.poll(async () => Number(await page.locator('#system-mini-layout-svg').getAttribute('data-baseline-rays')), { timeout: 3_000 }).toBeGreaterThan(0)
  await page.getByRole('button', { name: 'Preview', exact: true }).click()
  await page.locator('#show-density-rays').setChecked(true, { force: true })
  await expect.poll(async () => Number(await page.locator('#layout-svg').getAttribute('data-density-rays')), { timeout: 3_000 }).toBeGreaterThan(0)
  await page.locator('#show-density-rays').setChecked(false, { force: true })
  await expect(page.locator('#layout-svg path[data-ray-layer="density"]')).toHaveCount(0)
  await expect.poll(async () => Number(await page.locator('#layout-svg').getAttribute('data-baseline-rays')), { timeout: 3_000 }).toBeGreaterThan(0)
})

test('group motion sliders send runtime configuration through debounced preview', async ({ page }) => {
  const previewRequests: unknown[] = []
  await mockEngine(page, { previewRequests })
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()
  await openRuntimeControls(page)

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
  await openRuntimeControls(page)

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
  await openRuntimeControls(page)

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

  await page.locator('#shift-y-slider').evaluate((node) => {
    const input = node as HTMLInputElement
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, '4.5')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await expect(page.getByText('Possible vignetting')).toBeVisible()
})

test('P002 and P003 analysis charts render standard aberration panels without collapsed labels', async ({ page }) => {
  await mockEngine(page)
  for (const preset of ['P002 N-BK7 Biconvex Singlet 50mm Demo', 'P003 Achromat Doublet 100mm Demo']) {
    await page.goto('/?lng=en')
    await selectPresetOption(page, preset)

    await page.getByRole('button', { name: 'Analysis', exact: true }).click()
    await page.getByRole('button', { name: 'Run Charts' }).click()

    await expect(page.getByTestId('analysis-chart-grid')).toBeVisible()
    await expect(page.getByText('Longitudinal Aberration Standard Panels').first()).toBeVisible()
    await expect(page.getByTestId('standard-aberration-grid')).toBeVisible()
    await expect(page.getByTestId('longitudinal-aberration-chart')).toBeVisible()
    await expect(page.getByTestId('standard-field-curvature-chart')).toBeVisible()
    await expect(page.getByTestId('standard-distortion-chart')).toBeVisible()
    await expect(page.getByText('focus shift mm').first()).toBeVisible()
    await expect(page.getByText('pupil coordinate').first()).toBeVisible()
    await expect(page.getByText('half field deg').first()).toBeVisible()
    await expect(page.getByText('distortion %').first()).toBeVisible()
    await expect(page.getByText('Ray Fan').first()).toBeVisible()
    await expect(page.getByText('Distortion').first()).toBeVisible()
    await expect(page.getByText('Field Curvature').first()).toBeVisible()
    await expect(page.getByText('Relative Illumination').first()).toBeVisible()
    await expect(page.getByText('MTF').first()).toBeVisible()
    await expect(page.getByText('Diffraction included: false')).toBeVisible()
    await expect(page.getByTestId('longitudinal-aberration-chart').locator('circle')).toHaveCount(9)
    await expect(page.getByTestId('ray-fan-y-chart').locator('circle')).toHaveCount(27)
    await expect(page.getByTestId('ray-fan-z-chart').locator('circle')).toHaveCount(27)
    await expect(page.getByTestId('mtf-chart').locator('circle')).toHaveCount(198)
    await expect(page.getByTestId('ray-fan-y-chart')).toHaveAttribute('data-point-count', '27')
    await expect(page.getByTestId('ray-fan-y-chart')).toHaveAttribute('data-marker-radius', '1.7')
    await expect(page.getByTestId('ray-fan-y-chart')).toHaveAttribute('data-marker-opacity', '0.68')
    await expect(page.getByTestId('standard-field-curvature-chart')).toHaveAttribute('data-point-count', '32')
    await expect(page.getByTestId('standard-distortion-chart')).toHaveAttribute('data-point-count', '16')
    await expect(page.getByTestId('distortion-chart')).toHaveAttribute('data-point-count', '16')
    await expect(page.getByTestId('field-curvature-chart')).toHaveAttribute('data-point-count', '32')
    await expect(page.getByTestId('relative-illumination-chart')).toHaveAttribute('data-point-count', '16')
    await expect(page.getByTestId('standard-distortion-chart')).toHaveAttribute('data-marker-radius', '2.2')
    await expect(page.getByTestId('standard-distortion-chart')).toHaveAttribute('data-marker-opacity', '0.78')
    for (const legend of ['center M', 'center S', 'mid-y M', 'mid-y S', 'edge-y M', 'edge-y S']) {
      await expect(page.getByTestId('mtf-chart').locator('..').getByText(legend, { exact: true })).toBeVisible()
    }

    const labelBoxes = await page.getByTestId('standard-aberration-grid').locator('.plot-label').evaluateAll((nodes) =>
      nodes.map((node) => {
        const rect = node.getBoundingClientRect()
        return { width: rect.width, height: rect.height }
      }),
    )
    expect(labelBoxes).toHaveLength(6)
    for (const box of labelBoxes) {
      expect(box.width).toBeGreaterThan(5)
      expect(box.height).toBeGreaterThan(5)
    }
  }
})

test('P002 through-focus MTF renders one four-series panel per recommended field', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.getByTestId('analysis-view-switcher').getByRole('tab', { name: 'Through-focus MTF' }).click()
  await page.getByRole('button', { name: 'Run Charts' }).click()

  const view = page.getByTestId('through-focus-mtf-view')
  await expect(view).toBeVisible()
  for (const fieldId of ['center', 'mid-y', 'edge-y']) {
    const panel = page.getByTestId(`through-focus-panel-${fieldId}`)
    const chart = page.getByTestId(`through-focus-chart-${fieldId}`)
    await expect(panel).toBeVisible()
    await expect(chart).toHaveAttribute('data-point-count', '84')
    await expect(chart).toHaveAttribute('data-x-domain-min', '-0.1')
    await expect(chart).toHaveAttribute('data-x-domain-max', '0.1')
    await expect(chart).toHaveAttribute('data-y-domain-min', '0')
    await expect(chart).toHaveAttribute('data-y-domain-max', '1')
    for (const legend of ['M @ 10 lp/mm', 'S @ 10 lp/mm', 'M @ 30 lp/mm', 'S @ 30 lp/mm']) {
      await expect(panel.getByText(legend, { exact: true })).toBeVisible()
    }
    await expect(chart.locator('polyline[stroke-dasharray="6 4"]')).toHaveCount(2)
  }
})

test('curve analyses keep dense fields separate from ray fan and MTF frequency sampling', async ({ page }) => {
  const requests: Array<{ endpoint: string; body: Record<string, unknown> }> = []
  page.on('request', (request) => {
    const endpoint = new URL(request.url()).pathname
    if (
      ['/v1/analysis/distortion', '/v1/analysis/field-curvature', '/v1/analysis/ms-image-surface', '/v1/analysis/relative-illumination', '/v1/analysis/ray-fan', '/v1/analysis/mtf'].includes(endpoint)
    ) {
      requests.push({ endpoint, body: request.postDataJSON() })
    }
  })
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.getByRole('button', { name: 'Run Charts' }).click()
  await expect(page.getByTestId('analysis-chart-grid')).toBeVisible()

  const curveEndpoints = [
    '/v1/analysis/distortion',
    '/v1/analysis/field-curvature',
    '/v1/analysis/ms-image-surface',
    '/v1/analysis/relative-illumination',
  ]
  for (const endpoint of curveEndpoints) {
    const request = requests.find((candidate) => candidate.endpoint === endpoint)
    expect(request, `${endpoint} request`).toBeDefined()
    const fields = request?.body.fields as Array<{ id: string; theta_y_deg: number; theta_z_deg: number }>
    expect(fields).toHaveLength(16)
    expect(fields.map((field) => field.theta_y_deg)).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9.900092, 10, 11, 12, 13, 14])
    expect(fields.find((field) => field.theta_y_deg === 0)?.id).toBe('center')
    expect(fields.find((field) => field.theta_y_deg === 9.900092)?.id).toBe('mid-y')
    expect(fields.find((field) => field.theta_y_deg === 14)?.id).toBe('edge-y')
    expect(fields.every((field) => field.theta_z_deg === 0)).toBe(true)
  }

  const relativeIlluminationRequest = requests.find((request) => request.endpoint === '/v1/analysis/relative-illumination')
  expect(relativeIlluminationRequest?.body.ray_sampling).toEqual({
    samples_per_field: 1000,
    pupil_distribution: 'grid',
    ray_aiming: { mode: 'paraxial' },
  })

  const rayFanRequests = requests.filter((request) => request.endpoint === '/v1/analysis/ray-fan')
  expect(rayFanRequests).toHaveLength(2)
  for (const request of rayFanRequests) {
    expect(request.body.fields).toHaveLength(3)
  }
  const mtfRequests = requests.filter((request) => request.endpoint === '/v1/analysis/mtf')
  expect(mtfRequests).toHaveLength(3)
  for (const request of mtfRequests) {
    expect(request.body.fields).toHaveLength(1)
    expect(request.body.frequencies_lp_per_mm).toEqual(expectedMtfFrequencies)
    expect(request.body.ray_sampling).toEqual(expectedMtfSampling)
  }
})

test('MTF mode switches between monochromatic and weighted white-light endpoints', async ({ page }) => {
  const mtfRequests: Array<{ url: string; body: Record<string, unknown> }> = []
  page.on('request', (request) => {
    if (request.url().endsWith('/v1/analysis/mtf') || request.url().endsWith('/v1/analysis/white-mtf')) {
      mtfRequests.push({ url: request.url(), body: request.postDataJSON() })
    }
  })
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P002 N-BK7 Biconvex Singlet 50mm Demo')
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()

  const modeControl = page.getByTestId('mtf-mode-control')
  await expect(modeControl.getByRole('tab', { name: 'Monochromatic' })).toHaveAttribute('aria-selected', 'true')
  await modeControl.getByRole('tab', { name: 'White light' }).click()
  await page.getByRole('button', { name: 'Run Charts' }).click()

  await expect(page.getByText('White light', { exact: true }).last()).toBeVisible()
  await expect(page.getByText('White-light MTF uses the wavelength weights from the analysis conditions. Unit: lp/mm.')).toBeVisible()
  for (const legend of ['white center M', 'white center S', 'white mid-y M', 'white mid-y S', 'white edge-y M', 'white edge-y S']) {
    await expect(page.getByTestId('mtf-chart').locator('..').getByText(legend, { exact: true })).toBeVisible()
  }
  const whiteRequests = mtfRequests.filter((request) => request.url.endsWith('/v1/analysis/white-mtf'))
  expect(whiteRequests).toHaveLength(3)
  expect(Array.isArray(whiteRequests[0].body.wavelength_weights)).toBe(false)
  expect(whiteRequests[0].body.wavelength_weights).toEqual({ '486.13': 0.5, '587.56': 1, '656.27': 0.5 })
  for (const request of whiteRequests) expect(request.body.ray_sampling).toEqual(expectedMtfSampling)
  expect(whiteRequests.every((request) => JSON.stringify(request.body.frequencies_lp_per_mm) === JSON.stringify(expectedMtfFrequencies))).toBe(true)
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-point-count', '198')
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-x-domain-min', '0')
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-x-domain-max', '80')
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-y-domain-min', '0')
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-y-domain-max', '1')
  await expect(page.getByTestId('mtf-chart').locator('.plot-tick')).toHaveText(['0.00', '80.00', '0.00', '1.00'])

  await modeControl.getByRole('tab', { name: 'Monochromatic' }).click()
  await page.getByRole('button', { name: 'Run Charts' }).click()
  await expect(page.getByText('Monochromatic', { exact: true }).last()).toBeVisible()
  await expect(page.getByTestId('mtf-chart').locator('..').getByText('center M', { exact: true })).toBeVisible()
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-x-domain-min', '0')
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-x-domain-max', '80')
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-y-domain-min', '0')
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-y-domain-max', '1')
  await expect(page.getByTestId('mtf-chart').locator('.plot-tick')).toHaveText(['0.00', '80.00', '0.00', '1.00'])
  const monochromaticRequests = mtfRequests.filter((request) => request.url.endsWith('/v1/analysis/mtf'))
  expect(monochromaticRequests).toHaveLength(3)
  for (const request of monochromaticRequests) expect(request.body.ray_sampling).toEqual(expectedMtfSampling)
  expect(monochromaticRequests.every((request) => JSON.stringify(request.body.frequencies_lp_per_mm) === JSON.stringify(expectedMtfFrequencies))).toBe(true)
  await expect(page.getByTestId('mtf-chart')).toHaveAttribute('data-point-count', '198')
})

test('P007 full aiming reports excluded failures in ray fan and longitudinal panels', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await selectPresetOption(page, 'P007 Fast Positive-Negative Meniscus Pair 50mm')
  await page.locator('#aiming').selectOption('full')
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.getByRole('button', { name: 'Run Charts' }).click()

  await expect(page.getByTestId('longitudinal-aiming-warning')).toContainText('aiming_failed detected')
  await expect(page.getByTestId('longitudinal-aiming-warning')).toContainText('Excluded from the plotted curve: 3 ray(s).')
  await expect(page.getByTestId('ray-fan-aiming-warning')).toContainText('aiming_failed detected')
  await expect(page.getByTestId('ray-fan-aiming-warning')).toContainText('fan_y: 9, fan_z: 9 ray(s).')
  await expect(page.getByTestId('longitudinal-aberration-chart').locator('circle')).toHaveCount(6)
  await expect(page.getByTestId('ray-fan-y-chart').locator('circle')).toHaveCount(18)
  await expect(page.getByTestId('ray-fan-z-chart').locator('circle')).toHaveCount(18)
})

test('image-plane policy solves focus, writes back sensor, and disables for afocal preset', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P002 N-BK7 Biconvex Singlet 50mm Demo').click()
  await expect(page.getByText('P002 N-BK7 Biconvex Singlet').first()).toBeVisible()
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
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
  await page.getByRole('button', { name: 'Debug', exact: true }).click()
  await expect(page.getByText('"thickness_after_mm": 46.92')).toBeVisible()

  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P006 Keplerian Afocal Telescope Demo').click()
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await expect(page.locator('#image-plane-policy-mode')).toBeDisabled()
  await expect(page.getByTestId('image-plane-policy-panel')).toContainText('Image-plane policy applies only to focal systems with a sensor.')
})

test('snapshots embed artifacts and compare two saved conditions', async ({ page }) => {
  await mockEngine(page)
  await page.goto('/?lng=en')
  await page.getByRole('combobox', { name: 'Preset', exact: true }).click()
  await page.getByText('P003 Achromat Doublet 100mm Demo').click()

  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.locator('#image-plane-policy-mode').selectOption('sweep')
  await expect(page.locator('#image-plane-policy-mode')).toHaveValue('sweep')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()
  await page.getByTestId('snapshot-toast').getByRole('button', { name: 'Open in Compare' }).click()
  await expect(page.locator('.snapshot-row').filter({ hasText: 'snapshot-1' })).toBeVisible()

  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.locator('#field-0-theta-y').fill('3')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()
  await page.getByTestId('snapshot-toast').getByRole('button', { name: 'Open in Compare' }).click()

  await expect(page.getByTestId('compare-view')).toContainText('Condition Diff')
  await expect(page.getByTestId('compare-view')).toContainText('Result Compare')
  await expect(page.getByText('Comparison guard')).toBeVisible()
  await expect(page.getByText('focus curve').first()).toBeVisible()
})

test('partial snapshots fall back when embedded artifact retrieval fails', async ({ page }) => {
  await mockEngine(page, { failArtifacts: true })
  await page.goto('/?lng=en')
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.locator('#image-plane-policy-mode').selectOption('sweep')
  await expect(page.locator('#image-plane-policy-mode')).toHaveValue('sweep')
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()
  await page.getByTestId('snapshot-toast').getByRole('button', { name: 'Open in Compare' }).click()
  await page.getByRole('button', { name: 'Analysis', exact: true }).click()
  await page.getByRole('button', { name: 'Solve Image Plane' }).click()
  await page.getByRole('button', { name: 'Save Snapshot' }).click()
  await page.getByTestId('snapshot-toast').getByRole('button', { name: 'Open in Compare' }).click()

  await expect(page.getByText('partial').first()).toBeVisible()
  await expect(page.getByText('Partial Snapshot')).toBeVisible()
  await expect(page.getByText('Comparison falls back to summary data')).toBeVisible()
})
