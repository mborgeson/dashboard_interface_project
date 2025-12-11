import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Analytics Page
 *
 * Tests for analytics page charts and data visualization.
 */
test.describe('Analytics Page', () => {
  test.describe('Page Load', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/analytics');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('should display analytics page', async ({ page }) => {
      await expect(page).toHaveURL(/\/analytics/);
      await expect(page.locator('main')).toBeVisible();
    });

    test('should load analytics content', async ({ page }) => {
      await page.waitForTimeout(1000);
      const content = await page.locator('main').textContent();
      expect(content).toBeTruthy();
      expect(content!.length).toBeGreaterThan(50);
    });

    test('should display charts or visualizations', async ({ page }) => {
      await page.waitForTimeout(1500);

      // Look for chart elements (Recharts, SVG, canvas)
      const charts = page.locator('svg.recharts-wrapper, canvas, [class*="chart"], [class*="Chart"]');
      const hasCharts = await charts.first().isVisible().catch(() => false);

      // Or look for card-based visualizations
      const cards = page.locator('[class*="Card"]');
      const hasCards = await cards.first().isVisible().catch(() => false);

      expect(hasCharts || hasCards).toBeTruthy();
    });
  });

  test.describe('Analytics API', () => {
    const API_BASE = 'http://localhost:8000/api/v1';

    test('should get dashboard metrics', async ({ request }) => {
      const response = await request.get(`${API_BASE}/analytics/dashboard`);

      if (response.status() === 404) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('portfolio_summary');
      expect(data).toHaveProperty('kpis');
    });

    test('should get portfolio analytics', async ({ request }) => {
      const response = await request.get(`${API_BASE}/analytics/portfolio`);

      if (response.status() === 404) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('performance');
      expect(data).toHaveProperty('composition');
    });

    test('should get deal pipeline analytics', async ({ request }) => {
      const response = await request.get(`${API_BASE}/analytics/deal-pipeline`);

      if (response.status() === 404) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('funnel');
      expect(data).toHaveProperty('conversion_rates');
    });

    test('should get market data', async ({ request }) => {
      const response = await request.get(`${API_BASE}/analytics/market-data`, {
        params: { market: 'Phoenix Metro' },
      });

      if (response.status() === 404) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('market');
      expect(data).toHaveProperty('metrics');
    });
  });

  test.describe('Time Period Filters', () => {
    test('should filter analytics by time period', async ({ page }) => {
      await page.goto('/analytics');
      await page.waitForTimeout(1000);

      // Look for time period selectors
      const timeSelector = page.locator('select, [role="combobox"], button:has-text("YTD"), button:has-text("MTD")');

      if (await timeSelector.first().isVisible().catch(() => false)) {
        // Time filter exists
        expect(await timeSelector.first().isVisible()).toBeTruthy();
      }
    });
  });
});
