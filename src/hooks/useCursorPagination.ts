/**
 * Hook for cursor-based pagination with TanStack Query integration.
 *
 * Works with backend endpoints that return CursorPaginatedResponse:
 *   { items: T[], next_cursor: string | null, prev_cursor: string | null, has_more: boolean, total: number | null }
 */

import { useState, useCallback, useMemo } from 'react';
import {
  useQuery,
  useQueryClient,
  type UseQueryOptions,
  type QueryKey,
} from '@tanstack/react-query';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Shape returned by cursor-paginated backend endpoints. */
export interface CursorPaginatedResponse<T> {
  items: T[];
  next_cursor: string | null;
  prev_cursor: string | null;
  has_more: boolean;
  total: number | null;
}

/** Parameters sent to cursor-paginated endpoints. */
export interface CursorPaginationParams {
  cursor: string | null;
  limit: number;
  direction: 'next' | 'prev';
}

export interface UseCursorPaginationOptions<T> {
  /** TanStack Query key prefix (the cursor is appended automatically). */
  queryKey: QueryKey;

  /**
   * Async function that fetches a page from the API.
   * Receives the current pagination params and should return the response.
   */
  queryFn: (params: CursorPaginationParams) => Promise<CursorPaginatedResponse<T>>;

  /** Items per page (default: 20). */
  limit?: number;

  /** Whether the query is enabled (default: true). */
  enabled?: boolean;

  /** Additional TanStack Query options. */
  queryOptions?: Omit<
    UseQueryOptions<CursorPaginatedResponse<T>>,
    'queryKey' | 'queryFn' | 'enabled'
  >;
}

export interface UseCursorPaginationReturn<T> {
  /** The current page of items. */
  items: T[];

  /** Whether there are more items after the current page. */
  hasMore: boolean;

  /** Total count (may be null if the backend omits it). */
  total: number | null;

  /** Whether data is currently loading. */
  isLoading: boolean;

  /** Whether a background refetch is in progress. */
  isFetching: boolean;

  /** Error from the last fetch, if any. */
  error: Error | null;

  /** Navigate to the next page. No-op if already at the end. */
  fetchNextPage: () => void;

  /** Navigate to the previous page. No-op if already at the start. */
  fetchPrevPage: () => void;

  /** Reset to the first page. */
  resetPagination: () => void;

  /** Whether there is a previous page available. */
  hasPrevPage: boolean;

  /** Whether there is a next page available. */
  hasNextPage: boolean;

  /** The current cursor string (null on first page). */
  currentCursor: string | null;
}

// ---------------------------------------------------------------------------
// Hook implementation
// ---------------------------------------------------------------------------

export function useCursorPagination<T>(
  options: UseCursorPaginationOptions<T>,
): UseCursorPaginationReturn<T> {
  const {
    queryKey,
    queryFn,
    limit = 20,
    enabled = true,
    queryOptions,
  } = options;

  const queryClient = useQueryClient();

  // Track cursor + direction for the current request
  const [cursor, setCursor] = useState<string | null>(null);
  const [direction, setDirection] = useState<'next' | 'prev'>('next');

  // Keep a stack of prev cursors so we can go back
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);

  const params: CursorPaginationParams = useMemo(
    () => ({ cursor, limit, direction }),
    [cursor, limit, direction],
  );

  // Build the full query key including pagination state
  const fullQueryKey = useMemo(
    () => [...(Array.isArray(queryKey) ? queryKey : [queryKey]), { cursor, limit, direction }],
    [queryKey, cursor, limit, direction],
  );

  const query = useQuery<CursorPaginatedResponse<T>, Error>({
    queryKey: fullQueryKey,
    queryFn: () => queryFn(params),
    enabled,
    // Keep previous data visible while fetching new page
    placeholderData: (previousData) => previousData,
    ...queryOptions,
  });

  const nextCursor = query.data?.next_cursor ?? null;

  const fetchNextPage = useCallback(() => {
    if (!nextCursor) return;

    setCursorHistory((prev) => [...prev, cursor ?? '']);
    setCursor(nextCursor);
    setDirection('next');
  }, [nextCursor, cursor]);

  const fetchPrevPage = useCallback(() => {
    if (cursorHistory.length === 0) return;

    const prevCursors = [...cursorHistory];
    const prevCursor = prevCursors.pop()!;
    setCursorHistory(prevCursors);
    setCursor(prevCursor === '' ? null : prevCursor);
    setDirection('prev');
  }, [cursorHistory]);

  const resetPagination = useCallback(() => {
    setCursor(null);
    setDirection('next');
    setCursorHistory([]);
    // Invalidate all pages for this base query key
    queryClient.invalidateQueries({ queryKey: Array.isArray(queryKey) ? queryKey : [queryKey] });
  }, [queryClient, queryKey]);

  return {
    items: query.data?.items ?? [],
    hasMore: query.data?.has_more ?? false,
    total: query.data?.total ?? null,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error,
    fetchNextPage,
    fetchPrevPage,
    resetPagination,
    hasPrevPage: cursorHistory.length > 0,
    hasNextPage: query.data?.next_cursor != null,
    currentCursor: cursor,
  };
}
