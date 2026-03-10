import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock localStorage
const mockStorage: Record<string, string> = {};
vi.stubGlobal('localStorage', {
  getItem: vi.fn((key: string) => mockStorage[key] || null),
  setItem: vi.fn((key: string, value: string) => { mockStorage[key] = value; }),
  removeItem: vi.fn((key: string) => { delete mockStorage[key]; }),
});
vi.stubGlobal('dispatchEvent', vi.fn());

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, status = 200, headers?: Record<string, string>) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'content-type': 'application/json', ...headers }),
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  };
}

describe('apiClient (fetch)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(mockStorage).forEach(k => delete mockStorage[k]);
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('get() sends GET and returns parsed JSON', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ items: [1, 2] }));
    const { get } = await import('../api');
    const result = await get('/test');
    expect(mockFetch).toHaveBeenCalledOnce();
    expect(result).toEqual({ items: [1, 2] });
  });

  it('post() sends POST with JSON body', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ id: 1 }));
    const { post } = await import('../api');
    const result = await post('/test', { name: 'foo' });
    expect(result).toEqual({ id: 1 });

    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe('POST');
    expect(options.body).toBe(JSON.stringify({ name: 'foo' }));
  });

  it('post() sends URLSearchParams as form-urlencoded', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ token: 'abc' }));
    const { apiClient } = await import('../api');
    const params = new URLSearchParams();
    params.append('username', 'test@test.com');
    params.append('password', 'pass');

    await apiClient.post('/auth/login', params);

    const [, options] = mockFetch.mock.calls[0];
    expect(options.body).toBeInstanceOf(URLSearchParams);
    // Should NOT have Content-Type: application/json header
    const headers = options.headers as Record<string, string>;
    expect(headers['Content-Type']).toBeUndefined();
  });

  it('put() sends PUT and returns data', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ updated: true }));
    const { put } = await import('../api');
    const result = await put('/test/1', { name: 'bar' });
    expect(result).toEqual({ updated: true });
  });

  it('patch() sends PATCH and returns data', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ patched: true }));
    const { patch } = await import('../api');
    const result = await patch('/test/1', { stage: 'closed' });
    expect(result).toEqual({ patched: true });
  });

  it('del() sends DELETE', async () => {
    mockFetch.mockResolvedValue(jsonResponse({}));
    const { del } = await import('../api');
    await del('/test/1');
    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe('DELETE');
  });

  it('attaches auth token from localStorage', async () => {
    mockStorage['access_token'] = 'my-jwt';
    mockFetch.mockResolvedValue(jsonResponse({ ok: true }));
    const { get } = await import('../api');
    await get('/test');
    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers['Authorization']).toBe('Bearer my-jwt');
  });

  it('throws ApiError on non-OK response', async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: 'Not found' }, 404));
    const { get, ApiError } = await import('../api');
    await expect(get('/missing')).rejects.toThrow(ApiError);
  });

  it('exports apiClient and convenience functions', async () => {
    const mod = await import('../api');
    expect(mod.apiClient).toBeDefined();
    expect(mod.get).toBeDefined();
    expect(mod.post).toBeDefined();
    expect(mod.put).toBeDefined();
    expect(mod.patch).toBeDefined();
    expect(mod.del).toBeDefined();
    expect(mod.api).toBeDefined();
  });
});
