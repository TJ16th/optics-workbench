import type {
  AnalysisField,
  BestFocusResponse,
  ChartAnalysisResult,
  EngineIssue,
  EngineMeta,
  FieldCurvatureRow,
  ImagePlanePolicy,
  OpticalSystem,
  RuntimeConfiguration,
  TraceResponse,
  ValidationResult,
  VisualCompositeResponse,
  WavelengthSample,
} from '../domain/types'

export const defaultApiBase = 'http://127.0.0.1:8000'

export class EngineApiError extends Error {
  issue: EngineIssue

  constructor(issue: EngineIssue, status: number) {
    super(issue.message_en || `${issue.code}: ${status}`)
    this.name = 'EngineApiError'
    this.issue = issue
  }
}

async function readJson<T>(response: Response, fallbackCode: string): Promise<T> {
  const payload = await response.json().catch(() => undefined)
  if (!response.ok) {
    const issue = payload && typeof payload === 'object' && 'code' in payload
      ? (payload as EngineIssue)
      : {
          code: fallbackCode,
          params: { status: response.status },
          message_en: `${fallbackCode}: ${response.status}`,
          severity: 'error' as const,
        }
    throw new EngineApiError(issue, response.status)
  }
  return payload as T
}

async function readArtifact(response: Response, fallbackCode: string): Promise<unknown> {
  if (!response.ok) {
    const payload = await response.json().catch(() => undefined)
    const issue = payload && typeof payload === 'object' && 'code' in payload
      ? (payload as EngineIssue)
      : {
          code: fallbackCode,
          params: { status: response.status },
          message_en: `${fallbackCode}: ${response.status}`,
          severity: 'error' as const,
        }
    throw new EngineApiError(issue, response.status)
  }
  const contentType = response.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) return response.json()
  return response.arrayBuffer()
}

export async function getHealth(apiBase: string): Promise<{ status: string }> {
  const response = await fetch(`${apiBase}/v1/health`)
  return readJson(response, 'api_error')
}

export async function getMeta(apiBase: string): Promise<EngineMeta> {
  const response = await fetch(`${apiBase}/v1/meta`)
  return readJson(response, 'api_error')
}

export async function validateSystem(apiBase: string, system: OpticalSystem): Promise<ValidationResult> {
  const response = await fetch(`${apiBase}/v1/systems/validate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(system),
  })
  return readJson(response, 'api_error')
}

export async function registerSystem(apiBase: string, system: OpticalSystem): Promise<{ system_id: string; system_hash: string }> {
  const response = await fetch(`${apiBase}/v1/systems/register`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(system),
  })
  return readJson(response, 'api_error')
}

export async function fetchArtifact(apiBase: string, uri: string): Promise<unknown> {
  const match = /^artifact:\/\/([^/]+)\/(.+)$/.exec(uri)
  if (!match) throw new EngineApiError({ code: 'artifact_not_found', params: { uri }, message_en: `Invalid artifact URI ${uri}`, severity: 'error' }, 404)
  const [, category, id] = match
  const response = await fetch(`${apiBase}/v1/artifacts/${encodeURIComponent(category)}/${encodeURIComponent(id)}`)
  return readArtifact(response, 'artifact_not_found')
}

export type PreviewRequest = {
  system_id: string
  fields: AnalysisField[]
  ray_sampling: {
    samples_per_field: number
    pupil_distribution: string
    ray_aiming: { mode: string }
  }
  wavelengths_nm: number[]
  wavelength_weights?: WavelengthSample[]
  configuration?: RuntimeConfiguration
  options: { store_path: boolean; profiling: boolean; include_layout_baseline_rays?: boolean }
}

export async function runPreview(apiBase: string, request: PreviewRequest): Promise<TraceResponse> {
  const response = await fetch(`${apiBase}/v1/education/preview`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(request),
  })
  return readJson(response, 'api_error')
}

export type AnalysisRequest = PreviewRequest & {
  frequencies_lp_per_mm?: number[]
  image_plane_policy?: ImagePlanePolicy
}

async function postAnalysis<T>(apiBase: string, endpoint: string, request: AnalysisRequest): Promise<T> {
  const response = await fetch(`${apiBase}${endpoint}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(request),
  })
  return readJson(response, 'api_error')
}

