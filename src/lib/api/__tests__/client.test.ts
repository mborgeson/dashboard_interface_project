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

    it('dispatches auth:unauthorized on 401 when no refresh token', async () => {
      mockFetch.mockResolvedValue(jsonResponse({ detail: 'unauth' }, 401));
      await expect(apiClient.get('/protected')).rejects.toThrow();
      expect(window.dispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'auth:unauthorized' }),
      );
    });

    it('removes tokens on 401 when refresh fails', async () => {
      mockStorage['access_token'] = 'old-token';
      mockStorage['refresh_token'] = 'old-refresh';
      // First call: original request returns 401
      // Second call: refresh endpoint also fails
      mockFetch
        .mockResolvedValueOnce(jsonResponse({}, 401))
        .mockResolvedValueOnce(jsonResponse({ detail: 'invalid refresh' }, 401));
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

  describe('token refresh on 401', () => {
    it('attempts refresh and retries original request on 401', async () => {
      mockStorage['access_token'] = 'expired-token';
      mockStorage['refresh_token'] = 'valid-refresh';

      // 1st fetch: original request → 401
      // 2nd fetch: refresh endpoint → success with new tokens
      // 3rd fetch: retry original request → success
      mockFetch
        .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
        .mockResolvedValueOnce(jsonResponse({
          access_token: 'new-access',
          refresh_token: 'new-refresh',
          token_type: 'bearer',
        }))
        .mockResolvedValueOnce(jsonResponse({ data: 'protected-data' }));

      const result = await apiClient.get('/protected');
      expect(result).toEqual({ data: 'protected-data' });

      // Verify tokens were updated in localStorage
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new-access');
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'new-refresh');

      // Verify 3 fetch calls: original, refresh, retry
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it('retries with the new access token in Authorization header', async () => {
      mockStorage['access_token'] = 'expired-token';
      mockStorage['refresh_token'] = 'valid-refresh';

      mockFetch
        .mockResolvedValueOnce(jsonResponse({}, 401))
        .mockResolvedValueOnce(jsonResponse({
          access_token: 'fresh-token',
          refresh_token: 'fresh-refresh',
          token_type: 'bearer',
        }))
        .mockResolvedValueOnce(jsonResponse({ ok: true }));

      await apiClient.get('/protected');

      // 3rd call is the retry — check it used the new token
      const retryCall = mockFetch.mock.calls[2];
      expect(retryCall[1].headers['Authorization']).toBe('Bearer fresh-token');
    });

    it('does not attempt refresh for the refresh endpoint itself', async () => {
      mockStorage['access_token'] = 'token';
      mockStorage['refresh_token'] = 'refresh';

      mockFetch.mockResolvedValue(jsonResponse({ detail: 'invalid' }, 401));

      // Calling refresh endpoint that returns 401 should NOT trigger another refresh
      await expect(apiClient.post('/auth/refresh', { refresh_token: 'bad' })).rejects.toThrow(ApiError);

      // Only 1 fetch call — no refresh attempt
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('clears auth and dispatches event when refresh fails', async () => {
      mockStorage['access_token'] = 'expired';
      mockStorage['refresh_token'] = 'also-expired';

      mockFetch
        .mockResolvedValueOnce(jsonResponse({}, 401))
        .mockResolvedValueOnce(jsonResponse({}, 401)); // refresh also fails

      await expect(apiClient.get('/protected')).rejects.toThrow(ApiError);

      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(window.dispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'auth:unauthorized' }),
      );
    });

    it('clears auth when retry after refresh also returns 401', async () => {
      mockStorage['access_token'] = 'expired';
      mockStorage['refresh_token'] = 'valid-refresh';

      mockFetch
        .mockResolvedValueOnce(jsonResponse({}, 401))         // original 401
        .mockResolvedValueOnce(jsonResponse({                  // refresh succeeds
          access_token: 'new-token',
          refresh_token: 'new-refresh',
          token_type: 'bearer',
        }))
        .mockResolvedValueOnce(jsonResponse({}, 401));         // retry also 401

      await expect(apiClient.get('/protected')).rejects.toThrow(ApiError);

      expect(window.dispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'auth:unauthorized' }),
      );
    });

    it('skips refresh when no refresh_token in localStorage', async () => {
      mockStorage['access_token'] = 'expired';
      // No refresh_token set

      mockFetch.mockResolvedValue(jsonResponse({}, 401));

      await expect(apiClient.get('/protected')).rejects.toThrow(ApiError);

      // Only 1 fetch — no refresh attempt
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(window.dispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'auth:unauthorized' }),
      );
    });
  });

  describe('empty responses', () => {
    it('returns null for non-JSON responses', async () => {
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
      expect(result).toBeNull();
    });
  });
});
