import axios, { AxiosError } from 'axios';
import type { InternalAxiosRequestConfig } from 'axios';
import { API_URL } from './config';

// Create axios instance with base configuration
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle 401 Unauthorized - redirect to login or refresh token
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // Could dispatch a logout action or redirect here
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      window.dispatchEvent(new CustomEvent('auth:forbidden'));
    }

    // Handle network errors
    if (!error.response) {
      window.dispatchEvent(new CustomEvent('network:error'));
    }

    return Promise.reject(error);
  }
);

// Type-safe API helper functions
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await api.get<T>(url, { params });
  return response.data;
}

export async function post<T, D = unknown>(url: string, data?: D): Promise<T> {
  const response = await api.post<T>(url, data);
  return response.data;
}

export async function put<T, D = unknown>(url: string, data?: D): Promise<T> {
  const response = await api.put<T>(url, data);
  return response.data;
}

export async function patch<T, D = unknown>(url: string, data?: D): Promise<T> {
  const response = await api.patch<T>(url, data);
  return response.data;
}

export async function del<T>(url: string): Promise<T> {
  const response = await api.delete<T>(url);
  return response.data;
}

// Export default instance
export default api;
