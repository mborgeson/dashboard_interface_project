import type { Document } from '@/types/document';
import { DocumentCard } from './DocumentCard';

interface DocumentGridProps {
  documents: Document[];
  onView?: (document: Document) => void;
  onDownload?: (document: Document) => void;
  onDelete?: (document: Document) => void;
}

export function DocumentGrid({
  documents,
  onView,
  onDownload,
  onDelete,
}: DocumentGridProps) {
  if (documents.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        No documents found matching your filters.
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {documents.map((document) => (
        <DocumentCard
          key={document.id}
          document={document}
          onView={onView}
          onDownload={onDownload}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
