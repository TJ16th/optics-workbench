import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import type {
  AnalysisField,
  BestFocusResponse,
  ChartAnalysisResult,
  EvaluationPlaneMetadata,
  MtfMode,
  OpticalSystem,
  RuntimeConfiguration,
  TraceResponse,
  ValidationResult,
  VisualCompositeResponse,
  WavelengthSample,
  FocusCurvePoint,
} from '../domain/types'
import type { SupportedLanguage } from '../i18n/resources'

export type WorkbenchViewKey = 'system' | 'preview' | 'analysis' | 'compare' | 'debug'
export type AnalysisViewKey = 'standard' | 'through_focus'
export type ThemePreference = 'system' | 'light' | 'dark'

const navigationStorageKey = 'optics-workbench-navigation-expanded'

type ControllerInitialState<ImagePlanePolicyDraft, DecenterTiltDraft> = {
  apiBase: string
  system: OpticalSystem
  fields: AnalysisField[]
  wavelengths: WavelengthSample[]
  imagePlanePolicy: ImagePlanePolicyDraft
  decenterTiltDraft: DecenterTiltDraft
  irisRadiusMm: number
  helpTermId: string | null
  themePreference: ThemePreference
  systemDark: boolean
}

export function useWorkbenchControllerState<Snapshot, ImagePlanePolicyDraft, DecenterTiltDraft>(
  initial: ControllerInitialState<ImagePlanePolicyDraft, DecenterTiltDraft>,
) {
  const [themePreference, setThemePreference] = useState<ThemePreference>(initial.themePreference)
  const [systemDark, setSystemDark] = useState(initial.systemDark)
  const [apiBase, setApiBase] = useState(initial.apiBase)
  const [selectedPresetId, setSelectedPresetId] = useState('P001')
  const [activeTab, setActiveTab] = useState<WorkbenchViewKey>('preview')
  const [analysisView, setAnalysisView] = useState<AnalysisViewKey>('standard')
  const [samplesPerField, setSamplesPerField] = useState(9)
  const [analysisFields, setAnalysisFields] = useState<AnalysisField[]>(initial.fields)
  const [wavelengths, setWavelengths] = useState<WavelengthSample[]>(initial.wavelengths)
  const [pupilDistribution, setPupilDistribution] = useState('grid')
  const [aimingMode, setAimingMode] = useState('paraxial')
  const [mtfMode, setMtfMode] = useState<MtfMode>('monochromatic')
  const [showDensityRays, setShowDensityRays] = useState(true)
  const [imagePlanePolicy, setImagePlanePolicy] = useState<ImagePlanePolicyDraft>(initial.imagePlanePolicy)
  const imagePlanePolicyRef = useRef<ImagePlanePolicyDraft>(imagePlanePolicy)
  const [zoomPositionId, setZoomPositionId] = useState('')
  const [focusGroupId, setFocusGroupId] = useState('')
  const [focusShiftMm, setFocusShiftMm] = useState(0)
  const [decenterTiltDraft, setDecenterTiltDraft] = useState<DecenterTiltDraft>(initial.decenterTiltDraft)
  const decenterTiltDraftRef = useRef<DecenterTiltDraft>(initial.decenterTiltDraft)
  const [runtimeConfiguration, setRuntimeConfiguration] = useState<RuntimeConfiguration>({})
  const runtimeConfigurationRef = useRef<RuntimeConfiguration>({})
  const [irisRadiusMm, setIrisRadiusMm] = useState(initial.irisRadiusMm)
  const [irisMaxRadiusMm, setIrisMaxRadiusMm] = useState(initial.irisRadiusMm)
  const irisRadiusRef = useRef(irisRadiusMm)
  const sliderPreviewTimerRef = useRef<number | undefined>()
  const motionPreviewSequenceRef = useRef(0)
  const [sliderPreviewPending, setSliderPreviewPending] = useState(false)
  const [analysisDirty, setAnalysisDirty] = useState(false)
  const [systemDirty, setSystemDirty] = useState(false)
  const [system, setSystem] = useState<OpticalSystem>(initial.system)
  const [systemId, setSystemId] = useState<string | null>(null)
  const [systemHash, setSystemHash] = useState<string | null>(null)
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [trace, setTrace] = useState<TraceResponse | undefined>()
  const [chartResult, setChartResult] = useState<ChartAnalysisResult | undefined>()
  const [visualResult, setVisualResult] = useState<VisualCompositeResponse | undefined>()
  const [visualResultMode, setVisualResultMode] = useState<'instrument' | 'retinal'>('instrument')
  const [evaluationPlane, setEvaluationPlane] = useState<EvaluationPlaneMetadata | undefined>()
  const [focusCurve, setFocusCurve] = useState<FocusCurvePoint[]>([])
  const [focusResult, setFocusResult] = useState<BestFocusResponse | undefined>()
  const [lastRequest, setLastRequest] = useState<unknown>(null)
  const [lastResponse, setLastResponse] = useState<unknown>(null)
  const [helpTermId, setHelpTermId] = useState<string | null>(initial.helpTermId)
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [compareLeftId, setCompareLeftId] = useState('')
  const [compareRightId, setCompareRightId] = useState('')
  const [selectedSurfaceId, setSelectedSurfaceId] = useState(initial.system.surfaces[0]?.id ?? '')
  const [selectedGroupId, setSelectedGroupId] = useState('')
  const [snapshotNoticeId, setSnapshotNoticeId] = useState('')
  const [exportLanguage, setExportLanguage] = useState<SupportedLanguage>('ja')

  return {
    themePreference, setThemePreference, systemDark, setSystemDark, apiBase, setApiBase,
    selectedPresetId, setSelectedPresetId, activeTab, setActiveTab, analysisView, setAnalysisView,
    samplesPerField, setSamplesPerField, analysisFields, setAnalysisFields, wavelengths, setWavelengths,
    pupilDistribution, setPupilDistribution, aimingMode, setAimingMode, mtfMode, setMtfMode,
    showDensityRays, setShowDensityRays, imagePlanePolicy, setImagePlanePolicy, imagePlanePolicyRef,
    zoomPositionId, setZoomPositionId, focusGroupId, setFocusGroupId, focusShiftMm, setFocusShiftMm,
    decenterTiltDraft, setDecenterTiltDraft, decenterTiltDraftRef, runtimeConfiguration,
    setRuntimeConfiguration, runtimeConfigurationRef, irisRadiusMm, setIrisRadiusMm, irisMaxRadiusMm,
    setIrisMaxRadiusMm, irisRadiusRef, sliderPreviewTimerRef, motionPreviewSequenceRef,
    sliderPreviewPending, setSliderPreviewPending, analysisDirty, setAnalysisDirty, systemDirty,
    setSystemDirty, system, setSystem, systemId, setSystemId, systemHash, setSystemHash,
    validation, setValidation, trace, setTrace, chartResult, setChartResult, visualResult,
    setVisualResult, visualResultMode, setVisualResultMode, evaluationPlane, setEvaluationPlane,
    focusCurve, setFocusCurve, focusResult, setFocusResult, lastRequest, setLastRequest,
    lastResponse, setLastResponse, helpTermId, setHelpTermId, snapshots, setSnapshots,
    compareLeftId, setCompareLeftId, compareRightId, setCompareRightId, exportLanguage, setExportLanguage,
    selectedSurfaceId, setSelectedSurfaceId, selectedGroupId, setSelectedGroupId,
    snapshotNoticeId, setSnapshotNoticeId,
  }
}

