import { useState, memo, useCallback, useMemo } from 'react';
import type { Deal } from '@/types/deal';
import { DEAL_STAGE_LABELS, DEAL_STAGE_COLORS } from '@/types/deal';
import {
  Building2,
  MapPin,
  DollarSign,
  TrendingUp,
  User,
  Calendar,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/useToast';
import { DealQuickActions } from '@/components/quick-actions/QuickActionButton';

interface DealCardProps {
  deal: Deal;
  isDragging?: boolean;
  compact?: boolean;
  onClick?: (dealId: string) => void;
}

// Currency formatter instance - created once, reused
const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

// Progress stages constant - defined outside component
const PROGRESS_STAGES: Deal['stage'][] = [
  'lead',
  'underwriting',
  'loi',
  'due_diligence',
  'closing',
];

export const DealCard = memo(function DealCard({ deal, isDragging = false, compact = false, onClick }: DealCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { info } = useToast();

  // Memoized currency formatting
  const formattedValue = useMemo(() => currencyFormatter.format(deal.value), [deal.value]);

  // Memoized progress percentage calculation
  const progressPercentage = useMemo(() => {
    const currentIndex = PROGRESS_STAGES.indexOf(deal.stage);
    if (currentIndex === -1) return 100;
    return ((currentIndex + 1) / PROGRESS_STAGES.length) * 100;
  }, [deal.stage]);

  // Memoized click handler
  const handleClick = useCallback(() => {
    onClick?.(deal.id);
  }, [onClick, deal.id]);

  // Memoized keyboard handler
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick?.(deal.id);
    }
  }, [onClick, deal.id]);

  // Memoized stage button click handler
  const handleStageClick = useCallback(() => {
    info(`Deal moved to ${DEAL_STAGE_LABELS[deal.stage]}`);
  }, [info, deal.stage]);

  // Memoized expand toggle
  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  return (
    <div
      className={cn(
        "bg-white rounded-lg border border-neutral-200 shadow-card transition-all",
        compact ? "p-3" : "p-4",
        isDragging ? "shadow-2xl ring-2 ring-blue-400 cursor-grabbing" : "hover:shadow-card-hover",
        !isDragging && onClick && "cursor-pointer"
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-neutral-900 mb-1">
            {deal.propertyName}
          </h3>
          <div className="flex items-center text-sm text-neutral-600 gap-1">
            <MapPin className="w-3.5 h-3.5" />
            <span>
              {deal.address.city}, {deal.address.state}
            </span>
          </div>
        </div>
        <button
          onClick={handleStageClick}
          className={cn(
            'px-2.5 py-1 rounded-md text-xs font-medium border cursor-pointer hover:opacity-80 transition-opacity',
            DEAL_STAGE_COLORS[deal.stage]
          )}
        >
          {DEAL_STAGE_LABELS[deal.stage]}
        </button>
      </div>

      {/* Key Metrics */}
      <div className="space-y-2 mb-3">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-1.5 text-neutral-600">
            <DollarSign className="w-4 h-4" />
            <span>Value</span>
          </div>
          <span className="font-semibold text-neutral-900">
            {formattedValue}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-1.5 text-neutral-600">
            <TrendingUp className="w-4 h-4" />
            <span>Cap Rate</span>
          </div>
          <span className="font-semibold text-neutral-900">
            {deal.capRate.toFixed(1)}%
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-1.5 text-neutral-600">
            <Building2 className="w-4 h-4" />
            <span>Units</span>
          </div>
          <span className="font-semibold text-neutral-900">{deal.units}</span>
        </div>
      </div>

      {/* Progress Bar */}
      {!['closed_won', 'closed_lost'].includes(deal.stage) && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs text-neutral-600 mb-1">
            <span>Progress</span>
            <span>{progressPercentage.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-neutral-100 rounded-full h-1.5">
            <div
              className="bg-accent-500 h-1.5 rounded-full transition-all"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-neutral-100">
        <div className="flex items-center gap-1.5 text-xs text-neutral-600">
          <User className="w-3.5 h-3.5" />
          <span>{deal.assignee}</span>
        </div>
        <div className="flex items-center gap-3">
          <DealQuickActions dealId={deal.id} size="sm" />
          <div className="flex items-center gap-1.5 text-xs text-neutral-600">
            <Calendar className="w-3.5 h-3.5" />
            <span>{deal.daysInStage} days</span>
          </div>
        </div>
      </div>

      {/* Expandable Details */}
      {deal.notes && (
        <>
          <button
            onClick={toggleExpanded}
            className="w-full flex items-center justify-center gap-1 mt-3 pt-3 border-t border-neutral-100 text-xs text-neutral-600 hover:text-neutral-900 transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" />
                Hide Details
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" />
                Show Details
              </>
            )}
          </button>

          {isExpanded && (
            <div className="mt-3 pt-3 border-t border-neutral-100 text-sm text-neutral-700">
              <p className="font-medium text-neutral-900 mb-1">Notes:</p>
              <p>{deal.notes}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
});
