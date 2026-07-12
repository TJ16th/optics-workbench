import { useRef, useState } from 'react'
import {
  Accordion,
  AccordionItem,
  Button,
  Checkbox,
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
import { presets, visualFixturePresets } from '../domain/presets'
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
  LayoutBaselineRay,
  LongitudinalAberrationPoint,
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
const decenterShiftLimitMm = 5
const presetIdCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })

function formatAsphereParameters(surface: Surface) {
  const values: string[] = []
  if (typeof surface.conic === 'number' && Number.isFinite(surface.conic)) values.push(`k=${surface.conic}`)
  Object.entries(surface.asphere_coefficients ?? {})
    .filter((entry): entry is [string, number] => typeof entry[1] === 'number' && Number.isFinite(entry[1]))
    .sort(([left], [right]) => left.localeCompare(right, undefined, { numeric: true }))
    .forEach(([key, value]) => values.push(`${key}=${value}`))
  return values.length ? values.join(', ') : '-'
}

const surfaceColumns: Array<{
  id: string
  termId?: string
  value: (surface: Surface) => string | number
}> = [
  { id: 'id', value: (row) => row.id },
  { id: 'kind', value: (row) => row.kind },
  { id: 'surface_type', value: (row) => row.surface_type ?? 'plane' },
  { id: 'radius_mm', termId: 'radius_mm', value: (row) => row.radius_mm ?? 0 },
  { id: 'asphere', value: formatAsphereParameters },
  { id: 'thickness_after_mm', termId: 'thickness_after_mm', value: (row) => row.thickness_after_mm ?? 0 },
  { id: 'material', termId: 'material', value: (row) => row.material_after ?? '-' },
  { id: 'semi_diameter_mm', termId: 'semi_diameter_mm', value: (row) => formatScalarNumber(row.aperture?.outer_semi_diameter_mm ?? row.semi_diameter_mm ?? row.aperture?.semi_diameter_mm) },
]

function cloneSystem(system: OpticalSystem): OpticalSystem {
  return JSON.parse(JSON.stringify(system))
}

function scalarNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (value && typeof value === 'object' && 'default' in value) {
    const next = Number((value as { default?: unknown }).default)
    return Number.isFinite(next) ? next : undefined
  }
  return undefined
}

function formatScalarNumber(value: unknown) {
  const next = scalarNumber(value)
  return next ?? '-'
}

function cloneFields(fields: AnalysisField[]): AnalysisField[] {
  return fields.map((field) => ({ ...field }))
}

