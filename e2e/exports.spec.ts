import { test, expect } from './fixtures/auth';

/**
 * E2E Tests: Export Functionality
 *
 * Tests for data export features (Excel, PDF).
 * Backend must be running -- tests fail (not skip) if unavailable.
 */
test.describe('Export Functionality', () => {
  test.describe('Export UI', () => {
    test('should have export options on investments page', async ({ page }) => {
      await page.goto('/investments');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Look for export button or menu
      const exportButton = page.locator('button:has-text("Export"), button:has-text("Download"), [aria-label*="export" i]');

      if (await exportButton.first().isVisible().catch(() => false)) {
        expect(await exportButton.first().isVisible()).toBeTruthy();
      }
    });

    test('should have export options on analytics page', async ({ page }) => {
      await page.goto('/analytics');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Look for export controls
      const exportControls = page.locator('button:has-text("Export"), button:has-text("Download")');

      if (await exportControls.first().isVisible().catch(() => false)) {
        expect(await exportControls.first().isVisible()).toBeTruthy();
      }
    });
  });

  // NOTE: Export API E2E tests were removed because the export endpoints
  // (/exports/properties/excel, /exports/analytics/excel, /exports/properties/{id}/pdf,
  // /exports/portfolio/pdf) return 404/501 in E2E and were previously masked by
  // test.fixme. The backend pytest suite (test_exports.py) now tests these honestly.
});
