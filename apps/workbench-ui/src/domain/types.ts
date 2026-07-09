export type Material = {
  id: string
  type: 'constant' | 'nd_vd' | 'sellmeier' | 'catalog' | 'custom_table'
  n?: number
  nd?: number
  vd?: number
  B?: number[]
  C?: number[]
}

export type VariableNumber = {
  variable: string
  default: number
}

export type ScalarNumber = number | VariableNumber

export type Surface = {
  id: string
  kind: string
  surface_type?: string
  radius_mm?: number
  conic?: number
  asphere_coefficients?: Record<string, number>
  thickness_after_mm?: number
  material_after?: string
  semi_diameter_mm?: ScalarNumber
  aperture?: {
    shape: 'circle' | 'annulus' | 'polygon'
    semi_diameter_mm?: ScalarNumber
    outer_semi_diameter_mm?: ScalarNumber
    inner_semi_diameter_mm?: ScalarNumber
  }
  sensor?: {
    width_mm: number
    height_mm: number
    pixel_pitch_um?: number
  }
  eye?: {
    pupil_diameter_mm?: number
    position_mode?: string
    offset_from_last_surface_mm?: number
  }
  focal_length_mm?: number
}

export type OpticalSystem = {
  name: string
  units?: 'mm'
  optical_axis?: '+X'
  system_type?: 'focal' | 'afocal'
  wavelengths_nm?: {
    primary: number
    samples: number[]
  }
  materials: Material[]
  surfaces: Surface[]
  groups?: OpticalGroup[]
  zoom_positions?: Array<{
    id: string
    focal_length_nominal_mm?: number
    group_positions: Record<string, { shift_x_mm?: number; shift_y_mm?: number; shift_z_mm?: number }>
  }>
  metadata?: Record<string, unknown>
}

export type OpticalGroup = {
  id: string
  name?: string
  from_surface: string
  to_surface: string
}

export type RuntimeConfiguration = {
  zoom_position?: string
  group_positions?: Record<string, { shift_x_mm?: number; shift_y_mm?: number; shift_z_mm?: number }>
  decenters?: Array<{ group?: string; shift_y_mm?: number; shift_z_mm?: number }>
  tilts?: Array<{
    group?: string
    tilt_y_deg?: number
    tilt_z_deg?: number
    roll_x_deg?: number
    rotation_center?: { reference?: string; offset_x_mm?: number; offset_y_mm?: number; offset_z_mm?: number }
  }>
  variables?: Record<string, number>
}

export type AnalysisField = {
  id: string
  type: 'angular'
  theta_y_deg: number
  theta_z_deg: number
}

export type WavelengthSample = {
  wavelength_nm: number
  weight: number
}

export type ImagePlanePolicyMode = 'fixed_sensor' | 'paraxial_image' | 'best_focus_rms' | 'best_focus_mtf' | 'custom_offset' | 'sweep'

export type ImagePlanePolicyApplyTo = 'evaluation_plane' | 'focus_group' | 'report_only'

export type ImagePlanePolicy = {
  mode: ImagePlanePolicyMode
  apply_to: ImagePlanePolicyApplyTo
  offset_mm?: number
  frequency_lpmm?: number
  criteria?: {
    fields?: Array<AnalysisField & { weight?: number }>
    wavelengths?: Array<{ wavelength_nm: number; weight?: number }>
    frequency_lpmm?: number
  }
  search?: {
    range_mm?: number
    tolerance_mm?: number
    max_iterations?: number
    steps?: number
  }
}

export type FocusCurvePoint = {
  offset_from_sensor_mm: number
  metric: number
}

export type EvaluationPlaneMetadata = {
  policy_mode?: string
  apply_to?: string
  evaluation_plane_x_mm?: number
  sensor_x_mm?: number
  offset_from_sensor_mm?: number
  solved_evaluation_plane_x_mm?: number
  solved_offset_from_sensor_mm?: number
  solved_focus_group_shift_mm?: number | null
  solve_status?: string
  solve_metric?: number
  focus_curve?: FocusCurvePoint[]
  warnings?: EngineIssue[]
}

