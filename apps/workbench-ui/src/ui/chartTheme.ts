export type WavelengthBand = 'F' | 'd' | 'e' | 'C' | 'custom'

export const wavelengthPalette: Record<WavelengthBand, string> = {
  F: '#0f62fe',
  d: '#8a7400',
  e: '#24a148',
  C: '#da1e28',
  custom: '#6f6f6f',
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
