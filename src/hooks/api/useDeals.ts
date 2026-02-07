import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post, put, patch, del } from '@/lib/api';
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
import { backendDealSchema, mapBackendStage } from '@/lib/api/schemas/deal';

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
  kanban: (filters?: KanbanFilters) => [...dealKeys.all, 'kanban', filters] as const,
  stats: () => [...dealKeys.all, 'stats'] as const,
  activities: (dealId: string) => [...dealKeys.all, 'activities', dealId] as const,
};

// ============================================================================
// Filter Types
// ============================================================================

export interface KanbanFilters {
  dealType?: string;
  assignedUserId?: number;
}

// ============================================================================
// Query Hooks
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
 * Errors propagate to React Query error state
 */
export function useDealsWithMockFallback(
  options?: Omit<UseQueryOptions<DealsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.lists(),
    queryFn: async (): Promise<DealsWithFallbackResponse> => {
      // Backend returns { items: [...], total, page, page_size }
      const response = await get<{ items: unknown[]; total: number }>('/deals', { page_size: 100 });
      return {
        deals: response.items?.map((item) => backendDealSchema.parse(item)) ?? [],
        total: response.total ?? 0,
      };
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}



/**
 * Hook to fetch Kanban board data
 * Errors propagate to React Query error state
 */
export function useKanbanBoardWithMockFallback(
  filters?: KanbanFilters,
  options?: Omit<UseQueryOptions<KanbanBoardWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.kanban(filters),
    queryFn: async (): Promise<KanbanBoardWithFallbackResponse> => {
      const params: Record<string, unknown> = {};
      if (filters?.dealType) params.deal_type = filters.dealType;
      if (filters?.assignedUserId) params.assigned_user_id = filters.assignedUserId;

      const frontendStages: DealStageApi[] = [
        'dead', 'initial_review', 'active_review', 'under_contract', 'closed', 'realized',
      ];

      try {
        const response = await get<KanbanBoardApiResponse>('/deals/kanban', params);

        const stages: Record<DealStageApi, { deals: Deal[]; count: number; totalValue: number }> = {} as never;
        for (const fs of frontendStages) {
          stages[fs] = { deals: [], count: 0, totalValue: 0 };
        }

        // Map backend stages to frontend stages and transform deals
        for (const [backendStage, data] of Object.entries(response.stages)) {
          const frontendStage = mapBackendStage(backendStage);
          const deals = (data.deals as unknown[]).map((d) => backendDealSchema.parse(d));
          stages[frontendStage].deals.push(...deals);
          stages[frontendStage].count += data.count;
          stages[frontendStage].totalValue += data.totalValue;
        }

        const stageCounts: Record<string, number> = {};
        for (const [stage, data] of Object.entries(stages)) {
          stageCounts[stage] = data.count;
        }

        return {
          stages,
          totalDeals: response.total_deals,
          stageCounts,
        };
      } catch {
        // Fallback: fetch all deals and group by stage
        const dealsResponse = await get<{ items: unknown[]; total: number }>('/deals', { page_size: 100 });
        const allDeals = dealsResponse.items?.map((item) => backendDealSchema.parse(item)) ?? [];

        const stages: Record<DealStageApi, { deals: Deal[]; count: number; totalValue: number }> = {} as never;
        for (const fs of frontendStages) {
          stages[fs] = { deals: [], count: 0, totalValue: 0 };
        }

        for (const deal of allDeals) {
          const stage = deal.stage;
          if (stages[stage]) {
            stages[stage].deals.push(deal);
            stages[stage].count += 1;
            stages[stage].totalValue += deal.value;
          }
        }

        const stageCounts: Record<string, number> = {};
        for (const [stage, data] of Object.entries(stages)) {
          stageCounts[stage] = data.count;
        }

        return {
          stages,
          totalDeals: allDeals.length,
          stageCounts,
        };
      }
    },
    staleTime: 1000 * 60 * 2,
    ...options,
  });
}

/**
 * Hook to fetch deal activities with mock data fallback
 * Uses deal timeline as mock activity data
 */
