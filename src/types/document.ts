export type DocumentType = 'lease' | 'financial' | 'legal' | 'due_diligence' | 'photo' | 'other';

export interface Document {
  id: string;
  name: string;
  type: DocumentType;
  propertyId: string;
  propertyName: string;
  size: number; // bytes
  uploadedAt: Date;
  uploadedBy: string;
  description?: string;
  tags: string[];
  url?: string;
}

export interface DocumentFilters {
  searchTerm: string;
  type: DocumentType | 'all';
  propertyId: string | 'all';
  dateRange: 'all' | '7days' | '30days' | '90days' | '1year';
}

export interface DocumentStats {
  totalDocuments: number;
  totalSize: number;
  byType: Record<DocumentType, number>;
  recentUploads: number;
}
