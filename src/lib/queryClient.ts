import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 30 * 60 * 1000, // 30 minutes (formerly cacheTime)
      retry: 2,
      refetchOnWindowFocus: false,
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
