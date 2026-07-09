import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL: 'http://127.0.0.1:5177',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'node ../../node_modules/vite/bin/vite.js . --host 127.0.0.1 --port 5177',
    url: 'http://127.0.0.1:5177/?lng=en',
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    {
      name: 'msedge',
      use: { ...devices['Desktop Chrome'], channel: 'msedge' },
    },
  ],
})
