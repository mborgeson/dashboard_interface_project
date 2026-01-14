/**
 * KanbanHeader - Header component for the Kanban board
 * Shows pipeline stats and view mode toggle
 */
import { LayoutGrid, List } from 'lucide-react';
import { cn } from '@/lib/utils';

interface KanbanHeaderProps {
  totalDeals: number;
  totalPipelineValue: number;
  viewMode: 'compact' | 'full';
  onViewModeChange: (mode: 'compact' | 'full') => void;
  className?: string;
}

export function KanbanHeader({
  totalDeals,
  totalPipelineValue,
  viewMode,
  onViewModeChange,
  className,
}: KanbanHeaderProps) {
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
    <div className={cn(
      'p-4 border-b border-neutral-200 bg-gradient-to-r from-blue-50 to-indigo-50',
      className
    )}>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900">Deal Pipeline</h2>
          <p className="text-sm text-neutral-600">
            {totalDeals} {totalDeals === 1 ? 'deal' : 'deals'} in pipeline • Drag and drop to update stage
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 bg-white rounded-lg border border-neutral-200 p-1">
            <button
              onClick={() => onViewModeChange('full')}
              className={cn(
                'p-2 rounded-md transition-colors',
                viewMode === 'full'
                  ? 'bg-neutral-100 text-neutral-900'
                  : 'text-neutral-500 hover:text-neutral-700'
              )}
              title="Full view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => onViewModeChange('compact')}
              className={cn(
                'p-2 rounded-md transition-colors',
                viewMode === 'compact'
                  ? 'bg-neutral-100 text-neutral-900'
                  : 'text-neutral-500 hover:text-neutral-700'
              )}
              title="Compact view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* Total Value */}
          <div className="text-right">
            <div className="text-sm text-neutral-600">Total Pipeline Value</div>
            <div className="text-2xl font-bold text-blue-600">
              {formatCurrency(totalPipelineValue)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
