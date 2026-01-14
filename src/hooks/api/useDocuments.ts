import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { get, post, put, del } from '@/lib/api';
import { USE_MOCK_DATA, IS_DEV } from '@/lib/config';
import { mockDocuments } from '@/data/mockDocuments';
import type { Document, DocumentType, DocumentStats, DocumentFilters } from '@/types/document';

// ============================================================================
// API Types
// ============================================================================

export interface DocumentApiResponse {
  id: number;
  name: string;
  type: string;
  property_id?: string | null;
  propertyId?: string | null;
  property_name?: string | null;
  propertyName?: string | null;
  size: number;
  mime_type?: string | null;
  uploaded_at: string;
  uploadedAt?: string;
  uploaded_by?: string | null;
  uploadedBy?: string | null;
  description?: string | null;
  tags?: string[] | null;
  url?: string | null;
  file_path?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListApiResponse {
  items: DocumentApiResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentStatsApiResponse {
  total_documents: number;
  total_size: number;
  by_type: Record<string, number>;
  recent_uploads: number;
}

export interface DocumentCreateInput {
  name: string;
  type: DocumentType;
  property_id?: string;
  property_name?: string;
  size?: number;
  mime_type?: string;
  uploaded_by?: string;
  description?: string;
  tags?: string[];
  url?: string;
}

export interface DocumentUpdateInput {
  id: string | number;
  name?: string;
  type?: DocumentType;
  property_id?: string;
  property_name?: string;
  description?: string;
  tags?: string[];
  url?: string;
}

// ============================================================================
// Query Key Factory
// ============================================================================

export const documentKeys = {
  all: ['documents'] as const,
  lists: () => [...documentKeys.all, 'list'] as const,
  list: (filters: Partial<DocumentFilters>) => [...documentKeys.lists(), filters] as const,
  details: () => [...documentKeys.all, 'detail'] as const,
  detail: (id: string) => [...documentKeys.details(), id] as const,
  byProperty: (propertyId: string) => [...documentKeys.all, 'property', propertyId] as const,
  stats: () => [...documentKeys.all, 'stats'] as const,
};

// ============================================================================
// Transform Functions
// ============================================================================

/**
 * Transform API document response to local Document type
 */
function transformDocumentFromApi(apiDoc: DocumentApiResponse): Document {
  return {
    id: String(apiDoc.id),
    name: apiDoc.name,
    type: apiDoc.type as DocumentType,
    propertyId: apiDoc.property_id || apiDoc.propertyId || '',
    propertyName: apiDoc.property_name || apiDoc.propertyName || '',
    size: apiDoc.size,
    uploadedAt: new Date(apiDoc.uploaded_at || apiDoc.uploadedAt || Date.now()),
    uploadedBy: apiDoc.uploaded_by || apiDoc.uploadedBy || '',
    description: apiDoc.description || undefined,
    tags: apiDoc.tags || [],
    url: apiDoc.url || undefined,
  };
}

/**
 * Transform API stats response to local DocumentStats type
 */
function transformStatsFromApi(apiStats: DocumentStatsApiResponse): DocumentStats {
  return {
    totalDocuments: apiStats.total_documents,
    totalSize: apiStats.total_size,
    byType: apiStats.by_type as Record<DocumentType, number>,
    recentUploads: apiStats.recent_uploads,
  };
}

// ============================================================================
// Query Hooks (with mock data fallback)
// ============================================================================

/**
 * Response type for documents with fallback
 */
export interface DocumentsWithFallbackResponse {
  documents: Document[];
  total: number;
}

/**
 * Hook to fetch all documents with mock data fallback
 * Falls back to mock data if API is unavailable or USE_MOCK_DATA is true
 */
export function useDocumentsWithMockFallback(
  filters?: Partial<DocumentFilters>,
  options?: Omit<UseQueryOptions<DocumentsWithFallbackResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: documentKeys.list(filters || {}),
    queryFn: async (): Promise<DocumentsWithFallbackResponse> => {
      if (USE_MOCK_DATA) {
        // Apply client-side filtering to mock data
        let filtered = [...mockDocuments];

        if (filters?.type && filters.type !== 'all') {
          filtered = filtered.filter((d) => d.type === filters.type);
        }
        if (filters?.propertyId && filters.propertyId !== 'all') {
          filtered = filtered.filter((d) => d.propertyId === filters.propertyId);
        }
        if (filters?.searchTerm) {
          const term = filters.searchTerm.toLowerCase();
          filtered = filtered.filter(
            (d) =>
              d.name.toLowerCase().includes(term) ||
              d.description?.toLowerCase().includes(term)
          );
        }
        if (filters?.dateRange && filters.dateRange !== 'all') {
          const now = new Date();
          let cutoff: Date;
          switch (filters.dateRange) {
            case '7days':
              cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
              break;
            case '30days':
              cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
              break;
            case '90days':
              cutoff = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
              break;
            case '1year':
              cutoff = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
              break;
            default:
              cutoff = new Date(0);
          }
          filtered = filtered.filter((d) => d.uploadedAt >= cutoff);
        }

        return {
          documents: filtered,
          total: filtered.length,
        };
      }

      try {
        const params: Record<string, unknown> = {};
        if (filters?.type && filters.type !== 'all') params.type = filters.type;
        if (filters?.propertyId && filters.propertyId !== 'all')
          params.property_id = filters.propertyId;
        if (filters?.searchTerm) params.search = filters.searchTerm;
        if (filters?.dateRange && filters.dateRange !== 'all')
          params.date_range = filters.dateRange;

        const response = await get<DocumentListApiResponse>('/documents', params);
        return {
          documents: response.items?.map(transformDocumentFromApi) ?? [],
          total: response.total ?? 0,
        };
      } catch (error) {
        // Fall back to mock data if API fails in development
        if (IS_DEV) {
          console.warn('API unavailable, falling back to mock documents:', error);
          return {
            documents: mockDocuments,
            total: mockDocuments.length,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

/**
 * Hook to fetch document statistics with mock data fallback
 */
export function useDocumentStatsWithMockFallback(
  options?: Omit<UseQueryOptions<DocumentStats>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: documentKeys.stats(),
    queryFn: async (): Promise<DocumentStats> => {
      if (USE_MOCK_DATA) {
        // Calculate stats from mock data
        const byType: Record<DocumentType, number> = {
          lease: 0,
          financial: 0,
          legal: 0,
          due_diligence: 0,
          photo: 0,
          other: 0,
        };

        let totalSize = 0;
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        let recentUploads = 0;

        for (const doc of mockDocuments) {
          byType[doc.type]++;
          totalSize += doc.size;
          if (doc.uploadedAt >= thirtyDaysAgo) {
            recentUploads++;
          }
        }

        return {
          totalDocuments: mockDocuments.length,
          totalSize,
          byType,
          recentUploads,
        };
      }

      try {
        const response = await get<DocumentStatsApiResponse>('/documents/stats');
        return transformStatsFromApi(response);
      } catch (error) {
        if (IS_DEV) {
          console.warn('API unavailable, calculating stats from mock data:', error);
          // Return mock stats (same calculation as above)
          const byType: Record<DocumentType, number> = {
            lease: 0,
            financial: 0,
            legal: 0,
            due_diligence: 0,
            photo: 0,
            other: 0,
          };
          let totalSize = 0;
          const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
          let recentUploads = 0;

          for (const doc of mockDocuments) {
            byType[doc.type]++;
            totalSize += doc.size;
            if (doc.uploadedAt >= thirtyDaysAgo) {
              recentUploads++;
            }
          }

          return {
            totalDocuments: mockDocuments.length,
            totalSize,
            byType,
            recentUploads,
          };
        }
        throw error;
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    ...options,
  });
}

// ============================================================================
// Query Hooks (API-first, no mock fallback)
// ============================================================================

/**
 * Fetch paginated list of documents with filters (API-first, no mock fallback)
 */
export function useDocumentsApi(
  filters: Partial<DocumentFilters> = {},
  options?: Omit<UseQueryOptions<DocumentListApiResponse>, 'queryKey' | 'queryFn'>
) {
  const params: Record<string, unknown> = {};
  if (filters.type && filters.type !== 'all') params.type = filters.type;
  if (filters.propertyId && filters.propertyId !== 'all')
    params.property_id = filters.propertyId;
  if (filters.searchTerm) params.search = filters.searchTerm;
  if (filters.dateRange && filters.dateRange !== 'all')
    params.date_range = filters.dateRange;

  return useQuery({
    queryKey: documentKeys.list(filters),
    queryFn: () => get<DocumentListApiResponse>('/documents', params),
    ...options,
  });
}

/**
 * Fetch a single document by ID
 */
export function useDocument(
  id: string,
  options?: Omit<UseQueryOptions<DocumentApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: documentKeys.detail(id),
    queryFn: () => get<DocumentApiResponse>(`/documents/${id}`),
    enabled: !!id,
    ...options,
  });
}

/**
 * Fetch documents for a specific property
 */
export function useDocumentsByProperty(
  propertyId: string,
  options?: Omit<UseQueryOptions<DocumentListApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: documentKeys.byProperty(propertyId),
    queryFn: () => get<DocumentListApiResponse>(`/documents/property/${propertyId}`),
    enabled: !!propertyId,
    ...options,
  });
}

/**
 * Fetch document statistics (API-first)
 */
export function useDocumentStats(
  options?: Omit<UseQueryOptions<DocumentStatsApiResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: documentKeys.stats(),
    queryFn: () => get<DocumentStatsApiResponse>('/documents/stats'),
    ...options,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Create a new document metadata entry
 */
export function useCreateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: DocumentCreateInput) =>
      post<DocumentApiResponse, DocumentCreateInput>('/documents', data),
    onSuccess: () => {
      // Invalidate all document lists and stats
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: documentKeys.stats() });
    },
  });
}

