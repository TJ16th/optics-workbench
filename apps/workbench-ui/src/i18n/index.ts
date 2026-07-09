import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'
import { namespaces, pseudoResources, resources, type SupportedLanguage } from './resources'

export const languageStorageKey = 'optics.workbench.language'

function normalizeLanguage(value: string | undefined | null): SupportedLanguage | null {
  if (!value) return null
  const lower = value.toLowerCase()
  if (lower === 'pseudo') return 'pseudo'
  if (lower.startsWith('ja')) return 'ja'
  if (lower.startsWith('en')) return 'en'
  return null
}

export function initialLanguage(): SupportedLanguage {
  if (import.meta.env.VITE_PSEUDO_LOCALE === '1') return 'pseudo'
  const urlLanguage = normalizeLanguage(new URLSearchParams(window.location.search).get('lng'))
  if (urlLanguage) {
    persistLanguage(urlLanguage)
    return urlLanguage
  }
  const stored = normalizeLanguage(window.localStorage.getItem(languageStorageKey))
  if (stored) return stored
  return normalizeLanguage(window.navigator.language) ?? 'en'
}

export function persistLanguage(language: SupportedLanguage) {
  window.localStorage.setItem(languageStorageKey, language)
}

export async function changeLanguage(language: SupportedLanguage) {
  persistLanguage(language)
  await i18next.changeLanguage(language)
}

void i18next.use(initReactI18next).init({
  resources: {
    ...resources,
    pseudo: pseudoResources,
  },
  lng: initialLanguage(),
  fallbackLng: 'en',
  ns: namespaces,
  defaultNS: 'common',
  interpolation: {
    escapeValue: false,
  },
})

export { i18next }
