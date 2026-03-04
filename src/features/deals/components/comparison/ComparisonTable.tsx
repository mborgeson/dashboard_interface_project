import { useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import type { DealForComparison, ComparisonMetric } from '@/hooks/api/useDealComparison';
import { DEAL_STAGE_LABELS } from '@/types/deal';

interface ComparisonTableProps {
  deals: DealForComparison[];
  metrics?: ComparisonMetric[];
  highlightBestWorst?: boolean;
}

// ---------- Formatting helpers ----------

function fmtPct(v: number | undefined): string {
  if (v == null) return 'N/A';
  return `${(v * 100).toFixed(1)}%`;
}

function fmtCompact(v: number | undefined): string {
  if (v == null) return 'N/A';
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function fmtMultiple(v: number | undefined): string {
  if (v == null) return 'N/A';
  return `${v.toFixed(1)}x`;
}

// UW metric row definitions
interface UwMetricRow {
  label: string;
  getValue: (d: DealForComparison) => string;
  getNumeric?: (d: DealForComparison) => number | undefined;
  higherIsBetter?: boolean;
}

const UW_METRICS: UwMetricRow[] = [
  {
    label: 'Units / Avg SF',
    getValue: (d) => `${d.units || 'N/A'} / ${d.avgUnitSf || 'N/A'} SF`,
  },
  {
    label: 'Loss Factor',
    getValue: (d) => {
      const total = (d.vacancyRate ?? 0) + (d.badDebtRate ?? 0) + (d.otherLossRate ?? 0) + (d.concessionsRate ?? 0);
      return total > 0 ? fmtPct(total) : 'N/A';
    },
    getNumeric: (d) => {
      const total = (d.vacancyRate ?? 0) + (d.badDebtRate ?? 0) + (d.otherLossRate ?? 0) + (d.concessionsRate ?? 0);
      return total > 0 ? total : undefined;
    },
    higherIsBetter: false,
  },
  {
    label: 'NOI Margin',
    getValue: (d) => fmtPct(d.noiMargin),
    getNumeric: (d) => d.noiMargin,
    higherIsBetter: true,
  },
  {
    label: 'Going-in Basis',
    getValue: (d) => `${fmtCompact(d.totalAcquisitionBudget ?? d.purchasePrice)} | ${fmtCompact(d.basisPerUnit)}/u`,
  },
  {
    label: 'Cap Rate (PP) T12',
    getValue: (d) => fmtPct(d.t12CapOnPp),
    getNumeric: (d) => d.t12CapOnPp,
    higherIsBetter: true,
  },
  {
    label: 'Cap Rate (PP) T3',
    getValue: (d) => fmtPct(d.t3CapOnPp),
    getNumeric: (d) => d.t3CapOnPp,
    higherIsBetter: true,
  },
  {
    label: 'Cap Rate (TC) T12',
    getValue: (d) => fmtPct(d.totalCostCapT12),
    getNumeric: (d) => d.totalCostCapT12,
    higherIsBetter: true,
  },
  {
    label: 'Cap Rate (TC) T3',
    getValue: (d) => fmtPct(d.totalCostCapT3),
    getNumeric: (d) => d.totalCostCapT3,
    higherIsBetter: true,
  },
  {
    label: 'Debt / Equity',
    getValue: (d) => `${fmtCompact(d.loanAmount)} / ${fmtCompact(d.lpEquity)}`,
  },
  {
    label: 'Exit Horizon',
    getValue: (d) => {
      const months = d.exitMonths != null ? `${Math.round(d.exitMonths)}mo` : 'N/A';
      return `${months} @ ${fmtPct(d.exitCapRate)}`;
    },
  },
  {
    label: 'Unlevered IRR / MOIC',
    getValue: (d) => `${fmtPct(d.unleveredIrr)} / ${fmtMultiple(d.unleveredMoic)}`,
    getNumeric: (d) => d.unleveredIrr,
    higherIsBetter: true,
  },
  {
    label: 'Levered IRR / MOIC',
    getValue: (d) => `${fmtPct(d.leveredIrr)} / ${fmtMultiple(d.leveredMoic)}`,
    getNumeric: (d) => d.leveredIrr,
    higherIsBetter: true,
  },
];

export function ComparisonTable({
  deals,
  highlightBestWorst = true,
}: ComparisonTableProps) {
  // For each metric with a numeric getter, find best/worst
  const metricHighlights = useMemo(() => {
    const highlights = new Map<string, { best: number; worst: number }>();
    for (const metric of UW_METRICS) {
      if (!metric.getNumeric) continue;
      const values = deals.map((d) => metric.getNumeric!(d)).filter((v): v is number => v != null);
      if (values.length < 2) continue;
      highlights.set(metric.label, {
        best: metric.higherIsBetter ? Math.max(...values) : Math.min(...values),
        worst: metric.higherIsBetter ? Math.min(...values) : Math.max(...values),
      });
    }
    return highlights;
  }, [deals]);

  const getCellClass = (metric: UwMetricRow, deal: DealForComparison): string => {
    if (!highlightBestWorst || !metric.getNumeric) return '';
    const val = metric.getNumeric(deal);
    if (val == null) return '';
    const stats = metricHighlights.get(metric.label);
    if (!stats || stats.best === stats.worst) return '';
    if (val === stats.best) return 'bg-green-50 text-green-700 font-semibold';
    if (val === stats.worst) return 'bg-red-50 text-red-700';
    return '';
  };

  if (deals.length === 0) {
    return (
      <div className="text-center py-8 text-neutral-500">
        No deals selected for comparison
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="bg-neutral-50">
            <TableHead className="sticky left-0 bg-neutral-50 z-10 min-w-[180px] font-semibold text-neutral-900">
              Metric
            </TableHead>
            {deals.map((deal) => (
              <TableHead
                key={deal.id}
                className="min-w-[200px] text-center font-semibold text-neutral-900"
              >
                <div className="space-y-1">
                  <div className="truncate max-w-[180px]" title={deal.propertyName}>
                    {deal.propertyName}
                  </div>
                  <div className="text-xs font-normal text-neutral-500">
                    {deal.submarket ?? `${deal.address.city}, ${deal.address.state}`}
                  </div>
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {/* Stage Row */}
          <TableRow>
            <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
              Pipeline Stage
            </TableCell>
            {deals.map((deal) => (
              <TableCell key={deal.id} className="text-center">
                {DEAL_STAGE_LABELS[deal.stage]}
              </TableCell>
            ))}
          </TableRow>

          {/* Vintage Row */}
          <TableRow>
            <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
              Vintage
            </TableCell>
            {deals.map((deal) => (
              <TableCell key={deal.id} className="text-center">
                {deal.yearBuilt
                  ? deal.yearRenovated
                    ? `${deal.yearBuilt} / Reno ${deal.yearRenovated}`
                    : `${deal.yearBuilt}`
                  : 'N/A'}
              </TableCell>
            ))}
          </TableRow>

          {/* UW Metric Rows */}
          {UW_METRICS.map((metric) => (
            <TableRow key={metric.label}>
              <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
                {metric.label}
              </TableCell>
              {deals.map((deal) => (
                <TableCell
                  key={deal.id}
                  className={cn('text-center', getCellClass(metric, deal))}
                >
                  {metric.getValue(deal)}
                </TableCell>
              ))}
            </TableRow>
          ))}

          {/* Days in Pipeline Row */}
          <TableRow>
            <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
              Days in Pipeline
            </TableCell>
            {deals.map((deal) => (
              <TableCell key={deal.id} className="text-center">
                {deal.totalDaysInPipeline} days
              </TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}
