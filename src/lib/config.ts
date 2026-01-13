/**
 * Application Configuration
 *
 * Centralized configuration derived from environment variables.
 * Use this module instead of accessing import.meta.env directly.
 */

/**
 * Check if mock data should be used instead of real API
 * Set VITE_USE_MOCK_DATA=true in your .env file to enable
 */
export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';

/**
 * Check if running in development mode
 */
export const IS_DEV = import.meta.env.DEV;

/**
 * Check if running in production mode
 */
export const IS_PROD = import.meta.env.PROD;

/**
 * API base URL for backend requests
 */
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * WebSocket URL for real-time updates
 */
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

/**
 * Feature flags
 */
export const FEATURES = {
  /** Enable analytics tracking */
  analytics: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  /** Enable debug logging */
  debug: import.meta.env.VITE_DEBUG === 'true',
  /** Enable experimental features */
  experimental: import.meta.env.VITE_EXPERIMENTAL === 'true',
} as const;

/**
 * Helper to determine if API calls should use mock data
 * Uses mock data if:
 * 1. VITE_USE_MOCK_DATA is explicitly set to 'true', OR
 * 2. In development mode and API is unavailable (fallback behavior)
 */
export function shouldUseMockData(): boolean {
  return USE_MOCK_DATA;
}

/**
 * Helper for conditional mock data fallback in development
 * Returns mock data if in dev mode and API call fails
 */
export function withMockFallback<T>(
  apiCall: () => Promise<T>,
  mockData: T
): Promise<T> {
  if (USE_MOCK_DATA) {
    return Promise.resolve(mockData);
  }

  return apiCall().catch((error) => {
    if (IS_DEV) {
      console.warn('API unavailable, falling back to mock data:', error);
      return mockData;
    }
    throw error;
  });
}
