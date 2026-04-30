import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env.CI;

/**
 * Playwright E2E Test Configuration
 * B&R Capital Real Estate Analytics Dashboard
 *
 * Projects:
 *   - "smoke": One-shot infrastructure check — dev server up, app renders,
 *     routing works. Runs FIRST. If it fails, downstream projects are skipped
 *     and the suite exits in <2 min instead of ~40 min of redundant red.
 *   - "setup": Authenticates a browser context and saves storage state to
 *     e2e/.auth/admin.json so subsequent UI tests don't bounce to /login.
 *     Runs after smoke so a broken dev server fails before we waste time
 *     trying to log in.
 *   - "chromium" (default): Local development — depends on smoke + setup.
 *   - "ci": CI pipeline — chromium only, depends on smoke + setup, 1 retry,
 *     30s timeout, JSON + HTML reporters.
 *
 * Usage:
 *   Local:  npx playwright test
 *   CI:     npx playwright test --project=ci
 *   Smoke:  npx playwright test --project=smoke
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
    /* Smoke fail-fast project — runs FIRST. If dev server / build / routing
     * is broken, downstream projects are skipped and the suite exits fast.
     * Standalone: no auth, no storageState, no backend dependency beyond
     * the login page being reachable. */
    {
      name: 'smoke',
      testMatch: /smoke\.spec\.ts/,
      retries: 0,
      use: { ...devices['Desktop Chrome'] },
    },

    /* Setup project — runs after smoke. Authenticates a browser context
     * and persists storage state to e2e/.auth/admin.json so subsequent UI
     * tests don't bounce to /login. */
    {
      name: 'setup',
      testMatch: /global\.setup\.ts/,
      dependencies: ['smoke'],
    },

    /* Local development project — runs by default when no --project is specified */
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/admin.json',
      },
      testIgnore: /(smoke|global\.setup)\.spec\.ts/,
      dependencies: ['smoke', 'setup'],
    },

    /* CI project — single browser, stricter timeouts, retries on failure */
    {
      name: 'ci',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/admin.json',
        /* CI-specific: capture video on first retry for debugging */
        video: 'on-first-retry',
      },
      testIgnore: /(smoke|global\.setup)\.spec\.ts/,
      dependencies: ['smoke', 'setup'],
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