/**
 * Update an existing document
 */
export function useUpdateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, ...data }: DocumentUpdateInput) =>
      put<DocumentApiResponse, Omit<DocumentUpdateInput, 'id'>>(`/documents/${id}`, data),
    onSuccess: (data) => {
      // Update the specific document in cache
      queryClient.setQueryData(documentKeys.detail(String(data.id)), data);
      // Invalidate lists for consistency
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
    },
  });
}

/**
 * Delete a document
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => del<void>(`/documents/${id}`),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: documentKeys.detail(id) });
      // Invalidate lists and stats
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: documentKeys.stats() });
    },
  });
}

// ============================================================================
// Prefetch Utilities
// ============================================================================

/**
 * Prefetch a single document
 */
export function usePrefetchDocument() {
  const queryClient = useQueryClient();

  return (id: string) => {
    queryClient.prefetchQuery({
      queryKey: documentKeys.detail(id),
      queryFn: () => get<DocumentApiResponse>(`/documents/${id}`),
      staleTime: 5 * 60 * 1000,
    });
  };
}

/**
 * Prefetch documents for a specific property
 */
export function usePrefetchPropertyDocuments() {
  const queryClient = useQueryClient();

  return (propertyId: string) => {
    queryClient.prefetchQuery({
      queryKey: documentKeys.byProperty(propertyId),
      queryFn: () => get<DocumentListApiResponse>(`/documents/property/${propertyId}`),
      staleTime: 5 * 60 * 1000,
    });
  };
}
