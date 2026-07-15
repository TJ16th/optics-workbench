import type {
  AnalysisField,
  BestFocusResponse,
  ChartAnalysisResult,
  EngineIssue,
  EngineMeta,
  FieldCurvatureRow,
  ImagePlanePolicy,
  MtfMode,
  MtfPoint,
  OpticalSystem,
  RuntimeConfiguration,
  TraceResponse,
  ThroughFocusMtfResult,
  ValidationResult,
  VisualCompositeResponse,
  WavelengthSample,
} from '../domain/types'

export const defaultApiBase = 'http://127.0.0.1:8000'
export const DEFAULT_MTF_FREQUENCIES_LP_PER_MM = Array.from({ length: 33 }, (_, index) => index * 2.5)

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
  relative_illumination_sampling?: PreviewRequest['ray_sampling']
}

type WhiteMtfResponse = {
  mtf: { points: MtfPoint[]; metadata?: Record<string, unknown>; artifacts?: Record<string, string> }
  wavelength_weights: Record<string, number>
  metadata?: Record<string, unknown>
}

async function postAnalysis<T>(apiBase: string, endpoint: string, request: object, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBase}${endpoint}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  return readJson(response, 'api_error')
}

const CURVE_ANALYSIS_SAMPLE_COUNT = 15
const DEFAULT_RELATIVE_ILLUMINATION_SAMPLING: PreviewRequest['ray_sampling'] = {
  samples_per_field: 1000,
  pupil_distribution: 'grid',
  ray_aiming: { mode: 'paraxial' },
}
const DEFAULT_MTF_SAMPLING: PreviewRequest['ray_sampling'] = {
  samples_per_field: 4096,
  pupil_distribution: 'grid',
  ray_aiming: { mode: 'paraxial' },
}

function fieldCoordinateKey(field: Pick<AnalysisField, 'theta_y_deg' | 'theta_z_deg'>) {
  return `${field.theta_y_deg.toFixed(12)}:${field.theta_z_deg.toFixed(12)}`
}

export function buildCurveAnalysisFields(fields: AnalysisField[]): AnalysisField[] {
  if (!fields.length) return []
  const maxField = fields.reduce((current, field) =>
    Math.hypot(field.theta_y_deg, field.theta_z_deg) > Math.hypot(current.theta_y_deg, current.theta_z_deg) ? field : current,
  )
  if (Math.hypot(maxField.theta_y_deg, maxField.theta_z_deg) <= Number.EPSILON) {
    return fields.map((field) => ({ ...field }))
  }

  const byCoordinate = new Map<string, AnalysisField>()
  for (let index = 0; index < CURVE_ANALYSIS_SAMPLE_COUNT; index += 1) {
    const fraction = index / (CURVE_ANALYSIS_SAMPLE_COUNT - 1)
    const field: AnalysisField = {
      id: `curve-${String(index + 1).padStart(2, '0')}`,
      type: 'angular',
      theta_y_deg: maxField.theta_y_deg * fraction,
      theta_z_deg: maxField.theta_z_deg * fraction,
    }
    byCoordinate.set(fieldCoordinateKey(field), field)
  }
  for (const field of fields) {
    byCoordinate.set(fieldCoordinateKey(field), { ...field })
  }
  return [...byCoordinate.values()].sort(
    (left, right) => Math.hypot(left.theta_y_deg, left.theta_z_deg) - Math.hypot(right.theta_y_deg, right.theta_z_deg),
  )
}

export function chartAnalysisRequestCount(request: AnalysisRequest) {
  return 7 + Math.max(1, request.fields.length)
}

