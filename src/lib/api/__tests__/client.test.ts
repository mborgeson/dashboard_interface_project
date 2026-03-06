import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError, apiClient } from '../client';

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

function jsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response;
}

describe('ApiError', () => {
  it('creates error with status and message', () => {
    const err = new ApiError(404, 'Not Found');
    expect(err.status).toBe(404);
    expect(err.message).toBe('Not Found');
    expect(err.name).toBe('ApiError');
  });

  it('stores optional data', () => {
    const err = new ApiError(422, 'Validation', { detail: 'bad field' });
    expect(err.data).toEqual({ detail: 'bad field' });
  });
});

describe('apiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(mockStorage).forEach(k => delete mockStorage[k]);
  });

  describe('GET', () => {
    it('makes GET request and returns JSON', async () => {
      mockFetch.mockResolvedValue(jsonResponse({ items: [1] }));
      const result = await apiClient.get('/test');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/test'),
        expect.objectContaining({ method: 'GET' }),
      );
      expect(result).toEqual({ items: [1] });
    });

    it('appends query params', async () => {
      mockFetch.mockResolvedValue(jsonResponse({}));
      await apiClient.get('/test', { params: { page: 1, q: 'foo' } });
      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('page=1');
      expect(url).toContain('q=foo');
    });

    it('skips undefined params', async () => {
      mockFetch.mockResolvedValue(jsonResponse({}));
      await apiClient.get('/test', { params: { page: 1, q: undefined } });
      const url = mockFetch.mock.calls[0][0] as string;
      expect(url).toContain('page=1');
      expect(url).not.toContain('q=');
    });
  });

  describe('POST', () => {
    it('sends JSON body', async () => {
      mockFetch.mockResolvedValue(jsonResponse({ id: 1 }));
      await apiClient.post('/test', { name: 'foo' });
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(opts.body).toBe(JSON.stringify({ name: 'foo' }));
    });

    it('handles undefined body', async () => {
      mockFetch.mockResolvedValue(jsonResponse({}));
      await apiClient.post('/test');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.body).toBeUndefined();
    });
  });

  describe('PUT', () => {
    it('sends PUT request', async () => {
      mockFetch.mockResolvedValue(jsonResponse({ ok: true }));
      await apiClient.put('/test/1', { name: 'bar' });
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PUT');
    });
  });

  describe('PATCH', () => {
    it('sends PATCH request', async () => {
      mockFetch.mockResolvedValue(jsonResponse({ ok: true }));
      await apiClient.patch('/test/1', { stage: 'closed' });
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PATCH');
    });
  });

  describe('DELETE', () => {
    it('sends DELETE request', async () => {
      mockFetch.mockResolvedValue(jsonResponse({}));
      await apiClient.delete('/test/1');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
    });
  });

  describe('auth token', () => {
    it('attaches Bearer token from localStorage', async () => {
      mockStorage['access_token'] = 'test-jwt-token';
      mockFetch.mockResolvedValue(jsonResponse({}));
      await apiClient.get('/test');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBe('Bearer test-jwt-token');
    });

    it('omits Authorization header when no token', async () => {
      mockFetch.mockResolvedValue(jsonResponse({}));
      await apiClient.get('/test');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBeUndefined();
    });
  });

  describe('error handling', () => {
    it('throws ApiError on non-OK response', async () => {
      mockFetch.mockResolvedValue(jsonResponse({ detail: 'not found' }, 404));
      await expect(apiClient.get('/missing')).rejects.toThrow(ApiError);
    });

    it('dispatches auth:unauthorized on 401', async () => {
      mockFetch.mockResolvedValue(jsonResponse({ detail: 'unauth' }, 401));
      await expect(apiClient.get('/protected')).rejects.toThrow();
      expect(window.dispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'auth:unauthorized' }),
      );
    });

    it('removes tokens on 401', async () => {
      mockStorage['access_token'] = 'old-token';
      mockStorage['refresh_token'] = 'old-refresh';
      mockFetch.mockResolvedValue(jsonResponse({}, 401));
      await expect(apiClient.get('/protected')).rejects.toThrow();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token');
    });

    it('handles text error responses', async () => {
      const resp = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        headers: new Headers({ 'content-type': 'text/plain' }),
        json: () => Promise.reject(new Error('not json')),
        text: () => Promise.resolve('server error'),
      } as Response;
      mockFetch.mockResolvedValue(resp);
      await expect(apiClient.get('/broken')).rejects.toThrow(ApiError);
    });
  });

  describe('empty responses', () => {
    it('returns empty object for non-JSON responses', async () => {
      const resp = {
        ok: true,
        status: 204,
        statusText: 'No Content',
        headers: new Headers({}),
        json: () => Promise.reject(new Error('no json')),
        text: () => Promise.resolve(''),
      } as Response;
      mockFetch.mockResolvedValue(resp);
      const result = await apiClient.delete('/test/1');
      expect(result).toEqual({});
    });
  });
});
