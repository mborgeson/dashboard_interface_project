import { test as setup, expect } from '@playwright/test';
import { TEST_CREDENTIALS } from './fixtures/auth';

/**
 * Playwright "setup" project: authenticates once and persists the browser
 * storage state to disk. Browser-context tests reuse this state via
 * `use: { storageState: 'e2e/.auth/admin.json' }` in playwright.config.ts,
 * so they start already logged in and skip the /login redirect.
 *
 * The auth store (src/stores/authStore.ts) persists tokens to localStorage,
 * so we drive the UI login flow to ensure the store is properly hydrated.
 * `storageState()` captures cookies + localStorage + sessionStorage by default.
 */
const AUTH_FILE = 'e2e/.auth/admin.json';

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login');

  await page.getByLabel('Email').fill(TEST_CREDENTIALS.admin.email);
  await page.getByLabel('Password').fill(TEST_CREDENTIALS.admin.password);
  await page.getByRole('button', { name: /sign in/i }).click();

  // RequireAuth replaces /login with / on successful auth, so wait for the
  // URL to land on the dashboard root before snapshotting storage.
  await page.waitForURL('**/', { timeout: 30_000 });
  await expect(page.locator('main')).toBeVisible({ timeout: 15_000 });

  await page.context().storageState({ path: AUTH_FILE });
});
