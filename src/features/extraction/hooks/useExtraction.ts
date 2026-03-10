import { useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type {
  ExtractionRun,
  ExtractionStatusResponse,
  ExtractionHistoryResponse,
  ExtractedPropertiesResponse,
  ExtractedPropertyValuesResponse,
  ExtractedValue,
  GroupedExtractedValues,
  ExtractionFilters,
} from '@/types/extraction';

// ============================================================================
// Query Key Factory
// ============================================================================

export const extractionLegacyKeys = {
  all: ['extraction-legacy'] as const,
  status: (runId?: string) => [...extractionLegacyKeys.all, 'status', runId ?? ''] as const,
  history: (limit: number, page: number) =>
    [...extractionLegacyKeys.all, 'history', limit, page] as const,
  properties: (runId?: string, searchTerm?: string, hasErrors?: boolean) =>
    [...extractionLegacyKeys.all, 'properties', runId ?? '', searchTerm ?? '', String(hasErrors ?? '')] as const,
  propertyValues: (propertyName: string, runId?: string, category?: string, hasErrors?: boolean) =>
    [...extractionLegacyKeys.all, 'propertyValues', propertyName, runId ?? '', category ?? '', String(hasErrors ?? '')] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook to fetch and manage extraction status
 */
export function useExtractionStatus(runId?: string) {
  const query = useQuery({
    queryKey: extractionLegacyKeys.status(runId),
    queryFn: () => {
      const params: Record<string, string | number | boolean | undefined> = {};
      if (runId) params.run_id = runId;
      return apiClient.get<ExtractionStatusResponse>('/extraction/status', { params });
    },
    // Auto-refresh when extraction is running
    refetchInterval: (q) => {
      const data = q.state.data;
      if (data?.current_run?.status === 'running') {
        return 5000;
      }
      return false;
    },
  });

  return {
    status: query.data ?? null,
    currentRun: query.data?.current_run ?? null,
    lastRun: query.data?.last_completed_run ?? null,
    stats: query.data?.stats ?? null,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook to fetch extraction history
 */
export function useExtractionHistory(limit: number = 20, page: number = 1) {
  const query = useQuery({
    queryKey: extractionLegacyKeys.history(limit, page),
    queryFn: () =>
      apiClient.get<ExtractionHistoryResponse>('/extraction/history', {
        params: { limit, page },
      }),
  });

  return {
    runs: query.data?.runs ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? 1,
    pageSize: query.data?.page_size ?? limit,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook to fetch list of properties with extracted data
 */
export function useExtractedProperties(runId?: string, filters?: ExtractionFilters) {
  const query = useQuery({
    queryKey: extractionLegacyKeys.properties(runId, filters?.searchTerm, filters?.hasErrors),
    queryFn: () => {
      const params: Record<string, string | number | boolean | undefined> = {};
      if (runId) params.run_id = runId;
      if (filters?.searchTerm) params.search = filters.searchTerm;
      if (filters?.hasErrors !== undefined) params.has_errors = filters.hasErrors;
      return apiClient.get<ExtractedPropertiesResponse>('/extraction/properties', { params });
    },
  });

  // Filter properties locally if needed
  const filteredProperties = useMemo(() => {
    if (!query.data?.properties) return [];
    let result = query.data.properties;

    if (filters?.searchTerm) {
      const search = filters.searchTerm.toLowerCase();
      result = result.filter(p =>
        p.property_name.toLowerCase().includes(search)
      );
    }

    if (filters?.hasErrors === true) {
      result = result.filter(p => p.error_count > 0);
    } else if (filters?.hasErrors === false) {
      result = result.filter(p => p.error_count === 0);
    }

    return result;
  }, [query.data?.properties, filters]);

  return {
    properties: filteredProperties,
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook to fetch extracted values for a specific property
 */
export function useExtractedPropertyValues(
  propertyName: string,
  runId?: string,
  filters?: ExtractionFilters
) {
  const query = useQuery({
    queryKey: extractionLegacyKeys.propertyValues(propertyName, runId, filters?.category, filters?.hasErrors),
    queryFn: () => {
      const params: Record<string, string | number | boolean | undefined> = {};
      if (runId) params.run_id = runId;
      if (filters?.category) params.category = filters.category;
      if (filters?.hasErrors !== undefined) params.has_errors = filters.hasErrors;
      const encodedName = encodeURIComponent(propertyName);
      return apiClient.get<ExtractedPropertyValuesResponse>(
        `/extraction/properties/${encodedName}`,
        { params }
      );
    },
    enabled: !!propertyName,
  });

  const rawValues = query.data?.values;

  // Group values by category
  const groupedValues = useMemo((): GroupedExtractedValues[] => {
    if (!rawValues) return [];

    const groups: Record<string, ExtractedValue[]> = {};

    for (const value of rawValues) {
      const category = value.field_category || 'Uncategorized';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(value);
    }

    return Object.entries(groups)
      .map(([category, values]) => ({
        category,
        values,
        errorCount: values.filter(v => v.is_error).length,
      }))
      .sort((a, b) => a.category.localeCompare(b.category));
  }, [rawValues]);

  // Filter values locally
  const filteredValues = useMemo(() => {
    if (!rawValues) return [];
    let result = rawValues;

    if (filters?.searchTerm) {
      const search = filters.searchTerm.toLowerCase();
      result = result.filter(v =>
        v.field_name.toLowerCase().includes(search) ||
        v.value_text?.toLowerCase().includes(search)
      );
    }

    if (filters?.category) {
      result = result.filter(v => v.field_category === filters.category);
    }

    if (filters?.hasErrors === true) {
      result = result.filter(v => v.is_error);
    } else if (filters?.hasErrors === false) {
      result = result.filter(v => !v.is_error);
    }

    return result;
  }, [rawValues, filters]);

  return {
    propertyName: query.data?.property_name ?? propertyName,
    values: filteredValues,
    groupedValues,
    categories: query.data?.categories ?? [],
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook to trigger a manual extraction run
 */
export function useStartExtraction() {
  const queryClient = useQueryClient();

  const startMutation = useMutation({
    mutationFn: () =>
      apiClient.post<ExtractionRun>('/extraction/start', { source: 'local' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: extractionLegacyKeys.all });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (runId: string) =>
      apiClient.post<void>('/extraction/cancel', null, {
        params: { run_id: runId },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: extractionLegacyKeys.all });
    },
  });

  return {
    startExtraction: async (): Promise<ExtractionRun | null> => {
      try {
        return await startMutation.mutateAsync();
      } catch {
        return null;
      }
    },
    cancelExtraction: async (runId: string): Promise<boolean> => {
      try {
        await cancelMutation.mutateAsync(runId);
        return true;
      } catch {
        return false;
      }
    },
    isLoading: startMutation.isPending || cancelMutation.isPending,
    error: startMutation.error ?? cancelMutation.error ?? null,
  };
}

// ============================================================================
// Helper Functions (unchanged)
// ============================================================================

/**
 * Helper function to format extracted value for display
 */
export function formatExtractedValue(value: ExtractedValue): string {
  if (value.is_error) {
    return value.error_message || 'Error';
  }

  switch (value.data_type) {
    case 'numeric':
      if (value.value_numeric !== undefined && value.value_numeric !== null) {
        // Format as currency if it looks like money (large numbers)
        if (Math.abs(value.value_numeric) >= 1000) {
          return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
          }).format(value.value_numeric);
        }
        // Format as percentage if field name suggests it
        if (value.field_name.toLowerCase().includes('rate') ||
            value.field_name.toLowerCase().includes('percent') ||
            value.field_name.toLowerCase().includes('%')) {
          return `${(value.value_numeric * 100).toFixed(2)}%`;
        }
        return value.value_numeric.toLocaleString('en-US', {
          maximumFractionDigits: 2,
        });
      }
      return value.value_text || '-';

    case 'date':
      if (value.value_date) {
        return new Date(value.value_date).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        });
      }
      return value.value_text || '-';

    case 'boolean':
      return value.value_text === 'true' ? 'Yes' : 'No';

    default:
      return value.value_text || '-';
  }
}

/**
 * Get duration string from extraction run
 */
export function getExtractionDuration(run: ExtractionRun): string {
  if (!run.completed_at) {
    const start = new Date(run.started_at);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);
    return formatDuration(seconds);
  }

  const start = new Date(run.started_at);
  const end = new Date(run.completed_at);
  const seconds = Math.floor((end.getTime() - start.getTime()) / 1000);
  return formatDuration(seconds);
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}
