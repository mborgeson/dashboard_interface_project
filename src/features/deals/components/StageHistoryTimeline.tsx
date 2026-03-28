/**
 * StageHistoryTimeline — vertical timeline of deal stage transitions.
 *
 * Fetches from GET /api/v1/deals/{id}/stage-history and renders a
 * chronological list with color-coded stage badges, relative timestamps,
 * and source attribution.
 */
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { STALE_TIMES } from '@/lib/constants/query';
import { cn } from '@/lib/utils';
import { DEAL_STAGE_LABELS, DEAL_STAGE_COLORS, type DealStage } from '@/types/deal';

// ── Types ────────────────────────────────────────────────────────────────

interface StageChangeLogEntry {
  id: number;
  deal_id: number;
  old_stage: string | null;
  new_stage: string;
  source: string;
  changed_by_user_id: number | null;
  reason: string | null;
  created_at: string;
}

interface StageHistoryResponse {
  deal_id: number;
  history: StageChangeLogEntry[];
  total: number;
}

// ── Query ────────────────────────────────────────────────────────────────

const stageHistoryKeys = {
  all: ['stage-history'] as const,
  byDeal: (dealId: string) => [...stageHistoryKeys.all, dealId] as const,
};

function useStageHistory(dealId: string | null) {
  return useQuery({
    queryKey: stageHistoryKeys.byDeal(dealId ?? ''),
    queryFn: () =>
      apiClient.get<StageHistoryResponse>(`/deals/${dealId}/stage-history`),
    enabled: !!dealId,
    staleTime: STALE_TIMES.MEDIUM,
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────

const SOURCE_LABELS: Record<string, string> = {
  sharepoint_sync: 'SharePoint Sync',
  user_kanban: 'Kanban Board',
  extraction_sync: 'Extraction',
  manual_override: 'Manual',
  file_monitor: 'File Monitor',
  manual: 'Manual',
};

function relativeTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function stageBadge(stage: string) {
  const label = DEAL_STAGE_LABELS[stage as DealStage] ?? stage;
  const colors = DEAL_STAGE_COLORS[stage as DealStage] ?? 'bg-neutral-100 text-neutral-700 border-neutral-300';
  return (
    <Badge className={cn('text-xs font-medium px-2 py-0.5 border', colors)}>
      {label}
    </Badge>
  );
}

// ── Component ────────────────────────────────────────────────────────────

interface StageHistoryTimelineProps {
  dealId: string | null;
}

export function StageHistoryTimeline({ dealId }: StageHistoryTimelineProps) {
  const { data, isLoading, error } = useStageHistory(dealId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-neutral-700">Stage History</h3>
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-3 w-3 rounded-full mt-1.5 shrink-0" />
            <div className="space-y-1 flex-1">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return null; // Silently fail — timeline is supplementary
  }

  if (!data || data.total === 0) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-neutral-700">Stage History</h3>
        <p className="text-sm text-neutral-500 italic">No stage changes recorded.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-neutral-700">
        Stage History ({data.total})
      </h3>
      <div className="relative pl-5 space-y-4">
        {/* Vertical line */}
        <div className="absolute left-[5px] top-2 bottom-2 w-px bg-neutral-200" />

        {data.history.map((entry) => (
          <div key={entry.id} className="relative flex gap-3">
            {/* Dot */}
            <div className="absolute left-[-17px] top-1.5 w-2.5 h-2.5 rounded-full bg-neutral-400 border-2 border-white" />

            <div className="flex-1 min-w-0">
              {/* Stage badges */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {entry.old_stage && (
                  <>
                    {stageBadge(entry.old_stage)}
                    <span className="text-neutral-400 text-xs">&rarr;</span>
                  </>
                )}
                {stageBadge(entry.new_stage)}
              </div>

              {/* Metadata line */}
              <div className="flex items-center gap-2 mt-1 text-xs text-neutral-500">
                <span title={new Date(entry.created_at).toLocaleString()}>
                  {relativeTime(entry.created_at)}
                </span>
                <span className="text-neutral-300">|</span>
                <span>{SOURCE_LABELS[entry.source] ?? entry.source}</span>
              </div>

              {/* Reason */}
              {entry.reason && (
                <p className="mt-1 text-xs text-neutral-600 italic">
                  {entry.reason}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default StageHistoryTimeline;
