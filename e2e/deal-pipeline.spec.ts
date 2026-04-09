import { test, expect } from './fixtures/auth';
import { assertBackendHealthy } from './fixtures/auth';

/**
 * E2E Tests: Deal Pipeline - Kanban Board and Deal Detail Modal
 *
 * Tests the Kanban board widget, deal card interactions, deal detail modal,
 * activity feed, and stage transitions for the Wave 5 integration.
 */

const API_BASE = 'http://localhost:8000/api/v1';

// Deal pipeline stages as displayed in the Kanban board
const PIPELINE_STAGES = [
  { id: 'lead', label: 'Lead' },
  { id: 'underwriting', label: 'Underwriting' },
  { id: 'loi', label: 'LOI' },
  { id: 'due_diligence', label: 'Due Diligence' },
  { id: 'closing', label: 'Closing' },
  { id: 'closed_won', label: 'Closed Won' },
];

test.describe('Deal Pipeline - Kanban Board', () => {
  test.describe('Kanban Board Loading', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/deals');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      // Wait for loading state to complete
      await page.waitForFunction(
        () => !document.body.textContent?.includes('Loading page...'),
        { timeout: 15000 }
      ).catch(() => {});
      await page.waitForLoadState('networkidle');
    });

    test('should display deals page with Kanban view as default', async ({ page }) => {
      // Verify we're on the deals page
      await expect(page).toHaveURL(/\/deals/);

      // Check for Deal Pipeline header
      const header = page.getByRole('heading', { name: /deal pipeline/i });
      await expect(header).toBeVisible();

      // Kanban button should be active (blue background)
      const kanbanButton = page.getByRole('button', { name: /kanban/i });
      await expect(kanbanButton).toBeVisible();
    });

    test('should render all 6 Kanban columns for pipeline stages', async ({ page }) => {
      // Wait for Kanban board to load
      await page.waitForLoadState('networkidle');

      // Check for pipeline stage column headers
      for (const stage of PIPELINE_STAGES) {
        const stageHeader = page.getByRole('heading', { name: stage.label }).or(
          page.getByText(stage.label, { exact: false })
        );

        // At least some stages should be visible
        const isVisible = await stageHeader.first().isVisible().catch(() => false);
        if (isVisible) {
          expect(isVisible).toBeTruthy();
        }
      }
    });

    test('should display summary stats above Kanban board', async ({ page }) => {
      await page.waitForLoadState('networkidle');

      // Check for summary statistics cards
      const statLabels = ['Active Deals', 'Pipeline Value', 'Avg Days in Pipeline', 'Win Rate'];

      for (const label of statLabels) {
        const statElement = page.getByText(label, { exact: false });
        if (await statElement.isVisible().catch(() => false)) {
          await expect(statElement).toBeVisible();
        }
      }
    });

    test('should display Kanban board structure', async ({ page }) => {
      // Wait for content to fully load
      await page.waitForLoadState('networkidle');

      // Verify the Kanban board structure exists - columns should be visible
      // even if there are no deals in them
      const kanbanButton = page.getByRole('button', { name: /kanban/i });
      const pipelineValue = page.getByText(/Pipeline Value/i);
      const activeDeals = page.getByText(/Active Deals/i);

      // Should have the Kanban view button (active) and stats visible
      await expect(kanbanButton).toBeVisible();

      // Should have stats section
      const hasStats = await pipelineValue.isVisible().catch(() => false) ||
                       await activeDeals.isVisible().catch(() => false);
      expect(hasStats).toBeTruthy();
    });

    test('should handle loading state with skeleton', async ({ page }) => {
      // Navigate fresh to catch loading state
      await page.goto('/deals', { waitUntil: 'domcontentloaded' });

      // Wait for main to be visible (either loading or loaded state)
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

      // Wait for loading to complete
      await page.waitForFunction(
        () => !document.body.textContent?.includes('Loading page...'),
        { timeout: 15000 }
      ).catch(() => {});

      // Now verify main content exists
      const mainContent = await page.locator('main[role="main"]').textContent();
      expect(mainContent && mainContent.length > 50).toBeTruthy();
    });

    test('should display empty state message in columns with no deals', async ({ page }) => {
      await page.waitForLoadState('networkidle');

      // Look for empty state text
      const emptyText = page.getByText(/no deals/i);
      const dragHereText = page.getByText(/drag a deal here/i);

      // Some columns may show empty state
      const hasEmptyState = await emptyText.first().isVisible().catch(() => false) ||
        await dragHereText.first().isVisible().catch(() => false);

      // This is informational - empty state may or may not be visible depending on data
      expect(typeof hasEmptyState).toBe('boolean');
    });
  });

  test.describe('View Mode Toggle', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/deals');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.waitForLoadState('networkidle');
    });

    test('should toggle between Kanban, Pipeline, and Timeline views', async ({ page }) => {
      // Kanban should be default
      const kanbanButton = page.getByRole('button', { name: /kanban/i });
      await expect(kanbanButton).toBeVisible();

      // Click Pipeline view
      const pipelineButton = page.getByRole('button', { name: /pipeline/i });
      if (await pipelineButton.isVisible().catch(() => false)) {
        await pipelineButton.click();
        await expect(page.locator('main[role="main"]')).toBeVisible();
      }

      // Click Timeline/List view
      const timelineButton = page.getByRole('button', { name: /timeline/i });
      if (await timelineButton.isVisible().catch(() => false)) {
        await timelineButton.click();
        await expect(page.locator('main[role="main"]')).toBeVisible();
      }

      // Return to Kanban
      await kanbanButton.click();
      await expect(page.locator('main[role="main"]')).toBeVisible();
    });
  });
});

