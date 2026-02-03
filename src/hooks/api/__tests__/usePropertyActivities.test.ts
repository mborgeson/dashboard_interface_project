import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { type ReactNode } from 'react';
import {
  usePropertyActivitiesWithMockFallback,
  usePropertyActivitiesApi,
  propertyActivityKeys,
  type PropertyActivityType,
} from '../usePropertyActivities';
import * as api from '@/lib/api';

// Mock the API module
vi.mock('@/lib/api', () => ({
  get: vi.fn(),
  post: vi.fn(),
}));

// Create a wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('propertyActivityKeys', () => {
  it('generates correct query keys', () => {
    expect(propertyActivityKeys.all).toEqual(['propertyActivities']);
    expect(propertyActivityKeys.lists()).toEqual(['propertyActivities', 'list']);
    expect(propertyActivityKeys.list('prop-123')).toEqual([
      'propertyActivities',
      'list',
      'prop-123',
      undefined,
    ]);
    expect(propertyActivityKeys.list('prop-123', ['view', 'edit'])).toEqual([
      'propertyActivities',
      'list',
      'prop-123',
      ['view', 'edit'],
    ]);
    expect(propertyActivityKeys.detail('act-456')).toEqual([
      'propertyActivities',
      'detail',
      'act-456',
    ]);
  });
});

describe('usePropertyActivitiesWithMockFallback', () => {
  const mockGet = vi.mocked(api.get);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('with API data', () => {
    it('fetches data from API', async () => {
      const mockApiResponse = {
        activities: [
          {
            id: 'act-1',
            property_id: 'prop-123',
            type: 'view' as PropertyActivityType,
            description: 'Viewed property',
            user_name: 'Test User',
            user_avatar: null,
            timestamp: '2024-01-15T10:00:00Z',
            metadata: {},
          },
        ],
        total: 1,
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => usePropertyActivitiesWithMockFallback('prop-123'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockGet).toHaveBeenCalledWith(
        '/properties/prop-123/activities',
        expect.any(Object)
      );
      expect(result.current.data?.activities).toHaveLength(1);
    });

    it('transforms snake_case to camelCase', async () => {
      const mockApiResponse = {
        activities: [
          {
            id: 'act-1',
            property_id: 'prop-123',
            type: 'view' as PropertyActivityType,
            description: 'Viewed property',
            user_name: 'Test User',
            user_avatar: 'https://example.com/avatar.jpg',
            timestamp: '2024-01-15T10:00:00Z',
            metadata: { some_key: 'value' },
          },
        ],
        total: 1,
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => usePropertyActivitiesWithMockFallback('prop-123'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const activity = result.current.data?.activities[0];
      expect(activity).toBeDefined();
      expect(activity?.propertyId).toBe('prop-123');
      expect(activity?.userName).toBe('Test User');
      expect(activity?.userAvatar).toBe('https://example.com/avatar.jpg');
    });

    it('converts timestamp string to Date object', async () => {
      const mockApiResponse = {
        activities: [
          {
            id: 'act-1',
            property_id: 'prop-123',
            type: 'view' as PropertyActivityType,
            description: 'Viewed property',
            user_name: 'Test User',
            timestamp: '2024-01-15T10:00:00Z',
            metadata: {},
          },
        ],
        total: 1,
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => usePropertyActivitiesWithMockFallback('prop-123'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const activity = result.current.data?.activities[0];
      expect(activity?.timestamp).toBeInstanceOf(Date);
    });

    it('sorts activities by timestamp descending', async () => {
      const mockApiResponse = {
        activities: [
          {
            id: 'act-1',
            property_id: 'prop-123',
            type: 'view' as PropertyActivityType,
            description: 'First',
            user_name: 'User A',
            timestamp: '2024-01-15T10:00:00Z',
            metadata: {},
          },
          {
            id: 'act-2',
            property_id: 'prop-123',
            type: 'edit' as PropertyActivityType,
            description: 'Second',
            user_name: 'User B',
            timestamp: '2024-01-16T10:00:00Z',
            metadata: {},
          },
        ],
        total: 2,
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => usePropertyActivitiesWithMockFallback('prop-123'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const activities = result.current.data?.activities ?? [];
      expect(activities.length).toBe(2);
      for (let i = 1; i < activities.length; i++) {
        expect(activities[i - 1].timestamp.getTime()).toBeGreaterThanOrEqual(
          activities[i].timestamp.getTime()
        );
      }
    });

    it('passes activity types filter to API', async () => {
      mockGet.mockResolvedValue({ activities: [], total: 0 });

      const { result } = renderHook(
        () =>
          usePropertyActivitiesWithMockFallback('prop-123', {
            activityTypes: ['view', 'edit'],
          }),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockGet).toHaveBeenCalledWith(
        '/properties/prop-123/activities',
        { activity_types: 'view,edit' }
      );
    });

    it('propagates API errors', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(
        () => usePropertyActivitiesWithMockFallback('prop-123'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
    });
  });

  describe('query options', () => {
    it('is disabled when propertyId is empty', async () => {
      const { result } = renderHook(
        () => usePropertyActivitiesWithMockFallback(''),
        { wrapper: createWrapper() }
      );

      // Should not fetch
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('is enabled when propertyId is provided', async () => {
      mockGet.mockResolvedValue({ activities: [], total: 0 });

      const { result } = renderHook(
        () => usePropertyActivitiesWithMockFallback('prop-123'),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });
    });
  });
});

describe('usePropertyActivitiesApi', () => {
  const mockGet = vi.mocked(api.get);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls API directly without fallback', async () => {
    const mockApiResponse = {
      activities: [],
      total: 0,
    };

    mockGet.mockResolvedValue(mockApiResponse);

    const { result } = renderHook(
      () => usePropertyActivitiesApi('prop-123'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith(
      '/properties/prop-123/activities',
      expect.any(Object)
    );
  });

  it('does not fall back to mock data on error', async () => {
    mockGet.mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(
      () => usePropertyActivitiesApi('prop-123'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });
});
