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

interface MetricConfig {
  key: ComparisonMetric;
  label: string;
  getValue: (deal: DealForComparison) => number | undefined;
  format: (value: number) => string;
  higherIsBetter: boolean;
}

const METRIC_CONFIGS: MetricConfig[] = [
  {
    key: 'cap_rate',
    label: 'Cap Rate',
    getValue: (deal) => deal.capRate,
    format: (v) => `${v.toFixed(2)}%`,
    higherIsBetter: true,
  },
  {
    key: 'noi',
    label: 'NOI',
    getValue: (deal) => deal.noi,
    format: (v) =>
      new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
      }).format(v),
    higherIsBetter: true,
  },
  {
    key: 'price_per_sqft',
    label: 'Price / SF',
    getValue: (deal) => deal.pricePerSqft,
    format: (v) =>
      new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
      }).format(v),
    higherIsBetter: false, // Lower price per sqft is better
  },
  {
    key: 'projected_irr',
    label: 'Projected IRR',
    getValue: (deal) => deal.projectedIrr,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    higherIsBetter: true,
  },
  {
    key: 'cash_on_cash',
    label: 'Cash-on-Cash',
    getValue: (deal) => deal.cashOnCash,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    higherIsBetter: true,
  },
  {
    key: 'equity_multiple',
    label: 'Equity Multiple',
    getValue: (deal) => deal.equityMultiple,
    format: (v) => `${v.toFixed(2)}x`,
    higherIsBetter: true,
  },
  {
    key: 'total_units',
    label: 'Total Units',
    getValue: (deal) => deal.units,
    format: (v) => v.toLocaleString(),
    higherIsBetter: true,
  },
  {
    key: 'total_sf',
    label: 'Total SF',
    getValue: (deal) => deal.totalSf,
    format: (v) => `${v.toLocaleString()} SF`,
    higherIsBetter: true,
  },
  {
    key: 'occupancy_rate',
    label: 'Occupancy Rate',
    getValue: (deal) => deal.occupancyRate,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    higherIsBetter: true,
  },
];

const DEFAULT_METRICS: ComparisonMetric[] = [
  'cap_rate',
  'noi',
  'price_per_sqft',
  'projected_irr',
  'cash_on_cash',
  'equity_multiple',
  'total_units',
  'occupancy_rate',
];

export function ComparisonTable({
  deals,
  metrics = DEFAULT_METRICS,
  highlightBestWorst = true,
}: ComparisonTableProps) {
  const activeMetrics = useMemo(() => {
    return METRIC_CONFIGS.filter((config) => metrics.includes(config.key));
  }, [metrics]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Calculate best/worst values for each metric
  const metricStats = useMemo(() => {
    const stats: Record<ComparisonMetric, { best: number; worst: number }> = {} as never;

    activeMetrics.forEach((config) => {
      const values = deals
        .map((deal) => config.getValue(deal))
        .filter((v): v is number => v !== undefined && !isNaN(v));

      if (values.length > 0) {
        stats[config.key] = {
          best: config.higherIsBetter ? Math.max(...values) : Math.min(...values),
          worst: config.higherIsBetter ? Math.min(...values) : Math.max(...values),
        };
      }
    });

    return stats;
  }, [deals, activeMetrics]);

  const getCellStyle = (
    config: MetricConfig,
    value: number | undefined
  ): string => {
    if (!highlightBestWorst || value === undefined || isNaN(value)) return '';

    const stats = metricStats[config.key];
    if (!stats) return '';

    // Only highlight if there's variance between deals
    if (stats.best === stats.worst) return '';

    if (value === stats.best) {
      return 'bg-green-50 text-green-700 font-semibold';
    }
    if (value === stats.worst) {
      return 'bg-red-50 text-red-700';
    }
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
                    {deal.address.city}, {deal.address.state}
                  </div>
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {/* Property Type Row */}
          <TableRow>
            <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
              Property Type
            </TableCell>
            {deals.map((deal) => (
              <TableCell key={deal.id} className="text-center">
                {deal.propertyType}
              </TableCell>
            ))}
          </TableRow>

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

          {/* Value Row */}
          <TableRow>
            <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
              Deal Value
            </TableCell>
            {deals.map((deal) => (
              <TableCell key={deal.id} className="text-center font-semibold">
                {formatCurrency(deal.value)}
              </TableCell>
            ))}
          </TableRow>

          {/* Dynamic Metric Rows */}
          {activeMetrics.map((config) => (
            <TableRow key={config.key}>
              <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
                {config.label}
              </TableCell>
              {deals.map((deal) => {
                const value = config.getValue(deal);
                return (
                  <TableCell
                    key={deal.id}
                    className={cn('text-center', getCellStyle(config, value))}
                  >
                    {value !== undefined && !isNaN(value) ? config.format(value) : '-'}
                  </TableCell>
                );
              })}
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

          {/* Assignee Row */}
          <TableRow>
            <TableCell className="sticky left-0 bg-white z-10 font-medium text-neutral-700">
              Assignee
            </TableCell>
            {deals.map((deal) => (
              <TableCell key={deal.id} className="text-center">
                {deal.assignee}
              </TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}
