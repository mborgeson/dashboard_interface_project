import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  constructionKeys,
  useProjects,
  useConstructionFilterOptions,
  usePipelineSummary,
  usePipelineFunnel,
  usePermitTrends,
  useEmploymentOverlay,
  useSubmarketPipeline,
  useClassificationBreakdown,
  useConstructionDataQuality,
  useConstructionImportStatus,
} from '../useConstructionData';
import type { ConstructionFilters } from '../../types';

// Mock the entire construction API module
vi.mock('@/lib/api/construction', () => ({
  fetchProjects: vi.fn().mockResolvedValue({
    data: [],
    total: 0,
    page: 1,
    pageSize: 50,
    totalPages: 0,
  }),
  fetchConstructionFilterOptions: vi.fn().mockResolvedValue({
    submarkets: [],
    cities: [],
    statuses: [],
    classifications: [],
    rentTypes: [],
  }),
  fetchPipelineSummary: vi.fn().mockResolvedValue([]),
  fetchPipelineFunnel: vi.fn().mockResolvedValue([]),
  fetchPermitTrends: vi.fn().mockResolvedValue([]),
  fetchEmploymentOverlay: vi.fn().mockResolvedValue([]),
  fetchSubmarketPipeline: vi.fn().mockResolvedValue([]),
  fetchClassificationBreakdown: vi.fn().mockResolvedValue([]),
  fetchConstructionDataQuality: vi.fn().mockResolvedValue({
    totalProjects: 0,
    projectsBySource: {},
    sourceLogs: [],
    nullRates: {},
    permitDataCount: 0,
    employmentDataCount: 0,
  }),
  fetchConstructionImportStatus: vi.fn().mockResolvedValue({
    unimportedFiles: [],
    lastImportedFile: null,
    lastImportDate: null,
    totalProjects: 0,
  }),
  triggerConstructionImport: vi.fn().mockResolvedValue({
    success: true,
    message: 'ok',
  }),
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

const defaultFilters: ConstructionFilters = {};

// ============================================================================
// Query Key Factory
// ============================================================================

describe('constructionKeys', () => {
  it('produces correct base key', () => {
    expect(constructionKeys.all).toEqual(['construction']);
  });

  it('produces correct lists key', () => {
    expect(constructionKeys.lists()).toEqual(['construction', 'list']);
  });

  it('produces correct list key with filters and pagination', () => {
    const filters: ConstructionFilters = { search: 'mesa' };
    const key = constructionKeys.list(filters, 1, 50);
    expect(key).toEqual(['construction', 'list', filters, 1, 50]);
  });

  it('produces correct analytics base key', () => {
    expect(constructionKeys.analytics()).toEqual([
      'construction',
      'analytics',
    ]);
  });

  it('produces correct pipelineSummary key with filters', () => {
    const filters: ConstructionFilters = { statuses: ['proposed'] };
    const key = constructionKeys.pipelineSummary(filters);
    expect(key).toEqual([
      'construction',
      'analytics',
      'pipeline-summary',
      filters,
    ]);
  });

  it('produces correct pipelineFunnel key', () => {
    const key = constructionKeys.pipelineFunnel(defaultFilters);
    expect(key).toEqual([
      'construction',
      'analytics',
      'pipeline-funnel',
      defaultFilters,
    ]);
  });

  it('produces correct permitTrends key with source', () => {
    const key = constructionKeys.permitTrends('census_bps');
    expect(key).toEqual([
      'construction',
      'analytics',
      'permit-trends',
      'census_bps',
    ]);
  });

  it('produces correct employmentOverlay key', () => {
    expect(constructionKeys.employmentOverlay()).toEqual([
      'construction',
      'analytics',
      'employment-overlay',
    ]);
  });

  it('produces correct submarketPipeline key', () => {
    const key = constructionKeys.submarketPipeline(defaultFilters);
    expect(key).toEqual([
      'construction',
      'analytics',
      'submarket-pipeline',
      defaultFilters,
    ]);
  });

  it('produces correct classificationBreakdown key', () => {
    const key = constructionKeys.classificationBreakdown(defaultFilters);
    expect(key).toEqual([
      'construction',
      'analytics',
      'classification-breakdown',
      defaultFilters,
    ]);
  });

  it('produces correct dataQuality key', () => {
    expect(constructionKeys.dataQuality()).toEqual([
      'construction',
      'data-quality',
    ]);
  });

  it('produces correct importStatus key', () => {
    expect(constructionKeys.importStatus()).toEqual([
      'construction',
      'import-status',
    ]);
  });

  it('produces correct filterOptions key', () => {
    expect(constructionKeys.filterOptions()).toEqual([
      'construction',
      'filter-options',
    ]);
  });
});

// ============================================================================
// Query Hooks
// ============================================================================

describe('useProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useProjects(defaultFilters, 1, 50),
      { wrapper: createWrapper() },
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.error).toBeNull();
  });
});

describe('useConstructionFilterOptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => useConstructionFilterOptions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.submarkets).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('usePipelineSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => usePipelineSummary(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('usePipelineFunnel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => usePipelineFunnel(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('usePermitTrends', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => usePermitTrends(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useEmploymentOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => useEmploymentOverlay(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useSubmarketPipeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useSubmarketPipeline(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useClassificationBreakdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(
      () => useClassificationBreakdown(defaultFilters),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('useConstructionDataQuality', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => useConstructionDataQuality(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeDefined();
    expect(result.current.data?.totalProjects).toBe(0);
    expect(result.current.error).toBeNull();
  });
});

describe('useConstructionImportStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns expected query properties', async () => {
    const { result } = renderHook(() => useConstructionImportStatus(), {
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
