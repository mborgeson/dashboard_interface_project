import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post, put, patch, del } from '@/lib/api';
import { USE_MOCK_DATA, IS_DEV } from '@/lib/config';
import { mockDeals } from '@/data/mockDeals';
import type { Deal } from '@/types/deal';
import type {
  DealFilters,
  DealApiResponse,
  DealListResponse,
  DealCreateInput,
  DealUpdateInput,
  DealStageUpdateInput,
  DealStageApi,
} from '@/types/api';

// ============================================================================
// Query Key Factory
// ============================================================================

export const dealKeys = {
  all: ['deals'] as const,
  lists: () => [...dealKeys.all, 'list'] as const,
  list: (filters: DealFilters) => [...dealKeys.lists(), filters] as const,
  details: () => [...dealKeys.all, 'detail'] as const,
  detail: (id: string) => [...dealKeys.details(), id] as const,
  pipeline: () => [...dealKeys.all, 'pipeline'] as const,
  pipelineByStage: (stage: DealStageApi) => [...dealKeys.pipeline(), stage] as const,
  stats: () => [...dealKeys.all, 'stats'] as const,
};

// ============================================================================
// Query Hooks (with mock data fallback for development)
// ============================================================================

/**
 * Response type for deals with fallback
 */
export interface DealsWithFallbackResponse {
  deals: Deal[];
  total: number;
}

/**
 * Hook to fetch all deals with mock data fallback
 * Falls back to mock data if API is unavailable or USE_MOCK_DATA is true
 */
export function useDealsWithMockFallback(
  options?: Omit<UseQueryOptions<DealsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.lists(),
    queryFn: async (): Promise<DealsWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        // Return mock data for development/testing
        return {
          deals: mockDeals,
          total: mockDeals.length,
        };
      }

      try {
        const response = await get<DealListResponse>('/deals');
        // Transform API response to Deal[] format
        // DealListResponse is PaginatedResponse<DealApiResponse> with 'data' property
        return {
          deals: response.data?.map(transformDealFromApi) ?? mockDeals,
          total: response.total ?? mockDeals.length,
        };
      } catch (error) {
        // Fall back to mock data if API fails in development
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock deals:', error);
          return {
            deals: mockDeals,
            total: mockDeals.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Transform API deal response to local Deal type
 * API response uses camelCase properties
 */
function transformDealFromApi(apiDeal: DealApiResponse): Deal {
  return {
    id: apiDeal.id,
    propertyName: apiDeal.propertyName || '',
    address: {
      street: apiDeal.address?.street || '',
      city: apiDeal.address?.city || '',
      state: apiDeal.address?.state || '',
    },
    value: apiDeal.value || 0,
    capRate: apiDeal.capRate || 0,
    stage: apiDeal.stage as Deal['stage'],
    daysInStage: apiDeal.daysInStage || 0,
    totalDaysInPipeline: apiDeal.totalDaysInPipeline || 0,
    assignee: apiDeal.assignee || '',
    propertyType: apiDeal.propertyType || '',
    units: apiDeal.units || 0,
    createdAt: new Date(apiDeal.createdAt || Date.now()),
    timeline: (apiDeal.timeline || []).map((event) => ({
      id: event.id,
      date: new Date(event.date),
      stage: event.stage as Deal['stage'],
      description: event.description,
      user: event.user,
    })),
    notes: apiDeal.notes,
  };
}

// ============================================================================
// Query Hooks (API-first, no mock fallback)
// ============================================================================

/**
 * Fetch paginated list of deals with filters (API-first, no mock fallback)
 */
export function useDealsApi(
  filters: DealFilters = {},
  options?: Omit<UseQueryOptions<DealListResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.list(filters),
    queryFn: () => get<DealListResponse>('/deals', filters as Record<string, unknown>),
    ...options,
  });
}

/**
 * Fetch a single deal by ID
 */
export function useDeal(
  id: string,
  options?: Omit<UseQueryOptions<DealApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.detail(id),
    queryFn: () => get<DealApiResponse>(`/deals/${id}`),
    enabled: !!id,
    ...options,
  });
}

/**
 * Fetch deals grouped by pipeline stage (for kanban board)
 */
export function useDealPipeline(
  options?: Omit<UseQueryOptions<DealPipelineResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.pipeline(),
    queryFn: () => get<DealPipelineResponse>('/deals/pipeline'),
    ...options,
  });
}

/**
 * Fetch deals for a specific pipeline stage
 */
export function useDealsByStage(
  stage: DealStageApi,
  options?: Omit<UseQueryOptions<DealApiResponse[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.pipelineByStage(stage),
    queryFn: () => get<DealApiResponse[]>(`/deals/pipeline/${stage}`),
    ...options,
  });
}

