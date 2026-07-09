import { build } from 'esbuild'
import { readFile, mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(scriptDir, '..')
const repoDir = path.resolve(appDir, '..', '..')
const outDir = path.join(appDir, '.test-build')
const outFile = path.join(outDir, 'exportSvg.mjs')

await mkdir(outDir, { recursive: true })
await build({
  entryPoints: [path.join(appDir, 'src', 'ui', 'exportSvg.ts')],
  outfile: outFile,
  bundle: true,
  platform: 'browser',
  format: 'esm',
  logLevel: 'silent',
})

const { makeExportSvg } = await import(`${pathToFileURL(outFile).href}?t=${Date.now()}`)

async function readJson(relativePath) {
  const raw = await readFile(path.join(repoDir, relativePath), 'utf8')
  return JSON.parse(raw)
}

const glossary = {
  ja: await readJson('apps/workbench-ui/src/i18n/glossary/glossary.ja.json'),
  en: await readJson('apps/workbench-ui/src/i18n/glossary/glossary.en.json'),
}

function termLabel(termId, language, fallback = termId) {
  const lang = language.startsWith('ja') ? 'ja' : 'en'
  const term = glossary[lang].terms[termId]
  if (!term) return fallback
  if (lang === 'ja' && term.en_term && term.en_term !== term.label) {
    return `${term.label} (${term.en_term})`
  }
  return term.label
}

function textNodes(svg) {
  return [...svg.matchAll(/<text\b[^>]*>([^<]*)<\/text>/g)].map((match) => match[1])
}

function assertIncludes(labels, expected, context) {
  if (!labels.includes(expected)) {
    throw new Error(`${context}: expected SVG text label "${expected}", got ${JSON.stringify(labels)}`)
  }
}

function assertSvgLabels(chart, language) {
  const svg = makeExportSvg(chart, language)
  const labels = textNodes(svg)
  const title = chart === 'layout' ? termLabel('ray_fan', language, 'ray_fan') : termLabel('spot_diagram', language, 'spot_diagram')
  const field = termLabel('field', language, 'field')
  assertIncludes(labels, title, `${chart}/${language} title`)
  assertIncludes(labels, field, `${chart}/${language} axis`)
  if (!svg.startsWith('<svg ') || !svg.endsWith('</svg>')) {
    throw new Error(`${chart}/${language}: exported content is not an SVG document`)
  }
}

for (const language of ['ja', 'en']) {
  for (const chart of ['layout', 'spot']) {
    assertSvgLabels(chart, language)
  }
}

console.log('svg-export-readback ok: ja/en layout/spot labels verified')
