/**
 * KanbanBoardWidget - Self-fetching Kanban board with hook integration
 * Wraps the existing KanbanBoard with data fetching, filters, and loading states
 */
import { useState, useCallback, useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragStartEvent, DragEndEvent } from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { ErrorState } from '@/components/ui/error-state';
import { useKanbanBoardWithMockFallback, useUpdateDealStage } from '@/hooks/api/useDeals';
import type { KanbanFilters } from '@/hooks/api/useDeals';
import type { Deal, DealStage } from '@/types/deal';
import type { DealStageApi } from '@/types/api';
import { KanbanColumn } from './KanbanColumn';
import { DealCard } from './DealCard';
import { KanbanHeader } from './KanbanHeader';
import { KanbanFiltersBar } from './KanbanFiltersBar';
import { KanbanSkeleton } from './KanbanSkeleton';
import { useToast } from '@/hooks/useToast';
import { cn } from '@/lib/utils';

interface KanbanBoardWidgetProps {
  className?: string;
  showFilters?: boolean;
  showHeader?: boolean;
  viewMode?: 'compact' | 'full';
  /** Callback when a deal card is clicked (reserved for deal details modal) */
  onDealClick?: (dealId: string) => void;
}

const PIPELINE_STAGES: DealStageApi[] = [
  'lead',
  'underwriting',
  'loi',
  'due_diligence',
  'closing',
  'closed_won',
];

function isValidTransition(from: DealStage): boolean {
  if (from === 'closed_won' || from === 'closed_lost') {
    return false;
  }
  return true;
}

export function KanbanBoardWidget({
  className,
  showFilters = true,
  showHeader = true,
  viewMode: initialViewMode = 'full',
}: KanbanBoardWidgetProps) {
  const [filters, setFilters] = useState<KanbanFilters>({});
  const [viewMode, setViewMode] = useState<'compact' | 'full'>(initialViewMode);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeDeal, setActiveDeal] = useState<Deal | null>(null);

  const { data, isLoading, error, refetch } = useKanbanBoardWithMockFallback(filters);
  const updateStageMutation = useUpdateDealStage();
  const { success, error: showError } = useToast();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Extract unique deal types and assignees for filter options
  const stages = data?.stages;
  const filterOptions = useMemo(() => {
    if (!stages) return { dealTypes: [], assignees: [] };

    const dealTypes = new Set<string>();
    const assignees = new Set<string>();

    Object.values(stages).forEach(({ deals }) => {
      deals.forEach(deal => {
        if (deal.propertyType) dealTypes.add(deal.propertyType);
        if (deal.assignee) assignees.add(deal.assignee);
      });
    });

    return {
      dealTypes: Array.from(dealTypes).sort(),
      assignees: Array.from(assignees).sort(),
    };
  }, [stages]);

  const findDealById = useCallback((id: string): Deal | null => {
    if (!stages) return null;
    for (const stage of Object.keys(stages) as DealStageApi[]) {
      const deal = stages[stage].deals.find((d) => d.id === id);
      if (deal) return deal;
    }
    return null;
  }, [stages]);

  const findStageByDealId = useCallback((id: string): DealStageApi | null => {
    if (!stages) return null;
    for (const stage of Object.keys(stages) as DealStageApi[]) {
      const deal = stages[stage].deals.find((d) => d.id === id);
      if (deal) return stage;
    }
    return null;
  }, [stages]);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const { active } = event;
    const deal = findDealById(active.id as string);
    setActiveId(active.id as string);
    setActiveDeal(deal);
  }, [findDealById]);

  const handleDragOver = useCallback(() => {
    // Preview handled by KanbanColumn visual highlighting
  }, []);

  const formatStageName = (stage: DealStageApi) => {
    return stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;

    setActiveId(null);
    setActiveDeal(null);

    if (!over) return;

    const dealId = active.id as string;
    const oldStage = findStageByDealId(dealId);

    // Determine the new stage
    let newStage: DealStageApi;

    if ([...PIPELINE_STAGES, 'closed_lost'].includes(over.id as DealStageApi)) {
      newStage = over.id as DealStageApi;
    } else {
      const overStage = findStageByDealId(over.id as string);
      if (!overStage) return;
      newStage = overStage;
    }

    if (oldStage && oldStage !== newStage) {
      if (isValidTransition(oldStage as DealStage)) {
        updateStageMutation.mutate(
          { id: dealId, stage: newStage },
          {
            onSuccess: () => {
              success(`Deal moved to ${formatStageName(newStage)}`);
              // Refetch to get fresh data
              refetch();
            },
            onError: () => {
              showError('Failed to update deal stage');
            },
          }
        );
      } else {
        showError('Cannot move deals from closed stages');
      }
    }
  }, [findStageByDealId, updateStageMutation, success, showError, refetch]);

  const handleDragCancel = useCallback(() => {
    setActiveId(null);
    setActiveDeal(null);
  }, []);

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

  const getTotalPipelineValue = useCallback(() => {
    if (!stages) return 0;
    return PIPELINE_STAGES.filter(s => s !== 'closed_won')
      .reduce((sum, stage) => sum + (stages[stage]?.totalValue || 0), 0);
  }, [stages]);

  if (isLoading) {
    return <KanbanSkeleton className={className} />;
  }

  if (error || !data) {
    return (
      <div className={className}>
        <ErrorState
          title="Failed to load deal pipeline"
          description="Unable to fetch deal data. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const closedLostDeals = data.stages.closed_lost?.deals || [];

  return (
    <div className={cn('bg-white rounded-lg border border-neutral-200 shadow-card', className)}>
      {/* Header */}
      {showHeader && (
        <KanbanHeader
          totalDeals={data.totalDeals}
          totalPipelineValue={getTotalPipelineValue()}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      )}

      {/* Filters */}
      {showFilters && (
        <KanbanFiltersBar
          filters={filters}
          onFiltersChange={setFilters}
          dealTypes={filterOptions.dealTypes}
          assignees={filterOptions.assignees}
        />
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        {/* Pipeline Columns */}
        <div className="grid grid-cols-6 min-h-[500px]">
          {PIPELINE_STAGES.map((stage) => (
            <KanbanColumn
              key={stage}
              stage={stage as DealStage}
              deals={data.stages[stage]?.deals || []}
              total={data.stages[stage]?.totalValue || 0}
              isOver={false}
            />
          ))}
        </div>

        {/* Drag Overlay */}
        <DragOverlay dropAnimation={null}>
          {activeId && activeDeal ? (
            <div className="opacity-90 transform rotate-3 scale-105">
              <DealCard deal={activeDeal} isDragging compact={viewMode === 'compact'} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Lost Deals Section */}
      {closedLostDeals.length > 0 && (
        <div className="border-t border-neutral-200">
          <div className="p-4 bg-red-50">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold text-red-800">Closed Lost</div>
              <div className="text-xs text-red-600">
                {closedLostDeals.length}{' '}
                {closedLostDeals.length === 1 ? 'deal' : 'deals'} •{' '}
                {formatCurrency(data.stages.closed_lost?.totalValue || 0)}
              </div>
            </div>
            <div className="grid grid-cols-6 gap-3">
              {closedLostDeals.map((deal) => (
                <DealCard
                  key={deal.id}
                  deal={deal}
                  compact={viewMode === 'compact'}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
