import type {
  AnalysisField,
  BestFocusResponse,
  ChartAnalysisResult,
  EngineIssue,
  EngineMeta,
  FieldCurvatureRow,
  ImagePlanePolicy,
  OpticalSystem,
  TraceResponse,
  ValidationResult,
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
  options: { store_path: boolean; profiling: boolean }
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
  const [rayFan, distortion, fieldCurvature, msImageSurface, relativeIllumination, mtf] = await Promise.all([
    postAnalysis<ChartAnalysisResult['rayFan']>(apiBase, '/v1/analysis/ray-fan', {
      ...request,
      ray_sampling: { ...request.ray_sampling, pupil_distribution: 'fan_y' },
    }),
    postAnalysis<ChartAnalysisResult['distortion']>(apiBase, '/v1/analysis/distortion', request),
    postAnalysis<{ rows: FieldCurvatureRow[]; artifacts?: Record<string, string> }>(apiBase, '/v1/analysis/field-curvature', request),
    postAnalysis<{ rows: FieldCurvatureRow[] }>(apiBase, '/v1/analysis/ms-image-surface', request),
    postAnalysis<ChartAnalysisResult['relativeIllumination']>(apiBase, '/v1/analysis/relative-illumination', request),
    postAnalysis<ChartAnalysisResult['mtf']>(apiBase, '/v1/analysis/mtf', {
      ...request,
      frequencies_lp_per_mm: request.frequencies_lp_per_mm ?? [0, 10, 20, 40, 80],
    }),
  ])
  const msRowsByField = new Map((msImageSurface.rows ?? []).map((row) => [row.field_id, row]))
  return {
    rayFan,
    distortion,
    fieldCurvature: {
      rows: (fieldCurvature.rows ?? []).map((row) => ({ ...row, ...msRowsByField.get(row.field_id) })),
      artifacts: fieldCurvature.artifacts,
    },
    relativeIllumination,
    mtf: { points: mtf?.points ?? [], metadata: mtf?.metadata, artifacts: mtf?.artifacts, diffraction_included: false },
  }
}

export async function runBestFocus(apiBase: string, request: AnalysisRequest): Promise<BestFocusResponse> {
  return postAnalysis<BestFocusResponse>(apiBase, '/v1/solve/best-focus', request)
}
