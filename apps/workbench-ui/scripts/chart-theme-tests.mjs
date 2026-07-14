import { build } from 'esbuild'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(scriptDir, '..')
const outDir = path.join(appDir, '.test-build')
const outFile = path.join(outDir, 'chartTheme.mjs')

await mkdir(outDir, { recursive: true })
await build({
  entryPoints: [path.join(appDir, 'src', 'ui', 'chartTheme.ts')],
  outfile: outFile,
  bundle: true,
  platform: 'browser',
  format: 'esm',
  logLevel: 'silent',
})

const { chartPalettes, wavelengthBand, wavelengthColor, wavelengthPalette } = await import(`${pathToFileURL(outFile).href}?t=${Date.now()}`)

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

assert(wavelengthBand(486.13) === 'F', 'F line should map to blue band')
assert(wavelengthBand(587.56) === 'd', 'd line should map to yellow-green band')
assert(wavelengthBand(546.07) === 'e', 'e line should map to green band')
assert(wavelengthBand(656.27) === 'C', 'C line should map to red band')
assert(wavelengthBand(610) === 'custom', 'custom wavelengths should use neutral band')
assert(wavelengthColor(486.13) === wavelengthPalette.F, 'F line color mismatch')
assert(wavelengthColor(656.27) === wavelengthPalette.C, 'C line color mismatch')
assert(new Set(['F', 'd', 'e', 'C'].map((band) => wavelengthPalette[band])).size === 4, 'standard line colors must be distinct')
assert(chartPalettes.light.F !== chartPalettes.dark.F, 'light and dark chart palettes should use different contrast values')
assert(new Set(['F', 'd', 'e', 'C'].map((band) => chartPalettes.dark[band])).size === 4, 'dark standard line colors must remain distinct')

console.log('chart-theme:test ok')
