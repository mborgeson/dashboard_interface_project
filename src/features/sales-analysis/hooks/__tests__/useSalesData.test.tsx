import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  salesKeys,
  useSalesData,
  useTimeSeriesAnalytics,
  useSubmarketComparison,
  useBuyerActivity,
  useDistributions,
  useDataQuality,
  useImportStatus,
  useReminderStatus,
} from '../useSalesData';
import type { SalesFilters } from '../../types';

// Mock the entire sales API module
vi.mock('@/lib/api/sales', () => ({
  fetchSalesData: vi.fn().mockResolvedValue({
    data: [],
    total: 0,
    page: 1,
    pageSize: 25,
    totalPages: 0,
  }),
  fetchTimeSeriesAnalytics: vi.fn().mockResolvedValue([]),
  fetchSubmarketComparison: vi.fn().mockResolvedValue([]),
  fetchBuyerActivity: vi.fn().mockResolvedValue([]),
  fetchDistributions: vi.fn().mockResolvedValue([]),
  fetchDataQuality: vi.fn().mockResolvedValue({
    totalRecords: 0,
    recordsByFile: {},
    nullRates: {},
    flaggedOutliers: {},
  }),
  fetchImportStatus: vi.fn().mockResolvedValue({
    unimportedFiles: [],
    lastImportedFile: null,
    lastImportDate: null,
  }),
  triggerImport: vi.fn().mockResolvedValue({ success: true, message: 'ok' }),
  fetchReminderStatus: vi.fn().mockResolvedValue({
    showReminder: false,
    lastImportedFileName: null,
    lastImportedFileDate: null,
  }),
  dismissReminder: vi.fn().mockResolvedValue(undefined),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

const defaultFilters: SalesFilters = {};

// ============================================================================
// Query Key Factory
// ============================================================================

describe('salesKeys', () => {
  it('produces correct base key', () => {
    expect(salesKeys.all).toEqual(['sales']);
  });

  it('produces correct lists key', () => {
    expect(salesKeys.lists()).toEqual(['sales', 'list']);
  });

  it('produces correct list key with filters and pagination', () => {
    const filters: SalesFilters = { search: 'phoenix' };
    const key = salesKeys.list(filters, 1, 25);
    expect(key).toEqual(['sales', 'list', filters, 1, 25]);
  });

  it('produces correct analytics base key', () => {
    expect(salesKeys.analytics()).toEqual(['sales', 'analytics']);
  });

  it('produces correct timeSeries key with filters', () => {
    const filters: SalesFilters = { submarkets: ['Tempe'] };
    const key = salesKeys.timeSeries(filters);
    expect(key).toEqual(['sales', 'analytics', 'time-series', filters]);
  });

  it('produces correct submarketComparison key', () => {
    const key = salesKeys.submarketComparison(defaultFilters);
    expect(key).toEqual([
      'sales',
      'analytics',
      'submarket-comparison',
      defaultFilters,
    ]);
  });

  it('produces correct buyerActivity key', () => {
    const key = salesKeys.buyerActivity(defaultFilters);
    expect(key).toEqual([
      'sales',
      'analytics',
      'buyer-activity',
      defaultFilters,
    ]);
  });

  it('produces correct distributions key', () => {
    const key = salesKeys.distributions(defaultFilters);
    expect(key).toEqual([
      'sales',
      'analytics',
      'distributions',
      defaultFilters,
    ]);
  });

  it('produces correct dataQuality key', () => {
    expect(salesKeys.dataQuality()).toEqual(['sales', 'data-quality']);
  });

  it('produces correct importStatus key', () => {
    expect(salesKeys.importStatus()).toEqual(['sales', 'import-status']);
  });

  it('produces correct reminderStatus key', () => {
    expect(salesKeys.reminderStatus()).toEqual(['sales', 'reminder-status']);
  });
});

// ============================================================================
// Query Hooks
// ============================================================================

describe('useSalesData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useSalesData(defaultFilters, 1, 25),
      { wrapper: createWrapper() },
    );

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.error).toBeNull();
  });
});

describe('useTimeSeriesAnalytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useTimeSeriesAnalytics(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useSubmarketComparison', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useSubmarketComparison(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useBuyerActivity', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useBuyerActivity(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useDistributions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useDistributions(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useDataQuality', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => useDataQuality(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.totalRecords).toBe(0);
    expect(result.current.error).toBeNull();
  });
});

describe('useImportStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => useImportStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.unimportedFiles).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useReminderStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => useReminderStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.showReminder).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
