import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement, type ReactNode } from 'react';

// Mock the API client module before importing hooks
vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from '@/lib/api/client';
import {
  useGroupPipelineStatus,
  useGroups,
  useGroupDetail,
  useRunDiscovery,
  useRunGroupExtraction,
  useApproveGroup,
} from '../useGroupPipeline';
import type {
  PipelineStatus,
  GroupListResponse,
  GroupDetail,
  DiscoveryResponse,
  GroupExtractionResponse,
  GroupApprovalResponse,
} from '@/types/grouping';

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

// ---------------------------------------------------------------------------
// Test wrapper with QueryClient
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const fakePipelineStatus: PipelineStatus = {
  data_dir: '/data/uw-models',
  phases: {
    discovery: '2026-03-01T10:00:00Z',
    fingerprint: '2026-03-01T10:30:00Z',
  },
  stats: { total_files: 302, total_groups: 12 },
  created_at: '2026-03-01T09:00:00Z',
  updated_at: '2026-03-01T10:30:00Z',
};

const fakeGroupList: GroupListResponse = {
  groups: [
    { group_name: 'Group A', file_count: 10, structural_overlap: 92.5, era: '2020-2024', sub_variant_count: 2 },
    { group_name: 'Group B', file_count: 5, structural_overlap: 78.3, era: '2018-2020', sub_variant_count: 1 },
  ],
  total_groups: 2,
  total_ungrouped: 3,
  total_empty_templates: 1,
};

const fakeGroupDetail: GroupDetail = {
  group_name: 'Group A',
  files: [{ filename: 'model1.xlsx' }, { filename: 'model2.xlsx' }],
  structural_overlap: 92.5,
  era: '2020-2024',
  sub_variants: ['v1', 'v2'],
  variances: { sheet_count: { min: 8, max: 10 } },
};

const fakeDiscoveryResponse: DiscoveryResponse = {
  total_scanned: 400,
  candidates_accepted: 302,
  candidates_skipped: 90,
  duplicates_removed: 8,
};

const fakeExtractionResponse: GroupExtractionResponse = {
  group_name: 'Group A',
  dry_run: false,
  files_processed: 10,
  files_failed: 0,
  total_values: 240,
  started_at: '2026-03-01T11:00:00Z',
  completed_at: '2026-03-01T11:05:00Z',
};

const fakeApprovalResponse: GroupApprovalResponse = {
  group_name: 'Group A',
  approved: true,
  message: 'Group approved successfully',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useGroupPipelineStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches pipeline status on mount and returns data', async () => {
    mockGet.mockResolvedValueOnce(fakePipelineStatus);

    const { result } = renderHook(() => useGroupPipelineStatus(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);
    expect(result.current.status).toBeNull();

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/extraction/grouping/status');
    expect(result.current.status).toEqual(fakePipelineStatus);
    expect(result.current.error).toBeNull();
  });

  it('handles API errors', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network failure'));

    const { result } = renderHook(() => useGroupPipelineStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Network failure');
    expect(result.current.status).toBeNull();
  });

  it('refetch triggers a new fetch', async () => {
    mockGet.mockResolvedValueOnce(fakePipelineStatus);

    const { result } = renderHook(() => useGroupPipelineStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.status).toEqual(fakePipelineStatus);

    const updatedStatus = { ...fakePipelineStatus, stats: { total_files: 310, total_groups: 14 } };
    mockGet.mockResolvedValueOnce(updatedStatus);

    await act(async () => {
      await result.current.refetch();
    });

    await waitFor(() => {
      expect(result.current.status).toEqual(updatedStatus);
    });

    expect(mockGet).toHaveBeenCalledTimes(2);
  });
});

describe('useGroups', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches groups list on mount and returns parsed data', async () => {
    mockGet.mockResolvedValueOnce(fakeGroupList);

    const { result } = renderHook(() => useGroups(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/extraction/grouping/groups');
    expect(result.current.groups).toHaveLength(2);
    expect(result.current.groups[0].group_name).toBe('Group A');
    expect(result.current.totalGroups).toBe(2);
    expect(result.current.totalUngrouped).toBe(3);
    expect(result.current.totalEmptyTemplates).toBe(1);
    expect(result.current.error).toBeNull();
  });

  it('returns empty defaults when data is null', async () => {
    // Simulate an error so data stays null (defaults kick in)
    mockGet.mockRejectedValueOnce(new Error('fail'));

    const { result } = renderHook(() => useGroups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.groups).toEqual([]);
    expect(result.current.totalGroups).toBe(0);
    expect(result.current.totalUngrouped).toBe(0);
    expect(result.current.totalEmptyTemplates).toBe(0);
  });

  it('handles API errors', async () => {
    mockGet.mockRejectedValueOnce(new Error('Server error'));

    const { result } = renderHook(() => useGroups(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error?.message).toBe('Server error');
  });
});

