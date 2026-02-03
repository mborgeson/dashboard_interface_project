import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { type ReactNode } from 'react';
import {
  useDealComparisonWithMockFallback,
  useDealComparisonApi,
  dealComparisonKeys,
} from '../useDealComparison';
import * as api from '@/lib/api';

// Mock the API module
vi.mock('@/lib/api', () => ({
  get: vi.fn(),
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

describe('dealComparisonKeys', () => {
  it('generates correct query keys', () => {
    expect(dealComparisonKeys.all).toEqual(['dealComparison']);

    // IDs are sorted for consistent cache keys
    expect(dealComparisonKeys.comparison(['deal-002', 'deal-001'])).toEqual([
      'dealComparison',
      'compare',
      'deal-001,deal-002',
    ]);

    expect(dealComparisonKeys.comparison(['deal-001', 'deal-002', 'deal-003'])).toEqual([
      'dealComparison',
      'compare',
      'deal-001,deal-002,deal-003',
    ]);
  });
});

describe('useDealComparisonWithMockFallback', () => {
  const mockGet = vi.mocked(api.get);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('query enabling', () => {
    it('is disabled when dealIds has less than 2 items', async () => {
      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001']),
        { wrapper: createWrapper() }
      );

      // Should not fetch
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
      expect(mockGet).not.toHaveBeenCalled();
    });

    it('is disabled when dealIds is empty', async () => {
      const { result } = renderHook(
        () => useDealComparisonWithMockFallback([]),
        { wrapper: createWrapper() }
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('is enabled when dealIds has 2+ items', async () => {
      const mockApiResponse = {
        deals: [
          {
            id: 'deal-001',
            propertyName: 'Test Property 1',
            address: { street: '123 Test St', city: 'Phoenix', state: 'AZ' },
            value: 5000000,
            capRate: 5.5,
            stage: 'underwriting',
            daysInStage: 10,
            totalDaysInPipeline: 30,
            assignee: 'Test User',
            propertyType: 'Garden',
            units: 100,
            createdAt: '2024-01-01T00:00:00Z',
            timeline: [],
            noi: 275000,
          },
          {
            id: 'deal-002',
            propertyName: 'Test Property 2',
            address: { street: '456 Test Ave', city: 'Mesa', state: 'AZ' },
            value: 7500000,
            capRate: 5.8,
            stage: 'loi',
            daysInStage: 5,
            totalDaysInPipeline: 45,
            assignee: 'Test User 2',
            propertyType: 'Mid-Rise',
            units: 150,
            createdAt: '2024-02-01T00:00:00Z',
            timeline: [],
            noi: 435000,
          },
        ],
        comparisonDate: '2024-01-15T00:00:00Z',
        generatedAt: '2024-01-15T12:00:00Z',
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });
    });
  });

  describe('with API data', () => {
    it('fetches data from API', async () => {
      const mockApiResponse = {
        deals: [
          {
            id: 'deal-001',
            propertyName: 'API Property 1',
            address: { street: '123 API St', city: 'Phoenix', state: 'AZ' },
            value: 5000000,
            capRate: 5.5,
            stage: 'underwriting',
            daysInStage: 10,
            totalDaysInPipeline: 30,
            assignee: 'Test User',
            propertyType: 'Garden',
            units: 100,
            createdAt: '2024-01-01T00:00:00Z',
            timeline: [],
            noi: 275000,
            pricePerSqft: 250,
            projectedIrr: 0.15,
            cashOnCash: 0.08,
            equityMultiple: 1.8,
            totalSf: 85000,
            occupancyRate: 0.95,
          },
          {
            id: 'deal-002',
            propertyName: 'API Property 2',
            address: { street: '456 API Ave', city: 'Mesa', state: 'AZ' },
            value: 7500000,
            capRate: 5.8,
            stage: 'loi',
            daysInStage: 5,
            totalDaysInPipeline: 45,
            assignee: 'Test User 2',
            propertyType: 'Mid-Rise',
            units: 150,
            createdAt: '2024-02-01T00:00:00Z',
            timeline: [],
            noi: 435000,
            pricePerSqft: 280,
            projectedIrr: 0.18,
            cashOnCash: 0.10,
            equityMultiple: 2.0,
            totalSf: 127500,
            occupancyRate: 0.97,
          },
        ],
        comparisonDate: '2024-01-15T00:00:00Z',
        generatedAt: '2024-01-15T12:00:00Z',
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockGet).toHaveBeenCalledWith('/deals/compare', {
        ids: 'deal-001,deal-002',
      });

      expect(result.current.data?.deals).toHaveLength(2);
    });

    it('transforms API response correctly', async () => {
      const mockApiResponse = {
        deals: [
          {
            id: 'deal-001',
            propertyName: 'API Property 1',
            address: { street: '123 Test St', city: 'Phoenix', state: 'AZ' },
            value: 5000000,
            capRate: 5.5,
            stage: 'underwriting',
            daysInStage: 10,
            totalDaysInPipeline: 30,
            assignee: 'Test User',
            propertyType: 'Garden',
            units: 100,
            createdAt: '2024-01-01T00:00:00Z',
            timeline: [],
            noi: 275000,
          },
        ],
        comparisonDate: '2024-01-15T00:00:00Z',
        generatedAt: '2024-01-15T12:00:00Z',
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Check date transformation
      expect(result.current.data?.comparisonDate).toBeInstanceOf(Date);
      expect(result.current.data?.generatedAt).toBeInstanceOf(Date);

      // Check deal createdAt transformation
      const deal = result.current.data?.deals[0];
      expect(deal?.createdAt).toBeInstanceOf(Date);
    });

    it('propagates API errors', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
    });

    it('handles empty API response gracefully', async () => {
      mockGet.mockResolvedValue({
        deals: null,
        comparisonDate: '2024-01-15T00:00:00Z',
        generatedAt: '2024-01-15T12:00:00Z',
      });

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data?.deals).toEqual([]);
    });
  });
});

describe('useDealComparisonApi', () => {
  const mockGet = vi.mocked(api.get);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls API directly without fallback', async () => {
    const mockApiResponse = {
      deals: [],
      comparisonDate: '2024-01-15T00:00:00Z',
      generatedAt: '2024-01-15T12:00:00Z',
    };

    mockGet.mockResolvedValue(mockApiResponse);

    const { result } = renderHook(
      () => useDealComparisonApi(['deal-001', 'deal-002']),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/compare', {
      ids: 'deal-001,deal-002',
    });
  });

  it('does not fall back to mock data on error', async () => {
    mockGet.mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(
      () => useDealComparisonApi(['deal-001', 'deal-002']),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('is disabled when dealIds has less than 2 items', async () => {
    const { result } = renderHook(
      () => useDealComparisonApi(['deal-001']),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(mockGet).not.toHaveBeenCalled();
  });
});