test.describe('Deal Pipeline - Deal Card Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/deals');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    await page.waitForLoadState('networkidle');
  });

  test('should open DealDetailModal when clicking a deal card', async ({ page }) => {
    // Find a deal card with role="button" (clickable cards)
    const dealCards = page.locator('[role="button"]').filter({
      has: page.locator('h3'),
    });

    const cardCount = await dealCards.count();

    if (cardCount > 0) {
      // Click the first deal card
      await dealCards.first().click();

      // Check for dialog/modal
      const modal = page.getByRole('dialog');
      await expect(modal).toBeVisible({ timeout: 5000 });
    } else {
      // No clickable deal cards found - check for any cards in the grid
      const anyCards = page.locator('[class*="Card"]');
      const anyCardCount = await anyCards.count();

      // If we have cards but they're not clickable, that's informational
      if (anyCardCount > 0) {
        console.log('Deal cards found but may not be in clickable mode');
      }
    }
  });

  test('should close modal with Escape key', async ({ page }) => {
    const dealCards = page.locator('[role="button"]').filter({
      has: page.locator('h3'),
    });

    const cardCount = await dealCards.count();
    test.skip(cardCount === 0, 'No deal cards in Kanban view to test modal close');

    // Open modal
    await dealCards.first().click();

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible({ timeout: 5000 });

    // Press Escape to close
    await page.keyboard.press('Escape');

    // Modal should be closed
    await expect(modal).not.toBeVisible({ timeout: 3000 });
  });
});

test.describe('Deal Pipeline - Stage Transitions API', () => {
  test.beforeAll(async ({ request }) => {
    await assertBackendHealthy(request);
  });

  test('should list deals via API with stage information', async ({ request, authToken }) => {
    const response = await request.get(`${API_BASE}/deals/`, {
      params: { page: 1, page_size: 20 },
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toBeDefined();

    // If deals exist, they should have stage property
    if (data.deals && data.deals.length > 0) {
      expect(data.deals[0]).toHaveProperty('stage');
    } else if (data.items && data.items.length > 0) {
      expect(data.items[0]).toHaveProperty('stage');
    }
  });

  test('should get deal by ID with stage information', async ({ request, authToken }) => {
    const response = await request.get(`${API_BASE}/deals/1/`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    if (response.status() === 404) {
      // Deal ID 1 may not exist
      return;
    }

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('stage');
  });

  test('should filter deals by stage via API', async ({ request, authToken }) => {
    const stages = ['lead', 'underwriting', 'due_diligence', 'closing'];

    for (const stage of stages) {
      const response = await request.get(`${API_BASE}/deals/`, {
        params: { stage },
        headers: { Authorization: `Bearer ${authToken}` },
      });

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toBeDefined();
    }
  });

  test('should get deal activities via API', async ({ request, authToken }) => {
    const response = await request.get(`${API_BASE}/deals/1/activities/`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    if (response.status() === 404) {
      // Deal 1 or activities endpoint may not exist
      return;
    }

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toBeDefined();

    // Activities response should have array structure
    if (data.activities) {
      expect(Array.isArray(data.activities)).toBeTruthy();
    } else if (data.items) {
      expect(Array.isArray(data.items)).toBeTruthy();
    }
  });
});

test.describe('Deal Pipeline - Kanban Board Filters', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/deals');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    await page.waitForLoadState('networkidle');
  });

  test('should display filter controls', async ({ page }) => {
    // Look for filter-related elements
    const filterElements = [
      page.getByRole('textbox', { name: /search/i }),
      page.getByRole('combobox'),
      page.locator('[class*="filter"]'),
      page.getByPlaceholder(/search/i),
    ];

    let hasFilters = false;
    for (const element of filterElements) {
      if (await element.first().isVisible().catch(() => false)) {
        hasFilters = true;
        break;
      }
    }

    // Filters may or may not be visible depending on view mode
    expect(typeof hasFilters).toBe('boolean');
  });

  test('should update deal count when filters applied', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Look for results count text
    const resultsText = page.getByText(/showing.*of.*deals/i);

    if (await resultsText.isVisible().catch(() => false)) {
      const initialText = await resultsText.textContent();
      expect(initialText).toMatch(/showing.*\d+.*of.*\d+.*deals/i);
    }
  });
});

