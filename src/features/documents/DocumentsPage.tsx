import { useState } from 'react';
import { Grid3x3, List, Upload, HardDrive } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DocumentFilters } from './components/DocumentFilters';
import { DocumentGrid } from './components/DocumentGrid';
import { DocumentList } from './components/DocumentList';
import { DocumentUploadModal } from './components/DocumentUploadModal';
import { useDocuments } from './hooks/useDocuments';
import type { Document, DocumentType } from '@/types/document';

type ViewMode = 'grid' | 'list';

export function DocumentsPage() {
  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType | 'all'>('all');
  const [propertyId, setPropertyId] = useState<string>('all');
  const [dateRange, setDateRange] = useState<'all' | '7days' | '30days' | '90days' | '1year'>('all');

  // Get filtered documents and stats
  const { documents, stats } = useDocuments({
    searchTerm,
    type: documentType,
    propertyId,
    dateRange,
  });

  // Mock handlers
  const handleView = (document: Document) => {
    console.log('View document:', document);
    alert(`Viewing: ${document.name}`);
  };

  const handleDownload = (document: Document) => {
    console.log('Download document:', document);
    alert(`Downloading: ${document.name}`);
  };

  const handleDelete = (document: Document) => {
    console.log('Delete document:', document);
    if (confirm(`Are you sure you want to delete "${document.name}"?`)) {
      alert('Document deleted (mock)');
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground">
            Manage property documents, leases, and financial records
          </p>
        </div>
        <Button onClick={() => setUploadModalOpen(true)}>
          <Upload className="h-4 w-4 mr-2" />
          Upload Documents
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalDocuments}</div>
            <p className="text-xs text-muted-foreground">
              Across all properties
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Storage</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatFileSize(stats.totalSize)}</div>
            <p className="text-xs text-muted-foreground">
              Used storage space
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">By Category</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Lease</span>
                <span className="font-medium">{stats.byType.lease}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Financial</span>
                <span className="font-medium">{stats.byType.financial}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Legal</span>
                <span className="font-medium">{stats.byType.legal}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recent Uploads</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.recentUploads}</div>
            <p className="text-xs text-muted-foreground">
              Last 30 days
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and View Toggle */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                All Documents ({documents.length})
              </h2>
              <div className="flex gap-2">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid3x3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <DocumentFilters
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              documentType={documentType}
              onDocumentTypeChange={setDocumentType}
              propertyId={propertyId}
              onPropertyIdChange={setPropertyId}
              dateRange={dateRange}
              onDateRangeChange={setDateRange}
            />
          </div>
        </CardContent>
      </Card>

      {/* Documents Display */}
      <div>
        {viewMode === 'grid' ? (
          <DocumentGrid
            documents={documents}
            onView={handleView}
            onDownload={handleDownload}
            onDelete={handleDelete}
          />
        ) : (
          <DocumentList
            documents={documents}
            onView={handleView}
            onDownload={handleDownload}
            onDelete={handleDelete}
          />
        )}
      </div>

      {/* Upload Modal */}
      <DocumentUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
      />
    </div>
  );
}
