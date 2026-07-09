import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const srcDir = path.join(root, 'apps/workbench-ui/src')
const localeDir = path.join(srcDir, 'i18n/locales')
const namespaces = ['common', 'surfaceTable', 'layoutView', 'analysis', 'settings', 'units']
const languages = ['ja', 'en']

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'))
}

function flatten(value, prefix = '', out = new Set()) {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    for (const [key, child] of Object.entries(value)) {
      flatten(child, prefix ? `${prefix}.${key}` : key, out)
    }
  } else {
    out.add(prefix)
  }
  return out
}

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'dist' || entry.name === 'node_modules') continue
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(full, out)
    else if (/\.(ts|tsx)$/.test(entry.name)) out.push(full)
  }
  return out
}

const resourceKeys = new Map()
for (const lang of languages) {
  const keys = new Set()
  for (const ns of namespaces) {
    const file = path.join(localeDir, lang, `${ns}.json`)
    const json = readJson(file)
    for (const key of flatten(json)) keys.add(`${ns}:${key}`)
  }
  resourceKeys.set(lang, keys)
}

const source = walk(srcDir)
  .map((file) => fs.readFileSync(file, 'utf8'))
  .join('\n')

const referenced = new Set()
const namespaceSet = new Set(namespaces)
const normalizeKey = (raw) => {
  if (raw.includes(':')) return raw
  const first = raw.split('.')[0]
  if (namespaceSet.has(first)) return `${first}:${raw}`
  return `common:${raw}`
}
const tCall = /\bt\(\s*['"`]([A-Za-z0-9_.:-]+)['"`]/g
for (const match of source.matchAll(tCall)) {
  const raw = match[1]
  const key = normalizeKey(raw)
  if (key.includes('${')) continue
  referenced.add(key)
}

const allowedDynamicPrefixes = [
  'common:common.tabs.',
  'common:common.preset.items.',
  'surfaceTable:surfaceTable.columns.',
  'surfaceTable:surfaceTable.help.',
  'units:units.',
]

const allowedDynamicKeys = new Set([
  'surfaceTable:surfaceTable.groups.issue_error',
  'surfaceTable:surfaceTable.groups.issue_warning',
  'surfaceTable:surfaceTable.groups.duplicate_id',
  'surfaceTable:surfaceTable.groups.unknown_surface',
  'surfaceTable:surfaceTable.groups.invalid_range',
  'surfaceTable:surfaceTable.groups.overlap',
])

const errors = []
for (const lang of languages) {
  const keys = resourceKeys.get(lang)
  for (const key of referenced) {
    if (!keys.has(key)) errors.push(`${lang}: missing i18n key ${key}`)
  }
  for (const key of keys) {
    if (allowedDynamicPrefixes.some((prefix) => key.startsWith(prefix))) continue
    if (allowedDynamicKeys.has(key)) continue
    if (!referenced.has(key)) errors.push(`${lang}: unused i18n key ${key}`)
  }
}

if (errors.length) {
  console.error(errors.join('\n'))
  process.exit(1)
}

console.log(`i18n:check ok (${referenced.size} keys)`)
