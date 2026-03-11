import { test as base, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';

/**
 * Shared auth credentials for E2E tests.
 * These match the demo users seeded in the database.
 */
export const TEST_CREDENTIALS = {
  admin: {
    email: 'matt@bandrcapital.com',
    password: 'Wildcats777!!',
  },
  analyst: {
    email: 'demo@bandrcapital.com',
    password: 'Password123!',
  },
};

/**
 * Authenticates against the backend and returns an access token.
 * Throws (fails the test) if login fails — never silently skips.
 */
export async function getAuthToken(
  request: { post: (url: string, options?: Record<string, unknown>) => Promise<{ ok: () => boolean; status: () => number; json: () => Promise<Record<string, unknown>> }> },
  credentials = TEST_CREDENTIALS.admin
): Promise<string> {
  const response = await request.post(`${API_BASE}/auth/login`, {
    form: {
      username: credentials.email,
      password: credentials.password,
    },
  });

  if (!response.ok()) {
    throw new Error(
      `Auth login failed with status ${response.status()}. ` +
      `Ensure the backend is running at ${API_BASE} and demo users are seeded.`
    );
  }

  const data = await response.json();
  return data.access_token as string;
}

/**
 * Checks that the backend health endpoint responds.
 * Throws (fails the test) if backend is not reachable.
 */
export async function assertBackendHealthy(
  request: { get: (url: string) => Promise<{ ok: () => boolean; status: () => number }> }
): Promise<void> {
  let response;
  try {
    response = await request.get(`${API_BASE}/health`);
  } catch {
    throw new Error(
      `Backend health check failed — could not connect to ${API_BASE}/health. ` +
      `Ensure the backend is running (npm run dev:all).`
    );
  }

  if (!response.ok()) {
    throw new Error(
      `Backend health check returned status ${response.status()}. ` +
      `Ensure the backend is running and healthy at ${API_BASE}.`
    );
  }
}

/**
 * Extended test fixture that provides an authenticated API request context.
 *
 * Usage in spec files:
 *   import { test, expect } from '../fixtures/auth';
 *
 * The `authedRequest` fixture provides a request function that automatically
 * includes the Authorization header. The `authToken` fixture provides the
 * raw token string.
 *
 * If the backend is not running or auth fails, the ENTIRE test file fails
 * instead of silently skipping individual tests.
 */
type AuthFixtures = {
  authToken: string;
};

export const test = base.extend<AuthFixtures>({
  authToken: async ({ request }, use) => {
    // Health check — fail fast if backend is down
    await assertBackendHealthy(request);

    // Get auth token — fail if credentials are rejected
    const token = await getAuthToken(request);

    await use(token);
  },
});

export { expect } from '@playwright/test';
