import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get } from '@/lib/api';
import { USE_MOCK_DATA, IS_DEV } from '@/lib/config';
import {
  phoenixMSAOverview,
  economicIndicators,
  marketTrends,
  monthlyMarketData,
  submarketMetrics,
} from '@/data/mockMarketData';
import type {
  SubmarketMetrics,
  MarketTrend,
  EconomicIndicator,
  MSAOverview,
  MonthlyMarketData,
} from '@/types/market';

// ============================================================================
// API Types
// ============================================================================

export interface MarketOverviewApiResponse {
  msa_overview: {
    population: number;
    employment: number;
    gdp: number;
    population_growth: number;
    employment_growth: number;
    gdp_growth: number;
    last_updated: string;
  };
  economic_indicators: Array<{
    indicator: string;
    value: number;
    yoy_change: number;
    unit: string;
  }>;
  last_updated: string;
  source: string;
}

export interface SubmarketsApiResponse {
  submarkets: Array<{
    name: string;
    avg_rent: number;
    rent_growth: number;
    occupancy: number;
    cap_rate: number;
    inventory: number;
    absorption: number;
  }>;
  total_inventory: number;
  total_absorption: number;
  average_occupancy: number;
  average_rent_growth: number;
  last_updated: string;
  source: string;
}

export interface MarketTrendsApiResponse {
  trends: Array<{
    month: string;
    rent_growth: number;
    occupancy: number;
    cap_rate: number;
  }>;
  monthly_data: Array<{
    month: string;
    rent_growth: number;
    occupancy: number;
    cap_rate: number;
    employment: number;
    population: number;
  }>;
  period: string;
  last_updated: string;
  source: string;
}

export interface PropertyComparableApi {
  id: string;
  name: string;
  address: string;
  submarket: string;
  units: number;
  year_built: number;
  avg_rent: number;
  occupancy: number;
  sale_price: number | null;
  sale_date: string | null;
  cap_rate: number | null;
}

export interface ComparablesApiResponse {
  comparables: PropertyComparableApi[];
  total: number;
  radius_miles: number;
  last_updated: string;
  source: string;
}

// ============================================================================
// Query Key Factory
// ============================================================================

export const marketDataKeys = {
  all: ['marketData'] as const,
  overview: () => [...marketDataKeys.all, 'overview'] as const,
  submarkets: () => [...marketDataKeys.all, 'submarkets'] as const,
  trends: (periodMonths: number) => [...marketDataKeys.all, 'trends', periodMonths] as const,
  comparables: (filters: ComparableFilters) =>
    [...marketDataKeys.all, 'comparables', filters] as const,
};

export interface ComparableFilters {
  property_id?: string;
  submarket?: string;
  radius_miles?: number;
  limit?: number;
}

// ============================================================================
// Transform Functions
// ============================================================================

function transformMSAOverview(api: MarketOverviewApiResponse['msa_overview']): MSAOverview {
  return {
    population: api.population,
    employment: api.employment,
    gdp: api.gdp,
    populationGrowth: api.population_growth,
    employmentGrowth: api.employment_growth,
    gdpGrowth: api.gdp_growth,
    lastUpdated: api.last_updated,
  };
}

function transformEconomicIndicator(
  api: MarketOverviewApiResponse['economic_indicators'][0]
): EconomicIndicator {
  return {
    indicator: api.indicator,
    value: api.value,
    yoyChange: api.yoy_change,
    unit: api.unit,
  };
}

function transformSubmarket(api: SubmarketsApiResponse['submarkets'][0]): SubmarketMetrics {
  return {
    name: api.name,
    avgRent: api.avg_rent,
    rentGrowth: api.rent_growth,
    occupancy: api.occupancy,
    capRate: api.cap_rate,
    inventory: api.inventory,
    absorption: api.absorption,
  };
}

function transformTrend(api: MarketTrendsApiResponse['trends'][0]): MarketTrend {
  return {
    month: api.month,
    rentGrowth: api.rent_growth,
    occupancy: api.occupancy,
    capRate: api.cap_rate,
  };
}

function transformMonthlyData(api: MarketTrendsApiResponse['monthly_data'][0]): MonthlyMarketData {
  return {
    month: api.month,
    rentGrowth: api.rent_growth,
    occupancy: api.occupancy,
    capRate: api.cap_rate,
    employment: api.employment,
    population: api.population,
  };
}

// ============================================================================
// Response Types with Fallback
// ============================================================================

export interface MarketOverviewWithFallbackResponse {
  msaOverview: MSAOverview;
  economicIndicators: EconomicIndicator[];
}

export interface SubmarketsWithFallbackResponse {
  submarkets: SubmarketMetrics[];
  totalInventory: number;
  totalAbsorption: number;
  averageOccupancy: number;
  averageRentGrowth: number;
}

