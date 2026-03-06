import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('config module', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('exports API_URL with /api/v1 suffix', async () => {
    const { API_URL } = await import('../config');
    expect(API_URL).toMatch(/\/api\/v1$/);
  });

  it('strips trailing slashes from API_URL', async () => {
    const { API_URL } = await import('../config');
    expect(API_URL).not.toMatch(/\/\/api/);
  });

  it('exports WS_URL', async () => {
    const { WS_URL } = await import('../config');
    expect(typeof WS_URL).toBe('string');
    expect(WS_URL).toMatch(/^ws/);
  });

  it('exports IS_DEV and IS_PROD as booleans', async () => {
    const { IS_DEV, IS_PROD } = await import('../config');
    expect(typeof IS_DEV).toBe('boolean');
    expect(typeof IS_PROD).toBe('boolean');
  });

  it('exports FEATURES object', async () => {
    const { FEATURES } = await import('../config');
    expect(FEATURES).toHaveProperty('analytics');
    expect(FEATURES).toHaveProperty('debug');
    expect(FEATURES).toHaveProperty('experimental');
  });

  it('shouldUseMockData() returns boolean', async () => {
    const { shouldUseMockData } = await import('../config');
    expect(typeof shouldUseMockData()).toBe('boolean');
  });

  it('withMockFallback returns API result on success', async () => {
    const { withMockFallback } = await import('../config');
    const apiCall = () => Promise.resolve({ data: 'real' });
    const result = await withMockFallback(apiCall, { data: 'mock' });
    expect(result).toEqual({ data: 'real' });
  });

  it('withMockFallback returns mock data in dev on failure', async () => {
    const { withMockFallback, IS_DEV } = await import('../config');
    if (!IS_DEV) return; // Only applicable in dev
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const apiCall = () => Promise.reject(new Error('network'));
    const result = await withMockFallback(apiCall, { data: 'mock' });
    expect(result).toEqual({ data: 'mock' });
    consoleSpy.mockRestore();
  });
});
