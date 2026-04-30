import { test, expect } from '@playwright/test';

/**
 * Smoke fail-fast test
 *
 * One-shot infrastructure check that runs BEFORE every other Playwright project
 * via the `smoke` project + `dependencies: ['smoke']` wiring in playwright.config.ts.
 *
 * Purpose:
 *   Detect the catastrophic, "nothing will pass" failures (dev server down,
 *   broken build, routing wedged) and abort the suite in <2 minutes instead of
 *   running ~40 minutes of redundant red across hundreds of dependent tests.
 *
 * Scope (intentionally narrow):
 *   - Standalone — no auth, no storageState, no backend dependency beyond the
 *     login page being reachable. Composes cleanly with the auth setup project
 *     (PR #12); both can run as dependencies of `chromium`/`ci` in any order.
 *   - Tests only the most fundamental contract: dev server serves the React
 *     app and the auth-gated router redirects unauthenticated users to /login.
 *
 * Failure semantics:
 *   - retries: 0 (configured at the project level) — flakes are not tolerated
 *     here; if smoke is flaky, fix smoke. A pass means downstream tests have a
 *     chance; a fail means they have no chance, so Playwright skips them.
 */
test.describe('Smoke', () => {
  test('dev server serves the app and routing redirects to /login', async ({ page }) => {
    // Hitting the root should bounce an unauthenticated user to /login.
    // This single navigation proves three things at once:
    //   1. The dev server is reachable on baseURL (http://localhost:5173).
    //   2. Vite served the React bundle (HTML + JS).
    //   3. The router booted and the auth gate redirect ran.
    await page.goto('/');

    await expect(page).toHaveURL(/\/login$/, { timeout: 10_000 });

    // And the login page actually rendered — not a blank white screen from a
    // hydration crash. getByLabel matches the <Label htmlFor="email">Email</Label>
    // pair in src/features/auth/LoginPage.tsx.
    await expect(page.getByLabel(/email/i)).toBeVisible({ timeout: 5_000 });
  });
});
