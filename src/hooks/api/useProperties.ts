/**
 * React Query hooks for properties API
 * Provides data fetching with caching, loading states, and error handling
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import {
  fetchProperties,
  fetchPropertyById,
  fetchPortfolioSummary,
  type PropertyFiltersParams,
} from '@/lib/api/properties';
import { get, post, put, del } from '@/lib/api';
import { mockProperties } from '@/data/mockProperties';
import type { Property, PropertySummaryStats } from '@/types';
import type {
  PropertyFilters,
  PropertyApiResponse,
  PropertyListResponse,
  PropertyCreateInput,
  PropertyUpdateInput,
} from '@/types/api';

// Check if we should use mock data (for development/testing)
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true';

// ============================================================================
// Query Key Factory
// ============================================================================

export const propertyKeys = {
  all: ['properties'] as const,
  lists: () => [...propertyKeys.all, 'list'] as const,
  list: (filters?: PropertyFiltersParams | PropertyFilters) => [...propertyKeys.lists(), filters] as const,
  details: () => [...propertyKeys.all, 'detail'] as const,
  detail: (id: string) => [...propertyKeys.details(), id] as const,
  summary: () => [...propertyKeys.all, 'summary'] as const,
};

// ============================================================================
// Query Hooks (with mock data fallback for development)
// ============================================================================

/**
 * Hook to fetch all properties
 * Falls back to mock data if API is unavailable or USE_MOCK_DATA is true
 */
export function useProperties(filters?: PropertyFiltersParams) {
  return useQuery({
    queryKey: propertyKeys.list(filters),
    queryFn: async () => {
      if (USE_MOCK_DATA) {
        // Return mock data for development/testing
        return {
          properties: mockProperties,
          total: mockProperties.length,
        };
      }

      try {
        return await fetchProperties(filters);
      } catch (error) {
        // Fall back to mock data if API fails in development
        if (import.meta.env.DEV) {
          console.warn('API unavailable, falling back to mock data:', error);
          return {
            properties: mockProperties,
            total: mockProperties.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 10, // 10 min - property data is relatively stable, rarely changes mid-session
  });
}

/**
 * Fetch paginated list of properties with filters (API-first, no mock fallback)
 */
export function usePropertiesApi(
  filters: PropertyFilters = {},
  options?: Omit<UseQueryOptions<PropertyListResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: propertyKeys.list(filters),
    queryFn: () => get<PropertyListResponse>('/properties', filters as Record<string, unknown>),
    ...options,
  });
}

/**
 * Hook to fetch a single property by ID
 */
export function useProperty(id: string | undefined) {
  return useQuery({
    queryKey: propertyKeys.detail(id || ''),
    queryFn: async () => {
      if (!id) {
        throw new Error('Property ID is required');
      }

      if (USE_MOCK_DATA) {
        const property = mockProperties.find((p) => p.id === id);
        if (!property) {
          throw new Error('Property not found');
        }
        return property;
      }

      try {
        return await fetchPropertyById(id);
      } catch (error) {
        // Fall back to mock data if API fails in development
        if (import.meta.env.DEV) {
          console.warn('API unavailable, falling back to mock data:', error);
          const property = mockProperties.find((p) => p.id === id);
          if (!property) {
            throw new Error('Property not found');
          }
          return property;
        }
        throw error;
      }
    },
    enabled: !!id,
    staleTime: 1000 * 60 * 10, // 10 min - individual property details are stable within a session
  });
}

/**
 * Fetch a single property by ID (API-first, no mock fallback)
 */
export function usePropertyApi(
  id: string,
  options?: Omit<UseQueryOptions<PropertyApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: propertyKeys.detail(id),
    queryFn: () => get<PropertyApiResponse>(`/properties/${id}`),
    enabled: !!id,
    ...options,
  });
}

/**
 * Hook to fetch portfolio summary statistics
 */