export type BestFocusResponse = {
  evaluation_plane: EvaluationPlaneMetadata
  focus_curve?: FocusCurvePoint[]
  artifacts?: Record<string, string>
  metadata?: Record<string, unknown>
}

export type Preset = {
  id: string
  name: string
  summary: string
  recommendedAnalysis: string[]
  system: OpticalSystem
}

export type EngineMeta = {
  engine_version: string
  api_schema_version: string
  result_schema_version: string
  material_catalog_version: string
  preset_version: string
  build_info?: {
    git_commit: string
    git_dirty: boolean
    started_at: string
  }
  capabilities: Record<string, unknown>
  enumerations?: {
    metrics: string[]
    error_codes: string[]
    warning_codes: string[]
    ray_status_codes: string[]
    variable_key_patterns: string[]
  }
}

export type EngineIssue = {
  code: string
  params: Record<string, unknown>
  message_en: string
  severity: 'error' | 'warning' | 'info'
  surface_id?: string
}

export type ValidationResult = {
  status: 'ok' | 'warning' | 'error'
  issues: EngineIssue[]
}

export type TraceResponse = {
  status: string[]
  sensor_y_mm: number[]
  sensor_z_mm: number[]
  paths?: Array<
    Array<{
      surface_id: string
      point_mm: [number, number, number] | number[]
      local_point_mm?: [number, number, number] | number[]
      direction?: [number, number, number] | number[]
      status?: string
    }>
  >
  metadata: {
    evaluated_fields?: AnalysisField[]
    wavelengths_nm?: number[]
    pupil_distribution?: string
    ray_aiming_mode?: string
    samples_per_field?: number
    profiling?: Record<string, number | boolean | null>
    [key: string]: unknown
  }
}

export type ArtifactMap = Record<string, string>

export type RayFanPoint = {
  field_id: string
  wavelength_nm: number
  pupil_y: number
  pupil_z: number
  sensor_y_mm: number | null
  sensor_z_mm: number | null
  transverse_error_y_mm: number | null
  transverse_error_z_mm: number | null
  status: string
}

export type LongitudinalAberrationPoint = {
  field_id: string
  wavelength_nm: number
  pupil_y: number
  pupil_z: number
  focus_x_y_mm: number | null
  focus_x_z_mm: number | null
  longitudinal_error_y_mm: number | null
  longitudinal_error_z_mm: number | null
  status: string
}

export type DistortionRow = {
  field_id: string
  theta_y_deg: number
  theta_z_deg: number
  ideal_y_mm: number | null
  ideal_z_mm: number | null
  distortion_percent: number | null
}

export type FieldCurvatureRow = {
  field_id: string
  theta_y_deg: number
  theta_z_deg: number
  best_focus_shift_mm: number | null
  rms_radius_mm?: number | null
  tangential_focus_shift_mm?: number | null
  sagittal_focus_shift_mm?: number | null
}

export type RelativeIlluminationRow = {
  field_id: string
  theta_y_deg: number
  theta_z_deg: number
  relative_illumination: number
  throughput: number
  cos4_factor: number
}

export type MtfPoint = {
  frequency_lp_per_mm: number
  mtf_y: number
  mtf_z: number
  mtf_radial: number
}

export type ChartAnalysisResult = {
  rayFan?: { points: RayFanPoint[]; metadata?: Record<string, unknown>; artifacts?: ArtifactMap }
  longitudinal?: { points: LongitudinalAberrationPoint[]; metadata?: Record<string, unknown>; artifacts?: ArtifactMap }
  distortion?: { rows: DistortionRow[]; metadata?: Record<string, unknown>; artifacts?: ArtifactMap }
  fieldCurvature?: { rows: FieldCurvatureRow[]; artifacts?: ArtifactMap }
  relativeIllumination?: { rows: RelativeIlluminationRow[]; metadata?: Record<string, unknown>; artifacts?: ArtifactMap }
  mtf?: { points: MtfPoint[]; diffraction_included?: boolean; metadata?: Record<string, unknown>; artifacts?: ArtifactMap }
}
