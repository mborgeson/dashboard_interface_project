/**
 * Route Prefetch Hook
 *
 * Prefetches route data on link hover/focus for improved navigation performance.
 * Features:
 * - Debounced prefetching to prevent excessive requests
 * - Caching of already-prefetched routes
 * - Integration with React Query for data prefetching
 * - Support for lazy-loaded route components
 */

import { useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { propertyKeys } from './api/useProperties';
import { dealKeys } from './api/useDeals';
import { transactionKeys } from './api/useTransactions';
import { documentKeys } from './api/useDocuments';
import { marketDataKeys } from './api/useMarketData';
import { interestRateKeys } from './api/useInterestRates';
import { reportingKeys } from './api/useReporting';
import { extractionKeys } from './api/useExtraction';
import { get } from '@/lib/api';

// Route to prefetch config mapping
interface RoutePrefetchConfig {
  queryKey: readonly unknown[];
  queryFn: () => Promise<unknown>;
  staleTime?: number;
}

// Default stale times for different data types
const STALE_TIMES = {
  short: 2 * 60 * 1000,    // 2 minutes - frequently changing data
  medium: 5 * 60 * 1000,   // 5 minutes - moderately stable data
  long: 15 * 60 * 1000,    // 15 minutes - stable data
} as const;

// Debounce delay in milliseconds
const DEBOUNCE_DELAY = 150;

/**
 * Get prefetch configurations for a specific route
 */
function getRoutePrefetchConfigs(route: string): RoutePrefetchConfig[] {
  const configs: RoutePrefetchConfig[] = [];

  switch (route) {
    case '/':
      // Dashboard prefetches are handled by usePrefetchDashboard
      break;

    case '/investments':
      configs.push({
        queryKey: propertyKeys.lists(),
        queryFn: () => get('/properties'),
        staleTime: STALE_TIMES.medium,
      });
      break;

    case '/transactions':
      configs.push({
        queryKey: transactionKeys.list({}),
        queryFn: () => get('/transactions'),
        staleTime: STALE_TIMES.medium,
      });
      break;

    case '/deals':
      configs.push({
        queryKey: dealKeys.lists(),
        queryFn: () => get('/deals'),
        staleTime: STALE_TIMES.medium,
      });
      break;

    case '/documents':
      configs.push({
        queryKey: documentKeys.list({}),
        queryFn: () => get('/documents'),
        staleTime: STALE_TIMES.medium,
      });
      break;

    case '/analytics':
      configs.push({
        queryKey: propertyKeys.lists(),
        queryFn: () => get('/properties'),
        staleTime: STALE_TIMES.medium,
      });
      break;

    case '/interest-rates':
      configs.push({
        queryKey: interestRateKeys.current(),
        queryFn: () => get('/interest-rates/current'),
        staleTime: STALE_TIMES.short,
      });
      configs.push({
        queryKey: interestRateKeys.yieldCurve(),
        queryFn: () => get('/interest-rates/yield-curve'),
        staleTime: STALE_TIMES.short,
      });
      break;

    case '/market':
      configs.push({
        queryKey: marketDataKeys.overview(),
        queryFn: () => get('/market/overview'),
        staleTime: STALE_TIMES.long,
      });
      configs.push({
        queryKey: marketDataKeys.submarkets(),
        queryFn: () => get('/market/submarkets'),
        staleTime: STALE_TIMES.long,
      });
      break;

    case '/reporting':
      configs.push({
        queryKey: reportingKeys.templateList({}),
        queryFn: () => get('/reporting/templates'),
        staleTime: STALE_TIMES.long,
      });
      configs.push({
        queryKey: reportingKeys.queueList({}),
        queryFn: () => get('/reporting/queue'),
        staleTime: STALE_TIMES.short,
      });
      break;

    case '/extraction':
      configs.push({
        queryKey: extractionKeys.historyList({}),
        queryFn: () => get('/extraction/history'),
        staleTime: STALE_TIMES.short,
      });
      break;

    case '/mapping':
      configs.push({
        queryKey: propertyKeys.lists(),
        queryFn: () => get('/properties'),
        staleTime: STALE_TIMES.medium,
      });
      break;
  }

  return configs;
}

/**
 * Lazy load route component modules
 * This helps with code splitting by preloading the JS chunks
 */
async function prefetchRouteComponent(route: string): Promise<void> {
  try {
    switch (route) {
      case '/investments':
        await import('@/features/investments');
        break;
      case '/transactions':
        await import('@/features/transactions');
        break;
      case '/deals':
        await import('@/features/deals');
        break;
      case '/documents':
        await import('@/features/documents');
        break;
      case '/analytics':
        await import('@/features/analytics');
        break;
      case '/interest-rates':
        await import('@/features/interest-rates');
        break;
      case '/market':
        await import('@/features/market');
        break;
      case '/reporting':
        await import('@/features/reporting-suite');
        break;
      case '/extraction':
        await import('@/features/extraction');
        break;
      case '/mapping':
        await import('@/features/mapping');
        break;
    }
  } catch {
    // Silently fail - component will be loaded on navigation anyway
  }
}

export interface UsePrefetchOptions {
  /**
   * Whether to prefetch the route's data queries
   * @default true
   */
  prefetchData?: boolean;
  /**
   * Whether to prefetch the route's component chunk
   * @default true
   */
  prefetchComponent?: boolean;
  /**
   * Custom debounce delay in milliseconds
   * @default 150
   */
  debounceDelay?: number;
}

export interface UsePrefetchReturn {
  /**
   * Trigger prefetch for a route
   */
  prefetch: (route: string) => void;
  /**
   * Cancel pending prefetch
   */
  cancelPrefetch: () => void;
  /**
   * Check if a route has been prefetched
   */
  isPrefetched: (route: string) => boolean;
}

/**
 * Hook for prefetching route data and components
 *
 * @example
 * ```tsx
 * function NavLink({ to, children }) {
 *   const { prefetch, cancelPrefetch } = usePrefetch();
 *
 *   return (
 *     <Link
 *       to={to}
 *       onMouseEnter={() => prefetch(to)}
 *       onMouseLeave={cancelPrefetch}
 *       onFocus={() => prefetch(to)}
 *       onBlur={cancelPrefetch}
 *     >
 *       {children}
 *     </Link>
 *   );
 * }
 * ```
 */
export function usePrefetch(options: UsePrefetchOptions = {}): UsePrefetchReturn {
  const {
    prefetchData = true,
    prefetchComponent = true,
    debounceDelay = DEBOUNCE_DELAY,
  } = options;

  const queryClient = useQueryClient();
  const prefetchedRoutesRef = useRef<Set<string>>(new Set());
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentRouteRef = useRef<string | null>(null);

  const cancelPrefetch = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    currentRouteRef.current = null;
  }, []);

  const prefetch = useCallback(
    (route: string) => {
      // Skip if already prefetched
      if (prefetchedRoutesRef.current.has(route)) {
        return;
      }

      // Cancel any pending prefetch
      cancelPrefetch();

      // Store current route being prefetched
      currentRouteRef.current = route;

      // Debounce the prefetch
      timeoutRef.current = setTimeout(async () => {
        // Verify we're still prefetching the same route
        if (currentRouteRef.current !== route) {
          return;
        }

        // Mark as prefetched early to prevent duplicate requests
        prefetchedRoutesRef.current.add(route);

        // Prefetch component chunk
        if (prefetchComponent) {
          prefetchRouteComponent(route);
        }

        // Prefetch data queries
        if (prefetchData) {
          const configs = getRoutePrefetchConfigs(route);

          for (const config of configs) {
            // Only prefetch if data is not already fresh in cache
            const existingData = queryClient.getQueryData(config.queryKey);
            if (!existingData) {
              queryClient.prefetchQuery({
                queryKey: config.queryKey,
                queryFn: config.queryFn,
                staleTime: config.staleTime,
              });
            }
          }
        }
      }, debounceDelay);
    },
    [queryClient, prefetchData, prefetchComponent, debounceDelay, cancelPrefetch]
  );

  const isPrefetched = useCallback((route: string) => {
    return prefetchedRoutesRef.current.has(route);
  }, []);

  return {
    prefetch,
    cancelPrefetch,
    isPrefetched,
  };
}

export default usePrefetch;
