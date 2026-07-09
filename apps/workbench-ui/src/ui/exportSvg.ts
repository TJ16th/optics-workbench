import { termLabel } from '../i18n/glossary'

export type ExportChart = 'layout' | 'spot'

export function makeExportSvg(chart: ExportChart, language: string) {
  const title = chart === 'layout' ? termLabel('ray_fan', language, 'ray_fan') : termLabel('spot_diagram', language, 'spot_diagram')
  const axisY = termLabel('field', language, 'Y')
  const axisZ = termLabel('field', language, 'Z')
  return `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="#ffffff"/>
  <text x="24" y="36" font-family="Arial" font-size="18">${title}</text>
  <line x1="60" y1="180" x2="580" y2="180" stroke="#8d8d8d"/>
  <line x1="320" y1="70" x2="320" y2="300" stroke="#8d8d8d"/>
  <text x="584" y="184" font-family="Arial" font-size="12">${axisY}</text>
  <text x="324" y="78" font-family="Arial" font-size="12">${axisZ}</text>
  <circle cx="320" cy="180" r="5" fill="#0f62fe"/>
</svg>`
}
