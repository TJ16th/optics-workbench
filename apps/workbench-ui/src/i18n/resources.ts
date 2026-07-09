import analysisEn from './locales/en/analysis.json'
import commonEn from './locales/en/common.json'
import layoutViewEn from './locales/en/layoutView.json'
import settingsEn from './locales/en/settings.json'
import surfaceTableEn from './locales/en/surfaceTable.json'
import unitsEn from './locales/en/units.json'
import analysisJa from './locales/ja/analysis.json'
import commonJa from './locales/ja/common.json'
import layoutViewJa from './locales/ja/layoutView.json'
import settingsJa from './locales/ja/settings.json'
import surfaceTableJa from './locales/ja/surfaceTable.json'
import unitsJa from './locales/ja/units.json'

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
type ResourceTree = Record<string, JsonValue>

function pseudoText(value: string) {
  return `[!! ${value} !!]`
}

function makePseudo<T extends JsonValue>(value: T): T {
  if (typeof value === 'string') return pseudoText(value) as T
  if (Array.isArray(value)) return value.map((item) => makePseudo(item)) as T
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, makePseudo(item)])) as T
  }
  return value
}

export const resources = {
  en: {
    common: commonEn as ResourceTree,
    surfaceTable: surfaceTableEn as ResourceTree,
    layoutView: layoutViewEn as ResourceTree,
    analysis: analysisEn as ResourceTree,
    settings: settingsEn as ResourceTree,
    units: unitsEn as ResourceTree,
  },
  ja: {
    common: commonJa as ResourceTree,
    surfaceTable: surfaceTableJa as ResourceTree,
    layoutView: layoutViewJa as ResourceTree,
    analysis: analysisJa as ResourceTree,
    settings: settingsJa as ResourceTree,
    units: unitsJa as ResourceTree,
  },
} as const

export const pseudoResources = makePseudo(resources.en)

export const namespaces = ['common', 'surfaceTable', 'layoutView', 'analysis', 'settings', 'units'] as const
export const supportedLanguages = ['ja', 'en', 'pseudo'] as const
export type SupportedLanguage = (typeof supportedLanguages)[number]

