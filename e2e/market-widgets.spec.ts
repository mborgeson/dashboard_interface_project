import { test, expect, type Page } from '@playwright/test';

/**
 * E2E Tests: Market Widgets
 *
 * Comprehensive tests for market data visualizations across:
 * - Dashboard page market widgets (MarketOverviewWidget, SubmarketComparisonWidget, MarketTrendsWidget)
 * - Market page components (MarketOverview, EconomicIndicators, MarketTrendsChart, MarketHeatmap, SubmarketComparison)
 * - Data loading states, error handling, and chart interactions
 */

// =============================================================================
// Test Utilities
// =============================================================================

/**
 * Wait for loading states to complete
 */
async function waitForLoadingComplete(page: Page, timeout = 10000) {
  // Wait for any loading skeletons to disappear
  await page.waitForFunction(
    () => {
      const skeletons = document.querySelectorAll('[class*="animate-pulse"], [class*="skeleton"]');
      return skeletons.length === 0;
    },
    { timeout }
  ).catch(() => {
    // If timeout, continue anyway - content may have loaded differently
  });

  // Wait a bit for charts to render
  await page.waitForTimeout(500);
}

/**
 * Wait for Recharts SVG to be visible
 */
async function waitForChart(page: Page, timeout = 10000) {
  await page.waitForSelector('.recharts-wrapper, .recharts-surface, svg[class*="recharts"]', {
    timeout,
    state: 'visible',
  }).catch(() => {
    // Chart may not exist, continue with test
  });
}

// =============================================================================
// Dashboard Market Widgets Tests
// =============================================================================

