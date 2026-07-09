export function formatFixed(value: number | undefined | null, digits = 3): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return '-'
  return Number(value).toFixed(digits)
}

export function formatInteger(value: number | undefined | null): string {
  if (value === undefined || value === null || !Number.isFinite(value)) return '0'
  return String(Math.trunc(value))
}

export function isoNow(): string {
  return new Date().toISOString()
}

export function displayIsoDate(value: string): string {
  return value
}