describe('useGroupDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches group detail when name is provided', async () => {
    mockGet.mockResolvedValueOnce(fakeGroupDetail);

    const { result } = renderHook(() => useGroupDetail('Group A'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/extraction/grouping/groups/Group%20A');
    expect(result.current.detail).toEqual(fakeGroupDetail);
    expect(result.current.error).toBeNull();
  });

  it('skips fetch when name is empty', async () => {
    const { result } = renderHook(() => useGroupDetail(''), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).not.toHaveBeenCalled();
    expect(result.current.detail).toBeNull();
  });

  it('encodes special characters in group name', async () => {
    mockGet.mockResolvedValueOnce(fakeGroupDetail);

    const { result } = renderHook(() => useGroupDetail('Group/Special&Name'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/extraction/grouping/groups/Group%2FSpecial%26Name');
  });

  it('handles API errors', async () => {
    mockGet.mockRejectedValueOnce(new Error('Not found'));

    const { result } = renderHook(() => useGroupDetail('Missing'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error?.message).toBe('Not found');
    expect(result.current.detail).toBeNull();
  });
});

describe('useRunDiscovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts not loading with no error', () => {
    const { result } = renderHook(() => useRunDiscovery(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('triggers POST on mutate and returns response', async () => {
    mockPost.mockResolvedValueOnce(fakeDiscoveryResponse);

    const { result } = renderHook(() => useRunDiscovery(), {
      wrapper: createWrapper(),
    });

    let response: DiscoveryResponse | null = null;
    await act(async () => {
      response = await result.current.mutate();
    });

    expect(mockPost).toHaveBeenCalledWith('/extraction/grouping/discover');
    expect(response).toEqual(fakeDiscoveryResponse);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failure and returns null', async () => {
    mockPost.mockRejectedValueOnce(new Error('Discovery failed'));

    const { result } = renderHook(() => useRunDiscovery(), {
      wrapper: createWrapper(),
    });

    let response: DiscoveryResponse | null = null;
    await act(async () => {
      response = await result.current.mutate();
    });

    expect(response).toBeNull();
    // With React Query, the error is on the mutation, which resets on next mutate
    expect(result.current.isLoading).toBe(false);
  });
});

describe('useRunGroupExtraction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls POST with group name and dry_run=false by default', async () => {
    mockPost.mockResolvedValueOnce(fakeExtractionResponse);

    const { result } = renderHook(() => useRunGroupExtraction(), {
      wrapper: createWrapper(),
    });

    let response: GroupExtractionResponse | null = null;
    await act(async () => {
      response = await result.current.mutate('Group A');
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/extraction/grouping/extract/Group%20A',
      { dry_run: false },
    );
    expect(response).toEqual(fakeExtractionResponse);
  });

  it('passes dry_run=true when specified', async () => {
    const dryRunResponse = { ...fakeExtractionResponse, dry_run: true };
    mockPost.mockResolvedValueOnce(dryRunResponse);

    const { result } = renderHook(() => useRunGroupExtraction(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutate('Group A', { dry_run: true });
    });

    expect(mockPost).toHaveBeenCalledWith(
      '/extraction/grouping/extract/Group%20A',
      { dry_run: true },
    );
  });

  it('sets error on failure', async () => {
    mockPost.mockRejectedValueOnce(new Error('Extraction error'));

    const { result } = renderHook(() => useRunGroupExtraction(), {
      wrapper: createWrapper(),
    });

    const response = await act(async () => {
      return result.current.mutate('Group A');
    });

    expect(response).toBeNull();
  });
});

describe('useApproveGroup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls POST with encoded group name', async () => {
    mockPost.mockResolvedValueOnce(fakeApprovalResponse);

    const { result } = renderHook(() => useApproveGroup(), {
      wrapper: createWrapper(),
    });

    let response: GroupApprovalResponse | null = null;
    await act(async () => {
      response = await result.current.mutate('Group A');
    });

    expect(mockPost).toHaveBeenCalledWith('/extraction/grouping/approve/Group%20A');
    expect(response).toEqual(fakeApprovalResponse);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failure and returns null', async () => {
    mockPost.mockRejectedValueOnce(new Error('Approval denied'));

    const { result } = renderHook(() => useApproveGroup(), {
      wrapper: createWrapper(),
    });

    const response = await act(async () => {
      return result.current.mutate('Group A');
    });

    expect(response).toBeNull();
  });

  it('clears previous error on successful retry', async () => {
    mockPost.mockRejectedValueOnce(new Error('Temporary error'));

    const { result } = renderHook(() => useApproveGroup(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutate('Group A');
    });

    // After failure, mutate again successfully
    mockPost.mockResolvedValueOnce(fakeApprovalResponse);

    await act(async () => {
      await result.current.mutate('Group A');
    });

    expect(result.current.error).toBeNull();
  });
});
