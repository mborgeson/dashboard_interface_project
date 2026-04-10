import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { ErrorState } from '@/components/ui/error-state';
import { useDealWithMockFallback, useDealProformaReturns } from '@/hooks/api/useDeals';
import type { ProformaField } from '@/hooks/api/useDeals';
import { ActivityFeed } from './ActivityFeed';
import { DealAerialMap } from './DealAerialMap';
import { StageHistoryTimeline } from './StageHistoryTimeline';
import { StageOverrideForm } from './StageOverrideForm';
import { getSharePointDealFolderUrl } from '../utils/sharepoint';
import { MapPin, ExternalLink, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { DEAL_STAGE_LABELS, type DealStage } from '@/types/deal';

interface DealDetailModalProps {
  dealId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const stageColors: Record<string, string> = {
  dead: 'bg-red-100 text-red-800',
  initial_review: 'bg-blue-100 text-blue-800',
  active_review: 'bg-purple-100 text-purple-800',
  under_contract: 'bg-orange-100 text-orange-800',
  closed: 'bg-green-100 text-green-800',
  realized: 'bg-emerald-100 text-emerald-800',
};

// ---------- Formatting helpers ----------

function fmtPct(v: number | undefined | null): string {
  if (v == null) return 'N/A';
  return `${(v * 100).toFixed(1)}%`;
}

function fmtCompact(v: number | undefined | null): string {
  if (v == null) return 'N/A';
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toLocaleString('en-US', { maximumFractionDigits: 0 })}K`;
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

function DealDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-5 w-48" />
        </div>
        <Skeleton className="h-6 w-24" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="p-3 rounded-lg border border-neutral-200 bg-neutral-50">
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-6 w-28" />
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-neutral-50 last:border-b-0">
      <span className="text-sm text-neutral-600">{label}</span>
      <span className="text-sm font-medium text-neutral-900 text-right">{children}</span>
    </div>
  );
}

// ---------- Proforma field display helpers ----------

const PROFORMA_LABEL_MAP: Record<string, string> = {
  LEVERED_RETURNS_IRR_YR2: 'Levered IRR — Yr 2',
  LEVERED_RETURNS_IRR_YR3: 'Levered IRR — Yr 3',
  LEVERED_RETURNS_IRR_YR7: 'Levered IRR — Yr 7',
  LEVERED_RETURNS_MOIC_YR2: 'Levered MOIC — Yr 2',
  LEVERED_RETURNS_MOIC_YR3: 'Levered MOIC — Yr 3',
  LEVERED_RETURNS_MOIC_YR7: 'Levered MOIC — Yr 7',
  UNLEVERED_RETURNS_IRR_YR2: 'Unlevered IRR — Yr 2',
  UNLEVERED_RETURNS_IRR_YR3: 'Unlevered IRR — Yr 3',
  UNLEVERED_RETURNS_IRR_YR7: 'Unlevered IRR — Yr 7',
  UNLEVERED_RETURNS_MOIC_YR2: 'Unlevered MOIC — Yr 2',
  UNLEVERED_RETURNS_MOIC_YR3: 'Unlevered MOIC — Yr 3',
  UNLEVERED_RETURNS_MOIC_YR7: 'Unlevered MOIC — Yr 7',
  NOI_PER_UNIT_YR2: 'NOI / Unit — Yr 2',
  NOI_PER_UNIT_YR3: 'NOI / Unit — Yr 3',
  NOI_PER_UNIT_YR5: 'NOI / Unit — Yr 5',
  NOI_PER_UNIT_YR7: 'NOI / Unit — Yr 7',
  CAP_RATE_ALL_IN_YR3: 'All-In Cap Rate — Yr 3',
  CAP_RATE_ALL_IN_YR5: 'All-In Cap Rate — Yr 5',
  COC_YR5: 'Cash-on-Cash — Yr 5',
  DSCR_T3: 'DSCR — T3',
  DSCR_YR5: 'DSCR — Yr 5',
  PROFORMA_NOI_YR1: 'Proforma NOI — Yr 1',
  PROFORMA_NOI_YR2: 'Proforma NOI — Yr 2',
  PROFORMA_NOI_YR3: 'Proforma NOI — Yr 3',
  PROFORMA_DSCR_YR1: 'Proforma DSCR — Yr 1',
  PROFORMA_DSCR_YR2: 'Proforma DSCR — Yr 2',
  PROFORMA_DSCR_YR3: 'Proforma DSCR — Yr 3',
  PROFORMA_DEBT_YIELD_YR1: 'Proforma Debt Yield — Yr 1',
  PROFORMA_DEBT_YIELD_YR2: 'Proforma Debt Yield — Yr 2',
  PROFORMA_DEBT_YIELD_YR3: 'Proforma Debt Yield — Yr 3',
};

function fmtProformaValue(field: ProformaField): string {
  if (field.value_numeric == null) return field.value_text ?? 'N/A';
  const name = field.field_name;
  if (name.includes('IRR') || name.includes('CAP_RATE') || name.includes('COC') || name.includes('DEBT_YIELD')) {
    return `${(field.value_numeric * 100).toFixed(1)}%`;
  }
  if (name.includes('MOIC')) {
    return `${field.value_numeric.toFixed(2)}x`;
  }
  if (name.includes('DSCR')) {
    return `${field.value_numeric.toFixed(2)}x`;
  }
  if (name.includes('NOI') && !name.includes('PER_UNIT')) {
    return fmtCompact(field.value_numeric);
  }
  if (name.includes('PER_UNIT')) {
    return `$${Math.round(field.value_numeric).toLocaleString()}`;
  }
  return field.value_numeric.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

function ProformaReturnsSection({ dealId }: { dealId: string }) {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading } = useDealProformaReturns(expanded ? dealId : null);

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="flex items-center gap-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors"
      >
        <ChevronDown className="w-4 h-4" />
        Proforma Returns (Year-Specific)
      </button>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="flex items-center gap-2 text-sm font-medium text-neutral-700"
        >
          <ChevronDown className="w-4 h-4 rotate-180" />
          Proforma Returns (Year-Specific)
        </button>
        <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-200">
          <Skeleton className="h-4 w-48 mb-2" />
          <Skeleton className="h-4 w-36" />
        </div>
      </div>
    );
  }

  if (!data || data.total === 0) {
    return (
      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="flex items-center gap-2 text-sm font-medium text-neutral-700"
        >
          <ChevronDown className="w-4 h-4 rotate-180" />
          Proforma Returns (Year-Specific)
        </button>
        <p className="text-sm text-neutral-500 italic pl-6">
          No Proforma data available for this deal.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setExpanded(false)}
        className="flex items-center gap-2 text-sm font-medium text-neutral-700"
      >
        <ChevronDown className="w-4 h-4 rotate-180" />
        Proforma Returns (Year-Specific)
      </button>
      {data.groups.map((group) => (
        <div
          key={group.category}
          className="bg-neutral-50 rounded-lg p-4 border border-neutral-200"
        >
          <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
            {group.category}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
            {group.fields.map((field) => (
              <MetricRow
                key={field.field_name}
                label={PROFORMA_LABEL_MAP[field.field_name] ?? field.field_name}
              >
                {fmtProformaValue(field)}
              </MetricRow>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function DealDetailModal({ dealId, open, onOpenChange }: DealDetailModalProps) {
  const { data: deal, isLoading, error, refetch } = useDealWithMockFallback(dealId);

  // Loss factor total
  const totalLoss = deal
    ? (deal.vacancyRate ?? 0) + (deal.badDebtRate ?? 0) + (deal.otherLossRate ?? 0) + (deal.concessionsRate ?? 0)
    : 0;

  // Vintage string
  const vintage = deal?.yearBuilt
    ? deal.yearRenovated
      ? `Built ${deal.yearBuilt} / Reno ${deal.yearRenovated}`
      : `Built ${deal.yearBuilt}`
    : null;

  const dealFolderUrl = deal ? getSharePointDealFolderUrl(deal) : '';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-white">
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
          <div className="space-y-5">
            {/* Deal Header */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-neutral-900">
                  {deal.propertyName}
                </h2>
                <div className="flex items-center gap-1.5 text-neutral-600 mt-1">
                  <MapPin className="w-4 h-4" />
                  <span className="text-sm">
                    {deal.address.city && deal.address.state
                      ? `${deal.address.city}, ${deal.address.state}`
                      : deal.submarket ?? ''}
                    {vintage ? ` · ${vintage}` : ''}
                  </span>
                </div>
              </div>
              <Badge
                className={cn(
                  'text-sm font-medium px-3 py-1',
                  stageColors[deal.stage] || 'bg-neutral-100 text-neutral-800'
                )}
              >
                {DEAL_STAGE_LABELS[deal.stage as DealStage] ?? deal.stage}
              </Badge>
            </div>

            {/* SharePoint Link */}
            <div className="flex items-center gap-2">
              <a
                href={dealFolderUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md bg-neutral-100 text-neutral-700 hover:bg-neutral-200 font-medium transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Deal Folder
              </a>
            </div>

            {/* Full UW Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 bg-neutral-50 rounded-lg p-4 border border-neutral-200">
              <MetricRow label="Units / Avg SF">
                {fmtNum(deal.units)} / {deal.avgUnitSf != null && deal.avgUnitSf !== 0 ? `${Math.round(deal.avgUnitSf)} SF` : 'N/A'}
              </MetricRow>
              <MetricRow label="Total Loss Factor (T12)">
                {totalLoss > 0 ? fmtPct(totalLoss) : 'N/A'}
              </MetricRow>
              <MetricRow label="NOI Margin">{fmtPct(deal.noiMargin)}</MetricRow>
              <MetricRow label="Total Going-in Basis (Total / Per Unit)">
                {fmtCompact(deal.totalAcquisitionBudget ?? deal.purchasePrice)} / {deal.basisPerUnit != null ? `$${Math.round(deal.basisPerUnit).toLocaleString()}/Unit` : 'N/A'}
              </MetricRow>
              <MetricRow label="Cap Rate — Purchase Price (T12 / T3)">
                {fmtPct(deal.t12CapOnPp)} / {fmtPct(deal.t3CapOnPp)}
              </MetricRow>
              <MetricRow label="Cap Rate — Total Cost (T12 / T3)">
                {fmtPct(deal.totalCostCapT12)} / {fmtPct(deal.totalCostCapT3)}
              </MetricRow>
              <MetricRow label="Debt Capitalization ($ Amount / % of Total Capital)">
                {fmtCompact(deal.loanAmount)}{deal.loanAmount != null && deal.totalAcquisitionBudget ? ` / ${((deal.loanAmount / deal.totalAcquisitionBudget) * 100).toFixed(1)}%` : ''}
              </MetricRow>
              <MetricRow label="Equity Capitalization ($ Amount / % of Total Capital)">
                {fmtCompact(deal.lpEquity ?? deal.totalEquityCommitment)}{(deal.lpEquity ?? deal.totalEquityCommitment) != null && deal.totalAcquisitionBudget ? ` / ${(((deal.lpEquity ?? deal.totalEquityCommitment ?? 0) / deal.totalAcquisitionBudget) * 100).toFixed(1)}%` : ''}
              </MetricRow>
              <MetricRow label="Unlevered Returns (IRR / MOIC)">
                {fmtPct(deal.unleveredIrr)} / {fmtMultiple(deal.unleveredMoic)}
              </MetricRow>
              <MetricRow label="Levered Returns (IRR / MOIC)">
                {fmtPct(deal.leveredIrr)} / {fmtMultiple(deal.leveredMoic)}
              </MetricRow>
              <MetricRow label="LP Returns (IRR / MOIC)">
                {fmtPct(deal.lpIrr)} / {fmtMultiple(deal.lpMoic)}
              </MetricRow>
              <MetricRow label="Sale Attributes (Exit Month / Exit Cap Rate)">
                {deal.exitMonths != null ? `Month ${Math.round(deal.exitMonths)}` : 'N/A'} / {fmtPct(deal.exitCapRate)}
              </MetricRow>
            </div>

            {/* Manual Stage Override */}
            <StageOverrideForm
              dealId={deal.id}
              currentStage={deal.stage as DealStage}
              onSuccess={() => refetch()}
            />

            {/* Stage History Timeline */}
            <StageHistoryTimeline dealId={deal.id} />

            {/* Proforma Returns (year-specific fields from extraction) */}
            <ProformaReturnsSection dealId={deal.id} />

            {/* Aerial Map */}
            {(deal.latitude != null && deal.longitude != null) && (
              <div className="rounded-lg overflow-hidden border border-neutral-200">
                <DealAerialMap latitude={deal.latitude} longitude={deal.longitude} />
              </div>
            )}

            {/* Notes */}
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
