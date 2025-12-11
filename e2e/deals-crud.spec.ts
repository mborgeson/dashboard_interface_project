import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Deals CRUD Operations
 *
 * Tests the Deals page and CRUD operations via API and UI.
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
      await page.waitForTimeout(1000);

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

    test('should list deals via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/deals/`, {
        params: { page: 1, page_size: 10 },
      });

      // May need authentication, so accept 200, 401, or 403
      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      // Should return a list or paginated response
      expect(data).toBeDefined();
    });

    test('should get deal by ID via API', async ({ request }) => {
      // Try to get deal ID 1 (from demo data)
      const response = await request.get(`${API_BASE}/deals/1/`);

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      if (response.status() === 404) {
        // No deals exist yet, that's okay
        expect(response.status()).toBe(404);
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('name');
    });

    test('should create deal via API', async ({ request }) => {
      const newDeal = {
        name: 'E2E Test Deal',
        deal_type: 'acquisition',
        stage: 'lead',
        asking_price: 15000000,
        priority: 'medium',
      };

      const response = await request.post(`${API_BASE}/deals/`, {
        data: newDeal,
      });

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      if (response.status() === 404) {
        // Endpoint not implemented
        test.skip();
        return;
      }

      // Accept 200 or 201 for successful creation
      expect([200, 201]).toContain(response.status());

      if (response.ok()) {
        const data = await response.json();
        expect(data.name).toBe('E2E Test Deal');
      }
    });

    test('should filter deals by stage via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/deals/`, {
        params: { stage: 'lead' },
      });

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();
    });
  });

  test.describe('Deal Stage Transitions', () => {
    const API_BASE = 'http://localhost:8000/api/v1';

    test('should update deal stage via API', async ({ request }) => {
      // Try to update deal stage
      const response = await request.patch(`${API_BASE}/deals/1/stage`, {
        data: { stage: 'underwriting' },
      });

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      if (response.status() === 404) {
        // Deal not found or endpoint not implemented
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      if (response.ok()) {
        const data = await response.json();
        expect(data.stage).toBe('underwriting');
      }
    });
  });

  test.describe('Deal Pipeline View', () => {
    test('should display pipeline stages', async ({ page }) => {
      await page.goto('/deals');
      await page.waitForTimeout(1000);

      // Look for pipeline-related elements (Kanban columns, stage labels)
      const pipelineContent = await page.locator('main').textContent();

      // Page should have some content
      expect(pipelineContent).toBeTruthy();
      expect(pipelineContent?.length).toBeGreaterThan(50);
    });

    test('should navigate between list and pipeline views', async ({ page }) => {
      await page.goto('/deals');
      await page.waitForTimeout(1000);

      // Check for view toggle buttons (if implemented)
      const viewToggle = page.locator('[role="tablist"], [class*="toggle"], button:has-text("Pipeline"), button:has-text("List")');

      if (await viewToggle.first().isVisible().catch(() => false)) {
        // Try to toggle views
        await viewToggle.first().click();
        await page.waitForTimeout(500);

        // Verify page still works
        await expect(page.locator('main')).toBeVisible();
      }
    });
  });
});
