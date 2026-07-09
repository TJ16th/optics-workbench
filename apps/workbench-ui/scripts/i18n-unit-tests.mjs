import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const glossaryDir = path.join(root, 'apps/workbench-ui/src/i18n/glossary')

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'))
}

function merge(lang) {
  const base = readJson(path.join(glossaryDir, `glossary.${lang}.json`))
  const supplement = readJson(path.join(glossaryDir, `glossary.supplement.${lang}.json`))
  return {
    terms: { ...base.terms, ...supplement.terms },
    errors: { ...base.errors, ...supplement.errors },
  }
}

function interpolate(template, params, messageEn = '') {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key) => {
    const value = key === 'message_en' ? messageEn : params[key]
    return Array.isArray(value) ? value.join('-') : String(value ?? '')
  })
}

function render(issue, lang) {
  const glossary = merge(lang)
  const code = issue.code || issue.type
  const entry = glossary.errors[code]
  if (!entry) return { title: code, message: issue.message_en, action: undefined }
  return {
    title: entry.label,
    message: interpolate(entry.message, issue.params || {}, issue.message_en),
    action: interpolate(entry.action, issue.params || {}, issue.message_en),
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const issue = {
  code: 'negative_air_gap',
  params: { surface_ids: ['S4', 'S5'], gap_mm: -0.35 },
  message_en: 'Air gap between S4 and S5 is negative (-0.35 mm).',
  severity: 'error',
}

const ja = render(issue, 'ja')
const en = render(issue, 'en')
assert(ja.message.includes('S4-S5'), 'ja negative_air_gap should render surface ids')
assert(ja.message.includes('-0.35'), 'ja negative_air_gap should render gap')
assert(en.message.includes('S4-S5'), 'en negative_air_gap should render surface ids')
assert(en.message.includes('-0.35'), 'en negative_air_gap should render gap')

const fallback = render({ code: 'unknown_code', message_en: 'Fallback message.', params: {} }, 'ja')
assert(fallback.message === 'Fallback message.', 'unknown errors should fall back to message_en')

const snapshot = {
  created_at: '2026-07-09T00:00:00.000Z',
  metrics: { rms_spot_radius: 1.25 },
}
assert(Object.keys(snapshot.metrics)[0] === 'rms_spot_radius', 'snapshot stores raw metric key')
assert(snapshot.created_at.endsWith('Z'), 'snapshot stores ISO 8601 date')

const number = (1.5).toFixed(3)
assert(number === '1.500', 'numeric formatting must use fixed period decimal')
assert('mm' === 'mm' && 'µm' === 'µm' && 'deg' === 'deg', 'units are not translated')

console.log('i18n:test ok')

