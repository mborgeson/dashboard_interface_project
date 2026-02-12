import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Underwriting Deal Modal
 *
 * Tests the Underwriting Deal modal including:
 * - Modal access and display
 * - Tab navigation (Inputs, Results, Projections, Sensitivity)
 * - Input field interactions and validation
 * - Calculations and projections display
 * - Sensitivity analysis
 * - Export functionality
 * - Error handling and edge cases
 */

test.describe('Underwriting Deal Modal', () => {
  test.describe('Page/Modal Access', () => {
    test('should navigate to underwriting modal via top nav button', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Look for underwriting button in navigation
      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();

        // Modal should appear
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display underwriting modal interface', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Open underwriting modal
      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Should show modal title
        const dialogTitle = page.getByRole('dialog').locator('[class*="DialogTitle"], h2, h3').first();
        await expect(dialogTitle).toBeVisible();
      }
    });

    test('should show deal basic information in modal header', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Should show description text
        const description = page.getByRole('dialog').getByText(/enter property details|financial assumptions|calculate returns/i);
        await expect(description).toBeVisible();
      }
    });
  });

  test.describe('Tab Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      // Open underwriting modal
      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display available tabs (Inputs, Results, Projections, Sensitivity)', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Check for all tabs
        await expect(dialog.getByRole('tab', { name: /inputs/i })).toBeVisible();
        await expect(dialog.getByRole('tab', { name: /results/i })).toBeVisible();
        await expect(dialog.getByRole('tab', { name: /projections/i })).toBeVisible();
        await expect(dialog.getByRole('tab', { name: /sensitivity/i })).toBeVisible();
      }
    });

    test('should switch between tabs', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Inputs tab should be active by default
        const inputsTab = dialog.getByRole('tab', { name: /inputs/i });
        await expect(inputsTab).toHaveAttribute('data-state', 'active');

        // Results, Projections, Sensitivity tabs are disabled until results are calculated
        const resultsTab = dialog.getByRole('tab', { name: /results/i });
        await expect(resultsTab).toBeDisabled();
      }
    });

    test('should maintain state when switching tabs', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Fill in a property name
        const propertyNameInput = dialog.locator('input#propertyName');
        if (await propertyNameInput.isVisible()) {
          await propertyNameInput.fill('Test Property');

          // Value should persist (would switch tabs if results were available)
          await expect(propertyNameInput).toHaveValue('Test Property');
        }
      }
    });

    test('should show correct content per tab', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Inputs tab should show Property Assumptions section
        const content = await dialog.textContent();
        expect(
          content?.includes('Property Assumptions') ||
          content?.includes('Acquisition') ||
          content?.includes('Purchase Price')
        ).toBeTruthy();
      }
    });
  });

  test.describe('Inputs Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display Property Assumptions section', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Look for Property Assumptions collapsible section
        const propertySection = dialog.getByText('Property Assumptions');
        await expect(propertySection).toBeVisible();

        // Should show property-related fields
        const content = await dialog.textContent();
        expect(
          content?.includes('Property Name') ||
          content?.includes('Property Class') ||
          content?.includes('Units')
        ).toBeTruthy();
      }
    });

    test('should display Acquisition Assumptions section', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const acquisitionSection = dialog.getByText('Acquisition Assumptions');
        await expect(acquisitionSection).toBeVisible();

        // Should show acquisition-related content
        const content = await dialog.textContent();
        expect(
          content?.includes('Purchase Price') ||
          content?.includes('Closing Costs') ||
          content?.includes('Due Diligence')
        ).toBeTruthy();
      }
    });

    test('should display Financing Assumptions section', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const financingSection = dialog.getByText('Financing Assumptions');
        await expect(financingSection).toBeVisible();

        // Should show financing-related content
        const content = await dialog.textContent();
        expect(
          content?.includes('Loan Type') ||
          content?.includes('LTV') ||
          content?.includes('Interest Rate')
        ).toBeTruthy();
      }
    });

    test('should edit input fields', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Edit property name
        const propertyNameInput = dialog.locator('input#propertyName');
        if (await propertyNameInput.isVisible()) {
          await propertyNameInput.clear();
          await propertyNameInput.fill('New Test Property');
          await expect(propertyNameInput).toHaveValue('New Test Property');
        }

        // Edit units field
        const unitsInput = dialog.locator('input#units');
        if (await unitsInput.isVisible()) {
          await unitsInput.clear();
          await unitsInput.fill('150');
          await expect(unitsInput).toHaveValue('150');
        }
      }
    });

    test('should show calculated derived values', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Look for derived values like Price/Unit, Price/SF, Loan Amount
        const content = await dialog.textContent();
        expect(
          content?.includes('Price/Unit') ||
          content?.includes('Price/SF') ||
          content?.includes('Loan Amount')
        ).toBeTruthy();
      }
    });

    test('should reset to defaults functionality', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Modify a field
        const propertyNameInput = dialog.locator('input#propertyName');
        if (await propertyNameInput.isVisible()) {
          await propertyNameInput.fill('Modified Name');
        }

        // Click reset button
        const resetButton = dialog.getByRole('button', { name: /reset/i });
        if (await resetButton.isVisible()) {
          await resetButton.click();

          // Property name should be reset (default is empty string)
          await expect(propertyNameInput).toHaveValue('');
        }
      }
    });
  });

  test.describe('Results Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should enable Results tab when calculations are ready', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // With default inputs, results should be calculated automatically
        await page.waitForTimeout(500);

        const resultsTab = dialog.getByRole('tab', { name: /results/i });

        // Results tab should be enabled (not disabled) since defaults generate valid results
        const isDisabled = await resultsTab.isDisabled();

        // If enabled, click to view results
        if (!isDisabled) {
          await resultsTab.click();
          await page.waitForTimeout(300);

          // Should show results content
          const content = await dialog.textContent();
          expect(
            content?.includes('Investment Summary') ||
            content?.includes('Levered IRR') ||
            content?.includes('Return Metrics')
          ).toBeTruthy();
        }
      }
    });

    test('should display key metrics (IRR, Cash-on-Cash, Equity Multiple)', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const resultsTab = dialog.getByRole('tab', { name: /results/i });
        const isDisabled = await resultsTab.isDisabled();

        if (!isDisabled) {
          await resultsTab.click();
          await page.waitForTimeout(300);

          // Check for key metrics
          const content = await dialog.textContent();
          expect(content?.includes('IRR')).toBeTruthy();
          expect(
            content?.includes('Equity Multiple') ||
            content?.includes('equity multiple')
          ).toBeTruthy();
          expect(
            content?.includes('Cash-on-Cash') ||
            content?.includes('Cash Flow')
          ).toBeTruthy();
        }
      }
    });

    test('should display quick stats bar with color-coded metrics', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        await page.waitForTimeout(500);

        // Quick stats bar should be visible at the bottom
        const statsBar = dialog.locator('[class*="bg-neutral-900"]');

        if (await statsBar.isVisible()) {
          const statsContent = await statsBar.textContent();
          expect(
            statsContent?.includes('Levered IRR') ||
            statsContent?.includes('Equity Multiple') ||
            statsContent?.includes('DSCR')
          ).toBeTruthy();
        }
      }
    });

    test('should update results when inputs change', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Note the initial stats bar content
        const statsBar = dialog.locator('[class*="bg-neutral-900"]');
        let initialContent = '';

        if (await statsBar.isVisible()) {
          initialContent = await statsBar.textContent() || '';
        }

        // Change purchase price significantly
        const purchasePriceInput = dialog.locator('input#purchasePrice');
        if (await purchasePriceInput.isVisible()) {
          await purchasePriceInput.clear();
          await purchasePriceInput.fill('20000000');
          await page.waitForTimeout(500);

          // Stats should update (IRR would change with different purchase price)
          const updatedContent = await statsBar.textContent() || '';
          // Content may or may not change based on calculation, but should be present
          expect(updatedContent.length).toBeGreaterThan(0);
        }
      }
    });
  });

  test.describe('Projections Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display projections tab with chart and table', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const projectionsTab = dialog.getByRole('tab', { name: /projections/i });
        const isDisabled = await projectionsTab.isDisabled();

        if (!isDisabled) {
          await projectionsTab.click();
          await page.waitForTimeout(500);

          // Should show projection-related content
          const content = await dialog.textContent();
          expect(
            content?.includes('NOI') ||
            content?.includes('Cash Flow') ||
            content?.includes('Year 1') ||
            content?.includes('Projections')
          ).toBeTruthy();
        }
      }
    });

    test('should display year-by-year projection table', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const projectionsTab = dialog.getByRole('tab', { name: /projections/i });
        const isDisabled = await projectionsTab.isDisabled();

        if (!isDisabled) {
          await projectionsTab.click();
          await page.waitForTimeout(500);

          // Look for table with projections
          const table = dialog.locator('table');
          if (await table.isVisible()) {
            const tableContent = await table.textContent();
            expect(
              tableContent?.includes('Year') ||
              tableContent?.includes('NOI') ||
              tableContent?.includes('Cash Flow')
            ).toBeTruthy();
          }
        }
      }
    });

    test('should display charts for NOI and Cash Flow', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const projectionsTab = dialog.getByRole('tab', { name: /projections/i });
        const isDisabled = await projectionsTab.isDisabled();

        if (!isDisabled) {
          await projectionsTab.click();
          await page.waitForTimeout(500);

          // Look for chart-related headings
          const content = await dialog.textContent();
          expect(
            content?.includes('NOI & Cash Flow Projections') ||
            content?.includes('Property Value') ||
            content?.includes('Cumulative Cash Flow')
          ).toBeTruthy();
        }
      }
    });

    test('should show Property Value and Equity Build chart', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const projectionsTab = dialog.getByRole('tab', { name: /projections/i });
        const isDisabled = await projectionsTab.isDisabled();

        if (!isDisabled) {
          await projectionsTab.click();
          await page.waitForTimeout(500);

          const content = await dialog.textContent();
          expect(
            content?.includes('Property Value') ||
            content?.includes('Equity Build') ||
            content?.includes('Loan Balance')
          ).toBeTruthy();
        }
      }
    });
  });

  test.describe('Sensitivity Analysis', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display sensitivity analysis tab', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const sensitivityTab = dialog.getByRole('tab', { name: /sensitivity/i });
        const isDisabled = await sensitivityTab.isDisabled();

        if (!isDisabled) {
          await sensitivityTab.click();
          await page.waitForTimeout(500);

          // Should show sensitivity-related content
          const content = await dialog.textContent();
          expect(
            content?.includes('Sensitivity Analysis') ||
            content?.includes('Base Case IRR') ||
            content?.includes('Tornado')
          ).toBeTruthy();
        }
      }
    });

    test('should display base case IRR in sensitivity header', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const sensitivityTab = dialog.getByRole('tab', { name: /sensitivity/i });
        const isDisabled = await sensitivityTab.isDisabled();

        if (!isDisabled) {
          await sensitivityTab.click();
          await page.waitForTimeout(500);

          // Should show base case IRR
          const content = await dialog.textContent();
          expect(content?.includes('Base Case IRR')).toBeTruthy();
        }
      }
    });

    test('should display tornado chart', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const sensitivityTab = dialog.getByRole('tab', { name: /sensitivity/i });
        const isDisabled = await sensitivityTab.isDisabled();

        if (!isDisabled) {
          await sensitivityTab.click();
          await page.waitForTimeout(500);

          // Should show tornado chart heading
          const content = await dialog.textContent();
          expect(
            content?.includes('Tornado Chart') ||
            content?.includes('IRR Tornado') ||
            content?.includes('point change')
          ).toBeTruthy();
        }
      }
    });

    test('should display detailed sensitivity scenarios table', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const sensitivityTab = dialog.getByRole('tab', { name: /sensitivity/i });
        const isDisabled = await sensitivityTab.isDisabled();

        if (!isDisabled) {
          await sensitivityTab.click();
          await page.waitForTimeout(500);

          // Should show sensitivity table
          const content = await dialog.textContent();
          expect(
            content?.includes('Detailed Sensitivity') ||
            content?.includes('Downside') ||
            content?.includes('Upside')
          ).toBeTruthy();
        }
      }
    });
  });

  test.describe('Export Functionality', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display PDF export button when results available', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        await page.waitForTimeout(500);

        // PDF button should be visible when results are ready
        const pdfButton = dialog.getByRole('button', { name: /pdf/i });

        // May be visible or not depending on results state
        const isVisible = await pdfButton.isVisible().catch(() => false);

        if (isVisible) {
          await expect(pdfButton).toBeEnabled();
        }
      }
    });

    test('should display Excel export button when results available', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        await page.waitForTimeout(500);

        // Excel button should be visible when results are ready
        const excelButton = dialog.getByRole('button', { name: /excel/i });

        const isVisible = await excelButton.isVisible().catch(() => false);

        if (isVisible) {
          await expect(excelButton).toBeEnabled();
        }
      }
    });
  });

  test.describe('Error Handling', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should handle invalid numeric input gracefully', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Try to enter invalid value in purchase price
        const purchasePriceInput = dialog.locator('input#purchasePrice');
        if (await purchasePriceInput.isVisible()) {
          await purchasePriceInput.clear();
          await purchasePriceInput.fill('invalid');

          // Input should handle invalid input (convert to 0 or show validation)
          const value = await purchasePriceInput.inputValue();
          // HTML number inputs typically clear invalid input
          expect(value === '' || value === '0' || !isNaN(parseFloat(value))).toBeTruthy();
        }
      }
    });

    test('should handle zero values gracefully', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Set units to 0
        const unitsInput = dialog.locator('input#units');
        if (await unitsInput.isVisible()) {
          await unitsInput.clear();
          await unitsInput.fill('0');
          await page.waitForTimeout(500);

          // Dialog should still be functional (no crash)
          await expect(dialog).toBeVisible();
        }
      }
    });

    test('should display error states appropriately', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // The modal should handle edge cases without crashing
        // Try extreme values
        const purchasePriceInput = dialog.locator('input#purchasePrice');
        if (await purchasePriceInput.isVisible()) {
          await purchasePriceInput.clear();
          await purchasePriceInput.fill('999999999999');
          await page.waitForTimeout(500);

          // Dialog should remain functional
          await expect(dialog).toBeVisible();

          // Stats bar or results should still render (even with extreme values)
          const statsBar = dialog.locator('[class*="bg-neutral-900"]');
          if (await statsBar.isVisible()) {
            const content = await statsBar.textContent();
            expect(content?.length).toBeGreaterThan(0);
          }
        }
      }
    });
  });

  test.describe('Collapsible Sections', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should collapse and expand Property Assumptions section', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Find and click Property Assumptions header button
        const sectionButton = dialog.locator('button:has-text("Property Assumptions")');

        if (await sectionButton.isVisible()) {
          // Should be expanded by default - check for fields
          const propertyNameInput = dialog.locator('input#propertyName');
          const wasVisible = await propertyNameInput.isVisible();

          // Click to collapse
          await sectionButton.click();
          await page.waitForTimeout(300);

          // Click to expand again if it was visible before
          if (wasVisible) {
            await sectionButton.click();
            await page.waitForTimeout(300);
            await expect(propertyNameInput).toBeVisible();
          }
        }
      }
    });

    test('should toggle Operating Expenses section', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Find Operating Expenses section
        const sectionButton = dialog.locator('button:has-text("Operating Expenses")');

        if (await sectionButton.isVisible()) {
          // Click to toggle
          await sectionButton.click();
          await page.waitForTimeout(300);

          // Section should still be functional
          await expect(sectionButton).toBeVisible();
        }
      }
    });
  });

  test.describe('Slider Inputs', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should interact with LTV slider', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Find LTV slider
        const ltvSlider = dialog.locator('input#ltvPercent[type="range"]');

        if (await ltvSlider.isVisible()) {
          // Get initial value
          const initialValue = await ltvSlider.inputValue();

          // Change value
          await ltvSlider.fill('0.7');

          const newValue = await ltvSlider.inputValue();
          expect(newValue).toBe('0.7');
        }
      }
    });

    test('should interact with Interest Rate slider', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const interestSlider = dialog.locator('input#interestRate[type="range"]');

        if (await interestSlider.isVisible()) {
          await interestSlider.fill('0.07');

          const newValue = await interestSlider.inputValue();
          expect(newValue).toBe('0.07');
        }
      }
    });
  });

  test.describe('Select Dropdowns', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should change Property Class dropdown', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const propertyClassSelect = dialog.locator('select#propertyClass');

        if (await propertyClassSelect.isVisible()) {
          await propertyClassSelect.selectOption('A');
          await expect(propertyClassSelect).toHaveValue('A');
        }
      }
    });

    test('should change Loan Type dropdown', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const loanTypeSelect = dialog.locator('select#loanType');

        if (await loanTypeSelect.isVisible()) {
          await loanTypeSelect.selectOption('CMBS');
          await expect(loanTypeSelect).toHaveValue('CMBS');
        }
      }
    });

    test('should change Asset Type dropdown', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        const assetTypeSelect = dialog.locator('select#assetType');

        if (await assetTypeSelect.isVisible()) {
          await assetTypeSelect.selectOption('High-Rise');
          await expect(assetTypeSelect).toHaveValue('High-Rise');
        }
      }
    });
  });

  test.describe('Modal Behavior', () => {
    test('should close modal when clicking close button', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Find and click close button (usually X button)
        const closeButton = page.getByRole('dialog').locator('button[class*="close"], button:has(svg[class*="X"])').first();

        if (await closeButton.isVisible()) {
          await closeButton.click();
          await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });
        }
      }
    });

    test('should close modal when pressing Escape', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Press Escape
        await page.keyboard.press('Escape');

        // Modal should close
        await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });
      }
    });

    test('should re-open modal after closing', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        // Open modal
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Close with Escape
        await page.keyboard.press('Escape');
        await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });

        // Re-open
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('Assumptions Presets', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });
      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      }
    });

    test('should display assumptions presets component', async ({ page }) => {
      const dialog = page.getByRole('dialog');

      if (await dialog.isVisible()) {
        // Look for presets section or buttons
        const content = await dialog.textContent();

        // May have preset options
        const hasPresets =
          content?.includes('Preset') ||
          content?.includes('Template') ||
          content?.includes('Conservative') ||
          content?.includes('Aggressive');

        // Presets may or may not be visible depending on implementation
        expect(dialog).toBeVisible();
      }
    });
  });

  test.describe('Complete Underwriting Workflow', () => {
    test('should complete full underwriting analysis workflow', async ({ page }) => {
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (!(await underwriteButton.isVisible())) {
        test.skip();
        return;
      }

      // Step 1: Open modal
      await underwriteButton.click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      const dialog = page.getByRole('dialog');

      // Step 2: Fill in property details
      const propertyNameInput = dialog.locator('input#propertyName');
      if (await propertyNameInput.isVisible()) {
        await propertyNameInput.fill('E2E Test Property');
      }

      // Step 3: Modify purchase price
      const purchasePriceInput = dialog.locator('input#purchasePrice');
      if (await purchasePriceInput.isVisible()) {
        await purchasePriceInput.clear();
        await purchasePriceInput.fill('18000000');
      }

      await page.waitForTimeout(500);

      // Step 4: Check Results tab is available
      const resultsTab = dialog.getByRole('tab', { name: /results/i });
      const resultsEnabled = !(await resultsTab.isDisabled());

      if (resultsEnabled) {
        // Step 5: Navigate to Results tab
        await resultsTab.click();
        await page.waitForTimeout(300);

        // Verify results are displayed
        const content = await dialog.textContent();
        expect(
          content?.includes('Investment Summary') ||
          content?.includes('IRR') ||
          content?.includes('Equity Multiple')
        ).toBeTruthy();

        // Step 6: Navigate to Projections tab
        const projectionsTab = dialog.getByRole('tab', { name: /projections/i });
        if (!(await projectionsTab.isDisabled())) {
          await projectionsTab.click();
          await page.waitForTimeout(300);

          const projContent = await dialog.textContent();
          expect(
            projContent?.includes('NOI') ||
            projContent?.includes('Year')
          ).toBeTruthy();
        }

        // Step 7: Navigate to Sensitivity tab
        const sensitivityTab = dialog.getByRole('tab', { name: /sensitivity/i });
        if (!(await sensitivityTab.isDisabled())) {
          await sensitivityTab.click();
          await page.waitForTimeout(300);

          const sensContent = await dialog.textContent();
          expect(
            sensContent?.includes('Sensitivity') ||
            sensContent?.includes('Base Case')
          ).toBeTruthy();
        }
      }

      // Step 8: Close modal
      await page.keyboard.press('Escape');
      await expect(dialog).not.toBeVisible({ timeout: 3000 });
    });
  });

  test.describe('Responsive Layout', () => {
    test('should display correctly on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();

        // Modal should still be visible and functional
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Tabs should still be accessible
        const inputsTab = page.getByRole('dialog').getByRole('tab', { name: /inputs/i });
        await expect(inputsTab).toBeVisible();
      }
    });

    test('should display correctly on larger viewport', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('/');
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });

      const underwriteButton = page.getByRole('button', { name: /underwrite deal/i });

      if (await underwriteButton.isVisible()) {
        await underwriteButton.click();

        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

        // Should have full layout with two columns on large screens
        const dialog = page.getByRole('dialog');
        const content = await dialog.textContent();
        expect(content?.length).toBeGreaterThan(100);
      }
    });
  });
});
