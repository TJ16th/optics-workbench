import { useRef, useState } from 'react'
import {
  Button,
  CodeSnippet,
  ContentSwitcher,
  Dropdown,
  Header,
  HeaderName,
  InlineNotification,
  NumberInput,
  Select,
  SelectItem,
  Switch,
  Tag,
  TextInput,
  Toggletip,
  ToggletipButton,
  ToggletipContent,
} from '@carbon/react'
import { Add, Checkmark, Download, Play, Renew, Save, TrashCan } from '@carbon/icons-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { defaultApiBase, EngineApiError, fetchArtifact, registerSystem, runBestFocus, runChartAnalyses, runPreview, validateSystem, getHealth, getMeta, type AnalysisRequest } from '../api/engine'
import { presets } from '../domain/presets'
import type {
  AnalysisField,
  BestFocusResponse,
  ChartAnalysisResult,
  DistortionRow,
  EngineIssue,
  EvaluationPlaneMetadata,
  FieldCurvatureRow,
  FocusCurvePoint,
  ImagePlanePolicy,
  ImagePlanePolicyApplyTo,
  ImagePlanePolicyMode,
  MtfPoint,
  OpticalGroup,
  OpticalSystem,
  RayFanPoint,
  RelativeIlluminationRow,
  RuntimeConfiguration,
  Surface,
  TraceResponse,
  ValidationResult,
  WavelengthSample,
} from '../domain/types'
import { changeLanguage } from '../i18n'
import { displayIsoDate, formatFixed, formatInteger, isoNow } from '../i18n/format'
import { getTerm, renderEngineIssue, termLabel } from '../i18n/glossary'
import type { SupportedLanguage } from '../i18n/resources'
import { wavelengthColor } from './chartTheme'
import { makeExportSvg, type ExportChart } from './exportSvg'

type TabKey = 'system' | 'preview' | 'analysis' | 'compare' | 'debug'

type Snapshot = {
  id: string
  created_at: string
  preset_id: string
  system_name: string
  system_hash: string | null
  system: OpticalSystem
  analysis: {
    fields: AnalysisField[]
    wavelengths: WavelengthSample[]
    samples_per_field: number
    pupil_distribution: string
    aiming_mode: string
    image_plane_policy?: ImagePlanePolicy
    evaluation_plane?: EvaluationPlaneMetadata
  }
  results: {
    trace?: TraceResponse
    charts?: ChartAnalysisResult
    focus?: BestFocusResponse
  }
  artifacts: Record<string, unknown>
  artifact_uris: Record<string, string>
  missing_artifacts: string[]
  partial: boolean
  metrics: Record<string, string | number | null>
  trace_status: string[]
}

type ImagePlanePolicyDraft = {
  mode: ImagePlanePolicyMode
  applyTo: ImagePlanePolicyApplyTo
  customOffsetMm: number
  frequencyLpMm: number
  searchRangeMm: number
  searchSteps: number
}

type DecenterTiltDraft = {
  targetGroupId: string
  shiftY: number
  shiftZ: number
  tiltY: number
  tiltZ: number
  rollX: number
  rotationReference: 'from_surface_vertex' | 'to_surface_vertex'
}

const tabKeys: TabKey[] = ['system', 'preview', 'analysis', 'compare', 'debug']

const defaultImagePlanePolicy: ImagePlanePolicyDraft = {
  mode: 'fixed_sensor',
  applyTo: 'evaluation_plane',
  customOffsetMm: 0,
  frequencyLpMm: 20,
  searchRangeMm: 5,
  searchSteps: 11,
}

const defaultDecenterTiltDraft: DecenterTiltDraft = {
  targetGroupId: '',
  shiftY: 0,
  shiftZ: 0,
  tiltY: 0,
  tiltZ: 0,
  rollX: 0,
  rotationReference: 'from_surface_vertex',
}

const defaultFieldSet: AnalysisField[] = [
  { id: 'center', type: 'angular' as const, theta_y_deg: 0, theta_z_deg: 0 },
  { id: 'edge-y', type: 'angular' as const, theta_y_deg: 10, theta_z_deg: 0 },
  { id: 'edge-z', type: 'angular' as const, theta_y_deg: 0, theta_z_deg: 10 },
]

const wavelengthPresets: Array<{ id: string; label: string; wavelength_nm: number }> = [
  { id: 'F', label: 'F 486.13 nm', wavelength_nm: 486.13 },
  { id: 'd', label: 'd 587.56 nm', wavelength_nm: 587.56 },
  { id: 'C', label: 'C 656.27 nm', wavelength_nm: 656.27 },
  { id: 'e', label: 'e 546.07 nm', wavelength_nm: 546.07 },
]

const sliderPreviewDebounceMs = 70
const sliderPreviewSamplesPerField = 5

const surfaceColumns: Array<{
  id: string
  termId?: string
  value: (surface: Surface) => string | number
}> = [
  { id: 'id', value: (row) => row.id },
  { id: 'kind', value: (row) => row.kind },
  { id: 'surface_type', value: (row) => row.surface_type ?? 'plane' },
  { id: 'radius_mm', termId: 'radius_mm', value: (row) => row.radius_mm ?? 0 },
  { id: 'thickness_after_mm', termId: 'thickness_after_mm', value: (row) => row.thickness_after_mm ?? 0 },
  { id: 'material', termId: 'material', value: (row) => row.material_after ?? '-' },
  { id: 'semi_diameter_mm', termId: 'semi_diameter_mm', value: (row) => row.semi_diameter_mm ?? row.aperture?.semi_diameter_mm ?? '-' },
]

function cloneSystem(system: OpticalSystem): OpticalSystem {
  return JSON.parse(JSON.stringify(system))
}

function cloneFields(fields: AnalysisField[]): AnalysisField[] {
  return fields.map((field) => ({ ...field }))
}

function initialWavelengths(system: OpticalSystem): WavelengthSample[] {
  const samples = system.wavelengths_nm?.samples?.length ? system.wavelengths_nm.samples : [system.wavelengths_nm?.primary ?? 587.56]
  return samples.map((wavelength) => ({ wavelength_nm: wavelength, weight: wavelength === system.wavelengths_nm?.primary ? 1 : 0.5 }))
}

function numericInputValue(value: string | number | undefined, fallback: number) {
  const next = Number(value)
  return Number.isFinite(next) ? next : fallback
}

function uniqueFieldId(fields: AnalysisField[]) {
  let index = fields.length + 1
  let id = `field-${index}`
  const used = new Set(fields.map((field) => field.id))
  while (used.has(id)) {
    index += 1
    id = `field-${index}`
  }
  return id
}

function traceEvaluatedFields(trace: TraceResponse | undefined, fallback: AnalysisField[]) {
  return trace?.metadata.evaluated_fields?.length ? trace.metadata.evaluated_fields : fallback
}

function fieldAngle(row: { theta_y_deg: number; theta_z_deg: number }) {
  return Math.hypot(row.theta_y_deg, row.theta_z_deg)
}

function finitePoint(x: number | null | undefined, y: number | null | undefined) {
  return typeof x === 'number' && typeof y === 'number' && Number.isFinite(x) && Number.isFinite(y)
}

function statusTone(status?: string) {
  if (status === 'ok') return 'green'
  if (status === 'warning') return 'magenta'
  if (status === 'error') return 'red'
  return 'gray'
}

function issueKind(severity?: string) {
  if (severity === 'error') return 'error'
  if (severity === 'warning') return 'warning'
  return 'info'
}

function systemPositions(system: OpticalSystem) {
  let x = 0
  return system.surfaces.map((surface) => {
    const row = { surface, x }
    x += surface.thickness_after_mm ?? 0
    return row
  })
}

function traceArrived(trace?: TraceResponse) {
  return trace?.status.filter((item, index) => item === 'alive' && Number.isFinite(trace.sensor_y_mm[index])).length ?? 0
}

function collectArtifactUris(value: unknown, prefix = 'result'): Record<string, string> {
  const found: Record<string, string> = {}
  if (!value || typeof value !== 'object') return found
  if (Array.isArray(value)) {
    value.forEach((item, index) => Object.assign(found, collectArtifactUris(item, `${prefix}.${index}`)))
    return found
  }
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    const nextKey = `${prefix}.${key}`
    if (typeof item === 'string' && item.startsWith('artifact://')) {
      found[nextKey] = item
    } else if (item && typeof item === 'object') {
      Object.assign(found, collectArtifactUris(item, nextKey))
    }
  }
  return found
}

function sameJson(left: unknown, right: unknown) {
  return JSON.stringify(left) === JSON.stringify(right)
}

function evaluationPlaneSignature(metadata?: EvaluationPlaneMetadata) {
  if (!metadata) return null
  return {
    policy_mode: metadata.policy_mode,
    evaluation_plane_x_mm: metadata.evaluation_plane_x_mm,
    offset_from_sensor_mm: metadata.offset_from_sensor_mm,
  }
}

function comparisonWarnings(left?: Snapshot, right?: Snapshot) {
  if (!left || !right) return []
  const warnings: string[] = []
  if (!sameJson(left.analysis.fields, right.analysis.fields)) warnings.push('fields')
  if (!sameJson(left.analysis.wavelengths, right.analysis.wavelengths)) warnings.push('wavelengths')
  if (!sameJson(evaluationPlaneSignature(left.analysis.evaluation_plane), evaluationPlaneSignature(right.analysis.evaluation_plane))) warnings.push('evaluation_plane')
  return warnings
}

function extractEvaluationPlane(result?: TraceResponse | ChartAnalysisResult): EvaluationPlaneMetadata | undefined {
  if (!result) return undefined
  if ('metadata' in result && result.metadata?.evaluation_plane) return result.metadata.evaluation_plane as EvaluationPlaneMetadata
  const chart = result as ChartAnalysisResult
  return (
    (chart.mtf?.metadata?.evaluation_plane as EvaluationPlaneMetadata | undefined) ??
    (chart.rayFan?.metadata?.evaluation_plane as EvaluationPlaneMetadata | undefined) ??
    (chart.distortion?.metadata?.evaluation_plane as EvaluationPlaneMetadata | undefined) ??
    (chart.relativeIllumination?.metadata?.evaluation_plane as EvaluationPlaneMetadata | undefined)
  )
}

function makePolicy(draft: ImagePlanePolicyDraft, fields: AnalysisField[], wavelengths: WavelengthSample[]): ImagePlanePolicy {
  const policy: ImagePlanePolicy = {
    mode: draft.mode,
    apply_to: draft.applyTo,
    frequency_lpmm: draft.frequencyLpMm,
    criteria: {
      fields: fields.map((field) => ({ ...field, weight: 1 })),
      wavelengths: wavelengths.map((sample) => ({ wavelength_nm: sample.wavelength_nm, weight: sample.weight })),
      frequency_lpmm: draft.frequencyLpMm,
    },
  }
  if (draft.mode === 'custom_offset') {
    policy.offset_mm = draft.customOffsetMm
  }
  if (draft.mode === 'best_focus_rms' || draft.mode === 'best_focus_mtf' || draft.mode === 'sweep') {
    policy.search = {
      range_mm: draft.searchRangeMm,
      tolerance_mm: 0.001,
      max_iterations: 64,
      steps: draft.searchSteps,
    }
  }
  return policy
}

function sensorIndex(system: OpticalSystem) {
  return system.surfaces.findIndex((surface) => surface.kind === 'sensor')
}

function applySensorOffset(system: OpticalSystem, offsetMm: number): OpticalSystem | undefined {
  const index = sensorIndex(system)
  if (index <= 0 || !Number.isFinite(offsetMm)) return undefined
  const next = cloneSystem(system)
  const previous = next.surfaces[index - 1]
  previous.thickness_after_mm = (previous.thickness_after_mm ?? 0) + offsetMm
  return next
}

function uniqueGroupId(groups: OpticalGroup[]) {
  let index = groups.length + 1
  let id = `G${index}`
  const used = new Set(groups.map((group) => group.id))
  while (used.has(id)) {
    index += 1
    id = `G${index}`
  }
  return id
}

function defaultGroupFor(system: OpticalSystem): OpticalGroup {
  const firstSurface = system.surfaces.find((surface) => surface.kind !== 'sensor') ?? system.surfaces[0]
  return {
    id: uniqueGroupId(system.groups ?? []),
    name: '',
    from_surface: firstSurface?.id ?? '',
    to_surface: firstSurface?.id ?? '',
  }
}

function groupSurfaceRange(group: OpticalGroup, surfaces: Surface[]) {
  const fromIndex = surfaces.findIndex((surface) => surface.id === group.from_surface)
  const toIndex = surfaces.findIndex((surface) => surface.id === group.to_surface)
  return { fromIndex, toIndex }
}

