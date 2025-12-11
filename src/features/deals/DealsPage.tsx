import { useState, useEffect } from 'react';
import { mockDeals } from '@/data/mockDeals';
import { useDeals } from './hooks/useDeals';
import { DealPipeline } from './components/DealPipeline';
import { KanbanBoard } from './components/KanbanBoard';
import { DealTimeline } from './components/DealTimeline';
import { DealFilters } from './components/DealFilters';
import { Briefcase, LayoutGrid, List, TrendingUp, Calendar, Target, Kanban } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DealPipelineSkeleton } from '@/components/skeletons';
import { EmptyState } from '@/components/ui/empty-state';

type ViewMode = 'kanban' | 'pipeline' | 'list';

export function DealsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('kanban');
  const [isLoading, setIsLoading] = useState(true);

  const {
    filters,
    updateFilters,
    clearFilters,
    filteredDeals,
    dealsByStage,
    metrics,
    filterOptions,
    updateDealStage,
  } = useDeals(mockDeals);

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 800);
    return () => clearTimeout(timer);
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

  const formatPercent = (value: number) => {
    return (value * 100).toFixed(0) + '%';
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-neutral-900">Deal Pipeline</h1>
            <p className="text-neutral-600 mt-1">
              Track and manage acquisition opportunities
            </p>
          </div>
        </div>

        {/* Summary Stats Skeleton */}
        <div className="grid grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
              <div className="h-10 w-10 bg-neutral-200 animate-pulse rounded-lg mb-3" />
              <div className="h-8 w-16 bg-neutral-200 animate-pulse rounded mb-2" />
              <div className="h-4 w-24 bg-neutral-200 animate-pulse rounded" />
            </div>
          ))}
        </div>

        {/* Filters Skeleton */}
        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
          <div className="h-10 w-full bg-neutral-200 animate-pulse rounded" />
        </div>

        {/* Pipeline Skeleton */}
        <DealPipelineSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">Deal Pipeline</h1>
          <p className="text-neutral-600 mt-1">
            Track and manage acquisition opportunities
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2 bg-white rounded-lg shadow-md border border-neutral-200 p-1">
          <button
            onClick={() => setViewMode('kanban')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
              viewMode === 'kanban'
                ? 'bg-blue-600 text-white'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
            )}
          >
            <Kanban className="w-4 h-4" />
            Kanban
          </button>
          <button
            onClick={() => setViewMode('pipeline')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
              viewMode === 'pipeline'
                ? 'bg-blue-600 text-white'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
            )}
          >
            <LayoutGrid className="w-4 h-4" />
            Pipeline
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
              viewMode === 'list'
                ? 'bg-blue-600 text-white'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
            )}
          >
            <List className="w-4 h-4" />
            Timeline
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-6">
        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Briefcase className="w-5 h-5 text-blue-600" />
            </div>
          </div>
          <div className="text-2xl font-bold text-neutral-900 mb-1">
            {metrics.activeDealsCount}
          </div>
          <div className="text-sm text-neutral-600">Active Deals</div>
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="p-2 bg-green-100 rounded-lg">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
          </div>
          <div className="text-2xl font-bold text-neutral-900 mb-1">
            {formatCurrency(metrics.pipelineValue)}
          </div>
          <div className="text-sm text-neutral-600">Pipeline Value</div>
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="p-2 bg-orange-100 rounded-lg">
              <Calendar className="w-5 h-5 text-orange-600" />
            </div>
          </div>
          <div className="text-2xl font-bold text-neutral-900 mb-1">
            {metrics.avgDaysInPipeline}
          </div>
          <div className="text-sm text-neutral-600">Avg Days in Pipeline</div>
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Target className="w-5 h-5 text-purple-600" />
            </div>
          </div>
          <div className="text-2xl font-bold text-neutral-900 mb-1">
            {formatPercent(metrics.winRate)}
          </div>
          <div className="text-sm text-neutral-600">Win Rate</div>
          <div className="text-xs text-neutral-500 mt-1">
            {metrics.closedWonCount} won / {metrics.closedLostCount} lost
          </div>
        </div>
      </div>

      {/* Filters */}
      <DealFilters
        filters={filters}
        onUpdateFilters={updateFilters}
        onClearFilters={clearFilters}
        propertyTypes={filterOptions.propertyTypes}
        assignees={filterOptions.assignees}
      />

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-600">
          Showing {filteredDeals.length} of {mockDeals.length} deals
        </p>
      </div>

      {/* Deals View */}
      {filteredDeals.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No deals found"
          description="No deals match your current filters. Try adjusting your search criteria."
          action={{
            label: 'Clear Filters',
            onClick: clearFilters,
          }}
        />
      ) : viewMode === 'kanban' ? (
        <KanbanBoard dealsByStage={dealsByStage} onDealStageChange={updateDealStage} />
      ) : viewMode === 'pipeline' ? (
        <DealPipeline dealsByStage={dealsByStage} />
      ) : (
        <DealTimeline deals={filteredDeals} />
      )}
    </div>
  );
}
