import type { Deal } from '@/types/deal';
import { DEAL_STAGE_LABELS, DEAL_STAGE_COLORS } from '@/types/deal';
import { Building2, MapPin, DollarSign, TrendingUp, User, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DealTimelineProps {
  deals: Deal[];
}

export function DealTimeline({ deals }: DealTimelineProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  };

  // Sort deals by most recent activity
  const sortedDeals = [...deals].sort(
    (a, b) => b.createdAt.getTime() - a.createdAt.getTime()
  );

  return (
    <div className="space-y-6">
      {sortedDeals.map((deal, index) => (
        <div key={deal.id} className="relative">
          {/* Timeline line */}
          {index < sortedDeals.length - 1 && (
            <div className="absolute left-5 top-12 bottom-0 w-0.5 bg-neutral-200" />
          )}

          {/* Deal Card */}
          <div className="flex gap-4">
            {/* Timeline indicator */}
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-accent-100 border-4 border-white shadow-md flex items-center justify-center">
              <Building2 className="w-5 h-5 text-accent-600" />
            </div>

            {/* Content */}
            <div className="flex-1 bg-white rounded-lg border border-neutral-200 shadow-card p-6">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-neutral-900 mb-1">
                    {deal.propertyName}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-neutral-600">
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      <span>
                        {deal.address.city}, {deal.address.state}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <User className="w-4 h-4" />
                      <span>{deal.assignee}</span>
                    </div>
                  </div>
                </div>
                <span
                  className={cn(
                    'px-3 py-1.5 rounded-md text-sm font-medium border',
                    DEAL_STAGE_COLORS[deal.stage]
                  )}
                >
                  {DEAL_STAGE_LABELS[deal.stage]}
                </span>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div>
                  <div className="flex items-center gap-1.5 text-sm text-neutral-600 mb-1">
                    <DollarSign className="w-4 h-4" />
                    <span>Deal Value</span>
                  </div>
                  <div className="text-lg font-semibold text-neutral-900">
                    {formatCurrency(deal.value)}
                  </div>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-sm text-neutral-600 mb-1">
                    <TrendingUp className="w-4 h-4" />
                    <span>Cap Rate</span>
                  </div>
                  <div className="text-lg font-semibold text-neutral-900">
                    {deal.capRate.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-sm text-neutral-600 mb-1">
                    <Building2 className="w-4 h-4" />
                    <span>Units</span>
                  </div>
                  <div className="text-lg font-semibold text-neutral-900">
                    {deal.units}
                  </div>
                </div>
                <div>
                  <div className="flex items-center gap-1.5 text-sm text-neutral-600 mb-1">
                    <Clock className="w-4 h-4" />
                    <span>In Pipeline</span>
                  </div>
                  <div className="text-lg font-semibold text-neutral-900">
                    {deal.totalDaysInPipeline}d
                  </div>
                </div>
              </div>

              {/* Timeline Events */}
              <div className="border-t border-neutral-100 pt-4">
                <h4 className="text-sm font-semibold text-neutral-900 mb-3">
                  Timeline
                </h4>
                <div className="space-y-3">
                  {deal.timeline.map((event, eventIndex) => (
                    <div key={event.id} className="flex gap-3">
                      {/* Event dot */}
                      <div className="flex-shrink-0 w-2 h-2 rounded-full bg-accent-500 mt-2" />

                      {/* Event content */}
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-neutral-900">
                            {DEAL_STAGE_LABELS[event.stage]}
                          </span>
                          <span className="text-xs text-neutral-500">
                            {formatDate(event.date)}
                          </span>
                        </div>
                        <p className="text-sm text-neutral-600 mt-0.5">
                          {event.description}
                        </p>
                        {event.user && (
                          <p className="text-xs text-neutral-500 mt-0.5">
                            by {event.user}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Notes */}
              {deal.notes && (
                <div className="border-t border-neutral-100 pt-4 mt-4">
                  <h4 className="text-sm font-semibold text-neutral-900 mb-2">
                    Notes
                  </h4>
                  <p className="text-sm text-neutral-700">{deal.notes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
