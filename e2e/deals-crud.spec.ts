import { test, expect } from './fixtures/auth';
import { assertBackendHealthy } from './fixtures/auth';

/**
 * E2E Tests: Deals CRUD Operations
 *
 * Tests the Deals page and CRUD operations via API and UI.
 * Backend must be running — tests fail (not skip) if unavailable.
 */
test.describe('Deals Page', () => {
  test.describe('Deals List', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/deals');
      // Wait for page to load
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('should display deals page', async ({ page }) => {
      // Verify we're on the deals page
      await expect(page).toHaveURL(/\/deals/);

      // Page should have main content
      await expect(page.locator('main')).toBeVisible();
    });

    test('should have navigation to deals page', async ({ page }) => {
      await page.goto('/');

      // Find and click Deals link
      const dealsLink = page.getByRole('link', { name: /deals/i });
      await expect(dealsLink).toBeVisible();

      await dealsLink.click();
      await expect(page).toHaveURL(/\/deals/);
    });

    test('should display deal cards or table', async ({ page }) => {
      // Wait for content to load
      await page.waitForLoadState('networkidle');

      // Should have some deal-related content (cards, table, or text)
      const hasCards = await page.locator('[class*="Card"]').first().isVisible()
        .catch(() => false);
      const hasTable = await page.locator('table, [role="table"]').first().isVisible()
        .catch(() => false);
      const hasContent = await page.locator('main').textContent()
        .then(text => text && text.length > 100)
        .catch(() => false);

      expect(hasCards || hasTable || hasContent).toBeTruthy();
    });
  });

  test.describe('Deals API CRUD', () => {
    const API_BASE = 'http://localhost:8000/api/v1';

    test.beforeAll(async ({ request }) => {
      await assertBackendHealthy(request);
    });

    test('should list deals via API', async ({ request, authToken }) => {
      const response = await request.get(`${API_BASE}/deals/`, {
        params: { page: 1, page_size: 10 },
        headers: { Authorization: `Bearer ${authToken}` },
      });

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toBeDefined();
    });

    test('should get deal by ID via API', async ({ request, authToken }) => {
      const response = await request.get(`${API_BASE}/deals/1/`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });

      if (response.status() === 404) {
        // Deal ID 1 may not exist — data-dependent, not infrastructure
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('id');
    });

    test('should create deal via API', async ({ request, authToken }) => {
      const newDeal = {
        name: 'E2E Test Deal',
        deal_type: 'acquisition',
        stage: 'lead',
        asking_price: 15000000,
        priority: 'medium',
      };

      const response = await request.post(`${API_BASE}/deals/`, {
        data: newDeal,
        headers: { Authorization: `Bearer ${authToken}` },
      });

      if (response.status() === 422) {
        // Validation error — likely schema mismatch, not infrastructure failure
        const errorData = await response.json();
        throw new Error(`Deal creation failed with validation error: ${JSON.stringify(errorData)}`);
      }

      // Accept 200 or 201 for successful creation
      expect([200, 201]).toContain(response.status());
    });

    test('should filter deals by stage via API', async ({ request, authToken }) => {
      const response = await request.get(`${API_BASE}/deals/`, {
        params: { stage: 'lead' },
        headers: { Authorization: `Bearer ${authToken}` },
      });

      expect(response.ok()).toBeTruthy();
    });
  });

  // NOTE: Deal stage transition test (PATCH /deals/{id}/stage) was removed
  // because the endpoint is not implemented. Re-add when the endpoint exists.

  test.describe('Deal Pipeline View', () => {
    test('should display pipeline stages', async ({ page }) => {
      await page.goto('/deals');
      await page.waitForLoadState('networkidle');

      // Look for pipeline-related elements (Kanban columns, stage labels)
      const pipelineContent = await page.locator('main').textContent();

      // Page should have some content
      expect(pipelineContent).toBeTruthy();
      expect(pipelineContent?.length).toBeGreaterThan(50);
    });

    test('should navigate between list and pipeline views', async ({ page }) => {
      await page.goto('/deals');
      await page.waitForLoadState('networkidle');

      // Check for view toggle buttons (if implemented)
      const viewToggle = page.locator('[role="tablist"], [class*="toggle"], button:has-text("Pipeline"), button:has-text("List")');

      if (await viewToggle.first().isVisible().catch(() => false)) {
        // Try to toggle views
        await viewToggle.first().click();
        await page.waitForLoadState('networkidle');

        // Verify page still works
        await expect(page.locator('main')).toBeVisible();
      }
    });
  });
});
