import { useState, useMemo } from 'react';
import { useExtractedPropertyValues } from '../hooks/useExtraction';
import { ExtractedValueGrid } from './ExtractedValueCard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Building2,
  Search,
  RefreshCw,
  ArrowLeft,
  AlertTriangle,
  Filter,
  X,
  LayoutGrid,
  List,
  ChevronDown,
  FolderOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ExtractionFilters } from '@/types/extraction';

interface ExtractedPropertyDetailProps {
  propertyName: string;
  runId?: string;
  onBack?: () => void;
  className?: string;
}

type ViewMode = 'accordion' | 'grid' | 'list';

export function ExtractedPropertyDetail({
  propertyName,
  runId,
  onBack,
  className,
}: ExtractedPropertyDetailProps) {
  const [filters, setFilters] = useState<ExtractionFilters>({
    searchTerm: '',
    category: undefined,
    hasErrors: undefined,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('accordion');
  const [expandedCategories, setExpandedCategories] = useState<string[]>([]);

  const {
    values,
    groupedValues,
    categories,
    total,
    isLoading,
    error,
    refetch,
  } = useExtractedPropertyValues(propertyName, runId, filters);

  // Stats
  const stats = useMemo(() => {
    const errorCount = values.filter((v) => v.is_error).length;
    return {
      total: values.length,
      errors: errorCount,
      success: values.length - errorCount,
    };
  }, [values]);

  const handleSearchChange = (value: string) => {
    setFilters((prev) => ({ ...prev, searchTerm: value }));
  };

  const handleCategoryChange = (value: string) => {
    setFilters((prev) => ({
      ...prev,
      category: value === 'all' ? undefined : value,
    }));
  };

  const handleErrorFilterChange = (checked: boolean | 'indeterminate') => {
    if (checked === 'indeterminate') {
      setFilters((prev) => ({ ...prev, hasErrors: undefined }));
    } else {
      setFilters((prev) => ({ ...prev, hasErrors: checked ? true : undefined }));
    }
  };

  const clearFilters = () => {
    setFilters({ searchTerm: '', category: undefined, hasErrors: undefined });
  };

  const hasActiveFilters =
    filters.searchTerm || filters.category || filters.hasErrors !== undefined;

  const toggleExpandAll = () => {
    if (expandedCategories.length === groupedValues.length) {
      setExpandedCategories([]);
    } else {
      setExpandedCategories(groupedValues.map((g) => g.category));
    }
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            {onBack && (
              <Button variant="ghost" size="sm" onClick={onBack}>
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <Skeleton className="h-6 w-48" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <div className="grid grid-cols-3 gap-4">
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
            </div>
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            {onBack && (
              <Button variant="ghost" size="sm" onClick={onBack}>
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <CardTitle className="text-lg">{propertyName}</CardTitle>
          </div>
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
          <div className="flex items-center gap-3">
            {onBack && (
              <Button variant="ghost" size="sm" onClick={onBack}>
                <ArrowLeft className="h-4 w-4" />
              </Button>
            )}
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-blue-600" />
              <CardTitle className="text-lg">{propertyName}</CardTitle>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center border rounded-lg p-1">
              <Button
                variant={viewMode === 'accordion' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('accordion')}
                className="h-8 px-2"
              >
                <FolderOpen className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className="h-8 px-2"
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
                className="h-8 px-2"
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
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
        {/* Stats Summary */}
        <div className="grid grid-cols-3 gap-4 mb-4 p-4 bg-neutral-50 rounded-lg">
          <div className="text-center">
            <div className="text-2xl font-semibold text-neutral-900">
              {stats.total.toLocaleString()}
            </div>
            <div className="text-xs text-neutral-500">Total Fields</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-semibold text-green-600">
              {stats.success.toLocaleString()}
            </div>
            <div className="text-xs text-neutral-500">Successful</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-semibold text-red-600">
              {stats.errors.toLocaleString()}
            </div>
            <div className="text-xs text-neutral-500">Errors</div>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <Input
            placeholder="Search fields..."
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-neutral-500 mb-1 block">
                  Category
                </Label>
                <Select
                  value={filters.category || 'all'}
                  onValueChange={handleCategoryChange}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="All categories" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All categories</SelectItem>
                    {categories.map((category) => (
                      <SelectItem key={category} value={category}>
                        {category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="hasErrorsDetail"
                    checked={filters.hasErrors === true}
                    onCheckedChange={handleErrorFilterChange}
                  />
                  <Label
                    htmlFor="hasErrorsDetail"
                    className="text-sm font-normal cursor-pointer"
                  >
                    Show only errors
                  </Label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Values Display */}
        {values.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FolderOpen className="h-10 w-10 text-neutral-300 mb-2" />
            <p className="text-sm text-neutral-600">
              {hasActiveFilters
                ? 'No fields match your filters'
                : 'No extracted fields found'}
            </p>
          </div>
        ) : viewMode === 'accordion' ? (
          <div>
            <div className="flex justify-end mb-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleExpandAll}
                className="text-xs"
              >
                <ChevronDown
                  className={cn(
                    "h-3 w-3 mr-1 transition-transform",
                    expandedCategories.length === groupedValues.length && "rotate-180"
                  )}
                />
                {expandedCategories.length === groupedValues.length
                  ? 'Collapse All'
                  : 'Expand All'}
              </Button>
            </div>
            <Accordion
              type="multiple"
              value={expandedCategories}
              onValueChange={setExpandedCategories}
            >
              {groupedValues.map((group) => (
                <AccordionItem key={group.category} value={group.category}>
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{group.category}</span>
                      <Badge variant="secondary" className="text-xs">
                        {group.values.length}
                      </Badge>
                      {group.errorCount > 0 && (
                        <Badge variant="destructive" className="text-xs">
                          {group.errorCount} errors
                        </Badge>
                      )}
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <ExtractedValueGrid
                      values={group.values}
                      compact
                      className="pt-2"
                    />
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        ) : viewMode === 'grid' ? (
          <ExtractedValueGrid values={values} columns={2} />
        ) : (
          <ExtractedValueGrid values={values} compact />
        )}

        {/* Results Count */}
        {values.length > 0 && hasActiveFilters && (
          <div className="mt-4 pt-4 border-t text-sm text-neutral-500 text-center">
            Showing {values.length} of {total} fields
          </div>
        )}
      </CardContent>
    </Card>
  );
}
