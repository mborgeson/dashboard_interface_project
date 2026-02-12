import { useMemo, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  useMarketOverview,
  useSubmarkets,
  useMarketTrends,
  marketDataKeys,
} from '@/hooks/api/useMarketData';
import { apiClient } from '@/lib/api/client';

export function useMarketData() {
  const queryClient = useQueryClient();

  // Fetch from API (with DB fallback on the backend)
  const { data: overviewData, isLoading: overviewLoading, error: overviewError } = useMarketOverview();
  const { data: submarketsData, isLoading: submarketsLoading, error: submarketsError } = useSubmarkets();
  const { data: trendsData, isLoading: trendsLoading, error: trendsError } = useMarketTrends();
  const isLoading = overviewLoading || submarketsLoading || trendsLoading;
  const error = overviewError || submarketsError || trendsError;

  const submarketMetrics = useMemo(() => submarketsData?.submarkets ?? [], [submarketsData]);
  const trends = useMemo(() => trendsData?.trends ?? [], [trendsData]);
  const monthlyData = useMemo(() => trendsData?.monthlyData ?? [], [trendsData]);

  // Derive sparkline data from monthly API data (last 6 data points).
  // monthlyData includes employment/population fields from /api/v1/market/trends.
  // Falls back to trends-based approximation, then to static placeholder values.
  const { sparklineData, isSparklinePlaceholder } = useMemo(() => {
    // Prefer monthlyData which has employment & population fields
    if (monthlyData.length >= 2) {
      const last6 = monthlyData.slice(-6);
      return {
        sparklineData: {
          unemployment: last6.map(m => (1 - m.occupancy) * 100),
          jobGrowth: last6.map(m => m.employment),
          incomeGrowth: last6.map(m => m.rentGrowth * 100),
          populationGrowth: last6.map(m => m.population),
        },
        isSparklinePlaceholder: false,
      };
    }
    // Fall back to basic trends if monthlyData is unavailable
    if (trends.length >= 2) {
      const last6 = trends.slice(-6);
      return {
        sparklineData: {
          unemployment: last6.map(t => (1 - t.occupancy) * 100),
          jobGrowth: last6.map(t => t.rentGrowth * 100),
          incomeGrowth: last6.map(t => t.rentGrowth * 100),
          populationGrowth: last6.map(t => t.rentGrowth * 50),
        },
        isSparklinePlaceholder: false,
      };
    }
    // No data available - return empty arrays (no fake/placeholder data)
    return {
      sparklineData: {
        unemployment: [],
        jobGrowth: [],
        incomeGrowth: [],
        populationGrowth: [],
      },
      isSparklinePlaceholder: true,
    };
  }, [monthlyData, trends]);

  // Calculate aggregate metrics
  const aggregateMetrics = useMemo(() => {
    if (submarketMetrics.length === 0) {
      return { totalInventory: 0, avgOccupancy: 0, avgRentGrowth: 0, avgCapRate: 0 };
    }
    const totalInventory = submarketMetrics.reduce((sum, s) => sum + s.inventory, 0);
    const avgOccupancy = submarketMetrics.reduce((sum, s) => sum + s.occupancy, 0) / submarketMetrics.length;
    const avgRentGrowth = submarketMetrics.reduce((sum, s) => sum + s.rentGrowth, 0) / submarketMetrics.length;
    const avgCapRate = submarketMetrics.reduce((sum, s) => sum + s.capRate, 0) / submarketMetrics.length;

    return {
      totalInventory,
      avgOccupancy,
      avgRentGrowth,
      avgCapRate,
    };
  }, [submarketMetrics]);

  // Calculate trends with proper formatting
  const formattedTrends = useMemo(() => {
    return trends.map(trend => ({
      ...trend,
      rentGrowthPct: trend.rentGrowth * 100,
      occupancyPct: trend.occupancy * 100,
      capRatePct: trend.capRate * 100,
    }));
  }, [trends]);

  // Format submarket data for comparison
  const formattedSubmarkets = useMemo(() => {
    return submarketMetrics.map(submarket => ({
      ...submarket,
      rentGrowthPct: submarket.rentGrowth * 100,
      occupancyPct: submarket.occupancy * 100,
      capRatePct: submarket.capRate * 100,
    }));
  }, [submarketMetrics]);

  /**
   * Trigger a server-side FRED extraction refresh, then invalidate
   * all market data queries so React Query re-fetches fresh data.
   */
  const refreshAll = useCallback(async () => {
    await apiClient.post<{ status: string; records_upserted: number }>(
      '/market/refresh'
    );
    await queryClient.invalidateQueries({ queryKey: marketDataKeys.all });
  }, [queryClient]);

  return {
    msaOverview: overviewData?.msaOverview ?? null,
    economicIndicators: overviewData?.economicIndicators ?? [],
    marketTrends: formattedTrends,
    submarketMetrics: formattedSubmarkets,
    monthlyMarketData: monthlyData,
    aggregateMetrics,
    sparklineData,
    isSparklinePlaceholder,
    isLoading,
    error,
    refreshAll,
  };
}
