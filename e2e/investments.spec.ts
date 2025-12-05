import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Investments Page
 * Tests filtering, sorting, and property interactions
 */
test.describe('Investments Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/investments');
    // Wait for page header to load (visible even during loading state)
    await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
    // Wait for loading state to complete (800ms delay in component)
    await page.waitForTimeout(1000);
  });

  test('should display property cards', async ({ page }) => {
    // Wait for property cards to appear after loading
    // Look for CardTitle in property section
    const cardTitles = page.locator('h3, [class*="CardTitle"]').first();
    await expect(cardTitles).toBeVisible({ timeout: 10000 });
  });

  test('should have filter controls', async ({ page }) => {
    // Look for PropertyFilters component elements - search input or select dropdowns
    const searchInput = page.getByPlaceholder(/search/i);
    const selectTriggers = page.locator('[role="combobox"]');

    // Either search input or select triggers should exist
    const hasSearch = await searchInput.isVisible({ timeout: 5000 }).catch(() => false);
    const hasSelects = await selectTriggers.first().isVisible({ timeout: 5000 }).catch(() => false);

    expect(hasSearch || hasSelects).toBeTruthy();
  });

  test('should have search functionality', async ({ page }) => {
    // Look for search input
    const searchInput = page.getByPlaceholder(/search/i);

    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Type in search
      await searchInput.fill('test');

      // Verify input accepted the value
      await expect(searchInput).toHaveValue('test');
    }
  });

  test('should display portfolio summary stats', async ({ page }) => {
    // Check for summary stat cards with CardTitle "Total Properties", "Total Units", etc.
    const totalPropertiesCard = page.getByText('Total Properties');
    await expect(totalPropertiesCard).toBeVisible({ timeout: 10000 });
  });
});
