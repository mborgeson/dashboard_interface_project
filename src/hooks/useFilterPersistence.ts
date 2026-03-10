import { useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * Custom hook for persisting filters in URL search parameters
 * Enables sharing filtered views via URL
 */
type FilterValue = string | number | boolean | string[] | number[] | Record<string, unknown> | null | undefined;

export function useFilterPersistence<T extends Record<string, FilterValue>>(
  filters: T,
  setFilters: (filters: T) => void,
  options: {
    /** Prefix for URL params to avoid conflicts */
    paramPrefix?: string;
    /** Fields to exclude from URL persistence */
    excludeFields?: string[];
    /** Enable/disable persistence */
    enabled?: boolean;
  } = {}
) {
  const {
    paramPrefix = 'f_',
    excludeFields = [],
    enabled = true,
  } = options;

  const [searchParams, setSearchParams] = useSearchParams();

  /** Guard: tracks whether we are currently pushing filter state to the URL.
   *  Prevents re-entrant cycles (filter→URL→searchParams change→filter→…). */
  const isSyncingToUrlRef = useRef(false);

  // Serialize filter value to string
  const serializeValue = (value: FilterValue): string | null => {
    if (value === null || value === undefined || value === '') {
      return null;
    }

    if (Array.isArray(value)) {
      return value.length > 0 ? JSON.stringify(value) : null;
    }

    if (typeof value === 'object') {
      return Object.keys(value).length > 0 ? JSON.stringify(value) : null;
    }

    return String(value);
  };

  // Deserialize filter value from string
  const deserializeValue = (value: string): FilterValue => {
    try {
      // Try parsing as JSON first
      return JSON.parse(value);
    } catch {
      // If not JSON, return as string
      return value;
    }
  };

  // Load filters from URL on mount and when URL changes
  useEffect(() => {
    if (!enabled) return;

    const urlFilters: Record<string, FilterValue> = {};
    let hasFilters = false;

    // Extract all filter params from URL
    searchParams.forEach((value, key) => {
      if (key.startsWith(paramPrefix)) {
        const filterKey = key.substring(paramPrefix.length);
        if (!excludeFields.includes(filterKey)) {
          urlFilters[filterKey] = deserializeValue(value);
          hasFilters = true;
        }
      }
    });

    // Apply URL filters if any exist
    if (hasFilters) {
      setFilters({ ...filters, ...urlFilters });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // Sync filters to URL whenever they change
  useEffect(() => {
    if (!enabled) return;

    // Skip if this effect was triggered by our own URL update
    if (isSyncingToUrlRef.current) {
      isSyncingToUrlRef.current = false;
      return;
    }

    const newParams = new URLSearchParams(searchParams);

    // Remove all existing filter params
    Array.from(newParams.keys()).forEach((key) => {
      if (key.startsWith(paramPrefix)) {
        newParams.delete(key);
      }
    });

    // Add current filter params
    Object.entries(filters).forEach(([key, value]) => {
      if (excludeFields.includes(key)) return;

      const serialized = serializeValue(value);
      if (serialized !== null) {
        newParams.set(`${paramPrefix}${key}`, serialized);
      }
    });

    // Only update URL if the params actually differ
    const currentSorted = new URLSearchParams([...searchParams.entries()].sort()).toString();
    const newSorted = new URLSearchParams([...newParams.entries()].sort()).toString();

    if (currentSorted !== newSorted) {
      isSyncingToUrlRef.current = true;
      setSearchParams(newParams, { replace: true });
    }
  }, [filters, enabled, paramPrefix, excludeFields, searchParams, setSearchParams]);

  // Clear all filters
  const clearFilters = useCallback(() => {
    const newParams = new URLSearchParams(searchParams);
    
    // Remove all filter params
    Array.from(newParams.keys()).forEach((key) => {
      if (key.startsWith(paramPrefix)) {
        newParams.delete(key);
      }
    });

    setSearchParams(newParams, { replace: true });
    
    // Reset filters to empty object
    const emptyFilters: Partial<T> = {};
    Object.keys(filters).forEach((key) => {
      emptyFilters[key as keyof T] = undefined as T[keyof T];
    });
    
    setFilters(emptyFilters as T);
  }, [filters, paramPrefix, searchParams, setSearchParams, setFilters]);

  // Get shareable URL with current filters
  const getShareableUrl = useCallback(() => {
    return window.location.href;
  }, []);

  // Copy shareable URL to clipboard
  const copyShareableUrl = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(getShareableUrl());
      return true;
    } catch {
      return false;
    }
  }, [getShareableUrl]);

  return {
    clearFilters,
    getShareableUrl,
    copyShareableUrl,
  };
}
