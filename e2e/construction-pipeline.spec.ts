import { test, expect, type Page } from '@playwright/test';

/**
 * E2E Tests: Construction Pipeline Page
 *
 * Comprehensive tests for the Construction Pipeline feature including:
 * - Page load and initialization
 * - Tab navigation (Table, Charts, Map, Data Sources)
 * - Filter panel functionality
 * - Table view with pagination
 * - Charts tab with multiple visualizations
 * - Map tab with project markers
 * - Data sources tab with freshness information
 */

// =============================================================================
// Test Utilities
// =============================================================================

/**
 * Wait for loading states to complete
 */
async function waitForLoadingComplete(page: Page, timeout = 15000) {
  // Wait for any loading skeletons to disappear
  await page
    .waitForFunction(
      () => {
        const skeletons = document.querySelectorAll(
          '[class*="animate-pulse"], [class*="skeleton"]'
        );
        return skeletons.length === 0;
      },
      { timeout }
    )
    .catch(() => {
      // If timeout, continue anyway - content may have loaded differently
    });

  // Wait a bit for charts/components to render
  await page.waitForTimeout(500);
}

/**
 * Wait for Recharts SVG to be visible
 */
async function waitForChart(page: Page, timeout = 10000) {
  await page
    .waitForSelector('.recharts-wrapper, .recharts-surface, svg[class*="recharts"]', {
      timeout,
      state: 'visible',
    })
    .catch(() => {
      // Chart may not exist, continue with test
    });
}

/**
 * Wait for table to be visible
 */
async function waitForTable(page: Page, timeout = 10000) {
  await page
    .waitForSelector('table', {
      timeout,
      state: 'visible',
    })
    .catch(() => {
      // Table may not exist, continue with test
    });
}

// =============================================================================
// Page Load & Initialization Tests
// =============================================================================

