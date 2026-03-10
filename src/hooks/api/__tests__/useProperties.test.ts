import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { type ReactNode } from 'react';

// Mock the API modules
vi.mock('@/lib/api', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}));

vi.mock('@/lib/api/properties', () => ({
  fetchProperties: vi.fn(),
  fetchPropertyById: vi.fn(),
  fetchPortfolioSummary: vi.fn(),
}));

import { get, post, put, del } from '@/lib/api';
import { fetchProperties, fetchPropertyById, fetchPortfolioSummary } from '@/lib/api/properties';
import {
  propertyKeys,
  useProperties,
  usePropertiesApi,
  useProperty,
  usePropertyApi,
  usePortfolioSummary,
  usePropertySummary,
  useCreateProperty,
  useUpdateProperty,
  useDeleteProperty,
  selectProperties,
} from '../useProperties';

const mockGet = vi.mocked(get);
const mockPost = vi.mocked(post);
const mockPut = vi.mocked(put);
const mockDel = vi.mocked(del);
const mockFetchProperties = vi.mocked(fetchProperties);
const mockFetchPropertyById = vi.mocked(fetchPropertyById);
const mockFetchPortfolioSummary = vi.mocked(fetchPortfolioSummary);

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
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const fakeProperty = {
  id: '1',
  name: 'Sunset Apartments',
  address: {
    street: '123 Main St',
    city: 'Phoenix',
    state: 'AZ',
    zip: '85001',
    latitude: 33.45,
    longitude: -112.07,
    submarket: 'Central Phoenix',
  },
  propertyDetails: {
    units: 200,
    squareFeet: 180000,
    averageUnitSize: 900,
    yearBuilt: 1985,
    propertyClass: 'B' as const,
    assetType: 'Garden',
    amenities: ['Pool', 'Fitness Center'],
  },
  acquisition: { date: new Date(), purchasePrice: 0, pricePerUnit: 0, closingCosts: 0, acquisitionFee: 0, totalInvested: 0, landAndAcquisitionCosts: 0, hardCosts: 0, softCosts: 0, lenderClosingCosts: 0, equityClosingCosts: 0, totalAcquisitionBudget: 0 },
  financing: { loanAmount: 0, loanToValue: 0, interestRate: 0, loanTerm: 0, amortization: 0, monthlyPayment: 0, lender: null, originationDate: new Date(), maturityDate: null },
  valuation: { currentValue: 0, lastAppraisalDate: new Date(), capRate: 0, appreciationSinceAcquisition: 0 },
  operations: { occupancy: 0, averageRent: 0, rentPerSqft: 0, monthlyRevenue: 0, otherIncome: 0, expenses: { realEstateTaxes: 0, otherExpenses: 0, propertyInsurance: 0, staffingPayroll: 0, propertyManagementFee: 0, repairsAndMaintenance: 0, turnover: 0, contractServices: 0, reservesForReplacement: 0, adminLegalSecurity: 0, advertisingLeasingMarketing: 0, total: 0 }, noi: 0, operatingExpenseRatio: 0, grossPotentialRevenue: 0, netRentalIncome: 0, otherIncomeAnnual: 0, vacancyLoss: 0, concessions: 0 },
  operationsByYear: [],
  performance: { leveredIrr: 0, leveredMoic: 0, unleveredIrr: null, unleveredMoic: null, totalEquityCommitment: 0, totalCashFlowsToEquity: 0, netCashFlowsToEquity: 0, holdPeriodYears: 0, exitCapRate: 0, totalBasisPerUnitClose: 0, seniorLoanBasisPerUnitClose: 0, totalBasisPerUnitExit: null, seniorLoanBasisPerUnitExit: null },
  images: { main: '', gallery: [] },
} satisfies import('@/types/property').Property;

const fakePropertiesResponse = {
  properties: [fakeProperty],
  total: 1,
};

const fakeSummaryStats = {
  totalProperties: 42,
  totalUnits: 8500,
  totalValue: 1250000000,
  averageCapRate: 5.2,
  averageOccupancy: 94.5,
};

// ---------------------------------------------------------------------------
// Query Key Factory Tests
// ---------------------------------------------------------------------------

describe('propertyKeys', () => {
  it('generates correct base key', () => {
    expect(propertyKeys.all).toEqual(['properties']);
  });

  it('generates lists key', () => {
    expect(propertyKeys.lists()).toEqual(['properties', 'list']);
  });

  it('generates list key with filters', () => {
    const filters = { submarket: 'Tempe' };
    expect(propertyKeys.list(filters)).toEqual(['properties', 'list', filters]);
  });

  it('generates list key without filters', () => {
    expect(propertyKeys.list()).toEqual(['properties', 'list', undefined]);
  });

  it('generates detail key', () => {
    expect(propertyKeys.detail('42')).toEqual(['properties', 'detail', '42']);
  });

  it('generates summary key', () => {
    expect(propertyKeys.summary()).toEqual(['properties', 'summary']);
  });
});

// ---------------------------------------------------------------------------
// Query Hooks
// ---------------------------------------------------------------------------

