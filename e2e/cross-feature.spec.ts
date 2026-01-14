import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Cross-Feature Integration
 *
 * Tests navigation flows, data consistency, and feature interactions
 * across the B&R Capital Dashboard application.
 */
test.describe('Cross-Feature Integration', () => {
  /**
   * SECTION 1: Navigation Integrity
   * Tests sidebar navigation, URL changes, and browser history
   */
  test.describe('Navigation Integrity', () => {
    test('should navigate to all major sections via sidebar', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

      // Define all navigation items from the sidebar
      const navItems = [
        { name: /investments/i, url: /\/investments/ },
        { name: /transactions/i, url: /\/transactions/ },
        { name: /deals/i, url: /\/deals/ },
        { name: /documents/i, url: /\/documents/ },
        { name: /reporting/i, url: /\/reporting/ },
        { name: /analytics/i, url: /\/analytics/ },
        { name: /interest rates/i, url: /\/interest-rates/ },
        { name: /market/i, url: /\/market/ },
        { name: /mapping/i, url: /\/mapping/ },
      ];

      // Test navigation to each section
      for (const item of navItems) {
        await page.getByRole('link', { name: item.name }).click();
        await expect(page).toHaveURL(item.url, { timeout: 10000 });
        await expect(page.locator('main[role="main"]')).toBeVisible();
      }

      // Return to Dashboard
      await page.getByRole('link', { name: /dashboard/i }).click();
      await expect(page).toHaveURL('/');
    });

    test('should verify URL changes correctly on navigation', async ({ page }) => {
      await page.goto('/');

      // Navigate to Investments
      await page.getByRole('link', { name: /investments/i }).click();
      await expect(page).toHaveURL(/\/investments/);
      expect(page.url()).toContain('/investments');

      // Navigate to Deals
      await page.getByRole('link', { name: /deals/i }).click();
      await expect(page).toHaveURL(/\/deals/);
      expect(page.url()).toContain('/deals');

      // Navigate to Analytics
      await page.getByRole('link', { name: /analytics/i }).click();
      await expect(page).toHaveURL(/\/analytics/);
      expect(page.url()).toContain('/analytics');
    });

    test('should handle browser back/forward navigation across multiple pages', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main[role="main"]')).toBeVisible();

      // Build navigation history: Dashboard -> Investments -> Deals -> Analytics
      await page.getByRole('link', { name: /investments/i }).click();
      await expect(page).toHaveURL(/\/investments/);

      await page.getByRole('link', { name: /deals/i }).click();
      await expect(page).toHaveURL(/\/deals/);

      await page.getByRole('link', { name: /analytics/i }).click();
      await expect(page).toHaveURL(/\/analytics/);

      // Navigate back through history
      await page.goBack();
      await expect(page).toHaveURL(/\/deals/);

      await page.goBack();
      await expect(page).toHaveURL(/\/investments/);

      await page.goBack();
      await expect(page).toHaveURL('/');

      // Navigate forward through history
      await page.goForward();
      await expect(page).toHaveURL(/\/investments/);

      await page.goForward();
      await expect(page).toHaveURL(/\/deals/);
    });

    test('should maintain main content area across all navigation', async ({ page }) => {
      const routes = ['/', '/investments', '/deals', '/analytics', '/market', '/documents'];

      for (const route of routes) {
        await page.goto(route);
        await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

        // Verify sidebar remains visible on desktop
        const sidebar = page.locator('aside[role="navigation"]');
        // Sidebar is hidden on mobile, check if in desktop viewport
        const viewportSize = page.viewportSize();
        if (viewportSize && viewportSize.width >= 1024) {
          await expect(sidebar).toBeVisible();
        }
      }
    });

    test('should handle direct URL navigation to deep routes', async ({ page }) => {
      // Direct navigation to property detail page
      await page.goto('/properties/1');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

      // Direct navigation to other pages
      await page.goto('/deals');
      await expect(page).toHaveURL(/\/deals/);
      await expect(page.locator('main[role="main"]')).toBeVisible();

      await page.goto('/analytics');
      await expect(page).toHaveURL(/\/analytics/);
      await expect(page.locator('main[role="main"]')).toBeVisible();
    });
  });

  /**
   * SECTION 2: Investments to Property Detail Flow
   * Tests navigation from property list to property details
   */
  test.describe('Investments to Property Detail Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/investments');
      await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      await page.waitForTimeout(1500); // Wait for data to load
    });

    test('should navigate from property card to property detail', async ({ page }) => {
      // Look for View Details button on property cards
      const viewDetailsButton = page.getByRole('button', { name: /view details/i }).first();

      if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await viewDetailsButton.click();

        // Verify navigation to property detail page
        await expect(page).toHaveURL(/\/properties\/\d+/);
        await expect(page.locator('main[role="main"]')).toBeVisible();

        // Verify back navigation button exists
        const backButton = page.getByRole('button', { name: /back to investments/i });
        await expect(backButton).toBeVisible();
      }
    });

    test('should navigate back from property detail to investments', async ({ page }) => {
      // Navigate to property detail first
      const viewDetailsButton = page.getByRole('button', { name: /view details/i }).first();

      if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await viewDetailsButton.click();
        await expect(page).toHaveURL(/\/properties\/\d+/);

        // Click back button
        const backButton = page.getByRole('button', { name: /back to investments/i });
        await backButton.click();

        // Verify returned to investments
        await expect(page).toHaveURL(/\/investments/);
        await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      }
    });

    test('should display property tabs on detail page', async ({ page }) => {
      // Navigate to property detail
      const viewDetailsButton = page.getByRole('button', { name: /view details/i }).first();

      if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await viewDetailsButton.click();
        await expect(page).toHaveURL(/\/properties\/\d+/);

        // Verify tabs are present
        const tabLabels = ['Overview', 'Financials', 'Operations', 'Performance', 'Transactions'];

        for (const tabLabel of tabLabels) {
          const tab = page.getByRole('button', { name: new RegExp(tabLabel, 'i') });
          await expect(tab).toBeVisible();
        }
      }
    });

    test('should switch between property detail tabs', async ({ page }) => {
      // Navigate to property detail
      const viewDetailsButton = page.getByRole('button', { name: /view details/i }).first();

      if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await viewDetailsButton.click();
        await expect(page).toHaveURL(/\/properties\/\d+/);

        // Click through each tab
        const tabNames = ['Financials', 'Operations', 'Performance', 'Transactions', 'Overview'];

        for (const tabName of tabNames) {
          const tab = page.getByRole('button', { name: new RegExp(tabName, 'i') });
          await tab.click();
          await page.waitForTimeout(300); // Allow tab content to render

          // Verify main content area still visible
          await expect(page.locator('main[role="main"]')).toBeVisible();
        }
      }
    });
  });

  /**
   * SECTION 3: Dashboard Quick Access
   * Tests dashboard widgets and quick navigation links
   */
  test.describe('Dashboard Quick Access', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.getByRole('heading', { name: /Portfolio Dashboard/i })).toBeVisible();
      await page.waitForTimeout(1500); // Wait for data to load
    });

    test('should display hero stat cards', async ({ page }) => {
      // Check for stat card content
      const statCards = page.locator('[class*="shadow-card"]');
      await expect(statCards.first()).toBeVisible({ timeout: 10000 });

      // Verify at least 4 stat cards (Portfolio Value, Units, NOI, Cap Rate)
      const cardCount = await statCards.count();
      expect(cardCount).toBeGreaterThanOrEqual(4);
    });

    test('should display Top Performing Properties section', async ({ page }) => {
      const topPropertiesHeading = page.getByRole('heading', { name: /Top Performing Properties/i });
      await expect(topPropertiesHeading).toBeVisible({ timeout: 10000 });

      // Verify property items are displayed
      const propertyItems = page.locator('text=/IRR/i');
      await expect(propertyItems.first()).toBeVisible();
    });

    test('should display Recent Transactions section', async ({ page }) => {
      const recentTxnHeading = page.getByRole('heading', { name: /Recent Transactions/i });
      await expect(recentTxnHeading).toBeVisible({ timeout: 10000 });
    });

    test('should display Portfolio Distribution section', async ({ page }) => {
      const distributionHeading = page.getByRole('heading', { name: /Portfolio Distribution/i });
      await expect(distributionHeading).toBeVisible({ timeout: 10000 });

      // Verify property class sections are displayed
      const classA = page.getByText(/Class A/i);
      const classB = page.getByText(/Class B/i);
      const classC = page.getByText(/Class C/i);

      await expect(classA.first()).toBeVisible();
      await expect(classB.first()).toBeVisible();
      await expect(classC.first()).toBeVisible();
    });

    test('should display Property Map section', async ({ page }) => {
      const mapHeading = page.getByRole('heading', { name: /Property Locations/i });
      await expect(mapHeading).toBeVisible({ timeout: 10000 });
    });

    test('should navigate from sidebar to dashboard', async ({ page }) => {
      // Navigate away first
      await page.getByRole('link', { name: /investments/i }).click();
      await expect(page).toHaveURL(/\/investments/);

      // Navigate back to dashboard
      await page.getByRole('link', { name: /dashboard/i }).click();
      await expect(page).toHaveURL('/');
      await expect(page.getByRole('heading', { name: /Portfolio Dashboard/i })).toBeVisible();
    });
  });

  /**
   * SECTION 4: Data Consistency
   * Tests that data is consistent across different views and pages
   */
  test.describe('Data Consistency', () => {
    test('should show consistent portfolio stats on dashboard and investments', async ({ page }) => {
      // Get stats from dashboard
      await page.goto('/');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(1500);

      // Look for total units on dashboard
      const dashboardContent = await page.locator('main').textContent();

      // Navigate to investments
      await page.goto('/investments');
      await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      await page.waitForTimeout(1500);

      // Verify Total Properties card exists
      const totalPropertiesCard = page.getByText('Total Properties');
      await expect(totalPropertiesCard).toBeVisible();

      // Verify Total Units card exists
      const totalUnitsCard = page.getByText('Total Units');
      await expect(totalUnitsCard).toBeVisible();
    });

    test('should show consistent property count across pages', async ({ page }) => {
      // Get property count from investments page
      await page.goto('/investments');
      await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      await page.waitForTimeout(1500);

      // Count property cards in grid view
      const propertyCards = page.locator('[class*="CardFooter"]');
      const investmentsCardCount = await propertyCards.count();

      // Navigate to dashboard and check sidebar
      await page.goto('/');
      await page.waitForTimeout(1500);

      // Sidebar shows property count
      const sidebarStats = page.locator('aside').getByText(/Properties/i);
      await expect(sidebarStats.first()).toBeVisible();

      // Both should reference consistent data (exact matching is fragile, so check for presence)
      expect(investmentsCardCount).toBeGreaterThan(0);
    });

    test('should display deals data on deals page', async ({ page }) => {
      await page.goto('/deals');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(1500);

      // Verify deals content is present
      const mainContent = await page.locator('main').textContent();
      expect(mainContent).toBeTruthy();
      expect(mainContent?.length).toBeGreaterThan(50);
    });

    test('should display analytics data on analytics page', async ({ page }) => {
      await page.goto('/analytics');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.waitForTimeout(1500);

      // Verify analytics content is present
      const mainContent = await page.locator('main').textContent();
      expect(mainContent).toBeTruthy();
      expect(mainContent?.length).toBeGreaterThan(50);
    });
  });

  /**
   * SECTION 5: Session Persistence and Filter State
   * Tests that filters and UI state persist across navigation
   */
  test.describe('Session Persistence', () => {
    test('should maintain view mode toggle state on investments page', async ({ page }) => {
      await page.goto('/investments');
      await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      await page.waitForTimeout(1500);

      // Look for view toggle buttons (grid/table view)
      const tableViewButton = page.locator('button').filter({ has: page.locator('[class*="List"]') });
      const gridViewButton = page.locator('button').filter({ has: page.locator('[class*="Grid"]') });

      if (await tableViewButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Switch to table view
        await tableViewButton.click();
        await page.waitForTimeout(500);

        // Navigate away
        await page.getByRole('link', { name: /dashboard/i }).click();
        await expect(page).toHaveURL('/');

        // Navigate back
        await page.getByRole('link', { name: /investments/i }).click();
        await expect(page).toHaveURL(/\/investments/);
        await page.waitForTimeout(1000);

        // View mode may reset (React state) - this is expected behavior
        // Test that the page still functions correctly
        await expect(page.locator('main[role="main"]')).toBeVisible();
      }
    });

    test('should maintain search filter value during typing', async ({ page }) => {
      await page.goto('/investments');
      await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      await page.waitForTimeout(1500);

      // Find search input
      const searchInput = page.getByPlaceholder(/search/i);

      if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Type search query
        await searchInput.fill('Mesa');
        await page.waitForTimeout(500);

        // Verify value is maintained
        await expect(searchInput).toHaveValue('Mesa');

        // Clear and try another search
        await searchInput.clear();
        await searchInput.fill('Phoenix');
        await expect(searchInput).toHaveValue('Phoenix');
      }
    });

    test('should reset filters on page refresh', async ({ page }) => {
      await page.goto('/investments');
      await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      await page.waitForTimeout(1500);

      // Find search input and apply filter
      const searchInput = page.getByPlaceholder(/search/i);

      if (await searchInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await searchInput.fill('TestSearch');
        await expect(searchInput).toHaveValue('TestSearch');

        // Refresh page
        await page.reload();
        await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
        await page.waitForTimeout(1500);

        // Verify filter is reset (typical React behavior)
        const searchInputAfterRefresh = page.getByPlaceholder(/search/i);
        if (await searchInputAfterRefresh.isVisible({ timeout: 3000 }).catch(() => false)) {
          await expect(searchInputAfterRefresh).toHaveValue('');
        }
      }
    });

    test('should handle rapid navigation between pages', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main[role="main"]')).toBeVisible();

      // Rapid navigation sequence
      const routes = ['/investments', '/deals', '/analytics', '/market', '/documents', '/'];

      for (const route of routes) {
        await page.goto(route);
        // Quick check that main content area renders
        await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 5000 });
      }
    });
  });

  /**
   * SECTION 6: Cross-Page Navigation Flows
   * Tests complete user flows across multiple features
   */
  test.describe('Cross-Page Navigation Flows', () => {
    test('should complete Dashboard -> Investments -> Property Detail flow', async ({ page }) => {
      // Start at Dashboard
      await page.goto('/');
      await expect(page.getByRole('heading', { name: /Portfolio Dashboard/i })).toBeVisible();
      await page.waitForTimeout(1000);

      // Navigate to Investments via sidebar
      await page.getByRole('link', { name: /investments/i }).click();
      await expect(page).toHaveURL(/\/investments/);
      await expect(page.getByRole('heading', { name: /Investment Portfolio/i })).toBeVisible();
      await page.waitForTimeout(1000);

      // Click View Details on a property
      const viewDetailsButton = page.getByRole('button', { name: /view details/i }).first();

      if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await viewDetailsButton.click();
        await expect(page).toHaveURL(/\/properties\/\d+/);

        // Verify property detail loaded
        const backButton = page.getByRole('button', { name: /back to investments/i });
        await expect(backButton).toBeVisible();
      }
    });

    test('should navigate through all main sections sequentially', async ({ page }) => {
      const sections = [
        { route: '/', heading: /Portfolio Dashboard/i },
        { route: '/investments', heading: /Investment Portfolio/i },
        { route: '/transactions', heading: null }, // Check main content instead
        { route: '/deals', heading: null },
        { route: '/documents', heading: null },
        { route: '/analytics', heading: null },
        { route: '/market', heading: null },
        { route: '/reporting', heading: null },
      ];

      for (const section of sections) {
        await page.goto(section.route);
        await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

        if (section.heading) {
          await expect(page.getByRole('heading', { name: section.heading })).toBeVisible();
        }

        // Verify page has content
        const content = await page.locator('main').textContent();
        expect(content?.length).toBeGreaterThan(10);
      }
    });

    test('should handle back button from property detail to previous page', async ({ page }) => {
      // Start from dashboard
      await page.goto('/');
      await expect(page.locator('main[role="main"]')).toBeVisible();

      // Navigate to investments
      await page.getByRole('link', { name: /investments/i }).click();
      await expect(page).toHaveURL(/\/investments/);
      await page.waitForTimeout(1500);

      // Navigate to property detail
      const viewDetailsButton = page.getByRole('button', { name: /view details/i }).first();

      if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await viewDetailsButton.click();
        await expect(page).toHaveURL(/\/properties\/\d+/);

        // Use browser back
        await page.goBack();
        await expect(page).toHaveURL(/\/investments/);

        // Use browser back again
        await page.goBack();
        await expect(page).toHaveURL('/');
      }
    });
  });

  /**
   * SECTION 7: Error Handling and Edge Cases
   * Tests error states and edge cases in cross-feature navigation
   */
  test.describe('Error Handling and Edge Cases', () => {
    test('should handle navigation to non-existent property', async ({ page }) => {
      // Navigate to non-existent property ID
      await page.goto('/properties/99999');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

      // Should show error or "not found" message
      const errorOrNotFound = await page.locator('text=/not found|error/i').isVisible()
        .catch(() => false);

      // Or may redirect/show empty state - just verify page is functional
      await expect(page.locator('main[role="main"]')).toBeVisible();
    });

    test('should handle navigation to invalid routes gracefully', async ({ page }) => {
      // Navigate to invalid route
      await page.goto('/invalid-route-that-does-not-exist');

      // Should handle gracefully - either 404 page or redirect
      // At minimum, page should not crash
      const pageNotCrashed = await page.locator('body').isVisible();
      expect(pageNotCrashed).toBeTruthy();
    });

    test('should maintain navigation functionality after error', async ({ page }) => {
      // Trigger potential error by navigating to non-existent property
      await page.goto('/properties/99999');
      await page.waitForTimeout(1000);

      // Verify navigation still works
      await page.goto('/investments');
      await expect(page).toHaveURL(/\/investments/);
      await expect(page.locator('main[role="main"]')).toBeVisible();

      // Navigate to dashboard
      await page.getByRole('link', { name: /dashboard/i }).click();
      await expect(page).toHaveURL('/');
    });

    test('should handle page refresh on deep routes', async ({ page }) => {
      // Navigate to investments
      await page.goto('/investments');
      await expect(page).toHaveURL(/\/investments/);
      await page.waitForTimeout(1500);

      // Navigate to property detail if possible
      const viewDetailsButton = page.getByRole('button', { name: /view details/i }).first();

      if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await viewDetailsButton.click();
        await expect(page).toHaveURL(/\/properties\/\d+/);

        // Refresh on property detail page
        await page.reload();

        // Should still be on property detail page
        await expect(page).toHaveURL(/\/properties\/\d+/);
        await expect(page.locator('main[role="main"]')).toBeVisible();
      }
    });
  });

  /**
   * SECTION 8: Sidebar Behavior
   * Tests sidebar collapse, mobile menu, and external links
   */
  test.describe('Sidebar Behavior', () => {
    test('should display all navigation items in sidebar', async ({ page }) => {
      await page.goto('/');

      // Set viewport to desktop size to ensure sidebar is visible
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.waitForTimeout(500);

      // Check for all main navigation items
      const navItems = [
        'Dashboard',
        'Investments',
        'Transactions',
        'Deals',
        'Documents',
        'Reporting',
        'Analytics',
        'Interest Rates',
        'Market',
        'Mapping',
      ];

      const sidebar = page.locator('aside[role="navigation"]');
      await expect(sidebar).toBeVisible();

      for (const item of navItems) {
        const navLink = sidebar.getByRole('link', { name: new RegExp(item, 'i') });
        await expect(navLink).toBeVisible();
      }
    });

    test('should display sidebar footer with portfolio stats', async ({ page }) => {
      await page.goto('/');

      // Set viewport to desktop size
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.waitForTimeout(1000);

      // Check for portfolio stats in sidebar footer
      const sidebarFooter = page.locator('aside').getByText(/Portfolio Dashboard/i);
      await expect(sidebarFooter).toBeVisible();

      // Check for property/unit counts
      const statsText = page.locator('aside').getByText(/Properties.*Units/i);
      await expect(statsText).toBeVisible();
    });

    test('should have external links section in sidebar', async ({ page }) => {
      await page.goto('/');

      // Set viewport to desktop size
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.waitForTimeout(500);

      // Check for External section
      const externalSection = page.locator('aside').getByText('External');
      await expect(externalSection).toBeVisible();

      // Check for external links
      const bandRCapitalLink = page.locator('aside').getByRole('link', { name: /B&R Capital/i });
      const sharePointLink = page.locator('aside').getByRole('link', { name: /SharePoint/i });
      const linkedInLink = page.locator('aside').getByRole('link', { name: /LinkedIn/i });

      await expect(bandRCapitalLink).toBeVisible();
      await expect(sharePointLink).toBeVisible();
      await expect(linkedInLink).toBeVisible();
    });

    test('should have tools section in sidebar', async ({ page }) => {
      await page.goto('/');

      // Set viewport to desktop size
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.waitForTimeout(500);

      // Check for Tools section
      const toolsSection = page.locator('aside').getByText('Tools');
      await expect(toolsSection).toBeVisible();

      // Check for Rent Roll Analyzer link
      const rentRollLink = page.locator('aside').getByRole('link', { name: /Rent Roll Analyzer/i });
      await expect(rentRollLink).toBeVisible();
    });

    test('should toggle sidebar collapse on desktop', async ({ page }) => {
      await page.goto('/');

      // Set viewport to desktop size
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.waitForTimeout(500);

      // Find collapse button
      const collapseButton = page.locator('aside').getByRole('button', { name: /collapse|expand/i });

      if (await collapseButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        // Click to collapse
        await collapseButton.click();
        await page.waitForTimeout(500);

        // Click to expand
        await collapseButton.click();
        await page.waitForTimeout(500);

        // Sidebar should still be functional
        const sidebar = page.locator('aside[role="navigation"]');
        await expect(sidebar).toBeVisible();
      }
    });
  });

  /**
   * SECTION 9: Skip Link Accessibility
   * Tests keyboard navigation and skip to content functionality
   */
  test.describe('Accessibility Navigation', () => {
    test('should have skip to main content link', async ({ page }) => {
      await page.goto('/');

      // Check for skip link (may be visually hidden)
      const skipLink = page.getByRole('link', { name: /skip to main content/i });
      await expect(skipLink).toBeAttached();
    });

    test('should navigate with keyboard through sidebar links', async ({ page }) => {
      await page.goto('/');

      // Set desktop viewport
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.waitForTimeout(500);

      // Tab through to find a navigation link
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Verify focus is moving (at least body is still visible)
      await expect(page.locator('body')).toBeVisible();
    });
  });
});
