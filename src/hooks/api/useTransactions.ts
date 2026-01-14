import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post, put, patch, del } from '@/lib/api';
import { USE_MOCK_DATA, IS_DEV } from '@/lib/config';
import { mockTransactions } from '@/data/mockTransactions';
import type { Transaction, TransactionType } from '@/types';

// ============================================================================
// API Types
// ============================================================================

export interface TransactionFilters {
  page?: number;
  page_size?: number;
  type?: TransactionType;
  property_id?: number;
  category?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface TransactionApiResponse {
  id: number;
  property_id: number | null;
  property_name: string;
  type: TransactionType;
  category: string | null;
  amount: number;
  date: string;
  description: string | null;
  documents: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionListResponse {
  items: TransactionApiResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface TransactionSummaryResponse {
  total_acquisitions: number;
  total_dispositions: number;
  total_capital_improvements: number;
  total_refinances: number;
  total_distributions: number;
  transaction_count: number;
  transactions_by_type: Record<string, number>;
}

export interface TransactionCreateInput {
  property_id?: number | null;
  property_name: string;
  type: TransactionType;
  category?: string | null;
  amount: number;
  date: string;
  description?: string | null;
  documents?: string[] | null;
}

export interface TransactionUpdateInput {
  id: number;
  property_id?: number | null;
  property_name?: string;
  type?: TransactionType;
  category?: string | null;
  amount?: number;
  date?: string;
  description?: string | null;
  documents?: string[] | null;
}

// ============================================================================
// Query Key Factory
// ============================================================================

export const transactionKeys = {
  all: ['transactions'] as const,
  lists: () => [...transactionKeys.all, 'list'] as const,
  list: (filters: TransactionFilters) => [...transactionKeys.lists(), filters] as const,
  details: () => [...transactionKeys.all, 'detail'] as const,
  detail: (id: string | number) => [...transactionKeys.details(), id] as const,
  byProperty: (propertyId: string | number) => [...transactionKeys.all, 'property', propertyId] as const,
  byType: (type: TransactionType) => [...transactionKeys.all, 'type', type] as const,
  summary: () => [...transactionKeys.all, 'summary'] as const,
  summaryFiltered: (filters: { property_id?: number; date_from?: string; date_to?: string }) =>
    [...transactionKeys.summary(), filters] as const,
};

// ============================================================================
// Transform Functions
// ============================================================================

/**
 * Transform API transaction response to local Transaction type
 */
function transformTransactionFromApi(apiTransaction: TransactionApiResponse): Transaction {
  return {
    id: String(apiTransaction.id),
    propertyId: apiTransaction.property_id ? String(apiTransaction.property_id) : '',
    propertyName: apiTransaction.property_name,
    type: apiTransaction.type,
    category: apiTransaction.category || undefined,
    amount: apiTransaction.amount,
    date: new Date(apiTransaction.date),
    description: apiTransaction.description || '',
    documents: apiTransaction.documents || undefined,
  };
}

// ============================================================================
// Query Hooks (with mock data fallback for development)
// ============================================================================

/**
 * Response type for transactions with fallback
 */
export interface TransactionsWithFallbackResponse {
  transactions: Transaction[];
  total: number;
}

/**
 * Hook to fetch all transactions with mock data fallback
 * Falls back to mock data if API is unavailable or USE_MOCK_DATA is true
 */
export function useTransactionsWithMockFallback(
  filters?: TransactionFilters,
  options?: Omit<UseQueryOptions<TransactionsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: transactionKeys.list(filters || {}),
    queryFn: async (): Promise<TransactionsWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        // Apply filters to mock data
        let filtered = [...mockTransactions];

        if (filters?.type) {
          filtered = filtered.filter((t) => t.type === filters.type);
        }
        if (filters?.property_id) {
          filtered = filtered.filter((t) => t.propertyId === `prop-${String(filters.property_id).padStart(3, '0')}`);
        }
        if (filters?.category) {
          filtered = filtered.filter((t) => t.category === filters.category);
        }
        if (filters?.date_from) {
          const fromDate = new Date(filters.date_from);
          filtered = filtered.filter((t) => t.date >= fromDate);
        }
        if (filters?.date_to) {
          const toDate = new Date(filters.date_to);
          filtered = filtered.filter((t) => t.date <= toDate);
        }

        // Sort
        const sortBy = filters?.sort_by || 'date';
        const sortDesc = filters?.sort_order !== 'asc';
        filtered.sort((a, b) => {
          const aVal = sortBy === 'date' ? a.date.getTime() : sortBy === 'amount' ? a.amount : 0;
          const bVal = sortBy === 'date' ? b.date.getTime() : sortBy === 'amount' ? b.amount : 0;
          return sortDesc ? bVal - aVal : aVal - bVal;
        });

        // Paginate
        const page = filters?.page || 1;
        const pageSize = filters?.page_size || 20;
        const start = (page - 1) * pageSize;
        const paginated = filtered.slice(start, start + pageSize);

        return {
          transactions: paginated,
          total: filtered.length,
        };
      }

      try {
        const response = await get<TransactionListResponse>('/transactions', filters as Record<string, unknown>);
        return {
          transactions: response.items?.map(transformTransactionFromApi) ?? [],
          total: response.total ?? 0,
        };
      } catch (error) {
        // Fall back to mock data if API fails in development
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock transactions:', error);
          return {
            transactions: mockTransactions,
            total: mockTransactions.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 7, // 7 min - transactions change more than properties but less than real-time data
    ...options,
  });
}

// ============================================================================
// Query Hooks (API-first, no mock fallback)
// ============================================================================

/**
 * Fetch paginated list of transactions with filters (API-first, no mock fallback)
 */
export function useTransactionsApi(
  filters: TransactionFilters = {},
  options?: Omit<UseQueryOptions<TransactionListResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: transactionKeys.list(filters),
    queryFn: () => get<TransactionListResponse>('/transactions', filters as Record<string, unknown>),
    ...options,
  });
}

