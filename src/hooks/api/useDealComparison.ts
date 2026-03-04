import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get } from '@/lib/api';
import type { Deal } from '@/types/deal';
import { backendDealSchema } from '@/lib/api/schemas/deal';
import { z } from 'zod';

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

export interface DealComparisonWithFallbackResponse {
  deals: DealForComparison[];
  comparisonDate: Date;
  generatedAt: Date;
}

// ============================================================================
// Response schema — backend now returns DealResponse objects
// ============================================================================

const comparisonResponseSchema = z.object({
  deals: z.array(backendDealSchema),
  comparison_summary: z.unknown(),
  metric_comparisons: z.unknown(),
  deal_count: z.number(),
  compared_at: z.string(),
});

// ============================================================================
// Query Key Factory
// ============================================================================

export const dealComparisonKeys = {
  all: ['dealComparison'] as const,
  comparison: (ids: string[]) => [...dealComparisonKeys.all, 'compare', ids.sort().join(',')] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to fetch deal comparison data — uses Zod schema to parse enriched DealResponse
 */
export function useDealComparisonWithMockFallback(
  dealIds: string[],
  options?: Omit<UseQueryOptions<DealComparisonWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: dealComparisonKeys.comparison(dealIds),
    queryFn: async (): Promise<DealComparisonWithFallbackResponse> => {
      const raw = await get<unknown>('/deals/compare', {
        ids: dealIds.join(','),
      });

      const parsed = comparisonResponseSchema.parse(raw);

      return {
        deals: parsed.deals as DealForComparison[],
        comparisonDate: new Date(parsed.compared_at),
        generatedAt: new Date(parsed.compared_at),
      };
    },
    enabled: dealIds.length >= 2,
    staleTime: 1000 * 60 * 5,
    ...options,
  });
}

// ============================================================================
// Convenience Aliases
// ============================================================================

export const useDealComparison = useDealComparisonWithMockFallback;