function groupIssues(groups: OpticalGroup[], surfaces: Surface[]) {
  const issues: Array<{ key: string; type: 'error' | 'warning'; messageKey: string; values?: Record<string, string> }> = []
  const ranges = groups.map((group) => ({ group, ...groupSurfaceRange(group, surfaces) }))
  const ids = new Set<string>()
  for (const { group, fromIndex, toIndex } of ranges) {
    if (ids.has(group.id)) {
      issues.push({ key: `duplicate-${group.id}`, type: 'error', messageKey: 'surfaceTable.groups.duplicate_id', values: { group_id: group.id } })
    }
    ids.add(group.id)
    if (fromIndex < 0 || toIndex < 0) {
      issues.push({ key: `unknown-${group.id}`, type: 'error', messageKey: 'surfaceTable.groups.unknown_surface', values: { group_id: group.id } })
      continue
    }
    if (fromIndex > toIndex) {
      issues.push({ key: `range-${group.id}`, type: 'error', messageKey: 'surfaceTable.groups.invalid_range', values: { group_id: group.id } })
    }
  }

  for (let leftIndex = 0; leftIndex < ranges.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < ranges.length; rightIndex += 1) {
      const left = ranges[leftIndex]
      const right = ranges[rightIndex]
      if (left.fromIndex < 0 || left.toIndex < 0 || right.fromIndex < 0 || right.toIndex < 0) continue
      if (left.fromIndex > left.toIndex || right.fromIndex > right.toIndex) continue
      if (left.fromIndex <= right.toIndex && right.fromIndex <= left.toIndex) {
        issues.push({
          key: `overlap-${left.group.id}-${right.group.id}`,
          type: 'warning',
          messageKey: 'surfaceTable.groups.overlap',
          values: { left: left.group.id, right: right.group.id },
        })
      }
    }
  }
  return issues
}

function motionGroupIds(system: OpticalSystem) {
  const ids = new Set<string>()
  for (const position of system.zoom_positions ?? []) {
    for (const groupId of Object.keys(position.group_positions)) ids.add(groupId)
  }
  for (const group of system.groups ?? []) {
    if (/focus|zoom/i.test(`${group.id} ${group.name ?? ''}`)) ids.add(group.id)
  }
  return [...ids]
}

function decenterTiltGroupIds(system: OpticalSystem) {
  const groups = system.groups ?? []
  const preferred = groups.filter((group) => /ois|decenter|tilt|align/i.test(`${group.id} ${group.name ?? ''}`)).map((group) => group.id)
  const all = groups.map((group) => group.id)
  return [...new Set([...preferred, ...all])]
}

function zoomBaseShift(system: OpticalSystem, zoomPositionId: string, groupId: string) {
  const position = system.zoom_positions?.find((item) => item.id === zoomPositionId)
  return position?.group_positions[groupId]?.shift_x_mm ?? 0
}

function hasNonzeroDecenterTilt(draft: DecenterTiltDraft) {
  return [draft.shiftY, draft.shiftZ, draft.tiltY, draft.tiltZ, draft.rollX].some((value) => Math.abs(value) > 1.0e-12)
}

function makeRuntimeConfiguration(system: OpticalSystem, zoomPositionId: string, focusGroupId: string, focusShiftMm: number, decenterTilt: DecenterTiltDraft): RuntimeConfiguration {
  const configuration: RuntimeConfiguration = {}
  if (zoomPositionId) configuration.zoom_position = zoomPositionId
  if (focusGroupId) {
    configuration.group_positions = {
      [focusGroupId]: {
        shift_x_mm: zoomBaseShift(system, zoomPositionId, focusGroupId) + focusShiftMm,
      },
    }
  }
  if (decenterTilt.targetGroupId && hasNonzeroDecenterTilt(decenterTilt)) {
    if (Math.abs(decenterTilt.shiftY) > 1.0e-12 || Math.abs(decenterTilt.shiftZ) > 1.0e-12) {
      configuration.decenters = [
        {
          group: decenterTilt.targetGroupId,
          shift_y_mm: decenterTilt.shiftY,
          shift_z_mm: decenterTilt.shiftZ,
        },
      ]
    }
    if (Math.abs(decenterTilt.tiltY) > 1.0e-12 || Math.abs(decenterTilt.tiltZ) > 1.0e-12 || Math.abs(decenterTilt.rollX) > 1.0e-12) {
      configuration.tilts = [
        {
          group: decenterTilt.targetGroupId,
          tilt_y_deg: decenterTilt.tiltY,
          tilt_z_deg: decenterTilt.tiltZ,
          roll_x_deg: decenterTilt.rollX,
          rotation_center: { reference: decenterTilt.rotationReference },
        },
      ]
    }
  }
  return configuration
}

function apertureStopIndex(system: OpticalSystem) {
  return system.surfaces.findIndex((surface) => surface.kind === 'aperture_stop')
}

function apertureStopRadius(system: OpticalSystem) {
  const stop = system.surfaces[apertureStopIndex(system)]
  if (!stop) return null
  return stop.aperture?.semi_diameter_mm ?? stop.aperture?.outer_semi_diameter_mm ?? stop.semi_diameter_mm ?? null
}

function withApertureStopRadius(system: OpticalSystem, radiusMm: number): OpticalSystem | undefined {
  const index = apertureStopIndex(system)
  if (index < 0 || !Number.isFinite(radiusMm) || radiusMm <= 0) return undefined
  const next = cloneSystem(system)
  const stop = next.surfaces[index]
  stop.semi_diameter_mm = radiusMm
  if (stop.aperture) {
    stop.aperture.semi_diameter_mm = radiusMm
    if (stop.aperture.outer_semi_diameter_mm !== undefined) stop.aperture.outer_semi_diameter_mm = radiusMm
  } else {
    stop.aperture = { shape: 'circle', semi_diameter_mm: radiusMm }
  }
  return next
}

function presetLabel(id: string, fallback: string, t: (key: string, options?: Record<string, unknown>) => string) {
  return t(`common.preset.items.${id}.name`, { defaultValue: fallback })
}

function presetSummary(id: string, fallback: string, t: (key: string, options?: Record<string, unknown>) => string) {
  return t(`common.preset.items.${id}.summary`, { defaultValue: fallback })
}

function getApiIssue(error: unknown): EngineIssue | undefined {
  if (error instanceof EngineApiError) return error.issue
  if (error instanceof Error) {
    return { code: 'api_error', params: {}, message_en: error.message, severity: 'error' }
  }
  return undefined
}

function TermHelp({
  termId,
  fallback,
  plainHelp,
  onOpenHelp,
}: {
  termId?: string
  fallback: string
  plainHelp?: string
  onOpenHelp: (termId: string) => void
}) {
  const { t, i18n } = useTranslation(['common'])
  const term = termId ? getTerm(termId, i18n.language) : undefined
  const label = termId ? termLabel(termId, i18n.language, fallback) : fallback
  const body = term?.short ?? plainHelp ?? fallback

  const stableTermId = termId ?? fallback

  return (
    <span className="term-help" data-term-id={stableTermId} data-testid={`term-help-${stableTermId}`}>
      <span>{label}</span>
      <Toggletip align="bottom">
        <ToggletipButton label={t('common.buttons.details')} />
        <ToggletipContent>
          <div className="toggletip-body" data-testid={termId ? `term-help-content-${termId}` : undefined}>
            <p>{body}</p>
            {term?.formula ? <code>{term.formula}</code> : null}
            {termId && term?.long ? (
              <Button kind="ghost" size="sm" onClick={() => onOpenHelp(termId)}>
                {t('common.buttons.details')}
              </Button>
            ) : null}
          </div>
        </ToggletipContent>
      </Toggletip>
    </span>
  )
}

function HelpDrawer({ termId, onClose, onNavigate }: { termId: string | null; onClose: () => void; onNavigate: (termId: string) => void }) {
  const { t, i18n } = useTranslation(['common'])
  if (!termId) return null
  const term = getTerm(termId, i18n.language)
  if (!term) return null
  return (
    <aside className="help-drawer" aria-label={term.label}>
      <div className="help-drawer__header">
        <h2>{termLabel(termId, i18n.language)}</h2>
        <Button kind="ghost" size="sm" onClick={onClose}>
          {t('common.buttons.close')}
        </Button>
      </div>
      <p>{term.long ?? term.short}</p>
      {term.formula ? <code>{term.formula}</code> : null}
      {term.see_also?.length ? (
        <div className="see-also-list">
          {term.see_also.map((id) => (
            <Button key={id} kind="ghost" size="sm" onClick={() => onNavigate(id)}>
              {termLabel(id, i18n.language, id)}
            </Button>
          ))}
        </div>
      ) : null}
    </aside>
  )
}

function groupVisualTransform(system: OpticalSystem, surfaceId: string, configuration?: RuntimeConfiguration) {
  const containingGroups = (system.groups ?? []).filter((item) => {
    const range = groupSurfaceRange(item, system.surfaces)
    const index = system.surfaces.findIndex((surface) => surface.id === surfaceId)
    return range.fromIndex >= 0 && range.toIndex >= 0 && index >= range.fromIndex && index <= range.toIndex
  })
  const configuredIds = new Set([...(configuration?.decenters ?? []).map((entry) => entry.group), ...(configuration?.tilts ?? []).map((entry) => entry.group)])
  const group = containingGroups.find((item) => configuredIds.has(item.id)) ?? containingGroups[0]
  if (!group || !configuration) return { shiftY: 0, tiltZ: 0, active: false }
  const decenter = configuration.decenters?.find((entry) => entry.group === group.id)
  const tilt = configuration.tilts?.find((entry) => entry.group === group.id)
  return {
    shiftY: decenter?.shift_y_mm ?? 0,
    tiltZ: tilt?.tilt_z_deg ?? 0,
    active: Boolean(decenter || tilt),
  }
}

function LayoutView({
  system,
  trace,
  evaluationPlane,
  configuration,
}: {
  system: OpticalSystem
  trace?: TraceResponse
  evaluationPlane?: EvaluationPlaneMetadata
  configuration?: RuntimeConfiguration
}) {
  const { t } = useTranslation(['layoutView'])
  const positions = systemPositions(system)
  const evalX = evaluationPlane?.evaluation_plane_x_mm
  const solvedX = evaluationPlane?.solved_evaluation_plane_x_mm
  const xs = [...positions.map((row) => row.x), ...(Number.isFinite(evalX) ? [evalX as number] : []), ...(Number.isFinite(solvedX) ? [solvedX as number] : [])]
  const minX = Math.min(...xs, 0)
  const maxX = Math.max(...xs, 1)
  const span = Math.max(1, maxX - minX)
  const xScale = (x: number) => 36 + ((x - minX) / span) * 648
  const centerY = 170
  const apertureY = (semiD?: number | string) => {
    const value = typeof semiD === 'number' ? semiD : 8
    return Math.max(20, Math.min(92, value * 4))
  }
  const tracePoints = trace?.sensor_y_mm
    ?.map((y, index) => ({ y, z: trace.sensor_z_mm[index], status: trace.status[index] }))
    .filter((point) => Number.isFinite(point.y) && point.status === 'alive')
    .slice(0, 80)

  return (
    <svg id="layout-svg" className="layout-view" viewBox="0 0 720 340" role="img" aria-label={t('layoutView.optical_layout_aria')}>
      <title>{t('layoutView.optical_layout')}</title>
      <line x1="24" x2="696" y1={centerY} y2={centerY} className="axis-line" />
      {positions.map(({ surface, x }) => {
        const sx = xScale(x)
        const h = apertureY(surface.semi_diameter_mm ?? surface.aperture?.semi_diameter_mm)
        const transform = groupVisualTransform(system, surface.id, configuration)
        const sy = centerY - Math.max(-52, Math.min(52, transform.shiftY * 10))
        const tiltDx = Math.max(-20, Math.min(20, transform.tiltZ * 3))
        const className = `surface-line surface-${surface.kind}${transform.active ? ' surface-configured' : ''}`
        return (
          <g key={surface.id}>
            <line x1={sx - tiltDx} x2={sx + tiltDx} y1={sy - h} y2={sy + h} className={className} />
            {surface.kind === 'sensor' ? <rect x={sx - 3} y={sy - 62} width="6" height="124" className="sensor-plane" /> : null}
            {surface.kind === 'aperture_stop' ? <circle cx={sx} cy={sy} r="5" className="stop-dot" /> : null}
            {transform.active ? <circle cx={sx} cy={sy - h - 10} r="3.5" className="configured-dot" /> : null}
            <text x={sx} y={sy + h + 22} textAnchor="middle" className="surface-label">
              {surface.id}
            </text>
          </g>
        )
      })}
      {Number.isFinite(evalX) ? (
        <g>
          <line x1={xScale(evalX as number)} x2={xScale(evalX as number)} y1={centerY - 96} y2={centerY + 96} className="evaluation-plane-line" />
          <text x={xScale(evalX as number) + 6} y={centerY - 104} className="surface-label">
            EVAL
          </text>
        </g>
      ) : null}
      {Number.isFinite(solvedX) && solvedX !== evalX ? (
        <g>
          <line x1={xScale(solvedX as number)} x2={xScale(solvedX as number)} y1={centerY - 78} y2={centerY + 78} className="paraxial-plane-line" />
          <text x={xScale(solvedX as number) + 6} y={centerY + 108} className="surface-label">
            SOLVE
          </text>
        </g>
      ) : null}
      {tracePoints?.map((point, index) => {
        const sensorX = xScale(positions[positions.length - 1]?.x ?? maxX)
        const py = centerY - Math.max(-80, Math.min(80, point.y * 8))
        return <line key={index} x1={xScale(positions[0]?.x ?? minX)} y1={centerY + (index % 7 - 3) * 7} x2={sensorX} y2={py} className="ray-line" />
      })}
    </svg>
  )
}

