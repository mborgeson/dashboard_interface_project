/**
 * Interest Rates API Hooks
 *
 * React Query hooks for fetching interest rate data including:
 * - Key rates (Fed Funds, Treasury yields, SOFR, mortgage rates)
 * - Treasury yield curve
 * - Historical rates
 * - Rate spreads
 * - Data sources
 * - Real estate lending context
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get } from '@/lib/api';
import type {
  KeyRate,
  YieldCurvePoint,
  HistoricalRate,
  RateDataSource,
} from '@/features/interest-rates/types';

// ============================================================================
// Query Key Factory
// ============================================================================

export const interestRateKeys = {
  all: ['interest-rates'] as const,
  current: () => [...interestRateKeys.all, 'current'] as const,
  yieldCurve: () => [...interestRateKeys.all, 'yield-curve'] as const,
  historical: (months: number) => [...interestRateKeys.all, 'historical', months] as const,
  spreads: (months: number) => [...interestRateKeys.all, 'spreads', months] as const,
  dataSources: () => [...interestRateKeys.all, 'data-sources'] as const,
  lendingContext: () => [...interestRateKeys.all, 'lending-context'] as const,
};

// ============================================================================
// API Response Types
// ============================================================================

interface KeyRatesApiResponse {
  key_rates: Array<{
    id: string;
    name: string;
    short_name: string;
    current_value: number;
    previous_value: number;
    change: number;
    change_percent: number;
    as_of_date: string;
    category: 'federal' | 'treasury' | 'sofr' | 'mortgage';
    description: string;
  }>;
  last_updated: string;
  source: string;
}

interface YieldCurveApiResponse {
  yield_curve: Array<{
    maturity: string;
    yield: number;
    previous_yield: number;
    maturity_months: number;
  }>;
  as_of_date: string;
  last_updated: string;
  source: string;
}

interface HistoricalRatesApiResponse {
  rates: Array<{
    date: string;
    federal_funds: number;
    treasury_2y: number;
    treasury_5y: number;
    treasury_10y: number;
    treasury_30y: number;
    sofr: number;
    mortgage_30y: number;
  }>;
  start_date: string;
  end_date: string;
  last_updated: string;
  source: string;
}

interface DataSourcesApiResponse {
  sources: Array<{
    id: string;
    name: string;
    url: string;
    description: string;
    data_types: string[];
    update_frequency: string;
    logo?: string;
  }>;
}

interface RateSpreadsApiResponse {
  spreads: {
    treasury_spread_2s10s: Array<{ date: string; spread: number }>;
    mortgage_spread: Array<{ date: string; spread: number }>;
    fed_funds_vs_treasury: Array<{
      date: string;
      fed_funds: number;
      treasury_10y: number;
      spread: number;
    }>;
  };
  last_updated: string;
  source: string;
}

interface LendingContextApiResponse {
  context: {
    typical_spreads: Record<
      string,
      {
        name: string;
        spread: number;
        benchmark: string;
      }
    >;
    current_indicative_rates: Record<string, number>;
  };
  last_updated: string;
}

// ============================================================================
// Response Types for Hooks
// ============================================================================

export interface KeyRatesWithFallbackResponse {
  keyRates: KeyRate[];
  lastUpdated: Date;
  source: string;
}

export interface YieldCurveWithFallbackResponse {
  yieldCurve: YieldCurvePoint[];
  asOfDate: string;
  lastUpdated: Date;
  source: string;
}

export interface HistoricalRatesWithFallbackResponse {
  rates: HistoricalRate[];
  startDate: string;
  endDate: string;
  lastUpdated: Date;
  source: string;
}

export interface DataSourcesWithFallbackResponse {
  sources: RateDataSource[];
}

export interface RateSpreadsWithFallbackResponse {
  spreads: {
    treasurySpread2s10s: Array<{ date: string; spread: number }>;
    mortgageSpread: Array<{ date: string; spread: number }>;
    fedFundsVsTreasury: Array<{
      date: string;
      fedFunds: number;
      treasury10Y: number;
      spread: number;
    }>;
  };
  lastUpdated: Date;
  source: string;
}

export interface LendingContextWithFallbackResponse {
  typicalSpreads: Record<
    string,
    {
      name: string;
      spreadOverTreasury?: number;
      spreadOverSOFR?: number;
      spreadOverPrime?: number;
      benchmark: string;
    }
  >;
  currentIndicativeRates: Record<string, number>;
  lastUpdated: Date;
}

// ============================================================================
// Transform Functions
// ============================================================================

function transformKeyRatesFromApi(apiResponse: KeyRatesApiResponse): KeyRatesWithFallbackResponse {
  return {
    keyRates: apiResponse.key_rates.map((rate) => ({
      id: rate.id,
      name: rate.name,
      shortName: rate.short_name,
      currentValue: rate.current_value,
      previousValue: rate.previous_value,
      change: rate.change,
      changePercent: rate.change_percent,
      asOfDate: rate.as_of_date,
      category: rate.category,
      description: rate.description,
    })),
    lastUpdated: new Date(apiResponse.last_updated),
    source: apiResponse.source,
  };
}

function transformYieldCurveFromApi(
  apiResponse: YieldCurveApiResponse
): YieldCurveWithFallbackResponse {
  return {
    yieldCurve: apiResponse.yield_curve.map((point) => ({
      maturity: point.maturity,
      yield: point.yield,
      previousYield: point.previous_yield,
      maturityMonths: point.maturity_months,
    })),
    asOfDate: apiResponse.as_of_date,
    lastUpdated: new Date(apiResponse.last_updated),
    source: apiResponse.source,
  };
}

function transformHistoricalRatesFromApi(
  apiResponse: HistoricalRatesApiResponse
): HistoricalRatesWithFallbackResponse {
  return {
    rates: apiResponse.rates.map((rate) => ({
      date: rate.date,
      federalFunds: rate.federal_funds,
      treasury2Y: rate.treasury_2y,
      treasury5Y: rate.treasury_5y,
      treasury10Y: rate.treasury_10y,
      treasury30Y: rate.treasury_30y,
      sofr: rate.sofr,
      mortgage30Y: rate.mortgage_30y,
    })),
    startDate: apiResponse.start_date,
    endDate: apiResponse.end_date,
    lastUpdated: new Date(apiResponse.last_updated),
    source: apiResponse.source,
  };
}

function transformDataSourcesFromApi(
  apiResponse: DataSourcesApiResponse
): DataSourcesWithFallbackResponse {
  return {
    sources: apiResponse.sources.map((source) => ({
      id: source.id,
      name: source.name,
      url: source.url,
      description: source.description,
      dataTypes: source.data_types,
      updateFrequency: source.update_frequency,
      logo: source.logo,
    })),
  };
}

function transformRateSpreadsFromApi(
  apiResponse: RateSpreadsApiResponse
): RateSpreadsWithFallbackResponse {
  return {
    spreads: {
      treasurySpread2s10s: apiResponse.spreads.treasury_spread_2s10s,
      mortgageSpread: apiResponse.spreads.mortgage_spread,
      fedFundsVsTreasury: apiResponse.spreads.fed_funds_vs_treasury.map((item) => ({
        date: item.date,
        fedFunds: item.fed_funds,
        treasury10Y: item.treasury_10y,
        spread: item.spread,
      })),
    },
    lastUpdated: new Date(apiResponse.last_updated),
    source: apiResponse.source,
  };
}

function transformLendingContextFromApi(
  apiResponse: LendingContextApiResponse
): LendingContextWithFallbackResponse {
  // Transform snake_case keys to camelCase
  const typicalSpreads: Record<
    string,
    { name: string; spreadOverTreasury?: number; spreadOverSOFR?: number; spreadOverPrime?: number; benchmark: string }
  > = {};

  for (const [key, value] of Object.entries(apiResponse.context.typical_spreads)) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
    typicalSpreads[camelKey] = {
      name: value.name,
      benchmark: value.benchmark,
      ...(value.benchmark.includes('Treasury') ? { spreadOverTreasury: value.spread } : {}),
      ...(value.benchmark.includes('SOFR') ? { spreadOverSOFR: value.spread } : {}),
      ...(value.benchmark.includes('Prime') ? { spreadOverPrime: value.spread } : {}),
    };
  }

  const currentIndicativeRates: Record<string, number> = {};
  for (const [key, value] of Object.entries(apiResponse.context.current_indicative_rates)) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
    currentIndicativeRates[camelKey] = value;
  }

  return {
    typicalSpreads: typicalSpreads as LendingContextWithFallbackResponse['typicalSpreads'],
    currentIndicativeRates: currentIndicativeRates as LendingContextWithFallbackResponse['currentIndicativeRates'],
    lastUpdated: new Date(apiResponse.last_updated),
  };
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to fetch current key interest rates
 * Errors propagate to React Query error state
 */
