import { QueryClient } from '@tanstack/react-query';

/**
 * Query Client Configuration - Caching Strategy
 *
 * staleTime values are optimized per query type based on data volatility:
 * - Reference data (data sources): 60 min - rarely changes
 * - Market data: 15 min - updates periodically but not real-time
 * - Properties/Portfolio: 10 min - stable within a session
 * - Transactions: 7 min - moderate change frequency
 * - Kanban boards: 2 min - needs real-time feel for collaboration
 * - Report queues: 30 sec - high visibility for queue status
 *
 * Default staleTime (5 min) applies to queries without explicit overrides.
 * refetchOnWindowFocus is disabled to prevent unnecessary API calls when
 * users switch tabs - data freshness is managed via staleTime instead.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 min default - balanced freshness vs performance
      gcTime: 30 * 60 * 1000, // 30 min garbage collection (formerly cacheTime)
      retry: 2,
      refetchOnWindowFocus: false, // Disabled - prevents unnecessary refetches on tab switch
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

// Utility function to invalidate all queries
export function invalidateAllQueries() {
  return queryClient.invalidateQueries();
}

// Utility function to clear the cache
export function clearQueryCache() {
  return queryClient.clear();
}
