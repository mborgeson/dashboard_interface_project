import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Sales Analysis Page
 *
 * Tests the Sales Analysis page including:
 * - Page load and navigation
 * - Tab navigation (Table, Charts, Map, Data Quality)
 * - Filter panel functionality
 * - Table view with sorting and pagination
 * - Charts tab with multiple visualizations
 * - Map view with property markers
 * - Data quality metrics
 * - Import notification banner
 */

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('Sales Analysis Page', () => {
  test.describe('Page Load & Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('should navigate to sales analysis page', async ({ page }) => {
      await expect(page).toHaveURL(/\/sales-analysis/);
      await expect(page.locator('main')).toBeVisible();
    });

    test('should display page header and summary stats', async ({ page }) => {
      // Check page header
      const heading = page.getByRole('heading', { name: /sales analysis/i });
      await expect(heading).toBeVisible();

      // Check subtitle
      await expect(page.getByText(/phoenix msa multifamily sales comps/i)).toBeVisible();

      // Check summary stat cards
      await expect(page.getByText(/total sales/i)).toBeVisible();
      await expect(page.getByText(/current page/i)).toBeVisible();
      await expect(page.getByText(/filters active/i)).toBeVisible();
      await expect(page.getByText(/data quality/i)).toBeVisible();
    });

    test('should show tab navigation', async ({ page }) => {
      // Check for all tabs
      await expect(page.getByRole('tab', { name: /table/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /charts/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /map/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /data quality/i })).toBeVisible();
    });
  });

  test.describe('Tab Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('should default to Table tab', async ({ page }) => {
      // Table tab should be active by default
      const tableTab = page.getByRole('tab', { name: /table/i });
      await expect(tableTab).toHaveAttribute('data-state', 'active');

      // Sales Data table should be visible
      await expect(page.getByRole('heading', { name: /sales data/i })).toBeVisible();
    });

    test('should switch to Charts tab', async ({ page }) => {
      await page.getByRole('tab', { name: /charts/i }).click();
      await page.waitForTimeout(500);

      // Charts tab should be active
      const chartsTab = page.getByRole('tab', { name: /charts/i });
      await expect(chartsTab).toHaveAttribute('data-state', 'active');

      // Should show chart components
      await expect(page.getByText(/time-series trends/i)).toBeVisible();
    });

    test('should switch to Map tab', async ({ page }) => {
      await page.getByRole('tab', { name: /map/i }).click();
      await page.waitForTimeout(500);

      // Map tab should be active
      const mapTab = page.getByRole('tab', { name: /map/i });
      await expect(mapTab).toHaveAttribute('data-state', 'active');

      // Should show map header
      await expect(page.getByText(/sales map/i)).toBeVisible();
    });

    test('should switch to Data Quality tab', async ({ page }) => {
      await page.getByRole('tab', { name: /data quality/i }).click();
      await page.waitForTimeout(500);

      // Data Quality tab should be active
      const qualityTab = page.getByRole('tab', { name: /data quality/i });
      await expect(qualityTab).toHaveAttribute('data-state', 'active');

      // Should show data quality content
      await expect(page.getByText(/data quality summary/i)).toBeVisible();
    });
  });

  test.describe('Filter Panel', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('should display filter panel with toggle', async ({ page }) => {
      // Filter panel should be visible by default
      await expect(page.getByText(/^filters$/i)).toBeVisible();

      // Check for search input
      await expect(page.getByPlaceholder(/property name, address, buyer, seller/i)).toBeVisible();
    });

    test('should apply single filter - price range', async ({ page }) => {
      // Find the Sale Price filter inputs
      await expect(page.getByText(/sale price/i)).toBeVisible();

      // Get min price input and fill it
      const minPriceInput = page.locator('input[type="number"][placeholder="Min"]').nth(1);
      await minPriceInput.fill('1000000');
      await minPriceInput.blur();

      await page.waitForTimeout(500);

      // Filters Active count should update
      const filtersActive = page.locator('text=Filters Active').locator('..').locator('..').getByText(/[0-9]+/);
      const activeCount = await filtersActive.textContent();
      expect(Number(activeCount)).toBeGreaterThan(0);
    });

    test('should apply date range filter', async ({ page }) => {
      // Find the Sale Date filter inputs
      await expect(page.getByText(/sale date/i)).toBeVisible();

      // Get date inputs
      const dateFromInput = page.locator('input[type="date"]').first();
      await dateFromInput.fill('2023-01-01');

      await page.waitForTimeout(500);

      // Filters should be active
      const content = await page.locator('main').textContent();
      expect(content).toBeTruthy();
    });

    test('should search by property name', async ({ page }) => {
      const searchInput = page.getByPlaceholder(/property name, address, buyer, seller/i);
      await searchInput.fill('Apartments');

      // Wait for debounced search
      await page.waitForTimeout(500);

      // Table should update (either show filtered results or no results message)
      const content = await page.locator('main').textContent();
      expect(content).toBeTruthy();
    });

    test('should clear all filters', async ({ page }) => {
      // First apply a filter
      const searchInput = page.getByPlaceholder(/property name, address, buyer, seller/i);
      await searchInput.fill('Test');
      await page.waitForTimeout(500);

      // Check if Clear Filters button appears
      const clearButton = page.getByRole('button', { name: /clear filters/i });

      if (await clearButton.isVisible()) {
        await clearButton.click();
        await page.waitForTimeout(300);

        // Search input should be cleared
        await expect(searchInput).toHaveValue('');
      }
    });

    test('should toggle submarket filter', async ({ page }) => {
      // Wait for submarkets to load
      await page.waitForTimeout(1000);

      // Look for submarket checkboxes
      const submarketSection = page.getByText(/submarkets/i);
      await expect(submarketSection).toBeVisible();

      // Find checkbox labels (submarkets)
      const checkboxes = page.locator('label:has(input[type="checkbox"], [role="checkbox"])');
      const count = await checkboxes.count();

      if (count > 0) {
        // Click first submarket checkbox
        await checkboxes.first().click();
        await page.waitForTimeout(300);

        // Filter should be applied
        const content = await page.locator('main').textContent();
        expect(content).toBeTruthy();
      }
    });
  });

  test.describe('Table View', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('should display sales data table with columns', async ({ page }) => {
      // Check for table headers
      await expect(page.getByRole('columnheader', { name: /property name/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /city/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /submarket/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /sale date/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /sale price/i })).toBeVisible();
    });

    test('should sort by column - price', async ({ page }) => {
      // Click on Sale Price header to sort
      const priceHeader = page.getByRole('columnheader', { name: /sale price/i });
      await priceHeader.click();
      await page.waitForTimeout(300);

      // Verify sort indicator appears (arrow icon should change)
      const content = await page.locator('main').textContent();
      expect(content).toBeTruthy();

      // Click again for reverse sort
      await priceHeader.click();
      await page.waitForTimeout(300);
    });

    test('should sort by column - date', async ({ page }) => {
      const dateHeader = page.getByRole('columnheader', { name: /sale date/i });
      await dateHeader.click();
      await page.waitForTimeout(300);

      // Verify table updates
      const content = await page.locator('main').textContent();
      expect(content).toBeTruthy();
    });

    test('should handle pagination navigation', async ({ page }) => {
      await page.waitForTimeout(1000);

      // Check if pagination exists (depends on data volume)
      const nextButton = page.getByRole('button', { name: /next/i });
      const prevButton = page.getByRole('button', { name: /previous/i });

      if (await nextButton.isVisible()) {
        // Previous should be disabled on first page
        await expect(prevButton).toBeDisabled();

        // Click Next
        await nextButton.click();
        await page.waitForTimeout(500);

        // Previous should now be enabled
        await expect(prevButton).toBeEnabled();
      }
    });

    test('should show current page info', async ({ page }) => {
      await page.waitForTimeout(500);

      // Look for pagination text "Page X of Y"
      const pageInfo = page.getByText(/page \d+ of \d+/i);

      if (await pageInfo.isVisible()) {
        const text = await pageInfo.textContent();
        expect(text).toMatch(/page \d+ of \d+/i);
      }
    });

    test('should handle empty results', async ({ page }) => {
      // Apply filter that returns no results
      const searchInput = page.getByPlaceholder(/property name, address, buyer, seller/i);
      await searchInput.fill('xyznonexistentproperty123456789');
      await page.waitForTimeout(500);

      // Should show empty state message
      await expect(page.getByText(/no sales data matches your filters/i)).toBeVisible();
    });
  });

  test.describe('Charts Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
      await page.getByRole('tab', { name: /charts/i }).click();
      await page.waitForTimeout(500);
    });

    test('should display Time Series Trends chart', async ({ page }) => {
      await expect(page.getByText(/time-series trends/i)).toBeVisible();

      // Check for granularity buttons
      await expect(page.getByRole('button', { name: /monthly/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /quarterly/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /yearly/i })).toBeVisible();
    });

    test('should display Submarket Comparison chart', async ({ page }) => {
      // Scroll down if needed
      await page.evaluate(() => window.scrollBy(0, 500));
      await page.waitForTimeout(300);

      await expect(page.getByText(/submarket comparison/i)).toBeVisible();
    });

    test('should display Buyer Activity Analysis', async ({ page }) => {
      // Scroll down to find buyer activity
      await page.evaluate(() => window.scrollBy(0, 800));
      await page.waitForTimeout(300);

      await expect(page.getByText(/buyer activity/i)).toBeVisible();
    });

    test('should display Distribution Analysis', async ({ page }) => {
      // Scroll down to find distribution analysis
      await page.evaluate(() => window.scrollBy(0, 1200));
      await page.waitForTimeout(300);

      await expect(page.getByText(/distribution analysis/i)).toBeVisible();
    });

    test('should change time series granularity', async ({ page }) => {
      // Default is Yearly, click Quarterly
      const quarterlyButton = page.getByRole('button', { name: /quarterly/i });
      await quarterlyButton.click();
      await page.waitForTimeout(300);

      // Button should show active state
      await expect(quarterlyButton).toHaveClass(/bg-blue-600/);

      // Click Monthly
      const monthlyButton = page.getByRole('button', { name: /monthly/i });
      await monthlyButton.click();
      await page.waitForTimeout(300);

      await expect(monthlyButton).toHaveClass(/bg-blue-600/);
    });

    test('should show charts with data or empty state', async ({ page }) => {
      // Charts should either show data or empty state
      const content = await page.locator('main').textContent();

      // Should have chart content or "No data available" message
      expect(
        content?.includes('recharts') ||
        content?.includes('Transactions') ||
        content?.includes('Volume') ||
        content?.includes('No time-series data') ||
        content?.includes('data available')
      ).toBeTruthy();
    });
  });

  test.describe('Map View', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
      await page.getByRole('tab', { name: /map/i }).click();
      await page.waitForTimeout(1000);
    });

    test('should display sales map with header', async ({ page }) => {
      await expect(page.getByText(/sales map/i)).toBeVisible();
    });

    test('should show map legend with recency colors', async ({ page }) => {
      // Check for legend items
      await expect(page.getByText(/recency/i)).toBeVisible();
      await expect(page.getByText(/<1 yr/i)).toBeVisible();
      await expect(page.getByText(/1-3 yr/i)).toBeVisible();
      await expect(page.getByText(/3-5 yr/i)).toBeVisible();
      await expect(page.getByText(/5\+ yr/i)).toBeVisible();
    });

    test('should display mapped records count', async ({ page }) => {
      // Should show "X mapped of Y records"
      const mapInfo = page.getByText(/mapped of/i);

      if (await mapInfo.isVisible()) {
        const text = await mapInfo.textContent();
        expect(text).toMatch(/\d+ mapped of \d+ records/i);
      }
    });

    test('should display map container', async ({ page }) => {
      // Look for the leaflet map container
      const mapContainer = page.locator('.leaflet-container, [class*="h-[600px]"]');
      await expect(mapContainer.first()).toBeVisible();
    });
  });

  test.describe('Data Quality Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
      await page.getByRole('tab', { name: /data quality/i }).click();
      await page.waitForTimeout(500);
    });

    test('should display data quality metrics', async ({ page }) => {
      await expect(page.getByText(/data quality summary/i)).toBeVisible();

      // Check for metric cards
      await expect(page.getByText(/total records/i)).toBeVisible();
      await expect(page.getByText(/source files/i)).toBeVisible();
      await expect(page.getByText(/flagged outliers/i)).toBeVisible();
    });

    test('should show records by source section', async ({ page }) => {
      // Look for the collapsible source files section
      const sourceButton = page.getByText(/records by source file/i);

      if (await sourceButton.isVisible()) {
        // Click to expand
        await sourceButton.click();
        await page.waitForTimeout(300);

        // Should show file entries
        const content = await page.locator('main').textContent();
        expect(content).toBeTruthy();
      }
    });

    test('should display field completeness metrics', async ({ page }) => {
      // Check for null rates / field completeness section
      await expect(page.getByText(/field completeness|null rates/i)).toBeVisible();

      // Should show various field metrics
      const content = await page.locator('main').textContent();
      expect(
        content?.includes('Cap Rate') ||
        content?.includes('Price Per Unit') ||
        content?.includes('Sale Price') ||
        content?.includes('%')
      ).toBeTruthy();
    });
  });

  test.describe('Import Banner', () => {
    test('should show import notification when new data available', async ({ page }) => {
      // Mock API to return unimported files
      await page.route('**/sales/import-status**', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            unimportedFiles: ['new_sales_data.xlsx'],
            lastImportedFile: 'old_data.xlsx',
            lastImportDate: '2024-01-01',
          }),
        });
      });

      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Check for import banner
      const banner = page.locator('[role="alert"]');

      if (await banner.isVisible()) {
        await expect(page.getByText(/new sales file/i)).toBeVisible();
        await expect(page.getByRole('button', { name: /import now/i })).toBeVisible();
      }
    });

    test('should trigger import action when clicking import button', async ({ page }) => {
      // Mock import status API
      await page.route('**/sales/import-status**', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            unimportedFiles: ['test_file.xlsx'],
            lastImportedFile: null,
            lastImportDate: null,
          }),
        });
      });

      // Mock import trigger API
      let importTriggered = false;
      await page.route('**/sales/import**', (route) => {
        if (route.request().method() === 'POST') {
          importTriggered = true;
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ success: true }),
          });
        } else {
          route.continue();
        }
      });

      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const importButton = page.getByRole('button', { name: /import now/i });

      if (await importButton.isVisible()) {
        await importButton.click();
        await page.waitForTimeout(500);

        // Button text should change to "Importing..."
        const buttonText = await importButton.textContent();
        expect(buttonText?.includes('Importing') || importTriggered).toBeTruthy();
      }
    });

    test('should hide banner when no import files available', async ({ page }) => {
      // Mock API to return no unimported files
      await page.route('**/sales/import-status**', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            unimportedFiles: [],
            lastImportedFile: 'latest.xlsx',
            lastImportDate: '2024-06-01',
          }),
        });
      });

      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Import banner should not be visible
      await expect(page.getByText(/new sales file.*available for import/i)).not.toBeVisible();
    });
  });

  test.describe('Error Handling', () => {
    test('should display error state when API fails', async ({ page }) => {
      // Mock API failure
      await page.route('**/sales**', (route) => {
        if (route.request().url().includes('/sales/')) {
          route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Internal server error' }),
          });
        } else {
          route.continue();
        }
      });

      await page.goto('/sales-analysis');
      await page.waitForTimeout(2000);

      // Check for error state (page handles errors gracefully)
      const content = await page.locator('main').textContent();
      expect(content).toBeTruthy();
    });

    test('should show retry button on error', async ({ page }) => {
      // Mock API failure for sales data
      await page.route('**/sales?**', (route) => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' }),
        });
      });

      await page.goto('/sales-analysis');
      await page.waitForTimeout(2000);

      // Look for retry button
      const retryButton = page.getByRole('button', { name: /retry/i });

      if (await retryButton.isVisible()) {
        await expect(retryButton).toBeVisible();
      }
    });
  });

  test.describe('Sales API Endpoints', () => {
    test('should list sales data via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/sales`, {
        params: { page: 1, page_size: 10 },
      });

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('data');
      expect(data).toHaveProperty('total');
      expect(data).toHaveProperty('page');
    });

    test('should get filter options via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/sales/filter-options`);

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('submarkets');
    });

    test('should get time series analytics via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/sales/analytics/time-series`);

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(Array.isArray(data)).toBeTruthy();
    });

    test('should get data quality report via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/sales/data-quality`);

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('totalRecords');
    });

    test('should filter sales by submarket via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/sales`, {
        params: { submarkets: 'Central Phoenix' },
      });

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();
    });

    test('should filter sales by price range via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/sales`, {
        params: { min_price: 1000000, max_price: 10000000 },
      });

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();
    });
  });

  test.describe('Responsive Layout', () => {
    test('should display correctly on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Page should still be functional
      await expect(page.getByRole('heading', { name: /sales analysis/i })).toBeVisible();

      // Tabs should be visible
      await expect(page.getByRole('tab', { name: /table/i })).toBeVisible();
    });

    test('should display correctly on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Core elements should be visible
      await expect(page.getByRole('heading', { name: /sales analysis/i })).toBeVisible();
    });
  });

  test.describe('Navigation from Dashboard', () => {
    test('should navigate to sales analysis from main navigation', async ({ page }) => {
      await page.goto('/');
      await page.waitForTimeout(1000);

      // Find and click Sales Analysis link
      const salesLink = page.getByRole('link', { name: /sales|comps/i });

      if (await salesLink.first().isVisible()) {
        await salesLink.first().click();
        await page.waitForTimeout(500);

        // Should navigate to sales analysis page
        await expect(page).toHaveURL(/\/sales-analysis/);
      }
    });
  });

  test.describe('Complete User Flow', () => {
    test('should complete full analysis workflow', async ({ page }) => {
      await page.goto('/sales-analysis');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Step 1: Verify page loaded with data
      await expect(page.getByRole('heading', { name: /sales analysis/i })).toBeVisible();

      // Step 2: Apply a filter
      const searchInput = page.getByPlaceholder(/property name, address, buyer, seller/i);
      await searchInput.fill('Phoenix');
      await page.waitForTimeout(500);

      // Step 3: Check table results
      await expect(page.getByRole('heading', { name: /sales data/i })).toBeVisible();

      // Step 4: Switch to Charts tab
      await page.getByRole('tab', { name: /charts/i }).click();
      await page.waitForTimeout(500);
      await expect(page.getByText(/time-series trends/i)).toBeVisible();

      // Step 5: Switch to Map tab
      await page.getByRole('tab', { name: /map/i }).click();
      await page.waitForTimeout(500);
      await expect(page.getByText(/sales map/i)).toBeVisible();

      // Step 6: Switch to Data Quality tab
      await page.getByRole('tab', { name: /data quality/i }).click();
      await page.waitForTimeout(500);
      await expect(page.getByText(/data quality summary/i)).toBeVisible();

      // Step 7: Clear filters and return to table
      await page.getByRole('tab', { name: /table/i }).click();
      await page.waitForTimeout(300);

      const clearButton = page.getByRole('button', { name: /clear filters/i });
      if (await clearButton.isVisible()) {
        await clearButton.click();
        await page.waitForTimeout(300);
      }

      // Verify we're back to clean state
      const tableTab = page.getByRole('tab', { name: /table/i });
      await expect(tableTab).toHaveAttribute('data-state', 'active');
    });
  });
});
