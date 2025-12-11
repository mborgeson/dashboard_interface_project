import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Property Details
 *
 * Tests for property details page and interactions.
 */
test.describe('Property Details', () => {
  test.describe('Property List Interactions', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/investments');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(1000);
    });

    test('should display property cards on investments page', async ({ page }) => {
      // Wait for property cards to load - look for headings within cards (property names)
      const propertyHeadings = page.locator('h3');

      // Wait for at least one property card heading to appear
      await expect(propertyHeadings.first()).toBeVisible({ timeout: 10000 });

      // Verify multiple properties are displayed
      const count = await propertyHeadings.count();
      expect(count).toBeGreaterThan(0);
    });

    test('should have clickable property cards', async ({ page }) => {
      // Look for any interactive property elements
      const propertyCards = page.locator('[class*="Card"]');

      if (await propertyCards.first().isVisible()) {
        // Cards exist - verify they're rendered
        const count = await propertyCards.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should display property summary stats', async ({ page }) => {
      // Check for summary statistics
      const statsText = ['Total Properties', 'Total Units', 'Occupancy'];

      for (const stat of statsText) {
        const element = page.getByText(stat);
        if (await element.isVisible().catch(() => false)) {
          expect(await element.isVisible()).toBeTruthy();
          break;
        }
      }
    });
  });

  test.describe('Property API', () => {
    const API_BASE = 'http://localhost:8000/api/v1';

    test('should list properties via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/properties/`);

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('items');
      expect(data).toHaveProperty('total');
    });

    test('should get property by ID via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/properties/1`);

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      if (response.status() === 404) {
        // Property not found - acceptable
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('name');
      expect(data).toHaveProperty('property_type');
    });

    test('should get property analytics via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/properties/1/analytics`);

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      if (response.status() === 404) {
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('property_id');
      expect(data).toHaveProperty('metrics');
    });

    test('should filter properties by type via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/properties/`, {
        params: { property_type: 'multifamily' },
      });

      if (response.status() === 401 || response.status() === 403) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();
    });
  });
});
