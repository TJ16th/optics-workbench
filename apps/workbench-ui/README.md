# Optics Workbench UI

## i18n key convention

All display strings use i18n resources under `src/i18n/locales/{ja,en}/{namespace}.json`.

Keys follow:

```text
{namespace}.{view}.{element}
```

Examples:

- `common.buttons.validate`
- `surfaceTable.columns.radius_mm`
- `analysis.trace_summary`

Do not use English text as the key. Engine identifiers such as surface IDs, metric raw keys, variable keys, error codes, and raw JSON are not translated.

## Glossary coverage

The attached seed files are copied without content changes:

- `src/i18n/glossary/glossary.ja.json`
- `src/i18n/glossary/glossary.en.json`

Engine-specific identifiers not present in the seed files live in `glossary.supplement.{lang}.json`. When the engine adds an identifier to `/v1/meta.enumerations`, add a matching term or error entry for both `ja` and `en` before merging.

## Checks

```bash
npm.cmd run i18n:check
npm.cmd run i18n:coverage
npm.cmd run i18n:test
npm.cmd run ui:build
```

Pseudo locale is available with:

```bash
npm.cmd run ui:build:pseudo
```