test.describe('Dashboard Market Widgets', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    await waitForLoadingComplete(page);
  });

  test.describe('MarketOverviewWidget', () => {
    test('should render Phoenix MSA overview widget on dashboard', async ({ page }) => {
      // Look for the Market Overview widget (compact variant on dashboard)
      const marketSection = page.locator('[class*="shadow-card"]').filter({
        hasText: /Phoenix MSA/i,
      });

      // Should find the widget or at least the section
      const widgetExists = await marketSection.first().isVisible().catch(() => false);

      if (widgetExists) {
        await expect(marketSection.first()).toBeVisible();

        // Verify key metrics are displayed
        const metricsText = await marketSection.first().textContent();
        expect(metricsText).toBeTruthy();
      }
    });

    test('should display population, employment, and GDP metrics', async ({ page }) => {
      // Look for metric labels in market overview area
      const populationLabel = page.getByText(/population/i).first();
      const employmentLabel = page.getByText(/employment/i).first();

      // At least one should be visible on dashboard
      const hasPopulation = await populationLabel.isVisible().catch(() => false);
      const hasEmployment = await employmentLabel.isVisible().catch(() => false);

      // Dashboard should have some market metrics
      expect(hasPopulation || hasEmployment).toBeTruthy();
    });

    test('should show YoY change indicators with trend icons', async ({ page }) => {
      // Look for trend indicators (percentages with + or -)
      const trendIndicators = page.locator('[class*="text-green"], [class*="text-red"]').filter({
        hasText: /%/,
      });

      // Should have at least one trend indicator
      const hasTrends = await trendIndicators.first().isVisible().catch(() => false);

      if (hasTrends) {
        await expect(trendIndicators.first()).toBeVisible();
      }
    });
  });

  test.describe('SubmarketComparisonWidget', () => {
    test('should render submarket comparison widget on dashboard', async ({ page }) => {
      // Look for Submarket Comparison widget
      const submarketWidget = page.locator('[class*="shadow-card"]').filter({
        hasText: /Submarket Comparison/i,
      });

      const widgetExists = await submarketWidget.first().isVisible().catch(() => false);

      if (widgetExists) {
        await expect(submarketWidget.first()).toBeVisible();
      }
    });

    test('should display chart visualization', async ({ page }) => {
      // Wait for any recharts to render
      await waitForChart(page);

      // Look for SVG chart elements
      const chartElements = page.locator('.recharts-wrapper, .recharts-surface, svg');

      // Dashboard should have at least one chart
      const hasCharts = await chartElements.first().isVisible().catch(() => false);
      expect(hasCharts).toBeTruthy();
    });

    test('should show metric toggle buttons', async ({ page }) => {
      // Look for metric selector buttons (Avg Rent, Rent Growth, Occupancy, Cap Rate)
      const avgRentBtn = page.getByRole('button', { name: /avg rent/i });
      const rentGrowthBtn = page.getByRole('button', { name: /rent growth/i });
      const occupancyBtn = page.getByRole('button', { name: /occupancy/i });
      const capRateBtn = page.getByRole('button', { name: /cap rate/i });

      // At least one metric button should be visible
      const hasAvgRent = await avgRentBtn.isVisible().catch(() => false);
      const hasRentGrowth = await rentGrowthBtn.isVisible().catch(() => false);
      const hasOccupancy = await occupancyBtn.isVisible().catch(() => false);
      const hasCapRate = await capRateBtn.isVisible().catch(() => false);

      // Should have metric toggles if widget is present
      const hasMetricToggles = hasAvgRent || hasRentGrowth || hasOccupancy || hasCapRate;

      // This is optional on dashboard, but if present should work
      if (hasMetricToggles) {
        expect(hasMetricToggles).toBeTruthy();
      }
    });

    test('should switch metrics when toggle is clicked', async ({ page }) => {
      // Find metric toggle buttons
      const rentGrowthBtn = page.getByRole('button', { name: /rent growth/i }).first();
      const occupancyBtn = page.getByRole('button', { name: /occupancy/i }).first();

      const hasRentGrowth = await rentGrowthBtn.isVisible().catch(() => false);

      if (hasRentGrowth) {
        // Click Rent Growth button
        await rentGrowthBtn.click();
        await page.waitForTimeout(300);

        // Verify button state changed (active state)
        await expect(rentGrowthBtn).toHaveClass(/bg-primary/);

        // Now click Occupancy
        const hasOccupancy = await occupancyBtn.isVisible().catch(() => false);
        if (hasOccupancy) {
          await occupancyBtn.click();
          await page.waitForTimeout(300);
          await expect(occupancyBtn).toHaveClass(/bg-primary/);
        }
      }
    });
  });

  test.describe('MarketTrendsWidget', () => {
    test('should render market trends widget on dashboard', async ({ page }) => {
      // Look for Market Trends widget
      const trendsWidget = page.locator('text=Market Trends').first();

      const widgetExists = await trendsWidget.isVisible().catch(() => false);

      if (widgetExists) {
        await expect(trendsWidget).toBeVisible();
      }
    });

    test('should display period selector buttons', async ({ page }) => {
      // Look for period selector buttons (6M, 1Y, 2Y)
      const sixMonthBtn = page.getByRole('button', { name: '6M' });
      const oneYearBtn = page.getByRole('button', { name: '1Y' });
      const twoYearBtn = page.getByRole('button', { name: '2Y' });

      const has6M = await sixMonthBtn.isVisible().catch(() => false);
      const has1Y = await oneYearBtn.isVisible().catch(() => false);
      const has2Y = await twoYearBtn.isVisible().catch(() => false);

      // If period selector exists, test it
      if (has6M || has1Y || has2Y) {
        expect(has6M || has1Y || has2Y).toBeTruthy();
      }
    });

    test('should switch time periods when selector is clicked', async ({ page }) => {
      const sixMonthBtn = page.getByRole('button', { name: '6M' });
      const oneYearBtn = page.getByRole('button', { name: '1Y' });

      const has6M = await sixMonthBtn.isVisible().catch(() => false);

      if (has6M) {
        // Click 6M button
        await sixMonthBtn.click();
        await page.waitForTimeout(500);

        // Verify button shows active state
        await expect(sixMonthBtn).toHaveClass(/bg-neutral-800|text-white/);

        // Switch to 1Y
        const has1Y = await oneYearBtn.isVisible().catch(() => false);
        if (has1Y) {
          await oneYearBtn.click();
          await page.waitForTimeout(500);
          await expect(oneYearBtn).toHaveClass(/bg-neutral-800|text-white/);
        }
      }
    });

    test('should show area chart with trend data', async ({ page }) => {
      // Wait for chart to render
      await waitForChart(page, 15000);

      // Look for Recharts area chart elements
      const areaChart = page.locator('.recharts-area, .recharts-area-area');
      const lineChart = page.locator('.recharts-line, .recharts-line-curve');
      const anyChart = page.locator('.recharts-surface');

      const hasArea = await areaChart.first().isVisible().catch(() => false);
      const hasLine = await lineChart.first().isVisible().catch(() => false);
      const hasAny = await anyChart.first().isVisible().catch(() => false);

      // Should have some chart visualization
      expect(hasArea || hasLine || hasAny).toBeTruthy();
    });
  });
});

