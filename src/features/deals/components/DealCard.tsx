import { memo, useCallback, useMemo } from 'react';
import type { Deal } from '@/types/deal';
import { DEAL_STAGE_LABELS, DEAL_STAGE_COLORS } from '@/types/deal';
import { cn } from '@/lib/utils';
import { getSharePointDealFolderUrl } from '../utils/sharepoint';

interface DealCardProps {
  deal: Deal;
  isDragging?: boolean;
  compact?: boolean;
  onClick?: (dealId: string) => void;
}

// ---------- Formatting helpers ----------

function fmtPct(v: number | undefined | null): string {
  if (v == null) return 'N/A';
  return `${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | undefined | null): string {
  if (v == null || v === 0) return 'N/A';
  return v.toLocaleString();
}

// ---------- DealCard ----------

export const DealCard = memo(function DealCard({
  deal,
  isDragging = false,
  onClick,
}: DealCardProps) {
  const handleClick = useCallback(() => {
    onClick?.(deal.id);
  }, [onClick, deal.id]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick?.(deal.id);
      }
    },
    [onClick, deal.id],
  );

  const dealFolderUrl = useMemo(() => getSharePointDealFolderUrl(deal), [deal]);

  return (
    <div
      className={cn(
        'bg-white rounded-lg border border-neutral-200 shadow-card transition-all',
        'p-3',
        isDragging
          ? 'shadow-2xl ring-2 ring-blue-400 cursor-grabbing'
          : 'hover:shadow-card-hover hover:border-neutral-300',
        !isDragging && onClick && 'cursor-pointer',
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Stage Header — full-width, left-justified */}
      <div
        className={cn(
          'px-2 py-1 -mx-3 -mt-3 rounded-t-lg text-[11px] font-semibold border-b mb-2',
          DEAL_STAGE_COLORS[deal.stage],
        )}
      >
        {DEAL_STAGE_LABELS[deal.stage]}
      </div>

      {/* Name + Submarket */}
      <div className="mb-2">
        <h3 className="font-semibold text-sm text-neutral-900 truncate leading-tight">
          {deal.propertyName}
        </h3>
        <div className="text-[11px] text-neutral-500 truncate mt-0.5">
          {deal.submarket ?? deal.address.city}
        </div>
      </div>

      {/* Key Metrics — 4 compact rows */}
      <div className="space-y-1 py-1.5 border-t border-neutral-100">
        <div className="flex items-center justify-between text-xs">
          <span className="text-neutral-500">Units</span>
          <span className="font-medium text-neutral-900">{fmtNum(deal.units)}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-neutral-500">Cap Rate — PP (T12)</span>
          <span className="font-medium text-neutral-900">{fmtPct(deal.t12CapOnPp)}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-neutral-500">Total Going-In Basis/Unit</span>
          <span className="font-medium text-neutral-900">
            {deal.basisPerUnit != null ? `$${Math.round(deal.basisPerUnit).toLocaleString()}/Unit` : 'N/A'}
          </span>
        </div>
      </div>

      {/* Actions Row */}
      <div className="flex items-center gap-1 pt-1.5 mt-1 border-t border-neutral-100">
        <a
          href={dealFolderUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-[10px] px-2 py-0.5 rounded bg-neutral-100 hover:bg-neutral-200 text-neutral-600 font-medium transition-colors"
        >
          Deal Folder
        </a>
      </div>
    </div>
  );
});
