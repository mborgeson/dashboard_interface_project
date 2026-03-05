import { useState, useEffect, useCallback } from 'react';
import { get, post } from '@/lib/api';
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

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

/**
 * Fetch the overall grouping pipeline status.
 * GET /extraction/grouping/status
 */
export function useGroupPipelineStatus() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      const result = await get<PipelineStatus>('/extraction/grouping/status');
      setStatus(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { status, isLoading, error, refetch };
}

/**
 * Fetch all groups (summary list).
 * GET /extraction/grouping/groups
 */
export function useGroups() {
  const [data, setData] = useState<GroupListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      const result = await get<GroupListResponse>('/extraction/grouping/groups');
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return {
    groups: data?.groups ?? ([] as GroupSummary[]),
    totalGroups: data?.total_groups ?? 0,
    totalUngrouped: data?.total_ungrouped ?? 0,
    totalEmptyTemplates: data?.total_empty_templates ?? 0,
    isLoading,
    error,
    refetch,
  };
}

/**
 * Fetch detail for a single group.
 * GET /extraction/grouping/groups/{name}
 *
 * Skips the request when `name` is empty.
 */
export function useGroupDetail(name: string) {
  const [detail, setDetail] = useState<GroupDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    if (!name) {
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      const encoded = encodeURIComponent(name);
      const result = await get<GroupDetail>(`/extraction/grouping/groups/${encoded}`);
      setDetail(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [name]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { detail, isLoading, error, refetch };
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

/**
 * Trigger discovery phase.
 * POST /extraction/grouping/discover
 */
export function useRunDiscovery() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (): Promise<DiscoveryResponse | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await post<DiscoveryResponse>('/extraction/grouping/discover');
      return result;
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Unknown error');
      setError(e);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutate, isLoading, error };
}

/**
 * Trigger fingerprinting phase.
 * POST /extraction/grouping/fingerprint
 */
export function useRunFingerprint() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (): Promise<FingerprintResponse | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await post<FingerprintResponse>('/extraction/grouping/fingerprint');
      return result;
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Unknown error');
      setError(e);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutate, isLoading, error };
}

/**
 * Trigger reference mapping phase.
 * POST /extraction/grouping/reference-map
 */
export function useRunReferenceMap() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (): Promise<ReferenceMappingResponse | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await post<ReferenceMappingResponse>('/extraction/grouping/reference-map');
      return result;
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Unknown error');
      setError(e);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutate, isLoading, error };
}

/**
 * Run conflict check across groups.
 * POST /extraction/grouping/conflict-check
 */
export function useRunConflictCheck() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (): Promise<ConflictCheckResponse | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await post<ConflictCheckResponse>('/extraction/grouping/conflict-check');
      return result;
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Unknown error');
      setError(e);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutate, isLoading, error };
}

/**
 * Extract values for a single group (supports dry-run).
 * POST /extraction/grouping/extract/{name}
 */
export function useRunGroupExtraction() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (
      name: string,
      options: { dry_run: boolean } = { dry_run: false },
    ): Promise<GroupExtractionResponse | null> => {
      try {
        setIsLoading(true);
        setError(null);
        const encoded = encodeURIComponent(name);
        const result = await post<GroupExtractionResponse>(
          `/extraction/grouping/extract/${encoded}`,
          options,
        );
        return result;
      } catch (err) {
        const e = err instanceof Error ? err : new Error('Unknown error');
        setError(e);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { mutate, isLoading, error };
}

/**
 * Approve a group's extraction results.
 * POST /extraction/grouping/approve/{name}
 */
export function useApproveGroup() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (name: string): Promise<GroupApprovalResponse | null> => {
      try {
        setIsLoading(true);
        setError(null);
        const encoded = encodeURIComponent(name);
        const result = await post<GroupApprovalResponse>(
          `/extraction/grouping/approve/${encoded}`,
        );
        return result;
      } catch (err) {
        const e = err instanceof Error ? err : new Error('Unknown error');
        setError(e);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { mutate, isLoading, error };
}

/**
 * Run batch extraction across multiple groups.
 * POST /extraction/grouping/extract-batch
 */
export function useRunBatchExtraction() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (options: {
      group_names: string[];
      dry_run: boolean;
      stop_on_error: boolean;
    }): Promise<BatchExtractionResponse | null> => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await post<BatchExtractionResponse>(
          '/extraction/grouping/extract-batch',
          options,
        );
        return result;
      } catch (err) {
        const e = err instanceof Error ? err : new Error('Unknown error');
        setError(e);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { mutate, isLoading, error };
}

/**
 * Run cross-group validation.
 * POST /extraction/grouping/validate
 */
export function useRunValidation() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (): Promise<ValidationResponse | null> => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await post<ValidationResponse>('/extraction/grouping/validate');
      return result;
    } catch (err) {
      const e = err instanceof Error ? err : new Error('Unknown error');
      setError(e);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutate, isLoading, error };
}
