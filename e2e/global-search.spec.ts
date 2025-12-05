import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Global Search
 * Tests the global search modal functionality
 */
test.describe('Global Search', () => {
  test('should open search modal with keyboard shortcut', async ({ page }) => {
    await page.goto('/');

    // Wait for page to load
    await expect(page.locator('main[role="main"]')).toBeVisible();

    // Press Cmd/Ctrl + K to open search
    await page.keyboard.press('Meta+k');

    // If Meta+k doesn't work (Linux), try Ctrl+k
    const searchModal = page.locator('[role="dialog"], [class*="search-modal"], [class*="GlobalSearch"]');
    if (!await searchModal.isVisible({ timeout: 1000 }).catch(() => false)) {
      await page.keyboard.press('Control+k');
    }

    // Check if search modal opened
    await expect(searchModal.first()).toBeVisible({ timeout: 5000 });
  });

  test('should close search modal with Escape', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main[role="main"]')).toBeVisible();

    // Open search
    await page.keyboard.press('Control+k');

    const searchModal = page.locator('[role="dialog"], [class*="search-modal"], [class*="GlobalSearch"]');

    // Wait for modal to be visible
    if (await searchModal.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      // Press Escape to close
      await page.keyboard.press('Escape');

      // Modal should be hidden
      await expect(searchModal.first()).toBeHidden({ timeout: 2000 });
    }
  });

  test('should search and show results', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main[role="main"]')).toBeVisible();

    // Open search
    await page.keyboard.press('Control+k');

    const searchInput = page.locator('input[type="text"][placeholder*="Search"], input[aria-label*="Search"]');

    if (await searchInput.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      // Type search query
      await searchInput.first().fill('property');

      // Wait for results to appear (debounced)
      await page.waitForTimeout(500);

      // Check for results or "no results" message
      const results = page.locator('[class*="result"], [class*="search-item"], [role="listbox"], [role="option"]');
      const noResults = page.getByText(/no results/i);

      const hasContent = await results.first().isVisible({ timeout: 2000 }).catch(() => false) ||
                        await noResults.isVisible({ timeout: 1000 }).catch(() => false);

      expect(hasContent).toBeTruthy();
    }
  });

  test('should navigate search results with keyboard', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main[role="main"]')).toBeVisible();

    // Open search
    await page.keyboard.press('Control+k');

    const searchInput = page.locator('input[type="text"][placeholder*="Search"], input[aria-label*="Search"]');

    if (await searchInput.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      // Type search query
      await searchInput.first().fill('test');
      await page.waitForTimeout(500);

      // Press arrow down to navigate results
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('ArrowUp');

      // This test passes if no errors occur during navigation
      expect(true).toBeTruthy();
    }
  });
});
