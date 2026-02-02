import { useState, useEffect, useCallback, useMemo } from 'react';
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

import { API_URL } from '@/lib/config';

// API base URL from centralized config
const API_BASE = API_URL;

/**
 * Hook to fetch and manage extraction status
 */
export function useExtractionStatus(runId?: string) {
  const [data, setData] = useState<ExtractionStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      const url = runId
        ? `${API_BASE}/extraction/status?run_id=${runId}`
        : `${API_BASE}/extraction/status`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Failed to fetch extraction status: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Auto-refresh when extraction is running
  useEffect(() => {
    if (data?.current_run?.status === 'running') {
      const interval = setInterval(fetchStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [data?.current_run?.status, fetchStatus]);

  return {
    status: data,
    currentRun: data?.current_run,
    lastRun: data?.last_completed_run,
    stats: data?.stats,
    isLoading,
    error,
    refetch: fetchStatus,
  };
}

/**
 * Hook to fetch extraction history
 */
export function useExtractionHistory(limit: number = 20, page: number = 1) {
  const [data, setData] = useState<ExtractionHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams({
        limit: limit.toString(),
        page: page.toString(),
      });
      const response = await fetch(`${API_BASE}/extraction/history?${params}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch extraction history: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [limit, page]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return {
    runs: data?.runs || [],
    total: data?.total || 0,
    page: data?.page || 1,
    pageSize: data?.page_size || limit,
    isLoading,
    error,
    refetch: fetchHistory,
  };
}

/**
 * Hook to fetch list of properties with extracted data
 */
export function useExtractedProperties(runId?: string, filters?: ExtractionFilters) {
  const [data, setData] = useState<ExtractedPropertiesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchProperties = useCallback(async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams();
      if (runId) params.set('run_id', runId);
      if (filters?.searchTerm) params.set('search', filters.searchTerm);
      if (filters?.hasErrors !== undefined) params.set('has_errors', filters.hasErrors.toString());

      const response = await fetch(`${API_BASE}/extraction/properties?${params}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch extracted properties: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [runId, filters?.searchTerm, filters?.hasErrors]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  // Filter properties locally if needed
  const filteredProperties = useMemo(() => {
    if (!data?.properties) return [];
    let result = data.properties;

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
  }, [data?.properties, filters]);

  return {
    properties: filteredProperties,
    total: data?.total || 0,
    isLoading,
    error,
    refetch: fetchProperties,
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
  const [data, setData] = useState<ExtractedPropertyValuesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchValues = useCallback(async () => {
    if (!propertyName) {
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const params = new URLSearchParams();
      if (runId) params.set('run_id', runId);
      if (filters?.category) params.set('category', filters.category);
      if (filters?.hasErrors !== undefined) params.set('has_errors', filters.hasErrors.toString());

      const encodedName = encodeURIComponent(propertyName);
      const response = await fetch(
        `${API_BASE}/extraction/properties/${encodedName}?${params}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch property values: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [propertyName, runId, filters?.category, filters?.hasErrors]);

  useEffect(() => {
    fetchValues();
  }, [fetchValues]);

  // Group values by category
  const groupedValues = useMemo((): GroupedExtractedValues[] => {
    if (!data?.values) return [];

    const groups: Record<string, ExtractedValue[]> = {};

    for (const value of data.values) {
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
  }, [data?.values]);

  // Filter values locally
  const filteredValues = useMemo(() => {
    if (!data?.values) return [];
    let result = data.values;

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
  }, [data?.values, filters]);

  return {
    propertyName: data?.property_name || propertyName,
    values: filteredValues,
    groupedValues,
    categories: data?.categories || [],
    total: data?.total || 0,
    isLoading,
    error,
    refetch: fetchValues,
  };
}

/**
 * Hook to trigger a manual extraction run
 */
export function useStartExtraction() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const startExtraction = useCallback(async (): Promise<ExtractionRun | null> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/extraction/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to start extraction: ${response.statusText}`);
      }

      const result = await response.json();
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const cancelExtraction = useCallback(async (runId: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/extraction/cancel?run_id=${runId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to cancel extraction: ${response.statusText}`);
      }

      return true;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    startExtraction,
    cancelExtraction,
    isLoading,
    error,
  };
}

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
