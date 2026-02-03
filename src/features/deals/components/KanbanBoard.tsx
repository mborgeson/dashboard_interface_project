/**
 * KanbanBoard - Drag and drop deal management board
 * Provides visual pipeline management with stage transitions
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
import type {
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import type { Deal, DealStage } from '@/types/deal';
import { KanbanColumn } from './KanbanColumn';
import { DealCard } from './DealCard';
import { useToast } from '@/hooks/useToast';

interface KanbanBoardProps {
  dealsByStage: Record<DealStage, Deal[]>;
  onDealStageChange: (dealId: string, newStage: DealStage, oldStage: DealStage) => void;
}

const PIPELINE_STAGES: DealStage[] = [
  'dead',
  'initial_review',
  'active_review',
  'under_contract',
  'closed',
  'realized',
];

// Validate stage transitions (prevent skipping stages or going backwards)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function isValidTransition(from: DealStage, _to: DealStage): boolean {
  // Allow any transition for flexibility - can be customized for business rules
  // For example, to enforce sequential progression:
  // const stageOrder: DealStage[] = ['lead', 'underwriting', 'loi', 'due_diligence', 'closing', 'closed_won'];
  // const fromIndex = stageOrder.indexOf(from);
  // const toIndex = stageOrder.indexOf(to);
  // return toIndex === fromIndex + 1 || to === 'closed_lost';

  // For now, allow any transition except from closed states
  if (from === 'realized') {
    return false;
  }
  return true;
}

export function KanbanBoard({ dealsByStage, onDealStageChange }: KanbanBoardProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeDeal, setActiveDeal] = useState<Deal | null>(null);
  const { success, error } = useToast();

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const findDealById = useCallback((id: string): Deal | null => {
    for (const stage of Object.keys(dealsByStage) as DealStage[]) {
      const deal = dealsByStage[stage].find((d) => d.id === id);
      if (deal) return deal;
    }
    return null;
  }, [dealsByStage]);

  const findStageByDealId = useCallback((id: string): DealStage | null => {
    for (const stage of Object.keys(dealsByStage) as DealStage[]) {
      const deal = dealsByStage[stage].find((d) => d.id === id);
      if (deal) return stage;
    }
    return null;
  }, [dealsByStage]);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const { active } = event;
    const deal = findDealById(active.id as string);
    setActiveId(active.id as string);
    setActiveDeal(deal);
  }, [findDealById]);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleDragOver = useCallback((_event: DragOverEvent) => {
    // Preview of drop is handled by visual highlighting in KanbanColumn
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event;

    setActiveId(null);
    setActiveDeal(null);

    if (!over) return;

    const dealId = active.id as string;
    const oldStage = findStageByDealId(dealId);

    // Determine the new stage - could be a column or another deal in a column
    let newStage: DealStage;

    if (PIPELINE_STAGES.includes(over.id as DealStage)) {
      // Dropped on a column
      newStage = over.id as DealStage;
    } else {
      // Dropped on a deal - find which stage that deal is in
      const overStage = findStageByDealId(over.id as string);
      if (!overStage) return;
      newStage = overStage;
    }

    if (oldStage && oldStage !== newStage) {
      // Validate stage transition
      if (isValidTransition(oldStage, newStage)) {
        onDealStageChange(dealId, newStage, oldStage);
        success(`Deal moved to ${newStage.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}`);
      } else {
        error('Invalid stage transition');
      }
    }
  }, [findStageByDealId, onDealStageChange, success, error]);

  const handleDragCancel = useCallback(() => {
    setActiveId(null);
    setActiveDeal(null);
  }, []);

  // Memoized currency formatter
  const formatCurrency = useCallback((value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(value);
  }, []);

  // Memoize stage totals to avoid recalculation on every render
  const stageTotals = useMemo(() => {
    const totals: Record<DealStage, number> = {} as Record<DealStage, number>;
    for (const stage of PIPELINE_STAGES) {
      totals[stage] = dealsByStage[stage]?.reduce((sum, deal) => sum + deal.value, 0) ?? 0;
    }
    return totals;
  }, [dealsByStage]);

  // Memoized total pipeline value
  const totalPipelineValue = useMemo(() => {
    return PIPELINE_STAGES
      .reduce((sum, stage) => sum + stageTotals[stage], 0);
  }, [stageTotals]);

  return (
    <div className="bg-white rounded-lg border border-neutral-200 shadow-card">
      {/* Pipeline Summary Header */}
      <div className="p-4 border-b border-neutral-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">Deal Pipeline</h2>
            <p className="text-sm text-neutral-600">
              Drag and drop deals to update their stage
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm text-neutral-600">Total Pipeline Value</div>
            <div className="text-2xl font-bold text-blue-600">
              {formatCurrency(totalPipelineValue)}
            </div>
          </div>
        </div>
      </div>

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
              stage={stage}
              deals={dealsByStage[stage]}
              total={stageTotals[stage]}
              isOver={false}
            />
          ))}
        </div>

        {/* Drag Overlay - Shows the card being dragged */}
        <DragOverlay dropAnimation={null}>
          {activeId && activeDeal ? (
            <div className="opacity-90 transform rotate-3 scale-105">
              <DealCard deal={activeDeal} isDragging />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

    </div>
  );
}
