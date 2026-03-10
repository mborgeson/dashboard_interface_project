/**
 * API Client for backend communication
 * Handles requests to the FastAPI backend
 *
 * Features:
 * - ETag-based conditional requests: caches ETags per URL and sends
 *   If-None-Match on GET requests. On 304 responses, returns cached data
 *   instead of re-parsing the (empty) response body.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/** Per-URL ETag + cached response body for conditional GET requests. */
const ETAG_CACHE_MAX_SIZE = 100;
const etagCache = new Map<string, { etag: string; data: unknown }>();

/** Add an entry to the ETag cache with LRU-like eviction. */
function etagCacheSet(url: string, entry: { etag: string; data: unknown }) {
  // Delete first so re-insertion moves key to end (most-recent)
  etagCache.delete(url);
  etagCache.set(url, entry);
  // Evict oldest entry (first key) when over limit
  if (etagCache.size > ETAG_CACHE_MAX_SIZE) {
    const oldest = etagCache.keys().next().value;
    if (oldest !== undefined) {
      etagCache.delete(oldest);
    }
  }
}

/** Guard against concurrent refresh attempts — only one in-flight at a time. */
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns true if successful, false otherwise.
 * Uses localStorage directly to avoid circular dependency with authStore.
 */
async function attemptTokenRefresh(): Promise<boolean> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return false;

  // Deduplicate concurrent refresh calls
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      if (data.access_token && data.refresh_token) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        return true;
      }
      return false;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options;

  // Build URL with query parameters
  let url = `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // Detect URLSearchParams body — let fetch set Content-Type automatically
  const isFormData = fetchOptions.body instanceof URLSearchParams;

  // Set default headers (skip Content-Type for form-urlencoded — fetch handles it)
  const headers: HeadersInit = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...fetchOptions.headers,
  };

  // Attach auth token from localStorage
  const token = localStorage.getItem('access_token');
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  // For GET requests, send If-None-Match if we have a cached ETag
  const method = fetchOptions.method ?? 'GET';
  if (method === 'GET') {
    const cached = etagCache.get(url);
    if (cached) {
      (headers as Record<string, string>)['If-None-Match'] = cached.etag;
    }
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  // Handle 304 Not Modified — return cached data
  if (response.status === 304) {
    const cached = etagCache.get(url);
    if (cached) {
      return cached.data as T;
    }
    // Cache was cleared (e.g., on logout) between request and response.
    // Retry without If-None-Match to get a fresh response.
    const retryHeaders = { ...headers } as Record<string, string>;
    delete retryHeaders['If-None-Match'];
    const freshResponse = await fetch(url, { ...fetchOptions, headers: retryHeaders });
    if (freshResponse.ok) {
      const ct = freshResponse.headers.get('content-type');
      if (ct?.includes('application/json')) {
        const data = await freshResponse.json();
        const etag = freshResponse.headers.get('etag');
        if (etag) {
          etagCacheSet(url, { etag, data });
        }
        return data;
      }
      return {} as T;
    }
    throw new ApiError(freshResponse.status, `API Error: ${freshResponse.statusText}`);
  }

  if (!response.ok) {
    // On 401, try token refresh before giving up (skip for the refresh endpoint itself)
    if (response.status === 401 && !endpoint.endsWith('/auth/refresh')) {
      const refreshed = await attemptTokenRefresh();
      if (refreshed) {
        // Retry the original request with the new access token
        const newToken = localStorage.getItem('access_token');
        const retryHeaders = { ...headers } as Record<string, string>;
        if (newToken) {
          retryHeaders['Authorization'] = `Bearer ${newToken}`;
        }
        // Remove If-None-Match for retry to avoid stale 304
        delete retryHeaders['If-None-Match'];

        const retryResponse = await fetch(url, {
          ...fetchOptions,
          headers: retryHeaders,
        });

        if (retryResponse.ok) {
          const contentType = retryResponse.headers.get('content-type');
          if (contentType?.includes('application/json')) {
            const data = await retryResponse.json();
            if (method === 'GET') {
              const etag = retryResponse.headers.get('etag');
              if (etag) {
                etagCacheSet(url, { etag, data });
              }
            }
            return data;
          }
          return {} as T;
        }
        // Retry also failed — fall through to logout
      }

      // Refresh failed or retry failed — clear auth
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      throw new ApiError(401, 'API Error: Unauthorized');
    }

    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }
    throw new ApiError(response.status, `API Error: ${response.statusText}`, errorData);
  }

  // Handle empty responses
  const contentType = response.headers.get('content-type');
  if (contentType?.includes('application/json')) {
    const data = await response.json();

    // Cache ETag for GET responses
    if (method === 'GET') {
      const etag = response.headers.get('etag');
      if (etag) {
        etagCacheSet(url, { etag, data });
      }
    }

    return data;
  }

  return {} as T;
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data instanceof URLSearchParams ? data : data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data instanceof URLSearchParams ? data : data ? JSON.stringify(data) : undefined,
    }),

  patch: <T>(endpoint: string, data?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data instanceof URLSearchParams ? data : data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};
