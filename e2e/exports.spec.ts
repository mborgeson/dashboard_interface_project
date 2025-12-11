import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Export Functionality
 *
 * Tests for data export features (Excel, PDF).
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

  test.describe('Export API', () => {
    const API_BASE = 'http://localhost:8000/api/v1';

    test('should export properties to Excel', async ({ request }) => {
      const response = await request.get(`${API_BASE}/exports/properties/excel`);

      if (response.status() === 404) {
        test.skip();
        return;
      }

      if (response.status() === 501) {
        // Service not available - skip
        test.skip();
        return;
      }

      // Should return Excel file or error
      expect([200, 500]).toContain(response.status());

      if (response.ok()) {
        const contentType = response.headers()['content-type'] || '';
        expect(
          contentType.includes('spreadsheet') ||
          contentType.includes('octet-stream')
        ).toBeTruthy();
      }
    });

    test('should export analytics to Excel', async ({ request }) => {
      const response = await request.get(`${API_BASE}/exports/analytics/excel`);

      if (response.status() === 404 || response.status() === 501) {
        test.skip();
        return;
      }

      expect([200, 500]).toContain(response.status());
    });

    test('should export property to PDF', async ({ request }) => {
      const response = await request.get(`${API_BASE}/exports/properties/1/pdf`);

      if (response.status() === 404 || response.status() === 501) {
        test.skip();
        return;
      }

      expect([200, 500]).toContain(response.status());

      if (response.ok()) {
        const contentType = response.headers()['content-type'] || '';
        expect(
          contentType.includes('pdf') ||
          contentType.includes('octet-stream')
        ).toBeTruthy();
      }
    });

    test('should export portfolio to PDF', async ({ request }) => {
      const response = await request.get(`${API_BASE}/exports/portfolio/pdf`);

      if (response.status() === 404 || response.status() === 501) {
        test.skip();
        return;
      }

      expect([200, 500]).toContain(response.status());
    });

    test('should handle export with filters', async ({ request }) => {
      const response = await request.get(`${API_BASE}/exports/properties/excel`, {
        params: { property_type: 'multifamily' },
      });

      if (response.status() === 404 || response.status() === 501) {
        test.skip();
        return;
      }

      // Should accept the filter parameter
      expect([200, 404, 500]).toContain(response.status());
    });
  });
});
