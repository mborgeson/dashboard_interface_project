import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Dashboard Main Page
 * Tests the core dashboard functionality and initial load
 */
test.describe('Dashboard Main Page', () => {
  test('should load dashboard with all key components', async ({ page }) => {
    await page.goto('/');

    // Wait for main content to load
    await expect(page.locator('main[role="main"]')).toBeVisible();

    // Check for key dashboard sections - page title is "Portfolio Dashboard"
    await expect(page.getByRole('heading', { name: /Portfolio Dashboard/i })).toBeVisible();

    // Check stat cards are present (Card components with shadow-card class)
    const statCards = page.locator('[class*="shadow-card"]');
    await expect(statCards.first()).toBeVisible();
  });

  test('should display sidebar navigation', async ({ page }) => {
    await page.goto('/');

    // Check sidebar is present with navigation items
    const sidebar = page.locator('nav, aside').first();
    await expect(sidebar).toBeVisible();

    // Check for key navigation links
    await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /investments/i })).toBeVisible();
  });

  test('should have accessible skip link', async ({ page }) => {
    await page.goto('/');

    // Tab to skip link and verify it exists
    const skipLink = page.getByRole('link', { name: /skip to main content/i });
    await expect(skipLink).toBeAttached();
  });
});