export function useKeyRatesWithMockFallback(
  options?: Omit<UseQueryOptions<KeyRatesWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.current(),
    queryFn: async (): Promise<KeyRatesWithFallbackResponse> => {
      const response = await get<KeyRatesApiResponse>('/interest-rates/current');
      return transformKeyRatesFromApi(response);
    },
    staleTime: 1000 * 60 * 5, // 5 minutes - rates don't change frequently
    ...options,
  });
}

/**
 * Hook to fetch Treasury yield curve
 */
export function useYieldCurveWithMockFallback(
  options?: Omit<UseQueryOptions<YieldCurveWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.yieldCurve(),
    queryFn: async (): Promise<YieldCurveWithFallbackResponse> => {
      const response = await get<YieldCurveApiResponse>('/interest-rates/yield-curve');
      return transformYieldCurveFromApi(response);
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch historical interest rates
 */
export function useHistoricalRatesWithMockFallback(
  months: number = 12,
  options?: Omit<UseQueryOptions<HistoricalRatesWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.historical(months),
    queryFn: async (): Promise<HistoricalRatesWithFallbackResponse> => {
      const response = await get<HistoricalRatesApiResponse>('/interest-rates/historical', {
        months,
      });
      return transformHistoricalRatesFromApi(response);
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch rate data sources
 */
export function useDataSourcesWithMockFallback(
  options?: Omit<UseQueryOptions<DataSourcesWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.dataSources(),
    queryFn: async (): Promise<DataSourcesWithFallbackResponse> => {
      const response = await get<DataSourcesApiResponse>('/interest-rates/data-sources');
      return transformDataSourcesFromApi(response);
    },
    staleTime: 1000 * 60 * 60, // 1 hour - data sources rarely change
    ...options,
  });
}

/**
 * Hook to fetch rate spreads
 */
export function useRateSpreadsWithMockFallback(
  months: number = 12,
  options?: Omit<UseQueryOptions<RateSpreadsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.spreads(months),
    queryFn: async (): Promise<RateSpreadsWithFallbackResponse> => {
      const response = await get<RateSpreadsApiResponse>('/interest-rates/spreads', { months });
      return transformRateSpreadsFromApi(response);
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch real estate lending context
 */
export function useLendingContextWithMockFallback(
  options?: Omit<UseQueryOptions<LendingContextWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.lendingContext(),
    queryFn: async (): Promise<LendingContextWithFallbackResponse> => {
      const response = await get<LendingContextApiResponse>('/interest-rates/lending-context');
      return transformLendingContextFromApi(response);
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

// ============================================================================
// API-first Hooks (no mock fallback)
// ============================================================================

/**
 * Fetch current key rates from API (no mock fallback)
 */
export function useKeyRatesApi(
  options?: Omit<UseQueryOptions<KeyRatesApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.current(),
    queryFn: () => get<KeyRatesApiResponse>('/interest-rates/current'),
    staleTime: 1000 * 60 * 5,
    ...options,
  });
}

/**
 * Fetch yield curve from API (no mock fallback)
 */
export function useYieldCurveApi(
  options?: Omit<UseQueryOptions<YieldCurveApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.yieldCurve(),
    queryFn: () => get<YieldCurveApiResponse>('/interest-rates/yield-curve'),
    staleTime: 1000 * 60 * 5,
    ...options,
  });
}

/**
 * Fetch historical rates from API (no mock fallback)
 */
export function useHistoricalRatesApi(
  months: number = 12,
  options?: Omit<UseQueryOptions<HistoricalRatesApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.historical(months),
    queryFn: () => get<HistoricalRatesApiResponse>('/interest-rates/historical', { months }),
    staleTime: 1000 * 60 * 5,
    ...options,
  });
}

