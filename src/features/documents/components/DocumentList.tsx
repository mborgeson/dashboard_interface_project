import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  ChevronDown,
  ChevronUp,
  Download,
  Trash2,
  Eye,
  FileText,
  FileSpreadsheet,
  File,
  Image,
} from 'lucide-react';
import type { Document, DocumentType } from '@/types/document';
import { format } from 'date-fns';

interface DocumentListProps {
  documents: Document[];
  onView?: (document: Document) => void;
  onDownload?: (document: Document) => void;
  onDelete?: (document: Document) => void;
}

type SortColumn = 'name' | 'type' | 'propertyName' | 'size' | 'uploadedAt' | 'uploadedBy';

// Helper to get file icon
function getFileIcon(document: Document) {
  const extension = document.name.split('.').pop()?.toLowerCase();

  if (extension === 'pdf') {
    return <FileText className="h-4 w-4 text-red-500" />;
  }
  if (['xlsx', 'xls', 'csv'].includes(extension || '')) {
    return <FileSpreadsheet className="h-4 w-4 text-green-600" />;
  }
  if (['docx', 'doc'].includes(extension || '')) {
    return <FileText className="h-4 w-4 text-blue-600" />;
  }
  if (['jpg', 'jpeg', 'png', 'gif', 'zip'].includes(extension || '')) {
    return <Image className="h-4 w-4 text-purple-500" />;
  }

  return <File className="h-4 w-4 text-gray-500" />;
}

// Helper to format file size
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
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

export function DocumentList({
  documents,
  onView,
  onDownload,
  onDelete,
}: DocumentListProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('uploadedAt');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());

  // Handle sorting
  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  // Sort documents
  const sortedDocuments = [...documents].sort((a, b) => {
    let aVal: string | number | Date;
    let bVal: string | number | Date;

    switch (sortColumn) {
      case 'name':
        aVal = a.name.toLowerCase();
        bVal = b.name.toLowerCase();
        break;
      case 'type':
        aVal = a.type;
        bVal = b.type;
        break;
      case 'propertyName':
        aVal = a.propertyName;
        bVal = b.propertyName;
        break;
      case 'size':
        aVal = a.size;
        bVal = b.size;
        break;
      case 'uploadedAt':
        aVal = a.uploadedAt.getTime();
        bVal = b.uploadedAt.getTime();
        break;
      case 'uploadedBy':
        aVal = a.uploadedBy;
        bVal = b.uploadedBy;
        break;
      default:
        return 0;
    }

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection === 'asc'
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    }

    return sortDirection === 'asc'
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number);
  });

  // Handle selection
  const handleSelectAll = () => {
    if (selectedDocs.size === documents.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(documents.map((d) => d.id)));
    }
  };

  const handleSelectDoc = (docId: string) => {
    const newSelected = new Set(selectedDocs);
    if (newSelected.has(docId)) {
      newSelected.delete(docId);
    } else {
      newSelected.add(docId);
    }
    setSelectedDocs(newSelected);
  };

  // Handle expand/collapse
  const toggleExpand = (docId: string) => {
    const newExpanded = new Set(expandedDocs);
    if (newExpanded.has(docId)) {
      newExpanded.delete(docId);
    } else {
      newExpanded.add(docId);
    }
    setExpandedDocs(newExpanded);
  };

  // Render sort icon
  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (sortColumn !== column) return null;
    return sortDirection === 'asc' ? (
      <ChevronUp className="h-4 w-4" />
    ) : (
      <ChevronDown className="h-4 w-4" />
    );
  };

  if (documents.length === 0) {
    return (
      <Card>
        <CardContent className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground">
            No documents found matching your filters.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="p-4 text-left">
                  <Checkbox
                    checked={
                      selectedDocs.size === documents.length && documents.length > 0
                    }
                    onCheckedChange={handleSelectAll}
                  />
                </th>
                <th className="p-4 text-left"></th>
                <th
                  className="p-4 text-left cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('name')}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Name</span>
                    <SortIcon column="name" />
                  </div>
                </th>
                <th
                  className="p-4 text-left cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('type')}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Type</span>
                    <SortIcon column="type" />
                  </div>
                </th>
                <th
                  className="p-4 text-left cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('propertyName')}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Property</span>
                    <SortIcon column="propertyName" />
                  </div>
                </th>
                <th
                  className="p-4 text-left cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('size')}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Size</span>
                    <SortIcon column="size" />
                  </div>
                </th>
                <th
                  className="p-4 text-left cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('uploadedAt')}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Uploaded</span>
                    <SortIcon column="uploadedAt" />
                  </div>
                </th>
                <th
                  className="p-4 text-left cursor-pointer hover:bg-muted"
                  onClick={() => handleSort('uploadedBy')}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Uploaded By</span>
                    <SortIcon column="uploadedBy" />
                  </div>
                </th>
                <th className="p-4 text-left">
                  <span className="text-sm font-medium">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedDocuments.map((doc) => (
                <>
                  <tr
                    key={doc.id}
                    className="border-b hover:bg-muted/50 cursor-pointer"
                    onClick={() => toggleExpand(doc.id)}
                  >
                    <td className="p-4" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedDocs.has(doc.id)}
                        onCheckedChange={() => handleSelectDoc(doc.id)}
                      />
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        {expandedDocs.has(doc.id) ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                        {getFileIcon(doc)}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="font-medium text-sm">{doc.name}</div>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-muted-foreground">
                        {getDocumentTypeLabel(doc.type)}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm">{doc.propertyName}</span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-muted-foreground">
                        {formatFileSize(doc.size)}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-muted-foreground">
                        {format(doc.uploadedAt, 'MMM d, yyyy')}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="text-sm text-muted-foreground">
                        {doc.uploadedBy}
                      </span>
                    </td>
                    <td className="p-4" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onView?.(doc)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onDownload?.(doc)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onDelete?.(doc)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                  {expandedDocs.has(doc.id) && (
                    <tr key={`${doc.id}-details`} className="border-b bg-muted/20">
                      <td colSpan={9} className="p-4">
                        <div className="space-y-2 text-sm">
                          {doc.description && (
                            <div>
                              <span className="font-medium">Description: </span>
                              <span className="text-muted-foreground">
                                {doc.description}
                              </span>
                            </div>
                          )}
                          {doc.tags.length > 0 && (
                            <div>
                              <span className="font-medium">Tags: </span>
                              <div className="inline-flex flex-wrap gap-1 mt-1">
                                {doc.tags.map((tag) => (
                                  <span
                                    key={tag}
                                    className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                                  >
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>

        {/* Bulk Actions Footer */}
        {selectedDocs.size > 0 && (
          <div className="flex items-center justify-between p-4 border-t bg-muted/50">
            <span className="text-sm text-muted-foreground">
              {selectedDocs.size} document{selectedDocs.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Download Selected
              </Button>
              <Button variant="outline" size="sm">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Selected
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
