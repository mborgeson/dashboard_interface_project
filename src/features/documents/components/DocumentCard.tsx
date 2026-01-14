import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  FileText,
  Download,
  Trash2,
  Eye,
  Image,
  FileSpreadsheet,
  File,
} from 'lucide-react';
import type { Document, DocumentType } from '@/types/document';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

interface DocumentCardProps {
  document: Document;
  onView?: (document: Document) => void;
  onDownload?: (document: Document) => void;
  onDelete?: (document: Document) => void;
}

// Helper to get file icon based on type and name
function getFileIcon(document: Document) {
  // Check file extension
  const extension = document.name.split('.').pop()?.toLowerCase();

  if (extension === 'pdf') {
    return <FileText className="h-8 w-8 text-red-500" />;
  }
  if (['xlsx', 'xls', 'csv'].includes(extension || '')) {
    return <FileSpreadsheet className="h-8 w-8 text-green-600" />;
  }
  if (['docx', 'doc'].includes(extension || '')) {
    return <FileText className="h-8 w-8 text-blue-600" />;
  }
  if (['jpg', 'jpeg', 'png', 'gif', 'zip'].includes(extension || '')) {
    return <Image className="h-8 w-8 text-purple-500" />;
  }

  return <File className="h-8 w-8 text-gray-500" />;
}

// Helper to format file size
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Helper to get document type label
function getDocumentTypeLabel(type: DocumentType): string {
  const labels: Record<DocumentType, string> = {
    lease: 'Lease',
    financial: 'Financial',
    legal: 'Legal',
    due_diligence: 'Due Diligence',
    photo: 'Photo',
    other: 'Other',
  };
  return labels[type];
}

// Helper to get type badge color
function getTypeBadgeColor(type: DocumentType): string {
  const colors: Record<DocumentType, string> = {
    lease: 'bg-blue-100 text-blue-800',
    financial: 'bg-green-100 text-green-800',
    legal: 'bg-purple-100 text-purple-800',
    due_diligence: 'bg-orange-100 text-orange-800',
    photo: 'bg-pink-100 text-pink-800',
    other: 'bg-gray-100 text-gray-800',
  };
  return colors[type];
}

export function DocumentCard({
  document,
  onView,
  onDownload,
  onDelete,
}: DocumentCardProps) {
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardContent className="p-4">
        <div className="flex flex-col gap-3">
          {/* Icon and Type Badge */}
          <div className="flex items-start justify-between">
            <div className="flex-shrink-0">{getFileIcon(document)}</div>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeBadgeColor(
                document.type
              )}`}
            >
              {getDocumentTypeLabel(document.type)}
            </span>
          </div>

          {/* File Name */}
          <div>
            <h3 className="font-semibold text-sm line-clamp-2 mb-1">
              {document.name}
            </h3>
            {document.description && (
              <p className="text-xs text-muted-foreground line-clamp-2">
                {document.description}
              </p>
            )}
          </div>

          {/* Property */}
          <div className="text-xs text-muted-foreground">
            <span className="font-medium">Property:</span> {document.propertyName}
          </div>

          {/* Metadata */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{formatFileSize(document.size)}</span>
            <span>{dayjs(document.uploadedAt).fromNow()}</span>
          </div>

          {/* Uploader */}
          <div className="text-xs text-muted-foreground">
            Uploaded by {document.uploadedBy}
          </div>

          {/* Tags */}
          {document.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {document.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                >
                  {tag}
                </span>
              ))}
              {document.tags.length > 3 && (
                <span className="px-2 py-0.5 text-gray-600 text-xs">
                  +{document.tags.length - 3}
                </span>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => onView?.(document)}
            >
              <Eye className="h-3 w-3 mr-1" />
              View
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDownload?.(document)}
            >
              <Download className="h-3 w-3" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDelete?.(document)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