/**
 * Fetch data sources from API (no mock fallback)
 */
export function useDataSourcesApi(
  options?: Omit<UseQueryOptions<DataSourcesApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.dataSources(),
    queryFn: () => get<DataSourcesApiResponse>('/interest-rates/data-sources'),
    staleTime: 1000 * 60 * 60,
    ...options,
  });
}

/**
 * Fetch rate spreads from API (no mock fallback)
 */
export function useRateSpreadsApi(
  months: number = 12,
  options?: Omit<UseQueryOptions<RateSpreadsApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.spreads(months),
    queryFn: () => get<RateSpreadsApiResponse>('/interest-rates/spreads', { months }),
    staleTime: 1000 * 60 * 5,
    ...options,
  });
}

/**
 * Fetch lending context from API (no mock fallback)
 */
export function useLendingContextApi(
  options?: Omit<UseQueryOptions<LendingContextApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: interestRateKeys.lendingContext(),
    queryFn: () => get<LendingContextApiResponse>('/interest-rates/lending-context'),
    staleTime: 1000 * 60 * 5,
    ...options,
  });
}

// ============================================================================
// Prefetch Utilities
// ============================================================================

/**
 * Prefetch current key interest rates
 * Useful for navigation patterns where rate data is likely to be needed
 */
export function usePrefetchKeyRates() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.prefetchQuery({
      queryKey: interestRateKeys.current(),
      queryFn: async () => {
        const response = await get<KeyRatesApiResponse>('/interest-rates/current');
        return transformKeyRatesFromApi(response);
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
    });
  };
}

/**
 * Prefetch Treasury yield curve
 * Useful for financing and deal analysis screens
 */
export function usePrefetchYieldCurve() {
  const queryClient = useQueryClient();

  return () => {
    queryClient.prefetchQuery({
      queryKey: interestRateKeys.yieldCurve(),
      queryFn: async () => {
        const response = await get<YieldCurveApiResponse>('/interest-rates/yield-curve');
        return transformYieldCurveFromApi(response);
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
    });
  };
}

// ============================================================================
// Convenience Aliases
// ============================================================================

/**
 * Primary hook for key rates
 */
export const useInterestRates = useKeyRatesWithMockFallback;

/**
 * Primary hook for yield curve
 */
export const useYieldCurve = useYieldCurveWithMockFallback;

/**
 * Primary hook for historical rates
 */
export const useHistoricalRates = useHistoricalRatesWithMockFallback;

/**
 * Primary hook for data sources
 */
export const useDataSources = useDataSourcesWithMockFallback;

/**
 * Primary hook for rate spreads
 */
export const useRateSpreads = useRateSpreadsWithMockFallback;

/**
 * Primary hook for lending context
 */
export const useLendingContext = useLendingContextWithMockFallback;
