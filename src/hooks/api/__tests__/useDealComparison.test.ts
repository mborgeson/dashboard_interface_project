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
import * as config from '@/lib/config';

// Mock the API and config modules
vi.mock('@/lib/api', () => ({
  get: vi.fn(),
}));

vi.mock('@/lib/config', () => ({
  USE_MOCK_DATA: false,
  IS_DEV: true,
}));

// Mock the mockDeals data
vi.mock('@/data/mockDeals', () => ({
  mockDeals: [
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
      createdAt: new Date('2024-01-01'),
      timeline: [],
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
      createdAt: new Date('2024-02-01'),
      timeline: [],
    },
    {
      id: 'deal-003',
      propertyName: 'Test Property 3',
      address: { street: '789 Test Blvd', city: 'Tempe', state: 'AZ' },
      value: 10000000,
      capRate: 5.2,
      stage: 'due_diligence',
      daysInStage: 20,
      totalDaysInPipeline: 60,
      assignee: 'Test User 3',
      propertyType: 'Garden',
      units: 200,
      createdAt: new Date('2024-03-01'),
      timeline: [],
    },
  ],
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
    vi.mocked(config).USE_MOCK_DATA = false;
    vi.mocked(config).IS_DEV = true;
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
      vi.mocked(config).USE_MOCK_DATA = true;

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });
    });
  });

  describe('with mock data enabled', () => {
    beforeEach(() => {
      vi.mocked(config).USE_MOCK_DATA = true;
    });

    it('returns mock data when USE_MOCK_DATA is true', async () => {
      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toBeDefined();
      expect(result.current.data?.deals).toBeDefined();
      expect(result.current.data?.deals.length).toBe(2);

      // API should not be called when using mock data
      expect(mockGet).not.toHaveBeenCalled();
    });

    it('filters mock deals by provided IDs', async () => {
      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-003']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const deals = result.current.data?.deals ?? [];
      expect(deals.length).toBe(2);
      expect(deals.map((d) => d.id).sort()).toEqual(['deal-001', 'deal-003']);
    });

    it('generates comparison metrics for mock deals', async () => {
      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const deals = result.current.data?.deals ?? [];
      deals.forEach((deal) => {
        expect(deal.noi).toBeDefined();
        expect(deal.pricePerSqft).toBeDefined();
        expect(deal.projectedIrr).toBeDefined();
        expect(deal.cashOnCash).toBeDefined();
        expect(deal.equityMultiple).toBeDefined();
        expect(deal.totalSf).toBeDefined();
        expect(deal.occupancyRate).toBeDefined();
      });
    });

    it('returns date objects for comparisonDate and generatedAt', async () => {
      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data?.comparisonDate).toBeInstanceOf(Date);
      expect(result.current.data?.generatedAt).toBeInstanceOf(Date);
    });
  });

  describe('with API data', () => {
    beforeEach(() => {
      vi.mocked(config).USE_MOCK_DATA = false;
    });

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

    it('falls back to mock data on API error in dev mode', async () => {
      vi.mocked(config).IS_DEV = true;
      mockGet.mockRejectedValue(new Error('Network error'));

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should have mock data as fallback
      expect(result.current.data?.deals).toBeDefined();
      expect(result.current.error).toBeNull();

      consoleSpy.mockRestore();
    });

    it('throws error in production mode when API fails', async () => {
      vi.mocked(config).IS_DEV = false;
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
  });

  describe('loading and error states', () => {
    it('shows loading state initially', () => {
      vi.mocked(config).USE_MOCK_DATA = true;

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['deal-001', 'deal-002']),
        { wrapper: createWrapper() }
      );

      // Initially loading
      expect(result.current.isLoading).toBe(true);
    });

    it('handles empty API response gracefully', async () => {
      vi.mocked(config).USE_MOCK_DATA = false;
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
