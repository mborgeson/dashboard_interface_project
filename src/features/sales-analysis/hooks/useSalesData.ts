import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchSalesData,
  fetchTimeSeriesAnalytics,
  fetchSubmarketComparison,
  fetchBuyerActivity,
  fetchDistributions,
  fetchDataQuality,
  fetchImportStatus,
  triggerImport,
  fetchReminderStatus,
  dismissReminder,
  fetchFilterOptions,
} from '@/lib/api/sales';
import type { SalesFilters } from '../types';

// ============================================================================
// Query Key Factory
// ============================================================================

export const salesKeys = {
  all: ['sales'] as const,
  lists: () => [...salesKeys.all, 'list'] as const,
  list: (filters: SalesFilters, page: number, pageSize: number) =>
    [...salesKeys.lists(), filters, page, pageSize] as const,
  analytics: () => [...salesKeys.all, 'analytics'] as const,
  timeSeries: (filters: SalesFilters) =>
    [...salesKeys.analytics(), 'time-series', filters] as const,
  submarketComparison: (filters: SalesFilters) =>
    [...salesKeys.analytics(), 'submarket-comparison', filters] as const,
  buyerActivity: (filters: SalesFilters) =>
    [...salesKeys.analytics(), 'buyer-activity', filters] as const,
  distributions: (filters: SalesFilters) =>
    [...salesKeys.analytics(), 'distributions', filters] as const,
  dataQuality: () => [...salesKeys.all, 'data-quality'] as const,
  importStatus: () => [...salesKeys.all, 'import-status'] as const,
  reminderStatus: () => [...salesKeys.all, 'reminder-status'] as const,
  filterOptions: () => [...salesKeys.all, 'filter-options'] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/** Paginated sales table data */
export function useSalesData(
  filters: SalesFilters,
  page: number,
  pageSize: number
) {
  return useQuery({
    queryKey: salesKeys.list(filters, page, pageSize),
    queryFn: () => fetchSalesData(filters, page, pageSize),
    staleTime: 1000 * 60 * 5,
  });
}

/** Time-series trend analytics */
export function useTimeSeriesAnalytics(filters: SalesFilters) {
  return useQuery({
    queryKey: salesKeys.timeSeries(filters),
    queryFn: () => fetchTimeSeriesAnalytics(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Submarket comparison analytics */
export function useSubmarketComparison(filters: SalesFilters) {
  return useQuery({
    queryKey: salesKeys.submarketComparison(filters),
    queryFn: () => fetchSubmarketComparison(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Buyer activity analytics */
export function useBuyerActivity(filters: SalesFilters) {
  return useQuery({
    queryKey: salesKeys.buyerActivity(filters),
    queryFn: () => fetchBuyerActivity(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Distribution analysis */
export function useDistributions(filters: SalesFilters) {
  return useQuery({
    queryKey: salesKeys.distributions(filters),
    queryFn: () => fetchDistributions(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Data quality report */
export function useDataQuality() {
  return useQuery({
    queryKey: salesKeys.dataQuality(),
    queryFn: fetchDataQuality,
    staleTime: 1000 * 60 * 10,
  });
}

/** Import status — polls every 60s to detect new files */
export function useImportStatus() {
  return useQuery({
    queryKey: salesKeys.importStatus(),
    queryFn: fetchImportStatus,
    refetchInterval: 1000 * 60,
  });
}

/** Trigger import mutation */
export function useTriggerImport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: triggerImport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: salesKeys.importStatus() });
      queryClient.invalidateQueries({ queryKey: salesKeys.lists() });
      queryClient.invalidateQueries({ queryKey: salesKeys.analytics() });
      queryClient.invalidateQueries({ queryKey: salesKeys.dataQuality() });
    },
  });
}

/** Filter options (distinct submarkets, etc.) */
export function useFilterOptions() {
  return useQuery({
    queryKey: salesKeys.filterOptions(),
    queryFn: fetchFilterOptions,
    staleTime: 1000 * 60 * 30,
  });
}

/** Monthly reminder status */
export function useReminderStatus() {
  return useQuery({
    queryKey: salesKeys.reminderStatus(),
    queryFn: fetchReminderStatus,
    staleTime: 1000 * 60 * 60,
  });
}

/** Dismiss reminder mutation */
export function useDismissReminder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dismissReminder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: salesKeys.reminderStatus() });
    },
  });
}
