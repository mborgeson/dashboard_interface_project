import { useState, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import type { ConstructionFilters, ConstructionFilterOptions } from '../types';

interface PipelineFilterPanelProps {
  filters: ConstructionFilters;
  onFiltersChange: (filters: ConstructionFilters) => void;
  filterOptions: ConstructionFilterOptions | undefined;
  isLoadingOptions: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  proposed: 'Proposed',
  final_planning: 'Final Planning',
  permitted: 'Permitted',
  under_construction: 'Under Construction',
  delivered: 'Delivered',
};

export function PipelineFilterPanel({
  filters,
  onFiltersChange,
  filterOptions,
  isLoadingOptions,
}: PipelineFilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [searchInput, setSearchInput] = useState(filters.search ?? '');

  // Local state for numeric inputs — propagate on blur
  const [localMinUnits, setLocalMinUnits] = useState(String(filters.minUnits ?? ''));
  const [localMaxUnits, setLocalMaxUnits] = useState(String(filters.maxUnits ?? ''));
  const [localMinYearBuilt, setLocalMinYearBuilt] = useState(String(filters.minYearBuilt ?? ''));
  const [localMaxYearBuilt, setLocalMaxYearBuilt] = useState(String(filters.maxYearBuilt ?? ''));

  // Sync local state from props during render
  const [prevFilters, setPrevFilters] = useState(filters);
  if (filters !== prevFilters) {
    setPrevFilters(filters);
    setSearchInput(filters.search ?? '');
    setLocalMinUnits(String(filters.minUnits ?? ''));
    setLocalMaxUnits(String(filters.maxUnits ?? ''));
    setLocalMinYearBuilt(String(filters.minYearBuilt ?? ''));
    setLocalMaxYearBuilt(String(filters.maxYearBuilt ?? ''));
  }

  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const activeFilterCount = [
    filters.search,
    filters.statuses?.length,
    filters.classifications?.length,
    filters.submarkets?.length,
    filters.cities?.length,
    filters.minUnits,
    filters.maxUnits,
    filters.minYearBuilt,
    filters.maxYearBuilt,
    filters.rentType,
  ].filter(Boolean).length;

  function handleSearchChange(value: string) {
    setSearchInput(value);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      onFiltersChange({ ...filters, search: value || undefined });
    }, 300);
  }

  function handleCheckboxToggle(
    key: 'statuses' | 'classifications' | 'submarkets' | 'cities',
    value: string,
    checked: boolean
  ) {
    const current = filters[key] ?? [];
    const next = checked
      ? [...current, value]
      : current.filter((v) => v !== value);
    onFiltersChange({ ...filters, [key]: next.length > 0 ? next : undefined });
  }

  function handleNumericBlur(
    key: 'minUnits' | 'maxUnits' | 'minYearBuilt' | 'maxYearBuilt',
    value: string
  ) {
    const num = value ? Number(value) : undefined;
    const parsed = num !== undefined && !isNaN(num) ? num : undefined;
    onFiltersChange({ ...filters, [key]: parsed });
  }

  function clearFilters() {
    onFiltersChange({});
  }

  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center justify-between mb-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}
            <span className="ml-1">{isExpanded ? '−' : '+'}</span>
          </Button>
          {activeFilterCount > 0 && (
            <Button variant="outline" size="sm" onClick={clearFilters}>
              Clear All
            </Button>
          )}
        </div>

        {isExpanded && (
          <div className="space-y-4">
            {/* Search */}
            <div>
              <Label htmlFor="cp-search">Search</Label>
              <Input
                id="cp-search"
                placeholder="Search projects, addresses, developers..."
                value={searchInput}
                onChange={(e) => handleSearchChange(e.target.value)}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {/* Pipeline Status */}
              <div>
                <Label className="mb-2 block">Pipeline Status</Label>
                {isLoadingOptions ? (
                  <p className="text-sm text-muted-foreground">Loading...</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {(filterOptions?.statuses ?? []).map((s) => (
                      <label key={s} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={(filters.statuses ?? []).includes(s)}
                          onCheckedChange={(checked) =>
                            handleCheckboxToggle('statuses', s, !!checked)
                          }
                        />
                        {STATUS_LABELS[s] ?? s}
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Classification */}
              <div>
                <Label className="mb-2 block">Classification</Label>
                {isLoadingOptions ? (
                  <p className="text-sm text-muted-foreground">Loading...</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {(filterOptions?.classifications ?? []).map((c) => (
                      <label key={c} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={(filters.classifications ?? []).includes(c)}
                          onCheckedChange={(checked) =>
                            handleCheckboxToggle('classifications', c, !!checked)
                          }
                        />
                        {c}
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Submarket */}
              <div>
                <Label className="mb-2 block">Submarket</Label>
                {isLoadingOptions ? (
                  <p className="text-sm text-muted-foreground">Loading...</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {(filterOptions?.submarkets ?? []).map((s) => (
                      <label key={s} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={(filters.submarkets ?? []).includes(s)}
                          onCheckedChange={(checked) =>
                            handleCheckboxToggle('submarkets', s, !!checked)
                          }
                        />
                        {s}
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* City */}
              <div>
                <Label className="mb-2 block">City</Label>
                {isLoadingOptions ? (
                  <p className="text-sm text-muted-foreground">Loading...</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {(filterOptions?.cities ?? []).map((c) => (
                      <label key={c} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={(filters.cities ?? []).includes(c)}
                          onCheckedChange={(checked) =>
                            handleCheckboxToggle('cities', c, !!checked)
                          }
                        />
                        {c}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Numeric ranges */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <Label htmlFor="cp-min-units">Min Units</Label>
                <Input
                  id="cp-min-units"
                  type="number"
                  value={localMinUnits}
                  onChange={(e) => setLocalMinUnits(e.target.value)}
                  onBlur={() => handleNumericBlur('minUnits', localMinUnits)}
                  placeholder="50"
                />
              </div>
              <div>
                <Label htmlFor="cp-max-units">Max Units</Label>
                <Input
                  id="cp-max-units"
                  type="number"
                  value={localMaxUnits}
                  onChange={(e) => setLocalMaxUnits(e.target.value)}
                  onBlur={() => handleNumericBlur('maxUnits', localMaxUnits)}
                  placeholder="500"
                />
              </div>
              <div>
                <Label htmlFor="cp-min-year">Min Year Built</Label>
                <Input
                  id="cp-min-year"
                  type="number"
                  value={localMinYearBuilt}
                  onChange={(e) => setLocalMinYearBuilt(e.target.value)}
                  onBlur={() => handleNumericBlur('minYearBuilt', localMinYearBuilt)}
                  placeholder="2020"
                />
              </div>
              <div>
                <Label htmlFor="cp-max-year">Max Year Built</Label>
                <Input
                  id="cp-max-year"
                  type="number"
                  value={localMaxYearBuilt}
                  onChange={(e) => setLocalMaxYearBuilt(e.target.value)}
                  onBlur={() => handleNumericBlur('maxYearBuilt', localMaxYearBuilt)}
                  placeholder="2026"
                />
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
