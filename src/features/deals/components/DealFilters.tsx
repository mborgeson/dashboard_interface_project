import { useState } from 'react';
import type { DealStage } from '@/types/deal';
import type { DealFilters as DealFiltersType } from '../hooks/useDeals';
import { DEAL_STAGE_LABELS } from '@/types/deal';
import { Filter, X, Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DealFiltersProps {
  filters: DealFiltersType;
  onUpdateFilters: (updates: Partial<DealFiltersType>) => void;
  onClearFilters: () => void;
  propertyTypes: string[];
  assignees: string[];
}

const ALL_STAGES: DealStage[] = [
  'lead',
  'underwriting',
  'loi',
  'due_diligence',
  'closing',
  'closed_won',
  'closed_lost',
];

export function DealFilters({
  filters,
  onUpdateFilters,
  onClearFilters,
  propertyTypes,
  assignees,
}: DealFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasActiveFilters =
    filters.stages.length > 0 ||
    filters.propertyTypes.length > 0 ||
    filters.assignees.length > 0 ||
    filters.searchQuery.length > 0;

  const toggleStage = (stage: DealStage) => {
    const newStages = filters.stages.includes(stage)
      ? filters.stages.filter((s) => s !== stage)
      : [...filters.stages, stage];
    onUpdateFilters({ stages: newStages });
  };

  const togglePropertyType = (type: string) => {
    const newTypes = filters.propertyTypes.includes(type)
      ? filters.propertyTypes.filter((t) => t !== type)
      : [...filters.propertyTypes, type];
    onUpdateFilters({ propertyTypes: newTypes });
  };

  const toggleAssignee = (assignee: string) => {
    const newAssignees = filters.assignees.includes(assignee)
      ? filters.assignees.filter((a) => a !== assignee)
      : [...filters.assignees, assignee];
    onUpdateFilters({ assignees: newAssignees });
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(value);
  };

  return (
    <div className="bg-white rounded-lg border border-neutral-200 shadow-card">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-200">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-neutral-600" />
          <h3 className="font-semibold text-neutral-900">Filters</h3>
          {hasActiveFilters && (
            <span className="px-2 py-0.5 bg-accent-100 text-accent-700 text-xs font-medium rounded-full">
              Active
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="text-sm text-neutral-600 hover:text-neutral-900 transition-colors"
            >
              Clear All
            </button>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-accent-600 hover:text-accent-700 font-medium transition-colors"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-neutral-200">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search by property, city, or assignee..."
            value={filters.searchQuery}
            onChange={(e) => onUpdateFilters({ searchQuery: e.target.value })}
            className="w-full pl-9 pr-4 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent"
          />
          {filters.searchQuery && (
            <button
              onClick={() => onUpdateFilters({ searchQuery: '' })}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Filter Options */}
      {isExpanded && (
        <div className="p-4 space-y-6">
          {/* Stage Filter */}
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 mb-3">
              Deal Stage
            </h4>
            <div className="flex flex-wrap gap-2">
              {ALL_STAGES.map((stage) => (
                <button
                  key={stage}
                  onClick={() => toggleStage(stage)}
                  className={cn(
                    'px-3 py-1.5 rounded-md text-sm font-medium border transition-colors',
                    filters.stages.includes(stage)
                      ? 'bg-accent-500 text-white border-accent-500'
                      : 'bg-white text-neutral-700 border-neutral-300 hover:border-accent-500'
                  )}
                >
                  {DEAL_STAGE_LABELS[stage]}
                </button>
              ))}
            </div>
          </div>

          {/* Property Type Filter */}
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 mb-3">
              Property Type
            </h4>
            <div className="flex flex-wrap gap-2">
              {propertyTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => togglePropertyType(type)}
                  className={cn(
                    'px-3 py-1.5 rounded-md text-sm font-medium border transition-colors',
                    filters.propertyTypes.includes(type)
                      ? 'bg-accent-500 text-white border-accent-500'
                      : 'bg-white text-neutral-700 border-neutral-300 hover:border-accent-500'
                  )}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Assignee Filter */}
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 mb-3">
              Assignee
            </h4>
            <div className="flex flex-wrap gap-2">
              {assignees.map((assignee) => (
                <button
                  key={assignee}
                  onClick={() => toggleAssignee(assignee)}
                  className={cn(
                    'px-3 py-1.5 rounded-md text-sm font-medium border transition-colors',
                    filters.assignees.includes(assignee)
                      ? 'bg-accent-500 text-white border-accent-500'
                      : 'bg-white text-neutral-700 border-neutral-300 hover:border-accent-500'
                  )}
                >
                  {assignee}
                </button>
              ))}
            </div>
          </div>

          {/* Value Range */}
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 mb-3">
              Deal Value Range
            </h4>
            <div className="space-y-2">
              <input
                type="range"
                min="0"
                max="100000000"
                step="1000000"
                value={filters.valueRange[1]}
                onChange={(e) =>
                  onUpdateFilters({
                    valueRange: [filters.valueRange[0], Number(e.target.value)],
                  })
                }
                className="w-full"
              />
              <div className="flex items-center justify-between text-sm text-neutral-600">
                <span>{formatCurrency(filters.valueRange[0])}</span>
                <span>{formatCurrency(filters.valueRange[1])}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
