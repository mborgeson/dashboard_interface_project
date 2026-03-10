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
const etagCache = new Map<string, { etag: string; data: unknown }>();

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
    // Fallback: if somehow we got 304 without cache, treat as empty
  }

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }
    // Dispatch auth event on 401 so authStore can auto-clear state
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
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
        etagCache.set(url, { etag, data });
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
