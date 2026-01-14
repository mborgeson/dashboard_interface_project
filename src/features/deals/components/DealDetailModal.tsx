/**
 * DealDetailModal - Modal component for viewing deal details with activity feed
 * Displays comprehensive deal information and integrated activity timeline
 */
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { ErrorState } from '@/components/ui/error-state';
import { useDealWithMockFallback } from '@/hooks/api/useDeals';
import { ActivityFeed } from './ActivityFeed';
import { Building2, DollarSign, Percent, Home, Calendar, User, MapPin } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DEAL_STAGE_LABELS } from '@/types/deal';

interface DealDetailModalProps {
  dealId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const stageColors: Record<string, string> = {
  lead: 'bg-slate-100 text-slate-800',
  underwriting: 'bg-blue-100 text-blue-800',
  loi: 'bg-purple-100 text-purple-800',
  due_diligence: 'bg-orange-100 text-orange-800',
  closing: 'bg-yellow-100 text-yellow-800',
  closed_won: 'bg-green-100 text-green-800',
  closed_lost: 'bg-red-100 text-red-800',
};

function formatCurrency(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value.toLocaleString()}`;
}

function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

function DealDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header Skeleton */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-5 w-48" />
        </div>
        <Skeleton className="h-6 w-24" />
      </div>

      {/* Metrics Grid Skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="p-4 rounded-lg border border-neutral-200 bg-neutral-50">
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-6 w-28" />
          </div>
        ))}
      </div>

      {/* Activity Feed Skeleton */}
      <div className="space-y-4">
        <Skeleton className="h-6 w-32" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="w-10 h-10 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface MetricCardProps {
  icon: React.ElementType;
  label: string;
  value: string;
  subValue?: string;
}

function MetricCard({ icon: Icon, label, value, subValue }: MetricCardProps) {
  return (
    <div className="p-4 rounded-lg border border-neutral-200 bg-neutral-50 hover:border-neutral-300 transition-colors">
      <div className="flex items-center gap-2 text-neutral-500 mb-1">
        <Icon className="w-4 h-4" />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="text-lg font-semibold text-neutral-900">{value}</div>
      {subValue && (
        <div className="text-xs text-neutral-500 mt-0.5">{subValue}</div>
      )}
    </div>
  );
}

export function DealDetailModal({ dealId, open, onOpenChange }: DealDetailModalProps) {
  const { data: deal, isLoading, error, refetch } = useDealWithMockFallback(dealId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="sr-only">
            {deal?.propertyName ?? 'Deal Details'}
          </DialogTitle>
        </DialogHeader>

        {isLoading && <DealDetailSkeleton />}

        {error && (
          <ErrorState
            title="Failed to load deal"
            description="Unable to fetch deal details. Please try again."
            onRetry={() => refetch()}
          />
        )}

        {!isLoading && !error && deal && (
          <div className="space-y-6">
            {/* Deal Header */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-neutral-900">
                  {deal.propertyName}
                </h2>
                <div className="flex items-center gap-1.5 text-neutral-600 mt-1">
                  <MapPin className="w-4 h-4" />
                  <span className="text-sm">
                    {deal.address.street}, {deal.address.city}, {deal.address.state}
                  </span>
                </div>
              </div>
              <Badge
                className={cn(
                  'text-sm font-medium px-3 py-1',
                  stageColors[deal.stage] || 'bg-neutral-100 text-neutral-800'
                )}
              >
                {DEAL_STAGE_LABELS[deal.stage] || deal.stage}
              </Badge>
            </div>

            {/* Deal Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <MetricCard
                icon={DollarSign}
                label="Deal Value"
                value={formatCurrency(deal.value)}
              />
              <MetricCard
                icon={Percent}
                label="Cap Rate"
                value={formatPercent(deal.capRate)}
              />
              <MetricCard
                icon={Home}
                label="Units"
                value={deal.units.toString()}
                subValue={deal.propertyType}
              />
              <MetricCard
                icon={Building2}
                label="Property Type"
                value={deal.propertyType}
              />
              <MetricCard
                icon={User}
                label="Assignee"
                value={deal.assignee}
              />
              <MetricCard
                icon={Calendar}
                label="Days in Pipeline"
                value={deal.totalDaysInPipeline.toString()}
                subValue={`${deal.daysInStage} days in current stage`}
              />
            </div>

            {/* Notes Section */}
            {deal.notes && (
              <div className="p-4 rounded-lg border border-neutral-200 bg-neutral-50">
                <h3 className="text-sm font-medium text-neutral-700 mb-2">Notes</h3>
                <p className="text-sm text-neutral-600 whitespace-pre-wrap">{deal.notes}</p>
              </div>
            )}

            {/* Activity Feed */}
            <ActivityFeed dealId={deal.id} showAddForm={true} />
          </div>
        )}

        {!isLoading && !error && !deal && dealId && (
          <ErrorState
            title="Deal not found"
            description="The requested deal could not be found."
            variant="warning"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

export default DealDetailModal;
