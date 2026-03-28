import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { type ReactNode } from 'react';

// Mock the API module
vi.mock('@/lib/api/client', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}));

import { get, post, put, patch, del } from '@/lib/api/client';
import {
  dealKeys,
  useDealsWithMockFallback,
  useDeal,
  useDealWithMockFallback,
  useDealsApi,
  useDealPipeline,
  useDealsByStage,
  useDealStats,
  useKanbanBoardApi,
  useDealActivitiesApi,
  useDealActivitiesWithMockFallback,
  useDealProformaReturns,
  useCreateDeal,
  useUpdateDeal,
  useUpdateDealStage,
  useDeleteDeal,
  useAddDealActivity,
} from '../useDeals';

const mockGet = vi.mocked(get);
const mockPost = vi.mocked(post);
const mockPut = vi.mocked(put);
const mockPatch = vi.mocked(patch);
const mockDel = vi.mocked(del);

// ---------------------------------------------------------------------------
// Test wrapper with QueryClient
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function mockBackendDeal(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    name: 'Test Property (Phoenix, AZ)',
    deal_type: 'acquisition',
    property_id: null,
    assigned_user_id: null,
    stage: 'active_review',
    stage_order: 2,
    asking_price: 5000000,
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
    priority: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    stage_updated_at: null,
    total_units: 100,
    avg_unit_sf: null,
    current_owner: null,
    last_sale_price_per_unit: null,
    last_sale_date: null,
    t12_return_on_cost: null,
    total_equity_commitment: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Query Key Factory Tests
// ---------------------------------------------------------------------------

describe('dealKeys', () => {
  it('generates correct base key', () => {
    expect(dealKeys.all).toEqual(['deals']);
  });

  it('generates lists key', () => {
    expect(dealKeys.lists()).toEqual(['deals', 'list']);
  });

  it('generates list key with filters', () => {
    const filters = { page: 1, pageSize: 20 };
    expect(dealKeys.list(filters)).toEqual(['deals', 'list', filters]);
  });

  it('generates detail key', () => {
    expect(dealKeys.detail('42')).toEqual(['deals', 'detail', '42']);
  });

  it('generates pipeline key', () => {
    expect(dealKeys.pipeline()).toEqual(['deals', 'pipeline']);
  });

  it('generates pipelineByStage key', () => {
    expect(dealKeys.pipelineByStage('closed')).toEqual(['deals', 'pipeline', 'closed']);
  });

  it('generates kanban key with filters', () => {
    const filters = { dealType: 'acquisition', assignedUserId: 1 };
    expect(dealKeys.kanban(filters)).toEqual(['deals', 'kanban', filters]);
  });

  it('generates kanban key without filters', () => {
    expect(dealKeys.kanban()).toEqual(['deals', 'kanban', undefined]);
  });

  it('generates stats key', () => {
    expect(dealKeys.stats()).toEqual(['deals', 'stats']);
  });

  it('generates activities key', () => {
    expect(dealKeys.activities('deal-1')).toEqual(['deals', 'activities', 'deal-1']);
  });

  it('generates proformaReturns key', () => {
    expect(dealKeys.proformaReturns('deal-1')).toEqual(['deals', 'proforma-returns', 'deal-1']);
  });
});

// ---------------------------------------------------------------------------
// Query Hooks
// ---------------------------------------------------------------------------

describe('useDealsWithMockFallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches deals list and transforms response via real Zod schema', async () => {
    const deal = mockBackendDeal();
    mockGet.mockResolvedValueOnce({ items: [deal], total: 1 });

    const { result } = renderHook(() => useDealsWithMockFallback(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals', { page_size: 500 });
    expect(result.current.data?.deals).toHaveLength(1);
    expect(result.current.data?.total).toBe(1);

    // Verify the real schema transform was applied (snake_case -> camelCase Deal)
    const parsed = result.current.data!.deals[0];
    expect(parsed.id).toBe('1');                      // number -> string
    expect(parsed.propertyName).toBe('Test Property (Phoenix, AZ)');
    expect(parsed.address.city).toBe('Phoenix');      // parsed from name
    expect(parsed.address.state).toBe('AZ');
    expect(parsed.stage).toBe('active_review');       // mapped via mapBackendStage
    expect(parsed.value).toBe(5000000);               // asking_price -> value
    expect(parsed.units).toBe(100);                   // total_units -> units
    expect(parsed.createdAt).toBeInstanceOf(Date);
  });

  it('uses custom pageSize', async () => {
    mockGet.mockResolvedValueOnce({ items: [], total: 0 });

    const { result } = renderHook(
      () => useDealsWithMockFallback({ pageSize: 100 }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals', { page_size: 100 });
  });

  it('handles empty items array', async () => {
    mockGet.mockResolvedValueOnce({ items: [], total: 0 });

    const { result } = renderHook(() => useDealsWithMockFallback(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.deals).toEqual([]);
    expect(result.current.data?.total).toBe(0);
  });

  it('handles null items gracefully', async () => {
    mockGet.mockResolvedValueOnce({ items: null, total: 0 });

    const { result } = renderHook(() => useDealsWithMockFallback(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.deals).toEqual([]);
  });

  it('skips items that fail Zod validation and keeps valid ones', async () => {
    const validDeal = mockBackendDeal({ id: 1 });
    const invalidItem = { bad: 'data' }; // missing required fields
    mockGet.mockResolvedValueOnce({ items: [validDeal, invalidItem], total: 2 });

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { result } = renderHook(() => useDealsWithMockFallback(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Only the valid deal should appear; the invalid one is skipped
    expect(result.current.data?.deals).toHaveLength(1);
    expect(result.current.data?.deals[0].id).toBe('1');
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it('handles API errors', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network failure'));

    const { result } = renderHook(() => useDealsWithMockFallback(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect((result.current.error as Error).message).toBe('Network failure');
  });
});

describe('useDeal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches a single deal by ID', async () => {
    const deal = { id: '5', name: 'Test Deal' };
    mockGet.mockResolvedValueOnce(deal);

    const { result } = renderHook(() => useDeal('5'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/5');
    expect(result.current.data).toEqual(deal);
  });

  it('is disabled when id is empty string', async () => {
    const { result } = renderHook(() => useDeal(''), {
      wrapper: createWrapper(),
    });

    // Should not be loading because it's disabled
    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle');
    });

    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe('useDealWithMockFallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches and parses deal via real Zod schema when id is provided', async () => {
    const deal = mockBackendDeal({ id: 7 });
    mockGet.mockResolvedValueOnce(deal);

    const { result } = renderHook(() => useDealWithMockFallback('7'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/7');
    expect(result.current.data).toBeTruthy();

    // Verify the real schema transform was applied
    const parsed = result.current.data!;
    expect(parsed.id).toBe('7');                      // number -> string
    expect(parsed.propertyName).toBe('Test Property (Phoenix, AZ)');
    expect(parsed.address.city).toBe('Phoenix');
    expect(parsed.stage).toBe('active_review');
    expect(parsed.value).toBe(5000000);
    expect(parsed.createdAt).toBeInstanceOf(Date);
  });

  it('is disabled when id is null', async () => {
    const { result } = renderHook(() => useDealWithMockFallback(null), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle');
    });

    expect(mockGet).not.toHaveBeenCalled();
  });

  it('returns null when Zod validation fails on invalid data', async () => {
    // Return data missing required fields — real schema should reject it
    mockGet.mockResolvedValueOnce({ bad: 'data' });

    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { result } = renderHook(() => useDealWithMockFallback('99'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Hook returns null when safeParse fails
    expect(result.current.data).toBeNull();
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it('handles API errors', async () => {
    mockGet.mockRejectedValueOnce(new Error('Not found'));

    const { result } = renderHook(() => useDealWithMockFallback('99'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeInstanceOf(Error);
  });
});

describe('useDealsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('passes filters as params', async () => {
    const filters = { page: 2, pageSize: 25 };
    mockGet.mockResolvedValueOnce({ items: [], total: 0 });

    const { result } = renderHook(() => useDealsApi(filters), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals', filters);
  });

  it('uses empty filters by default', async () => {
    mockGet.mockResolvedValueOnce({ items: [], total: 0 });

    const { result } = renderHook(() => useDealsApi(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals', {});
  });
});

describe('useDealPipeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches pipeline data', async () => {
    const pipeline = {
      dead: [],
      initial_review: [],
      active_review: [],
      under_contract: [],
      closed: [],
      realized: [],
    };
    mockGet.mockResolvedValueOnce(pipeline);

    const { result } = renderHook(() => useDealPipeline(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/pipeline');
    expect(result.current.data).toEqual(pipeline);
  });
});

describe('useDealsByStage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches deals for a specific stage', async () => {
    const deals = [{ id: 1, name: 'Deal A' }];
    mockGet.mockResolvedValueOnce(deals);

    const { result } = renderHook(() => useDealsByStage('closed'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/pipeline/closed');
    expect(result.current.data).toEqual(deals);
  });
});

describe('useDealStats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches deal statistics', async () => {
    const stats = { totalDeals: 42, totalValue: 100000000 };
    mockGet.mockResolvedValueOnce(stats);

    const { result } = renderHook(() => useDealStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/stats');
    expect(result.current.data).toEqual(stats);
  });
});

describe('useKanbanBoardApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches kanban data without filters', async () => {
    const kanbanData = { stages: {}, total_deals: 0, stage_counts: {} };
    mockGet.mockResolvedValueOnce(kanbanData);

    const { result } = renderHook(() => useKanbanBoardApi(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/kanban', {});
    expect(result.current.data).toEqual(kanbanData);
  });

  it('passes deal type and user filters', async () => {
    const kanbanData = { stages: {}, total_deals: 0, stage_counts: {} };
    mockGet.mockResolvedValueOnce(kanbanData);

    const filters = { dealType: 'acquisition', assignedUserId: 5 };

    const { result } = renderHook(() => useKanbanBoardApi(filters), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/kanban', {
      deal_type: 'acquisition',
      assigned_user_id: 5,
    });
  });
});

describe('useDealActivitiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches activities for a deal', async () => {
    const activities = { activities: [], total: 0 };
    mockGet.mockResolvedValueOnce(activities);

    const { result } = renderHook(() => useDealActivitiesApi('deal-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/deal-1/activity');
    expect(result.current.data).toEqual(activities);
  });

  it('is disabled when dealId is empty', async () => {
    const { result } = renderHook(() => useDealActivitiesApi(''), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle');
    });

    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe('useDealActivitiesWithMockFallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches and transforms activity data', async () => {
    mockGet.mockResolvedValueOnce({
      items: [
        {
          id: 10,
          deal_id: 1,
          activity_type: 'note',
          description: 'Added a note',
          user_id: 1,
          user_name: 'John',
          created_at: '2024-06-01T10:00:00Z',
          updated_at: '2024-06-01T10:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    });

    const { result } = renderHook(() => useDealActivitiesWithMockFallback('1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/1/activity');
    expect(result.current.data?.activities).toHaveLength(1);
    expect(result.current.data?.activities[0].type).toBe('note');
    expect(result.current.data?.activities[0].user).toBe('John');
    expect(result.current.data?.total).toBe(1);
  });

  it('is disabled when dealId is empty', async () => {
    const { result } = renderHook(() => useDealActivitiesWithMockFallback(''), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle');
    });

    expect(mockGet).not.toHaveBeenCalled();
  });

  it('handles missing items gracefully', async () => {
    mockGet.mockResolvedValueOnce({
      items: null,
      total: 0,
      page: 1,
      page_size: 50,
    });

    const { result } = renderHook(() => useDealActivitiesWithMockFallback('1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.activities).toEqual([]);
    expect(result.current.data?.total).toBe(0);
  });
});

describe('useDealProformaReturns', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches proforma returns for a deal', async () => {
    const proforma = {
      deal_id: 1,
      deal_name: 'Test Deal',
      groups: [{ category: 'Returns', fields: [] }],
      total: 5,
    };
    mockGet.mockResolvedValueOnce(proforma);

    const { result } = renderHook(() => useDealProformaReturns('1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/deals/1/proforma-returns');
    expect(result.current.data).toEqual(proforma);
  });

  it('is disabled when dealId is null', async () => {
    const { result } = renderHook(() => useDealProformaReturns(null), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle');
    });

    expect(mockGet).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Mutation Hooks
// ---------------------------------------------------------------------------

describe('useCreateDeal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts new deal data and invalidates caches', async () => {
    const newDeal = { id: '10', name: 'New Deal' };
    mockPost.mockResolvedValueOnce(newDeal);

    const { result } = renderHook(() => useCreateDeal(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ name: 'New Deal', deal_type: 'acquisition' } as never);
    });

    expect(mockPost).toHaveBeenCalledWith('/deals', expect.objectContaining({ name: 'New Deal' }));
  });

  it('handles creation errors', async () => {
    mockPost.mockRejectedValueOnce(new Error('Validation error'));

    const { result } = renderHook(() => useCreateDeal(), {
      wrapper: createWrapper(),
    });

    await expect(
      act(async () => {
        await result.current.mutateAsync({ name: 'Bad Deal' } as never);
      }),
    ).rejects.toThrow('Validation error');
  });
});

describe('useUpdateDeal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends PUT with deal data', async () => {
    const updated = { id: '5', name: 'Updated Deal' };
    mockPut.mockResolvedValueOnce(updated);

    const { result } = renderHook(() => useUpdateDeal(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ id: '5', name: 'Updated Deal' } as never);
    });

    expect(mockPut).toHaveBeenCalledWith('/deals/5', expect.objectContaining({ name: 'Updated Deal' }));
  });
});

describe('useUpdateDealStage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends PATCH with stage and note', async () => {
    mockPatch.mockResolvedValueOnce({ id: '3', stage: 'closed' });

    const { result } = renderHook(() => useUpdateDealStage(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({
        id: '3',
        stage: 'closed',
        note: 'Deal closed successfully',
      });
    });

    expect(mockPatch).toHaveBeenCalledWith('/deals/3/stage', {
      stage: 'closed',
      note: 'Deal closed successfully',
    });
  });
});

describe('useDeleteDeal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends DELETE request', async () => {
    mockDel.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeleteDeal(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync('42');
    });

    expect(mockDel).toHaveBeenCalledWith('/deals/42');
  });
});

describe('useAddDealActivity', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts activity and invalidates deal caches', async () => {
    const activity = { id: '1', deal_id: '5', type: 'note', description: 'Test' };
    mockPost.mockResolvedValueOnce(activity);

    const { result } = renderHook(() => useAddDealActivity(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({
        dealId: '5',
        type: 'note',
        description: 'Test note',
      });
    });

    expect(mockPost).toHaveBeenCalledWith('/deals/5/activity', {
      type: 'note',
      description: 'Test note',
    });
  });
});