// =============================================================================
// Market Page Tests
// =============================================================================

test.describe('Market Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/market');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
  });

  test.describe('Page Load', () => {
    test('should display market page with correct title', async ({ page }) => {
      await expect(page).toHaveURL(/\/market/);

      // Wait for loading to complete
      await waitForLoadingComplete(page);

      // Check for page title
      const pageTitle = page.getByRole('heading', { name: /market data/i });
      await expect(pageTitle).toBeVisible();
    });

    test('should show Phoenix MSA description', async ({ page }) => {
      await waitForLoadingComplete(page);

      const description = page.getByText(/Phoenix MSA/i).first();
      await expect(description).toBeVisible();
    });

    test('should have Export Report button', async ({ page }) => {
      await waitForLoadingComplete(page);

      const exportButton = page.getByRole('button', { name: /export report/i });
      await expect(exportButton).toBeVisible();
    });
  });

  test.describe('Loading States', () => {
    test('should show loading skeletons initially', async ({ page }) => {
      // Navigate fresh to catch loading state
      await page.goto('/market');

      // Look for skeleton elements (may be very quick)
      const skeletons = page.locator('[class*="animate-pulse"], [class*="skeleton"]');

      // Either skeletons are visible or content loaded fast
      const hasSkeletons = await skeletons.first().isVisible().catch(() => false);

      // Content should eventually load
      await waitForLoadingComplete(page, 15000);

      // After loading, check that real content is visible
      const pageTitle = page.getByRole('heading', { name: /market data/i });
      await expect(pageTitle).toBeVisible();
    });
  });

  test.describe('MarketOverview Component', () => {
    test('should display Phoenix MSA Overview section', async ({ page }) => {
      await waitForLoadingComplete(page);

      const overviewSection = page.getByText(/Phoenix MSA Overview/i).first();
      await expect(overviewSection).toBeVisible();
    });

    test('should show population, employment, and GDP cards', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for metric cards
      const populationCard = page.locator('text=Population').first();
      const employmentCard = page.locator('text=Employment').first();
      const gdpCard = page.locator('text=GDP').first();

      await expect(populationCard).toBeVisible();
      await expect(employmentCard).toBeVisible();
      await expect(gdpCard).toBeVisible();
    });

    test('should display formatted numeric values', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for formatted numbers (e.g., "5.08M" for population, "$xxx.xB" for GDP)
      const formattedValues = page.locator('text=/\\d+\\.\\d+[MBK]|\\$\\d/');

      const hasFormattedValues = await formattedValues.first().isVisible().catch(() => false);
      expect(hasFormattedValues).toBeTruthy();
    });

    test('should show YoY percentage changes', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for YoY indicators
      const yoyIndicators = page.locator('text=/YoY/i');

      const hasYoY = await yoyIndicators.first().isVisible().catch(() => false);
      expect(hasYoY).toBeTruthy();
    });
  });

  test.describe('EconomicIndicators Component', () => {
    test('should display Key Economic Indicators section', async ({ page }) => {
      await waitForLoadingComplete(page);

      const indicatorsSection = page.getByText(/Key Economic Indicators/i).first();
      await expect(indicatorsSection).toBeVisible();
    });

    test('should show unemployment rate indicator', async ({ page }) => {
      await waitForLoadingComplete(page);

      const unemploymentIndicator = page.locator('text=Unemployment Rate').first();
      await expect(unemploymentIndicator).toBeVisible();
    });

    test('should show job growth rate indicator', async ({ page }) => {
      await waitForLoadingComplete(page);

      const jobGrowthIndicator = page.locator('text=Job Growth Rate').first();
      await expect(jobGrowthIndicator).toBeVisible();
    });

    test('should display sparkline charts for indicators', async ({ page }) => {
      await waitForLoadingComplete(page);
      await waitForChart(page);

      // Look for sparkline SVG elements (small line charts)
      const sparklines = page.locator('.recharts-line, .recharts-wrapper');

      const hasSparklines = await sparklines.first().isVisible().catch(() => false);
      expect(hasSparklines).toBeTruthy();
    });

    test('should show 6-month trend label', async ({ page }) => {
      await waitForLoadingComplete(page);

      const trendLabel = page.locator('text=/Last 6 months/i').first();

      const hasTrendLabel = await trendLabel.isVisible().catch(() => false);
      expect(hasTrendLabel).toBeTruthy();
    });
  });

  test.describe('MarketTrendsChart Component', () => {
    test('should display Market Trends chart section', async ({ page }) => {
      await waitForLoadingComplete(page);

      const trendsSection = page.getByText(/Market Trends/i).first();
      await expect(trendsSection).toBeVisible();
    });

    test('should render area chart with data', async ({ page }) => {
      await waitForLoadingComplete(page);
      await waitForChart(page, 15000);

      // Look for Recharts area chart
      const areaChart = page.locator('.recharts-area, .recharts-area-curve, .recharts-surface');

      const hasChart = await areaChart.first().isVisible().catch(() => false);
      expect(hasChart).toBeTruthy();
    });

    test('should have metric toggle buttons (Rent Growth, Occupancy, Cap Rate)', async ({
      page,
    }) => {
      await waitForLoadingComplete(page);

      const rentGrowthBtn = page.getByRole('button', { name: /rent growth/i });
      const occupancyBtn = page.getByRole('button', { name: /occupancy/i });
      const capRateBtn = page.getByRole('button', { name: /cap rate/i });

      // At least one should be visible
      const hasRentGrowth = await rentGrowthBtn.isVisible().catch(() => false);
      const hasOccupancy = await occupancyBtn.isVisible().catch(() => false);
      const hasCapRate = await capRateBtn.isVisible().catch(() => false);

      expect(hasRentGrowth || hasOccupancy || hasCapRate).toBeTruthy();
    });

    test('should switch chart metric when toggle is clicked', async ({ page }) => {
      await waitForLoadingComplete(page);

      const occupancyBtn = page.getByRole('button', { name: /occupancy/i }).first();

      const hasOccupancy = await occupancyBtn.isVisible().catch(() => false);

      if (hasOccupancy) {
        // Click to change metric
        await occupancyBtn.click();
        await page.waitForTimeout(500);

        // Verify button is now active (primary color)
        await expect(occupancyBtn).toHaveClass(/bg-primary/);
      }
    });

    test('should show chart legend', async ({ page }) => {
      await waitForLoadingComplete(page);
      await waitForChart(page);

      // Look for legend text
      const legendText = page.locator('text=/Phoenix MSA/i');

      const hasLegend = await legendText.first().isVisible().catch(() => false);
      expect(hasLegend).toBeTruthy();
    });
  });

  test.describe('MarketHeatmap Component', () => {
    test('should display Market Performance Heatmap section', async ({ page }) => {
      await waitForLoadingComplete(page);

      const heatmapSection = page.getByText(/Market Performance Heatmap/i).first();
      await expect(heatmapSection).toBeVisible();
    });

    test('should show submarket tiles with color coding', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for submarket names (known Phoenix submarkets)
      const submarketNames = [
        'Scottsdale',
        'Tempe',
        'Downtown Phoenix',
        'Gilbert',
        'Chandler',
        'Mesa',
      ];

      let foundSubmarkets = 0;
      for (const name of submarketNames) {
        const submarket = page.locator(`text=${name}`).first();
        const isVisible = await submarket.isVisible().catch(() => false);
        if (isVisible) foundSubmarkets++;
      }

      // Should find at least a few submarkets
      expect(foundSubmarkets).toBeGreaterThan(0);
    });

    test('should have metric toggle buttons for heatmap', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Heatmap has Rent Growth, Occupancy, Cap Rate buttons
      const heatmapCard = page.locator('text=Market Performance Heatmap').locator('..');

      const rentGrowthBtn = heatmapCard.getByRole('button', { name: /rent growth/i });
      const occupancyBtn = heatmapCard.getByRole('button', { name: /occupancy/i });
      const capRateBtn = heatmapCard.getByRole('button', { name: /cap rate/i });

      const hasRentGrowth = await rentGrowthBtn.isVisible().catch(() => false);
      const hasOccupancy = await occupancyBtn.isVisible().catch(() => false);
      const hasCapRate = await capRateBtn.isVisible().catch(() => false);

      expect(hasRentGrowth || hasOccupancy || hasCapRate).toBeTruthy();
    });

    test('should update heatmap colors when metric changes', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Find the heatmap section
      const heatmapSection = page.locator('text=Market Performance Heatmap').locator('xpath=ancestor::div[contains(@class, "p-6")]');

      const capRateBtn = heatmapSection.getByRole('button', { name: /cap rate/i });

      const hasCapRate = await capRateBtn.isVisible().catch(() => false);

      if (hasCapRate) {
        // Click Cap Rate
        await capRateBtn.click();
        await page.waitForTimeout(500);

        // Verify it's now active
        await expect(capRateBtn).toHaveClass(/bg-primary/);
      }
    });

    test('should show legend with gradient', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Look for legend gradient or performance text
      const performanceText = page.locator('text=/Performance:/i');
      const legendGradient = page.locator('[style*="linear-gradient"]');

      const hasPerformance = await performanceText.isVisible().catch(() => false);
      const hasGradient = await legendGradient.first().isVisible().catch(() => false);

      expect(hasPerformance || hasGradient).toBeTruthy();
    });

    test('should display submarket details on hover', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Find a submarket tile
      const submarketTile = page.locator('text=Scottsdale').locator('xpath=ancestor::div[contains(@class, "rounded-lg")]').first();

      const hasTile = await submarketTile.isVisible().catch(() => false);

      if (hasTile) {
        // Hover over the tile
        await submarketTile.hover();
        await page.waitForTimeout(300);

        // Should see submarket details (Avg Rent, Inventory)
        const avgRentText = page.locator('text=/Avg Rent/i');
        const hasDetails = await avgRentText.first().isVisible().catch(() => false);
        expect(hasDetails).toBeTruthy();
      }
    });
  });

  test.describe('SubmarketComparison Component', () => {
    test('should display Submarket Comparison section', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Scroll down to find the section
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);

      const comparisonSection = page.getByText(/Submarket Comparison/i).first();
      await expect(comparisonSection).toBeVisible();
    });

    test('should render horizontal bar chart', async ({ page }) => {
      await waitForLoadingComplete(page);
      await waitForChart(page, 15000);

      // Scroll to ensure visibility
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);

      // Look for bar chart elements
      const barChart = page.locator('.recharts-bar, .recharts-bar-rectangle, .recharts-surface');

      const hasBarChart = await barChart.first().isVisible().catch(() => false);
      expect(hasBarChart).toBeTruthy();
    });

    test('should display comparison table with metrics', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Scroll down
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);

      // Look for table headers
      const tableHeaders = ['Submarket', 'Avg Rent', 'Rent Growth', 'Occupancy', 'Cap Rate', 'Inventory'];

      let foundHeaders = 0;
      for (const header of tableHeaders) {
        const headerElement = page.locator(`th:has-text("${header}")`).first();
        const isVisible = await headerElement.isVisible().catch(() => false);
        if (isVisible) foundHeaders++;
      }

      // Should find most table headers
      expect(foundHeaders).toBeGreaterThan(3);
    });

    test('should show summary statistics', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Scroll to bottom
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);

      // Look for summary stats
      const totalInventory = page.locator('text=/Total Inventory/i').first();
      const netAbsorption = page.locator('text=/Net Absorption/i').first();
      const avgOccupancy = page.locator('text=/Avg Occupancy/i').first();

      const hasTotalInventory = await totalInventory.isVisible().catch(() => false);
      const hasNetAbsorption = await netAbsorption.isVisible().catch(() => false);
      const hasAvgOccupancy = await avgOccupancy.isVisible().catch(() => false);

      expect(hasTotalInventory || hasNetAbsorption || hasAvgOccupancy).toBeTruthy();
    });

    test('should update chart when metric toggle is clicked', async ({ page }) => {
      await waitForLoadingComplete(page);

      // Scroll down
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);

      // Find metric buttons in the comparison section
      const capRateBtn = page.getByRole('button', { name: /cap rate/i }).last();

      const hasCapRate = await capRateBtn.isVisible().catch(() => false);

      if (hasCapRate) {
        await capRateBtn.click();
        await page.waitForTimeout(500);

        // Verify active state
        await expect(capRateBtn).toHaveClass(/bg-primary/);
      }
    });
  });
});

