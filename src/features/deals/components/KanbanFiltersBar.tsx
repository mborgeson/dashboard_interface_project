/**
 * KanbanFiltersBar - Filter controls for the Kanban board
 * Allows filtering by deal type and assignee
 */
import { Filter, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { KanbanFilters } from '@/hooks/api/useDeals';

interface KanbanFiltersBarProps {
  filters: KanbanFilters;
  onFiltersChange: (filters: KanbanFilters) => void;
  dealTypes: string[];
  assignees: string[];
  className?: string;
}

export function KanbanFiltersBar({
  filters,
  onFiltersChange,
  dealTypes,
  assignees,
  className,
}: KanbanFiltersBarProps) {
  const hasActiveFilters = filters.dealType || filters.assignedUserId;

  const handleDealTypeChange = (value: string) => {
    onFiltersChange({
      ...filters,
      dealType: value || undefined,
    });
  };

  const handleAssigneeChange = (value: string) => {
    onFiltersChange({
      ...filters,
      assignedUserId: value ? parseInt(value, 10) : undefined,
    });
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  return (
    <div className={cn(
      'flex items-center gap-4 px-4 py-3 border-b border-neutral-200 bg-neutral-50',
      className
    )}>
      <div className="flex items-center gap-2 text-sm text-neutral-600">
        <Filter className="w-4 h-4" />
        <span>Filters:</span>
      </div>

      {/* Deal Type Filter */}
      <select
        value={filters.dealType || ''}
        onChange={(e) => handleDealTypeChange(e.target.value)}
        className={cn(
          'px-3 py-1.5 rounded-lg border text-sm transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-blue-500',
          filters.dealType
            ? 'border-blue-300 bg-blue-50 text-blue-700'
            : 'border-neutral-200 bg-white text-neutral-700'
        )}
      >
        <option value="">All Property Types</option>
        {dealTypes.map((type) => (
          <option key={type} value={type}>
            {type}
          </option>
        ))}
      </select>

      {/* Assignee Filter */}
      <select
        value={filters.assignedUserId?.toString() || ''}
        onChange={(e) => handleAssigneeChange(e.target.value)}
        className={cn(
          'px-3 py-1.5 rounded-lg border text-sm transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-blue-500',
          filters.assignedUserId
            ? 'border-blue-300 bg-blue-50 text-blue-700'
            : 'border-neutral-200 bg-white text-neutral-700'
        )}
      >
        <option value="">All Assignees</option>
        {assignees.map((assignee, index) => (
          <option key={assignee} value={index + 1}>
            {assignee}
          </option>
        ))}
      </select>

      {/* Clear Filters */}
      {hasActiveFilters && (
        <button
          onClick={clearFilters}
          className="flex items-center gap-1 px-2 py-1 text-sm text-neutral-600 hover:text-neutral-900 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
          Clear
        </button>
      )}

      {/* Active Filter Count */}
      {hasActiveFilters && (
        <div className="ml-auto text-xs text-neutral-500">
          {[filters.dealType, filters.assignedUserId].filter(Boolean).length} filter(s) active
        </div>
      )}
    </div>
  );
}
