export type WavelengthBand = 'F' | 'd' | 'e' | 'C' | 'custom'
export type ChartColorMode = 'light' | 'dark'

export const wavelengthPalette: Record<WavelengthBand, string> = {
  F: 'var(--ow-wave-f)',
  d: 'var(--ow-wave-d)',
  e: 'var(--ow-wave-e)',
  C: 'var(--ow-wave-c)',
  custom: 'var(--ow-wave-custom)',
}

export const seriesPalette = [
  'var(--ow-series-1)',
  'var(--ow-series-2)',
  'var(--ow-series-3)',
  'var(--ow-series-4)',
  'var(--ow-series-5)',
  'var(--ow-series-6)',
]

export const chartPalettes: Record<ChartColorMode, Record<WavelengthBand, string>> = {
  light: { F: '#0f62fe', d: '#8a7400', e: '#198038', C: '#da1e28', custom: '#525252' },
  dark: { F: '#78a9ff', d: '#f1c21b', e: '#42be65', C: '#fa4d56', custom: '#c6c6c6' },
}

export function wavelengthBand(wavelengthNm: number): WavelengthBand {
  if (Math.abs(wavelengthNm - 486.13) <= 1.0) return 'F'
  if (Math.abs(wavelengthNm - 587.56) <= 1.0) return 'd'
  if (Math.abs(wavelengthNm - 546.07) <= 1.0) return 'e'
  if (Math.abs(wavelengthNm - 656.27) <= 1.0) return 'C'
  return 'custom'
}

export function wavelengthColor(wavelengthNm: number): string {
  return wavelengthPalette[wavelengthBand(wavelengthNm)]
}