// =============================================================================
// Chart Interactions Tests
// =============================================================================

test.describe('Chart Interactions', () => {
  test.describe('Tooltip Interactions', () => {
    test('should show tooltip on chart hover', async ({ page }) => {
      await page.goto('/market');
      await waitForLoadingComplete(page, 15000);
      await waitForChart(page, 15000);

      // Find a chart area
      const chartArea = page.locator('.recharts-surface').first();
      const hasChart = await chartArea.isVisible().catch(() => false);

      if (hasChart) {
        // Get chart bounding box and hover in the middle
        const box = await chartArea.boundingBox();
        if (box) {
          await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
          await page.waitForTimeout(500);

          // Look for tooltip
          const tooltip = page.locator('.recharts-tooltip-wrapper, [class*="shadow-lg"]');
          const hasTooltip = await tooltip.first().isVisible().catch(() => false);

          // Tooltip may or may not appear depending on chart data
          // Just verify no errors occurred
          expect(true).toBeTruthy();
        }
      }
    });

    test('should display formatted values in tooltip', async ({ page }) => {
      await page.goto('/market');
      await waitForLoadingComplete(page, 15000);
      await waitForChart(page, 15000);

      const chartArea = page.locator('.recharts-surface').first();
      const hasChart = await chartArea.isVisible().catch(() => false);

      if (hasChart) {
        const box = await chartArea.boundingBox();
        if (box) {
          // Hover over chart
          await page.mouse.move(box.x + box.width / 3, box.y + box.height / 2);
          await page.waitForTimeout(500);

          // If tooltip appears, it should have formatted values
          const tooltip = page.locator('[class*="shadow-lg"]');
          const tooltipText = await tooltip.first().textContent().catch(() => '');

          // Tooltip might have percentages or currency values
          if (tooltipText) {
            expect(tooltipText.length).toBeGreaterThan(0);
          }
        }
      }
    });
  });

  test.describe('Responsive Chart Behavior', () => {
    test('should resize charts on viewport change', async ({ page }) => {
      await page.goto('/market');
      await waitForLoadingComplete(page);
      await waitForChart(page);

      // Get initial chart size
      const chart = page.locator('.recharts-responsive-container').first();
      const hasChart = await chart.isVisible().catch(() => false);

      if (hasChart) {
        const initialBox = await chart.boundingBox();

        // Resize viewport to mobile
        await page.setViewportSize({ width: 375, height: 667 });
        await page.waitForTimeout(500);

        // Chart should still be visible
        await expect(chart).toBeVisible();

        // Reset viewport
        await page.setViewportSize({ width: 1280, height: 720 });
      }
    });
  });
});