export async function runChartAnalyses(
  apiBase: string,
  request: AnalysisRequest,
  mtfMode: MtfMode = 'monochromatic',
  options: { signal?: AbortSignal; onProgress?: (completed: number, total: number) => void } = {},
): Promise<ChartAnalysisResult> {
  const axialField = [...request.fields].sort(
    (left, right) => Math.hypot(left.theta_y_deg ?? 0, left.theta_z_deg ?? 0) - Math.hypot(right.theta_y_deg ?? 0, right.theta_z_deg ?? 0),
  )[0]
  const mtfFields = request.fields.length ? request.fields : [undefined]
  const curveRequest = { ...request, fields: buildCurveAnalysisFields(request.fields) }
  const wavelengthWeights = (request.wavelength_weights ?? request.wavelengths_nm.map((wavelength_nm) => ({ wavelength_nm, weight: 1 }))).reduce<Record<string, number>>(
    (weights, sample) => {
      const key = String(sample.wavelength_nm)
      weights[key] = (weights[key] ?? 0) + sample.weight
      return weights
    },
    {},
  )
  const total = chartAnalysisRequestCount(request)
  let completed = 0
  const tracked = async <T,>(promise: Promise<T>) => {
    try {
      return await promise
    } finally {
      completed += 1
      options.onProgress?.(completed, total)
    }
  }
  const [rayFanY, rayFanZ, longitudinal, distortion, fieldCurvature, msImageSurface, relativeIllumination, mtfByField] = await Promise.all([
    tracked(postAnalysis<ChartAnalysisResult['rayFan']>(apiBase, '/v1/analysis/ray-fan', {
      ...request,
      ray_sampling: { ...request.ray_sampling, pupil_distribution: 'fan_y' },
    }, options.signal)),
    tracked(postAnalysis<ChartAnalysisResult['rayFan']>(apiBase, '/v1/analysis/ray-fan', {
      ...request,
      ray_sampling: { ...request.ray_sampling, pupil_distribution: 'fan_z' },
    }, options.signal)),
    tracked(postAnalysis<ChartAnalysisResult['longitudinal']>(apiBase, '/v1/analysis/longitudinal-aberration', {
      ...request,
      fields: axialField ? [axialField] : request.fields,
      ray_sampling: { ...request.ray_sampling, pupil_distribution: 'fan_y' },
    }, options.signal)),
    tracked(postAnalysis<ChartAnalysisResult['distortion']>(apiBase, '/v1/analysis/distortion', curveRequest, options.signal)),
    tracked(postAnalysis<{ rows: FieldCurvatureRow[]; artifacts?: Record<string, string> }>(apiBase, '/v1/analysis/field-curvature', curveRequest, options.signal)),
    tracked(postAnalysis<{ rows: FieldCurvatureRow[] }>(apiBase, '/v1/analysis/ms-image-surface', curveRequest, options.signal)),
    tracked(postAnalysis<ChartAnalysisResult['relativeIllumination']>(apiBase, '/v1/analysis/relative-illumination', {
      ...curveRequest,
      ray_sampling: request.relative_illumination_sampling ?? DEFAULT_RELATIVE_ILLUMINATION_SAMPLING,
    }, options.signal)),
    Promise.all(
      mtfFields.map((field) =>
        tracked(postAnalysis<NonNullable<ChartAnalysisResult['mtf']> | WhiteMtfResponse>(apiBase, mtfMode === 'white' ? '/v1/analysis/white-mtf' : '/v1/analysis/mtf', {
          ...request,
          ...(field ? { fields: [field] } : {}),
          ...(mtfMode === 'white' ? { wavelength_weights: wavelengthWeights } : {}),
          ray_sampling: DEFAULT_MTF_SAMPLING,
          frequencies_lp_per_mm: request.frequencies_lp_per_mm ?? [...DEFAULT_MTF_FREQUENCIES_LP_PER_MM],
        }, options.signal)),
      ),
    ),
  ])
  const msRowsByField = new Map((msImageSurface.rows ?? []).map((row) => [row.field_id, row]))
  const mtfPoints = mtfByField.flatMap((result, index) => {
    const points = mtfMode === 'white' ? (result as WhiteMtfResponse).mtf?.points : (result as NonNullable<ChartAnalysisResult['mtf']>)?.points
    return (points ?? []).map((point) => ({ ...point, field_id: mtfFields[index]?.id }))
  })
  const firstMtf = mtfByField[0]
  const mtfMetadata = mtfMode === 'white'
    ? (firstMtf as WhiteMtfResponse | undefined)?.metadata ?? (firstMtf as WhiteMtfResponse | undefined)?.mtf?.metadata
    : (firstMtf as NonNullable<ChartAnalysisResult['mtf']> | undefined)?.metadata
  const mtfArtifacts = mtfMode === 'white'
    ? (firstMtf as WhiteMtfResponse | undefined)?.mtf?.artifacts
    : (firstMtf as NonNullable<ChartAnalysisResult['mtf']> | undefined)?.artifacts
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
    mtf: {
      points: mtfPoints,
      mode: mtfMode,
      ...(mtfMode === 'white' ? { wavelength_weights: (firstMtf as WhiteMtfResponse | undefined)?.wavelength_weights ?? wavelengthWeights } : {}),
      metadata: mtfMetadata,
      artifacts: mtfArtifacts,
      diffraction_included: false,
    },
  }
}

export async function runThroughFocusMtf(apiBase: string, request: AnalysisRequest): Promise<ThroughFocusMtfResult> {
  return postAnalysis<ThroughFocusMtfResult>(apiBase, '/v1/analysis/mtf/through-focus', {
    ...request,
    ray_sampling: DEFAULT_MTF_SAMPLING,
    frequencies_lp_per_mm: [10, 30],
    defocus_points: 21,
  })
}

export async function runBestFocus(apiBase: string, request: AnalysisRequest): Promise<BestFocusResponse> {
  return postAnalysis<BestFocusResponse>(apiBase, '/v1/solve/best-focus', request)
}

export async function runVisualComposite(apiBase: string, request: AnalysisRequest): Promise<VisualCompositeResponse> {
  return postAnalysis<VisualCompositeResponse>(apiBase, '/v1/analysis/visual-composite', request)
}