function presetFields(preset: { recommendedFields?: AnalysisField[] }) {
  return cloneFields(preset.recommendedFields ?? defaultFieldSet)
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

function analysisRequestSummary(request: unknown) {
  const value = request as Partial<AnalysisRequest> | null | undefined
  return {
    fields: Array.isArray(value?.fields) ? value.fields : [],
    wavelengths: Array.isArray(value?.wavelengths_nm) ? value.wavelengths_nm : [],
    samplesPerField: value?.ray_sampling?.samples_per_field,
    pupilDistribution: value?.ray_sampling?.pupil_distribution,
    rayAimingMode: value?.ray_sampling?.ray_aiming?.mode,
  }
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
  // Keep group issue message keys in sync with allowedDynamicKeys in scripts/i18n-check.mjs.
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

function makeRuntimeConfiguration(system: OpticalSystem, zoomPositionId: string, focusGroupId: string, focusShiftMm: number, decenterTilt: DecenterTiltDraft, irisRadiusMm?: number): RuntimeConfiguration {
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
  if (irisRadiusMm !== undefined && Number.isFinite(irisRadiusMm) && irisRadiusMm > 0) {
    configuration.variables = { iris_radius_mm: irisRadiusMm }
  }
  return configuration
}

function apertureStopIndex(system: OpticalSystem) {
  return system.surfaces.findIndex((surface) => surface.kind === 'aperture_stop')
}

function apertureStopRadius(system: OpticalSystem) {
  const stop = system.surfaces[apertureStopIndex(system)]
  if (!stop) return null
  return scalarNumber(stop.aperture?.outer_semi_diameter_mm) ?? scalarNumber(stop.aperture?.semi_diameter_mm) ?? scalarNumber(stop.semi_diameter_mm) ?? null
}

function apertureStopRadiusForLayout(system: OpticalSystem, configuration?: RuntimeConfiguration) {
  const stop = system.surfaces[apertureStopIndex(system)]
  return stop ? surfaceSemiDiameter(stop, configuration) : null
}

function surfaceSemiDiameter(surface: Surface, configuration?: RuntimeConfiguration) {
  if (surface.kind === 'sensor') {
    const sensorWidth = scalarNumber(surface.sensor?.width_mm)
    return sensorWidth && sensorWidth > 0 ? sensorWidth / 2 : 8
  }
  if (surface.kind === 'eye_reference') {
    const eyePupilDiameter = scalarNumber(surface.eye?.pupil_diameter_mm)
    return eyePupilDiameter && eyePupilDiameter > 0 ? eyePupilDiameter / 2 : 8
  }
  if (surface.kind === 'aperture_stop' || surface.kind === 'mechanical_aperture') {
    const irisRadius = configuration?.variables?.iris_radius_mm
    if (surface.kind === 'aperture_stop' && typeof irisRadius === 'number' && Number.isFinite(irisRadius) && irisRadius > 0) return irisRadius
    return scalarNumber(surface.aperture?.outer_semi_diameter_mm) ?? scalarNumber(surface.aperture?.semi_diameter_mm) ?? scalarNumber(surface.semi_diameter_mm) ?? 8
  }
  return scalarNumber(surface.semi_diameter_mm) ?? scalarNumber(surface.aperture?.semi_diameter_mm) ?? 8
}

function groupShiftClearance(system: OpticalSystem, draft: DecenterTiltDraft, configuration?: RuntimeConfiguration) {
  const shift = Math.hypot(draft.shiftY, draft.shiftZ)
  if (!draft.targetGroupId || shift <= 1.0e-9) return null
  const group = (system.groups ?? []).find((item) => item.id === draft.targetGroupId)
  if (!group) return null
  const range = groupSurfaceRange(group, system.surfaces)
  if (range.fromIndex < 0 || range.toIndex < range.fromIndex) return null
  const groupSemiDiameters = system.surfaces
    .slice(range.fromIndex, range.toIndex + 1)
    .filter((surface) => surface.kind !== 'sensor' && surface.kind !== 'eye_reference')
    .map((surface) => surfaceSemiDiameter(surface, configuration))
    .filter((value) => Number.isFinite(value) && value > 0)
  const groupRadius = Math.min(...groupSemiDiameters)
  const stopRadius = apertureStopRadiusForLayout(system, configuration)
  if (!Number.isFinite(groupRadius) || !Number.isFinite(stopRadius)) return null
  const clearance = groupRadius - (stopRadius as number) - shift
  return { shift, clearance }
}

function presetLabel(id: string, fallback: string, t: (key: string, options?: Record<string, unknown>) => string) {
  return t(`common.preset.items.${id}.name`, { defaultValue: fallback })
}

function presetSummary(id: string, fallback: string, t: (key: string, options?: Record<string, unknown>) => string) {
  return t(`common.preset.items.${id}.summary`, { defaultValue: fallback })
}

function sortPresetsById(items: typeof presets) {
  return [...items].sort((left, right) => presetIdCollator.compare(left.id, right.id))
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

function surfaceSagMm(surface: Surface, rayHeightMm: number) {
  const radius = surface.radius_mm ?? 0
  if (!Number.isFinite(radius) || Math.abs(radius) < 1.0e-12) return 0
  const r = Math.abs(rayHeightMm)
  const surfaceType = surface.surface_type ?? 'plane'
  if (surfaceType === 'aspherical_even') {
    const c = 1 / radius
    const conic = surface.conic ?? 0
    const radicand = 1 - (1 + conic) * c * c * r * r
    const base = radicand <= 0 ? 0 : (c * r * r) / (1 + Math.sqrt(radicand))
    const departure = Object.entries(surface.asphere_coefficients ?? {}).reduce((sum, [key, coefficient]) => {
      const order = Number(key.replace(/^A/i, ''))
      return Number.isFinite(order) && Number.isFinite(coefficient) ? sum + coefficient * r ** order : sum
    }, 0)
    return base + departure
  }
  if (surfaceType === 'spherical') {
    const limit = Math.max(0, radius * radius - r * r)
    return radius - Math.sign(radius) * Math.sqrt(limit)
  }
  return 0
}

type LayoutPoint = { x: number; y: number }

function surfaceProfilePoints(
  surface: Surface,
  vertexX: number,
  sy: number,
  h: number,
  semiDiameterMm: number,
  xScale: (x: number) => number,
  tiltDx: number,
  fromHeightMm = -semiDiameterMm,
  toHeightMm = semiDiameterMm,
  sampleCount = 25,
): LayoutPoint[] {
  const radius = surface.radius_mm ?? 0
  const surfaceType = surface.surface_type ?? 'plane'
  if ((surfaceType !== 'spherical' && surfaceType !== 'aspherical_even') || !Number.isFinite(radius) || Math.abs(radius) < 1.0e-12 || semiDiameterMm <= 0 || h <= 0) {
    return [fromHeightMm, toHeightMm].map((rayHeightMm) => {
      const normalizedHeight = rayHeightMm / semiDiameterMm
      return { x: xScale(vertexX) + normalizedHeight * tiltDx, y: sy + normalizedHeight * h }
    })
  }
  return Array.from({ length: sampleCount }, (_, index) => {
    const t = sampleCount <= 1 ? 0 : index / (sampleCount - 1)
    const rayHeightMm = fromHeightMm + t * (toHeightMm - fromHeightMm)
    const normalizedHeight = rayHeightMm / semiDiameterMm
    const pixelOffset = normalizedHeight * h
    const sag = surfaceSagMm(surface, rayHeightMm)
    const tiltedX = normalizedHeight * tiltDx
    return { x: xScale(vertexX + sag) + tiltedX, y: sy + pixelOffset }
  })
}

function pointsPath(points: LayoutPoint[]) {
  if (!points.length) return ''
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
}

function closedElementPath(left: LayoutPoint[], right: LayoutPoint[]) {
  if (left.length < 2 || right.length < 2) return ''
  return `${pointsPath(left)} ${right
    .slice()
    .reverse()
    .map((point) => `L ${point.x} ${point.y}`)
    .join(' ')} Z`
}

function isGlassMaterial(material?: string) {
  return Boolean(material && material.toUpperCase() !== 'AIR')
}

function edgeThicknessMm(left: Surface, right: Surface, leftX: number, rightX: number, semiD: number) {
  const leftSag = surfaceSagMm(left, semiD)
  const rightSag = surfaceSagMm(right, semiD)
  return rightX + rightSag - (leftX + leftSag)
}

function offsetRayPoint(point: number[], direction: number[] | undefined, distanceMm: number, sign: -1 | 1) {
  if (!direction || direction.length < 3 || !direction.every((value) => Number.isFinite(value))) return null
  return [point[0] + sign * direction[0] * distanceMm, point[1] + sign * direction[1] * distanceMm, point[2] + sign * direction[2] * distanceMm]
}

function rayPathD(
  path: NonNullable<TraceResponse['paths']>[number],
  xScale: (x: number) => number,
  centerY: number,
  yScale: number,
  objectPlaneX: number,
  imageExtensionMm: number,
) {
  const points = path
    .map((entry) => entry.point_mm)
    .filter((point) => point.length >= 3 && point.every((value) => Number.isFinite(value)))
  if (points.length < 2) return null
  const firstDirection = path.find((entry) => entry.direction)?.direction
  const lastDirection = [...path].reverse().find((entry) => entry.direction)?.direction
  const extendedPoints = [...points]
  const objectDistance = firstDirection && Math.abs(firstDirection[0]) > 1.0e-12
    ? Math.max(0, (points[0][0] - objectPlaneX) / firstDirection[0])
    : 0
  const objectPoint = offsetRayPoint(points[0], firstDirection, objectDistance, -1)
  if (objectPoint) extendedPoints.unshift(objectPoint)
  const imagePoint = imageExtensionMm > 0 ? offsetRayPoint(points[points.length - 1], lastDirection, imageExtensionMm, 1) : null
  if (imagePoint) extendedPoints.push(imagePoint)
  return extendedPoints.map((point, index) => `${index === 0 ? 'M' : 'L'} ${xScale(point[0])} ${centerY - point[1] * yScale}`).join(' ')
}

function wavelengthClass(wavelength: number | undefined) {
  if (wavelength === undefined || !Number.isFinite(wavelength)) return 'ray-d'
  if (wavelength <= 510) return 'ray-f'
  if (wavelength >= 630) return 'ray-c'
  return 'ray-d'
}

function rayStopY(path: NonNullable<TraceResponse['paths']>[number], apertureStopId?: string) {
  const stopEntry = (apertureStopId ? path.find((entry) => entry.surface_id === apertureStopId) : undefined) ?? path[0]
  const value = stopEntry?.local_point_mm?.[1] ?? stopEntry?.point_mm?.[1]
  return Number.isFinite(value) ? Number(value) : undefined
}

function layoutRayItems(trace?: TraceResponse, apertureStopId?: string) {
  const paths = trace?.paths
  if (!trace || !paths?.length) return []
  const samples = Math.max(1, Number(trace.metadata.samples_per_field ?? 1))
  const wavelengths = trace.metadata.wavelengths_nm?.length ? trace.metadata.wavelengths_nm : [undefined]
  const wavelengthCount = wavelengths.length
  const items = paths
    .map((path, index) => {
      const sampleIndex = index % samples
      const wavelengthIndex = Math.floor(index / samples) % wavelengthCount
      const fieldIndex = Math.floor(index / (samples * wavelengthCount))
      return {
        path,
        status: trace.status[index],
        index,
        sampleIndex,
        fieldIndex,
        wavelengthIndex,
        stopY: rayStopY(path, apertureStopId),
        sampleRole: 'candidate',
        className: `ray-line ${wavelengthClass(wavelengths[wavelengthIndex])}`,
      }
    })
    .filter((item) => item.status === 'alive' && item.path.length >= 2)
  const grouped = new Map<string, typeof items>()
  items.forEach((item) => {
    const key = `${item.fieldIndex}:${item.wavelengthIndex}`
    const group = grouped.get(key) ?? []
    group.push(item)
    grouped.set(key, group)
  })
  const selected: typeof items = []
  grouped.forEach((group) => {
    const finite = group.filter((item) => item.stopY !== undefined).sort((a, b) => (a.stopY as number) - (b.stopY as number))
    const picks = finite.length
      ? [
          { ...finite[0], sampleRole: 'lower' },
          { ...finite.reduce((best, item) => (Math.abs(item.stopY as number) < Math.abs(best.stopY as number) ? item : best), finite[0]), sampleRole: 'center' },
          { ...finite[finite.length - 1], sampleRole: 'upper' },
        ]
      : [0, Math.floor((samples - 1) / 2), samples - 1]
          .map((sampleIndex, pickIndex) => {
            const item = group.find((candidate) => candidate.sampleIndex === sampleIndex)
            const role = pickIndex === 0 ? 'lower' : pickIndex === 1 ? 'center' : 'upper'
            return item ? { ...item, sampleRole: role } : undefined
          })
          .filter((item): item is (typeof items)[number] => Boolean(item))
    const seen = new Set<number>()
    picks.forEach((item) => {
      if (!seen.has(item.index)) {
        selected.push(item)
        seen.add(item.index)
      }
    })
  })
  return (selected.length ? selected : items).slice(0, 36)
}

function layoutBaselineRayItems(trace?: TraceResponse) {
  const rays = trace?.metadata.layout_baseline_rays
  if (!rays?.length) return []
  return rays
    .map((ray: LayoutBaselineRay, index) => ({
      ...ray,
      index,
      className: `ray-line ray-baseline ray-baseline-${ray.role} ${wavelengthClass(ray.wavelength_nm)}${ray.status === 'blocked' ? ' ray-baseline-blocked' : ''}`,
    }))
    .filter((ray) => (ray.status === 'alive' || ray.status === 'aiming_failed' || ray.status === 'blocked') && ray.path.length >= 2)
}

function LayoutView({
  system,
  trace,
  evaluationPlane,
  configuration,
  showDensityRays,
}: {
  system: OpticalSystem
  trace?: TraceResponse
  evaluationPlane?: EvaluationPlaneMetadata
  configuration?: RuntimeConfiguration
  showDensityRays: boolean
}) {
  const { t } = useTranslation(['layoutView'])
  const positions = systemPositions(system)
  const evalX = evaluationPlane?.evaluation_plane_x_mm
  const solvedX = evaluationPlane?.solved_evaluation_plane_x_mm
  const apertureStopId = system.surfaces.find((surface) => surface.kind === 'aperture_stop')?.id
  const mirrorIncidentSigns = new Map<string, number>()
  let propagationSign = 1
  system.surfaces.forEach((surface) => {
    if (surface.kind !== 'mirror') return
    mirrorIncidentSigns.set(surface.id, propagationSign)
    propagationSign *= -1
  })
  const tracePaths = showDensityRays ? layoutRayItems(trace, apertureStopId) : []
  const baselinePaths = layoutBaselineRayItems(trace)
  const baseXs = positions.map((row) => row.x)
  const baseMinX = Math.min(...baseXs, 0)
  const baseMaxX = Math.max(...baseXs, 1)
  const baseSpan = Math.max(1, baseMaxX - baseMinX)
  const objectExtensionMm = Math.max(8, baseSpan * 0.2)
  const objectPlaneX = baseMinX - objectExtensionMm
  const hasSensor = system.surfaces.some((surface) => surface.kind === 'sensor')
  const paraxial = trace?.metadata.paraxial
  const paraxialImageX = paraxial?.paraxial_image_position_mm
  const principalPlaneXs = paraxial?.principal_plane_positions_mm ?? []
  const xs = [
    ...baseXs,
    objectPlaneX,
    ...(!hasSensor ? [baseMaxX + objectExtensionMm] : []),
  ]
  const minX = Math.min(...xs, 0)
  const maxX = Math.max(...xs, 1)
  const span = Math.max(1, maxX - minX)
  const xScale = (x: number) => 36 + ((x - minX) / span) * 648
  const centerY = 170
  const largestSemiDiameter = Math.max(1, ...system.surfaces.map((surface) => surfaceSemiDiameter(surface, configuration)))
  const rayYScale = Math.min(4, 92 / largestSemiDiameter)
  const surfaceYScale = rayYScale
  const apertureY = (semiD?: number | string) => {
    const value = typeof semiD === 'number' ? semiD : 8
    return Math.max(20, Math.min(92, value * surfaceYScale))
  }
  const annulusStopIndex = system.surfaces.findIndex((surface) => surface.kind === 'aperture_stop' && surface.aperture?.shape === 'annulus')
  const annulusStop = annulusStopIndex >= 0 ? system.surfaces[annulusStopIndex] : undefined
  const primaryHoleSemiDiameter = scalarNumber(annulusStop?.aperture?.inner_semi_diameter_mm)
  const primaryMirrorId = annulusStopIndex >= 0 ? system.surfaces.slice(annulusStopIndex + 1).find((surface) => surface.kind === 'mirror')?.id : undefined
  const tracePoints = trace?.sensor_y_mm
    ?.map((y, index) => ({ y, z: trace.sensor_z_mm[index], status: trace.status[index] }))
    .filter((point): point is { y: number; z: number | null; status: string } => Number.isFinite(point.y) && point.status === 'alive')
    .slice(0, 24)
  const surfaceViews = positions.map(({ surface, x }, index) => {
    const semiD = surfaceSemiDiameter(surface, configuration)
    const h = apertureY(semiD)
    const annulusInnerSemiD = surface.kind === 'aperture_stop' && surface.aperture?.shape === 'annulus'
      ? scalarNumber(surface.aperture.inner_semi_diameter_mm)
      : undefined
    const rawH = semiD * 4
    const transform = groupVisualTransform(system, surface.id, configuration)
    const sy = centerY - Math.max(-52, Math.min(52, transform.shiftY * 10))
    const tiltDx = Math.max(-20, Math.min(20, transform.tiltZ * 3))
    const previous = index > 0 ? positions[index - 1].surface : undefined
    const profilePoints = surfaceProfilePoints(surface, x, sy, h, semiD, xScale, tiltDx)
    const centralHoleSemiDiameter = surface.id === primaryMirrorId && primaryHoleSemiDiameter && primaryHoleSemiDiameter < semiD
      ? primaryHoleSemiDiameter
      : undefined
    const profileSegments = centralHoleSemiDiameter
      ? [
          surfaceProfilePoints(surface, x, sy, h, semiD, xScale, tiltDx, -semiD, -centralHoleSemiDiameter, 13),
          surfaceProfilePoints(surface, x, sy, h, semiD, xScale, tiltDx, centralHoleSemiDiameter, semiD, 13),
        ]
      : [profilePoints]
    return {
      surface,
      x,
      sx: xScale(x),
      semiD,
      h,
      annulusInnerSemiD,
      mirrorIncidentSign: mirrorIncidentSigns.get(surface.id),
      centralHoleSemiDiameter,
      rawH,
      sy,
      tiltDx,
      transform,
      profilePoints,
      profileSegments,
      cementedBoundary: surface.kind === 'refractive' && isGlassMaterial(previous?.material_after) && isGlassMaterial(surface.material_after),
    }
  })
  const glassElements = surfaceViews
    .map((view, index) => {
      const next = surfaceViews[index + 1]
      if (!next || view.surface.kind !== 'refractive' || !isGlassMaterial(view.surface.material_after)) return null
      const thickness = edgeThicknessMm(view.surface, next.surface, view.x, next.x, Math.min(view.semiD, next.semiD))
      return {
        key: `${view.surface.id}-${next.surface.id}`,
        d: closedElementPath(view.profilePoints, next.profilePoints),
        warning: thickness <= 0,
      }
    })
    .filter((item): item is { key: string; d: string; warning: boolean } => Boolean(item?.d))
  const labelRows = new Map<string, number>()
  let previousLabelX = Number.NEGATIVE_INFINITY
  let labelRow = 0
  surfaceViews.forEach((view) => {
    labelRow = view.sx - previousLabelX < 18 ? labelRow + 1 : 0
    labelRows.set(view.surface.id, labelRow)
    previousLabelX = view.sx
  })

  return (
    <svg
      id="layout-svg"
      className="layout-view"
      viewBox="0 0 720 340"
      role="img"
      aria-label={t('layoutView.optical_layout_aria')}
      data-total-rays={trace?.status.length ?? 0}
      data-displayed-rays={tracePaths.length + baselinePaths.length || tracePoints?.length || 0}
      data-baseline-rays={baselinePaths.length}
      data-density-rays={tracePaths.length}
      data-paraxial-image-x-mm={Number.isFinite(paraxialImageX) ? paraxialImageX : undefined}
      data-ray-y-scale={rayYScale}
      data-object-plane-x-mm={objectPlaneX}
    >
      <title>{t('layoutView.optical_layout')}</title>
      <line x1="24" x2="696" y1={centerY} y2={centerY} className="axis-line" />
      {glassElements.map((element) => (
        <path key={element.key} d={element.d} className={`glass-element${element.warning ? ' glass-element-warning' : ''}`} />
      ))}
      {surfaceViews.map(({ surface, x, sx, sy, semiD, h, rawH, annulusInnerSemiD, mirrorIncidentSign, centralHoleSemiDiameter, tiltDx, transform, profilePoints, profileSegments, cementedBoundary }) => {
        const className = `surface-line surface-${surface.kind}${transform.active ? ' surface-configured' : ''}${cementedBoundary ? ' surface-cemented' : ''}`
        const labelY = sy + h + 22 + (labelRows.get(surface.id) ?? 0) * 13
        const isStop = surface.kind === 'aperture_stop'
        const isAnnulusStop = isStop && Boolean(annulusInnerSemiD)
        const annulusInnerRadiusPx = isAnnulusStop && semiD > 0 ? h * (annulusInnerSemiD as number) / semiD : undefined
        const stopInnerRadiusPx = annulusInnerRadiusPx ?? 0
        const stopPhysicalLengthPx = Math.max(0, h - stopInnerRadiusPx)
        const stopVisualLengthPx = Math.max(4, stopPhysicalLengthPx)
        const stopSegmentMidRadiusPx = (h + stopInnerRadiusPx) / 2
        return (
          <g
            key={surface.id}
            data-surface-id={surface.id}
            data-surface-kind={surface.kind}
            data-vertex-x-mm={x}
            data-radius-mm={surface.radius_mm}
            data-mirror-incident-sign={mirrorIncidentSign}
            data-central-hole-semi-diameter-mm={centralHoleSemiDiameter}
            data-semi-diameter-mm={semiD}
            data-visual-half-height-px={h}
            data-raw-half-height-px={rawH}
            data-scale-clamped={Math.abs(h - rawH) > 1.0e-9 ? 'true' : 'false'}
            data-annulus-inner-semi-diameter-mm={annulusInnerSemiD}
            data-annulus-inner-radius-px={annulusInnerRadiusPx}
            data-annulus-outer-radius-px={isAnnulusStop ? h : undefined}
          >
            {isStop
              ? null
              : profilePoints.length > 2
                ? profileSegments.map((segment, segmentIndex) => <path key={segmentIndex} d={pointsPath(segment)} className={className} fill="none" />)
                : <line x1={sx - tiltDx} x2={sx + tiltDx} y1={sy - h} y2={sy + h} className={className} />}
            {surface.kind === 'sensor' ? <rect x={sx - 3} y={sy - h} width="6" height={h * 2} className="sensor-plane" /> : null}
            {isStop
              ? (
                  <g
                    className={`stop-aperture-marker${isAnnulusStop ? ' stop-annulus-marker' : ' stop-circle-marker'}`}
                    data-stop-min-visual-length-px="4"
                  >
                    {([-1, 1] as const).map((sign) => {
                      const segmentCenterY = sy + sign * stopSegmentMidRadiusPx
                      return (
                        <line
                          key={sign}
                          x1={sx}
                          x2={sx}
                          y1={segmentCenterY - stopVisualLengthPx / 2}
                          y2={segmentCenterY + stopVisualLengthPx / 2}
                          className="stop-aperture-segment"
                          data-stop-sign={sign}
                          data-stop-inner-radius-px={stopInnerRadiusPx}
                          data-stop-outer-radius-px={h}
                          data-stop-physical-length-px={stopPhysicalLengthPx}
                          data-stop-visual-length-px={stopVisualLengthPx}
                        />
                      )
                    })}
                    {!isAnnulusStop ? <circle cx={sx} cy={sy} r={Math.max(3, Math.min(6, h * 0.12))} className="stop-dot" /> : null}
                  </g>
                )
              : null}
            {transform.active ? <circle cx={sx} cy={sy - h - 10} r="3.5" className="configured-dot" /> : null}
            <text x={sx} y={labelY} textAnchor="middle" className="surface-label">
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
      {Number.isFinite(paraxialImageX) ? (
        <g data-testid="layout-paraxial-image-marker">
          <line x1={xScale(paraxialImageX as number)} x2={xScale(paraxialImageX as number)} y1={centerY - 66} y2={centerY + 66} className="focal-marker-line" />
          <text x={xScale(paraxialImageX as number) + 6} y={centerY - 72} className="surface-label">
            F'
          </text>
        </g>
      ) : null}
      {principalPlaneXs.map((x, index) =>
        Number.isFinite(x) ? (
          <g key={`principal-${index}`} data-testid="layout-principal-plane-marker">
            <line x1={xScale(x as number)} x2={xScale(x as number)} y1={centerY - 50} y2={centerY + 50} className="principal-plane-line" />
            <text x={xScale(x as number) + 6} y={centerY + 66 + index * 12} className="surface-label">
              H{index + 1}
            </text>
          </g>
        ) : null,
      )}
      {showDensityRays && tracePaths?.length
        ? tracePaths.map(({ path, className, index, fieldIndex, wavelengthIndex, sampleIndex, sampleRole, stopY }) => {
            const d = rayPathD(path, xScale, centerY, rayYScale, objectPlaneX, hasSensor ? 0 : objectExtensionMm)
            return d ? (
              <path
                key={index}
                d={d}
                className={`${className} ray-density`}
                fill="none"
                data-ray-layer="density"
                data-field-index={fieldIndex}
                data-wavelength-index={wavelengthIndex}
                data-sample-index={sampleIndex}
                data-sample-role={sampleRole}
                data-stop-y-mm={stopY}
              />
            ) : null
          })
        : showDensityRays && !baselinePaths.length
          ? tracePoints?.map((point, index) => {
            const sensorX = xScale(positions[positions.length - 1]?.x ?? maxX)
            const py = centerY - Math.max(-80, Math.min(80, point.y * 8))
            return <line key={index} x1={xScale(positions[0]?.x ?? minX)} y1={centerY + (index % 7 - 3) * 7} x2={sensorX} y2={py} className="ray-line ray-d ray-density" data-ray-layer="density" />
          })
          : null}
      {baselinePaths.map(({ path, className, index, field_index, wavelength_index, role, status, stop_y_mm }) => {
        const d = rayPathD(path, xScale, centerY, rayYScale, objectPlaneX, hasSensor ? 0 : objectExtensionMm)
        const endPoint = status === 'blocked' ? path[path.length - 1]?.point_mm : undefined
        const hasFiniteEnd = Boolean(endPoint?.length && endPoint.length >= 2 && endPoint.every((value) => Number.isFinite(value)))
        const endX = hasFiniteEnd && endPoint ? xScale(endPoint[0]) : undefined
        const endY = hasFiniteEnd && endPoint ? centerY - endPoint[1] * rayYScale : undefined
        return d ? (
          <g key={`baseline-${index}`}>
            <path
              d={d}
              className={className}
              fill="none"
              data-ray-layer="baseline"
              data-baseline-role={role}
              data-baseline-status={status}
              data-field-index={field_index}
              data-wavelength-index={wavelength_index}
              data-stop-y-mm={stop_y_mm ?? undefined}
            />
            {endX !== undefined && endY !== undefined ? (
              <g className="ray-blocked-marker" data-ray-end-marker="blocked" data-field-index={field_index} data-baseline-role={role}>
                <line x1={endX - 3.5} y1={endY - 3.5} x2={endX + 3.5} y2={endY + 3.5} />
                <line x1={endX - 3.5} y1={endY + 3.5} x2={endX + 3.5} y2={endY - 3.5} />
              </g>
            ) : null}
          </g>
        ) : null
          })}
    </svg>
  )
}

function LayoutLegend({ system }: { system: OpticalSystem }) {
  const { t } = useTranslation(['layoutView'])
  const hasCircleStop = system.surfaces.some((surface) => surface.kind === 'aperture_stop' && surface.aperture?.shape !== 'annulus')
  const hasAnnulusStop = system.surfaces.some((surface) => surface.kind === 'aperture_stop' && surface.aperture?.shape === 'annulus')
  const groups = [
    {
      title: t('layoutView.legend.rays'),
      items: [
        { key: 'chief', className: 'legend-line legend-line-chief', label: t('layoutView.legend.chief_ray') },
        { key: 'marginal', className: 'legend-line legend-line-marginal', label: t('layoutView.legend.marginal_ray') },
        { key: 'density', className: 'legend-line legend-line-density', label: t('layoutView.legend.density_ray') },
        { key: 'vignetted', className: 'legend-line legend-line-vignetted', label: t('layoutView.legend.vignetted_ray') },
      ],
    },
    {
      title: t('layoutView.legend.wavelengths'),
      items: [
        { key: 'f', className: 'legend-line ray-f', label: t('layoutView.legend.f_line') },
        { key: 'de', className: 'legend-line ray-d', label: t('layoutView.legend.de_line') },
        { key: 'c', className: 'legend-line ray-c', label: t('layoutView.legend.c_line') },
      ],
    },
    {
      title: t('layoutView.legend.elements'),
      items: [
        { key: 'glass', className: 'legend-swatch legend-glass', label: t('layoutView.legend.glass_region') },
        { key: 'air', className: 'legend-swatch legend-air', label: t('layoutView.legend.air_gap') },
        { key: 'cemented', className: 'legend-line legend-cemented', label: t('layoutView.legend.cemented_surface') },
        { key: 'mirror', className: 'legend-line legend-mirror', label: t('layoutView.legend.mirror_surface') },
        ...(hasCircleStop ? [{ key: 'stop', className: 'legend-symbol legend-stop', label: t('layoutView.legend.stop_symbol') }] : []),
        ...(hasAnnulusStop ? [{ key: 'annulus', className: 'legend-symbol legend-annulus', label: t('layoutView.legend.annulus_obscuration') }] : []),
        { key: 'img', className: 'legend-symbol legend-img', label: t('layoutView.legend.img_symbol') },
      ],
    },
    {
      title: t('layoutView.legend.markers'),
      items: [
        { key: 'focus', className: 'legend-line legend-focus', label: t('layoutView.legend.focus_marker') },
        { key: 'principal', className: 'legend-line legend-principal', label: t('layoutView.legend.principal_plane') },
      ],
    },
  ]
  return (
    <div className="layout-legend" data-testid="layout-legend" aria-label={t('layoutView.legend.aria')}>
      {groups.map((group) => (
        <div className="layout-legend-group" key={group.title}>
          <strong>{group.title}</strong>
          <div className="layout-legend-items">
            {group.items.map((item) => (
              <span className="layout-legend-item" key={item.key}>
                <i className={item.className} aria-hidden="true" />
                <span>{item.label}</span>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function SurfaceTable({
  surfaces,
  onUpdateAnnulusRadius,
  onOpenHelp,
}: {
  surfaces: Surface[]
  onUpdateAnnulusRadius: (index: number, radius: 'inner' | 'outer', value: number) => void
  onOpenHelp: (termId: string) => void
}) {
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
          {surfaces.map((surface, surfaceIndex) => (
            <tr key={surface.id}>
              {surfaceColumns.map((column) => {
                const isAnnulusDiameter = column.id === 'semi_diameter_mm' && surface.aperture?.shape === 'annulus'
                if (!isAnnulusDiameter) return <td key={column.id} data-column-id={column.id}>{String(column.value(surface))}</td>
                const inner = scalarNumber(surface.aperture?.inner_semi_diameter_mm) ?? 0
                const outer = scalarNumber(surface.aperture?.outer_semi_diameter_mm) ?? scalarNumber(surface.semi_diameter_mm) ?? 0
                return (
                  <td key={column.id} data-column-id={column.id}>
                    <div className="annulus-radius-editor" data-testid="annulus-radius-editor">
                      <NumberInput
                        id={`surface-${surface.id}-annulus-outer`}
                        label={t('surfaceTable.annulus.outer')}
                        min={0}
                        step={0.1}
                        size="sm"
                        value={outer}
                        onChange={(_, data) => onUpdateAnnulusRadius(surfaceIndex, 'outer', numericInputValue(data.value, outer))}
                      />
                      <NumberInput
                        id={`surface-${surface.id}-annulus-inner`}
                        label={t('surfaceTable.annulus.inner')}
                        min={0}
                        step={0.1}
                        size="sm"
                        value={inner}
                        onChange={(_, data) => onUpdateAnnulusRadius(surfaceIndex, 'inner', numericInputValue(data.value, inner))}
                      />
                    </div>
                  </td>
                )
              })}
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
  const clearance = groupShiftClearance(system, draft, runtimeConfiguration)
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
        <SliderControl id="shift-y-slider" label={t('settings:settings.shift_y_mm')} value={draft.shiftY} min={-decenterShiftLimitMm} max={decenterShiftLimitMm} step={0.1} unit={t('units:units.mm')} onChange={(value) => onUpdateDraft({ shiftY: value })} onCommit={onCommit} />
        <SliderControl id="shift-z-slider" label={t('settings:settings.shift_z_mm')} value={draft.shiftZ} min={-decenterShiftLimitMm} max={decenterShiftLimitMm} step={0.1} unit={t('units:units.mm')} onChange={(value) => onUpdateDraft({ shiftZ: value })} onCommit={onCommit} />
        <SliderControl id="tilt-y-slider" label={t('settings:settings.tilt_y_deg')} value={draft.tiltY} min={-5} max={5} step={0.1} unit={t('units:units.deg')} onChange={(value) => onUpdateDraft({ tiltY: value })} onCommit={onCommit} />
        <SliderControl id="tilt-z-slider" label={t('settings:settings.tilt_z_deg')} value={draft.tiltZ} min={-5} max={5} step={0.1} unit={t('units:units.deg')} onChange={(value) => onUpdateDraft({ tiltZ: value })} onCommit={onCommit} />
        <SliderControl id="roll-x-slider" label={t('settings:settings.roll_x_deg')} value={draft.rollX} min={-5} max={5} step={0.1} unit={t('units:units.deg')} onChange={(value) => onUpdateDraft({ rollX: value })} onCommit={onCommit} />
      </div>
      <p className="muted">{t('settings:settings.decenter_shift_limit', { limit: decenterShiftLimitMm })}</p>
      {clearance && clearance.clearance < 0 ? (
        <InlineNotification
          lowContrast
          kind="warning"
          title={t('settings:settings.decenter_vignetting_warning')}
          subtitle={t('settings:settings.decenter_vignetting_warning_detail', {
            shift: formatFixed(clearance.shift, 2),
            margin: formatFixed(clearance.clearance, 2),
          })}
        />
      ) : null}
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
  const samples = Math.max(1, Number(trace?.metadata.samples_per_field ?? 1))
  const wavelengths = trace?.metadata.wavelengths_nm?.length ? trace.metadata.wavelengths_nm : [undefined]
  const points = trace?.sensor_y_mm
    ?.map((y, index) => {
      const wavelengthIndex = Math.floor(index / samples) % wavelengths.length
      const wavelength = wavelengths[wavelengthIndex]
      return { y, z: trace.sensor_z_mm[index], status: trace.status[index], wavelength, wavelengthIndex }
    })
    .filter((point): point is { y: number; z: number; status: string; wavelength: number | undefined; wavelengthIndex: number } => Number.isFinite(point.y) && Number.isFinite(point.z))
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
        const color = point.wavelength === undefined ? undefined : wavelengthColor(point.wavelength)
        return (
          <circle
            key={index}
            cx={x}
            cy={y}
            r="2.7"
            className={point.status === 'alive' ? 'spot-point' : 'spot-blocked'}
            style={point.status === 'alive' && color ? { fill: color } : undefined}
            data-wavelength-index={point.wavelengthIndex}
            data-wavelength-nm={point.wavelength}
          />
        )
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

function ChartSvg({
  series,
  xLabel,
  yLabel,
  emptyLabel,
  testId,
}: {
  series: ChartSeries[]
  xLabel: string
  yLabel: string
  emptyLabel: string
  testId?: string
}) {
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
  const sx = (x: number) => 56 + ((x - x0) / (x1 - x0)) * 294
  const sy = (y: number) => 178 - ((y - y0) / (y1 - y0)) * 144

  return (
    <div className="chart-box">
      <svg viewBox="0 0 390 240" role="img" className="analysis-chart" data-testid={testId}>
        <line x1="56" x2="350" y1="178" y2="178" className="plot-axis" />
        <line x1="56" x2="56" y1="34" y2="178" className="plot-axis" />
        <text x="203" y="224" className="plot-label plot-label--x" textAnchor="middle">
          {xLabel}
        </text>
        <text x="18" y="106" className="plot-label plot-label--y" textAnchor="middle" transform="rotate(-90 18 106)">
          {yLabel}
        </text>
        <text x="56" y="197" className="plot-tick">
          {formatFixed(x0, 2)}
        </text>
        <text x="350" y="197" className="plot-tick" textAnchor="end">
          {formatFixed(x1, 2)}
        </text>
        <text x="50" y="182" className="plot-tick" textAnchor="end">
          {formatFixed(y0, 2)}
        </text>
        <text x="50" y="38" className="plot-tick" textAnchor="end">
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

function seriesFromLongitudinal(points: LongitudinalAberrationPoint[] | undefined): ChartSeries[] {
  const groups = new Map<string, ChartSeries>()
  for (const point of points ?? []) {
    if (point.status !== 'alive') continue
    if (!finitePoint(point.longitudinal_error_y_mm, point.pupil_y)) continue
    const key = `${formatFixed(point.wavelength_nm, 0)}nm`
    const existing = groups.get(key) ?? { id: key, color: wavelengthColor(point.wavelength_nm), points: [] }
    existing.points.push({ x: point.longitudinal_error_y_mm as number, y: point.pupil_y })
    groups.set(key, existing)
  }
  return [...groups.values()]
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

function seriesFromDistortionStandard(rows: DistortionRow[] | undefined): ChartSeries[] {
  return [
    {
      id: 'distortion',
      color: '#0f62fe',
      points: (rows ?? [])
        .filter((row) => finitePoint(row.distortion_percent, fieldAngle(row)))
        .map((row) => ({ x: row.distortion_percent as number, y: fieldAngle(row) })),
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

function seriesFromFieldCurvatureStandard(rows: FieldCurvatureRow[] | undefined): ChartSeries[] {
  const safeRows = rows ?? []
  return [
    {
      id: 'M',
      color: '#0f62fe',
      points: safeRows
        .filter((row) => finitePoint(row.tangential_focus_shift_mm ?? row.best_focus_shift_mm, fieldAngle(row)))
        .map((row) => ({ x: (row.tangential_focus_shift_mm ?? row.best_focus_shift_mm) as number, y: fieldAngle(row) })),
    },
    {
      id: 'S',
      color: '#da1e28',
      points: safeRows
        .filter((row) => finitePoint(row.sagittal_focus_shift_mm ?? row.best_focus_shift_mm, fieldAngle(row)))
        .map((row) => ({ x: (row.sagittal_focus_shift_mm ?? row.best_focus_shift_mm) as number, y: fieldAngle(row) })),
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
        <h2>{t('analysis:analysis.standard_aberration_title')}</h2>
        <div className="standard-aberration-grid" data-testid="standard-aberration-grid">
          <div>
            <h3>{termLabel('longitudinal_aberration', i18n.language)}</h3>
            <ChartSvg
              series={seriesFromLongitudinal(result.longitudinal?.points)}
              xLabel={t('analysis:analysis.axis_focus_shift_mm')}
              yLabel={t('analysis:analysis.axis_pupil_coordinate')}
              emptyLabel={empty}
              testId="longitudinal-aberration-chart"
            />
          </div>
          <div>
            <h3>{termLabel('field_curvature', i18n.language)}</h3>
            <ChartSvg
              series={seriesFromFieldCurvatureStandard(result.fieldCurvature?.rows)}
              xLabel={t('analysis:analysis.axis_focus_shift_mm')}
              yLabel={t('analysis:analysis.axis_half_field_deg')}
              emptyLabel={empty}
              testId="standard-field-curvature-chart"
            />
          </div>
          <div>
            <h3>{termLabel('distortion', i18n.language)}</h3>
            <ChartSvg
              series={seriesFromDistortionStandard(result.distortion?.rows)}
              xLabel={t('analysis:analysis.axis_distortion_percent')}
              yLabel={t('analysis:analysis.axis_half_field_deg')}
              emptyLabel={empty}
              testId="standard-distortion-chart"
            />
          </div>
        </div>
      </section>
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
        <p className="muted field-angle-hint">{t('settings:settings.field_angle_infinity_hint')}</p>
        <div className="field-editor" data-testid="field-editor">
          {fields.map((field, index) => (
            <div className="condition-row field-row" key={`${field.id}-${index}`} data-testid="field-row">
              <TextInput
                id={`field-${index}-id`}
                labelText={field.preset_label === 'image_height_70pct' ? t('settings:settings.field_id_70pct') : t('settings:settings.field_id')}
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
  const fixtureMode = new URLSearchParams(window.location.search).get('fixture')
  const visiblePresets = presets.filter((item) => item.visible !== false)
  const availablePresets = sortPresetsById(
    fixtureMode === 'all-presets'
      ? presets
      : fixtureMode === 'asphere-layout'
        ? [...visiblePresets, ...visualFixturePresets]
        : visiblePresets,
  )
  const [apiBase, setApiBase] = useState(defaultApiBase)
  const [selectedPresetId, setSelectedPresetId] = useState('P001')
  const [activeTab, setActiveTab] = useState<TabKey>('preview')
  const [samplesPerField, setSamplesPerField] = useState(9)
  const [analysisFields, setAnalysisFields] = useState<AnalysisField[]>(() => presetFields(presets[0]))
  const [wavelengths, setWavelengths] = useState<WavelengthSample[]>(() => initialWavelengths(presets[0].system))
  const [pupilDistribution, setPupilDistribution] = useState('grid')
  const [aimingMode, setAimingMode] = useState('paraxial')
  const [showDensityRays, setShowDensityRays] = useState(true)
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

  const preset = availablePresets.find((item) => item.id === selectedPresetId) ?? availablePresets[0]
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
    const nextConfiguration = makeRuntimeConfiguration(nextSystem, nextZoom, nextGroup, 0, nextDecenterTilt, nextIris)
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

  const updateAnnulusRadius = (index: number, radius: 'inner' | 'outer', value: number) => {
    const nextSystem = cloneSystem(system)
    const surface = nextSystem.surfaces[index]
    if (!surface || surface.aperture?.shape !== 'annulus') return
    if (radius === 'inner') surface.aperture.inner_semi_diameter_mm = value
    else {
      surface.aperture.outer_semi_diameter_mm = value
      surface.semi_diameter_mm = value
    }
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
    options: { store_path: true, profiling: true, include_layout_baseline_rays: true },
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
    const nextConfiguration = makeRuntimeConfiguration(system, nextZoom, nextFocusGroup, nextFocusShift, decenterTiltDraftRef.current, irisRadiusRef.current)
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
    const nextConfiguration = makeRuntimeConfiguration(system, zoomPositionId, focusGroupId, focusShiftMm, decenterTiltDraftRef.current, nextRadius)
    irisRadiusRef.current = nextRadius
    setIrisRadiusMm(nextRadius)
    runtimeConfigurationRef.current = nextConfiguration
    setRuntimeConfiguration(nextConfiguration)
    markAnalysisDirty()
    scheduleMotionPreview(nextConfiguration)
    if (commit) {
      if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
      void runMotionPreview(nextConfiguration, false)
    }
  }

  const commitApertureRadius = () => {
    const nextConfiguration = makeRuntimeConfiguration(system, zoomPositionId, focusGroupId, focusShiftMm, decenterTiltDraftRef.current, irisRadiusRef.current)
    runtimeConfigurationRef.current = nextConfiguration
    setRuntimeConfiguration(nextConfiguration)
    if (sliderPreviewTimerRef.current) window.clearTimeout(sliderPreviewTimerRef.current)
    void runMotionPreview(nextConfiguration, false)
  }

  const updateDecenterTilt = (patch: Partial<DecenterTiltDraft>, commit = false) => {
    const nextDraft = { ...decenterTiltDraftRef.current, ...patch }
    decenterTiltDraftRef.current = nextDraft
    setDecenterTiltDraft(nextDraft)
    const nextConfiguration = makeRuntimeConfiguration(system, zoomPositionId, focusGroupId, focusShiftMm, nextDraft, irisRadiusRef.current)
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
  const requestSummary = analysisRequestSummary(lastRequest)

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
              items={availablePresets}
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
                  setAnalysisFields(presetFields(selectedItem))
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
              <SurfaceTable surfaces={system.surfaces} onUpdateAnnulusRadius={updateAnnulusRadius} onOpenHelp={setHelpTermId} />
              <GroupPanel system={system} onAddGroup={addGroup} onUpdateGroup={updateGroup} onRemoveGroup={removeGroup} onOpenHelp={setHelpTermId} />
            </div>
          ) : null}

          {activeTab === 'preview' ? (
            <div className="preview-stack">
              <div className="panel large-panel">
                <div className="panel-heading">
                  <h2>{t('layoutView:layoutView.optical_layout')}</h2>
                  <div className="panel-actions">
                    <Checkbox
                      id="show-density-rays"
                      labelText={t('layoutView:layoutView.show_density_rays')}
                      checked={showDensityRays}
                      onChange={(_, data) => setShowDensityRays(Boolean(data.checked))}
                    />
                    <Button size="sm" kind="secondary" renderIcon={Save} disabled={!trace} onClick={() => void saveSnapshot()}>
                      {t('common.buttons.save_snapshot')}
                    </Button>
                    <Button size="sm" renderIcon={Play} disabled={!engineOnline || running || versionBlocked} onClick={() => previewMutation.mutate()}>
                      {t('common.buttons.run_preview')}
                    </Button>
                  </div>
                </div>
                <LayoutView system={system} trace={trace} evaluationPlane={evaluationPlane} configuration={runtimeConfiguration} showDensityRays={showDensityRays} />
                <LayoutLegend system={system} />
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
              <div className="panel">
                <h2>{t('common.debug.build_info')}</h2>
                <div className="metric-row">
                  <span>{t('common.debug.git_commit')}</span>
                  <code>{meta.data?.build_info?.git_commit ?? t('common.empty.dash')}</code>
                </div>
                <div className="metric-row">
                  <span>{t('common.debug.git_dirty')}</span>
                  <strong>{String(meta.data?.build_info?.git_dirty ?? t('common.empty.dash'))}</strong>
                </div>
                <div className="metric-row">
                  <span>{t('common.debug.started_at')}</span>
                  <code>{meta.data?.build_info?.started_at ?? t('common.empty.dash')}</code>
                </div>
              </div>
              <div className="panel" data-testid="request-sampling-panel">
                <h2>{t('common.debug.ray_sampling_request')}</h2>
                <div className="metric-row">
                  <span>{t('common.debug.samples_per_field')}</span>
                  <strong>{requestSummary.samplesPerField ?? t('common.empty.dash')}</strong>
                </div>
                <div className="metric-row">
                  <span>{t('common.debug.pupil_distribution')}</span>
                  <strong>{requestSummary.pupilDistribution ?? t('common.empty.dash')}</strong>
                </div>
                <div className="metric-row">
                  <span>{t('common.debug.ray_aiming_mode')}</span>
                  <strong>{requestSummary.rayAimingMode ?? t('common.empty.dash')}</strong>
                </div>
                <div className="metric-row">
                  <span>{t('common.debug.fields')}</span>
                  <code>{requestSummary.fields.length ? requestSummary.fields.map((field) => field.id).join(', ') : t('common.empty.dash')}</code>
                </div>
                <div className="metric-row">
                  <span>{t('common.debug.wavelengths')}</span>
                  <code>{requestSummary.wavelengths.length ? requestSummary.wavelengths.join(', ') : t('common.empty.dash')}</code>
                </div>
              </div>
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
          <Accordion className="right-panel-accordion" align="start">
            <AccordionItem title={t('settings:settings.api')}>
              <div className="right-accordion-body">
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
              </div>
            </AccordionItem>
          </Accordion>

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

          <Accordion className="right-panel-accordion" align="start">
            <AccordionItem title={t('settings:settings.validation')}>
              <div className="right-accordion-body">
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
              </div>
            </AccordionItem>
            <AccordionItem title={t('analysis:analysis.chart_export')}>
              <div className="right-accordion-body">
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
              </div>
            </AccordionItem>
          </Accordion>
        </aside>
      </main>

      <HelpDrawer termId={helpTermId} onClose={() => setHelpTermId(null)} onNavigate={setHelpTermId} />
    </div>
  )
}
