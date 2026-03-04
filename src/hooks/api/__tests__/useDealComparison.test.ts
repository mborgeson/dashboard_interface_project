import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { type ReactNode } from 'react';
import {
  useDealComparisonWithMockFallback,
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

/** Build a mock backend DealResponse (snake_case, matching backendDealSchema) */
function mockBackendDeal(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    name: 'Test Property (Phoenix, AZ)',
    deal_type: 'acquisition',
    property_id: null,
    assigned_user_id: null,
    stage: 'active_review',
    stage_order: 2,
    asking_price: '5000000',
    offer_price: null,
    final_price: null,
    projected_irr: null,
    projected_coc: null,
    projected_equity_multiple: null,
    hold_period_years: null,
    initial_contact_date: null,
    actual_close_date: null,
    source: null,
    broker_name: null,
    notes: null,
    investment_thesis: null,
    deal_score: null,
    priority: 'medium',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    stage_updated_at: null,
    total_units: 100,
    avg_unit_sf: 850,
    current_owner: null,
    last_sale_price_per_unit: null,
    last_sale_date: null,
    t12_return_on_cost: null,
    levered_irr: 0.15,
    levered_moic: 1.8,
    total_equity_commitment: null,
    ...overrides,
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
          mockBackendDeal({ id: 1, name: 'Prop A (Phoenix, AZ)' }),
          mockBackendDeal({ id: 2, name: 'Prop B (Mesa, AZ)' }),
        ],
        comparison_summary: {},
        metric_comparisons: [],
        deal_count: 2,
        compared_at: '2024-01-15T12:00:00Z',
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['1', '2']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });
    });
  });

  describe('with API data', () => {
    it('fetches data from API and parses via Zod', async () => {
      const mockApiResponse = {
        deals: [
          mockBackendDeal({ id: 1, name: 'Prop A (Phoenix, AZ)', levered_irr: 0.15 }),
          mockBackendDeal({ id: 2, name: 'Prop B (Mesa, AZ)', levered_irr: 0.18 }),
        ],
        comparison_summary: {},
        metric_comparisons: [],
        deal_count: 2,
        compared_at: '2024-01-15T12:00:00Z',
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['1', '2']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockGet).toHaveBeenCalledWith('/deals/compare', {
        ids: '1,2',
      });

      expect(result.current.data?.deals).toHaveLength(2);
      // Zod parses to Deal objects with camelCase keys
      expect(result.current.data?.deals[0].leveredIrr).toBe(0.15);
      expect(result.current.data?.deals[1].leveredIrr).toBe(0.18);
    });

    it('transforms dates correctly', async () => {
      const mockApiResponse = {
        deals: [
          mockBackendDeal({ id: 1 }),
          mockBackendDeal({ id: 2 }),
        ],
        comparison_summary: {},
        metric_comparisons: [],
        deal_count: 2,
        compared_at: '2024-01-15T12:00:00Z',
      };

      mockGet.mockResolvedValue(mockApiResponse);

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['1', '2']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data?.comparisonDate).toBeInstanceOf(Date);
      expect(result.current.data?.generatedAt).toBeInstanceOf(Date);
      expect(result.current.data?.deals[0].createdAt).toBeInstanceOf(Date);
    });

    it('propagates API errors', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(
        () => useDealComparisonWithMockFallback(['1', '2']),
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
    });
  });
});
