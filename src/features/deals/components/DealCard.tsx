import { memo, useCallback, useMemo } from 'react';
import type { Deal, DealStage } from '@/types/deal';
import { DEAL_STAGE_LABELS, DEAL_STAGE_COLORS } from '@/types/deal';
import { cn } from '@/lib/utils';
import { DealQuickActions } from '@/components/quick-actions/QuickActionButton';
import { DealAerialMap } from './DealAerialMap';

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

function fmtCompact(v: number | undefined | null): string {
  if (v == null) return 'N/A';
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function fmtMultiple(v: number | undefined | null): string {
  if (v == null) return 'N/A';
  return `${v.toFixed(1)}x`;
}

function fmtNum(v: number | undefined | null): string {
  if (v == null || v === 0) return 'N/A';
  return v.toLocaleString();
}

// ---------- Stage folder mapping for SharePoint ----------

const STAGE_FOLDER_MAP: Record<string, string> = {
  dead: '0) Dead Deals',
  initial_review: '1) Initial UW and Review',
  active_review: '2) Active Review',
  under_contract: '3) Under Contract',
  closed: '4) Closed - Active Assets',
  realized: '5) Realized',
};

function getUwModelUrl(deal: Deal): string {
  const stageFolder = STAGE_FOLDER_MAP[deal.stage] ?? '1) Initial UW and Review';
  const dealName = encodeURIComponent(deal.propertyName);
  return `https://bandrcapital.sharepoint.com/sites/BRCapital-Internal/Shared Documents/Real Estate/Deals/${encodeURIComponent(stageFolder)}/${dealName}/`;
}

function getDealFolderUrl(deal: Deal): string {
  const stageFolder = STAGE_FOLDER_MAP[deal.stage] ?? '1) Initial UW and Review';
  const dealName = encodeURIComponent(deal.propertyName);
  return `https://bandrcapital.sharepoint.com/sites/BRCapital-Internal/Shared Documents/Real Estate/Deals/${encodeURIComponent(stageFolder)}/${dealName}/`;
}

// ---------- MetricRow component ----------

function MetricRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-neutral-500 truncate mr-2">{label}</span>
      <span className="font-medium text-neutral-900 text-right whitespace-nowrap">{children}</span>
    </div>
  );
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

  // Loss factor total
  const totalLoss = useMemo(() => {
    const vac = deal.vacancyRate ?? 0;
    const bd = deal.badDebtRate ?? 0;
    const ol = deal.otherLossRate ?? 0;
    const con = deal.concessionsRate ?? 0;
    const total = vac + bd + ol + con;
    return total > 0 ? total : null;
  }, [deal.vacancyRate, deal.badDebtRate, deal.otherLossRate, deal.concessionsRate]);

  // Vintage string
  const vintage = useMemo(() => {
    if (!deal.yearBuilt) return null;
    if (deal.yearRenovated) return `Built ${deal.yearBuilt} / Reno ${deal.yearRenovated}`;
    return `Built ${deal.yearBuilt}`;
  }, [deal.yearBuilt, deal.yearRenovated]);

  return (
    <div
      className={cn(
        'bg-white rounded-lg border border-neutral-200 shadow-card transition-all',
        'p-3',
        isDragging
          ? 'shadow-2xl ring-2 ring-blue-400 cursor-grabbing'
          : 'hover:shadow-card-hover',
        !isDragging && onClick && 'cursor-pointer',
      )}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header: Name + Stage Badge */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm text-neutral-900 truncate">{deal.propertyName}</h3>
          <div className="text-xs text-neutral-500 truncate">
            {deal.submarket ?? deal.address.city}
            {vintage ? ` · ${vintage}` : ''}
          </div>
        </div>
        <span
          className={cn(
            'px-2 py-0.5 rounded-md text-[10px] font-medium border ml-2 shrink-0',
            DEAL_STAGE_COLORS[deal.stage],
          )}
        >
          {DEAL_STAGE_LABELS[deal.stage]}
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="space-y-1 py-2 border-t border-neutral-100">
        {/* Row 2: Units + Avg SF */}
        <MetricRow label="Units / Avg SF">
          {fmtNum(deal.units)} / {fmtNum(deal.avgUnitSf)} SF
        </MetricRow>

        {/* Row 3: Loss Factor */}
        <MetricRow label="Loss Factor">
          {totalLoss != null ? fmtPct(totalLoss) : 'N/A'}
        </MetricRow>

        {/* Row 4: NOI Margin */}
        <MetricRow label="NOI Margin">{fmtPct(deal.noiMargin)}</MetricRow>

        {/* Row 5: Going-in Basis */}
        <MetricRow label="Basis">
          {fmtCompact(deal.totalAcquisitionBudget ?? deal.purchasePrice)} | {fmtCompact(deal.basisPerUnit)}/u
        </MetricRow>

        {/* Row 6: Cap Rate on PP */}
        <MetricRow label="Cap (PP)">
          T12 {fmtPct(deal.t12CapOnPp)} · T3 {fmtPct(deal.t3CapOnPp)}
        </MetricRow>

        {/* Row 7: Cap Rate on Total Cost */}
        <MetricRow label="Cap (TC)">
          T12 {fmtPct(deal.totalCostCapT12)} · T3 {fmtPct(deal.totalCostCapT3)}
        </MetricRow>

        {/* Row 8: Project Capital */}
        <MetricRow label="Capital">
          {fmtCompact(deal.loanAmount)} D / {fmtCompact(deal.lpEquity)} E
        </MetricRow>

        {/* Row 9: Horizon + Exit Cap */}
        <MetricRow label="Exit">
          {deal.exitMonths != null ? `${Math.round(deal.exitMonths)}mo` : 'N/A'} @ {fmtPct(deal.exitCapRate)}
        </MetricRow>

        {/* Row 10: Unlevered Returns */}
        <MetricRow label="Unlev">
          {fmtPct(deal.unleveredIrr)} / {fmtMultiple(deal.unleveredMoic)}
        </MetricRow>

        {/* Row 11: Levered Returns */}
        <MetricRow label="Levered">
          {fmtPct(deal.leveredIrr)} / {fmtMultiple(deal.leveredMoic)}
        </MetricRow>
      </div>

      {/* Row 12: Aerial Map */}
      <div className="mt-1">
        <DealAerialMap latitude={deal.latitude} longitude={deal.longitude} />
      </div>

      {/* Mini Activity Feed */}
      {deal.recentActivities && deal.recentActivities.length > 0 && (
        <div className="mt-2 pt-2 border-t border-neutral-100 space-y-1">
          {deal.recentActivities.slice(0, 3).map((activity, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[10px] text-neutral-500">
              <span className="shrink-0 mt-0.5 w-1 h-1 rounded-full bg-neutral-300" />
              <span className="truncate">{activity.description}</span>
            </div>
          ))}
        </div>
      )}

      {/* Actions Row */}
      <div className="flex items-center justify-between pt-2 mt-2 border-t border-neutral-100">
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(getUwModelUrl(deal), '_blank');
            }}
            className="text-[10px] px-2 py-1 rounded bg-neutral-100 hover:bg-neutral-200 text-neutral-700 font-medium transition-colors"
          >
            UW Model
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(getDealFolderUrl(deal), '_blank');
            }}
            className="text-[10px] px-2 py-1 rounded bg-neutral-100 hover:bg-neutral-200 text-neutral-700 font-medium transition-colors"
          >
            Deal Folder
          </button>
        </div>
        <DealQuickActions dealId={deal.id} size="sm" />
      </div>
    </div>
  );
});