/**
 * Fetch deal pipeline statistics
 */
export function useDealStats(
  options?: Omit<UseQueryOptions<DealStatsResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.stats(),
    queryFn: () => get<DealStatsResponse>('/deals/stats'),
    ...options,
  });
}

// Local types for pipeline and stats responses
interface DealPipelineResponse {
  lead: DealApiResponse[];
  underwriting: DealApiResponse[];
  loi: DealApiResponse[];
  due_diligence: DealApiResponse[];
  closing: DealApiResponse[];
  closed_won: DealApiResponse[];
  closed_lost: DealApiResponse[];
}

interface DealStatsResponse {
  totalDeals: number;
  totalValue: number;
  averageCapRate: number;
  averageDaysInPipeline: number;
  conversionRate: number;
  dealsByStage: Record<DealStageApi, number>;
  valueByStage: Record<DealStageApi, number>;
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new deal
 */
export function useCreateDeal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DealCreateInput) =>
      post<DealApiResponse, DealCreateInput>('/deals', data),
    onSuccess: () => {
      // Invalidate all deal lists and pipeline
      queryClient.invalidateQueries({ queryKey: dealKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dealKeys.pipeline() });
      queryClient.invalidateQueries({ queryKey: dealKeys.stats() });
    },
  });
}

/**
 * Update an existing deal
 */
export function useUpdateDeal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: DealUpdateInput) =>
      put<DealApiResponse, Omit<DealUpdateInput, 'id'>>(`/deals/${id}`, data),
    onSuccess: (data) => {
      // Update the specific deal in cache
      queryClient.setQueryData(dealKeys.detail(data.id), data);
      // Invalidate lists and pipeline for consistency
      queryClient.invalidateQueries({ queryKey: dealKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dealKeys.pipeline() });
      queryClient.invalidateQueries({ queryKey: dealKeys.stats() });
    },
  });
}

/**
 * Update deal stage (move in pipeline)
 * Supports optimistic updates for smooth drag-and-drop UX
 */
export function useUpdateDealStage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, stage, note }: DealStageUpdateInput) =>
      patch<DealApiResponse, { stage: DealStageApi; note?: string }>(
        `/deals/${id}/stage`,
        { stage, note }
      ),
    // Optimistic update for smooth UX
    onMutate: async ({ id, stage }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: dealKeys.detail(id) });
      await queryClient.cancelQueries({ queryKey: dealKeys.pipeline() });

      // Snapshot the previous value
      const previousDeal = queryClient.getQueryData<DealApiResponse>(dealKeys.detail(id));
      const previousPipeline = queryClient.getQueryData<DealPipelineResponse>(dealKeys.pipeline());

      // Optimistically update the deal
      if (previousDeal) {
        queryClient.setQueryData(dealKeys.detail(id), {
          ...previousDeal,
          stage,
          daysInStage: 0,
        });
      }

      // Return context for rollback
      return { previousDeal, previousPipeline };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousDeal) {
        queryClient.setQueryData(
          dealKeys.detail(context.previousDeal.id),
          context.previousDeal
        );
      }
      if (context?.previousPipeline) {
        queryClient.setQueryData(dealKeys.pipeline(), context.previousPipeline);
      }
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey: dealKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dealKeys.pipeline() });
      queryClient.invalidateQueries({ queryKey: dealKeys.stats() });
    },
  });
}

/**
 * Delete a deal
 */
export function useDeleteDeal() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => del<void>(`/deals/${id}`),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: dealKeys.detail(id) });
      // Invalidate lists and pipeline
      queryClient.invalidateQueries({ queryKey: dealKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dealKeys.pipeline() });
      queryClient.invalidateQueries({ queryKey: dealKeys.stats() });
    },
  });
}

// ============================================================================
// Prefetch Utilities
// ============================================================================

/**
 * Prefetch a single deal
 */
export function usePrefetchDeal() {
  const queryClient = useQueryClient();

  return (id: string) => {
    queryClient.prefetchQuery({
      queryKey: dealKeys.detail(id),
      queryFn: () => get<DealApiResponse>(`/deals/${id}`),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Prefetch deals for a specific stage
 */
export function usePrefetchDealStage() {
  const queryClient = useQueryClient();

  return (stage: DealStageApi) => {
    queryClient.prefetchQuery({
      queryKey: dealKeys.pipelineByStage(stage),
      queryFn: () => get<DealApiResponse[]>(`/deals/pipeline/${stage}`),
      staleTime: 5 * 60 * 1000,
    });
  };
}
