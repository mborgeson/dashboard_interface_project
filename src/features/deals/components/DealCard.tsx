import { useState } from 'react';
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

interface DealCardProps {
  deal: Deal;
}

export function DealCard({ deal }: DealCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { info } = useToast();

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getProgressPercentage = () => {
    const stages: Deal['stage'][] = [
      'lead',
      'underwriting',
      'loi',
      'due_diligence',
      'closing',
    ];
    const currentIndex = stages.indexOf(deal.stage);
    if (currentIndex === -1) return 100;
    return ((currentIndex + 1) / stages.length) * 100;
  };

  return (
    <div className="bg-white rounded-lg border border-neutral-200 p-4 shadow-card hover:shadow-card-hover transition-shadow">
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
          onClick={() => info(`Deal moved to ${DEAL_STAGE_LABELS[deal.stage]}`)}
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
            {formatCurrency(deal.value)}
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
            <span>{getProgressPercentage().toFixed(0)}%</span>
          </div>
          <div className="w-full bg-neutral-100 rounded-full h-1.5">
            <div
              className="bg-accent-500 h-1.5 rounded-full transition-all"
              style={{ width: `${getProgressPercentage()}%` }}
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
        <div className="flex items-center gap-1.5 text-xs text-neutral-600">
          <Calendar className="w-3.5 h-3.5" />
          <span>{deal.daysInStage} days</span>
        </div>
      </div>

      {/* Expandable Details */}
      {deal.notes && (
        <>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
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
}
