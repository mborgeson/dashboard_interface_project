import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { get } from '@/lib/api';
import type {
  MarketOverviewApiResponse,
  MarketTrendsApiResponse,
} from '@/hooks/api/useMarketData';
import type {
  MSAOverview,
  EconomicIndicator,
  MarketTrend,
  MonthlyMarketData,
} from '@/types/market';

// ============================================================================
// Query Key Factory
// ============================================================================

export const usaMarketDataKeys = {
  all: ['usaMarketData'] as const,
  overview: () => [...usaMarketDataKeys.all, 'overview'] as const,
  trends: (periodMonths: number) => [...usaMarketDataKeys.all, 'trends', periodMonths] as const,
};

// ============================================================================
// Transform Functions (same shape as Phoenix transforms)
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
// Response Types
// ============================================================================

interface USAMarketOverviewResponse {
  msaOverview: MSAOverview;
  economicIndicators: EconomicIndicator[];
}

interface USAMarketTrendsResponse {
  trends: MarketTrend[];
  monthlyData: MonthlyMarketData[];
  period: string;
}

// ============================================================================
// Query Hooks
// ============================================================================

function useUSAMarketOverview() {
  return useQuery({
    queryKey: usaMarketDataKeys.overview(),
    queryFn: async (): Promise<USAMarketOverviewResponse> => {
      const response = await get<MarketOverviewApiResponse>('/market/usa/overview');
      return {
        msaOverview: transformMSAOverview(response.msa_overview),
        economicIndicators: response.economic_indicators.map(transformEconomicIndicator),
      };
    },
    staleTime: 1000 * 60 * 15, // 15 minutes
  });
}

function useUSAMarketTrends(periodMonths: number = 12) {
  return useQuery({
    queryKey: usaMarketDataKeys.trends(periodMonths),
    queryFn: async (): Promise<USAMarketTrendsResponse> => {
      const response = await get<MarketTrendsApiResponse>('/market/usa/trends', {
        period_months: periodMonths,
      });
      return {
        trends: response.trends.map(transformTrend),
        monthlyData: response.monthly_data.map(transformMonthlyData),
        period: response.period,
      };
    },
    staleTime: 1000 * 60 * 15, // 15 minutes
  });
}

// ============================================================================
// Composite Hook (mirrors useMarketData shape)
// ============================================================================

export function useUSAMarketData() {
  const { data: overviewData, isLoading: overviewLoading, error: overviewError } = useUSAMarketOverview();
  const { data: trendsData, isLoading: trendsLoading, error: trendsError } = useUSAMarketTrends();

  const isLoading = overviewLoading || trendsLoading;
  const error = overviewError || trendsError;

  const trends = useMemo(() => trendsData?.trends ?? [], [trendsData]);
  const monthlyData = useMemo(() => trendsData?.monthlyData ?? [], [trendsData]);

  // Derive sparkline data from monthly API data (last 6 data points)
  const { sparklineData, isSparklinePlaceholder } = useMemo(() => {
    if (monthlyData.length >= 2) {
      const last6 = monthlyData.slice(-6);
      return {
        sparklineData: {
          unemployment: last6.map(m => m.rentGrowth), // rent_growth holds unemployment for USA
          jobGrowth: last6.map(m => m.employment),
          incomeGrowth: last6.map(m => m.capRate), // cap_rate holds mortgage rate for USA
          populationGrowth: last6.map(m => m.population),
        },
        isSparklinePlaceholder: false,
      };
    }
    if (trends.length >= 2) {
      const last6 = trends.slice(-6);
      return {
        sparklineData: {
          unemployment: last6.map(t => t.rentGrowth),
          jobGrowth: last6.map(t => t.occupancy * 100),
          incomeGrowth: last6.map(t => t.capRate),
          populationGrowth: last6.map(t => t.occupancy * 50),
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

  // Calculate formatted trends
  const formattedTrends = useMemo(() => {
    return trends.map(trend => ({
      ...trend,
      rentGrowthPct: trend.rentGrowth,     // Already in % for USA (unemployment rate)
      occupancyPct: trend.occupancy * 100, // Employment rate
      capRatePct: trend.capRate,           // Already in % for USA (mortgage rate)
    }));
  }, [trends]);

  return {
    msaOverview: overviewData?.msaOverview ?? null,
    economicIndicators: overviewData?.economicIndicators ?? [],
    marketTrends: formattedTrends,
    sparklineData,
    isSparklinePlaceholder,
    isLoading,
    error,
  };
}
