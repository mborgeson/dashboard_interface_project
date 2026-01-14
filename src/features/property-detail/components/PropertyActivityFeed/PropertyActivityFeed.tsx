/**
 * PropertyActivityFeed - Self-fetching activity feed component for property detail pages
 * Displays property-specific activities with timeline view and filtering
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import * as Collapsible from '@radix-ui/react-collapsible';
import { ErrorState } from '@/components/ui/error-state';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import {
  usePropertyActivitiesWithMockFallback,
  type PropertyActivityType,
} from '@/hooks/api/usePropertyActivities';
import { PropertyActivityTimeline } from './PropertyActivityTimeline';
import {
  History,
  ChevronDown,
  ChevronRight,
  Filter,
  Eye,
  Edit3,
  MessageSquare,
  RefreshCw,
  Upload,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { WS_URL } from '@/lib/config';

export interface PropertyActivityFeedProps {
  propertyId: string;
  maxItems?: number;
  showAddForm?: boolean;
  collapsible?: boolean;
  className?: string;
  activityTypes?: PropertyActivityType[];
  enableRealtime?: boolean;
}

interface ActivityTypeFilter {
  type: PropertyActivityType;
  label: string;
  icon: typeof Eye;
}

const ACTIVITY_TYPE_FILTERS: ActivityTypeFilter[] = [
  { type: 'view', label: 'Views', icon: Eye },
  { type: 'edit', label: 'Edits', icon: Edit3 },
  { type: 'comment', label: 'Comments', icon: MessageSquare },
  { type: 'status_change', label: 'Status Changes', icon: RefreshCw },
  { type: 'document_upload', label: 'Documents', icon: Upload },
];

export function PropertyActivityFeed({
  propertyId,
  maxItems = 20,
  collapsible = false,
  className,
  activityTypes,
  enableRealtime = true,
}: PropertyActivityFeedProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<PropertyActivityType[]>(activityTypes || []);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch activities with the selected filters
  const { data, isLoading, error, refetch } = usePropertyActivitiesWithMockFallback(
    propertyId,
    { activityTypes: selectedTypes.length > 0 ? selectedTypes : undefined }
  );

  // WebSocket connection for real-time updates
  const connectWebSocket = useCallback(() => {
    if (!enableRealtime || !propertyId) return;

    try {
      const ws = new WebSocket(`${WS_URL}/property/${propertyId}`);

      ws.onopen = () => {
        // Subscribe to property room
        ws.send(JSON.stringify({ action: 'subscribe', room: `property_${propertyId}` }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'activity' && message.propertyId === propertyId) {
            // Refetch activities when a new one is received
            refetch();
          }
        } catch {
          // Ignore parsing errors
        }
      };

      ws.onerror = () => {
        // Silently handle WebSocket errors
      };

      ws.onclose = () => {
        // Could implement reconnection logic here
      };

      wsRef.current = ws;
    } catch {
      // WebSocket connection failed, continue without real-time updates
    }
  }, [enableRealtime, propertyId, refetch]);

  // Setup WebSocket connection
  useEffect(() => {
    if (enableRealtime) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [enableRealtime, connectWebSocket]);

  // Handle filter toggle
  const toggleFilter = (type: PropertyActivityType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // Clear all filters
  const clearFilters = () => {
    setSelectedTypes([]);
  };

  if (isLoading) {
    return <PropertyActivityFeedSkeleton className={className} collapsible={collapsible} />;
  }

  if (error || !data) {
    return (
      <div className={className}>
        <ErrorState
          title="Failed to load activities"
          description="Unable to fetch property activities. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const activities = maxItems ? data.activities.slice(0, maxItems) : data.activities;

  const content = (
    <>
      {/* Filters */}
      {showFilters && (
        <div className="mb-4 pb-4 border-b border-neutral-200">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-neutral-700">Filter by Type</span>
            {selectedTypes.length > 0 && (
              <button
                onClick={clearFilters}
                className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                <X className="w-3 h-3" />
                Clear filters
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {ACTIVITY_TYPE_FILTERS.map((filter) => {
              const Icon = filter.icon;
              const isSelected = selectedTypes.includes(filter.type);
              return (
                <button
                  key={filter.type}
                  onClick={() => toggleFilter(filter.type)}
                  aria-label={`Filter by ${filter.label}`}
                  aria-pressed={isSelected}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border',
                    isSelected
                      ? 'bg-blue-50 border-blue-300 text-blue-700'
                      : 'bg-white border-neutral-200 text-neutral-600 hover:bg-neutral-50'
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {filter.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Activity Timeline */}
      {activities.length > 0 ? (
        <PropertyActivityTimeline activities={activities} />
      ) : (
        <div className="text-center py-8 text-neutral-500">
          <History className="w-12 h-12 mx-auto mb-3 text-neutral-300" />
          <p className="font-medium">No activities yet</p>
          <p className="text-sm">
            {selectedTypes.length > 0
              ? 'No activities match the selected filters'
              : 'Property activity will appear here'}
          </p>
        </div>
      )}

      {/* Show More */}
      {maxItems && data.total > maxItems && (
        <div className="mt-4 pt-4 border-t border-neutral-100 text-center">
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            View all {data.total} activities
          </button>
        </div>
      )}
    </>
  );

  if (collapsible) {
    return (
      <Collapsible.Root open={isOpen} onOpenChange={setIsOpen}>
        <Card className={cn('overflow-hidden', className)}>
          <Collapsible.Trigger asChild>
            <CardHeader className="pb-3 cursor-pointer hover:bg-neutral-50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isOpen ? (
                    <ChevronDown className="w-4 h-4 text-neutral-500" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-neutral-500" />
                  )}
                  <History className="w-5 h-5 text-neutral-500" />
                  <CardTitle className="text-lg">Activity Feed</CardTitle>
                  {data.total > 0 && (
                    <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">
                      {data.total}
                    </span>
                  )}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowFilters(!showFilters);
                  }}
                  aria-label={showFilters ? 'Hide activity filters' : 'Show activity filters'}
                  aria-expanded={showFilters}
                  className={cn(
                    'p-2 rounded-lg transition-colors',
                    showFilters
                      ? 'bg-blue-100 text-blue-600'
                      : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100'
                  )}
                >
                  <Filter className="w-4 h-4" />
                </button>
              </div>
            </CardHeader>
          </Collapsible.Trigger>

          <Collapsible.Content>
            <CardContent className="pt-0">{content}</CardContent>
          </Collapsible.Content>
        </Card>
      </Collapsible.Root>
    );
  }

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-neutral-500" />
            <CardTitle className="text-lg">Activity Feed</CardTitle>
            {data.total > 0 && (
              <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">
                {data.total}
              </span>
            )}
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            aria-label={showFilters ? 'Hide activity filters' : 'Show activity filters'}
            aria-expanded={showFilters}
            className={cn(
              'p-2 rounded-lg transition-colors',
              showFilters
                ? 'bg-blue-100 text-blue-600'
                : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100'
            )}
          >
            <Filter className="w-4 h-4" />
          </button>
        </div>
      </CardHeader>
      <CardContent className="pt-0">{content}</CardContent>
    </Card>
  );
}

function PropertyActivityFeedSkeleton({
  className,
  collapsible,
}: {
  className?: string;
  collapsible?: boolean;
}) {
  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {collapsible && <Skeleton className="w-4 h-4" />}
            <Skeleton className="w-5 h-5" />
            <Skeleton className="h-6 w-28" />
            <Skeleton className="h-5 w-8 rounded-full" />
          </div>
          <Skeleton className="w-8 h-8" />
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="w-10 h-10 rounded-full flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-3 w-20" />
              </div>
              <Skeleton className="h-4 w-full" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
