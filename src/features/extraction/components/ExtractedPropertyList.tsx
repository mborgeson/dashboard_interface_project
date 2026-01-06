import { useState, useMemo } from 'react';
import { useExtractedProperties } from '../hooks/useExtraction';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { CompactTableSkeleton } from '@/components/skeletons';
import {
  Building2,
  Search,
  RefreshCw,
  ChevronRight,
  AlertTriangle,
  FileSpreadsheet,
  Filter,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ExtractedProperty, ExtractionFilters } from '@/types/extraction';

interface ExtractedPropertyListProps {
  runId?: string;
  onPropertyClick?: (propertyName: string) => void;
  className?: string;
}

export function ExtractedPropertyList({
  runId,
  onPropertyClick,
  className,
}: ExtractedPropertyListProps) {
  const [filters, setFilters] = useState<ExtractionFilters>({
    searchTerm: '',
    hasErrors: undefined,
  });
  const [showFilters, setShowFilters] = useState(false);

  const { properties, total, isLoading, error, refetch } = useExtractedProperties(
    runId,
    filters
  );

  // Sort properties by name
  const sortedProperties = useMemo(() => {
    return [...properties].sort((a, b) =>
      a.property_name.localeCompare(b.property_name)
    );
  }, [properties]);

  const handleSearchChange = (value: string) => {
    setFilters((prev) => ({ ...prev, searchTerm: value }));
  };

  const handleErrorFilterChange = (checked: boolean | 'indeterminate') => {
    if (checked === 'indeterminate') {
      setFilters((prev) => ({ ...prev, hasErrors: undefined }));
    } else {
      setFilters((prev) => ({ ...prev, hasErrors: checked ? true : undefined }));
    }
  };

  const clearFilters = () => {
    setFilters({ searchTerm: '', hasErrors: undefined });
  };

  const hasActiveFilters = filters.searchTerm || filters.hasErrors !== undefined;

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Properties
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="h-10 bg-neutral-100 rounded-md animate-pulse" />
          </div>
          <CompactTableSkeleton rows={6} />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Properties
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <AlertTriangle className="h-10 w-10 text-amber-500 mb-2" />
            <p className="text-sm text-neutral-600 mb-4">{error.message}</p>
            <Button variant="outline" size="sm" onClick={refetch}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Properties
            {total > 0 && (
              <Badge variant="secondary" className="ml-2">
                {total}
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className={cn(showFilters && "bg-neutral-100")}
            >
              <Filter className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={refetch}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <Input
            placeholder="Search properties..."
            value={filters.searchTerm || ''}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="mb-4 p-3 bg-neutral-50 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-neutral-700">Filters</span>
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="h-auto py-1 px-2 text-xs"
                >
                  <X className="h-3 w-3 mr-1" />
                  Clear
                </Button>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="hasErrors"
                checked={filters.hasErrors === true}
                onCheckedChange={handleErrorFilterChange}
              />
              <Label
                htmlFor="hasErrors"
                className="text-sm font-normal cursor-pointer"
              >
                Show only properties with errors
              </Label>
            </div>
          </div>
        )}

        {/* Property List */}
        {sortedProperties.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FileSpreadsheet className="h-10 w-10 text-neutral-300 mb-2" />
            <p className="text-sm text-neutral-600">
              {hasActiveFilters
                ? 'No properties match your filters'
                : 'No properties found'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {sortedProperties.map((property) => (
              <PropertyListItem
                key={property.property_name}
                property={property}
                onClick={() => onPropertyClick?.(property.property_name)}
              />
            ))}
          </div>
        )}

        {/* Results Count */}
        {sortedProperties.length > 0 && hasActiveFilters && (
          <div className="mt-4 pt-4 border-t text-sm text-neutral-500 text-center">
            Showing {sortedProperties.length} of {total} properties
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface PropertyListItemProps {
  property: ExtractedProperty;
  onClick?: () => void;
}

function PropertyListItem({ property, onClick }: PropertyListItemProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between p-3 rounded-lg border transition-colors",
        property.error_count > 0
          ? "bg-red-50/50 border-red-200 hover:bg-red-50"
          : "bg-white border-neutral-200 hover:bg-neutral-50",
        onClick && "cursor-pointer"
      )}
      onClick={onClick}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div
          className={cn(
            "flex items-center justify-center h-10 w-10 rounded-lg flex-shrink-0",
            property.error_count > 0 ? "bg-red-100" : "bg-blue-100"
          )}
        >
          <Building2
            className={cn(
              "h-5 w-5",
              property.error_count > 0 ? "text-red-600" : "text-blue-600"
            )}
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-medium text-neutral-900 truncate">
            {property.property_name}
          </div>
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <span>{property.total_fields.toLocaleString()} fields</span>
            <span className="text-neutral-300">|</span>
            <span>{property.categories.length} categories</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3 ml-3">
        {property.error_count > 0 && (
          <Badge variant="destructive" className="flex-shrink-0">
            {property.error_count} errors
          </Badge>
        )}
        <ChevronRight className="h-5 w-5 text-neutral-400 flex-shrink-0" />
      </div>
    </div>
  );
}
