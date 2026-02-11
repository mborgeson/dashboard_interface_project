import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchProjects,
  fetchConstructionFilterOptions,
  fetchPipelineSummary,
  fetchPipelineFunnel,
  fetchPermitTrends,
  fetchEmploymentOverlay,
  fetchSubmarketPipeline,
  fetchClassificationBreakdown,
  fetchConstructionDataQuality,
  fetchConstructionImportStatus,
  triggerConstructionImport,
} from '@/lib/api/construction';
import type { ConstructionFilters } from '../types';

// ============================================================================
// Query Key Factory
// ============================================================================

export const constructionKeys = {
  all: ['construction'] as const,
  lists: () => [...constructionKeys.all, 'list'] as const,
  list: (filters: ConstructionFilters, page: number, pageSize: number) =>
    [...constructionKeys.lists(), filters, page, pageSize] as const,
  analytics: () => [...constructionKeys.all, 'analytics'] as const,
  pipelineSummary: (filters: ConstructionFilters) =>
    [...constructionKeys.analytics(), 'pipeline-summary', filters] as const,
  pipelineFunnel: (filters: ConstructionFilters) =>
    [...constructionKeys.analytics(), 'pipeline-funnel', filters] as const,
  permitTrends: (source?: string) =>
    [...constructionKeys.analytics(), 'permit-trends', source] as const,
  employmentOverlay: () =>
    [...constructionKeys.analytics(), 'employment-overlay'] as const,
  submarketPipeline: (filters: ConstructionFilters) =>
    [...constructionKeys.analytics(), 'submarket-pipeline', filters] as const,
  classificationBreakdown: (filters: ConstructionFilters) =>
    [...constructionKeys.analytics(), 'classification-breakdown', filters] as const,
  dataQuality: () => [...constructionKeys.all, 'data-quality'] as const,
  importStatus: () => [...constructionKeys.all, 'import-status'] as const,
  filterOptions: () => [...constructionKeys.all, 'filter-options'] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/** Paginated project list */
export function useProjects(
  filters: ConstructionFilters,
  page: number,
  pageSize: number
) {
  return useQuery({
    queryKey: constructionKeys.list(filters, page, pageSize),
    queryFn: () => fetchProjects(filters, page, pageSize),
    staleTime: 1000 * 60 * 5,
  });
}

/** Filter options */
export function useConstructionFilterOptions() {
  return useQuery({
    queryKey: constructionKeys.filterOptions(),
    queryFn: fetchConstructionFilterOptions,
    staleTime: 1000 * 60 * 30,
  });
}

/** Pipeline summary (counts by status) */
export function usePipelineSummary(filters: ConstructionFilters) {
  return useQuery({
    queryKey: constructionKeys.pipelineSummary(filters),
    queryFn: () => fetchPipelineSummary(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Pipeline funnel */
export function usePipelineFunnel(filters: ConstructionFilters) {
  return useQuery({
    queryKey: constructionKeys.pipelineFunnel(filters),
    queryFn: () => fetchPipelineFunnel(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Permit trends time-series */
export function usePermitTrends(source?: string) {
  return useQuery({
    queryKey: constructionKeys.permitTrends(source),
    queryFn: () => fetchPermitTrends(source),
    staleTime: 1000 * 60 * 10,
  });
}

/** Employment overlay */
export function useEmploymentOverlay() {
  return useQuery({
    queryKey: constructionKeys.employmentOverlay(),
    queryFn: () => fetchEmploymentOverlay(),
    staleTime: 1000 * 60 * 10,
  });
}

/** Submarket pipeline breakdown */
export function useSubmarketPipeline(filters: ConstructionFilters) {
  return useQuery({
    queryKey: constructionKeys.submarketPipeline(filters),
    queryFn: () => fetchSubmarketPipeline(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Classification breakdown */
export function useClassificationBreakdown(filters: ConstructionFilters) {
  return useQuery({
    queryKey: constructionKeys.classificationBreakdown(filters),
    queryFn: () => fetchClassificationBreakdown(filters),
    staleTime: 1000 * 60 * 5,
  });
}

/** Data quality report */
export function useConstructionDataQuality() {
  return useQuery({
    queryKey: constructionKeys.dataQuality(),
    queryFn: fetchConstructionDataQuality,
    staleTime: 1000 * 60 * 10,
  });
}

/** Import status */
export function useConstructionImportStatus() {
  return useQuery({
    queryKey: constructionKeys.importStatus(),
    queryFn: fetchConstructionImportStatus,
    refetchInterval: 1000 * 60,
  });
}

/** Trigger import mutation */
export function useTriggerConstructionImport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: triggerConstructionImport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: constructionKeys.importStatus() });
      queryClient.invalidateQueries({ queryKey: constructionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: constructionKeys.analytics() });
      queryClient.invalidateQueries({ queryKey: constructionKeys.dataQuality() });
      queryClient.invalidateQueries({ queryKey: constructionKeys.filterOptions() });
    },
  });
}
