import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useAuthStore } from './authStore';

// Mock the apiClient module
vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

import { apiClient } from '@/lib/api/client';

const mockStorage: Record<string, string> = {};
const originalLocalStorage = globalThis.localStorage;

beforeEach(() => {
  vi.clearAllMocks();
  Object.keys(mockStorage).forEach(k => delete mockStorage[k]);
  vi.stubGlobal('localStorage', {
    getItem: vi.fn((key: string) => mockStorage[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { mockStorage[key] = value; }),
    removeItem: vi.fn((key: string) => { delete mockStorage[key]; }),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  globalThis.localStorage = originalLocalStorage;
  // Reset store state
  useAuthStore.setState({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
  });
});

describe('authStore', () => {
  describe('login', () => {
    it('stores tokens and user on successful login', async () => {
      vi.mocked(apiClient.post).mockResolvedValueOnce({
        access_token: 'access-123',
        refresh_token: 'refresh-456',
        token_type: 'bearer',
      });
      vi.mocked(apiClient.get).mockResolvedValueOnce({
        id: 1,
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'analyst',
        is_active: true,
      });

      await useAuthStore.getState().login('test@example.com', 'password');

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.accessToken).toBe('access-123');
      expect(state.refreshToken).toBe('refresh-456');
      expect(state.user?.email).toBe('test@example.com');
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'access-123');
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'refresh-456');
    });
  });

  describe('logout', () => {
    it('clears all auth state and localStorage', async () => {
      // Set up authenticated state
      useAuthStore.setState({
        user: { id: 1, email: 'test@example.com', full_name: 'Test', role: 'analyst', is_active: true },
        accessToken: 'token',
        refreshToken: 'refresh',
        isAuthenticated: true,
        isLoading: false,
      });
      mockStorage['access_token'] = 'token';
      mockStorage['refresh_token'] = 'refresh';

      vi.mocked(apiClient.post).mockResolvedValueOnce({});

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.user).toBeNull();
      expect(state.accessToken).toBeNull();
      expect(state.refreshToken).toBeNull();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token');
    });
  });

  describe('refreshAccessToken', () => {
    it('returns true and updates tokens on success', async () => {
      mockStorage['refresh_token'] = 'old-refresh';

      vi.mocked(apiClient.post).mockResolvedValueOnce({
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        token_type: 'bearer',
      });

      const result = await useAuthStore.getState().refreshAccessToken();

      expect(result).toBe(true);
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new-access');
      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'new-refresh');

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe('new-access');
      expect(state.refreshToken).toBe('new-refresh');
    });

    it('returns false when no refresh token exists', async () => {
      // No refresh_token in storage
      const result = await useAuthStore.getState().refreshAccessToken();
      expect(result).toBe(false);
      expect(apiClient.post).not.toHaveBeenCalled();
    });

    it('returns false when refresh endpoint fails', async () => {
      mockStorage['refresh_token'] = 'expired-refresh';

      vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('401'));

      const result = await useAuthStore.getState().refreshAccessToken();
      expect(result).toBe(false);
    });

    it('calls the correct endpoint with refresh_token', async () => {
      mockStorage['refresh_token'] = 'my-refresh-token';

      vi.mocked(apiClient.post).mockResolvedValueOnce({
        access_token: 'new',
        refresh_token: 'new-r',
        token_type: 'bearer',
      });

      await useAuthStore.getState().refreshAccessToken();

      expect(apiClient.post).toHaveBeenCalledWith(
        '/auth/refresh',
        { refresh_token: 'my-refresh-token' },
      );
    });
  });

  describe('initialize', () => {
    it('sets isAuthenticated when token is valid', async () => {
      mockStorage['access_token'] = 'valid-token';
      mockStorage['refresh_token'] = 'valid-refresh';

      vi.mocked(apiClient.get).mockResolvedValueOnce({
        id: 1,
        email: 'test@example.com',
        full_name: 'Test',
        role: 'analyst',
        is_active: true,
      });

      await useAuthStore.getState().initialize();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.user?.email).toBe('test@example.com');
    });

    it('clears state when no token exists', async () => {
      await useAuthStore.getState().initialize();

      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
    });

    it('clears tokens on initialization failure', async () => {
      mockStorage['access_token'] = 'bad-token';

      vi.mocked(apiClient.get).mockRejectedValueOnce(new Error('401'));

      await useAuthStore.getState().initialize();

      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(useAuthStore.getState().isLoading).toBe(false);
    });
  });
});
