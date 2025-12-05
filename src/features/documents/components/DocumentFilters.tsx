import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search } from 'lucide-react';
import type { DocumentType } from '@/types/document';
import { mockProperties } from '@/data/mockProperties';

interface DocumentFiltersProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  documentType: DocumentType | 'all';
  onDocumentTypeChange: (value: DocumentType | 'all') => void;
  propertyId: string;
  onPropertyIdChange: (value: string) => void;
  dateRange: 'all' | '7days' | '30days' | '90days' | '1year';
  onDateRangeChange: (value: 'all' | '7days' | '30days' | '90days' | '1year') => void;
}

export function DocumentFilters({
  searchTerm,
  onSearchChange,
  documentType,
  onDocumentTypeChange,
  propertyId,
  onPropertyIdChange,
  dateRange,
  onDateRangeChange,
}: DocumentFiltersProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Search */}
      <div className="space-y-2">
        <Label htmlFor="search">Search</Label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="search"
            type="text"
            placeholder="Search documents..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Document Type */}
      <div className="space-y-2">
        <Label htmlFor="type">Document Type</Label>
        <Select value={documentType} onValueChange={onDocumentTypeChange}>
          <SelectTrigger id="type">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="lease">Lease</SelectItem>
            <SelectItem value="financial">Financial</SelectItem>
            <SelectItem value="legal">Legal</SelectItem>
            <SelectItem value="due_diligence">Due Diligence</SelectItem>
            <SelectItem value="photo">Photo</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Property */}
      <div className="space-y-2">
        <Label htmlFor="property">Property</Label>
        <Select value={propertyId} onValueChange={onPropertyIdChange}>
          <SelectTrigger id="property">
            <SelectValue placeholder="All Properties" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Properties</SelectItem>
            {mockProperties.map((property) => (
              <SelectItem key={property.id} value={property.id}>
                {property.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Date Range */}
      <div className="space-y-2">
        <Label htmlFor="date">Date Range</Label>
        <Select value={dateRange} onValueChange={onDateRangeChange}>
          <SelectTrigger id="date">
            <SelectValue placeholder="All Time" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Time</SelectItem>
            <SelectItem value="7days">Last 7 Days</SelectItem>
            <SelectItem value="30days">Last 30 Days</SelectItem>
            <SelectItem value="90days">Last 90 Days</SelectItem>
            <SelectItem value="1year">Last Year</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
