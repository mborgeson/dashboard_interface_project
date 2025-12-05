import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Navigation
 * Tests navigation between pages and route handling
 */
test.describe('Navigation', () => {
  test('should navigate to Investments page', async ({ page }) => {
    await page.goto('/');

    // Click Investments link
    await page.getByRole('link', { name: /investments/i }).click();

    // Verify URL changed
    await expect(page).toHaveURL(/\/investments/);

    // Verify page header loaded - "Investment Portfolio" is the heading
    await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
  });

  test('should navigate to Transactions page', async ({ page }) => {
    await page.goto('/');

    // Click Transactions link
    await page.getByRole('link', { name: /transactions/i }).click();

    // Verify URL changed
    await expect(page).toHaveURL(/\/transactions/);

    // Verify page has transaction-related content
    await expect(page.locator('table, [role="table"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to Analytics page', async ({ page }) => {
    await page.goto('/');

    // Click Analytics link
    await page.getByRole('link', { name: /analytics/i }).click();

    // Verify URL changed
    await expect(page).toHaveURL(/\/analytics/);

    // Wait for lazy-loaded content
    await expect(page.locator('main[role="main"]')).toBeVisible();
  });

  test('should navigate to Deals page', async ({ page }) => {
    await page.goto('/');

    // Click Deals link
    await page.getByRole('link', { name: /deals/i }).click();

    // Verify URL changed
    await expect(page).toHaveURL(/\/deals/);

    // Wait for content
    await expect(page.locator('main[role="main"]')).toBeVisible();
  });

  test('should navigate back to Dashboard from other pages', async ({ page }) => {
    // Start on Investments page
    await page.goto('/investments');
    await expect(page).toHaveURL(/\/investments/);

    // Navigate back to Dashboard
    await page.getByRole('link', { name: /dashboard/i }).click();

    // Verify back on home
    await expect(page).toHaveURL('/');
  });

  test('should handle browser back/forward navigation', async ({ page }) => {
    await page.goto('/');

    // Navigate to Investments
    await page.getByRole('link', { name: /investments/i }).click();
    await expect(page).toHaveURL(/\/investments/);

    // Go back
    await page.goBack();
    await expect(page).toHaveURL('/');

    // Go forward
    await page.goForward();
    await expect(page).toHaveURL(/\/investments/);
  });
});