export async function runChartAnalyses(apiBase: string, request: AnalysisRequest): Promise<ChartAnalysisResult> {
  const axialField = [...request.fields].sort(
    (left, right) => Math.hypot(left.theta_y_deg ?? 0, left.theta_z_deg ?? 0) - Math.hypot(right.theta_y_deg ?? 0, right.theta_z_deg ?? 0),
  )[0]
  const mtfFields = request.fields.length ? request.fields : [undefined]
  const [rayFanY, rayFanZ, longitudinal, distortion, fieldCurvature, msImageSurface, relativeIllumination, mtfByField] = await Promise.all([
    postAnalysis<ChartAnalysisResult['rayFan']>(apiBase, '/v1/analysis/ray-fan', {
      ...request,
      ray_sampling: { ...request.ray_sampling, pupil_distribution: 'fan_y' },
    }),
    postAnalysis<ChartAnalysisResult['rayFan']>(apiBase, '/v1/analysis/ray-fan', {
      ...request,
      ray_sampling: { ...request.ray_sampling, pupil_distribution: 'fan_z' },
    }),
    postAnalysis<ChartAnalysisResult['longitudinal']>(apiBase, '/v1/analysis/longitudinal-aberration', {
      ...request,
      fields: axialField ? [axialField] : request.fields,
      ray_sampling: { ...request.ray_sampling, pupil_distribution: 'fan_y' },
    }),
    postAnalysis<ChartAnalysisResult['distortion']>(apiBase, '/v1/analysis/distortion', request),
    postAnalysis<{ rows: FieldCurvatureRow[]; artifacts?: Record<string, string> }>(apiBase, '/v1/analysis/field-curvature', request),
    postAnalysis<{ rows: FieldCurvatureRow[] }>(apiBase, '/v1/analysis/ms-image-surface', request),
    postAnalysis<ChartAnalysisResult['relativeIllumination']>(apiBase, '/v1/analysis/relative-illumination', request),
    Promise.all(
      mtfFields.map((field) =>
        postAnalysis<ChartAnalysisResult['mtf']>(apiBase, '/v1/analysis/mtf', {
          ...request,
          ...(field ? { fields: [field] } : {}),
          frequencies_lp_per_mm: request.frequencies_lp_per_mm ?? [0, 10, 20, 40, 80],
        }),
      ),
    ),
  ])
  const msRowsByField = new Map((msImageSurface.rows ?? []).map((row) => [row.field_id, row]))
  const mtfPoints = mtfByField.flatMap((result, index) =>
    (result?.points ?? []).map((point) => ({ ...point, field_id: mtfFields[index]?.id })),
  )
  return {
    rayFan: {
      points: rayFanY?.points ?? [],
      fan_y_points: rayFanY?.points ?? [],
      fan_z_points: rayFanZ?.points ?? [],
      metadata: rayFanY?.metadata,
      artifacts: rayFanY?.artifacts,
    },
    longitudinal,
    distortion,
    fieldCurvature: {
      rows: (fieldCurvature.rows ?? []).map((row) => ({ ...row, ...msRowsByField.get(row.field_id) })),
      artifacts: fieldCurvature.artifacts,
    },
    relativeIllumination,
    mtf: { points: mtfPoints, metadata: mtfByField[0]?.metadata, artifacts: mtfByField[0]?.artifacts, diffraction_included: false },
  }
}

export async function runBestFocus(apiBase: string, request: AnalysisRequest): Promise<BestFocusResponse> {
  return postAnalysis<BestFocusResponse>(apiBase, '/v1/solve/best-focus', request)
}

export async function runVisualComposite(apiBase: string, request: AnalysisRequest): Promise<VisualCompositeResponse> {
  return postAnalysis<VisualCompositeResponse>(apiBase, '/v1/analysis/visual-composite', request)
}
