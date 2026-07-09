module.exports = {
  locales: ['ja', 'en'],
  namespaceSeparator: ':',
  keySeparator: '.',
  defaultNamespace: 'common',
  input: ['src/**/*.{ts,tsx}'],
  output: 'apps/workbench-ui/.i18n-parser/$LOCALE/$NAMESPACE.json',
  createOldCatalogs: false,
  keepRemoved: false,
  sort: true,
}
