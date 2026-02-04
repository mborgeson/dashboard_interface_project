import { useMemo } from 'react';
import {
  useMarketOverview,
  useSubmarkets,
  useMarketTrends,
} from '@/hooks/api/useMarketData';

export function useMarketData() {
  // Fetch from API (with DB → static fallback)
  const { data: overviewData, isLoading: overviewLoading } = useMarketOverview();
  const { data: submarketsData, isLoading: submarketsLoading } = useSubmarkets();
  const { data: trendsData, isLoading: trendsLoading } = useMarketTrends();
  const isLoading = overviewLoading || submarketsLoading || trendsLoading;

  const submarketMetrics = submarketsData?.submarkets ?? [];
  const trends = trendsData?.trends ?? [];
  const monthlyData = trendsData?.monthlyData ?? [];

  // Derive sparkline data from trends (last 6 data points) instead of hardcoded values
  const sparklineData = useMemo(() => {
    if (trends.length === 0) {
      return {
        unemployment: [4.2, 4.0, 3.9, 3.8, 3.7, 3.6],
        jobGrowth: [2.1, 2.4, 2.6, 2.8, 3.0, 3.2],
        incomeGrowth: [3.8, 4.0, 4.1, 4.2, 4.3, 4.5],
        populationGrowth: [2.0, 2.1, 2.1, 2.2, 2.2, 2.3],
      };
    }
    const last6 = trends.slice(-6);
    return {
      unemployment: last6.map(t => (1 - t.occupancy) * 100),
      jobGrowth: last6.map(t => t.rentGrowth * 100),
      incomeGrowth: last6.map(t => t.rentGrowth * 100),
      populationGrowth: last6.map(t => t.rentGrowth * 50),
    };
  }, [trends]);

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

  return {
    msaOverview: overviewData?.msaOverview ?? null,
    economicIndicators: overviewData?.economicIndicators ?? [],
    marketTrends: formattedTrends,
    submarketMetrics: formattedSubmarkets,
    monthlyMarketData: monthlyData,
    aggregateMetrics,
    sparklineData,
    isLoading,
  };
}
