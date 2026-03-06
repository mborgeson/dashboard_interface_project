import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AxiosResponse, InternalAxiosRequestConfig, AxiosHeaders } from 'axios';

// Mock localStorage
const mockStorage: Record<string, string> = {};
vi.stubGlobal('localStorage', {
  getItem: vi.fn((key: string) => mockStorage[key] || null),
  setItem: vi.fn((key: string, value: string) => { mockStorage[key] = value; }),
  removeItem: vi.fn((key: string) => { delete mockStorage[key]; }),
});
vi.stubGlobal('dispatchEvent', vi.fn());

// Mock axios before importing the module
const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: { use: vi.fn() },
    response: { use: vi.fn() },
  },
};

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
  AxiosError: class AxiosError extends Error {
    response?: { status: number };
    constructor(message?: string) {
      super(message);
    }
  },
}));

describe('api module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.keys(mockStorage).forEach(k => delete mockStorage[k]);
  });

  describe('HTTP helper functions', () => {
    it('get() calls api.get and returns data', async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { items: [1, 2] } });
      const { get } = await import('../api');
      const result = await get('/test', { page: 1 });
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/test', { params: { page: 1 } });
      expect(result).toEqual({ items: [1, 2] });
    });

    it('post() calls api.post and returns data', async () => {
      mockAxiosInstance.post.mockResolvedValue({ data: { id: 1 } });
      const { post } = await import('../api');
      const result = await post('/test', { name: 'foo' });
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/test', { name: 'foo' });
      expect(result).toEqual({ id: 1 });
    });

    it('put() calls api.put and returns data', async () => {
      mockAxiosInstance.put.mockResolvedValue({ data: { updated: true } });
      const { put } = await import('../api');
      const result = await put('/test/1', { name: 'bar' });
      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/test/1', { name: 'bar' });
      expect(result).toEqual({ updated: true });
    });

    it('patch() calls api.patch and returns data', async () => {
      mockAxiosInstance.patch.mockResolvedValue({ data: { patched: true } });
      const { patch } = await import('../api');
      const result = await patch('/test/1', { stage: 'closed' });
      expect(mockAxiosInstance.patch).toHaveBeenCalledWith('/test/1', { stage: 'closed' });
      expect(result).toEqual({ patched: true });
    });

    it('del() calls api.delete and returns data', async () => {
      mockAxiosInstance.delete.mockResolvedValue({ data: undefined });
      const { del } = await import('../api');
      const result = await del('/test/1');
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/test/1');
      expect(result).toBeUndefined();
    });
  });

  it('exports default api instance', async () => {
    const mod = await import('../api');
    expect(mod.default).toBeDefined();
    expect(mod.api).toBeDefined();
  });
});
