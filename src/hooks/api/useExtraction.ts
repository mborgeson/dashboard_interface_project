import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post, del } from '@/lib/api';
import type {
  ExtractionRun,
  ExtractionHistoryFilters,
  ExtractionHistoryResponse,
  ExtractionStatusResponse,
  StartExtractionInput,
  ExtractedValue,
} from '@/types/api';

// ============================================================================
// Query Key Factory
// ============================================================================

export const extractionKeys = {
  all: ['extractions'] as const,
  history: () => [...extractionKeys.all, 'history'] as const,
  historyList: (filters: ExtractionHistoryFilters) => [...extractionKeys.history(), filters] as const,
  runs: () => [...extractionKeys.all, 'runs'] as const,
  run: (id: string) => [...extractionKeys.runs(), id] as const,
  status: (id: string) => [...extractionKeys.all, 'status', id] as const,
  values: (runId: string) => [...extractionKeys.all, 'values', runId] as const,
  propertyExtractions: (propertyId: string) => [...extractionKeys.all, 'property', propertyId] as const,
  dealExtractions: (dealId: string) => [...extractionKeys.all, 'deal', dealId] as const,
};

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Fetch extraction run status (useful for polling during active extractions)
 */
export function useExtractionStatus(
  runId: string | undefined,
  options?: Omit<UseQueryOptions<ExtractionStatusResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: extractionKeys.status(runId || ''),
    queryFn: () => get<ExtractionStatusResponse>(`/extraction/status`, { run_id: runId }),
    enabled: !!runId,
    // Poll every 2 seconds while extraction is in progress
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && (data.status === 'pending' || data.status === 'processing')) {
        return 2000;
      }
      return false;
    },
    ...options,
  });
}

/**
 * Fetch a single extraction run with all details
 */
export function useExtractionRun(
  runId: string,
  options?: Omit<UseQueryOptions<ExtractionRun>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: extractionKeys.run(runId),
    queryFn: () => get<ExtractionRun>(`/extraction/status`, { run_id: runId }),
    enabled: !!runId,
    ...options,
  });
}

/**
 * Fetch extraction history with filters
 */
export function useExtractionHistory(
  filters: ExtractionHistoryFilters = {},
  options?: Omit<UseQueryOptions<ExtractionHistoryResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: extractionKeys.historyList(filters),
    queryFn: () => get<ExtractionHistoryResponse>('/extraction/history', filters as Record<string, unknown>),
    ...options,
  });
}

/**
 * Fetch extracted values for a specific run
 */
export function useExtractedValues(
  runId: string,
  options?: Omit<UseQueryOptions<ExtractedValue[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: extractionKeys.values(runId),
    queryFn: () => get<ExtractedValue[]>(`/extractions/${runId}/values`),
    enabled: !!runId,
    ...options,
  });
}

/**
 * Fetch all extractions for a specific property
 */
export function usePropertyExtractions(
  propertyId: string,
  options?: Omit<UseQueryOptions<ExtractionRun[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: extractionKeys.propertyExtractions(propertyId),
    queryFn: () => get<ExtractionRun[]>(`/properties/${propertyId}/extractions`),
    enabled: !!propertyId,
    ...options,
  });
}

/**
 * Fetch all extractions for a specific deal
 */
export function useDealExtractions(
  dealId: string,
  options?: Omit<UseQueryOptions<ExtractionRun[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: extractionKeys.dealExtractions(dealId),
    queryFn: () => get<ExtractionRun[]>(`/deals/${dealId}/extractions`),
    enabled: !!dealId,
    ...options,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Start a new extraction run
 */
export function useStartExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: StartExtractionInput) =>
      post<ExtractionRun, StartExtractionInput>('/extraction/start', data),
    onSuccess: (data) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: extractionKeys.history() });

      // If property-specific, invalidate property extractions
      if (data.propertyId) {
        queryClient.invalidateQueries({
          queryKey: extractionKeys.propertyExtractions(data.propertyId),
        });
      }

      // If deal-specific, invalidate deal extractions
      if (data.dealId) {
        queryClient.invalidateQueries({
          queryKey: extractionKeys.dealExtractions(data.dealId),
        });
      }
    },
  });
}

/**
 * Cancel an in-progress extraction
 */
export function useCancelExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => post<void>(`/extraction/cancel`, { run_id: runId }),
    onSuccess: (_, runId) => {
      // Invalidate the specific run and status
      queryClient.invalidateQueries({ queryKey: extractionKeys.run(runId) });
      queryClient.invalidateQueries({ queryKey: extractionKeys.status(runId) });
      queryClient.invalidateQueries({ queryKey: extractionKeys.history() });
    },
  });
}

/**
 * Validate an extracted value (mark as validated by user)
 */
export function useValidateExtractedValue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ runId, valueId, validated }: ValidateValueInput) =>
      post<ExtractedValue>(`/extractions/${runId}/values/${valueId}/validate`, { validated }),
    onSuccess: (_, { runId }) => {
      // Invalidate the values for this run
      queryClient.invalidateQueries({ queryKey: extractionKeys.values(runId) });
      queryClient.invalidateQueries({ queryKey: extractionKeys.run(runId) });
    },
  });
}

/**
 * Delete an extraction run
 */
export function useDeleteExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => del<void>(`/extractions/${runId}`),
    onSuccess: (_, runId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: extractionKeys.run(runId) });
      queryClient.removeQueries({ queryKey: extractionKeys.status(runId) });
      queryClient.removeQueries({ queryKey: extractionKeys.values(runId) });
      // Invalidate history
      queryClient.invalidateQueries({ queryKey: extractionKeys.history() });
    },
  });
}

/**
 * Retry a failed extraction
 */
export function useRetryExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => post<ExtractionRun>(`/extractions/${runId}/retry`),
    onSuccess: (data, runId) => {
      // Update the run in cache
      queryClient.setQueryData(extractionKeys.run(runId), data);
      // Invalidate status and history
      queryClient.invalidateQueries({ queryKey: extractionKeys.status(runId) });
      queryClient.invalidateQueries({ queryKey: extractionKeys.history() });
    },
  });
}

// Local type for validate input
interface ValidateValueInput {
  runId: string;
  valueId: string;
  validated: boolean;
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to check if any extraction is currently in progress for a property
 */
export function useIsPropertyExtracting(propertyId: string): boolean {
  const { data } = usePropertyExtractions(propertyId);

  return (
    data?.some(
      (run) => run.status === 'pending' || run.status === 'processing'
    ) ?? false
  );
}

/**
 * Hook to check if any extraction is currently in progress for a deal
 */
export function useIsDealExtracting(dealId: string): boolean {
  const { data } = useDealExtractions(dealId);

  return (
    data?.some(
      (run) => run.status === 'pending' || run.status === 'processing'
    ) ?? false
  );
}
