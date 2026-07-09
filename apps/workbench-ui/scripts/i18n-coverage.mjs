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

async function readMeta() {
  const url = process.env.ENGINE_META_URL || 'http://127.0.0.1:8000/v1/meta'
  try {
    const response = await fetch(url)
    if (response.ok) return response.json()
  } catch {
    // Fall through to static parser for CI environments without a running API.
  }
  const metadata = fs.readFileSync(path.join(root, 'optics_engine/metadata.py'), 'utf8')
  const readList = (name) => {
    const match = metadata.match(new RegExp(`${name} = \\[((?:.|\\n)*?)\\]`, 'm'))
    if (!match) return []
    return [...match[1].matchAll(/"([^"]+)"/g)].map((item) => item[1])
  }
  return {
    enumerations: {
      metrics: readList('METRIC_CODES'),
      error_codes: readList('ERROR_CODES'),
      warning_codes: readList('WARNING_CODES'),
      ray_status_codes: readList('RAY_STATUS_CODES'),
      variable_key_patterns: readList('VARIABLE_KEY_PATTERNS'),
    },
  }
}

const ja = merge('ja')
const en = merge('en')
const errors = []

for (const bucket of ['terms', 'errors']) {
  const jaKeys = Object.keys(ja[bucket]).sort()
  const enKeys = Object.keys(en[bucket]).sort()
  const missingJa = enKeys.filter((key) => !jaKeys.includes(key))
  const missingEn = jaKeys.filter((key) => !enKeys.includes(key))
  if (missingJa.length) errors.push(`ja ${bucket} missing: ${missingJa.join(', ')}`)
  if (missingEn.length) errors.push(`en ${bucket} missing: ${missingEn.join(', ')}`)
}

const meta = await readMeta()
const enumerations = meta.enumerations || {}
const termSet = new Set([...Object.keys(ja.terms), ...Object.keys(en.terms)])
const errorSet = new Set([...Object.keys(ja.errors), ...Object.keys(en.errors)])

for (const key of enumerations.metrics || []) {
  if (!termSet.has(key)) errors.push(`metric missing glossary term: ${key}`)
}
for (const key of enumerations.error_codes || []) {
  if (!errorSet.has(key)) errors.push(`error code missing glossary error: ${key}`)
}
for (const key of enumerations.warning_codes || []) {
  if (!termSet.has(key) && !errorSet.has(key)) errors.push(`warning code missing glossary entry: ${key}`)
}
for (const key of enumerations.ray_status_codes || []) {
  if (!termSet.has(key) && !errorSet.has(key)) errors.push(`ray status missing glossary entry: ${key}`)
}

if (process.env.I18N_COVERAGE_RED_TEST === '1') {
  errors.push('red-test: deliberate coverage failure')
}

if (errors.length) {
  console.error(errors.join('\n'))
  process.exit(1)
}

console.log('i18n:coverage ok')

