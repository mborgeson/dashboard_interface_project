/**
 * Dashboard Prefetch Hook
 *
 * Prefetches common dashboard data on app initialization for improved
 * perceived performance. This hook should be called in the App component
 * to warm the cache with data that users are likely to need.
 */

import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { get } from '@/lib/api';
import { USE_MOCK_DATA } from '@/lib/config';
import { marketDataKeys, type MarketOverviewApiResponse } from './api/useMarketData';
import { interestRateKeys } from './api/useInterestRates';
import { reportingKeys, type ReportTemplateListApiResponse } from './api/useReporting';
import { propertyKeys } from './api/useProperties';
import {
  phoenixMSAOverview,
  economicIndicators,
} from '@/data/mockMarketData';
import { mockKeyRates } from '@/data/mockInterestRates';
import { mockReportTemplates } from '@/data/mockReportingData';
import { mockProperties } from '@/data/mockProperties';

/**
 * Prefetch common dashboard data on app initialization
 * Warms the cache with market overview, interest rates, and report templates
 */
export function usePrefetchDashboard() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Prefetch market overview - commonly accessed from dashboard
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

    // Prefetch current interest rates - important for deal analysis
    queryClient.prefetchQuery({
      queryKey: interestRateKeys.current(),
      queryFn: async () => {
        if (USE_MOCK_DATA) {
          return {
            keyRates: mockKeyRates,
            lastUpdated: new Date(),
            source: 'mock',
          };
        }
        const response = await get<{
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
        }>('/interest-rates/current');
        return {
          keyRates: response.key_rates.map((rate) => ({
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
          lastUpdated: new Date(response.last_updated),
          source: response.source,
        };
      },
      staleTime: 10 * 60 * 1000, // 10 minutes
    });

    // Prefetch report templates - needed for reporting suite
    queryClient.prefetchQuery({
      queryKey: reportingKeys.templateList({}),
      queryFn: async () => {
        if (USE_MOCK_DATA) {
          return {
            templates: mockReportTemplates,
            total: mockReportTemplates.length,
          };
        }
        const response = await get<ReportTemplateListApiResponse>('/reporting/templates');
        return {
          templates: response.items.map((t) => ({
            id: String(t.id),
            name: t.name,
            description: t.description || '',
            category: t.category,
            sections: t.sections,
            lastModified: t.updated_at.split('T')[0],
            createdBy: t.created_by,
            isDefault: t.is_default,
            supportedFormats: t.export_formats,
            parameters: [],
          })),
          total: response.total,
        };
      },
      staleTime: 10 * 60 * 1000, // 10 minutes
    });

    // Prefetch properties list - core dashboard data
    queryClient.prefetchQuery({
      queryKey: propertyKeys.lists(),
      queryFn: async () => {
        if (USE_MOCK_DATA) {
          return {
            properties: mockProperties,
            total: mockProperties.length,
          };
        }
        return await get('/properties');
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
    });
  }, [queryClient]);
}

export default usePrefetchDashboard;