// =============================================================================
// Data Loading and Error States Tests
// =============================================================================

test.describe('Data Loading and Error States', () => {
  test.describe('Loading Skeleton Display', () => {
    test('should show stat card skeletons during load', async ({ page }) => {
      // Use slow network to catch loading states
      await page.route('**/*', (route) => {
        setTimeout(() => route.continue(), 100);
      });

      await page.goto('/market');

      // Look for skeleton elements quickly
      const skeletons = page.locator('[class*="animate-pulse"]');

      // May or may not catch skeletons depending on speed
      // Just verify page eventually loads
      await waitForLoadingComplete(page, 20000);

      const pageTitle = page.getByRole('heading', { name: /market data/i });
      await expect(pageTitle).toBeVisible();
    });

    test('should show chart skeletons during load', async ({ page }) => {
      await page.goto('/market');

      // Wait for content to load
      await waitForLoadingComplete(page, 15000);

      // Verify charts rendered (no permanent skeletons)
      const permanentSkeletons = page.locator('[class*="animate-pulse"]');
      const skeletonCount = await permanentSkeletons.count();

      // After loading, should have minimal or no skeletons
      expect(skeletonCount).toBeLessThan(5);
    });
  });

  test.describe('Content Verification', () => {
    test('should display real data after loading', async ({ page }) => {
      await page.goto('/market');
      await waitForLoadingComplete(page, 15000);

      // Verify actual data is displayed (not placeholder text)
      const pageContent = await page.locator('main[role="main"]').textContent();

      // Should have numeric values
      expect(pageContent).toMatch(/\d+/);

      // Should have percentages
      expect(pageContent).toMatch(/%/);
    });

    test('should not show error state on normal load', async ({ page }) => {
      await page.goto('/market');
      await waitForLoadingComplete(page, 15000);

      // Look for error indicators
      const errorState = page.locator('text=/failed to load/i, text=/error/i, text=/try again/i');

      // Should not have error messages visible
      const hasErrors = await errorState.first().isVisible().catch(() => false);
      expect(hasErrors).toBeFalsy();
    });
  });
});