function SurfaceTable({ surfaces, onOpenHelp }: { surfaces: Surface[]; onOpenHelp: (termId: string) => void }) {
  const { t } = useTranslation(['surfaceTable'])
  return (
    <div className="table-shell">
      <table className="surface-table">
        <thead>
          <tr>
            {surfaceColumns.map((column) => (
              <th key={column.id}>
                <TermHelp
                  termId={column.termId}
                  fallback={t(`surfaceTable.columns.${column.id}`)}
                  plainHelp={t(`surfaceTable.help.${column.id}`, { defaultValue: t(`surfaceTable.columns.${column.id}`) })}
                  onOpenHelp={onOpenHelp}
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {surfaces.map((surface) => (
            <tr key={surface.id}>
              {surfaceColumns.map((column) => (
                <td key={column.id}>{String(column.value(surface))}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function GroupPanel({
  system,
  onAddGroup,
  onUpdateGroup,
  onRemoveGroup,
  onOpenHelp,
}: {
  system: OpticalSystem
  onAddGroup: () => void
  onUpdateGroup: (index: number, patch: Partial<OpticalGroup>) => void
  onRemoveGroup: (index: number) => void
  onOpenHelp: (termId: string) => void
}) {
  const { t } = useTranslation(['surfaceTable'])
  const groups = system.groups ?? []
  const surfaces = system.surfaces
  const issues = groupIssues(groups, surfaces)

  return (
    <section className="group-editor" aria-label={t('surfaceTable.groups.title')}>
      <div className="panel-heading">
        <div>
          <h2>
            <TermHelp termId="zoom_group" fallback={t('surfaceTable.groups.title')} onOpenHelp={onOpenHelp} />
          </h2>
          <p className="muted">{t('surfaceTable.groups.description')}</p>
        </div>
        <Button size="sm" kind="secondary" renderIcon={Add} onClick={onAddGroup}>
          {t('surfaceTable.groups.add')}
        </Button>
      </div>
      {groups.length ? (
        <div className="group-list">
          {groups.map((group, index) => {
            const range = groupSurfaceRange(group, surfaces)
            const rangeState = range.fromIndex < 0 || range.toIndex < 0 || range.fromIndex > range.toIndex ? 'invalid' : 'ok'
            return (
              <div key={`${group.id}-${index}`} className="group-row" data-testid="group-row" data-range-state={rangeState}>
                <TextInput
                  id={`group-id-${index}`}
                  labelText={t('surfaceTable.groups.id')}
                  value={group.id}
                  onChange={(event) => onUpdateGroup(index, { id: event.target.value })}
                />
                <TextInput
                  id={`group-name-${index}`}
                  labelText={t('surfaceTable.groups.name')}
                  value={group.name ?? ''}
                  onChange={(event) => onUpdateGroup(index, { name: event.target.value })}
                />
                <Select
                  id={`group-from-${index}`}
                  labelText={t('surfaceTable.groups.from_surface')}
                  value={group.from_surface}
                  onChange={(event) => onUpdateGroup(index, { from_surface: event.target.value })}
                >
                  {surfaces.map((surface) => (
                    <SelectItem key={surface.id} value={surface.id} text={surface.id} />
                  ))}
                </Select>
                <Select
                  id={`group-to-${index}`}
                  labelText={t('surfaceTable.groups.to_surface')}
                  value={group.to_surface}
                  onChange={(event) => onUpdateGroup(index, { to_surface: event.target.value })}
                >
                  {surfaces.map((surface) => (
                    <SelectItem key={surface.id} value={surface.id} text={surface.id} />
                  ))}
                </Select>
                <Button
                  hasIconOnly
                  size="sm"
                  kind="ghost"
                  renderIcon={TrashCan}
                  iconDescription={t('surfaceTable.groups.remove')}
                  tooltipPosition="left"
                  onClick={() => onRemoveGroup(index)}
                />
              </div>
            )
          })}
        </div>
      ) : (
        <p className="muted">{t('surfaceTable.groups.empty')}</p>
      )}
      {issues.length ? (
        <div className="group-issues">
          {issues.map((issue) => (
            <InlineNotification
              key={issue.key}
              lowContrast
              kind={issue.type}
              title={t(issue.type === 'error' ? 'surfaceTable.groups.issue_error' : 'surfaceTable.groups.issue_warning')}
              subtitle={t(issue.messageKey, issue.values)}
            />
          ))}
        </div>
      ) : null}
    </section>
  )
}

function GroupMotionPanel({
  system,
  zoomPositionId,
  focusGroupId,
  focusShiftMm,
  runtimeConfiguration,
  isPreviewing,
  onSetZoomPosition,
  onSetFocusGroup,
  onSetFocusShift,
  onCommit,
}: {
  system: OpticalSystem
  zoomPositionId: string
  focusGroupId: string
  focusShiftMm: number
  runtimeConfiguration: RuntimeConfiguration
  isPreviewing: boolean
  onSetZoomPosition: (id: string, commit?: boolean) => void
  onSetFocusGroup: (id: string, commit?: boolean) => void
  onSetFocusShift: (value: number, commit?: boolean) => void
  onCommit: () => void
}) {
  const { t } = useTranslation(['settings', 'units'])
  const zoomPositions = system.zoom_positions ?? []
  const groupIds = motionGroupIds(system)
  const zoomIndex = Math.max(0, zoomPositions.findIndex((position) => position.id === zoomPositionId))
  const enabled = zoomPositions.length > 0 || groupIds.length > 0
  const configJson = JSON.stringify(runtimeConfiguration)

  if (!enabled) {
    return (
      <section className="panel">
        <h2>{t('settings:settings.group_motion')}</h2>
        <p className="muted">{t('settings:settings.group_motion_empty')}</p>
      </section>
    )
  }

  return (
    <section className="panel group-motion-panel">
      <div className="condition-heading">
        <h2>{t('settings:settings.group_motion')}</h2>
        <Tag type={isPreviewing ? 'blue' : 'gray'}>{isPreviewing ? t('settings:settings.previewing') : t('settings:settings.preview_ready')}</Tag>
      </div>
      {zoomPositions.length ? (
        <div className="slider-control">
          <label htmlFor="zoom-position-slider">{t('settings:settings.zoom_position')}</label>
          <input
            id="zoom-position-slider"
            type="range"
            min={0}
            max={zoomPositions.length - 1}
            step={1}
            value={zoomIndex}
            onChange={(event) => onSetZoomPosition(zoomPositions[Number(event.target.value)]?.id ?? zoomPositions[0].id)}
            onMouseUp={onCommit}
            onTouchEnd={onCommit}
          />
          <div className="slider-meta">
            <strong>{zoomPositionId || zoomPositions[0].id}</strong>
            <span>{t('settings:settings.discrete_zoom')}</span>
          </div>
        </div>
      ) : null}
      {groupIds.length ? (
        <div className="slider-control">
          <Select id="focus-group" labelText={t('settings:settings.focus_group')} value={focusGroupId} onChange={(event) => onSetFocusGroup(event.target.value, true)}>
            {groupIds.map((groupId) => (
              <SelectItem key={groupId} value={groupId} text={groupId} />
            ))}
          </Select>
          <label htmlFor="focus-shift-slider">{t('settings:settings.focus_shift_x_mm')}</label>
          <input
            id="focus-shift-slider"
            type="range"
            min={-5}
            max={5}
            step={0.1}
            value={focusShiftMm}
            onChange={(event) => onSetFocusShift(Number(event.target.value))}
            onMouseUp={onCommit}
            onTouchEnd={onCommit}
          />
          <div className="slider-meta">
            <strong>
              {formatFixed(zoomBaseShift(system, zoomPositionId, focusGroupId) + focusShiftMm, 3)} {t('units:units.mm')}
            </strong>
            <span>{t('settings:settings.focus_shift_detail', { value: formatFixed(focusShiftMm, 1) })}</span>
          </div>
        </div>
      ) : null}
      <CodeSnippet type="single" hideCopyButton>
        {configJson}
      </CodeSnippet>
      <p className="muted">{t('settings:settings.group_motion_debounce', { ms: sliderPreviewDebounceMs, rays: sliderPreviewSamplesPerField })}</p>
    </section>
  )
}

function ApertureMotionPanel({
  system,
  irisRadiusMm,
  irisMaxRadiusMm,
  isPreviewing,
  onSetIrisRadius,
  onCommit,
  onOpenHelp,
}: {
  system: OpticalSystem
  irisRadiusMm: number
  irisMaxRadiusMm: number
  isPreviewing: boolean
  onSetIrisRadius: (value: number, commit?: boolean) => void
  onCommit: () => void
  onOpenHelp: (termId: string) => void
}) {
  const { t } = useTranslation(['settings', 'units'])
  const radius = apertureStopRadius(system)
  if (radius === null || irisMaxRadiusMm <= 0) {
    return (
      <section className="panel">
        <h2>{t('settings:settings.aperture_motion')}</h2>
        <p className="muted">{t('settings:settings.aperture_motion_empty')}</p>
      </section>
    )
  }
  const minRadius = Math.max(0.5, irisMaxRadiusMm * 0.1)
  return (
    <section className="panel group-motion-panel">
      <div className="condition-heading">
        <h2>
          <TermHelp termId="aperture_stop" fallback={t('settings:settings.aperture_motion')} onOpenHelp={onOpenHelp} />
        </h2>
        <Tag type={isPreviewing ? 'blue' : 'gray'}>{isPreviewing ? t('settings:settings.previewing') : t('settings:settings.preview_ready')}</Tag>
      </div>
      <div className="slider-control">
        <label htmlFor="iris-radius-slider">{t('settings:settings.iris_radius_mm')}</label>
        <input
          id="iris-radius-slider"
          type="range"
          min={minRadius}
          max={irisMaxRadiusMm}
          step={0.1}
          value={irisRadiusMm}
          onChange={(event) => onSetIrisRadius(Number(event.target.value))}
          onMouseUp={onCommit}
          onTouchEnd={onCommit}
        />
        <div className="slider-meta">
          <strong>
            {formatFixed(irisRadiusMm, 2)} {t('units:units.mm')}
          </strong>
          <span>{t('settings:settings.iris_radius_detail', { diameter: formatFixed(irisRadiusMm * 2, 2) })}</span>
        </div>
      </div>
      <p className="muted">{t('settings:settings.aperture_motion_debounce', { ms: sliderPreviewDebounceMs, rays: sliderPreviewSamplesPerField })}</p>
    </section>
  )
}

function DecenterTiltPanel({
  system,
  draft,
  runtimeConfiguration,
  isPreviewing,
  onUpdateDraft,
  onCommit,
  onOpenHelp,
}: {
  system: OpticalSystem
  draft: DecenterTiltDraft
  runtimeConfiguration: RuntimeConfiguration
  isPreviewing: boolean
  onUpdateDraft: (patch: Partial<DecenterTiltDraft>, commit?: boolean) => void
  onCommit: () => void
  onOpenHelp: (termId: string) => void
}) {
  const { t } = useTranslation(['settings', 'units'])
  const groupIds = decenterTiltGroupIds(system)
  if (!groupIds.length) {
    return (
      <section className="panel">
        <h2>{t('settings:settings.decenter_tilt')}</h2>
        <p className="muted">{t('settings:settings.decenter_tilt_empty')}</p>
      </section>
    )
  }
  const configJson = JSON.stringify({
    decenters: runtimeConfiguration.decenters ?? [],
    tilts: runtimeConfiguration.tilts ?? [],
  })
  return (
    <section className="panel group-motion-panel">
      <div className="condition-heading">
        <h2>
          <TermHelp termId="decenter" fallback={t('settings:settings.decenter_tilt')} onOpenHelp={onOpenHelp} />
        </h2>
        <Tag type={isPreviewing ? 'blue' : 'gray'}>{isPreviewing ? t('settings:settings.previewing') : t('settings:settings.preview_ready')}</Tag>
      </div>
      <Select id="decenter-tilt-group" labelText={t('settings:settings.target_group')} value={draft.targetGroupId} onChange={(event) => onUpdateDraft({ targetGroupId: event.target.value }, true)}>
        {groupIds.map((groupId) => (
          <SelectItem key={groupId} value={groupId} text={groupId} />
        ))}
      </Select>
      <div className="slider-grid">
        <SliderControl id="shift-y-slider" label={t('settings:settings.shift_y_mm')} value={draft.shiftY} min={-5} max={5} step={0.1} unit={t('units:units.mm')} onChange={(value) => onUpdateDraft({ shiftY: value })} onCommit={onCommit} />
        <SliderControl id="shift-z-slider" label={t('settings:settings.shift_z_mm')} value={draft.shiftZ} min={-5} max={5} step={0.1} unit={t('units:units.mm')} onChange={(value) => onUpdateDraft({ shiftZ: value })} onCommit={onCommit} />
        <SliderControl id="tilt-y-slider" label={t('settings:settings.tilt_y_deg')} value={draft.tiltY} min={-5} max={5} step={0.1} unit={t('units:units.deg')} onChange={(value) => onUpdateDraft({ tiltY: value })} onCommit={onCommit} />
        <SliderControl id="tilt-z-slider" label={t('settings:settings.tilt_z_deg')} value={draft.tiltZ} min={-5} max={5} step={0.1} unit={t('units:units.deg')} onChange={(value) => onUpdateDraft({ tiltZ: value })} onCommit={onCommit} />
        <SliderControl id="roll-x-slider" label={t('settings:settings.roll_x_deg')} value={draft.rollX} min={-5} max={5} step={0.1} unit={t('units:units.deg')} onChange={(value) => onUpdateDraft({ rollX: value })} onCommit={onCommit} />
      </div>
      <Select
        id="rotation-reference"
        labelText={t('settings:settings.rotation_center')}
        value={draft.rotationReference}
        onChange={(event) => onUpdateDraft({ rotationReference: event.target.value as DecenterTiltDraft['rotationReference'] }, true)}
      >
        <SelectItem value="from_surface_vertex" text={t('settings:settings.from_surface_vertex')} />
        <SelectItem value="to_surface_vertex" text={t('settings:settings.to_surface_vertex')} />
      </Select>
      <CodeSnippet type="single" hideCopyButton>
        {configJson}
      </CodeSnippet>
      <p className="muted">{t('settings:settings.decenter_tilt_debounce', { ms: sliderPreviewDebounceMs, rays: sliderPreviewSamplesPerField })}</p>
    </section>
  )
}

function SliderControl({
  id,
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
  onCommit,
}: {
  id: string
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  onChange: (value: number) => void
  onCommit: () => void
}) {
  return (
    <div className="slider-control">
      <label htmlFor={id}>{label}</label>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} onMouseUp={onCommit} onTouchEnd={onCommit} />
      <div className="slider-meta">
        <strong>
          {formatFixed(value, 2)} {unit}
        </strong>
      </div>
    </div>
  )
}

function SpotStrip({ trace }: { trace?: TraceResponse }) {
  const { t } = useTranslation(['layoutView'])
  const points = trace?.sensor_y_mm
    ?.map((y, index) => ({ y, z: trace.sensor_z_mm[index], status: trace.status[index] }))
    .filter((point) => Number.isFinite(point.y) && Number.isFinite(point.z))
    .slice(0, 120)

  return (
    <svg id="spot-svg" className="spot-strip" viewBox="0 0 260 220" role="img" aria-label={t('layoutView.spot_diagram_aria')}>
      <title>{t('layoutView.spot_diagram')}</title>
      <line x1="130" x2="130" y1="18" y2="202" className="plot-axis" />
      <line x1="28" x2="232" y1="110" y2="110" className="plot-axis" />
      <text x="236" y="114" className="plot-label">
        Y
      </text>
      <text x="134" y="24" className="plot-label">
        Z
      </text>
      {points?.map((point, index) => {
        const x = 130 + Math.max(-96, Math.min(96, point.y * 16))
        const y = 110 - Math.max(-86, Math.min(86, point.z * 16))
        return <circle key={index} cx={x} cy={y} r="2.7" className={point.status === 'alive' ? 'spot-point' : 'spot-blocked'} />
      })}
    </svg>
  )
}

function downloadText(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

async function exportChart(chart: ExportChart, language: string, format: 'svg' | 'png') {
  const svg = makeExportSvg(chart, language)
  if (format === 'svg') {
    downloadText(`${chart}-${language}.svg`, svg, 'image/svg+xml')
    return
  }
  const image = new Image()
  const svgUrl = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }))
  image.src = svgUrl
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve()
    image.onerror = () => reject(new Error('png export failed'))
  })
  const canvas = document.createElement('canvas')
  canvas.width = 640
  canvas.height = 360
  const context = canvas.getContext('2d')
  context?.drawImage(image, 0, 0)
  URL.revokeObjectURL(svgUrl)
  const pngUrl = canvas.toDataURL('image/png')
  const link = document.createElement('a')
  link.href = pngUrl
  link.download = `${chart}-${language}.png`
  link.click()
}

function SnapshotList({ snapshots, onExport }: { snapshots: Snapshot[]; onExport: (snapshot: Snapshot) => void }) {
  const { t, i18n } = useTranslation(['analysis'])
  if (!snapshots.length) return <p className="muted">{t('analysis.snapshot_empty')}</p>
  return (
    <div className="snapshot-list">
      {snapshots.map((snapshot) => (
        <div key={snapshot.id} className="snapshot-row">
          <div>
            <strong>{snapshot.id}</strong>
            <p className="muted">
              {t('analysis.snapshot_created')}: {displayIsoDate(snapshot.created_at)} / {snapshot.system_name}
            </p>
            {snapshot.partial ? <Tag type="magenta">{t('analysis:analysis.snapshot_partial')}</Tag> : null}
          </div>
          <Button size="sm" kind="ghost" renderIcon={Download} onClick={() => onExport(snapshot)}>
            JSON
          </Button>
          <dl>
            {Object.entries(snapshot.metrics).map(([metric, value]) => (
              <div key={metric} className="metric-row">
                <dt>{termLabel(metric, i18n.language, metric)}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  )
}

function CompareMetric({ label, left, right }: { label: string; left: string | number | null | undefined; right: string | number | null | undefined }) {
  const display = (value: string | number | null | undefined) => (value === null || value === undefined ? '-' : String(value))
  return (
    <div className="compare-metric-row">
      <span>{label}</span>
      <strong>{display(left)}</strong>
      <strong>{display(right)}</strong>
    </div>
  )
}

function CompareView({
  snapshots,
  leftId,
  rightId,
  onSetLeft,
  onSetRight,
}: {
  snapshots: Snapshot[]
  leftId: string
  rightId: string
  onSetLeft: (id: string) => void
  onSetRight: (id: string) => void
}) {
  const { t, i18n } = useTranslation(['analysis'])
  const left = snapshots.find((snapshot) => snapshot.id === leftId)
  const right = snapshots.find((snapshot) => snapshot.id === rightId)
  const warnings = comparisonWarnings(left, right)
  const artifactFallback = Boolean(left?.partial || right?.partial)
  const mtfLeft = left?.results.charts?.mtf?.points?.length ?? 0
  const mtfRight = right?.results.charts?.mtf?.points?.length ?? 0
  const riLeft = left?.results.charts?.relativeIllumination?.rows?.length ?? 0
  const riRight = right?.results.charts?.relativeIllumination?.rows?.length ?? 0
  const focusLeft = left?.results.focus?.focus_curve?.length ?? left?.analysis.evaluation_plane?.focus_curve?.length ?? 0
  const focusRight = right?.results.focus?.focus_curve?.length ?? right?.analysis.evaluation_plane?.focus_curve?.length ?? 0

  return (
    <div className="compare-stack" data-testid="compare-view">
      <div className="compare-selectors">
        <Select id="compare-left" labelText={t('analysis:analysis.compare_left')} value={leftId} onChange={(event) => onSetLeft(event.target.value)}>
          <SelectItem value="" text={t('analysis:analysis.select_snapshot')} />
          {snapshots.map((snapshot) => (
            <SelectItem key={snapshot.id} value={snapshot.id} text={snapshot.id} />
          ))}
        </Select>
        <Select id="compare-right" labelText={t('analysis:analysis.compare_right')} value={rightId} onChange={(event) => onSetRight(event.target.value)}>
          <SelectItem value="" text={t('analysis:analysis.select_snapshot')} />
          {snapshots.map((snapshot) => (
            <SelectItem key={snapshot.id} value={snapshot.id} text={snapshot.id} />
          ))}
        </Select>
      </div>
      {warnings.length ? <InlineNotification lowContrast kind="warning" title={t('analysis:analysis.compare_guard')} subtitle={t('analysis:analysis.compare_guard_detail', { items: warnings.join(', ') })} /> : null}
      {artifactFallback ? <InlineNotification lowContrast kind="warning" title={t('analysis:analysis.partial_snapshot')} subtitle={t('analysis:analysis.partial_snapshot_detail')} /> : null}
      {left && right ? (
        <div className="compare-grid">
          <section className="panel compare-panel">
            <h2>{t('analysis:analysis.condition_diff')}</h2>
            <CompareMetric label="system_hash" left={left.system_hash?.slice(0, 12) ?? null} right={right.system_hash?.slice(0, 12) ?? null} />
            <CompareMetric label="fields" left={left.analysis.fields.length} right={right.analysis.fields.length} />
            <CompareMetric label="wavelengths" left={left.analysis.wavelengths.length} right={right.analysis.wavelengths.length} />
            <CompareMetric label="evaluation_plane" left={formatFixed(left.analysis.evaluation_plane?.evaluation_plane_x_mm ?? 0, 4)} right={formatFixed(right.analysis.evaluation_plane?.evaluation_plane_x_mm ?? 0, 4)} />
          </section>
          <section className="panel compare-panel">
            <h2>{t('analysis:analysis.result_compare')}</h2>
            <CompareMetric label={termLabel('spot_diagram', i18n.language)} left={left.metrics.arrived} right={right.metrics.arrived} />
            <CompareMetric label={termLabel('mtf', i18n.language)} left={mtfLeft || t('analysis:analysis.no_data')} right={mtfRight || t('analysis:analysis.no_data')} />
            <CompareMetric label={termLabel('relative_illumination', i18n.language)} left={riLeft || t('analysis:analysis.no_data')} right={riRight || t('analysis:analysis.no_data')} />
            <CompareMetric label={t('analysis:analysis.focus_curve')} left={focusLeft || t('analysis:analysis.no_data')} right={focusRight || t('analysis:analysis.no_data')} />
          </section>
        </div>
      ) : (
        <p className="muted">{t('analysis:analysis.compare_select_prompt')}</p>
      )}
    </div>
  )
}

function EvaluatedFieldList({ trace, fields }: { trace?: TraceResponse; fields: AnalysisField[] }) {
  const { t } = useTranslation(['settings'])
  const evaluated = trace ? traceEvaluatedFields(trace, fields) : []
  return (
    <div className="evaluated-fields" data-testid="evaluated-fields">
      <h3>{t('settings:settings.evaluated_fields')}</h3>
      {evaluated.length ? (
        <ul>
          {evaluated.map((field) => (
            <li key={`${field.id}-${field.theta_y_deg}-${field.theta_z_deg}`}>
              <code>{field.id}</code>
              <span>
                {formatFixed(field.theta_y_deg, 3)} / {formatFixed(field.theta_z_deg, 3)} deg
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">{t('settings:settings.no_evaluated_fields')}</p>
      )}
    </div>
  )
}

type ChartPoint = { x: number; y: number }
type ChartSeries = { id: string; color: string; points: ChartPoint[] }

function ChartSvg({ series, xLabel, yLabel, emptyLabel }: { series: ChartSeries[]; xLabel: string; yLabel: string; emptyLabel: string }) {
  const points = series.flatMap((item) => item.points)
  if (!points.length) {
    return <div className="chart-empty">{emptyLabel}</div>
  }
  const xs = points.map((point) => point.x)
  const ys = points.map((point) => point.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const padX = maxX === minX ? 1 : (maxX - minX) * 0.05
  const padY = maxY === minY ? 1 : (maxY - minY) * 0.12
  const x0 = minX - padX
  const x1 = maxX + padX
  const y0 = minY - padY
  const y1 = maxY + padY
  const sx = (x: number) => 44 + ((x - x0) / (x1 - x0)) * 288
  const sy = (y: number) => 172 - ((y - y0) / (y1 - y0)) * 132

  return (
    <div className="chart-box">
      <svg viewBox="0 0 360 220" role="img" className="analysis-chart">
        <line x1="44" x2="332" y1="172" y2="172" className="plot-axis" />
        <line x1="44" x2="44" y1="40" y2="172" className="plot-axis" />
        <text x="338" y="188" className="plot-label" textAnchor="end">
          {xLabel}
        </text>
        <text x="16" y="44" className="plot-label">
          {yLabel}
        </text>
        <text x="44" y="190" className="plot-tick">
          {formatFixed(x0, 2)}
        </text>
        <text x="332" y="190" className="plot-tick" textAnchor="end">
          {formatFixed(x1, 2)}
        </text>
        <text x="38" y="176" className="plot-tick" textAnchor="end">
          {formatFixed(y0, 2)}
        </text>
        <text x="38" y="44" className="plot-tick" textAnchor="end">
          {formatFixed(y1, 2)}
        </text>
        {series.map((item) => {
          const ordered = [...item.points].sort((a, b) => a.x - b.x)
          const polyline = ordered.map((point) => `${sx(point.x)},${sy(point.y)}`).join(' ')
          return (
            <g key={item.id}>
              {ordered.length > 1 ? <polyline points={polyline} fill="none" stroke={item.color} strokeWidth="2" /> : null}
              {ordered.map((point, index) => (
                <circle key={index} cx={sx(point.x)} cy={sy(point.y)} r="2.7" fill={item.color} />
              ))}
            </g>
          )
        })}
      </svg>
      <div className="chart-legend">
        {series.map((item) => (
          <span key={item.id}>
            <i style={{ background: item.color }} />
            {item.id}
          </span>
        ))}
      </div>
    </div>
  )
}

function seriesFromRayFan(points: RayFanPoint[] | undefined, axis: 'y' | 'z'): ChartSeries[] {
  const groups = new Map<string, ChartSeries>()
  for (const point of points ?? []) {
    if (point.status !== 'alive') continue
    const x = axis === 'y' ? point.pupil_y : point.pupil_z
    const y = axis === 'y' ? point.transverse_error_y_mm : point.transverse_error_z_mm
    if (!finitePoint(x, y)) continue
    const key = `${point.field_id} ${formatFixed(point.wavelength_nm, 0)}nm`
    const existing = groups.get(key) ?? { id: key, color: wavelengthColor(point.wavelength_nm), points: [] }
    existing.points.push({ x, y: y as number })
    groups.set(key, existing)
  }
  return [...groups.values()]
}

function seriesFromDistortion(rows: DistortionRow[] | undefined): ChartSeries[] {
  return [
    {
      id: 'distortion',
      color: '#0f62fe',
      points: (rows ?? [])
        .filter((row) => finitePoint(fieldAngle(row), row.distortion_percent))
        .map((row) => ({ x: fieldAngle(row), y: row.distortion_percent as number })),
    },
  ]
}

function seriesFromFieldCurvature(rows: FieldCurvatureRow[] | undefined): ChartSeries[] {
  const safeRows = rows ?? []
  return [
    {
      id: 'M',
      color: '#0f62fe',
      points: safeRows
        .filter((row) => finitePoint(fieldAngle(row), row.tangential_focus_shift_mm ?? row.best_focus_shift_mm))
        .map((row) => ({ x: fieldAngle(row), y: (row.tangential_focus_shift_mm ?? row.best_focus_shift_mm) as number })),
    },
    {
      id: 'S',
      color: '#da1e28',
      points: safeRows
        .filter((row) => finitePoint(fieldAngle(row), row.sagittal_focus_shift_mm ?? row.best_focus_shift_mm))
        .map((row) => ({ x: fieldAngle(row), y: (row.sagittal_focus_shift_mm ?? row.best_focus_shift_mm) as number })),
    },
  ]
}

function seriesFromRelativeIllumination(rows: RelativeIlluminationRow[] | undefined): ChartSeries[] {
  return [
    {
      id: 'RI',
      color: '#24a148',
      points: (rows ?? []).map((row) => ({ x: fieldAngle(row), y: row.relative_illumination * 100 })),
    },
  ]
}

function seriesFromMtf(points: MtfPoint[] | undefined): ChartSeries[] {
  const safePoints = points ?? []
  return [
    { id: 'M', color: '#0f62fe', points: safePoints.map((point) => ({ x: point.frequency_lp_per_mm, y: point.mtf_y })) },
    { id: 'S', color: '#da1e28', points: safePoints.map((point) => ({ x: point.frequency_lp_per_mm, y: point.mtf_z })) },
  ]
}

function seriesFromFocusCurve(points: FocusCurvePoint[] | undefined, bestOffset?: number): ChartSeries[] {
  const curve = (points ?? [])
    .filter((point) => finitePoint(point.offset_from_sensor_mm, point.metric))
    .map((point) => ({ x: point.offset_from_sensor_mm, y: point.metric }))
  const best = Number.isFinite(bestOffset) ? curve.filter((point) => Math.abs(point.x - (bestOffset as number)) < 1.0e-9) : []
  return [
    { id: 'focus curve', color: '#0f62fe', points: curve },
    { id: 'best focus', color: '#da1e28', points: best },
  ]
}

function EvaluationPlanePanel({
  evaluationPlane,
  focusCurve,
  onWriteBack,
  canWriteBack,
  onOpenHelp,
}: {
  evaluationPlane?: EvaluationPlaneMetadata
  focusCurve: FocusCurvePoint[]
  onWriteBack: () => void
  canWriteBack: boolean
  onOpenHelp: (termId: string) => void
}) {
  const { t, i18n } = useTranslation(['analysis', 'common', 'units'])
  const warnings = evaluationPlane?.warnings ?? []
  return (
    <section className="panel image-plane-result" data-testid="evaluation-plane-panel">
      <div className="panel-heading">
        <h2>
          <TermHelp termId="evaluation_plane" fallback={t('analysis:analysis.evaluation_plane_title')} onOpenHelp={onOpenHelp} />
        </h2>
        <Button
          size="sm"
          kind="secondary"
          renderIcon={Save}
          disabled={!canWriteBack}
          onClick={onWriteBack}
          data-testid="write-back-sensor"
        >
          {t('analysis:analysis.write_back_sensor')}
        </Button>
      </div>
      {evaluationPlane ? (
        <div data-testid="evaluation-plane-metadata">
          <div className="metric-row">
            <span>{t('analysis:analysis.policy_mode')}</span>
            <strong>{evaluationPlane.policy_mode ?? t('common:common.empty.dash')}</strong>
          </div>
          <div className="metric-row">
            <span>{t('analysis:analysis.solve_status')}</span>
            <strong>{evaluationPlane.solve_status ?? t('common:common.empty.dash')}</strong>
          </div>
          <div className="metric-row">
            <span>{t('analysis:analysis.evaluation_plane_x_mm')}</span>
            <strong>{formatFixed(evaluationPlane.evaluation_plane_x_mm ?? 0, 4)} {t('units:units.mm')}</strong>
          </div>
          <div className="metric-row">
            <span>{t('analysis:analysis.offset_from_sensor_mm')}</span>
            <strong>{formatFixed(evaluationPlane.offset_from_sensor_mm ?? evaluationPlane.solved_offset_from_sensor_mm ?? 0, 4)} {t('units:units.mm')}</strong>
          </div>
          {Number.isFinite(evaluationPlane.solve_metric) ? (
            <div className="metric-row">
              <span>{t('analysis:analysis.solve_metric')}</span>
              <strong>{formatFixed(evaluationPlane.solve_metric, 6)}</strong>
            </div>
          ) : null}
          {warnings.map((issue) => {
            const rendered = renderEngineIssue(issue, i18n.language)
            return (
              <InlineNotification
                key={rendered.code}
                lowContrast
                kind={issueKind(issue.severity)}
                title={`${rendered.title} (${rendered.code})`}
                subtitle={`${rendered.message}${rendered.action ? ` ${rendered.action}` : ''}`}
              />
            )
          })}
        </div>
      ) : (
        <p className="muted">{t('analysis:analysis.evaluation_plane_empty')}</p>
      )}
      <div className="focus-curve" data-testid="focus-curve-chart">
        <h3>{t('analysis:analysis.focus_curve')}</h3>
        <ChartSvg
          series={seriesFromFocusCurve(focusCurve, evaluationPlane?.solved_offset_from_sensor_mm)}
          xLabel="offset mm"
          yLabel="metric"
          emptyLabel={t('analysis:analysis.focus_curve_empty')}
        />
      </div>
    </section>
  )
}

function AnalysisCharts({ result, onOpenHelp }: { result?: ChartAnalysisResult; onOpenHelp: (termId: string) => void }) {
  const { t, i18n } = useTranslation(['analysis'])
  const empty = t('analysis:analysis.chart_empty')
  if (!result) {
    return <p className="muted">{t('analysis:analysis.run_charts_empty')}</p>
  }
  return (
    <div className="analysis-chart-grid" data-testid="analysis-chart-grid">
      <section className="panel chart-panel chart-panel--wide">
        <h2>
          <TermHelp termId="ray_fan" fallback={termLabel('ray_fan', i18n.language)} onOpenHelp={onOpenHelp} />
        </h2>
        <div className="chart-pair">
          <ChartSvg series={seriesFromRayFan(result.rayFan?.points, 'y')} xLabel="Py" yLabel="Y mm" emptyLabel={empty} />
          <ChartSvg series={seriesFromRayFan(result.rayFan?.points, 'z')} xLabel="Pz" yLabel="Z mm" emptyLabel={empty} />
        </div>
      </section>
      <section className="panel chart-panel">
        <h2>{termLabel('distortion', i18n.language)}</h2>
        <ChartSvg series={seriesFromDistortion(result.distortion?.rows)} xLabel="field deg" yLabel="%" emptyLabel={empty} />
      </section>
      <section className="panel chart-panel">
        <h2>{termLabel('field_curvature', i18n.language)}</h2>
        <ChartSvg series={seriesFromFieldCurvature(result.fieldCurvature?.rows)} xLabel="field deg" yLabel="mm" emptyLabel={empty} />
      </section>
      <section className="panel chart-panel">
        <h2>{termLabel('relative_illumination', i18n.language)}</h2>
        <ChartSvg series={seriesFromRelativeIllumination(result.relativeIllumination?.rows)} xLabel="field deg" yLabel="%" emptyLabel={empty} />
      </section>
      <section className="panel chart-panel">
        <h2>
          <TermHelp termId="mtf" fallback={termLabel('mtf', i18n.language)} onOpenHelp={onOpenHelp} />
        </h2>
        <ChartSvg series={seriesFromMtf(result.mtf?.points)} xLabel="lp/mm" yLabel="MTF" emptyLabel={empty} />
        {result.mtf?.diffraction_included === false ? <p className="muted">{t('analysis:analysis.geometric_mtf_note')}</p> : null}
      </section>
    </div>
  )
}

function AnalysisConditionPanel({
  fields,
  wavelengths,
  samplesPerField,
  pupilDistribution,
  aimingMode,
  analysisDirty,
  trace,
  onAddField,
  onRemoveField,
  onUpdateField,
  onAddPresetWavelength,
  onAddCustomWavelength,
  onRemoveWavelength,
  onUpdateWavelength,
  onSetSamplesPerField,
  onSetPupilDistribution,
  onSetAimingMode,
}: {
  fields: AnalysisField[]
  wavelengths: WavelengthSample[]
  samplesPerField: number
  pupilDistribution: string
  aimingMode: string
  analysisDirty: boolean
  trace?: TraceResponse
  onAddField: () => void
  onRemoveField: (index: number) => void
  onUpdateField: (index: number, patch: Partial<AnalysisField>) => void
  onAddPresetWavelength: (wavelength: number) => void
  onAddCustomWavelength: (wavelength: number) => void
  onRemoveWavelength: (index: number) => void
  onUpdateWavelength: (index: number, patch: Partial<WavelengthSample>) => void
  onSetSamplesPerField: (value: number) => void
  onSetPupilDistribution: (value: string) => void
  onSetAimingMode: (value: string) => void
}) {
  const { t } = useTranslation(['settings'])
  const [presetWavelength, setPresetWavelength] = useState(String(wavelengthPresets[1].wavelength_nm))
  const [customWavelength, setCustomWavelength] = useState(546.07)

  return (
    <section className="panel analysis-conditions">
      <div className="panel-title-row">
        <h2>{t('settings:settings.analysis_conditions')}</h2>
        <Tag data-testid="analysis-dirty-status" type={analysisDirty ? 'magenta' : 'green'}>
          {analysisDirty ? t('settings:settings.analysis_dirty') : t('settings:settings.analysis_clean')}
        </Tag>
      </div>
      {analysisDirty && trace ? <InlineNotification lowContrast kind="warning" title={t('settings:settings.stale_results')} subtitle={t('settings:settings.stale_results_detail')} /> : null}

      <div className="condition-group">
        <div className="condition-heading">
          <h3>{t('settings:settings.fields')}</h3>
          <Button size="sm" kind="ghost" renderIcon={Add} onClick={onAddField}>
            {t('settings:settings.add_field')}
          </Button>
        </div>
        <div className="field-editor" data-testid="field-editor">
          {fields.map((field, index) => (
            <div className="condition-row field-row" key={`${field.id}-${index}`} data-testid="field-row">
              <TextInput
                id={`field-${index}-id`}
                labelText={t('settings:settings.field_id')}
                value={field.id}
                onChange={(event) => onUpdateField(index, { id: event.target.value })}
              />
              <NumberInput
                id={`field-${index}-theta-y`}
                label={t('settings:settings.theta_y_deg')}
                step={0.1}
                value={field.theta_y_deg}
                onChange={(_, data) => onUpdateField(index, { theta_y_deg: numericInputValue(data.value, field.theta_y_deg) })}
              />
              <NumberInput
                id={`field-${index}-theta-z`}
                label={t('settings:settings.theta_z_deg')}
                step={0.1}
                value={field.theta_z_deg}
                onChange={(_, data) => onUpdateField(index, { theta_z_deg: numericInputValue(data.value, field.theta_z_deg) })}
              />
              <Button
                hasIconOnly
                size="sm"
                kind="ghost"
                renderIcon={TrashCan}
                iconDescription={t('settings:settings.remove_field')}
                disabled={fields.length <= 1}
                onClick={() => onRemoveField(index)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="condition-group">
        <div className="condition-heading">
          <h3>{t('settings:settings.wavelengths')}</h3>
        </div>
        <div className="condition-row wavelength-add-row">
          <Select id="wavelength-preset" labelText={t('settings:settings.wavelength_preset')} value={presetWavelength} onChange={(event) => setPresetWavelength(event.target.value)}>
            {wavelengthPresets.map((preset) => (
              <SelectItem key={preset.id} value={String(preset.wavelength_nm)} text={preset.label} />
            ))}
          </Select>
          <Button size="sm" kind="ghost" renderIcon={Add} onClick={() => onAddPresetWavelength(Number(presetWavelength))}>
            {t('settings:settings.add_preset')}
          </Button>
        </div>
        <div className="condition-row wavelength-add-row">
          <NumberInput
            id="custom-wavelength"
            label={t('settings:settings.custom_wavelength_nm')}
            min={300}
            max={1100}
            step={0.01}
            value={customWavelength}
            onChange={(_, data) => setCustomWavelength(numericInputValue(data.value, customWavelength))}
          />
          <Button size="sm" kind="ghost" renderIcon={Add} onClick={() => onAddCustomWavelength(customWavelength)}>
            {t('settings:settings.add_custom')}
          </Button>
        </div>
        <div className="wavelength-list" data-testid="wavelength-list">
          {wavelengths.map((sample, index) => (
            <div className="condition-row wavelength-row" key={`${sample.wavelength_nm}-${index}`} data-testid="wavelength-row">
              <NumberInput
                id={`wavelength-${index}-nm`}
                label={t('settings:settings.wavelength_nm')}
                min={300}
                max={1100}
                step={0.01}
                value={sample.wavelength_nm}
                onChange={(_, data) => onUpdateWavelength(index, { wavelength_nm: numericInputValue(data.value, sample.wavelength_nm) })}
              />
              <NumberInput
                id={`wavelength-${index}-weight`}
                label={t('settings:settings.weight')}
                min={0}
                max={10}
                step={0.1}
                value={sample.weight}
                onChange={(_, data) => onUpdateWavelength(index, { weight: numericInputValue(data.value, sample.weight) })}
              />
              <Button
                hasIconOnly
                size="sm"
                kind="ghost"
                renderIcon={TrashCan}
                iconDescription={t('settings:settings.remove_wavelength')}
                disabled={wavelengths.length <= 1}
                onClick={() => onRemoveWavelength(index)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="condition-group">
        <h3>{t('settings:settings.ray_sampling')}</h3>
        <NumberInput
          id="samples"
          label={t('settings:settings.rays_per_field')}
          min={1}
          max={4096}
          step={2}
          value={samplesPerField}
          onChange={(_, data) => onSetSamplesPerField(numericInputValue(data.value, samplesPerField))}
        />
        <Select id="pupil-distribution" labelText={t('settings:settings.pupil_distribution')} value={pupilDistribution} onChange={(event) => onSetPupilDistribution(event.target.value)}>
          <SelectItem value="grid" text="grid" />
          <SelectItem value="hexapolar" text="hexapolar" />
          <SelectItem value="random" text="random" />
          <SelectItem value="fan_y" text="fan_y" />
          <SelectItem value="fan_z" text="fan_z" />
        </Select>
        <Select id="aiming" labelText={t('settings:settings.ray_aiming')} value={aimingMode} onChange={(event) => onSetAimingMode(event.target.value)}>
          <SelectItem value="paraxial" text="paraxial" />
          <SelectItem value="full" text="full" />
          <SelectItem value="off" text="off" />
        </Select>
      </div>

      <EvaluatedFieldList trace={trace} fields={fields} />
    </section>
  )
}

function ImagePlanePolicyPanel({
  policy,
  disabled,
  onUpdatePolicy,
  onSolve,
  isSolving,
}: {
  policy: ImagePlanePolicyDraft
  disabled: boolean
  onUpdatePolicy: (patch: Partial<ImagePlanePolicyDraft>) => void
  onSolve: () => void
  isSolving: boolean
}) {
  const { t } = useTranslation(['settings'])
  return (
    <section className="panel image-plane-policy" data-testid="image-plane-policy-panel">
      <div className="panel-title-row">
        <h2>{t('settings:settings.image_plane_policy')}</h2>
        {disabled ? <Tag type="gray">{t('settings:settings.not_applicable_afocal')}</Tag> : null}
      </div>
      {disabled ? <p className="muted">{t('settings:settings.image_plane_policy_afocal_detail')}</p> : null}
      <div className="condition-group">
        <Select
          id="image-plane-policy-mode"
          labelText={t('settings:settings.policy_mode')}
          value={policy.mode}
          disabled={disabled}
          onChange={(event) => onUpdatePolicy({ mode: event.target.value as ImagePlanePolicyMode })}
        >
          <SelectItem value="fixed_sensor" text="fixed_sensor" />
          <SelectItem value="paraxial_image" text="paraxial_image" />
          <SelectItem value="best_focus_rms" text="best_focus_rms" />
          <SelectItem value="best_focus_mtf" text="best_focus_mtf" />
          <SelectItem value="custom_offset" text="custom_offset" />
          <SelectItem value="sweep" text="sweep" />
        </Select>
        <Select
          id="image-plane-apply-to"
          labelText={t('settings:settings.apply_to')}
          value={policy.applyTo}
          disabled={disabled}
          onChange={(event) => onUpdatePolicy({ applyTo: event.target.value as ImagePlanePolicyApplyTo })}
        >
          <SelectItem value="evaluation_plane" text="evaluation_plane" />
          <SelectItem value="focus_group" text="focus_group" />
          <SelectItem value="report_only" text="report_only" />
        </Select>
        <NumberInput
          id="image-plane-custom-offset"
          label={t('settings:settings.custom_offset_mm')}
          step={0.01}
          value={policy.customOffsetMm}
          disabled={disabled || policy.mode !== 'custom_offset'}
          onChange={(_, data) => onUpdatePolicy({ customOffsetMm: numericInputValue(data.value, policy.customOffsetMm) })}
        />
        <NumberInput
          id="image-plane-frequency"
          label={t('settings:settings.mtf_frequency_lpmm')}
          min={0}
          step={1}
          value={policy.frequencyLpMm}
          disabled={disabled}
          onChange={(_, data) => onUpdatePolicy({ frequencyLpMm: Math.max(0, numericInputValue(data.value, policy.frequencyLpMm)) })}
        />
        <div className="condition-row focus-search-row">
          <NumberInput
            id="image-plane-search-range"
            label={t('settings:settings.search_range_mm')}
            min={0.1}
            step={0.1}
            value={policy.searchRangeMm}
            disabled={disabled || !['best_focus_rms', 'best_focus_mtf', 'sweep'].includes(policy.mode)}
            onChange={(_, data) => onUpdatePolicy({ searchRangeMm: Math.max(0.1, numericInputValue(data.value, policy.searchRangeMm)) })}
          />
          <NumberInput
            id="image-plane-sweep-steps"
            label={t('settings:settings.sweep_steps')}
            min={2}
            step={1}
            value={policy.searchSteps}
            disabled={disabled || policy.mode !== 'sweep'}
            onChange={(_, data) => onUpdatePolicy({ searchSteps: Math.max(2, Math.round(numericInputValue(data.value, policy.searchSteps))) })}
          />
        </div>
        <Button size="sm" renderIcon={Play} disabled={disabled || isSolving} onClick={onSolve}>
          {t('settings:settings.solve_image_plane')}
        </Button>
      </div>
    </section>
  )
}

export function App() {
  const { t, i18n } = useTranslation(['common', 'settings', 'analysis', 'layoutView'])
  const [apiBase, setApiBase] = useState(defaultApiBase)
  const [selectedPresetId, setSelectedPresetId] = useState('P001')
  const [activeTab, setActiveTab] = useState<TabKey>('preview')
  const [samplesPerField, setSamplesPerField] = useState(9)
  const [analysisFields, setAnalysisFields] = useState<AnalysisField[]>(() => cloneFields(defaultFieldSet))
  const [wavelengths, setWavelengths] = useState<WavelengthSample[]>(() => initialWavelengths(presets[0].system))
  const [pupilDistribution, setPupilDistribution] = useState('grid')
  const [aimingMode, setAimingMode] = useState('paraxial')
  const [imagePlanePolicy, setImagePlanePolicy] = useState<ImagePlanePolicyDraft>(() => ({ ...defaultImagePlanePolicy }))
  const imagePlanePolicyRef = useRef<ImagePlanePolicyDraft>(imagePlanePolicy)
  const [zoomPositionId, setZoomPositionId] = useState('')
  const [focusGroupId, setFocusGroupId] = useState('')
  const [focusShiftMm, setFocusShiftMm] = useState(0)
  const [decenterTiltDraft, setDecenterTiltDraft] = useState<DecenterTiltDraft>(() => ({ ...defaultDecenterTiltDraft }))
  const decenterTiltDraftRef = useRef<DecenterTiltDraft>({ ...defaultDecenterTiltDraft })
  const [runtimeConfiguration, setRuntimeConfiguration] = useState<RuntimeConfiguration>({})
  const runtimeConfigurationRef = useRef<RuntimeConfiguration>({})
  const [irisRadiusMm, setIrisRadiusMm] = useState(() => apertureStopRadius(presets[0].system) ?? 1)
  const [irisMaxRadiusMm, setIrisMaxRadiusMm] = useState(() => apertureStopRadius(presets[0].system) ?? 1)
  const irisRadiusRef = useRef(irisRadiusMm)
  const sliderPreviewTimerRef = useRef<number | undefined>()
  const motionPreviewSequenceRef = useRef(0)
  const [sliderPreviewPending, setSliderPreviewPending] = useState(false)
  const [analysisDirty, setAnalysisDirty] = useState(false)
  const [systemDirty, setSystemDirty] = useState(false)
  const [system, setSystem] = useState<OpticalSystem>(() => cloneSystem(presets[0].system))
  const [systemId, setSystemId] = useState<string | null>(null)
  const [systemHash, setSystemHash] = useState<string | null>(null)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [trace, setTrace] = useState<TraceResponse | undefined>()
  const [chartResult, setChartResult] = useState<ChartAnalysisResult | undefined>()
  const [evaluationPlane, setEvaluationPlane] = useState<EvaluationPlaneMetadata | undefined>()
  const [focusCurve, setFocusCurve] = useState<FocusCurvePoint[]>([])
  const [focusResult, setFocusResult] = useState<BestFocusResponse | undefined>()
  const [lastRequest, setLastRequest] = useState<unknown>(null)
  const [lastResponse, setLastResponse] = useState<unknown>(null)
  const [helpTermId, setHelpTermId] = useState<string | null>(() => new URLSearchParams(window.location.search).get('help'))
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [compareLeftId, setCompareLeftId] = useState('')
  const [compareRightId, setCompareRightId] = useState('')
  const [exportLanguage, setExportLanguage] = useState<SupportedLanguage>('ja')

  const preset = presets.find((item) => item.id === selectedPresetId) ?? presets[0]
  const policyDisabled = system.system_type === 'afocal'

  const health = useQuery({ queryKey: ['health', apiBase], queryFn: () => getHealth(apiBase), retry: false })
  const meta = useQuery({ queryKey: ['meta', apiBase], queryFn: () => getMeta(apiBase), retry: false })

  const markAnalysisDirty = () => setAnalysisDirty(true)

  const updateField = (index: number, patch: Partial<AnalysisField>) => {
    setAnalysisFields((current) => current.map((field, fieldIndex) => (fieldIndex === index ? { ...field, ...patch } : field)))
    markAnalysisDirty()
  }

  const addField = () => {
    setAnalysisFields((current) => [...current, { id: uniqueFieldId(current), type: 'angular', theta_y_deg: 0, theta_z_deg: 0 }])
    markAnalysisDirty()
  }

  const removeField = (index: number) => {
    setAnalysisFields((current) => (current.length <= 1 ? current : current.filter((_, fieldIndex) => fieldIndex !== index)))
    markAnalysisDirty()
  }

  const addWavelength = (wavelength: number) => {
    setWavelengths((current) => [...current, { wavelength_nm: wavelength, weight: 1 }])
    markAnalysisDirty()
  }

  const updateWavelength = (index: number, patch: Partial<WavelengthSample>) => {
    setWavelengths((current) => current.map((sample, sampleIndex) => (sampleIndex === index ? { ...sample, ...patch } : sample)))
    markAnalysisDirty()
  }

  const removeWavelength = (index: number) => {
    setWavelengths((current) => (current.length <= 1 ? current : current.filter((_, sampleIndex) => sampleIndex !== index)))
    markAnalysisDirty()
  }

  const updateSamplesPerField = (value: number) => {
    setSamplesPerField(Math.max(1, Math.round(value)))
    markAnalysisDirty()
  }

  const updatePupilDistribution = (value: string) => {
    setPupilDistribution(value)
    markAnalysisDirty()
  }

  const updateAimingMode = (value: string) => {
    setAimingMode(value)
    markAnalysisDirty()
  }

  const updateImagePlanePolicy = (patch: Partial<ImagePlanePolicyDraft>) => {
    setImagePlanePolicy((current) => {
      const next = { ...current, ...patch }
      imagePlanePolicyRef.current = next
      return next
    })
    markAnalysisDirty()
  }

  const resetMotionControls = (nextSystem: OpticalSystem) => {
    const nextZoom = nextSystem.zoom_positions?.[0]?.id ?? ''
    const nextGroup = motionGroupIds(nextSystem)[0] ?? ''
    const nextDecenterTilt = { ...defaultDecenterTiltDraft, targetGroupId: decenterTiltGroupIds(nextSystem)[0] ?? '' }
    const nextIris = apertureStopRadius(nextSystem) ?? 1
    setZoomPositionId(nextZoom)
    setFocusGroupId(nextGroup)
    setFocusShiftMm(0)
    setDecenterTiltDraft(nextDecenterTilt)
    decenterTiltDraftRef.current = nextDecenterTilt
    const nextConfiguration = makeRuntimeConfiguration(nextSystem, nextZoom, nextGroup, 0, nextDecenterTilt)
    runtimeConfigurationRef.current = nextConfiguration
    setRuntimeConfiguration(nextConfiguration)
    irisRadiusRef.current = nextIris
    setIrisRadiusMm(nextIris)
    setIrisMaxRadiusMm(nextIris)
  }

  const markSystemChanged = (nextSystem: OpticalSystem) => {
    setSystem(nextSystem)
    setSystemDirty(true)
    setSystemId(null)
    setSystemHash(null)
    setValidation(null)
    setTrace(undefined)
    setChartResult(undefined)
    setEvaluationPlane(undefined)
    setFocusCurve([])
    setFocusResult(undefined)
    setAnalysisDirty(true)
  }

  const addGroup = () => {
    const nextSystem = cloneSystem(system)
    nextSystem.groups = [...(nextSystem.groups ?? []), defaultGroupFor(nextSystem)]
    markSystemChanged(nextSystem)
  }

  const updateGroup = (index: number, patch: Partial<OpticalGroup>) => {
    const nextSystem = cloneSystem(system)
    const groups = nextSystem.groups ?? []
    nextSystem.groups = groups.map((group, groupIndex) => (groupIndex === index ? { ...group, ...patch } : group))
    markSystemChanged(nextSystem)
  }

  const removeGroup = (index: number) => {
    const nextSystem = cloneSystem(system)
    nextSystem.groups = (nextSystem.groups ?? []).filter((_, groupIndex) => groupIndex !== index)
    markSystemChanged(nextSystem)
  }

  const readImagePlanePolicyForm = () => {
    const modeElement = document.getElementById('image-plane-policy-mode') as HTMLSelectElement | null
    const applyToElement = document.getElementById('image-plane-apply-to') as HTMLSelectElement | null
    const next = {
      ...imagePlanePolicyRef.current,
      mode: (modeElement?.value as ImagePlanePolicyMode | undefined) ?? imagePlanePolicyRef.current.mode,
      applyTo: (applyToElement?.value as ImagePlanePolicyApplyTo | undefined) ?? imagePlanePolicyRef.current.applyTo,
    }
    imagePlanePolicyRef.current = next
    return next
  }

  const ensureRegisteredSystem = async () => {
    if (systemId) return systemId
    const result = await registerSystem(apiBase, system)
    setSystemId(result.system_id)
    setSystemHash(result.system_hash)
    setSystemDirty(false)
    return result.system_id
  }

  const makeAnalysisRequest = (
    id: string,
    overrides: { configuration?: RuntimeConfiguration; samplesPerField?: number; aimingMode?: string } = {},
  ): AnalysisRequest => ({
    system_id: id,
    fields: analysisFields,
    ray_sampling: {
      samples_per_field: overrides.samplesPerField ?? samplesPerField,
      pupil_distribution: pupilDistribution,
      ray_aiming: { mode: overrides.aimingMode ?? aimingMode },
    },
    wavelengths_nm: wavelengths.map((sample) => sample.wavelength_nm),
    wavelength_weights: wavelengths,
    configuration: overrides.configuration ?? runtimeConfiguration,
    frequencies_lp_per_mm: [0, 10, 20, 40, 80],
    ...(policyDisabled ? {} : { image_plane_policy: makePolicy(readImagePlanePolicyForm(), analysisFields, wavelengths) }),
    options: { store_path: true, profiling: true },
  })

  const applyPreviewResult = (result: TraceResponse, clean: boolean) => {
    setTrace(result)
    const nextEvaluationPlane = extractEvaluationPlane(result)
    setEvaluationPlane(nextEvaluationPlane)
    setFocusCurve(nextEvaluationPlane?.focus_curve ?? [])
    setFocusResult(undefined)
    setLastResponse(result)
    setAnalysisDirty(!clean)
    setActiveTab('preview')
  }

  const resolvePreviewSystemId = async (previewSystem: OpticalSystem, rememberRegistration: boolean) => {
    if (previewSystem === system && systemId) return systemId
    const result = await registerSystem(apiBase, previewSystem)
    if (rememberRegistration) {
      setSystemId(result.system_id)
      setSystemHash(result.system_hash)
      setSystemDirty(false)
    }
    return result.system_id
  }

  const runMotionPreview = async (
    configuration: RuntimeConfiguration,
    lowResolution: boolean,
    previewSystem: OpticalSystem = system,
    rememberRegistration = !lowResolution,
  ) => {
    const sequence = motionPreviewSequenceRef.current + 1
    motionPreviewSequenceRef.current = sequence
    setSliderPreviewPending(true)
    try {
      const id = await resolvePreviewSystemId(previewSystem, rememberRegistration)
      const request = makeAnalysisRequest(id, {
        configuration,
        ...(lowResolution ? { samplesPerField: sliderPreviewSamplesPerField, aimingMode: 'paraxial' } : {}),
      })
      setLastRequest(request)
      const result = await runPreview(apiBase, request)
      if (sequence !== motionPreviewSequenceRef.current) return
      applyPreviewResult(result, !lowResolution)
    } catch (error) {
      if (sequence !== motionPreviewSequenceRef.current) return
      setLastResponse(getApiIssue(error))
    } finally {
      if (sequence === motionPreviewSequenceRef.current) setSliderPreviewPending(false)
    }
  }

  const scheduleMotionPreview = (configuration: RuntimeConfiguration, previewSystem: OpticalSystem = system) => {
    if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
    sliderPreviewTimerRef.current = window.setTimeout(() => {
      void runMotionPreview(configuration, true, previewSystem, false)
    }, sliderPreviewDebounceMs)
  }

  const setMotionConfiguration = (nextZoom: string, nextFocusGroup: string, nextFocusShift: number, commit = false) => {
    const nextConfiguration = makeRuntimeConfiguration(system, nextZoom, nextFocusGroup, nextFocusShift, decenterTiltDraftRef.current)
    setZoomPositionId(nextZoom)
    setFocusGroupId(nextFocusGroup)
    setFocusShiftMm(nextFocusShift)
    runtimeConfigurationRef.current = nextConfiguration
    setRuntimeConfiguration(nextConfiguration)
    markAnalysisDirty()
    scheduleMotionPreview(nextConfiguration)
    if (commit) {
      if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
      void runMotionPreview(nextConfiguration, false)
    }
  }

  const commitMotionConfiguration = () => {
    if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
    void runMotionPreview(runtimeConfigurationRef.current, false)
  }

  const setApertureRadius = (value: number, commit = false) => {
    const nextRadius = Math.max(0.1, value)
    const nextSystem = withApertureStopRadius(system, nextRadius)
    if (!nextSystem) return
    irisRadiusRef.current = nextRadius
    setIrisRadiusMm(nextRadius)
    markSystemChanged(nextSystem)
    scheduleMotionPreview(runtimeConfigurationRef.current, nextSystem)
    if (commit) {
      if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
      void runMotionPreview(runtimeConfigurationRef.current, false, nextSystem, true)
    }
  }

  const commitApertureRadius = () => {
    const nextSystem = withApertureStopRadius(system, irisRadiusRef.current)
    if (!nextSystem) return
    if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
    void runMotionPreview(runtimeConfigurationRef.current, false, nextSystem, true)
  }

  const updateDecenterTilt = (patch: Partial<DecenterTiltDraft>, commit = false) => {
    const nextDraft = { ...decenterTiltDraftRef.current, ...patch }
    decenterTiltDraftRef.current = nextDraft
    setDecenterTiltDraft(nextDraft)
    const nextConfiguration = makeRuntimeConfiguration(system, zoomPositionId, focusGroupId, focusShiftMm, nextDraft)
    runtimeConfigurationRef.current = nextConfiguration
    setRuntimeConfiguration(nextConfiguration)
    markAnalysisDirty()
    scheduleMotionPreview(nextConfiguration)
    if (commit) {
      if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
      void runMotionPreview(nextConfiguration, false)
    }
  }

  const commitDecenterTilt = () => {
    if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
    void runMotionPreview(runtimeConfigurationRef.current, false)
  }

  const validateMutation = useMutation({
    mutationFn: async () => validateSystem(apiBase, system),
    onSuccess: (result) => {
      setValidation(result)
      setLastRequest(system)
      setLastResponse(result)
    },
    onError: (error) => {
      setLastResponse(getApiIssue(error))
    },
  })

  const registerMutation = useMutation({
    mutationFn: async () => {
      const validationResult = await validateSystem(apiBase, system)
      setValidation(validationResult)
      if (validationResult.status === 'error') throw new EngineApiError(validationResult.issues[0], 400)
      return registerSystem(apiBase, system)
    },
    onSuccess: (result) => {
      setSystemId(result.system_id)
      setSystemHash(result.system_hash)
      setSystemDirty(false)
      setLastRequest(system)
      setLastResponse(result)
    },
    onError: (error) => {
      setLastResponse(getApiIssue(error))
    },
  })

  const previewMutation = useMutation({
    mutationFn: async () => {
      const id = await ensureRegisteredSystem()
      const request = makeAnalysisRequest(id)
      setLastRequest(request)
      return runPreview(apiBase, request)
    },
    onSuccess: (result) => {
      applyPreviewResult(result, true)
    },
    onError: (error) => {
      setLastResponse(getApiIssue(error))
    },
  })

  const chartsMutation = useMutation({
    mutationFn: async () => {
      const id = await ensureRegisteredSystem()
      const request = makeAnalysisRequest(id)
      setLastRequest(request)
      return runChartAnalyses(apiBase, request)
    },
    onSuccess: (result) => {
      setChartResult(result)
      const nextEvaluationPlane = extractEvaluationPlane(result)
      setEvaluationPlane(nextEvaluationPlane)
      setFocusCurve(nextEvaluationPlane?.focus_curve ?? [])
      setFocusResult(undefined)
      setLastResponse(result)
      setAnalysisDirty(false)
      setActiveTab('analysis')
    },
    onError: (error) => {
      setLastResponse(getApiIssue(error))
    },
  })

  const focusMutation = useMutation({
    mutationFn: async () => {
      const id = await ensureRegisteredSystem()
      const request = makeAnalysisRequest(id)
      setLastRequest(request)
      return runBestFocus(apiBase, request)
    },
    onSuccess: (result: BestFocusResponse) => {
      setEvaluationPlane(result.evaluation_plane)
      setFocusCurve(result.focus_curve ?? result.evaluation_plane.focus_curve ?? [])
      setFocusResult(result)
      setLastResponse(result)
      setAnalysisDirty(false)
      setActiveTab('analysis')
    },
    onError: (error) => {
      setLastResponse(getApiIssue(error))
    },
  })

  const running = validateMutation.isPending || registerMutation.isPending || previewMutation.isPending || chartsMutation.isPending || focusMutation.isPending
  const engineOnline = health.data?.status === 'ok'
  const apiMajor = meta.data?.api_schema_version?.split('.')[0]
  const versionBlocked = Boolean(apiMajor && apiMajor !== '2')
  const healthIssue = getApiIssue(health.error)
  const mutationIssue = getApiIssue(validateMutation.error ?? registerMutation.error ?? previewMutation.error ?? chartsMutation.error ?? focusMutation.error)

  const saveSnapshot = async () => {
    const snapshotId = `snapshot-${snapshots.length + 1}`
    const artifactUris = collectArtifactUris({ trace, chartResult, focusResult })
    const artifacts: Record<string, unknown> = {}
    const missingArtifacts: string[] = []
    for (const [key, uri] of Object.entries(artifactUris)) {
      try {
        artifacts[key] = await fetchArtifact(apiBase, uri)
      } catch {
        missingArtifacts.push(key)
      }
    }
    const snapshot: Snapshot = {
      id: snapshotId,
      created_at: isoNow(),
      preset_id: preset.id,
      system_name: system.name,
      system_hash: systemHash,
      system: cloneSystem(system),
      analysis: {
        fields: cloneFields(analysisFields),
        wavelengths: wavelengths.map((sample) => ({ ...sample })),
        samples_per_field: samplesPerField,
        pupil_distribution: pupilDistribution,
        aiming_mode: aimingMode,
        ...(policyDisabled ? {} : { image_plane_policy: makePolicy(readImagePlanePolicyForm(), analysisFields, wavelengths) }),
        evaluation_plane: evaluationPlane,
      },
      results: {
        trace,
        charts: chartResult,
        focus: focusResult,
      },
      artifacts,
      artifact_uris: artifactUris,
      missing_artifacts: missingArtifacts,
      partial: missingArtifacts.length > 0,
      metrics: {
        rms_spot_radius: null,
        ray_count: trace?.status.length ?? 0,
        arrived: traceArrived(trace),
        mtf_points: chartResult?.mtf?.points.length ?? 0,
        ri_rows: chartResult?.relativeIllumination?.rows.length ?? 0,
        focus_curve_points: focusCurve.length,
      },
      trace_status: trace?.status ?? [],
    }
    setSnapshots((current) => [snapshot, ...current])
    setCompareLeftId((current) => current || snapshotId)
    setCompareRightId((current) => current || (compareLeftId ? snapshotId : ''))
    setActiveTab('compare')
  }

  const exportSnapshotJson = (snapshot: Snapshot) => {
    downloadText(`${snapshot.id}.json`, JSON.stringify(snapshot, null, 2), 'application/json')
  }

  const writeBackSensor = () => {
    const offset = evaluationPlane?.solved_offset_from_sensor_mm ?? evaluationPlane?.offset_from_sensor_mm
    if (!Number.isFinite(offset)) return
    if (!window.confirm(t('analysis:analysis.write_back_confirm'))) return
    const nextSystem = applySensorOffset(system, offset as number)
    if (!nextSystem) return
    markSystemChanged(nextSystem)
    setLastRequest(nextSystem)
    setLastResponse({ status: 'system_dirty', updated_surface: nextSystem.surfaces[sensorIndex(nextSystem) - 1]?.id, offset_mm: offset })
  }

  return (
    <div className="app-shell">
      <Header aria-label={t('common.app.aria')}>
        <HeaderName href="#" prefix={t('common.app.prefix')}>
          {t('common.app.name')}
        </HeaderName>
        <div className="header-status">
          <Tag type={engineOnline ? 'green' : 'red'}>{engineOnline ? t('common.status.engine_ok') : t('common.status.engine_offline')}</Tag>
          <Tag type={versionBlocked ? 'red' : 'blue'}>{t('common.status.api', { version: meta.data?.api_schema_version ?? t('common.status.unknown') })}</Tag>
          <Tag type={statusTone(validation?.status)}>{validation?.status ?? t('common.status.not_validated')}</Tag>
          {systemDirty ? <Tag type="magenta" data-testid="system-dirty-status">{t('common.status.system_dirty')}</Tag> : null}
        </div>
      </Header>

      <main className="workbench-grid">
        <aside className="left-pane">
          <section className="panel">
            <Dropdown
              id="preset"
              titleText={t('common.preset.label')}
              label={t('common.preset.label')}
              items={presets}
              itemToString={(item) => (item ? `${item.id} ${presetLabel(item.id, item.name, t)}` : '')}
              selectedItem={preset}
              onChange={({ selectedItem }) => {
                if (selectedItem) {
                  setSelectedPresetId(selectedItem.id)
                  setSystem(cloneSystem(selectedItem.system))
                  setSystemId(null)
                  setSystemHash(null)
                  setTrace(undefined)
                  setChartResult(undefined)
                  setEvaluationPlane(undefined)
                  setFocusCurve([])
                  setFocusResult(undefined)
                  setValidation(null)
                  setAnalysisFields(cloneFields(defaultFieldSet))
                  setWavelengths(initialWavelengths(selectedItem.system))
                  setSamplesPerField(9)
                  setPupilDistribution('grid')
                  setAimingMode('paraxial')
                  imagePlanePolicyRef.current = { ...defaultImagePlanePolicy }
                  setImagePlanePolicy(imagePlanePolicyRef.current)
                  resetMotionControls(selectedItem.system)
                  setAnalysisDirty(false)
                  setSystemDirty(false)
                }
              }}
            />
            <p className="muted">{presetSummary(preset.id, preset.summary, t)}</p>
            <div className="button-row">
              <Button size="sm" kind="secondary" renderIcon={Checkmark} disabled={!engineOnline || running || versionBlocked} onClick={() => validateMutation.mutate()}>
                {t('common.buttons.validate')}
              </Button>
              <Button size="sm" kind="secondary" renderIcon={Renew} disabled={!engineOnline || running || versionBlocked} onClick={() => registerMutation.mutate()}>
                {t('common.buttons.register')}
              </Button>
            </div>
          </section>

          <section className="panel">
            <h2>{t('common.system.title')}</h2>
            <div className="metric-row">
              <span>{t('common.system.name')}</span>
              <strong>{system.name}</strong>
            </div>
            <div className="metric-row">
              <span>{t('common.system.type')}</span>
              <strong>{system.system_type ?? 'focal'}</strong>
            </div>
            <div className="metric-row">
              <span>{t('common.system.surfaces')}</span>
              <strong>{formatInteger(system.surfaces.length)}</strong>
            </div>
            <div className="metric-row">
              <span>{t('common.system.system_id')}</span>
              <code>{systemId ? `${systemId.slice(0, 18)}...` : t('common.empty.dash')}</code>
            </div>
          </section>
        </aside>

        <section className="center-pane">
          <ContentSwitcher selectedIndex={tabKeys.indexOf(activeTab)} onChange={({ name }) => setActiveTab(name as TabKey)}>
            {tabKeys.map((key) => (
              <Switch key={key} name={key} text={t(`common.tabs.${key}`)} />
            ))}
          </ContentSwitcher>

          {activeTab === 'system' ? (
            <div className="panel large-panel">
              <SurfaceTable surfaces={system.surfaces} onOpenHelp={setHelpTermId} />
              <GroupPanel system={system} onAddGroup={addGroup} onUpdateGroup={updateGroup} onRemoveGroup={removeGroup} onOpenHelp={setHelpTermId} />
            </div>
          ) : null}

          {activeTab === 'preview' ? (
            <div className="preview-stack">
              <div className="panel large-panel">
                <div className="panel-heading">
                  <h2>{t('layoutView:layoutView.optical_layout')}</h2>
                  <div className="panel-actions">
                    <Button size="sm" kind="secondary" renderIcon={Save} disabled={!trace} onClick={() => void saveSnapshot()}>
                      {t('common.buttons.save_snapshot')}
                    </Button>
                    <Button size="sm" renderIcon={Play} disabled={!engineOnline || running || versionBlocked} onClick={() => previewMutation.mutate()}>
                      {t('common.buttons.run_preview')}
                    </Button>
                  </div>
                </div>
                <LayoutView system={system} trace={trace} evaluationPlane={evaluationPlane} configuration={runtimeConfiguration} />
              </div>
              <div className="result-band">
                <div className="panel">
                  <h2>{termLabel('spot_diagram', i18n.language)}</h2>
                  <SpotStrip trace={trace} />
                </div>
                <div className="panel">
                  <h2>{t('analysis:analysis.trace_summary')}</h2>
                  <div className="metric-row">
                    <TermHelp termId="ray_fan" fallback={t('analysis:analysis.rays')} onOpenHelp={setHelpTermId} />
                    <strong>{formatInteger(trace?.status.length ?? 0)}</strong>
                  </div>
                  <div className="metric-row">
                    <TermHelp termId="sensor" fallback={t('analysis:analysis.arrived')} onOpenHelp={setHelpTermId} />
                    <strong>{formatInteger(traceArrived(trace))}</strong>
                  </div>
                  <div className="metric-row">
                    <TermHelp termId="ray_aiming" fallback={t('analysis:analysis.aiming')} onOpenHelp={setHelpTermId} />
                    <strong>{String(trace?.metadata?.ray_aiming_mode ?? aimingMode)}</strong>
                  </div>
                  <div className="metric-row">
                    <TermHelp termId="merit" fallback={t('analysis:analysis.trace_ms')} onOpenHelp={setHelpTermId} />
                    <strong>
                      {formatFixed((trace?.metadata?.profiling as Record<string, number> | undefined)?.trace_ms ?? 0, 3)} {t('units:units.ms')}
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {activeTab === 'analysis' ? (
            <div className="analysis-stack">
              <div className="panel large-panel">
                <div className="panel-heading">
                  <div>
                    <h2>{t('analysis:analysis.analysis_charts_title')}</h2>
                    <p className="muted">{t('analysis:analysis.analysis_charts_summary')}</p>
                  </div>
                  <Button size="sm" renderIcon={Play} disabled={!engineOnline || running || versionBlocked} onClick={() => chartsMutation.mutate()}>
                    {t('analysis:analysis.run_charts')}
                  </Button>
                  <Button size="sm" kind="secondary" renderIcon={Save} disabled={!trace && !chartResult && !focusResult} onClick={() => void saveSnapshot()}>
                    {t('common.buttons.save_snapshot')}
                  </Button>
                </div>
              </div>
              <EvaluationPlanePanel
                evaluationPlane={evaluationPlane}
                focusCurve={focusCurve}
                canWriteBack={Boolean(!policyDisabled && evaluationPlane && Number.isFinite(evaluationPlane.solved_offset_from_sensor_mm ?? evaluationPlane.offset_from_sensor_mm))}
                onWriteBack={writeBackSensor}
                onOpenHelp={setHelpTermId}
              />
              <AnalysisCharts result={chartResult} onOpenHelp={setHelpTermId} />
            </div>
          ) : null}

          {activeTab === 'compare' ? (
            <div className="compare-page">
              <section className="panel large-panel">
                <h2>{t('analysis:analysis.compare_placeholder_title')}</h2>
                <p>{t('analysis:analysis.compare_placeholder')}</p>
                <SnapshotList snapshots={snapshots} onExport={exportSnapshotJson} />
              </section>
              <CompareView snapshots={snapshots} leftId={compareLeftId} rightId={compareRightId} onSetLeft={setCompareLeftId} onSetRight={setCompareRightId} />
            </div>
          ) : null}

          {activeTab === 'debug' ? (
            <div className="debug-grid">
              <div className="panel raw-panel">
                <h2>{t('common.debug.request')}</h2>
                <CodeSnippet type="multi" wrapText>
                  {JSON.stringify(lastRequest ?? system, null, 2)}
                </CodeSnippet>
              </div>
              <div className="panel raw-panel">
                <h2>{t('common.debug.response')}</h2>
                <CodeSnippet type="multi" wrapText>
                  {JSON.stringify(lastResponse ?? meta.data ?? {}, null, 2)}
                </CodeSnippet>
              </div>
            </div>
          ) : null}
        </section>

        <aside className="right-pane">
          <section className="panel">
            <h2>{t('settings:settings.api')}</h2>
            <TextInput id="api-base" labelText={t('settings:settings.base_url')} value={apiBase} onChange={(event) => setApiBase(event.target.value)} />
            <Select
              id="language"
              labelText={t('common.language.label')}
              value={i18n.language}
              onChange={(event) => {
                void changeLanguage(event.target.value as SupportedLanguage)
              }}
            >
              <SelectItem value="ja" text={t('common.language.ja')} />
              <SelectItem value="en" text={t('common.language.en')} />
              <SelectItem value="pseudo" text={t('common.language.pseudo')} />
            </Select>
            {healthIssue ? (
              <InlineNotification lowContrast kind="error" title={t('settings:settings.connection')} subtitle={renderEngineIssue(healthIssue, i18n.language).message} />
            ) : null}
            {versionBlocked ? <InlineNotification lowContrast kind="error" title={t('settings:settings.version')} subtitle={t('settings:settings.version_mismatch')} /> : null}
          </section>

          <AnalysisConditionPanel
            fields={analysisFields}
            wavelengths={wavelengths}
            samplesPerField={samplesPerField}
            pupilDistribution={pupilDistribution}
            aimingMode={aimingMode}
            analysisDirty={analysisDirty}
            trace={trace}
            onAddField={addField}
            onRemoveField={removeField}
            onUpdateField={updateField}
            onAddPresetWavelength={addWavelength}
            onAddCustomWavelength={addWavelength}
            onRemoveWavelength={removeWavelength}
            onUpdateWavelength={updateWavelength}
            onSetSamplesPerField={updateSamplesPerField}
            onSetPupilDistribution={updatePupilDistribution}
            onSetAimingMode={updateAimingMode}
          />

          <ImagePlanePolicyPanel
            policy={imagePlanePolicy}
            disabled={policyDisabled}
            isSolving={focusMutation.isPending}
            onUpdatePolicy={updateImagePlanePolicy}
            onSolve={() => focusMutation.mutate()}
          />

          <GroupMotionPanel
            system={system}
            zoomPositionId={zoomPositionId}
            focusGroupId={focusGroupId}
            focusShiftMm={focusShiftMm}
            runtimeConfiguration={runtimeConfiguration}
            isPreviewing={sliderPreviewPending}
            onSetZoomPosition={(id, commit) => setMotionConfiguration(id, focusGroupId, focusShiftMm, commit)}
            onSetFocusGroup={(id, commit) => setMotionConfiguration(zoomPositionId, id, focusShiftMm, commit)}
            onSetFocusShift={(value, commit) => setMotionConfiguration(zoomPositionId, focusGroupId, value, commit)}
            onCommit={commitMotionConfiguration}
          />

          <ApertureMotionPanel
            system={system}
            irisRadiusMm={irisRadiusMm}
            irisMaxRadiusMm={irisMaxRadiusMm}
            isPreviewing={sliderPreviewPending}
            onSetIrisRadius={setApertureRadius}
            onCommit={commitApertureRadius}
            onOpenHelp={setHelpTermId}
          />

          <DecenterTiltPanel
            system={system}
            draft={decenterTiltDraft}
            runtimeConfiguration={runtimeConfiguration}
            isPreviewing={sliderPreviewPending}
            onUpdateDraft={updateDecenterTilt}
            onCommit={commitDecenterTilt}
            onOpenHelp={setHelpTermId}
          />

          <section className="panel">
            <h2>{t('settings:settings.validation')}</h2>
            {mutationIssue ? (
              <InlineNotification lowContrast kind={issueKind(mutationIssue.severity)} title={renderEngineIssue(mutationIssue, i18n.language).title} subtitle={renderEngineIssue(mutationIssue, i18n.language).message} />
            ) : null}
            {validation?.issues.length ? (
              validation.issues.map((issue) => {
                const rendered = renderEngineIssue(issue, i18n.language)
                return (
                  <InlineNotification
                    key={`${rendered.code}-${issue.surface_id ?? ''}`}
                    lowContrast
                    kind={issueKind(issue.severity)}
                    title={`${rendered.title} (${rendered.code})`}
                    subtitle={`${rendered.message}${rendered.action ? ` ${rendered.action}` : ''}`}
                  />
                )
              })
            ) : (
              <p className="muted">{validation ? t('settings:settings.no_validation_issues') : t('settings:settings.run_validation')}</p>
            )}
          </section>

          <section className="panel">
            <h2>{t('analysis:analysis.chart_export')}</h2>
            <Select id="export-language" labelText={t('analysis:analysis.export_language')} value={exportLanguage} onChange={(event) => setExportLanguage(event.target.value as SupportedLanguage)}>
              <SelectItem value="ja" text={t('common.language.ja')} />
              <SelectItem value="en" text={t('common.language.en')} />
            </Select>
            <div className="button-column">
              <Button size="sm" kind="secondary" renderIcon={Download} onClick={() => void exportChart('layout', exportLanguage, 'svg')}>
                {t('analysis:analysis.export_layout_svg')}
              </Button>
              <Button size="sm" kind="secondary" renderIcon={Download} onClick={() => void exportChart('spot', exportLanguage, 'svg')}>
                {t('analysis:analysis.export_spot_svg')}
              </Button>
              <Button size="sm" kind="ghost" renderIcon={Download} onClick={() => void exportChart('layout', exportLanguage, 'png')}>
                {t('analysis:analysis.export_layout_png')}
              </Button>
            </div>
          </section>
        </aside>
      </main>

      <HelpDrawer termId={helpTermId} onClose={() => setHelpTermId(null)} onNavigate={setHelpTermId} />
    </div>
  )
}
