/**
 * Hook for fetching and managing interest rate data
 *
 * Wraps the React Query hooks from src/hooks/api/useInterestRates.ts
 * to provide the same combined interface that InterestRatesPage expects.
 * React Query manages caching, so the legacy localStorage caching is removed.
 */

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { KeyRate, YieldCurvePoint, HistoricalRate } from "../types";
import {
  useKeyRatesWithMockFallback,
  useYieldCurveWithMockFallback,
  useHistoricalRatesWithMockFallback,
  interestRateKeys,
} from "@/hooks/api/useInterestRates";
import { get } from "@/lib/api/client";
import { STALE_TIMES } from "@/lib/constants/query";

interface UseInterestRatesOptions {
  refreshInterval?: number; // in milliseconds, default 5 minutes
  autoRefresh?: boolean;
  cacheTTL?: number; // kept for API compat, no longer used (React Query manages caching)
}

const DEFAULT_REFRESH_INTERVAL = STALE_TIMES.MEDIUM; // 5 minutes

/**
 * Hook for fetching and managing interest rate data
 * @param options Configuration options for refresh interval, auto-refresh, and cache TTL
 * @returns Interest rate data and control functions
 */
export function useInterestRates(options: UseInterestRatesOptions = {}) {
  const {
    refreshInterval = DEFAULT_REFRESH_INTERVAL,
    autoRefresh = true,
  } = options;

  const queryClient = useQueryClient();

  const keyRatesQuery = useKeyRatesWithMockFallback({
    refetchInterval: autoRefresh ? refreshInterval : false,
  });

  const yieldCurveQuery = useYieldCurveWithMockFallback({
    refetchInterval: autoRefresh ? refreshInterval : false,
  });

  const historicalRatesQuery = useHistoricalRatesWithMockFallback(12, {
    refetchInterval: autoRefresh ? refreshInterval : false,
  });

  const keyRates: KeyRate[] = keyRatesQuery.data?.keyRates ?? [];
  const yieldCurve: YieldCurvePoint[] = yieldCurveQuery.data?.yieldCurve ?? [];
  const historicalRates: HistoricalRate[] = historicalRatesQuery.data?.rates ?? [];

  const isLoading =
    keyRatesQuery.isLoading || yieldCurveQuery.isLoading || historicalRatesQuery.isLoading;

  const isLiveData = !!(keyRatesQuery.data || yieldCurveQuery.data || historicalRatesQuery.data);

  const lastUpdated =
    keyRatesQuery.data?.lastUpdated ??
    yieldCurveQuery.data?.lastUpdated ??
    historicalRatesQuery.data?.lastUpdated ??
    null;

  const error =
    keyRatesQuery.error?.message ??
    yieldCurveQuery.error?.message ??
    historicalRatesQuery.error?.message ??
    null;

  // Manual refresh — hit FRED API directly via force_refresh, then invalidate cache
  const refresh = useCallback(async () => {
    // Fire force_refresh requests to pull fresh data from FRED into the DB
    await Promise.allSettled([
      get('/interest-rates/current', { force_refresh: true }),
      get('/interest-rates/yield-curve', { force_refresh: true }),
      get('/interest-rates/historical', { months: 12, force_refresh: true }),
    ]);
    // Invalidate React Query cache so hooks re-fetch with the fresh DB data
    queryClient.invalidateQueries({ queryKey: interestRateKeys.all });
  }, [queryClient]);

  return {
    keyRates,
    yieldCurve,
    historicalRates,
    lastUpdated,
    isLiveData,
    isLoading,
    error,
    refresh,
    isApiConfigured: true, // Backend always handles fallback
  };
}

/**
 * Get the as-of date from the key rates data
 * @param keyRates Array of key rates
 * @returns The most recent as-of date in ISO format
 */
export function getAsOfDate(keyRates: KeyRate[]): string {
  if (keyRates.length === 0) return new Date().toISOString().split("T")[0];

  // Find the most recent date from the rates
  const dates = keyRates.map((r) => r.asOfDate).filter(Boolean);
  if (dates.length === 0) return new Date().toISOString().split("T")[0];

  return dates.sort().reverse()[0];
}
