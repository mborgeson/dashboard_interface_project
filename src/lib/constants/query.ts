/**
 * React Query staleTime constants
 *
 * Centralized caching policy for all React Query hooks.
 * Values are chosen based on data volatility:
 *
 * - SHORT (1 min): Rapidly changing data (kanban boards, activity feeds)
 * - BRIEF (2 min): Frequently updated data (activity feeds, live status)
 * - MEDIUM (5 min): Moderately stable data (deals, documents, general queries)
 * - MODERATE (7 min): Moderate-change data (transactions)
 * - LONG (10 min): Stable within a session (properties, extracted data)
 * - EXTENDED (15 min): Infrequently changing data (market data, interest rates)
 * - HALF_HOUR (30 min): Rarely changing data (report widgets, pipeline summaries)
 * - REFERENCE (1 hour): Near-static reference data (data sources, configs)
 *
 * The default staleTime in queryClient.ts is 5 min (MEDIUM).
 * Only override when a query's data volatility differs from the default.
 */
export const STALE_TIMES = {
  /** 1 minute -- rapidly changing data (kanban, real-time status) */
  SHORT: 1000 * 60 * 1,
  /** 2 minutes -- frequently updated data (activity feeds, live status) */
  BRIEF: 1000 * 60 * 2,
  /** 5 minutes -- default for most queries (deals, documents) */
  MEDIUM: 1000 * 60 * 5,
  /** 7 minutes -- moderate-change data (transactions) */
  MODERATE: 1000 * 60 * 7,
  /** 10 minutes -- stable within a session (properties, extracted data) */
  LONG: 1000 * 60 * 10,
  /** 15 minutes -- infrequently changing data (market data, interest rates) */
  EXTENDED: 1000 * 60 * 15,
  /** 30 minutes -- rarely changing data (report widgets, pipeline summaries) */
  HALF_HOUR: 1000 * 60 * 30,
  /** 1 hour -- near-static reference data (data sources, configs) */
  REFERENCE: 1000 * 60 * 60,
} as const;

export type StaleTime = (typeof STALE_TIMES)[keyof typeof STALE_TIMES];
