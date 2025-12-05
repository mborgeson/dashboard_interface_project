import { useMemo } from 'react';
import type { Document, DocumentFilters, DocumentStats, DocumentType } from '@/types/document';
import { mockDocuments } from '@/data/mockDocuments';

export function useDocuments(filters: DocumentFilters) {
  // Filter documents based on criteria
  const filteredDocuments = useMemo(() => {
    let filtered = mockDocuments;

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
  }, [filters]);

  // Calculate statistics
  const stats = useMemo((): DocumentStats => {
    const totalDocuments = mockDocuments.length;
    const totalSize = mockDocuments.reduce((sum, doc) => sum + doc.size, 0);

    const byType: Record<DocumentType, number> = {
      lease: 0,
      financial: 0,
      legal: 0,
      due_diligence: 0,
      photo: 0,
      other: 0,
    };

    mockDocuments.forEach((doc) => {
      byType[doc.type]++;
    });

    // Count documents uploaded in last 30 days
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const recentUploads = mockDocuments.filter(
      (doc) => doc.uploadedAt >= thirtyDaysAgo
    ).length;

    return {
      totalDocuments,
      totalSize,
      byType,
      recentUploads,
    };
  }, []);

  return {
    documents: filteredDocuments,
    stats,
  };
}
