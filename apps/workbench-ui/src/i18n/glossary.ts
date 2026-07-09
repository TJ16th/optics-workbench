import glossaryEn from './glossary/glossary.en.json'
import glossaryJa from './glossary/glossary.ja.json'
import supplementEn from './glossary/glossary.supplement.en.json'
import supplementJa from './glossary/glossary.supplement.ja.json'
import type { SupportedLanguage } from './resources'

export type GlossaryTerm = {
  label: string
  en_term: string
  short: string
  long?: string
  formula?: string
  see_also?: string[]
  lesson_mode?: string | null
}

export type ErrorCatalogEntry = {
  label: string
  message: string
  action: string
}

export type Glossary = {
  $schema_version: string
  language: string
  terms: Record<string, GlossaryTerm>
  errors: Record<string, ErrorCatalogEntry>
}

export type EngineIssue = {
  code?: string
  type?: string
  params?: Record<string, unknown>
  message_en?: string
  message?: string
  severity?: 'error' | 'warning' | 'info'
  surface_id?: string
}

function mergeGlossary(base: Glossary, supplement: Glossary): Glossary {
  if (base.$schema_version !== supplement.$schema_version) {
    throw new Error(`glossary schema mismatch: ${base.$schema_version} !== ${supplement.$schema_version}`)
  }
  return {
    ...base,
    terms: { ...base.terms, ...supplement.terms },
    errors: { ...base.errors, ...supplement.errors },
  }
}

const merged = {
  en: mergeGlossary(glossaryEn as Glossary, supplementEn as Glossary),
  ja: mergeGlossary(glossaryJa as Glossary, supplementJa as Glossary),
}

export function normalizeGlossaryLanguage(language: string): 'ja' | 'en' {
  return language.startsWith('ja') ? 'ja' : 'en'
}

export function getGlossary(language: string): Glossary {
  return merged[normalizeGlossaryLanguage(language)]
}

export function getTerm(termId: string, language: string): GlossaryTerm | undefined {
  return getGlossary(language).terms[termId]
}

export function termLabel(termId: string, language: string, fallback = termId): string {
  const term = getTerm(termId, language)
  if (!term) return fallback
  if (normalizeGlossaryLanguage(language) === 'ja' && term.en_term && term.en_term !== term.label) {
    return `${term.label} (${term.en_term})`
  }
  return term.label
}

function stringifyParam(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => stringifyParam(item)).join('-')
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '-'
  if (value === undefined || value === null) return ''
  return String(value)
}

export function interpolateTemplate(template: string, params: Record<string, unknown>, messageEn?: string): string {
  const mergedParams: Record<string, unknown> = { ...params, message_en: messageEn ?? '' }
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key: string) => stringifyParam(mergedParams[key]))
}

export function renderEngineIssue(issue: EngineIssue, language: string): { title: string; message: string; action?: string; code: string; severity: string } {
  const code = issue.code ?? issue.type ?? 'api_error'
  const params = issue.params ?? {}
  const messageEn = issue.message_en ?? issue.message ?? code
  const catalog = getGlossary(language).errors[code]
  if (!catalog) {
    console.warn(`Unregistered engine issue code: ${code}`)
    return { title: code, message: messageEn, code, severity: issue.severity ?? 'error' }
  }
  return {
    title: catalog.label,
    message: interpolateTemplate(catalog.message, params, messageEn),
    action: interpolateTemplate(catalog.action, params, messageEn),
    code,
    severity: issue.severity ?? 'error',
  }
}

export function glossaryKeySet(language: SupportedLanguage) {
  const glossary = getGlossary(language)
  return {
    terms: new Set(Object.keys(glossary.terms)),
    errors: new Set(Object.keys(glossary.errors)),
  }
}