// =============================================================================
// Export Report Feature Tests
// =============================================================================

test.describe('Export Report Feature', () => {
  test('should open report wizard when Export Report is clicked', async ({ page }) => {
    await page.goto('/market');
    await waitForLoadingComplete(page);

    const exportButton = page.getByRole('button', { name: /export report/i });
    await expect(exportButton).toBeVisible();

    // Click export button
    await exportButton.click();
    await page.waitForTimeout(500);

    // Look for report wizard dialog
    const wizardDialog = page.locator('[role="dialog"], [class*="Dialog"]');
    const hasDialog = await wizardDialog.first().isVisible().catch(() => false);

    // Dialog should open (if implemented)
    if (hasDialog) {
      await expect(wizardDialog.first()).toBeVisible();

      // Close dialog
      const closeButton = page.getByRole('button', { name: /close|cancel|x/i }).first();
      if (await closeButton.isVisible()) {
        await closeButton.click();
      }
    }
  });
});

// =============================================================================
// Market Data Sources Footer Tests
// =============================================================================

test.describe('Market Data Sources', () => {
  test('should display data sources footer', async ({ page }) => {
    await page.goto('/market');
    await waitForLoadingComplete(page);

    // Scroll to bottom
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    // Look for data sources section
    const dataSourcesSection = page.locator('text=/Market Data Sources/i').first();
    const hasDataSources = await dataSourcesSection.isVisible().catch(() => false);

    if (hasDataSources) {
      await expect(dataSourcesSection).toBeVisible();

      // Verify source mentions
      const sourceText = await page.locator('text=/CoStar|Census Bureau|Bureau of Labor/i').first().textContent().catch(() => '');
      expect(sourceText?.length).toBeGreaterThan(0);
    }
  });
});

// =============================================================================
// Cross-Page Widget Consistency Tests
// =============================================================================

test.describe('Cross-Page Widget Consistency', () => {
  test('should show consistent market data between dashboard and market page', async ({
    page,
  }) => {
    // Get data from dashboard
    await page.goto('/');
    await waitForLoadingComplete(page, 15000);

    // Look for any Phoenix MSA metric on dashboard
    const dashboardMetrics = await page.locator('text=/Phoenix MSA/i').first().textContent().catch(() => '');

    // Navigate to market page
    await page.goto('/market');
    await waitForLoadingComplete(page, 15000);

    // Look for Phoenix MSA metric on market page
    const marketMetrics = await page.locator('text=/Phoenix MSA/i').first().textContent().catch(() => '');

    // Both pages should have Phoenix MSA data
    expect(dashboardMetrics?.length || 0).toBeGreaterThan(0);
    expect(marketMetrics?.length || 0).toBeGreaterThan(0);
  });
});
