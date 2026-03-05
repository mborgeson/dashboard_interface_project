/**
 * API module exports
 */
export { apiClient, ApiError } from './client';
export {
  fetchProperties,
  fetchPropertyById,
  fetchPortfolioSummary,
  type PropertiesResponse,
  type PropertyFiltersParams,
} from './properties';
export { fetchReportSettings, updateReportSettings } from './reporting';

/**
 * Convenience wrappers around apiClient for simpler call-sites.
 * Usage:  get<T>(endpoint, params?)  /  post<T>(endpoint, data?)  etc.
 */
import { apiClient } from './client';

export function get<T>(endpoint: string, params?: Record<string, unknown>): Promise<T> {
  return apiClient.get<T>(endpoint, { params: params as Record<string, string | number | boolean | undefined> });
}

export function post<T>(endpoint: string, data?: unknown, options?: { params?: Record<string, unknown> }): Promise<T> {
  return apiClient.post<T>(endpoint, data, {
    params: options?.params as Record<string, string | number | boolean | undefined>,
  });
}

export function put<T>(endpoint: string, data?: unknown): Promise<T> {
  return apiClient.put<T>(endpoint, data);
}

export function patch<T>(endpoint: string, data?: unknown): Promise<T> {
  return apiClient.patch<T>(endpoint, data);
}

export function del<T>(endpoint: string): Promise<T> {
  return apiClient.delete<T>(endpoint);
}

/** Default export so `import api from '@/lib/api'` works (used by extraction hooks). */
export const api = apiClient;
export default apiClient;
