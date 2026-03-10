import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type {
  PipelineStatus,
  GroupSummary,
  GroupDetail,
  DiscoveryResponse,
  FingerprintResponse,
  GroupListResponse,
  ReferenceMappingResponse,
  ConflictCheckResponse,
  GroupExtractionResponse,
  GroupApprovalResponse,
  BatchExtractionResponse,
  ValidationResponse,
} from '@/types/grouping';

// ============================================================================
// Query Key Factory
// ============================================================================

export const groupPipelineKeys = {
  all: ['group-pipeline'] as const,
  status: () => [...groupPipelineKeys.all, 'status'] as const,
  groups: () => [...groupPipelineKeys.all, 'groups'] as const,
  groupDetail: (name: string) => [...groupPipelineKeys.all, 'detail', name] as const,
};

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/**
 * Fetch the overall grouping pipeline status.
 * GET /extraction/grouping/status
 */
export function useGroupPipelineStatus() {
  const query = useQuery({
    queryKey: groupPipelineKeys.status(),
    queryFn: () => apiClient.get<PipelineStatus>('/extraction/grouping/status'),
  });

  return {
    status: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Fetch all groups (summary list).
 * GET /extraction/grouping/groups
 */
export function useGroups() {
  const query = useQuery({
    queryKey: groupPipelineKeys.groups(),
    queryFn: () => apiClient.get<GroupListResponse>('/extraction/grouping/groups'),
  });

  return {
    groups: query.data?.groups ?? ([] as GroupSummary[]),
    totalGroups: query.data?.total_groups ?? 0,
    totalUngrouped: query.data?.total_ungrouped ?? 0,
    totalEmptyTemplates: query.data?.total_empty_templates ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Fetch detail for a single group.
 * GET /extraction/grouping/groups/{name}
 *
 * Skips the request when `name` is empty.
 */
export function useGroupDetail(name: string) {
  const query = useQuery({
    queryKey: groupPipelineKeys.groupDetail(name),
    queryFn: () => {
      const encoded = encodeURIComponent(name);
      return apiClient.get<GroupDetail>(`/extraction/grouping/groups/${encoded}`);
    },
    enabled: !!name,
  });

  return {
    detail: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/**
 * Trigger discovery phase.
 * POST /extraction/grouping/discover
 */
export function useRunDiscovery() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.post<DiscoveryResponse>('/extraction/grouping/discover'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (): Promise<DiscoveryResponse | null> => {
      try {
        return await mutation.mutateAsync();
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Trigger fingerprinting phase.
 * POST /extraction/grouping/fingerprint
 */
export function useRunFingerprint() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.post<FingerprintResponse>('/extraction/grouping/fingerprint'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (): Promise<FingerprintResponse | null> => {
      try {
        return await mutation.mutateAsync();
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Trigger reference mapping phase.
 * POST /extraction/grouping/reference-map
 */
export function useRunReferenceMap() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.post<ReferenceMappingResponse>('/extraction/grouping/reference-map'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (): Promise<ReferenceMappingResponse | null> => {
      try {
        return await mutation.mutateAsync();
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Run conflict check across groups.
 * POST /extraction/grouping/conflict-check
 */
export function useRunConflictCheck() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.post<ConflictCheckResponse>('/extraction/grouping/conflict-check'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (): Promise<ConflictCheckResponse | null> => {
      try {
        return await mutation.mutateAsync();
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Extract values for a single group (supports dry-run).
 * POST /extraction/grouping/extract/{name}
 */
export function useRunGroupExtraction() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: ({
      name,
      options = { dry_run: false },
    }: {
      name: string;
      options?: { dry_run: boolean };
    }) => {
      const encoded = encodeURIComponent(name);
      return apiClient.post<GroupExtractionResponse>(
        `/extraction/grouping/extract/${encoded}`,
        options,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (
      name: string,
      options: { dry_run: boolean } = { dry_run: false },
    ): Promise<GroupExtractionResponse | null> => {
      try {
        return await mutation.mutateAsync({ name, options });
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Approve a group's extraction results.
 * POST /extraction/grouping/approve/{name}
 */
export function useApproveGroup() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (name: string) => {
      const encoded = encodeURIComponent(name);
      return apiClient.post<GroupApprovalResponse>(
        `/extraction/grouping/approve/${encoded}`,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (name: string): Promise<GroupApprovalResponse | null> => {
      try {
        return await mutation.mutateAsync(name);
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Run batch extraction across multiple groups.
 * POST /extraction/grouping/extract-batch
 */
export function useRunBatchExtraction() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (options: {
      group_names: string[];
      dry_run: boolean;
      stop_on_error: boolean;
    }) =>
      apiClient.post<BatchExtractionResponse>(
        '/extraction/grouping/extract-batch',
        options,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (options: {
      group_names: string[];
      dry_run: boolean;
      stop_on_error: boolean;
    }): Promise<BatchExtractionResponse | null> => {
      try {
        return await mutation.mutateAsync(options);
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Run cross-group validation.
 * POST /extraction/grouping/validate
 */
export function useRunValidation() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      apiClient.post<ValidationResponse>('/extraction/grouping/validate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: groupPipelineKeys.all });
    },
  });

  return {
    mutate: async (): Promise<ValidationResponse | null> => {
      try {
        return await mutation.mutateAsync();
      } catch {
        return null;
      }
    },
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}
