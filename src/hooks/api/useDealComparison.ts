import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get } from '@/lib/api';
import type { Deal } from '@/types/deal';

// ============================================================================
// Types
// ============================================================================

export type ComparisonMetric =
  | 'cap_rate'
  | 'noi'
  | 'price_per_sqft'
  | 'projected_irr'
  | 'cash_on_cash'
  | 'equity_multiple'
  | 'total_units'
  | 'total_sf'
  | 'occupancy_rate';

export interface DealForComparison extends Deal {
  // Extended metrics for comparison (may be computed or from API)
  noi?: number;
  pricePerSqft?: number;
  projectedIrr?: number;
  cashOnCash?: number;
  equityMultiple?: number;
  totalSf?: number;
  occupancyRate?: number;
}

export interface DealComparisonApiResponse {
  deals: DealForComparison[];
  comparisonDate: string;
  generatedAt: string;
}

export interface DealComparisonWithFallbackResponse {
  deals: DealForComparison[];
  comparisonDate: Date;
  generatedAt: Date;
}

// ============================================================================
// Query Key Factory
// ============================================================================

export const dealComparisonKeys = {
  all: ['dealComparison'] as const,
  comparison: (ids: string[]) => [...dealComparisonKeys.all, 'compare', ids.sort().join(',')] as const,
};

/**
 * Transform API deal response to DealForComparison
 */
function transformDealFromApi(apiDeal: DealForComparison): DealForComparison {
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
    stage: apiDeal.stage,
    daysInStage: apiDeal.daysInStage || 0,
    totalDaysInPipeline: apiDeal.totalDaysInPipeline || 0,
    assignee: apiDeal.assignee || '',
    propertyType: apiDeal.propertyType || '',
    units: apiDeal.units || 0,
    avgUnitSf: apiDeal.avgUnitSf || 0,
    currentOwner: apiDeal.currentOwner || '',
    lastSalePricePerUnit: apiDeal.lastSalePricePerUnit || 0,
    lastSaleDate: apiDeal.lastSaleDate || '',
    t12ReturnOnCost: apiDeal.t12ReturnOnCost || 0,
    leveredIrr: apiDeal.leveredIrr || 0,
    leveredMoic: apiDeal.leveredMoic || 0,
    totalEquityCommitment: apiDeal.totalEquityCommitment || 0,
    createdAt: new Date(apiDeal.createdAt || Date.now()),
    timeline: (apiDeal.timeline || []).map((event) => ({
      id: event.id,
      date: new Date(event.date),
      stage: event.stage,
      description: event.description,
      user: event.user,
    })),
    notes: apiDeal.notes,
    // Comparison-specific fields
    noi: apiDeal.noi,
    pricePerSqft: apiDeal.pricePerSqft,
    projectedIrr: apiDeal.projectedIrr,
    cashOnCash: apiDeal.cashOnCash,
    equityMultiple: apiDeal.equityMultiple,
    totalSf: apiDeal.totalSf,
    occupancyRate: apiDeal.occupancyRate,
  };
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to fetch deal comparison data with mock data fallback
 * Errors propagate to React Query error state
 */
export function useDealComparisonWithMockFallback(
  dealIds: string[],
  options?: Omit<UseQueryOptions<DealComparisonWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealComparisonKeys.comparison(dealIds),
    queryFn: async (): Promise<DealComparisonWithFallbackResponse> => {
      const response = await get<DealComparisonApiResponse>('/deals/compare', {
        ids: dealIds.join(','),
      });

      return {
        deals: response.deals?.map(transformDealFromApi) ?? [],
        comparisonDate: new Date(response.comparisonDate),
        generatedAt: new Date(response.generatedAt),
      };
    },
    enabled: dealIds.length >= 2,
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch deal comparison data from API (API-first, no mock fallback)
 */
export function useDealComparisonApi(
  dealIds: string[],
  options?: Omit<UseQueryOptions<DealComparisonApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealComparisonKeys.comparison(dealIds),
    queryFn: () =>
      get<DealComparisonApiResponse>('/deals/compare', {
        ids: dealIds.join(','),
      }),
    enabled: dealIds.length >= 2,
    ...options,
  });
}

// ============================================================================
// Convenience Aliases
// ============================================================================

/**
 * Primary hook for deal comparison - uses mock fallback pattern
 */
export const useDealComparison = useDealComparisonWithMockFallback;
