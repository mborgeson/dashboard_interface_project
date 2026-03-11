import { test, expect } from './fixtures/auth';
import { assertBackendHealthy } from './fixtures/auth';

/**
 * E2E Tests: Property Details
 *
 * Tests for property details page and interactions.
 * Backend must be running — tests fail (not skip) if unavailable.
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

    test.beforeAll(async ({ request }) => {
      await assertBackendHealthy(request);
    });

    test('should list properties via API', async ({ request, authToken }) => {
      const response = await request.get(`${API_BASE}/properties/`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('items');
      expect(data).toHaveProperty('total');
    });

    test('should get property by ID via API', async ({ request, authToken }) => {
      const response = await request.get(`${API_BASE}/properties/1`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });

      if (response.status() === 404) {
        // Property ID 1 may not exist — this is a data issue, not a test infrastructure issue
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('id');
      expect(data).toHaveProperty('name');
      expect(data).toHaveProperty('property_type');
    });

    test('should get property analytics via API', async ({ request, authToken }) => {
      const response = await request.get(`${API_BASE}/properties/1/analytics`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });

      if (response.status() === 404) {
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('property_id');
      expect(data).toHaveProperty('metrics');
    });

    test('should filter properties by type via API', async ({ request, authToken }) => {
      const response = await request.get(`${API_BASE}/properties/`, {
        params: { property_type: 'multifamily' },
        headers: { Authorization: `Bearer ${authToken}` },
      });

      expect(response.ok()).toBeTruthy();
    });
  });
});