export function usePortfolioSummary() {
  return useQuery({
    queryKey: propertyKeys.summary(),
    queryFn: async () => {
      if (USE_MOCK_DATA) {
        return calculateSummaryFromProperties(mockProperties);
      }

      try {
        return await fetchPortfolioSummary();
      } catch (error) {
        // Fall back to calculating from mock data if API fails
        if (import.meta.env.DEV) {
          console.warn('API unavailable, calculating summary from mock data:', error);
          return calculateSummaryFromProperties(mockProperties);
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 10, // 10 min - portfolio summary aggregates are stable, no need to refetch frequently
  });
}

/**
 * Fetch portfolio summary statistics (API-first)
 */
export function usePropertySummary(
  options?: Omit<UseQueryOptions<PropertySummaryStats>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: propertyKeys.summary(),
    queryFn: () => get<PropertySummaryStats>('/properties/summary'),
    ...options,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new property
 */
export function useCreateProperty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PropertyCreateInput) =>
      post<PropertyApiResponse, PropertyCreateInput>('/properties', data),
    onSuccess: () => {
      // Invalidate all property lists to refetch with new data
      queryClient.invalidateQueries({ queryKey: propertyKeys.lists() });
      queryClient.invalidateQueries({ queryKey: propertyKeys.summary() });
    },
  });
}

/**
 * Update an existing property
 */
export function useUpdateProperty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: PropertyUpdateInput) =>
      put<PropertyApiResponse, Omit<PropertyUpdateInput, 'id'>>(`/properties/${id}`, data),
    onSuccess: (data) => {
      // Update the specific property in cache
      queryClient.setQueryData(propertyKeys.detail(data.id), data);
      // Invalidate lists to ensure consistency
      queryClient.invalidateQueries({ queryKey: propertyKeys.lists() });
      queryClient.invalidateQueries({ queryKey: propertyKeys.summary() });
    },
  });
}

/**
 * Delete a property
 */
export function useDeleteProperty() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => del<void>(`/properties/${id}`),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: propertyKeys.detail(id) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: propertyKeys.lists() });
      queryClient.invalidateQueries({ queryKey: propertyKeys.summary() });
    },
  });
}

// ============================================================================
// Prefetch Utilities
// ============================================================================

/**
 * Prefetch a single property (useful for hover states or navigation)
 */
export function usePrefetchProperty() {
  const queryClient = useQueryClient();

  return (id: string) => {
    queryClient.prefetchQuery({
      queryKey: propertyKeys.detail(id),
      queryFn: () => get<PropertyApiResponse>(`/properties/${id}`),
      staleTime: 5 * 60 * 1000, // Consider fresh for 5 minutes
    });
  };
}

/**
 * Prefetch the next page of properties (for infinite scroll / pagination)
 */
export function usePrefetchNextPage() {
  const queryClient = useQueryClient();

  return (currentFilters: PropertyFilters) => {
    const nextPage = (currentFilters.page || 1) + 1;
    const nextFilters = { ...currentFilters, page: nextPage };

    queryClient.prefetchQuery({
      queryKey: propertyKeys.list(nextFilters),
      queryFn: () => get<PropertyListResponse>('/properties', nextFilters as Record<string, unknown>),
      staleTime: 5 * 60 * 1000,
    });
  };
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Calculate portfolio summary from properties array
 * Used when API summary endpoint is unavailable
 */
function calculateSummaryFromProperties(properties: Property[]): PropertySummaryStats {
  const totalProperties = properties.length;
  const totalUnits = properties.reduce((sum, p) => sum + p.propertyDetails.units, 0);
  const totalValue = properties.reduce((sum, p) => sum + p.valuation.currentValue, 0);
  const totalInvested = properties.reduce((sum, p) => sum + p.acquisition.totalInvested, 0);
  const totalNOI = properties.reduce((sum, p) => sum + p.operations.noi, 0);
  const averageOccupancy =
    properties.reduce((sum, p) => sum + p.operations.occupancy, 0) / totalProperties;
  const averageCapRate =
    properties.reduce((sum, p) => sum + p.valuation.capRate, 0) / totalProperties;

  // Calculate weighted portfolio returns
  const totalEquity = properties.reduce(
    (sum, p) => sum + (p.acquisition.totalInvested - p.financing.loanAmount),
    0
  );
  const portfolioCashOnCash =
    properties.reduce(
      (sum, p) =>
        sum +
        p.performance.cashOnCashReturn *
          (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;
  const portfolioIRR =
    properties.reduce(
      (sum, p) =>
        sum +
        p.performance.irr * (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;

  return {
    totalProperties,
    totalUnits,
    totalValue,
    totalInvested,
    totalNOI,
    averageOccupancy,
    averageCapRate,
    portfolioCashOnCash,
    portfolioIRR,
  };
}

/**
 * Selector to get just the properties array from the query result
 */
export function selectProperties(data: { properties: Property[]; total: number } | undefined) {
  return data?.properties ?? [];
}
