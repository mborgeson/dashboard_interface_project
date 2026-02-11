import { useState, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import type { SalesFilters, FilterOptions } from '../types';

interface SalesFilterPanelProps {
  filters: SalesFilters;
  onFiltersChange: (filters: SalesFilters) => void;
  filterOptions: FilterOptions | undefined;
  isLoadingOptions: boolean;
}

export function SalesFilterPanel({
  filters,
  onFiltersChange,
  filterOptions,
  isLoadingOptions,
}: SalesFilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [searchInput, setSearchInput] = useState(filters.search ?? '');

  // Local state for numeric/date inputs — propagate on blur to avoid focus loss
  const [localMinUnits, setLocalMinUnits] = useState(String(filters.minUnits ?? ''));
  const [localMaxUnits, setLocalMaxUnits] = useState(String(filters.maxUnits ?? ''));
  const [localMinPrice, setLocalMinPrice] = useState(String(filters.minPrice ?? ''));
  const [localMaxPrice, setLocalMaxPrice] = useState(String(filters.maxPrice ?? ''));
  const [localMinPPU, setLocalMinPPU] = useState(String(filters.minPricePerUnit ?? ''));
  const [localMaxPPU, setLocalMaxPPU] = useState(String(filters.maxPricePerUnit ?? ''));
  const [localDateFrom, setLocalDateFrom] = useState(filters.dateFrom ?? '');
  const [localDateTo, setLocalDateTo] = useState(filters.dateTo ?? '');

  // Sync local state from props during render (React-recommended pattern
  // for adjusting state when props change — no useEffect needed)
  const [prevFilters, setPrevFilters] = useState(filters);
  if (filters !== prevFilters) {
    setPrevFilters(filters);
    setSearchInput(filters.search ?? '');
    setLocalMinUnits(String(filters.minUnits ?? ''));
    setLocalMaxUnits(String(filters.maxUnits ?? ''));
    setLocalMinPrice(String(filters.minPrice ?? ''));
    setLocalMaxPrice(String(filters.maxPrice ?? ''));
    setLocalMinPPU(String(filters.minPricePerUnit ?? ''));
    setLocalMaxPPU(String(filters.maxPricePerUnit ?? ''));
    setLocalDateFrom(filters.dateFrom ?? '');
    setLocalDateTo(filters.dateTo ?? '');
  }

  // Timer ref for search debounce — only accessed inside event handlers, never during render
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const activeFilterCount = [
    filters.search,
    filters.submarkets?.length,
    filters.minUnits,
    filters.maxUnits,
    filters.minPrice,
    filters.maxPrice,
    filters.minPricePerUnit,
    filters.maxPricePerUnit,
    filters.dateFrom,
    filters.dateTo,
  ].filter(Boolean).length;

  // Event handlers — plain functions closing over current filters (no useCallback needed
  // since these are passed to native DOM elements, not memoized children)

  function handleSearchChange(value: string) {
    setSearchInput(value);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      const trimmed = value.trim() || undefined;
      if (trimmed !== filters.search) {
        onFiltersChange({ ...filters, search: trimmed });
      }
    }, 300);
  }

  function clearFilters() {
    onFiltersChange({});
  }

  function toggleSubmarket(submarket: string, checked: boolean) {
    const current = filters.submarkets ?? [];
    const updated = checked
      ? [...current, submarket]
      : current.filter((s) => s !== submarket);
    onFiltersChange({
      ...filters,
      submarkets: updated.length > 0 ? updated : undefined,
    });
  }

  function commitNumeric(key: keyof SalesFilters, localValue: string) {
    const num = localValue === '' ? undefined : Number(localValue);
    if (num !== filters[key]) {
      onFiltersChange({ ...filters, [key]: num });
    }
  }

  function commitDate(key: 'dateFrom' | 'dateTo', localValue: string) {
    const val = localValue || undefined;
    if (val !== filters[key]) {
      onFiltersChange({ ...filters, [key]: val });
    }
  }

  return (
    <Card>
      <CardContent className="pt-6">
        {/* Header row */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm font-medium hover:text-foreground transition-colors"
          >
            <span className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
              ▶
            </span>
            Filters
            {activeFilterCount > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-blue-600 rounded-full">
                {activeFilterCount}
              </span>
            )}
          </button>
          <div className="flex gap-2">
            {activeFilterCount > 0 && (
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear Filters
              </Button>
            )}
          </div>
        </div>

        {/* Filter fields */}
        {isExpanded && (
          <div className="space-y-4">
            {/* Search */}
            <div>
              <Label htmlFor="sales-search" className="text-xs font-medium text-muted-foreground mb-1 block">
                Search
              </Label>
              <Input
                id="sales-search"
                placeholder="Property name, address, buyer, seller..."
                value={searchInput}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="h-9"
              />
            </div>

            {/* Grid of range filters + date range */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {/* Unit Count Range */}
              <div>
                <Label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Unit Count
                </Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    placeholder="Min"
                    value={localMinUnits}
                    onChange={(e) => setLocalMinUnits(e.target.value)}
                    onBlur={() => commitNumeric('minUnits', localMinUnits)}
                    className="h-9"
                  />
                  <Input
                    type="number"
                    placeholder="Max"
                    value={localMaxUnits}
                    onChange={(e) => setLocalMaxUnits(e.target.value)}
                    onBlur={() => commitNumeric('maxUnits', localMaxUnits)}
                    className="h-9"
                  />
                </div>
              </div>

              {/* Sale Price Range */}
              <div>
                <Label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Sale Price ($)
                </Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    placeholder="Min"
                    value={localMinPrice}
                    onChange={(e) => setLocalMinPrice(e.target.value)}
                    onBlur={() => commitNumeric('minPrice', localMinPrice)}
                    className="h-9"
                  />
                  <Input
                    type="number"
                    placeholder="Max"
                    value={localMaxPrice}
                    onChange={(e) => setLocalMaxPrice(e.target.value)}
                    onBlur={() => commitNumeric('maxPrice', localMaxPrice)}
                    className="h-9"
                  />
                </div>
              </div>

              {/* Price Per Unit Range */}
              <div>
                <Label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Price Per Unit ($)
                </Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    placeholder="Min"
                    value={localMinPPU}
                    onChange={(e) => setLocalMinPPU(e.target.value)}
                    onBlur={() => commitNumeric('minPricePerUnit', localMinPPU)}
                    className="h-9"
                  />
                  <Input
                    type="number"
                    placeholder="Max"
                    value={localMaxPPU}
                    onChange={(e) => setLocalMaxPPU(e.target.value)}
                    onBlur={() => commitNumeric('maxPricePerUnit', localMaxPPU)}
                    className="h-9"
                  />
                </div>
              </div>

              {/* Date Range */}
              <div>
                <Label className="text-xs font-medium text-muted-foreground mb-1 block">
                  Sale Date
                </Label>
                <div className="flex gap-2">
                  <Input
                    type="date"
                    value={localDateFrom}
                    onChange={(e) => {
                      setLocalDateFrom(e.target.value);
                      commitDate('dateFrom', e.target.value);
                    }}
                    className="h-9"
                  />
                  <Input
                    type="date"
                    value={localDateTo}
                    onChange={(e) => {
                      setLocalDateTo(e.target.value);
                      commitDate('dateTo', e.target.value);
                    }}
                    className="h-9"
                  />
                </div>
              </div>
            </div>

            {/* Submarkets */}
            <div>
              <Label className="text-xs font-medium text-muted-foreground mb-2 block">
                Submarkets
              </Label>
              {isLoadingOptions ? (
                <p className="text-xs text-muted-foreground">Loading submarkets...</p>
              ) : (
                <div className="flex flex-wrap gap-x-4 gap-y-2">
                  {(filterOptions?.submarkets ?? []).map((sub) => (
                    <label
                      key={sub}
                      className="flex items-center gap-1.5 text-sm cursor-pointer"
                    >
                      <Checkbox
                        checked={filters.submarkets?.includes(sub) ?? false}
                        onCheckedChange={(checked) =>
                          toggleSubmarket(sub, checked === true)
                        }
                      />
                      {sub}
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