type MutationSpec<Result> = {
  mutationFn: () => Promise<Result>
  onSuccess: (result: Result) => void
  onError: (error: unknown) => void
}

export function useWorkbenchMutations<Validate, Register, Preview, Charts, ThroughFocus, Visual, Focus>(specs: {
  validate: MutationSpec<Validate>
  register: MutationSpec<Register>
  preview: MutationSpec<Preview>
  charts: MutationSpec<Charts>
  throughFocus: MutationSpec<ThroughFocus>
  visual: MutationSpec<Visual>
  focus: MutationSpec<Focus>
}) {
  const validateMutation = useMutation(specs.validate)
  const registerMutation = useMutation(specs.register)
  const previewMutation = useMutation(specs.preview)
  const chartsMutation = useMutation(specs.charts)
  const throughFocusMutation = useMutation(specs.throughFocus)
  const visualMutation = useMutation(specs.visual)
  const focusMutation = useMutation(specs.focus)
  return { validateMutation, registerMutation, previewMutation, chartsMutation, throughFocusMutation, visualMutation, focusMutation }
}

export function useNavigationShellState() {
  const [viewportWidth, setViewportWidth] = useState(() => window.innerWidth)
  const [navigationExpanded, setNavigationExpanded] = useState(() => {
    const saved = window.localStorage.getItem(navigationStorageKey)
    return saved == null ? window.innerWidth >= 1440 : saved === 'true'
  })
  const [contextDrawerOpen, setContextDrawerOpen] = useState(false)

  useEffect(() => {
    const updateViewport = () => setViewportWidth(window.innerWidth)
    window.addEventListener('resize', updateViewport)
    return () => window.removeEventListener('resize', updateViewport)
  }, [])

  useEffect(() => {
    window.localStorage.setItem(navigationStorageKey, String(navigationExpanded))
  }, [navigationExpanded])

  const contextUsesDrawer = viewportWidth <= 1366
  return {
    viewportWidth,
    navigationExpanded,
    setNavigationExpanded,
    contextUsesDrawer,
    contextDrawerOpen,
    setContextDrawerOpen,
  }
}
