/**
 * KanbanColumn - Droppable column for deal stages
 * Represents a single stage in the deal pipeline
 */
import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import type { Deal, DealStage } from '@/types/deal';
import { DEAL_STAGE_LABELS } from '@/types/deal';
import { DraggableDealCard } from './DraggableDealCard';
import { cn } from '@/lib/utils';
import { Plus, Inbox } from 'lucide-react';

interface KanbanColumnProps {
  stage: DealStage;
  deals: Deal[];
  total: number;
  isOver?: boolean;
}

const STAGE_ICONS: Record<DealStage, string> = {
  lead: '🎯',
  underwriting: '📊',
  loi: '📝',
  due_diligence: '🔍',
  closing: '🤝',
  closed_won: '🏆',
  closed_lost: '❌',
};

const STAGE_BG_COLORS: Record<DealStage, string> = {
  lead: 'bg-slate-50 border-t-slate-400',
  underwriting: 'bg-blue-50 border-t-blue-400',
  loi: 'bg-purple-50 border-t-purple-400',
  due_diligence: 'bg-amber-50 border-t-amber-400',
  closing: 'bg-orange-50 border-t-orange-400',
  closed_won: 'bg-green-50 border-t-green-400',
  closed_lost: 'bg-red-50 border-t-red-400',
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function KanbanColumn({ stage, deals, total, isOver: _isOver }: KanbanColumnProps) {
  const { setNodeRef, isOver: isDragOver } = useDroppable({
    id: stage,
  });

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

  const dealIds = deals.map((deal) => deal.id);

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'flex flex-col border-r border-neutral-200 last:border-r-0 transition-colors duration-200',
        STAGE_BG_COLORS[stage],
        'border-t-4',
        isDragOver && 'bg-blue-100/50 ring-2 ring-blue-400 ring-inset'
      )}
    >
      {/* Column Header */}
      <div className="p-4 border-b border-neutral-200/50">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-lg" role="img" aria-label={stage}>
            {STAGE_ICONS[stage]}
          </span>
          <h3 className="text-sm font-semibold text-neutral-900 truncate">
            {DEAL_STAGE_LABELS[stage]}
          </h3>
        </div>
        <div className="flex items-center justify-between">
          <span className={cn(
            'inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium',
            deals.length > 0
              ? 'bg-neutral-800 text-white'
              : 'bg-neutral-200 text-neutral-500'
          )}>
            {deals.length}
          </span>
          {total > 0 && (
            <span className="text-xs font-semibold text-neutral-700">
              {formatCurrency(total)}
            </span>
          )}
        </div>
      </div>

      {/* Column Content */}
      <SortableContext items={dealIds} strategy={verticalListSortingStrategy}>
        <div className="flex-1 p-3 space-y-3 overflow-y-auto min-h-[400px] max-h-[600px]">
          {deals.length === 0 ? (
            <div className={cn(
              'flex flex-col items-center justify-center py-8 text-center',
              isDragOver ? 'opacity-50' : 'opacity-100'
            )}>
              <div className="w-12 h-12 rounded-full bg-neutral-100 flex items-center justify-center mb-3">
                <Inbox className="w-6 h-6 text-neutral-400" />
              </div>
              <p className="text-sm text-neutral-500 mb-1">No deals</p>
              <p className="text-xs text-neutral-400">
                Drag a deal here
              </p>
            </div>
          ) : (
            deals.map((deal) => (
              <DraggableDealCard key={deal.id} deal={deal} />
            ))
          )}
        </div>
      </SortableContext>

      {/* Drop Zone Indicator */}
      {isDragOver && (
        <div className="px-3 pb-3">
          <div className="h-24 border-2 border-dashed border-blue-400 rounded-lg bg-blue-50/50 flex items-center justify-center">
            <div className="flex items-center gap-2 text-blue-600 text-sm">
              <Plus className="w-4 h-4" />
              <span>Drop here</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
