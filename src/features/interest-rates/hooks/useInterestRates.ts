/**
 * Hook for fetching and managing interest rate data
 * Fetches live data from the backend API (DB -> FRED fallback)
 * Includes localStorage caching to reduce API calls
 */

import { useState, useEffect, useCallback } from "react";
import type { KeyRate, YieldCurvePoint, HistoricalRate } from "../types";
import {
  fetchKeyRates,
  fetchYieldCurve,
  fetchHistoricalRates,
  isApiConfigured,
} from "@/services/interestRatesApi";

interface InterestRatesData {
  keyRates: KeyRate[];
  yieldCurve: YieldCurvePoint[];
  historicalRates: HistoricalRate[];
  lastUpdated: Date | null;
  isLiveData: boolean;
  isLoading: boolean;
  error: string | null;
}

interface CachedData {
  keyRates: KeyRate[];
  yieldCurve: YieldCurvePoint[];
  historicalRates: HistoricalRate[];
  timestamp: number;
}

interface UseInterestRatesOptions {
  refreshInterval?: number; // in milliseconds, default 5 minutes
  autoRefresh?: boolean;
  cacheTTL?: number; // cache time-to-live in milliseconds, default 5 minutes
}

const DEFAULT_REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes
const DEFAULT_CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const CACHE_KEY = "interestRatesCache";

/**
 * Get cached data from localStorage
 * @returns Cached data if valid and not expired, null otherwise
 */
function getCachedData(ttl: number): CachedData | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;

    const data: CachedData = JSON.parse(cached);
    const now = Date.now();

    // Check if cache is still valid
    if (now - data.timestamp < ttl) {
      return data;
    }

    // Cache expired, remove it
    localStorage.removeItem(CACHE_KEY);
    return null;
  } catch {
    // Invalid cache data
    localStorage.removeItem(CACHE_KEY);
    return null;
  }
}

/**
 * Save data to localStorage cache
 * @param data Rate data to cache
 */
function setCachedData(data: Omit<CachedData, "timestamp">): void {
  try {
    const cacheData: CachedData = {
      ...data,
      timestamp: Date.now(),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
  } catch {
    // Storage full or not available, silently fail
    console.warn("Failed to cache interest rate data to localStorage");
  }
}

/**
 * Hook for fetching and managing interest rate data
 * @param options Configuration options for refresh interval, auto-refresh, and cache TTL
 * @returns Interest rate data and control functions
 */
export function useInterestRates(options: UseInterestRatesOptions = {}) {
  const {
    refreshInterval = DEFAULT_REFRESH_INTERVAL,
    autoRefresh = true,
    cacheTTL = DEFAULT_CACHE_TTL,
  } = options;

  // Try to initialize from cache
  const cachedData = getCachedData(cacheTTL);

  const [data, setData] = useState<InterestRatesData>({
    keyRates: cachedData?.keyRates || [],
    yieldCurve: cachedData?.yieldCurve || [],
    historicalRates: cachedData?.historicalRates || [],
    lastUpdated: cachedData ? new Date(cachedData.timestamp) : null,
    isLiveData: !!cachedData,
    isLoading: !cachedData, // Don't show loading if we have cached data
    error: null,
  });

  const fetchData = useCallback(
    async (forceRefresh = false) => {
      // Check if API is configured
      if (!isApiConfigured()) {
        setData((prev) => ({
          ...prev,
          isLoading: false,
          isLiveData: false,
          lastUpdated: new Date(),
        }));
        return;
      }

      // Check cache first (unless forcing refresh)
      if (!forceRefresh) {
        const cached = getCachedData(cacheTTL);
        if (cached) {
          setData((prev) => ({
            ...prev,
            keyRates: cached.keyRates,
            yieldCurve: cached.yieldCurve,
            historicalRates: cached.historicalRates,
            lastUpdated: new Date(cached.timestamp),
            isLiveData: true,
            isLoading: false,
          }));
          return;
        }
      }

      setData((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        // Fetch all data in parallel
        // When forceRefresh is true, pass it to API calls so backend
        // queries FRED API first instead of returning cached DB data
        const [keyRatesResult, yieldCurveResult, historicalRatesResult] =
          await Promise.all([
            fetchKeyRates(forceRefresh),
            fetchYieldCurve(forceRefresh),
            fetchHistoricalRates(forceRefresh),
          ]);

        const newKeyRates = keyRatesResult || [];
        const newYieldCurve = yieldCurveResult || [];
        const newHistoricalRates = historicalRatesResult || [];
        const isLive = !!(
          keyRatesResult ||
          yieldCurveResult ||
          historicalRatesResult
        );

        // Cache the data if we got live results
        if (isLive) {
          setCachedData({
            keyRates: newKeyRates,
            yieldCurve: newYieldCurve,
            historicalRates: newHistoricalRates,
          });
        }

        setData((prev) => ({
          ...prev,
          keyRates: newKeyRates,
          yieldCurve: newYieldCurve,
          historicalRates: newHistoricalRates,
          lastUpdated: new Date(),
          isLiveData: isLive,
          isLoading: false,
        }));
      } catch (error) {
        console.error("Error fetching interest rates:", error);
        setData((prev) => ({
          ...prev,
          isLoading: false,
          error:
            error instanceof Error ? error.message : "Failed to fetch data",
          // Keep existing data on error
        }));
      }
    },
    [cacheTTL]
  );

  // Initial fetch - only if no valid cache
  useEffect(() => {
    const cached = getCachedData(cacheTTL);
    if (!cached) {
      fetchData();
    }
  }, [fetchData, cacheTTL]);

  // Auto-refresh at interval (always forces fresh fetch)
  useEffect(() => {
    if (!autoRefresh || !isApiConfigured()) return;

    const intervalId = setInterval(() => fetchData(true), refreshInterval);
    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, fetchData]);

  // Manual refresh function (always forces fresh fetch, bypassing cache)
  const refresh = useCallback(() => {
    return fetchData(true);
  }, [fetchData]);

  return {
    ...data,
    refresh,
    isApiConfigured: isApiConfigured(),
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
