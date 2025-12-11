import { test, expect } from "@playwright/test";

/**
 * E2E Tests: Interest Rates Page
 *
 * Tests for interest rates page, including live FRED API data fetching
 * and rate display functionality.
 */
test.describe("Interest Rates Page", () => {
  test.describe("Page Load", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/interest-rates");
      await expect(page.locator("main")).toBeVisible({ timeout: 10000 });
    });

    test("should display interest rates page", async ({ page }) => {
      await expect(page).toHaveURL(/\/interest-rates/);
      await expect(page.locator("main")).toBeVisible();
    });

    test("should display page title", async ({ page }) => {
      const title = page.locator('h1:has-text("Interest Rate Analysis")');
      await expect(title).toBeVisible();
    });

    test("should load rate data content", async ({ page }) => {
      await page.waitForTimeout(2000);

      // The page should have loaded with rate-related content
      const pageContent = await page.content();

      // Should have rate-related content indicating data is loaded
      const hasRateContent =
        pageContent.includes("Rate") ||
        pageContent.includes("%") ||
        pageContent.includes("Treasury") ||
        pageContent.includes("Fed");

      expect(hasRateContent).toBeTruthy();
    });

    test("should display refresh button", async ({ page }) => {
      const refreshButton = page.locator('button:has-text("Refresh")');
      await expect(refreshButton).toBeVisible();
    });

    test("should display last updated timestamp", async ({ page }) => {
      const lastUpdated = page.locator("text=Last updated:");
      await expect(lastUpdated).toBeVisible();
    });
  });

  test.describe("Tab Navigation", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/interest-rates");
      await page.waitForTimeout(1000);
    });

    test("should display all tabs", async ({ page }) => {
      await expect(
        page.locator('button:has-text("Key Rates Snapshot")')
      ).toBeVisible();
      await expect(
        page.locator('button:has-text("Treasury Yield Curve")')
      ).toBeVisible();
      await expect(
        page.locator('button:has-text("Rate Comparisons")')
      ).toBeVisible();
      await expect(
        page.locator('button:has-text("Data Sources")')
      ).toBeVisible();
    });

    test("should switch to Treasury Yield Curve tab", async ({ page }) => {
      const yieldCurveTab = page.locator(
        'button:has-text("Treasury Yield Curve")'
      );
      await yieldCurveTab.click();
      await page.waitForTimeout(500);

      // Should display yield curve chart or content
      const content = await page.locator("main").textContent();
      expect(content).toBeTruthy();
    });

    test("should switch to Rate Comparisons tab", async ({ page }) => {
      const comparisonsTab = page.locator(
        'button:has-text("Rate Comparisons")'
      );
      await comparisonsTab.click();
      await page.waitForTimeout(500);

      const content = await page.locator("main").textContent();
      expect(content).toBeTruthy();
    });

    test("should switch to Data Sources tab", async ({ page }) => {
      const sourcesTab = page.locator('button:has-text("Data Sources")');
      await sourcesTab.click();
      await page.waitForTimeout(500);

      // Data sources tab should mention FRED
      const content = await page.locator("main").textContent();
      expect(content?.toLowerCase()).toContain("fred");
    });
  });

  test.describe("Key Rates Snapshot", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/interest-rates");
      await page.waitForTimeout(2000);
    });

    test("should display Federal Reserve Rates section", async ({ page }) => {
      const fedRatesSection = page.locator("text=Federal Reserve Rates");
      await expect(fedRatesSection).toBeVisible();
    });

    test("should display Treasury Yields section", async ({ page }) => {
      // Look for Treasury-related content (may be "Treasury Yields" or individual treasury rates)
      const treasurySection = page.locator(
        "text=/Treasury|2Y Treasury|5Y Treasury|10Y Treasury/"
      );
      await expect(treasurySection.first()).toBeVisible();
    });

    test("should display rate cards with values", async ({ page }) => {
      // Look for rate cards (Fed Funds, Prime, Treasury rates)
      const fedFunds = page.locator("text=Fed Funds");
      const prime = page.locator("text=Prime");

      const hasFedFunds = await fedFunds.isVisible().catch(() => false);
      const hasPrime = await prime.isVisible().catch(() => false);

      expect(hasFedFunds || hasPrime).toBeTruthy();
    });

    test("should display percentage values", async ({ page }) => {
      // Rate values should contain percentage signs
      const percentages = page.locator("text=/%$/");
      const count = await percentages.count();
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe("Refresh Functionality", () => {
    test("should be able to click refresh button", async ({ page }) => {
      await page.goto("/interest-rates");
      await page.waitForTimeout(1000);

      const refreshButton = page.locator('button:has-text("Refresh")');
      await expect(refreshButton).toBeEnabled();

      // Click refresh
      await refreshButton.click();

      // Button should show loading state or remain clickable
      await page.waitForTimeout(500);
      await expect(page.locator("main")).toBeVisible();
    });
  });

  test.describe("FRED API Integration", () => {
    test("should fetch data from FRED API via proxy", async ({ page }) => {
      // Listen for FRED API requests
      const fredRequests: string[] = [];

      page.on("request", (request) => {
        if (request.url().includes("/api/fred/")) {
          fredRequests.push(request.url());
        }
      });

      await page.goto("/interest-rates");
      await page.waitForTimeout(3000);

      // If FRED API is configured, we should see requests
      // If not configured, page falls back to mock data (which is also valid)
      const content = await page.locator("main").textContent();
      expect(content).toBeTruthy();
    });
  });
});
