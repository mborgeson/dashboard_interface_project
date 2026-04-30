import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env.CI;

/**
 * Playwright E2E Test Configuration
 * B&R Capital Real Estate Analytics Dashboard
 *
 * Projects:
 *   - "chromium" (default): Local development — all browsers, no retries, HTML reporter
 *   - "ci": CI pipeline — chromium only, 1 retry, 30s timeout, JSON + HTML reporters
 *
 * Usage:
 *   Local:  npx playwright test
 *   CI:     npx playwright test --project=ci
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  /* Default retries/workers — overridden per-project */
  retries: 0,
  /* CI: 4 workers on a 4-core ubuntu-latest runner. Was 1 — caused 403 tests to
   * exhaust the 60m job timeout on every run. Drop to 2 if memory pressure surfaces. */
  workers: isCI ? 4 : undefined,
  reporter: isCI
    ? [['json', { outputFile: 'playwright-report/results.json' }], ['html', { open: 'never' }]]
    : 'html',

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    /* Local development project — runs by default when no --project is specified */
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    /* CI project — single browser, stricter timeouts, retries on failure */
    {
      name: 'ci',
      use: {
        ...devices['Desktop Chrome'],
        /* CI-specific: capture video on first retry for debugging */
        video: 'on-first-retry',
      },
      retries: 1,
      timeout: 30_000,
    },
  ],

  /* Run local dev server before starting tests (local only).
   * In CI, the workflow starts backend + frontend separately before running tests,
   * so we skip the webServer to avoid conflicts. */
  ...(isCI
    ? {}
    : {
        webServer: {
          command: 'npm run dev',
          url: 'http://localhost:5173',
          reuseExistingServer: true,
          timeout: 120_000,
        },
      }),
});
