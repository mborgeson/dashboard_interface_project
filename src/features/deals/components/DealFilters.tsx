import { useState } from 'react';
import type { DealStage } from '@/types/deal';
import type { DealFilterState } from '../hooks/useDeals';
import { DEAL_STAGE_LABELS } from '@/types/deal';
import { Filter, X, Search } from 'lucide-react';
import { ToggleButton } from '@/components/ui/ToggleButton';

interface DealFiltersProps {
  filters: DealFilterState;
  onUpdateFilters: (updates: Partial<DealFilterState>) => void;
  onClearFilters: () => void;
}

const ALL_STAGES: DealStage[] = [
  'dead',
  'initial_review',
  'active_review',
  'under_contract',
  'closed',
  'realized',
];

const inputClass =
  'w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent';

export function DealFilters({
  filters,
  onUpdateFilters,
  onClearFilters,
}: DealFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasActiveFilters =
    filters.stages.length > 0 ||
    filters.searchQuery.length > 0 ||
    filters.lastSalePricePerUnitRange[0] != null ||
    filters.lastSalePricePerUnitRange[1] != null ||
    filters.lastSaleDateRange[0] != null ||
    filters.lastSaleDateRange[1] != null ||
    filters.equityCommitmentRange[0] != null ||
    filters.equityCommitmentRange[1] != null;

  const toggleStage = (stage: DealStage) => {
    const newStages = filters.stages.includes(stage)
      ? filters.stages.filter((s) => s !== stage)
      : [...filters.stages, stage];
    onUpdateFilters({ stages: newStages });
  };

  const parseNumOrNull = (val: string): number | null => {
    if (!val.trim()) return null;
    const n = Number(val);
    return Number.isFinite(n) ? n : null;
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
            placeholder="Search by property, city, or submarket..."
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
                <ToggleButton
                  key={stage}
                  isActive={filters.stages.includes(stage)}
                  onClick={() => toggleStage(stage)}
                >
                  {DEAL_STAGE_LABELS[stage]}
                </ToggleButton>
              ))}
            </div>
          </div>

          {/* Last Sale Price per Unit */}
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 mb-3">
              Last Sale Price per Unit
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-neutral-500 mb-1">Min $/Unit</label>
                <input
                  type="number"
                  min={0}
                  placeholder="e.g. 100000"
                  value={filters.lastSalePricePerUnitRange[0] ?? ''}
                  onBlur={(e) =>
                    onUpdateFilters({
                      lastSalePricePerUnitRange: [
                        parseNumOrNull(e.target.value),
                        filters.lastSalePricePerUnitRange[1],
                      ],
                    })
                  }
                  onChange={(e) =>
                    onUpdateFilters({
                      lastSalePricePerUnitRange: [
                        parseNumOrNull(e.target.value),
                        filters.lastSalePricePerUnitRange[1],
                      ],
                    })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-500 mb-1">Max $/Unit</label>
                <input
                  type="number"
                  min={0}
                  placeholder="e.g. 300000"
                  value={filters.lastSalePricePerUnitRange[1] ?? ''}
                  onBlur={(e) =>
                    onUpdateFilters({
                      lastSalePricePerUnitRange: [
                        filters.lastSalePricePerUnitRange[0],
                        parseNumOrNull(e.target.value),
                      ],
                    })
                  }
                  onChange={(e) =>
                    onUpdateFilters({
                      lastSalePricePerUnitRange: [
                        filters.lastSalePricePerUnitRange[0],
                        parseNumOrNull(e.target.value),
                      ],
                    })
                  }
                  className={inputClass}
                />
              </div>
            </div>
          </div>

          {/* Last Sale Date */}
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 mb-3">
              Last Sale Date
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-neutral-500 mb-1">From Year</label>
                <input
                  type="number"
                  min={1980}
                  max={2030}
                  placeholder="e.g. 2018"
                  value={filters.lastSaleDateRange[0] ?? ''}
                  onBlur={(e) =>
                    onUpdateFilters({
                      lastSaleDateRange: [
                        parseNumOrNull(e.target.value),
                        filters.lastSaleDateRange[1],
                      ],
                    })
                  }
                  onChange={(e) =>
                    onUpdateFilters({
                      lastSaleDateRange: [
                        parseNumOrNull(e.target.value),
                        filters.lastSaleDateRange[1],
                      ],
                    })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-500 mb-1">To Year</label>
                <input
                  type="number"
                  min={1980}
                  max={2030}
                  placeholder="e.g. 2025"
                  value={filters.lastSaleDateRange[1] ?? ''}
                  onBlur={(e) =>
                    onUpdateFilters({
                      lastSaleDateRange: [
                        filters.lastSaleDateRange[0],
                        parseNumOrNull(e.target.value),
                      ],
                    })
                  }
                  onChange={(e) =>
                    onUpdateFilters({
                      lastSaleDateRange: [
                        filters.lastSaleDateRange[0],
                        parseNumOrNull(e.target.value),
                      ],
                    })
                  }
                  className={inputClass}
                />
              </div>
            </div>
          </div>

          {/* Equity Commitment Range */}
          <div>
            <h4 className="text-sm font-semibold text-neutral-900 mb-3">
              Equity Commitment Range
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-neutral-500 mb-1">Min Equity</label>
                <input
                  type="number"
                  min={0}
                  placeholder="e.g. 1000000"
                  value={filters.equityCommitmentRange[0] ?? ''}
                  onBlur={(e) =>
                    onUpdateFilters({
                      equityCommitmentRange: [
                        parseNumOrNull(e.target.value),
                        filters.equityCommitmentRange[1],
                      ],
                    })
                  }
                  onChange={(e) =>
                    onUpdateFilters({
                      equityCommitmentRange: [
                        parseNumOrNull(e.target.value),
                        filters.equityCommitmentRange[1],
                      ],
                    })
                  }
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-500 mb-1">Max Equity</label>
                <input
                  type="number"
                  min={0}
                  placeholder="e.g. 20000000"
                  value={filters.equityCommitmentRange[1] ?? ''}
                  onBlur={(e) =>
                    onUpdateFilters({
                      equityCommitmentRange: [
                        filters.equityCommitmentRange[0],
                        parseNumOrNull(e.target.value),
                      ],
                    })
                  }
                  onChange={(e) =>
                    onUpdateFilters({
                      equityCommitmentRange: [
                        filters.equityCommitmentRange[0],
                        parseNumOrNull(e.target.value),
                      ],
                    })
                  }
                  className={inputClass}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
