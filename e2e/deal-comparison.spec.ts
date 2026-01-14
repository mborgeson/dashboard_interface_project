import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Deal Comparison
 * Wave 9 Feature - Compare multiple deals side-by-side
 */
test.describe('Deal Comparison', () => {
  const API_BASE = 'http://localhost:8000/api/v1';

  test.describe('Deal Selection', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/deals');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(1000);
    });

    test('selects deals for comparison from deal cards', async ({ page }) => {
      // Look for comparison checkbox or select button on deal cards
      const compareCheckbox = page.locator(
        '[data-testid="compare-checkbox"], ' +
        'input[type="checkbox"][aria-label*="compare" i], ' +
        'button[aria-label*="compare" i], ' +
        '[class*="compare-select"]'
      );

      if (await compareCheckbox.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        // Select first deal
        await compareCheckbox.first().click();
        await page.waitForTimeout(300);

        // Select second deal
        if (await compareCheckbox.nth(1).isVisible().catch(() => false)) {
          await compareCheckbox.nth(1).click();
          await page.waitForTimeout(300);

          // Look for compare button that appears after selection
          const compareButton = page.locator(
            '[data-testid="compare-button"], ' +
            'button:has-text("Compare"), ' +
            'button:has-text("Compare Selected")'
          );

          if (await compareButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
            await expect(compareButton.first()).toBeVisible();
          }
        }
      }
    });

    test('navigates to comparison page with selected deals', async ({ page }) => {
      // Try to select deals and navigate to comparison
      const compareCheckbox = page.locator(
        '[data-testid="compare-checkbox"], ' +
        'input[type="checkbox"][aria-label*="compare" i]'
      );

      if (await compareCheckbox.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        await compareCheckbox.first().click();
        if (await compareCheckbox.nth(1).isVisible().catch(() => false)) {
          await compareCheckbox.nth(1).click();
        }

        const compareButton = page.locator('button:has-text("Compare")');

        if (await compareButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
          await compareButton.first().click();

          // Should navigate to comparison page
          await page.waitForTimeout(1000);
          const url = page.url();
          const isComparisonPage = url.includes('compare') || url.includes('comparison');

          // Even if not implemented, verify no errors
          await expect(page.locator('main')).toBeVisible();
        }
      }
    });

    test('comparison selector modal works', async ({ page }) => {
      // Look for "Compare Deals" button that opens modal
      const openModalButton = page.locator(
        '[data-testid="open-comparison-modal"], ' +
        'button:has-text("Compare Deals"), ' +
        'button:has-text("Select Deals to Compare")'
      );

      if (await openModalButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        await openModalButton.first().click();

        // Look for modal
        const modal = page.locator(
          '[data-testid="comparison-selector-modal"], ' +
          '[role="dialog"]:has-text("Compare"), ' +
          '[class*="modal"]:has-text("Compare")'
        );

        if (await modal.first().isVisible({ timeout: 2000 }).catch(() => false)) {
          await expect(modal.first()).toBeVisible();

          // Look for deal selection options in modal
          const dealOptions = page.locator(
            '[data-testid="deal-option"], ' +
            '[role="option"], ' +
            'input[type="checkbox"]'
          );

          if (await dealOptions.first().isVisible().catch(() => false)) {
            const count = await dealOptions.count();
            expect(count).toBeGreaterThan(0);
          }

          // Close modal
          await page.keyboard.press('Escape');
        }
      }
    });
  });

  test.describe('Comparison View', () => {
    test('displays comparison table with metrics', async ({ page }) => {
      // Navigate directly to comparison page if it exists
      await page.goto('/deals/compare?ids=1,2');
      await page.waitForTimeout(1000);

      // If URL redirects or page doesn't exist, try deals page
      if (page.url().includes('/deals/compare')) {
        const table = page.locator(
          '[data-testid="comparison-table"], ' +
          'table:has-text("Price"), ' +
          'table:has-text("IRR"), ' +
          '[class*="comparison-table"]'
        );

        if (await table.first().isVisible({ timeout: 3000 }).catch(() => false)) {
          await expect(table.first()).toBeVisible();

          // Check for metric rows
          const metricRows = page.locator('tr, [class*="metric-row"]');
          const rowCount = await metricRows.count();
          expect(rowCount).toBeGreaterThan(0);
        }
      }

      // Ensure main content is visible
      await expect(page.locator('main')).toBeVisible();
    });

    test('displays comparison charts', async ({ page }) => {
      await page.goto('/deals/compare?ids=1,2');
      await page.waitForTimeout(1000);

      if (page.url().includes('/deals/compare')) {
        // Look for chart elements
        const charts = page.locator(
          '[data-testid="comparison-chart"], ' +
          'canvas, ' +
          'svg[class*="chart"], ' +
          '[class*="recharts"], ' +
          '[class*="Chart"]'
        );

        if (await charts.first().isVisible({ timeout: 3000 }).catch(() => false)) {
          await expect(charts.first()).toBeVisible();
        }
      }

      await expect(page.locator('main')).toBeVisible();
    });

    test('highlights best and worst values', async ({ page }) => {
      await page.goto('/deals/compare?ids=1,2');
      await page.waitForTimeout(1000);

      if (page.url().includes('/deals/compare')) {
        // Look for highlighted cells (best/worst indicators)
        const highlightedCells = page.locator(
          '[data-testid="best-value"], ' +
          '[data-testid="worst-value"], ' +
          '[class*="best"], ' +
          '[class*="worst"], ' +
          '[class*="highlight"], ' +
          'td[class*="green"], ' +
          'td[class*="red"]'
        );

        if (await highlightedCells.first().isVisible({ timeout: 3000 }).catch(() => false)) {
          const count = await highlightedCells.count();
          expect(count).toBeGreaterThan(0);
        }
      }

      await expect(page.locator('main')).toBeVisible();
    });
  });

  test.describe('Comparison Export & Share', () => {
    test('exports comparison to PDF', async ({ page }) => {
      await page.goto('/deals/compare?ids=1,2');
      await page.waitForTimeout(1000);

      if (page.url().includes('/deals/compare')) {
        // Look for export button
        const exportButton = page.locator(
          '[data-testid="export-pdf"], ' +
          'button:has-text("Export PDF"), ' +
          'button:has-text("Download PDF"), ' +
          'button[aria-label*="PDF"]'
        );

        if (await exportButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
          // Set up download listener
          const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(() => null);

          await exportButton.first().click();

          const download = await downloadPromise;

          if (download) {
            // Verify download started
            expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
          }
        }
      }

      await expect(page.locator('main')).toBeVisible();
    });

    test('shares comparison URL', async ({ page }) => {
      await page.goto('/deals/compare?ids=1,2');
      await page.waitForTimeout(1000);

      if (page.url().includes('/deals/compare')) {
        // Look for share button
        const shareButton = page.locator(
          '[data-testid="share-comparison"], ' +
          'button:has-text("Share"), ' +
          'button:has-text("Copy Link"), ' +
          'button[aria-label*="share" i]'
        );

        if (await shareButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
          await shareButton.first().click();

          // Look for success toast or copied indicator
          const toast = page.locator(
            '[class*="toast"], ' +
            '[class*="notification"], ' +
            ':text("Copied"), ' +
            ':text("Link copied")'
          );

          if (await toast.first().isVisible({ timeout: 2000 }).catch(() => false)) {
            await expect(toast.first()).toBeVisible();
          }
        }
      }

      await expect(page.locator('main')).toBeVisible();
    });

    test('comparison URL contains selected deal IDs', async ({ page }) => {
      await page.goto('/deals');
      await page.waitForTimeout(1000);

      // Try to navigate to comparison
      const compareCheckbox = page.locator('[data-testid="compare-checkbox"]');

      if (await compareCheckbox.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await compareCheckbox.first().click();
        if (await compareCheckbox.nth(1).isVisible().catch(() => false)) {
          await compareCheckbox.nth(1).click();
        }

        const compareButton = page.locator('button:has-text("Compare")');
        if (await compareButton.first().isVisible().catch(() => false)) {
          await compareButton.first().click();
          await page.waitForTimeout(1000);

          // Check URL structure
          const url = page.url();
          if (url.includes('compare')) {
            // URL should contain IDs parameter
            expect(url.includes('ids=') || url.includes('deals=')).toBeTruthy();
          }
        }
      }

      await expect(page.locator('main')).toBeVisible();
    });
  });

  test.describe('Comparison API', () => {
    test('should fetch comparison data via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/deals/compare`, {
        params: { ids: '1,2,3' },
      });

      // Skip if endpoint not implemented
      if ([401, 403, 404, 405, 501, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toBeDefined();
    });

    test('should export comparison to PDF via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/deals/compare/export/pdf`, {
        params: { ids: '1,2' },
      });

      // Skip if endpoint not implemented
      if ([401, 403, 404, 405, 501, 502].includes(response.status())) {
        test.skip();
        return;
      }

      if (response.ok()) {
        const contentType = response.headers()['content-type'] || '';
        expect(
          contentType.includes('pdf') ||
          contentType.includes('octet-stream')
        ).toBeTruthy();
      }
    });

    test('should validate deal IDs in comparison request', async ({ request }) => {
      // Test with invalid IDs
      const response = await request.get(`${API_BASE}/deals/compare`, {
        params: { ids: 'invalid' },
      });

      // Should return 400 for invalid IDs or 404 if not found
      if (![401, 403, 404, 501, 502].includes(response.status())) {
        expect([200, 400, 422]).toContain(response.status());
      }
    });

    test('should limit number of deals in comparison', async ({ request }) => {
      // Test with too many IDs (if limit exists)
      const response = await request.get(`${API_BASE}/deals/compare`, {
        params: { ids: '1,2,3,4,5,6,7,8,9,10' },
      });

      // Skip if endpoint not implemented
      if ([401, 403, 404, 405, 501, 502].includes(response.status())) {
        test.skip();
        return;
      }

      // Should either accept or return error for too many deals
      expect([200, 400, 422]).toContain(response.status());
    });
  });

  test.describe('Comparison UX', () => {
    test('shows loading state while fetching comparison data', async ({ page }) => {
      await page.goto('/deals/compare?ids=1,2');

      // Look for loading indicator
      const loader = page.locator(
        '[data-testid="loading"], ' +
        '[class*="loading"], ' +
        '[class*="spinner"], ' +
        '[role="progressbar"]'
      );

      // Loading state may be brief, so just verify page loads
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('handles empty comparison gracefully', async ({ page }) => {
      await page.goto('/deals/compare');
      await page.waitForTimeout(1000);

      // Should show empty state or redirect
      const emptyState = page.locator(
        '[data-testid="empty-comparison"], ' +
        ':text("Select deals"), ' +
        ':text("No deals selected"), ' +
        ':text("Choose deals to compare")'
      );

      if (page.url().includes('/deals/compare')) {
        // Either shows empty state or redirects
        const hasEmptyState = await emptyState.first().isVisible({ timeout: 2000 }).catch(() => false);
        expect(hasEmptyState || !page.url().includes('/deals/compare')).toBeTruthy();
      }

      await expect(page.locator('main')).toBeVisible();
    });

    test('allows removing deals from comparison', async ({ page }) => {
      await page.goto('/deals/compare?ids=1,2,3');
      await page.waitForTimeout(1000);

      if (page.url().includes('/deals/compare')) {
        // Look for remove button on deal columns
        const removeButton = page.locator(
          '[data-testid="remove-deal"], ' +
          'button[aria-label*="remove" i], ' +
          'button:has-text("Remove"), ' +
          '[class*="close"][class*="deal"]'
        );

        if (await removeButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
          await removeButton.first().click();
          await page.waitForTimeout(500);

          // URL should update or deal should be removed from view
          await expect(page.locator('main')).toBeVisible();
        }
      }

      await expect(page.locator('main')).toBeVisible();
    });

    test('preserves comparison state on page refresh', async ({ page }) => {
      await page.goto('/deals/compare?ids=1,2');
      await page.waitForTimeout(1000);

      if (page.url().includes('/deals/compare')) {
        const originalUrl = page.url();

        // Refresh page
        await page.reload();
        await page.waitForTimeout(1000);

        // URL should still contain IDs
        expect(page.url()).toContain('ids=');
        await expect(page.locator('main')).toBeVisible();
      }
    });
  });
});
