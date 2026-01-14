/**
 * ActivityFeed - Self-fetching activity feed component
 * Displays deal activities with timeline view and add form
 */
import { useState } from 'react';
import { ErrorState } from '@/components/ui/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { useDealActivitiesWithMockFallback } from '@/hooks/api/useDeals';
import { ActivityTimeline } from './ActivityTimeline';
import { ActivityForm } from './ActivityForm';
import { Plus, History } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityFeedProps {
  dealId: string;
  className?: string;
  maxItems?: number;
  showAddForm?: boolean;
  collapsible?: boolean;
}

export function ActivityFeed({
  dealId,
  className,
  maxItems,
  showAddForm = true,
  collapsible = false,
}: ActivityFeedProps) {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const { data, isLoading, error, refetch } = useDealActivitiesWithMockFallback(dealId);

  if (isLoading) {
    return <ActivityFeedSkeleton className={className} />;
  }

  if (error || !data) {
    return (
      <div className={className}>
        <ErrorState
          title="Failed to load activities"
          description="Unable to fetch deal activities. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const activities = maxItems ? data.activities.slice(0, maxItems) : data.activities;

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-neutral-500" />
            <CardTitle className="text-lg">Activity Feed</CardTitle>
            {data.total > 0 && (
              <span className="text-sm text-neutral-500">
                ({data.total} {data.total === 1 ? 'activity' : 'activities'})
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {showAddForm && (
              <button
                onClick={() => setIsFormOpen(!isFormOpen)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  isFormOpen
                    ? 'bg-neutral-100 text-neutral-700'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                )}
              >
                <Plus className="w-4 h-4" />
                {isFormOpen ? 'Cancel' : 'Add Activity'}
              </button>
            )}
            {collapsible && (
              <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="text-sm text-neutral-500 hover:text-neutral-700"
              >
                {isCollapsed ? 'Show' : 'Hide'}
              </button>
            )}
          </div>
        </div>
      </CardHeader>

      {!isCollapsed && (
        <CardContent className="pt-0">
          {/* Add Activity Form */}
          {isFormOpen && (
            <div className="mb-4 pb-4 border-b border-neutral-200">
              <ActivityForm
                dealId={dealId}
                onSuccess={() => {
                  setIsFormOpen(false);
                  refetch();
                }}
                onCancel={() => setIsFormOpen(false)}
              />
            </div>
          )}

          {/* Activity Timeline */}
          {activities.length > 0 ? (
            <ActivityTimeline activities={activities} />
          ) : (
            <div className="text-center py-8 text-neutral-500">
              <History className="w-12 h-12 mx-auto mb-3 text-neutral-300" />
              <p className="font-medium">No activities yet</p>
              <p className="text-sm">Activity history will appear here</p>
            </div>
          )}

          {/* Show More */}
          {maxItems && data.total > maxItems && (
            <div className="mt-4 text-center">
              <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                View all {data.total} activities
              </button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

function ActivityFeedSkeleton({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="w-5 h-5" />
            <Skeleton className="h-6 w-32" />
          </div>
          <Skeleton className="h-8 w-28" />
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="w-10 h-10 rounded-full flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-32" />
              </div>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
