import { useMemo } from 'react';
import {
  phoenixMSAOverview,
  economicIndicators,
  marketTrends,
  submarketMetrics,
  monthlyMarketData,
  unemploymentSparkline,
  jobGrowthSparkline,
  incomeGrowthSparkline,
  populationGrowthSparkline,
} from '@/data/mockMarketData';

export function useMarketData() {
  // Calculate aggregate metrics
  const aggregateMetrics = useMemo(() => {
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
  }, []);

  // Calculate trends with proper formatting
  const formattedTrends = useMemo(() => {
    return marketTrends.map(trend => ({
      ...trend,
      rentGrowthPct: trend.rentGrowth * 100,
      occupancyPct: trend.occupancy * 100,
      capRatePct: trend.capRate * 100,
    }));
  }, []);

  // Format submarket data for comparison
  const formattedSubmarkets = useMemo(() => {
    return submarketMetrics.map(submarket => ({
      ...submarket,
      rentGrowthPct: submarket.rentGrowth * 100,
      occupancyPct: submarket.occupancy * 100,
      capRatePct: submarket.capRate * 100,
    }));
  }, []);

  // Get sparkline data for indicators
  const sparklineData = useMemo(() => ({
    unemployment: unemploymentSparkline,
    jobGrowth: jobGrowthSparkline,
    incomeGrowth: incomeGrowthSparkline,
    populationGrowth: populationGrowthSparkline,
  }), []);

  return {
    msaOverview: phoenixMSAOverview,
    economicIndicators,
    marketTrends: formattedTrends,
    submarketMetrics: formattedSubmarkets,
    monthlyMarketData,
    aggregateMetrics,
    sparklineData,
  };
}