export function useDealActivitiesWithMockFallback(
  dealId: string,
  options?: Omit<UseQueryOptions<DealActivitiesWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.activities(dealId),
    queryFn: async (): Promise<DealActivitiesWithFallbackResponse> => {
      const response = await get<DealActivitiesApiResponse>(`/deals/${dealId}/activities`);
      return {
        activities: response.activities.map((a) => ({
          id: a.id,
          dealId: a.deal_id,
          type: a.type,
          description: a.description,
          user: a.user,
          timestamp: new Date(a.timestamp),
          metadata: a.metadata,
        })),
        total: response.total,
      };
    },
    enabled: !!dealId,
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
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
 * Hook to fetch a single deal with mock data fallback
 * Errors propagate to React Query error state
 */
export function useDealWithMockFallback(
  id: string | null,
  options?: Omit<UseQueryOptions<Deal | null>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.detail(id ?? ''),
    queryFn: async (): Promise<Deal | null> => {
      if (!id) return null;

      const response = await get<unknown>(`/deals/${id}`);
      return backendDealSchema.parse(response);
    },
    enabled: !!id,
    staleTime: 1000 * 60 * 5, // 5 minutes
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

/**
 * Fetch Kanban board data from API (API-first)
 */
export function useKanbanBoardApi(
  filters?: KanbanFilters,
  options?: Omit<UseQueryOptions<KanbanBoardApiResponse>, 'queryKey' | 'queryFn'>
) {
  const params: Record<string, unknown> = {};
  if (filters?.dealType) params.deal_type = filters.dealType;
  if (filters?.assignedUserId) params.assigned_user_id = filters.assignedUserId;

  return useQuery({
    queryKey: dealKeys.kanban(filters),
    queryFn: () => get<KanbanBoardApiResponse>('/deals/kanban', params),
    ...options,
  });
}

/**
 * Fetch deal activities from API (API-first)
 */
export function useDealActivitiesApi(
  dealId: string,
  options?: Omit<UseQueryOptions<DealActivitiesApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealKeys.activities(dealId),
    queryFn: () => get<DealActivitiesApiResponse>(`/deals/${dealId}/activities`),
    enabled: !!dealId,
    ...options,
  });
}

// Local types for pipeline and stats responses
interface DealPipelineResponse {
  dead: DealApiResponse[];
  initial_review: DealApiResponse[];
  active_review: DealApiResponse[];
  under_contract: DealApiResponse[];
  closed: DealApiResponse[];
  realized: DealApiResponse[];
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
// Kanban Board Types
// ============================================================================

export interface KanbanStageData {
  stage: DealStageApi;
  deals: DealApiResponse[];
  count: number;
  totalValue: number;
}

export interface KanbanBoardApiResponse {
  stages: Record<DealStageApi, KanbanStageData>;
  total_deals: number;
  stage_counts: Record<DealStageApi, number>;
}

export interface KanbanBoardWithFallbackResponse {
  stages: Record<DealStageApi, { deals: Deal[]; count: number; totalValue: number }>;
  totalDeals: number;
  stageCounts: Record<DealStageApi, number>;
}

// ============================================================================
// Activity Types
// ============================================================================

export interface DealActivityApiResponse {
  id: string;
  deal_id: string;
  type: 'stage_change' | 'note' | 'document' | 'call' | 'email' | 'meeting' | 'other';
  description: string;
  user: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface DealActivitiesApiResponse {
  activities: DealActivityApiResponse[];
  total: number;
}

export interface DealActivity {
  id: string;
  dealId: string;
  type: 'stage_change' | 'note' | 'document' | 'call' | 'email' | 'meeting' | 'other';
  description: string;
  user: string;
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

export interface DealActivitiesWithFallbackResponse {
  activities: DealActivity[];
  total: number;
}

export interface AddActivityInput {
  dealId: string;
  type: DealActivity['type'];
  description: string;
  user?: string;
  metadata?: Record<string, unknown>;
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

/**
 * Add activity to a deal
 */
export function useAddDealActivity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ dealId, ...data }: AddActivityInput) =>
      post<DealActivityApiResponse, Omit<AddActivityInput, 'dealId'>>(
        `/deals/${dealId}/activity`,
        data
      ),
    onSuccess: (_, variables) => {
      // Invalidate activities for this deal
      queryClient.invalidateQueries({ queryKey: dealKeys.activities(variables.dealId) });
      // Also invalidate deal detail as timeline may have changed
      queryClient.invalidateQueries({ queryKey: dealKeys.detail(variables.dealId) });
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

// ============================================================================
// Convenience Aliases
// ============================================================================

/**
 * Primary hook for Kanban board - uses mock fallback pattern
 */
export const useKanbanBoard = useKanbanBoardWithMockFallback;

/**
 * Primary hook for deal activities - uses mock fallback pattern
 */
export const useDealActivities = useDealActivitiesWithMockFallback;
