/**
 * Hook for fetching and managing interest rate data
 * Automatically fetches live data if API is configured, otherwise uses mock data
 */

import { useState, useEffect, useCallback } from 'react';
import type { KeyRate, YieldCurvePoint, HistoricalRate } from '@/data/mockInterestRates';
import {
  mockKeyRates,
  mockYieldCurve,
  mockHistoricalRates,
} from '@/data/mockInterestRates';
import {
  fetchKeyRates,
  fetchYieldCurve,
  fetchHistoricalRates,
  isApiConfigured,
} from '@/services/interestRatesApi';

interface InterestRatesData {
  keyRates: KeyRate[];
  yieldCurve: YieldCurvePoint[];
  historicalRates: HistoricalRate[];
  lastUpdated: Date | null;
  isLiveData: boolean;
  isLoading: boolean;
  error: string | null;
}

interface UseInterestRatesOptions {
  refreshInterval?: number; // in milliseconds, default 5 minutes
  autoRefresh?: boolean;
}

const DEFAULT_REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useInterestRates(options: UseInterestRatesOptions = {}) {
  const {
    refreshInterval = DEFAULT_REFRESH_INTERVAL,
    autoRefresh = true,
  } = options;

  const [data, setData] = useState<InterestRatesData>({
    keyRates: mockKeyRates,
    yieldCurve: mockYieldCurve,
    historicalRates: mockHistoricalRates,
    lastUpdated: new Date(),
    isLiveData: false,
    isLoading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    // Check if API is configured
    if (!isApiConfigured()) {
      setData(prev => ({
        ...prev,
        isLoading: false,
        isLiveData: false,
        lastUpdated: new Date(),
      }));
      return;
    }

    setData(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // Fetch all data in parallel
      const [keyRatesResult, yieldCurveResult, historicalRatesResult] = await Promise.all([
        fetchKeyRates(),
        fetchYieldCurve(),
        fetchHistoricalRates(),
      ]);

      setData(prev => ({
        ...prev,
        keyRates: keyRatesResult || mockKeyRates,
        yieldCurve: yieldCurveResult || mockYieldCurve,
        historicalRates: historicalRatesResult || mockHistoricalRates,
        lastUpdated: new Date(),
        isLiveData: !!(keyRatesResult || yieldCurveResult || historicalRatesResult),
        isLoading: false,
      }));
    } catch (error) {
      console.error('Error fetching interest rates:', error);
      setData(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch data',
        // Keep existing data on error
      }));
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !isApiConfigured()) return;

    const intervalId = setInterval(fetchData, refreshInterval);
    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, fetchData]);

  // Manual refresh function
  const refresh = useCallback(() => {
    return fetchData();
  }, [fetchData]);

  return {
    ...data,
    refresh,
    isApiConfigured: isApiConfigured(),
  };
}

/**
 * Get the as-of date from the key rates data
 */
export function getAsOfDate(keyRates: KeyRate[]): string {
  if (keyRates.length === 0) return new Date().toISOString().split('T')[0];

  // Find the most recent date from the rates
  const dates = keyRates.map(r => r.asOfDate).filter(Boolean);
  if (dates.length === 0) return new Date().toISOString().split('T')[0];

  return dates.sort().reverse()[0];
}