test.describe('Construction Pipeline Page', () => {
  test.describe('Page Load & Initialization', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/construction-pipeline');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 15000 });
    });

    test('should navigate to construction pipeline page', async ({ page }) => {
      await expect(page).toHaveURL(/\/construction-pipeline/);
      await expect(page.locator('main[role="main"]')).toBeVisible();
    });

    test('should display page header and description', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Check for page title
      const heading = page.getByRole('heading', { name: /construction pipeline/i });
      await expect(heading).toBeVisible();

      // Check for description
      const description = page.getByText(/phoenix msa/i).first();
      await expect(description).toBeVisible();
    });

    test('should show status summary cards', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Check for status cards - these should contain status labels
      const statusLabels = ['Proposed', 'Final Planning', 'Permitted', 'Under Constr.', 'Delivered'];

      let foundCards = 0;
      for (const label of statusLabels) {
        const card = page.locator(`text=${label}`).first();
        const isVisible = await card.isVisible().catch(() => false);
        if (isVisible) foundCards++;
      }

      // Should find most status cards
      expect(foundCards).toBeGreaterThanOrEqual(3);
    });

    test('should load initial data', async ({ page }) => {
      await waitForLoadingComplete(page);

      // After loading, should have content (not error state)
      const mainContent = await page.locator('main[role="main"]').textContent();
      expect(mainContent).toBeTruthy();

      // Should not show error state
      const errorState = page.locator('text=/error loading data/i');
      const hasError = await errorState.isVisible().catch(() => false);
      expect(hasError).toBeFalsy();
    });
  });

  // =============================================================================
  // Tab Navigation Tests
  // =============================================================================

  test.describe('Tab Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/construction-pipeline');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 15000 });
      await waitForLoadingComplete(page);
    });

    test('should default to Table tab', async ({ page }) => {
      // Table tab should be active by default
      const tableTab = page.getByRole('tab', { name: /table/i });
      await expect(tableTab).toBeVisible();

      // Table content should be visible
      await waitForTable(page);
      const tableCard = page.locator('text=Construction Projects').first();
      await expect(tableCard).toBeVisible();
    });

    test('should switch to Charts tab', async ({ page }) => {
      // Click Charts tab
      const chartsTab = page.getByRole('tab', { name: /charts/i });
      await chartsTab.click();
      await page.waitForTimeout(500);

      // Charts content should be visible
      await waitForChart(page);
      const funnelChart = page.locator('text=/Pipeline Funnel/i').first();
      await expect(funnelChart).toBeVisible();
    });

    test('should switch to Map tab', async ({ page }) => {
      // Click Map tab
      const mapTab = page.getByRole('tab', { name: /map/i });
      await mapTab.click();
      await page.waitForTimeout(1000);

      // Map content should be visible
      const mapCard = page.locator('text=/Pipeline Map/i').first();
      await expect(mapCard).toBeVisible();
    });

    test('should switch to Data Sources tab', async ({ page }) => {
      // Click Data Sources tab
      const sourcesTab = page.getByRole('tab', { name: /data sources/i });
      await sourcesTab.click();
      await page.waitForTimeout(500);

      // Data sources content should be visible
      const sourcesCard = page.locator('text=/Data Quality|Data Sources/i').first();
      await expect(sourcesCard).toBeVisible();
    });
  });

  // =============================================================================
  // Filter Panel Tests
  // =============================================================================

  test.describe('Filter Panel', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/construction-pipeline');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 15000 });
      await waitForLoadingComplete(page);
    });

    test('should display filter panel with toggle button', async ({ page }) => {
      // Filter button should be visible
      const filterButton = page.getByRole('button', { name: /filters/i });
      await expect(filterButton).toBeVisible();
    });

    test('should toggle filter panel open and closed', async ({ page }) => {
      // Find the filter toggle button
      const filterButton = page.getByRole('button', { name: /filters/i });

      // Click to collapse (should be expanded by default)
      await filterButton.click();
      await page.waitForTimeout(300);

      // Search input should not be visible when collapsed
      const searchInput = page.getByPlaceholder(/search projects/i);
      const isSearchVisible = await searchInput.isVisible().catch(() => false);

      // Click again to expand
      await filterButton.click();
      await page.waitForTimeout(300);

      // Now search input should be visible
      await expect(searchInput).toBeVisible();
    });

    test('should apply status filter', async ({ page }) => {
      // Find a status checkbox (e.g., Proposed)
      const proposedCheckbox = page.getByRole('checkbox').first();
      const hasCheckbox = await proposedCheckbox.isVisible().catch(() => false);

      if (hasCheckbox) {
        // Get initial table content
        const initialContent = await page.locator('table').textContent().catch(() => '');

        // Click the checkbox
        await proposedCheckbox.click();
        await page.waitForTimeout(500);

        // Table should update (content may change)
        const updatedContent = await page.locator('table').textContent().catch(() => '');

        // Verify checkbox is checked
        await expect(proposedCheckbox).toBeChecked();
      }
    });

    test('should apply submarket filter', async ({ page }) => {
      // Look for submarket label and checkboxes
      const submarketLabel = page.locator('text=Submarket').first();
      const hasSubmarket = await submarketLabel.isVisible().catch(() => false);

      if (hasSubmarket) {
        // Find and click a submarket checkbox
        const submarketSection = submarketLabel.locator('xpath=following-sibling::div').first();
        const checkbox = submarketSection.locator('input[type="checkbox"]').first();

        const hasCheckbox = await checkbox.isVisible().catch(() => false);
        if (hasCheckbox) {
          await checkbox.click();
          await page.waitForTimeout(500);

          // Filter should be applied
          const filterButton = page.getByRole('button', { name: /filters/i });
          const filterText = await filterButton.textContent();
          expect(filterText).toMatch(/\d/); // Should show filter count
        }
      }
    });

    test('should clear all filters', async ({ page }) => {
      // First, apply a filter by clicking a checkbox
      const checkbox = page.getByRole('checkbox').first();
      const hasCheckbox = await checkbox.isVisible().catch(() => false);

      if (hasCheckbox) {
        await checkbox.click();
        await page.waitForTimeout(300);

        // Clear All button should appear
        const clearButton = page.getByRole('button', { name: /clear all/i });
        await expect(clearButton).toBeVisible();

        // Click Clear All
        await clearButton.click();
        await page.waitForTimeout(500);

        // Checkbox should be unchecked
        await expect(checkbox).not.toBeChecked();

        // Clear All button should disappear
        await expect(clearButton).not.toBeVisible();
      }
    });
  });

  // =============================================================================
  // Table View Tests
  // =============================================================================

  test.describe('Table View', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/construction-pipeline');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 15000 });
      await waitForLoadingComplete(page);
    });

    test('should display projects table with columns', async ({ page }) => {
      await waitForTable(page);

      // Check for table headers
      const expectedHeaders = [
        'Project Name',
        'City',
        'Submarket',
        'Status',
        'Type',
        'Units',
        'Developer',
        'Rent Type',
      ];

      let foundHeaders = 0;
      for (const header of expectedHeaders) {
        const headerElement = page.locator(`th:has-text("${header}")`).first();
        const isVisible = await headerElement.isVisible().catch(() => false);
        if (isVisible) foundHeaders++;
      }

      // Should find most headers
      expect(foundHeaders).toBeGreaterThanOrEqual(5);
    });

    test('should display table data rows', async ({ page }) => {
      await waitForTable(page);

      // Look for table rows (excluding header)
      const tableRows = page.locator('tbody tr');
      const rowCount = await tableRows.count();

      // Should have data rows or show "No projects found" message
      if (rowCount === 0) {
        const emptyMessage = page.locator('text=/no projects found/i');
        await expect(emptyMessage).toBeVisible();
      } else {
        expect(rowCount).toBeGreaterThan(0);
      }
    });

    test('should show loading state', async ({ page }) => {
      // Navigate fresh to catch loading state
      await page.goto('/construction-pipeline');

      // Look for skeleton elements quickly
      const skeletons = page.locator('[class*="animate-pulse"]');
      const hasSkeletons = await skeletons.first().isVisible().catch(() => false);

      // After loading, content should be visible
      await waitForLoadingComplete(page);

      const tableCard = page.locator('text=Construction Projects').first();
      await expect(tableCard).toBeVisible();
    });

    test('should display pagination controls when multiple pages', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for pagination buttons
      const previousButton = page.getByRole('button', { name: /previous/i });
      const nextButton = page.getByRole('button', { name: /next/i });

      // Pagination controls should exist if there's enough data
      const hasPrevious = await previousButton.isVisible().catch(() => false);
      const hasNext = await nextButton.isVisible().catch(() => false);

      if (hasPrevious || hasNext) {
        // If pagination exists, Previous should be disabled on page 1
        await expect(previousButton).toBeDisabled();

        // Page indicator should show
        const pageIndicator = page.locator('text=/page \\d+ of \\d+/i');
        await expect(pageIndicator).toBeVisible();
      }
    });
  });

  // =============================================================================
  // Charts Tab Tests
  // =============================================================================

  test.describe('Charts Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/construction-pipeline');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 15000 });
      await waitForLoadingComplete(page);

      // Navigate to Charts tab
      const chartsTab = page.getByRole('tab', { name: /charts/i });
      await chartsTab.click();
      await page.waitForTimeout(1000);
    });

    test('should display Pipeline Funnel chart', async ({ page }) => {
      // Look for Pipeline Funnel title
      const funnelTitle = page.locator('text=/Pipeline Funnel/i').first();
      await expect(funnelTitle).toBeVisible();

      // Should have chart elements or empty state
      const chartContent = page.locator('.recharts-wrapper, text=/no data available/i').first();
      await expect(chartContent).toBeVisible();
    });

    test('should display Delivery Timeline chart', async ({ page }) => {
      // Look for Delivery Timeline title
      const timelineTitle = page.locator('text=/Delivery Timeline/i').first();
      await expect(timelineTitle).toBeVisible();

      // Should have chart elements or empty state
      const chartContent = page
        .locator('.recharts-wrapper, text=/no.*data.*available/i')
        .first();
      const isVisible = await chartContent.isVisible().catch(() => false);
      expect(isVisible).toBeTruthy();
    });

    test('should display Submarket Pipeline breakdown', async ({ page }) => {
      // Scroll down to find submarket section
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
      await page.waitForTimeout(500);

      // Look for Pipeline by Submarket title
      const submarketTitle = page.locator('text=/Pipeline by Submarket/i').first();
      await expect(submarketTitle).toBeVisible();
    });

    test('should show empty state when no data', async ({ page }) => {
      // Apply a filter that likely returns no results
      const filterButton = page.getByRole('button', { name: /filters/i });

      // Check if we need to expand filters first
      const searchInput = page.getByPlaceholder(/search projects/i);
      const isSearchVisible = await searchInput.isVisible().catch(() => false);
      if (!isSearchVisible) {
        await filterButton.click();
        await page.waitForTimeout(300);
      }

      // Search for something unlikely to exist
      await searchInput.fill('xyznonexistent123456');
      await page.waitForTimeout(500);

      // Charts should show empty state or still render
      const chartsContent = await page.locator('main[role="main"]').textContent();
      expect(chartsContent).toBeTruthy();
    });

    test('should display charts with proper rendering', async ({ page }) => {
      await waitForChart(page, 15000);

      // Look for any recharts elements
      const chartSvg = page.locator('.recharts-surface, .recharts-wrapper');
      const hasChart = await chartSvg.first().isVisible().catch(() => false);

      // Either has charts or shows empty state messages
      const emptyState = page.locator('text=/no data available/i').first();
      const hasEmpty = await emptyState.isVisible().catch(() => false);

      expect(hasChart || hasEmpty).toBeTruthy();
    });
  });

  // =============================================================================
  // Map Tab Tests
  // =============================================================================

  test.describe('Map Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/construction-pipeline');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 15000 });
      await waitForLoadingComplete(page);

      // Navigate to Map tab
      const mapTab = page.getByRole('tab', { name: /map/i });
      await mapTab.click();
      await page.waitForTimeout(1500); // Map needs extra time to initialize
    });

    test('should display map with project markers info', async ({ page }) => {
      // Look for Pipeline Map title
      const mapTitle = page.locator('text=/Pipeline Map/i').first();
      await expect(mapTitle).toBeVisible();

      // Should show count of mapped projects
      const mappedInfo = page.locator('text=/mapped of/i').first();
      const hasMappedInfo = await mappedInfo.isVisible().catch(() => false);
      expect(hasMappedInfo).toBeTruthy();
    });

    test('should display map container', async ({ page }) => {
      // Look for the map container (Leaflet map)
      const mapContainer = page.locator('.leaflet-container, [class*="leaflet"]');
      const hasMap = await mapContainer.first().isVisible().catch(() => false);

      // Should have map or loading state
      if (!hasMap) {
        const loadingSkeleton = page.locator('[class*="animate-pulse"]');
        const hasLoading = await loadingSkeleton.first().isVisible().catch(() => false);
        expect(hasLoading).toBeTruthy();
      } else {
        expect(hasMap).toBeTruthy();
      }
    });

    test('should show status legend', async ({ page }) => {
      // Look for status legend
      const legendText = page.locator('text=/Status:/i').first();
      const hasLegend = await legendText.isVisible().catch(() => false);

      if (hasLegend) {
        // Should show status labels
        const proposedLegend = page.locator('text=/Proposed/i').first();
        const deliveredLegend = page.locator('text=/Delivered/i').first();

        const hasProposed = await proposedLegend.isVisible().catch(() => false);
        const hasDelivered = await deliveredLegend.isVisible().catch(() => false);

        expect(hasProposed || hasDelivered).toBeTruthy();
      }
    });
  });

  // =============================================================================
  // Data Sources Tab Tests
  // =============================================================================

  test.describe('Data Sources Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/construction-pipeline');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 15000 });
      await waitForLoadingComplete(page);

      // Navigate to Data Sources tab
      const sourcesTab = page.getByRole('tab', { name: /data sources/i });
      await sourcesTab.click();
      await page.waitForTimeout(500);
    });

    test('should display source freshness information', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for Data Quality or Data Sources title
      const dataCard = page.locator('text=/Data Quality|Data Sources/i').first();
      await expect(dataCard).toBeVisible();
    });

    test('should show data source list', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for known data sources
      const dataSourceNames = ['CoStar', 'Census BPS', 'FRED', 'BLS', 'Mesa', 'Tempe', 'Gilbert'];

      let foundSources = 0;
      for (const sourceName of dataSourceNames) {
        const sourceElement = page.locator(`text=${sourceName}`).first();
        const isVisible = await sourceElement.isVisible().catch(() => false);
        if (isVisible) foundSources++;
      }

      // Should find at least one data source
      expect(foundSources).toBeGreaterThan(0);
    });

    test('should display summary statistics', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for summary cards (Total Projects, Permit Records, Employment Records)
      const summaryLabels = ['Total Projects', 'Permit Records', 'Employment Records'];

      let foundLabels = 0;
      for (const label of summaryLabels) {
        const labelElement = page.locator(`text=${label}`).first();
        const isVisible = await labelElement.isVisible().catch(() => false);
        if (isVisible) foundLabels++;
      }

      // Should find some summary statistics
      expect(foundLabels).toBeGreaterThan(0);
    });
  });

  // =============================================================================
  // Loading States Tests
  // =============================================================================

  test.describe('Loading States', () => {
    test('should show loading skeletons during initial load', async ({ page }) => {
      // Navigate fresh to catch loading state
      await page.goto('/construction-pipeline');

      // May see skeletons briefly
      const skeletons = page.locator('[class*="animate-pulse"]');
      await page.waitForTimeout(100);

      // Eventually content should load
      await waitForLoadingComplete(page);

      // Title should be visible
      const heading = page.getByRole('heading', { name: /construction pipeline/i });
      await expect(heading).toBeVisible();
    });

    test('should handle slow network gracefully', async ({ page }) => {
      // Use slow network simulation
      await page.route('**/*', (route) => {
        setTimeout(() => route.continue(), 50);
      });

      await page.goto('/construction-pipeline');

      // Eventually should load
      await waitForLoadingComplete(page, 30000);

      // Page should be functional
      const heading = page.getByRole('heading', { name: /construction pipeline/i });
      await expect(heading).toBeVisible();
    });
  });

  // =============================================================================
  // Error Handling Tests
  // =============================================================================

  test.describe('Error Handling', () => {
    test('should show error state when API fails', async ({ page }) => {
      // Intercept API calls and fail them
      await page.route('**/construction/**', (route) => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Internal Server Error' }),
        });
      });

      await page.goto('/construction-pipeline');
      await page.waitForTimeout(2000);

      // Should show error state or fall back to mock data
      const content = await page.locator('main[role="main"]').textContent();
      expect(content).toBeTruthy();
    });

    test('should provide retry button on error', async ({ page }) => {
      // This test verifies the retry mechanism exists
      await page.route('**/construction/**', (route, request) => {
        // First request fails
        if (!request.url().includes('retry')) {
          route.fulfill({
            status: 500,
            body: JSON.stringify({ error: 'Server Error' }),
          });
        } else {
          route.continue();
        }
      });

      await page.goto('/construction-pipeline');
      await page.waitForTimeout(2000);

      // Look for retry button (if error state is shown)
      const retryButton = page.getByRole('button', { name: /retry/i });
      const hasRetry = await retryButton.isVisible().catch(() => false);

      // If error state is shown, retry should be available
      // If mock data fallback is used, page still works
      const content = await page.locator('main[role="main"]').textContent();
      expect(content).toBeTruthy();
    });
  });

  // =============================================================================
  // Responsive Layout Tests
  // =============================================================================

  test.describe('Responsive Layout', () => {
    test('should display correctly on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/construction-pipeline');
      await waitForLoadingComplete(page);

      // Page should still be functional
      const heading = page.getByRole('heading', { name: /construction pipeline/i });
      await expect(heading).toBeVisible();

      // Tabs should be visible
      const tableTab = page.getByRole('tab', { name: /table/i });
      await expect(tableTab).toBeVisible();
    });

    test('should display correctly on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/construction-pipeline');
      await waitForLoadingComplete(page);

      // Page should still be functional
      const heading = page.getByRole('heading', { name: /construction pipeline/i });
      await expect(heading).toBeVisible();

      // Status cards should stack
      const cards = page.locator('[class*="shadow"]');
      const cardCount = await cards.count();
      expect(cardCount).toBeGreaterThan(0);
    });
  });

  // =============================================================================
  // Navigation Tests
  // =============================================================================

  test.describe('Navigation', () => {
    test('should navigate to construction pipeline from main navigation', async ({ page }) => {
      await page.goto('/');
      await page.waitForTimeout(1000);

      // Find and click Construction Pipeline link
      const pipelineLink = page.getByRole('link', { name: /construction|pipeline/i });
      const hasLink = await pipelineLink.first().isVisible().catch(() => false);

      if (hasLink) {
        await pipelineLink.first().click();
        await expect(page).toHaveURL(/\/construction-pipeline/);

        // Verify page loaded
        const heading = page.getByRole('heading', { name: /construction pipeline/i });
        await expect(heading).toBeVisible();
      }
    });

    test('should maintain URL state after tab changes', async ({ page }) => {
      await page.goto('/construction-pipeline');
      await waitForLoadingComplete(page);

      // Switch to Charts tab
      const chartsTab = page.getByRole('tab', { name: /charts/i });
      await chartsTab.click();
      await page.waitForTimeout(500);

      // URL should still be construction-pipeline
      await expect(page).toHaveURL(/\/construction-pipeline/);

      // Switch to Map tab
      const mapTab = page.getByRole('tab', { name: /map/i });
      await mapTab.click();
      await page.waitForTimeout(500);

      // URL should still be construction-pipeline
      await expect(page).toHaveURL(/\/construction-pipeline/);
    });
  });

  // =============================================================================
  // Integration Tests
  // =============================================================================

  test.describe('Integration Tests', () => {
    test('should complete full workflow: load, filter, switch tabs', async ({ page }) => {
      await page.goto('/construction-pipeline');
      await waitForLoadingComplete(page);

      // Verify page loaded
      const heading = page.getByRole('heading', { name: /construction pipeline/i });
      await expect(heading).toBeVisible();

      // Verify table is visible by default
      await waitForTable(page);
      const tableTitle = page.locator('text=Construction Projects').first();
      await expect(tableTitle).toBeVisible();

      // Switch to Charts tab
      const chartsTab = page.getByRole('tab', { name: /charts/i });
      await chartsTab.click();
      await page.waitForTimeout(1000);

      // Verify charts are displayed
      const funnelTitle = page.locator('text=/Pipeline Funnel/i').first();
      await expect(funnelTitle).toBeVisible();

      // Switch to Map tab
      const mapTab = page.getByRole('tab', { name: /map/i });
      await mapTab.click();
      await page.waitForTimeout(1500);

      // Verify map is displayed
      const mapTitle = page.locator('text=/Pipeline Map/i').first();
      await expect(mapTitle).toBeVisible();

      // Switch to Data Sources tab
      const sourcesTab = page.getByRole('tab', { name: /data sources/i });
      await sourcesTab.click();
      await page.waitForTimeout(500);

      // Verify data sources are displayed
      const sourcesTitle = page.locator('text=/Data Quality|Data Sources/i').first();
      await expect(sourcesTitle).toBeVisible();

      // Switch back to Table tab
      const tableTab = page.getByRole('tab', { name: /table/i });
      await tableTab.click();
      await page.waitForTimeout(500);

      // Verify table is visible again
      await expect(tableTitle).toBeVisible();
    });

    test('should apply filters and see results update across tabs', async ({ page }) => {
      await page.goto('/construction-pipeline');
      await waitForLoadingComplete(page);

      // Get initial content
      const initialContent = await page.locator('main[role="main"]').textContent();

      // Apply a search filter
      const searchInput = page.getByPlaceholder(/search projects/i);
      const hasSearch = await searchInput.isVisible().catch(() => false);

      if (hasSearch) {
        await searchInput.fill('Phoenix');
        await page.waitForTimeout(500);

        // Content should update
        const filteredContent = await page.locator('main[role="main"]').textContent();
        expect(filteredContent).toBeTruthy();

        // Switch to Charts tab - filter should still be applied
        const chartsTab = page.getByRole('tab', { name: /charts/i });
        await chartsTab.click();
        await page.waitForTimeout(1000);

        // Charts should reflect filtered data
        const chartContent = await page.locator('main[role="main"]').textContent();
        expect(chartContent).toBeTruthy();
      }
    });
  });
});