describe('useProperties', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches properties via fetchProperties', async () => {
    mockFetchProperties.mockResolvedValueOnce(fakePropertiesResponse);

    const { result } = renderHook(() => useProperties(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockFetchProperties).toHaveBeenCalledWith(undefined);
    expect(result.current.data).toEqual(fakePropertiesResponse);
  });

  it('passes filters to fetchProperties', async () => {
    mockFetchProperties.mockResolvedValueOnce({ properties: [], total: 0 });

    const filters = { submarket: 'Tempe', min_units: 100 };

    const { result } = renderHook(() => useProperties(filters), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockFetchProperties).toHaveBeenCalledWith(filters);
  });

  it('handles API errors', async () => {
    mockFetchProperties.mockRejectedValueOnce(new Error('Server error'));

    const { result } = renderHook(() => useProperties(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect((result.current.error as Error).message).toBe('Server error');
  });
});

describe('usePropertiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches properties via get with filters', async () => {
    mockGet.mockResolvedValueOnce({ items: [], total: 0 });

    const filters = { page: 2, pageSize: 25 };

    const { result } = renderHook(() => usePropertiesApi(filters), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/properties', filters);
  });

  it('uses empty filters by default', async () => {
    mockGet.mockResolvedValueOnce({ items: [], total: 0 });

    const { result } = renderHook(() => usePropertiesApi(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/properties', {});
  });
});

describe('useProperty', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches a single property by ID', async () => {
    mockFetchPropertyById.mockResolvedValueOnce(fakeProperty as never);

    const { result } = renderHook(() => useProperty('1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockFetchPropertyById).toHaveBeenCalledWith('1');
    expect(result.current.data).toEqual(fakeProperty);
  });

  it('is disabled when id is undefined', async () => {
    const { result } = renderHook(() => useProperty(undefined), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle');
    });

    expect(mockFetchPropertyById).not.toHaveBeenCalled();
  });

  it('handles API errors', async () => {
    mockFetchPropertyById.mockRejectedValueOnce(new Error('Not found'));

    const { result } = renderHook(() => useProperty('999'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeInstanceOf(Error);
  });
});

describe('usePropertyApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches property via get endpoint', async () => {
    mockGet.mockResolvedValueOnce({ id: '5', name: 'Test Prop' });

    const { result } = renderHook(() => usePropertyApi('5'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/properties/5');
  });

  it('is disabled when id is empty', async () => {
    const { result } = renderHook(() => usePropertyApi(''), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.fetchStatus).toBe('idle');
    });

    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe('usePortfolioSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches portfolio summary stats', async () => {
    mockFetchPortfolioSummary.mockResolvedValueOnce(fakeSummaryStats as never);

    const { result } = renderHook(() => usePortfolioSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockFetchPortfolioSummary).toHaveBeenCalled();
    expect(result.current.data).toEqual(fakeSummaryStats);
  });

  it('handles API errors', async () => {
    mockFetchPortfolioSummary.mockRejectedValueOnce(new Error('Server error'));

    const { result } = renderHook(() => usePortfolioSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeInstanceOf(Error);
  });
});

describe('usePropertySummary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches summary via get endpoint', async () => {
    mockGet.mockResolvedValueOnce(fakeSummaryStats);

    const { result } = renderHook(() => usePropertySummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockGet).toHaveBeenCalledWith('/properties/summary');
    expect(result.current.data).toEqual(fakeSummaryStats);
  });
});

// ---------------------------------------------------------------------------
// Mutation Hooks
// ---------------------------------------------------------------------------

describe('useCreateProperty', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts new property data', async () => {
    const newProp = { id: '10', name: 'New Property' };
    mockPost.mockResolvedValueOnce(newProp);

    const { result } = renderHook(() => useCreateProperty(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ name: 'New Property' } as never);
    });

    expect(mockPost).toHaveBeenCalledWith('/properties', expect.objectContaining({ name: 'New Property' }));
  });

  it('handles creation errors', async () => {
    mockPost.mockRejectedValueOnce(new Error('Validation error'));

    const { result } = renderHook(() => useCreateProperty(), {
      wrapper: createWrapper(),
    });

    await expect(
      act(async () => {
        await result.current.mutateAsync({ name: 'Bad' } as never);
      }),
    ).rejects.toThrow('Validation error');
  });
});

describe('useUpdateProperty', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends PUT with property data', async () => {
    const updated = { id: '5', name: 'Updated Property' };
    mockPut.mockResolvedValueOnce(updated);

    const { result } = renderHook(() => useUpdateProperty(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ id: '5', name: 'Updated Property' } as never);
    });

    expect(mockPut).toHaveBeenCalledWith('/properties/5', expect.objectContaining({ name: 'Updated Property' }));
  });
});

describe('useDeleteProperty', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends DELETE request', async () => {
    mockDel.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeleteProperty(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync('42');
    });

    expect(mockDel).toHaveBeenCalledWith('/properties/42');
  });

  it('handles deletion errors', async () => {
    mockDel.mockRejectedValueOnce(new Error('Forbidden'));

    const { result } = renderHook(() => useDeleteProperty(), {
      wrapper: createWrapper(),
    });

    await expect(
      act(async () => {
        await result.current.mutateAsync('42');
      }),
    ).rejects.toThrow('Forbidden');
  });
});

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

describe('selectProperties', () => {
  it('extracts properties array from response', () => {
    const data = { properties: [fakeProperty], total: 1 };
    expect(selectProperties(data as never)).toEqual([fakeProperty]);
  });

  it('returns empty array when data is undefined', () => {
    expect(selectProperties(undefined)).toEqual([]);
  });

  it('returns empty array when properties is empty', () => {
    expect(selectProperties({ properties: [], total: 0 } as never)).toEqual([]);
  });
});
