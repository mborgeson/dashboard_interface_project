import { useMemo } from 'react';
import type { DocumentFilters, DocumentStats, DocumentType } from '@/types/document';
import {
  useDocumentsWithMockFallback,
  useDocumentStatsWithMockFallback,
} from '@/hooks/api/useDocuments';

export function useDocuments(filters: DocumentFilters) {
  // Fetch documents from API (with mock fallback)
  const { data: docData, isLoading } = useDocumentsWithMockFallback(filters);
  const allDocuments = useMemo(() => docData?.documents ?? [], [docData]);

  // Filter documents client-side (API may not support all filter combos)
  const filteredDocuments = useMemo(() => {
    let filtered = allDocuments;

    // Apply search filter
    if (filters.searchTerm) {
      const search = filters.searchTerm.toLowerCase();
      filtered = filtered.filter(
        (doc) =>
          doc.name.toLowerCase().includes(search) ||
          doc.propertyName.toLowerCase().includes(search) ||
          doc.description?.toLowerCase().includes(search) ||
          doc.tags.some(tag => tag.toLowerCase().includes(search))
      );
    }

    // Apply document type filter
    if (filters.type !== 'all') {
      filtered = filtered.filter((doc) => doc.type === filters.type);
    }

    // Apply property filter
    if (filters.propertyId !== 'all') {
      filtered = filtered.filter((doc) => doc.propertyId === filters.propertyId);
    }

    // Apply date range filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      const cutoffDate = new Date();

      switch (filters.dateRange) {
        case '7days':
          cutoffDate.setDate(now.getDate() - 7);
          break;
        case '30days':
          cutoffDate.setDate(now.getDate() - 30);
          break;
        case '90days':
          cutoffDate.setDate(now.getDate() - 90);
          break;
        case '1year':
          cutoffDate.setFullYear(now.getFullYear() - 1);
          break;
      }

      filtered = filtered.filter((doc) => doc.uploadedAt >= cutoffDate);
    }

    return filtered;
  }, [allDocuments, filters]);

  // Fetch stats from API (with mock fallback)
  const { data: apiStats } = useDocumentStatsWithMockFallback();

  // Calculate statistics from fetched data
  const stats = useMemo((): DocumentStats => {
    if (apiStats) return apiStats;

    // Fallback: calculate from loaded documents
    const totalDocuments = allDocuments.length;
    const totalSize = allDocuments.reduce((sum, doc) => sum + doc.size, 0);

    const byType: Record<DocumentType, number> = {
      lease: 0,
      financial: 0,
      legal: 0,
      due_diligence: 0,
      photo: 0,
      other: 0,
    };

    allDocuments.forEach((doc) => {
      byType[doc.type]++;
    });

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const recentUploads = allDocuments.filter(
      (doc) => doc.uploadedAt >= thirtyDaysAgo
    ).length;

    return {
      totalDocuments,
      totalSize,
      byType,
      recentUploads,
    };
  }, [allDocuments, apiStats]);

  return {
    documents: filteredDocuments,
    stats,
    isLoading,
  };
}
