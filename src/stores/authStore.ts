import { create } from 'zustand';
import { apiClient } from '@/lib/api/client';

interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    // OAuth2PasswordRequestForm requires x-www-form-urlencoded with "username" field
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const data = await apiClient.post<{ access_token: string; refresh_token: string; token_type: string }>(
      '/auth/login',
      params,
    );

    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);

    // Fetch user profile
    const user = await apiClient.get<User>('/auth/me');

    set({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  logout: async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore errors — clear state regardless
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  refreshAccessToken: async () => {
    const storedRefreshToken = localStorage.getItem('refresh_token');
    if (!storedRefreshToken) return false;

    try {
      const data = await apiClient.post<{ access_token: string; refresh_token: string; token_type: string }>(
        '/auth/refresh',
        { refresh_token: storedRefreshToken },
      );

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });

      return true;
    } catch {
      return false;
    }
  },

  initialize: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isLoading: false });
      return;
    }

    try {
      const user = await apiClient.get<User>('/auth/me');
      set({
        accessToken: token,
        refreshToken: localStorage.getItem('refresh_token'),
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      // Access token failed — the client.ts 401 handler will have already
      // attempted a refresh via attemptTokenRefresh(). If it succeeded,
      // the /auth/me retry should have worked. If we're here, auth is gone.
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({ isLoading: false });
    }
  },
}));

// Listen for 401 events from the API client to auto-clear auth state.
// Guard against SSR/test environments where window may not exist.
if (typeof window !== 'undefined') window.addEventListener('auth:unauthorized', () => {
  const { isAuthenticated } = useAuthStore.getState();
  if (isAuthenticated) {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }
});
