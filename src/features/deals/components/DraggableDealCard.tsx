/**
 * DraggableDealCard - Draggable wrapper for DealCard in Kanban board
 * Uses @dnd-kit/sortable for drag-and-drop functionality
 */
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Deal } from '@/types/deal';
import { DealCard } from './DealCard';
import { cn } from '@/lib/utils';
import { GripVertical } from 'lucide-react';

interface DraggableDealCardProps {
  deal: Deal;
}

export function DraggableDealCard({ deal }: DraggableDealCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: deal.id,
    data: {
      type: 'deal',
      deal,
    },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'relative group',
        isDragging && 'opacity-50 z-50'
      )}
    >
      {/* Drag Handle */}
      <div
        {...attributes}
        {...listeners}
        className={cn(
          'absolute left-0 top-0 bottom-0 w-8 flex items-center justify-center',
          'cursor-grab active:cursor-grabbing',
          'opacity-0 group-hover:opacity-100 transition-opacity',
          'bg-gradient-to-r from-neutral-100 to-transparent rounded-l-lg',
          'z-10'
        )}
        aria-label="Drag to move deal"
      >
        <GripVertical className="w-4 h-4 text-neutral-400" />
      </div>

      {/* Card Content */}
      <div className={cn(
        'transition-all duration-200',
        'group-hover:translate-x-2'
      )}>
        <DealCard deal={deal} isDragging={isDragging} compact />
      </div>
    </div>
  );
}