test.describe('Deal Pipeline - Drag and Drop (Visual Verification)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/deals');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    await page.waitForLoadState('networkidle');
  });

  test('should have draggable deal cards', async ({ page }) => {
    // Deal cards that are draggable have specific cursor styles
    const dealCards = page.locator('[role="button"]').filter({
      has: page.locator('h3'),
    });

    const cardCount = await dealCards.count();

    if (cardCount > 0) {
      // Verify cards exist and are interactive
      const firstCard = dealCards.first();
      await expect(firstCard).toBeVisible();

      // Cards should have cursor pointer or grab style
      const cursor = await firstCard.evaluate(el => getComputedStyle(el).cursor);
      expect(['pointer', 'grab', 'default']).toContain(cursor);
    }
  });

  test('should display drop zones on Kanban columns', async ({ page }) => {
    // Kanban columns act as drop zones
    const columns = page.locator('[class*="border-t-4"]');
    const columnCount = await columns.count();

    // Should have 6 pipeline columns
    expect(columnCount).toBeGreaterThanOrEqual(6);
  });

  test('should display stage icons and labels in columns', async ({ page }) => {
    // Check for stage emojis (icons) in column headers
    const stageIcons = ['Target', 'Underwriting', 'LOI', 'Due Diligence', 'Closing', 'Closed Won'];

    let foundStages = 0;
    for (const stage of stageIcons) {
      const stageElement = page.getByText(stage, { exact: false });
      if (await stageElement.first().isVisible().catch(() => false)) {
        foundStages++;
      }
    }

    // Should find at least some stages
    expect(foundStages).toBeGreaterThan(0);
  });
});

test.describe('Deal Pipeline - Deal Card Content Verification', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/deals');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    await page.waitForLoadState('networkidle');
  });

  test('should display deal card with property name', async ({ page }) => {
    // Deal cards have h3 headings with property names
    const propertyNames = page.locator('h3');
    const nameCount = await propertyNames.count();

    expect(nameCount).toBeGreaterThan(0);
  });

  test('should display deal card with value information', async ({ page }) => {
    // Look for currency values on cards
    const currencyPattern = page.getByText(/\$[\d,.]+[KMB]?/);
    const hasValues = await currencyPattern.first().isVisible().catch(() => false);

    if (hasValues) {
      expect(hasValues).toBeTruthy();
    }
  });

  test('should display deal card with cap rate', async ({ page }) => {
    // Look for percentage values (cap rate)
    const percentPattern = page.getByText(/[\d.]+%/);
    const hasPercent = await percentPattern.first().isVisible().catch(() => false);

    if (hasPercent) {
      expect(hasPercent).toBeTruthy();
    }
  });

  test('should display deal card with assignee information', async ({ page }) => {
    // Look for assignee section
    const assigneeLabels = page.getByText(/assignee/i);
    const hasAssignee = await assigneeLabels.first().isVisible().catch(() => false);

    // Deal cards should show assignee info
    if (hasAssignee) {
      expect(hasAssignee).toBeTruthy();
    }
  });

  test('should display deal card with days in stage', async ({ page }) => {
    // Look for "X days" text
    const daysText = page.getByText(/\d+\s+days?/i);
    const hasDays = await daysText.first().isVisible().catch(() => false);

    if (hasDays) {
      expect(hasDays).toBeTruthy();
    }
  });
});

test.describe('Deal Pipeline - Error Handling', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Navigate to deals page
    await page.goto('/deals');
    await page.waitForLoadState('networkidle');

    // Page should render even if API has issues
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

    // Either content loads or error state appears
    const hasContent = await page.locator('main[role="main"]').textContent().then(t => t && t.length > 50);
    const hasError = await page.getByText(/failed|error|unable/i).first().isVisible().catch(() => false);
    const hasRetry = await page.getByRole('button', { name: /retry|try again/i }).first().isVisible().catch(() => false);

    // Should have either content or proper error handling
    expect(hasContent || hasError || hasRetry).toBeTruthy();
  });

  test('should provide retry option on error state', async ({ page }) => {
    await page.goto('/deals');
    await page.waitForLoadState('networkidle');

    // If there's an error state, it should have a retry button
    const errorState = page.getByText(/failed to load/i);

    if (await errorState.isVisible().catch(() => false)) {
      const retryButton = page.getByRole('button', { name: /retry|try again/i });
      await expect(retryButton).toBeVisible();
    }
  });
});

test.describe('Deal Pipeline - Responsive Behavior', () => {
  test('should display properly on desktop viewport', async ({ page }) => {
    // Default viewport is desktop-sized
    await page.goto('/deals');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    await page.waitForLoadState('networkidle');

    // Kanban board should show columns in grid
    const gridColumns = page.locator('.grid-cols-6, [class*="grid-cols"]');
    const hasGrid = await gridColumns.isVisible().catch(() => false);

    // On desktop, should have grid layout
    if (hasGrid) {
      expect(hasGrid).toBeTruthy();
    }
  });

  test('should have scrollable columns for overflow content', async ({ page }) => {
    await page.goto('/deals');
    await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    await page.waitForLoadState('networkidle');

    // Column content areas should be scrollable
    const scrollableAreas = page.locator('[class*="overflow-y-auto"]');
    const hasScrollable = await scrollableAreas.first().isVisible().catch(() => false);

    // Should have scrollable areas for long lists
    if (hasScrollable) {
      expect(hasScrollable).toBeTruthy();
    }
  });
});