export interface MarketTrendsWithFallbackResponse {
  trends: MarketTrend[];
  monthlyData: MonthlyMarketData[];
  period: string;
}

export interface ComparablesWithFallbackResponse {
  comparables: PropertyComparableApi[];
  total: number;
  radiusMiles: number;
}

// ============================================================================
// Query Hooks (with mock data fallback)
// ============================================================================

/**
 * Hook to fetch market overview with mock data fallback
 */
export function useMarketOverviewWithMockFallback(
  options?: Omit<UseQueryOptions<MarketOverviewWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.overview(),
    queryFn: async (): Promise<MarketOverviewWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        return {
          msaOverview: phoenixMSAOverview,
          economicIndicators: economicIndicators,
        };
      }

      try {
        const response = await get<MarketOverviewApiResponse>('/market/overview');
        return {
          msaOverview: transformMSAOverview(response.msa_overview),
          economicIndicators: response.economic_indicators.map(transformEconomicIndicator),
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock market overview:', error);
          return {
            msaOverview: phoenixMSAOverview,
            economicIndicators: economicIndicators,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 15, // 15 minutes - market data changes less frequently
    ...options,
  });
}

/**
 * Hook to fetch submarket data with mock data fallback
 */
export function useSubmarketsWithMockFallback(
  options?: Omit<UseQueryOptions<SubmarketsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.submarkets(),
    queryFn: async (): Promise<SubmarketsWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        const totalInventory = submarketMetrics.reduce((sum, s) => sum + s.inventory, 0);
        const totalAbsorption = submarketMetrics.reduce((sum, s) => sum + s.absorption, 0);
        const avgOccupancy =
          submarketMetrics.reduce((sum, s) => sum + s.occupancy * s.inventory, 0) / totalInventory;
        const avgRentGrowth =
          submarketMetrics.reduce((sum, s) => sum + s.rentGrowth * s.inventory, 0) / totalInventory;

        return {
          submarkets: submarketMetrics,
          totalInventory,
          totalAbsorption,
          averageOccupancy: avgOccupancy,
          averageRentGrowth: avgRentGrowth,
        };
      }

      try {
        const response = await get<SubmarketsApiResponse>('/market/submarkets');
        return {
          submarkets: response.submarkets.map(transformSubmarket),
          totalInventory: response.total_inventory,
          totalAbsorption: response.total_absorption,
          averageOccupancy: response.average_occupancy,
          averageRentGrowth: response.average_rent_growth,
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock submarkets:', error);
          const totalInventory = submarketMetrics.reduce((sum, s) => sum + s.inventory, 0);
          return {
            submarkets: submarketMetrics,
            totalInventory,
            totalAbsorption: submarketMetrics.reduce((sum, s) => sum + s.absorption, 0),
            averageOccupancy:
              submarketMetrics.reduce((sum, s) => sum + s.occupancy * s.inventory, 0) /
              totalInventory,
            averageRentGrowth:
              submarketMetrics.reduce((sum, s) => sum + s.rentGrowth * s.inventory, 0) /
              totalInventory,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 15, // 15 minutes
    ...options,
  });
}

/**
 * Hook to fetch market trends with mock data fallback
 */
export function useMarketTrendsWithMockFallback(
  periodMonths: number = 12,
  options?: Omit<UseQueryOptions<MarketTrendsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.trends(periodMonths),
    queryFn: async (): Promise<MarketTrendsWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        return {
          trends: marketTrends.slice(0, periodMonths),
          monthlyData: monthlyMarketData.slice(0, periodMonths),
          period: `${periodMonths}M`,
        };
      }

      try {
        const response = await get<MarketTrendsApiResponse>('/market/trends', {
          period_months: periodMonths,
        });
        return {
          trends: response.trends.map(transformTrend),
          monthlyData: response.monthly_data.map(transformMonthlyData),
          period: response.period,
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock market trends:', error);
          return {
            trends: marketTrends.slice(0, periodMonths),
            monthlyData: monthlyMarketData.slice(0, periodMonths),
            period: `${periodMonths}M`,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 15, // 15 minutes
    ...options,
  });
}

/**
 * Hook to fetch property comparables with mock data fallback
 */
export function useComparablesWithMockFallback(
  filters: ComparableFilters = {},
  options?: Omit<UseQueryOptions<ComparablesWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.comparables(filters),
    queryFn: async (): Promise<ComparablesWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        // Return empty comparables in mock mode - no mock data defined
        return {
          comparables: [],
          total: 0,
          radiusMiles: filters.radius_miles || 5,
        };
      }

      try {
        const response = await get<ComparablesApiResponse>(
          '/market/comparables',
          filters as Record<string, unknown>
        );
        return {
          comparables: response.comparables,
          total: response.total,
          radiusMiles: response.radius_miles,
        };
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, falling back to empty comparables:', error);
          return {
            comparables: [],
            total: 0,
            radiusMiles: filters.radius_miles || 5,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 10, // 10 minutes
    ...options,
  });
}

