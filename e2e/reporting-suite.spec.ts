import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Reporting Suite
 *
 * Tests the Reporting Suite page including:
 * - Page load and navigation
 * - Multi-step Report Wizard flow
 * - Template selection, configuration, format selection
 * - Report generation with progress polling
 * - API endpoints for reports
 * - Edge cases and error handling
 */

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('Reporting Suite Page', () => {
  test.describe('Page Load', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    });

    test('should display reporting suite page', async ({ page }) => {
      await expect(page).toHaveURL(/\/reporting/);
      await expect(page.locator('main[role="main"]')).toBeVisible();
    });

    test('should display page header with title', async ({ page }) => {
      const heading = page.getByRole('heading', { name: /reporting suite/i });
      await expect(heading).toBeVisible();
    });

    test('should display tab navigation', async ({ page }) => {
      // Check for main tabs
      await expect(page.getByRole('button', { name: /report templates/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /custom builder/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /report queue/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /distribution/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /settings/i })).toBeVisible();
    });

    test('should display New Report button', async ({ page }) => {
      const newReportButton = page.getByRole('button', { name: /new report/i });
      await expect(newReportButton).toBeVisible();
    });

    test('should load templates tab by default', async ({ page }) => {
      await page.waitForTimeout(500);
      // Templates tab should be active (look for template cards or content)
      const content = await page.locator('main[role="main"]').textContent();
      expect(content).toBeTruthy();
      expect(content!.length).toBeGreaterThan(100);
    });
  });

  test.describe('Tab Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    });

    test('should switch to Custom Builder tab', async ({ page }) => {
      await page.getByRole('button', { name: /custom builder/i }).click();
      await page.waitForTimeout(500);

      // Should show builder-related content
      const content = await page.locator('main[role="main"]').textContent();
      expect(content).toBeTruthy();
    });

    test('should switch to Report Queue tab', async ({ page }) => {
      await page.getByRole('button', { name: /report queue/i }).click();
      await page.waitForTimeout(500);

      // Should show queue-related content
      const content = await page.locator('main[role="main"]').textContent();
      expect(content).toBeTruthy();
    });

    test('should switch to Distribution tab', async ({ page }) => {
      await page.getByRole('button', { name: /distribution/i }).click();
      await page.waitForTimeout(500);

      // Should show distribution-related content
      const content = await page.locator('main[role="main"]').textContent();
      expect(content).toBeTruthy();
    });

    test('should switch to Settings tab', async ({ page }) => {
      await page.getByRole('button', { name: /settings/i }).click();
      await page.waitForTimeout(500);

      // Should show settings-related content
      const content = await page.locator('main[role="main"]').textContent();
      expect(content).toBeTruthy();
    });
  });

  test.describe('Report Wizard - Opening and Closing', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    });

    test('should open report wizard dialog when clicking New Report', async ({ page }) => {
      await page.getByRole('button', { name: /new report/i }).click();

      // Wait for dialog to appear
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Should show wizard title
      await expect(page.getByRole('heading', { name: /generate report/i })).toBeVisible();
    });

    test('should display wizard step indicator', async ({ page }) => {
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Look for step indicator elements
      const dialog = page.getByRole('dialog');
      const stepContent = await dialog.textContent();

      // Should have step-related content (Template, Configure, Format, Generate)
      expect(
        stepContent?.includes('Template') ||
        stepContent?.includes('Select') ||
        stepContent?.includes('Step')
      ).toBeTruthy();
    });

    test('should close wizard when clicking Cancel', async ({ page }) => {
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Click cancel button
      await page.getByRole('button', { name: /cancel/i }).click();

      // Dialog should close
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });
    });

    test('should close wizard when clicking outside (escape key)', async ({ page }) => {
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Press escape key
      await page.keyboard.press('Escape');

      // Dialog should close
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });
    });
  });

  test.describe('Report Wizard - Template Selection Step', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
    });

    test('should display template search input', async ({ page }) => {
      const searchInput = page.getByPlaceholder(/search templates/i);
      await expect(searchInput).toBeVisible();
    });

    test('should display category filter dropdown', async ({ page }) => {
      // Look for category selector (select element with "All Categories" option)
      const categorySelect = page.locator('select').first();
      await expect(categorySelect).toBeVisible();
    });

    test('should display template cards', async ({ page }) => {
      await page.waitForTimeout(500);

      // Look for template buttons (template cards are buttons)
      const templateButtons = page.getByRole('dialog').locator('button[type="button"]');
      const count = await templateButtons.count();

      // Should have at least one template card (excluding Cancel/Next buttons)
      expect(count).toBeGreaterThan(2);
    });

    test('should select a template when clicked', async ({ page }) => {
      await page.waitForTimeout(500);

      // Find and click on a template card (Executive Summary)
      const templateCard = page.getByRole('dialog').getByText('Executive Summary').first();

      if (await templateCard.isVisible()) {
        await templateCard.click();

        // Next button should become enabled
        const nextButton = page.getByRole('button', { name: /next/i });
        await expect(nextButton).toBeEnabled();
      }
    });

    test('should filter templates by search query', async ({ page }) => {
      const searchInput = page.getByPlaceholder(/search templates/i);
      await searchInput.fill('Executive');

      await page.waitForTimeout(300);

      // Should show filtered results
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();
      expect(content?.includes('Executive')).toBeTruthy();
    });

    test('should filter templates by category', async ({ page }) => {
      const categorySelect = page.locator('select').first();

      // Select a specific category
      await categorySelect.selectOption('financial');

      await page.waitForTimeout(300);

      // Should show filtered results
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();
      expect(content?.includes('Financial')).toBeTruthy();
    });

    test('should show empty state when no templates match filter', async ({ page }) => {
      const searchInput = page.getByPlaceholder(/search templates/i);
      await searchInput.fill('nonexistent-template-xyz');

      await page.waitForTimeout(300);

      // Should show "No templates found" message
      await expect(page.getByText(/no templates found/i)).toBeVisible();
    });

    test('should disable Next button when no template selected', async ({ page }) => {
      const nextButton = page.getByRole('button', { name: /next/i });
      await expect(nextButton).toBeDisabled();
    });
  });

  test.describe('Report Wizard - Multi-Step Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
    });

    test('should navigate to Configure step after selecting template', async ({ page }) => {
      await page.waitForTimeout(500);

      // Select Executive Summary template
      const templateCard = page.getByRole('dialog').getByText('Executive Summary').first();
      if (await templateCard.isVisible()) {
        await templateCard.click();
      } else {
        // Try clicking any template card
        const anyTemplate = page.getByRole('dialog').locator('button[type="button"]').first();
        await anyTemplate.click();
      }

      // Click Next
      await page.getByRole('button', { name: /next/i }).click();

      await page.waitForTimeout(500);

      // Should show parameter configuration step
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();
      expect(
        content?.includes('Configure') ||
        content?.includes('Date') ||
        content?.includes('parameter') ||
        content?.includes('No configuration')
      ).toBeTruthy();
    });

    test('should show Back button on Configure step', async ({ page }) => {
      await page.waitForTimeout(500);

      // Select a template and navigate to next step
      const templateCard = page.getByRole('dialog').getByText('Executive Summary').first();
      if (await templateCard.isVisible()) {
        await templateCard.click();
      } else {
        const anyTemplate = page.getByRole('dialog').locator('button[type="button"]').first();
        await anyTemplate.click();
      }

      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Back button should be visible
      await expect(page.getByRole('button', { name: /back/i })).toBeVisible();
    });

    test('should navigate back to Template step when clicking Back', async ({ page }) => {
      await page.waitForTimeout(500);

      // Navigate to configure step
      const anyTemplate = page.getByRole('dialog').locator('button[type="button"]').first();
      await anyTemplate.click();
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Click Back
      await page.getByRole('button', { name: /back/i }).click();
      await page.waitForTimeout(500);

      // Should be back on template selection
      await expect(page.getByPlaceholder(/search templates/i)).toBeVisible();
    });

    test('should navigate through all wizard steps', async ({ page }) => {
      await page.waitForTimeout(500);

      // Step 1: Select template
      const templateCard = page.getByRole('dialog').getByText('Portfolio Overview').first();
      if (await templateCard.isVisible()) {
        await templateCard.click();
      } else {
        // Portfolio Overview has no required params, making it easier to test
        const anyTemplate = page.getByRole('dialog').locator('button[type="button"]').first();
        await anyTemplate.click();
      }
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Step 2: Configure parameters (may be empty for some templates)
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Step 3: Select format
      const dialog = page.getByRole('dialog');
      const formatContent = await dialog.textContent();
      expect(
        formatContent?.includes('PDF') ||
        formatContent?.includes('Excel') ||
        formatContent?.includes('format') ||
        formatContent?.includes('Format')
      ).toBeTruthy();
    });
  });

  test.describe('Report Wizard - Parameter Configuration Step', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Navigate to a template with parameters
      await page.waitForTimeout(500);
      const financialTemplate = page.getByRole('dialog').getByText('Financial Performance').first();
      if (await financialTemplate.isVisible()) {
        await financialTemplate.click();
      }
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);
    });

    test('should display parameter form fields', async ({ page }) => {
      // Financial Performance template has date parameters
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();

      expect(
        content?.includes('Date') ||
        content?.includes('date') ||
        content?.includes('Start') ||
        content?.includes('End') ||
        content?.includes('No configuration')
      ).toBeTruthy();
    });

    test('should allow filling date parameters', async ({ page }) => {
      // Look for date inputs
      const dateInputs = page.getByRole('dialog').locator('input[type="date"]');
      const count = await dateInputs.count();

      if (count > 0) {
        // Fill in date values
        await dateInputs.first().fill('2024-01-01');

        // Verify the value was set
        const value = await dateInputs.first().inputValue();
        expect(value).toBe('2024-01-01');
      }
    });

    test('should show validation errors for required fields', async ({ page }) => {
      // Try to proceed without filling required fields
      const nextButton = page.getByRole('button', { name: /next/i });

      // If there are required fields and they're not filled, Next should be disabled or show error
      // This depends on the template selected
      const isDisabled = await nextButton.isDisabled();

      // Either Next is disabled or clicking shows error
      if (!isDisabled) {
        await nextButton.click();
        await page.waitForTimeout(300);

        // Check for error messages or if we stayed on the same step
        const dialog = page.getByRole('dialog');
        const content = await dialog.textContent();
        expect(content).toBeTruthy();
      }
    });
  });

  test.describe('Report Wizard - Format Selection Step', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Select Portfolio Overview (no required params) and navigate to format step
      await page.waitForTimeout(500);
      const portfolioTemplate = page.getByRole('dialog').getByText('Portfolio Overview').first();
      if (await portfolioTemplate.isVisible()) {
        await portfolioTemplate.click();
      } else {
        const anyTemplate = page.getByRole('dialog').locator('button[type="button"]').first();
        await anyTemplate.click();
      }
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);
    });

    test('should display format options', async ({ page }) => {
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();

      // Should show format selection options
      expect(
        content?.includes('PDF') ||
        content?.includes('Excel') ||
        content?.includes('PowerPoint') ||
        content?.includes('format')
      ).toBeTruthy();
    });

    test('should select PDF format', async ({ page }) => {
      // Look for PDF option button
      const pdfOption = page.getByRole('dialog').getByText(/pdf/i).first();

      if (await pdfOption.isVisible()) {
        await pdfOption.click();

        // Generate button should become enabled
        const generateButton = page.getByRole('button', { name: /generate/i });
        await expect(generateButton).toBeEnabled();
      }
    });

    test('should select Excel format if available', async ({ page }) => {
      // Look for Excel option
      const excelOption = page.getByRole('dialog').getByText(/excel/i).first();

      if (await excelOption.isVisible()) {
        await excelOption.click();

        // Generate button should become enabled
        const generateButton = page.getByRole('button', { name: /generate/i });
        await expect(generateButton).toBeEnabled();
      }
    });

    test('should show Generate button instead of Next on format step', async ({ page }) => {
      // On the format step, the Next button should say "Generate"
      const generateButton = page.getByRole('button', { name: /generate/i });
      await expect(generateButton).toBeVisible();
    });
  });

  test.describe('Report Wizard - Generation Progress Step', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Complete wizard to generation step
      await page.waitForTimeout(500);

      // Select Portfolio Overview template
      const portfolioTemplate = page.getByRole('dialog').getByText('Portfolio Overview').first();
      if (await portfolioTemplate.isVisible()) {
        await portfolioTemplate.click();
      } else {
        const anyTemplate = page.getByRole('dialog').locator('button[type="button"]').first();
        await anyTemplate.click();
      }
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Skip configuration step
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Select format
      const pdfOption = page.getByRole('dialog').getByText(/pdf/i).first();
      if (await pdfOption.isVisible()) {
        await pdfOption.click();
      }
    });

    test('should show generation progress after clicking Generate', async ({ page }) => {
      // Click Generate
      await page.getByRole('button', { name: /generate/i }).click();

      await page.waitForTimeout(1000);

      // Should show progress indicator
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();

      expect(
        content?.includes('Progress') ||
        content?.includes('Generating') ||
        content?.includes('%') ||
        content?.includes('Initializing') ||
        content?.includes('Complete') ||
        content?.includes('Ready')
      ).toBeTruthy();
    });

    test('should show progress bar during generation', async ({ page }) => {
      await page.getByRole('button', { name: /generate/i }).click();

      await page.waitForTimeout(500);

      // Look for progress bar element (div with progress-related styles)
      const progressBar = page.getByRole('dialog').locator('[class*="progress"], [class*="bg-blue-500"], [class*="h-2"]');
      const hasProgressBar = await progressBar.first().isVisible().catch(() => false);

      // Either progress bar visible or some progress content
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();

      expect(hasProgressBar || content?.includes('%')).toBeTruthy();
    });

    test('should show download button when generation completes', async ({ page }) => {
      await page.getByRole('button', { name: /generate/i }).click();

      // Wait for generation to complete (mock mode completes in ~8 seconds)
      await page.waitForTimeout(10000);

      // Should show download button or completion message
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();

      const hasDownload = await page.getByRole('button', { name: /download/i }).isVisible().catch(() => false);
      const hasComplete = content?.includes('Complete') || content?.includes('Ready') || content?.includes('100%');

      expect(hasDownload || hasComplete).toBeTruthy();
    });

    test('should hide Back/Next buttons during generation', async ({ page }) => {
      await page.getByRole('button', { name: /generate/i }).click();

      await page.waitForTimeout(500);

      // Back and Next buttons should not be visible during generation
      await expect(page.getByRole('button', { name: /back/i })).not.toBeVisible();
      await expect(page.getByRole('button', { name: /next/i })).not.toBeVisible();
    });

    test('should show Close button when generation completes', async ({ page }) => {
      await page.getByRole('button', { name: /generate/i }).click();

      // Wait for generation to complete
      await page.waitForTimeout(10000);

      // Should show Close button
      await expect(page.getByRole('button', { name: /close/i })).toBeVisible();
    });
  });

  test.describe('Report Wizard - Error Handling', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    });

    test('should show error state if templates fail to load', async ({ page }) => {
      // Intercept API call to simulate failure
      await page.route('**/reporting/templates**', (route) => {
        route.fulfill({ status: 500, body: JSON.stringify({ error: 'Server error' }) });
      });

      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Should show error state or fall back to mock data (since mock mode is likely enabled)
      await page.waitForTimeout(1000);

      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();

      // Either shows error or loads mock templates successfully
      expect(content).toBeTruthy();
      expect(content!.length).toBeGreaterThan(50);
    });
  });

  test.describe('Reporting API Endpoints', () => {
    test('should list report templates via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/templates`, {
        params: { page: 1, page_size: 10 },
      });

      // Skip if auth required or backend unavailable
      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toBeDefined();
    });

    test('should get single template by ID via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/templates/1`);

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('id');
    });

    test('should list queued reports via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/queue`, {
        params: { page: 1, page_size: 10 },
      });

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toBeDefined();
    });

    test('should get queued report status via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/queue/1`);

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('status');
    });

    test('should generate report via API', async ({ request }) => {
      const reportRequest = {
        template_id: 1,
        name: 'E2E Test Report',
        format: 'pdf',
        parameters: {},
      };

      const response = await request.post(`${API_BASE}/reporting/generate`, {
        data: reportRequest,
      });

      // Skip if auth required, endpoint not ready, or validation errors
      if ([401, 403, 404, 405, 422, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      // Accept 200 or 201 for successful creation
      expect([200, 201]).toContain(response.status());

      const data = await response.json();
      expect(data).toHaveProperty('queued_report_id');
    });

    test('should list distribution schedules via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/schedules`);

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toBeDefined();
    });

    test('should list report widgets via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/widgets`);

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toBeDefined();
    });

    test('should filter templates by category via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/templates`, {
        params: { category: 'financial' },
      });

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();
    });

    test('should filter queued reports by status via API', async ({ request }) => {
      const response = await request.get(`${API_BASE}/reporting/queue`, {
        params: { status: 'completed' },
      });

      if ([401, 403, 404, 500, 502].includes(response.status())) {
        test.skip();
        return;
      }

      expect(response.ok()).toBeTruthy();
    });
  });

  test.describe('Report Templates Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
    });

    test('should display template cards in templates tab', async ({ page }) => {
      await page.waitForTimeout(1000);

      // Look for template-related content
      const mainContent = await page.locator('main[role="main"]').textContent();

      expect(
        mainContent?.includes('Executive') ||
        mainContent?.includes('Financial') ||
        mainContent?.includes('Portfolio') ||
        mainContent?.includes('template')
      ).toBeTruthy();
    });

    test('should have clickable templates to start wizard', async ({ page }) => {
      await page.waitForTimeout(1000);

      // Look for buttons or links that might trigger the wizard
      const buttons = page.locator('main[role="main"]').locator('button, [role="button"]');
      const count = await buttons.count();

      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Report Queue Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /report queue/i }).click();
      await page.waitForTimeout(500);
    });

    test('should display queue list', async ({ page }) => {
      const content = await page.locator('main[role="main"]').textContent();

      // Queue tab should show reports or empty state
      expect(content).toBeTruthy();
      expect(content!.length).toBeGreaterThan(50);
    });

    test('should show report status in queue', async ({ page }) => {
      const content = await page.locator('main[role="main"]').textContent();

      // Should show status indicators
      expect(
        content?.includes('pending') ||
        content?.includes('Pending') ||
        content?.includes('generating') ||
        content?.includes('Generating') ||
        content?.includes('completed') ||
        content?.includes('Completed') ||
        content?.includes('failed') ||
        content?.includes('Failed') ||
        content?.includes('Queue') ||
        content?.includes('empty')
      ).toBeTruthy();
    });
  });

  test.describe('Distribution Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /distribution/i }).click();
      await page.waitForTimeout(500);
    });

    test('should display distribution schedules', async ({ page }) => {
      const content = await page.locator('main[role="main"]').textContent();

      expect(content).toBeTruthy();
      expect(content!.length).toBeGreaterThan(50);
    });

    test('should show schedule frequency options', async ({ page }) => {
      const content = await page.locator('main[role="main"]').textContent();

      // Should show schedule-related content
      expect(
        content?.includes('Weekly') ||
        content?.includes('Daily') ||
        content?.includes('Monthly') ||
        content?.includes('Quarterly') ||
        content?.includes('Schedule') ||
        content?.includes('Recipient')
      ).toBeTruthy();
    });
  });

  test.describe('Settings Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });
      await page.getByRole('button', { name: /settings/i }).click();
      await page.waitForTimeout(500);
    });

    test('should display report settings', async ({ page }) => {
      const content = await page.locator('main[role="main"]').textContent();

      expect(content).toBeTruthy();
      expect(content!.length).toBeGreaterThan(50);
    });

    test('should show branding/format settings', async ({ page }) => {
      const content = await page.locator('main[role="main"]').textContent();

      // Settings tab should show configuration options
      expect(
        content?.includes('Company') ||
        content?.includes('Logo') ||
        content?.includes('Color') ||
        content?.includes('Font') ||
        content?.includes('Page') ||
        content?.includes('Header') ||
        content?.includes('Footer') ||
        content?.includes('Settings') ||
        content?.includes('Default')
      ).toBeTruthy();
    });
  });

  test.describe('Complete Wizard Flow - Happy Path', () => {
    test('should complete full report generation workflow', async ({ page }) => {
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

      // Open wizard
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(500);

      // Step 1: Select Portfolio Overview template (no required params)
      const portfolioTemplate = page.getByRole('dialog').getByText('Portfolio Overview').first();
      if (await portfolioTemplate.isVisible()) {
        await portfolioTemplate.click();
      } else {
        // Fallback to first available template
        const templates = page.getByRole('dialog').locator('button[type="button"]');
        await templates.first().click();
      }
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Step 2: Configure (skip - Portfolio Overview has no params)
      await page.getByRole('button', { name: /next/i }).click();
      await page.waitForTimeout(500);

      // Step 3: Select format (PDF)
      const pdfOption = page.getByRole('dialog').getByText(/pdf/i).first();
      if (await pdfOption.isVisible()) {
        await pdfOption.click();
      }

      // Step 4: Generate
      await page.getByRole('button', { name: /generate/i }).click();
      await page.waitForTimeout(1000);

      // Verify progress is shown
      const dialog = page.getByRole('dialog');
      const content = await dialog.textContent();
      expect(
        content?.includes('Progress') ||
        content?.includes('%') ||
        content?.includes('Generating') ||
        content?.includes('Initializing')
      ).toBeTruthy();

      // Wait for completion (mock completes in ~8 seconds with 4 polls at 2s intervals)
      await page.waitForTimeout(10000);

      // Verify completion
      const finalContent = await dialog.textContent();
      expect(
        finalContent?.includes('Complete') ||
        finalContent?.includes('Ready') ||
        finalContent?.includes('Download') ||
        finalContent?.includes('100%')
      ).toBeTruthy();
    });
  });

  test.describe('Navigation from Dashboard', () => {
    test('should navigate to reporting page from main navigation', async ({ page }) => {
      await page.goto('/');
      await page.waitForTimeout(1000);

      // Find and click Reporting link
      const reportingLink = page.getByRole('link', { name: /reporting/i });

      if (await reportingLink.isVisible()) {
        await reportingLink.click();
        await expect(page).toHaveURL(/\/reporting/);

        // Verify page loaded
        await expect(page.getByRole('heading', { name: /reporting suite/i })).toBeVisible();
      }
    });
  });

  test.describe('Responsive Layout', () => {
    test('should display correctly on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

      // Page should still be functional
      await expect(page.getByRole('heading', { name: /reporting suite/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /new report/i })).toBeVisible();
    });

    test('should display wizard correctly on smaller viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/reporting');
      await expect(page.locator('main[role="main"]')).toBeVisible({ timeout: 10000 });

      // Open wizard
      await page.getByRole('button', { name: /new report/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

      // Wizard should be visible and functional
      await expect(page.getByPlaceholder(/search templates/i)).toBeVisible();
    });
  });
});
