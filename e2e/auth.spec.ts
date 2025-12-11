import { test, expect } from '@playwright/test';

/**
 * E2E Tests: Authentication Flow
 *
 * Tests the authentication API endpoints and protected routes.
 * Note: Frontend login page is not yet implemented, so these tests
 * focus on API-level auth that the frontend will consume.
 */
test.describe('Authentication', () => {
  const API_BASE = 'http://localhost:8000/api/v1';

  test.describe('Login API', () => {
    test('should login with valid demo credentials', async ({ request }) => {
      const response = await request.post(`${API_BASE}/auth/login`, {
        form: {
          username: 'admin@brcapital.com',
          password: 'admin123',
        },
      });

      // API should return 200 with tokens
      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data).toHaveProperty('access_token');
      expect(data).toHaveProperty('refresh_token');
      expect(data).toHaveProperty('token_type', 'bearer');
      expect(data).toHaveProperty('expires_in');
    });

    test('should login with analyst credentials', async ({ request }) => {
      const response = await request.post(`${API_BASE}/auth/login`, {
        form: {
          username: 'analyst@brcapital.com',
          password: 'analyst123',
        },
      });

      expect(response.ok()).toBeTruthy();

      const data = await response.json();
      expect(data.access_token).toBeTruthy();
    });

    test('should reject invalid credentials', async ({ request }) => {
      const response = await request.post(`${API_BASE}/auth/login`, {
        form: {
          username: 'invalid@brcapital.com',
          password: 'wrongpassword',
        },
      });

      // Should return 401 Unauthorized
      expect(response.status()).toBe(401);

      const data = await response.json();
      expect(data.detail).toContain('Incorrect');
    });

    test('should reject empty credentials', async ({ request }) => {
      const response = await request.post(`${API_BASE}/auth/login`, {
        form: {
          username: '',
          password: '',
        },
      });

      // Should fail (400 or 401 or 422 depending on validation)
      expect(response.ok()).toBeFalsy();
    });
  });

  test.describe('Token Refresh', () => {
    test('should refresh access token with valid refresh token', async ({ request }) => {
      // First login to get tokens
      const loginResponse = await request.post(`${API_BASE}/auth/login`, {
        form: {
          username: 'admin@brcapital.com',
          password: 'admin123',
        },
      });

      expect(loginResponse.ok()).toBeTruthy();
      const loginData = await loginResponse.json();
      const refreshToken = loginData.refresh_token;

      // Now refresh the token
      const refreshResponse = await request.post(`${API_BASE}/auth/refresh`, {
        data: {
          refresh_token: refreshToken,
        },
      });

      expect(refreshResponse.ok()).toBeTruthy();

      const refreshData = await refreshResponse.json();
      expect(refreshData.access_token).toBeTruthy();
      expect(refreshData.refresh_token).toBeTruthy();

      // New tokens should be different from original
      expect(refreshData.access_token).not.toBe(loginData.access_token);
    });

    test('should reject invalid refresh token', async ({ request }) => {
      const response = await request.post(`${API_BASE}/auth/refresh`, {
        data: {
          refresh_token: 'invalid-token',
        },
      });

      expect(response.status()).toBe(401);
    });
  });

  test.describe('Get Current User', () => {
    test('should get current user info with valid token', async ({ request }) => {
      // Login first
      const loginResponse = await request.post(`${API_BASE}/auth/login`, {
        form: {
          username: 'admin@brcapital.com',
          password: 'admin123',
        },
      });

      expect(loginResponse.ok()).toBeTruthy();
      const loginData = await loginResponse.json();
      const accessToken = loginData.access_token;

      // Get current user
      const meResponse = await request.get(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      expect(meResponse.ok()).toBeTruthy();

      const userData = await meResponse.json();
      expect(userData).toHaveProperty('id');
      expect(userData).toHaveProperty('role');
    });

    test('should reject request without token', async ({ request }) => {
      const response = await request.get(`${API_BASE}/auth/me`);

      // Should return 401 or 403
      expect(response.status()).toBeGreaterThanOrEqual(400);
    });

    test('should reject request with invalid token', async ({ request }) => {
      const response = await request.get(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: 'Bearer invalid-token',
        },
      });

      expect(response.status()).toBe(401);
    });
  });

  test.describe('Logout', () => {
    test('should logout successfully', async ({ request }) => {
      // Login first
      const loginResponse = await request.post(`${API_BASE}/auth/login`, {
        form: {
          username: 'admin@brcapital.com',
          password: 'admin123',
        },
      });

      expect(loginResponse.ok()).toBeTruthy();
      const loginData = await loginResponse.json();

      // Logout
      const logoutResponse = await request.post(`${API_BASE}/auth/logout`, {
        headers: {
          Authorization: `Bearer ${loginData.access_token}`,
        },
      });

      expect(logoutResponse.ok()).toBeTruthy();

      const logoutData = await logoutResponse.json();
      expect(logoutData.message).toContain('logged out');
    });
  });

  test.describe('Protected Routes (Frontend)', () => {
    // These tests verify the frontend is accessible
    // Auth protection on the frontend will be implemented later

    test('dashboard loads without auth (dev mode)', async ({ page }) => {
      await page.goto('/');

      // Dashboard should load (no auth gate in current implementation)
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });

    test('investments page loads without auth (dev mode)', async ({ page }) => {
      await page.goto('/investments');

      // Page should load
      await expect(page.locator('main')).toBeVisible({ timeout: 10000 });
    });
  });
});