// ============================================================================
// Query Hooks (API-first, no mock fallback)
// ============================================================================

/**
 * Fetch market overview (API-first)
 */
export function useMarketOverviewApi(
  options?: Omit<UseQueryOptions<MarketOverviewApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.overview(),
    queryFn: () => get<MarketOverviewApiResponse>('/market/overview'),
    ...options,
  });
}

/**
 * Fetch submarkets (API-first)
 */
export function useSubmarketsApi(
  options?: Omit<UseQueryOptions<SubmarketsApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.submarkets(),
    queryFn: () => get<SubmarketsApiResponse>('/market/submarkets'),
    ...options,
  });
}

/**
 * Fetch market trends (API-first)
 */
export function useMarketTrendsApi(
  periodMonths: number = 12,
  options?: Omit<UseQueryOptions<MarketTrendsApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.trends(periodMonths),
    queryFn: () =>
      get<MarketTrendsApiResponse>('/market/trends', { period_months: periodMonths }),
    ...options,
  });
}

/**
 * Fetch comparables (API-first)
 */
export function useComparablesApi(
  filters: ComparableFilters = {},
  options?: Omit<UseQueryOptions<ComparablesApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: marketDataKeys.comparables(filters),
    queryFn: () =>
      get<ComparablesApiResponse>('/market/comparables', filters as Record<string, unknown>),
    ...options,
  });
}

// ============================================================================
// Prefetch Utilities
// ============================================================================

/**
 * Prefetch market overview data
 * Useful for navigation patterns where market data is likely to be needed
 */
export function usePrefetchMarketOverview() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.prefetchQuery({
      queryKey: marketDataKeys.overview(),
      queryFn: async () => {
        if (USE_MOCK_DATA) {
          return {
            msaOverview: phoenixMSAOverview,
            economicIndicators: economicIndicators,
          };
        }
        const response = await get<MarketOverviewApiResponse>('/market/overview');
        return {
          msaOverview: {
            population: response.msa_overview.population,
            employment: response.msa_overview.employment,
            gdp: response.msa_overview.gdp,
            populationGrowth: response.msa_overview.population_growth,
            employmentGrowth: response.msa_overview.employment_growth,
            gdpGrowth: response.msa_overview.gdp_growth,
            lastUpdated: response.msa_overview.last_updated,
          },
          economicIndicators: response.economic_indicators.map((ind) => ({
            indicator: ind.indicator,
            value: ind.value,
            yoyChange: ind.yoy_change,
            unit: ind.unit,
          })),
        };
      },
      staleTime: 15 * 60 * 1000, // 15 minutes
    });
  };
}

/**
 * Prefetch submarkets data
 * Useful when navigating to market analysis sections
 */
export function usePrefetchSubmarkets() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.prefetchQuery({
      queryKey: marketDataKeys.submarkets(),
      queryFn: async () => {
        if (USE_MOCK_DATA) {
          const totalInventory = submarketMetrics.reduce((sum, s) => sum + s.inventory, 0);
          return {
            submarkets: submarketMetrics,
            totalInventory,
            totalAbsorption: submarketMetrics.reduce((sum, s) => sum + s.absorption, 0),
            averageOccupancy:
              submarketMetrics.reduce((sum, s) => sum + s.occupancy * s.inventory, 0) /
              totalInventory,
            averageRentGrowth:
              submarketMetrics.reduce((sum, s) => sum + s.rentGrowth * s.inventory, 0) /
              totalInventory,
          };
        }
        const response = await get<SubmarketsApiResponse>('/market/submarkets');
        return {
          submarkets: response.submarkets.map((s) => ({
            name: s.name,
            avgRent: s.avg_rent,
            rentGrowth: s.rent_growth,
            occupancy: s.occupancy,
            capRate: s.cap_rate,
            inventory: s.inventory,
            absorption: s.absorption,
          })),
          totalInventory: response.total_inventory,
          totalAbsorption: response.total_absorption,
          averageOccupancy: response.average_occupancy,
          averageRentGrowth: response.average_rent_growth,
        };
      },
      staleTime: 15 * 60 * 1000, // 15 minutes
    });
  };
}

// ============================================================================
// Convenience Aliases
// ============================================================================

export const useMarketOverview = useMarketOverviewWithMockFallback;
export const useSubmarkets = useSubmarketsWithMockFallback;
export const useMarketTrends = useMarketTrendsWithMockFallback;
export const useComparables = useComparablesWithMockFallback;