/**
 * Fetch a single transaction by ID
 */
export function useTransaction(
  id: string | number,
  options?: Omit<UseQueryOptions<TransactionApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: transactionKeys.detail(id),
    queryFn: () => get<TransactionApiResponse>(`/transactions/${id}`),
    enabled: !!id,
    ...options,
  });
}

/**
 * Fetch transactions for a specific property
 */
export function useTransactionsByProperty(
  propertyId: string | number,
  options?: Omit<UseQueryOptions<TransactionApiResponse[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: transactionKeys.byProperty(propertyId),
    queryFn: () => get<TransactionApiResponse[]>(`/transactions/by-property/${propertyId}`),
    enabled: !!propertyId,
    ...options,
  });
}

/**
 * Fetch transactions by type
 */
export function useTransactionsByType(
  type: TransactionType,
  options?: Omit<UseQueryOptions<TransactionApiResponse[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: transactionKeys.byType(type),
    queryFn: () => get<TransactionApiResponse[]>(`/transactions/by-type/${type}`),
    enabled: !!type,
    ...options,
  });
}

/**
 * Fetch transaction summary statistics
 */
export function useTransactionSummary(
  filters?: { property_id?: number; date_from?: string; date_to?: string },
  options?: Omit<UseQueryOptions<TransactionSummaryResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: transactionKeys.summaryFiltered(filters || {}),
    queryFn: () => get<TransactionSummaryResponse>('/transactions/summary', filters as Record<string, unknown>),
    ...options,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new transaction
 */
export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TransactionCreateInput) =>
      post<TransactionApiResponse, TransactionCreateInput>('/transactions', data),
    onSuccess: (data) => {
      // Invalidate all transaction lists
      queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: transactionKeys.summary() });
      // Invalidate property-specific queries if property_id exists
      if (data.property_id) {
        queryClient.invalidateQueries({
          queryKey: transactionKeys.byProperty(data.property_id),
        });
      }
      // Invalidate type-specific queries
      queryClient.invalidateQueries({
        queryKey: transactionKeys.byType(data.type),
      });
    },
  });
}

/**
 * Update an existing transaction
 */
export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: TransactionUpdateInput) =>
      put<TransactionApiResponse, Omit<TransactionUpdateInput, 'id'>>(`/transactions/${id}`, data),
    onSuccess: (data) => {
      // Update the specific transaction in cache
      queryClient.setQueryData(transactionKeys.detail(data.id), data);
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: transactionKeys.summary() });
      if (data.property_id) {
        queryClient.invalidateQueries({
          queryKey: transactionKeys.byProperty(data.property_id),
        });
      }
    },
  });
}

/**
 * Patch (partial update) an existing transaction
 */
export function usePatchTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: Partial<TransactionUpdateInput> & { id: number }) =>
      patch<TransactionApiResponse, Partial<Omit<TransactionUpdateInput, 'id'>>>(`/transactions/${id}`, data),
    onSuccess: (data) => {
      // Update the specific transaction in cache
      queryClient.setQueryData(transactionKeys.detail(data.id), data);
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: transactionKeys.summary() });
    },
  });
}

/**
 * Delete a transaction
 */
export function useDeleteTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string | number) => del<void>(`/transactions/${id}`),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: transactionKeys.detail(id) });
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: transactionKeys.lists() });
      queryClient.invalidateQueries({ queryKey: transactionKeys.summary() });
    },
  });
}

// ============================================================================
// Prefetch Utilities
// ============================================================================

/**
 * Prefetch a single transaction
 */
export function usePrefetchTransaction() {
  const queryClient = useQueryClient();

  return (id: string | number) => {
    queryClient.prefetchQuery({
      queryKey: transactionKeys.detail(id),
      queryFn: () => get<TransactionApiResponse>(`/transactions/${id}`),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Prefetch transactions for a property
 */
export function usePrefetchPropertyTransactions() {
  const queryClient = useQueryClient();

  return (propertyId: string | number) => {
    queryClient.prefetchQuery({
      queryKey: transactionKeys.byProperty(propertyId),
      queryFn: () => get<TransactionApiResponse[]>(`/transactions/by-property/${propertyId}`),
      staleTime: 5 * 60 * 1000,
    });
  };
}
