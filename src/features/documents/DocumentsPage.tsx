import { useState, useCallback, lazy, Suspense } from 'react';
import { Grid3x3, List, Upload, HardDrive } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DocumentFilters } from './components/DocumentFilters';
import { DocumentGrid } from './components/DocumentGrid';
import { DocumentList } from './components/DocumentList';
import { useDocuments } from './hooks/useDocuments';
import { useDeleteDocument } from '@/hooks/api/useDocuments';
import { useToast } from '@/hooks/useToast';
import type { Document, DocumentType } from '@/types/document';
import { EmptyDocuments } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

// Lazy load DocumentUploadModal for code splitting
const DocumentUploadModal = lazy(() =>
  import('./components/DocumentUploadModal').then(m => ({ default: m.DocumentUploadModal }))
);

type ViewMode = 'grid' | 'list';

export function DocumentsPage() {
  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const { info, success: showSuccess, error: showError } = useToast();
  const deleteDocumentMutation = useDeleteDocument();

  // Delete confirmation state
  const [pendingDelete, setPendingDelete] = useState<Document | null>(null);

  // Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType | 'all'>('all');
  const [propertyId, setPropertyId] = useState<string>('all');
  const [dateRange, setDateRange] = useState<'all' | '7days' | '30days' | '90days' | '1year'>('all');

  // Get filtered documents and stats from API
  const { documents, stats, isLoading, error } = useDocuments({
    searchTerm,
    type: documentType,
    propertyId,
    dateRange,
  });

  // Document action handlers
  const handleView = (document: Document) => {
    if (document.url) {
      window.open(document.url, '_blank');
    } else {
      info('Document preview not available');
    }
  };

  const handleDownload = (_document: Document) => {
    info(`Download not yet implemented`);
  };

  const handleDelete = useCallback((document: Document) => {
    setPendingDelete(document);
  }, []);

  const confirmDelete = useCallback(() => {
    if (!pendingDelete) return;
    const doc = pendingDelete;
    setPendingDelete(null);
    deleteDocumentMutation.mutate(doc.id, {
      onSuccess: () => {
        showSuccess(`Deleted "${doc.name}"`);
      },
      onError: (err) => {
        showError(
          `Failed to delete "${doc.name}"`,
          { description: err instanceof Error ? err.message : 'An unexpected error occurred' }
        );
      },
    });
  }, [pendingDelete, deleteDocumentMutation, showSuccess, showError]);

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  // Show error state
  if (error) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
            <p className="text-muted-foreground">
              Manage property documents, leases, and financial records
            </p>
          </div>
        </div>
        <ErrorState
          title="Failed to load documents"
          description={error instanceof Error ? error.message : 'An unexpected error occurred while loading documents.'}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  // Show loading state
  if (isLoading) {
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
        </div>

        {/* Summary Stats Skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="h-4 w-32 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 bg-muted animate-pulse rounded mb-2" />
                <div className="h-3 w-24 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Filters Skeleton */}
        <Card>
          <CardContent className="pt-6">
            <div className="h-10 w-full bg-muted animate-pulse rounded" />
          </CardContent>
        </Card>

        {/* Grid Skeleton */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="h-12 w-12 bg-muted animate-pulse rounded-lg mb-4" />
                <div className="h-4 w-3/4 bg-muted animate-pulse rounded mb-2" />
                <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

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
        {documents.length === 0 ? (
          <EmptyDocuments />
        ) : viewMode === 'grid' ? (
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

      {/* Upload Modal - Lazy loaded */}
      {uploadModalOpen && (
        <Suspense fallback={null}>
          <DocumentUploadModal
            open={uploadModalOpen}
            onClose={() => setUploadModalOpen(false)}
          />
        </Suspense>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => { if (!open) setPendingDelete(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Document</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &ldquo;{pendingDelete?.name}&rdquo;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-red-600 hover:bg-red-700">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
