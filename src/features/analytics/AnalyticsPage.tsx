import { useState, useMemo, lazy, Suspense } from 'react';
import { shortPropertyName } from '@/lib/utils/formatters';
import { useProperties, selectProperties } from '@/hooks/api/useProperties';
import { Button } from '@/components/ui/button';
import { Download, Calendar } from 'lucide-react';
import { MarketOverviewWidget } from '@/features/market/components/widgets/MarketOverviewWidget';
import { EconomicIndicatorsWidget } from '@/features/market/components/widgets/EconomicIndicatorsWidget';

// Lazy load ReportWizard modal for code splitting
const ReportWizard = lazy(() =>
  import('@/features/reporting-suite/components/ReportWizard/ReportWizard').then(m => ({ default: m.ReportWizard }))
);
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { DistributionCharts } from './components/DistributionCharts';
import { ComparisonCharts } from './components/ComparisonCharts';
import { PageLoadingState, StatCard } from '@/components/shared';

type DateRange = '30' | '90' | '365' | 'all';

/** Cash-on-Cash Return = (NOI - Annual Debt Service) / Equity */
function calcCashOnCash(p: { operations: { noi: number }; financing: { monthlyPayment: number; loanAmount: number }; acquisition: { totalInvested: number } }): number {
  const equity = p.acquisition.totalInvested - p.financing.loanAmount;
  if (equity <= 0) return 0;
  const annualDebtService = p.financing.monthlyPayment * 12;
  const preTaxCashFlow = p.operations.noi - annualDebtService;
  return preTaxCashFlow / equity;
}

/** Equity-weighted average, skipping items where weight <= 0. Returns 0 if no valid items. */
function weightedAvg<T>(items: T[], valueFn: (item: T) => number, weightFn: (item: T) => number): number {
  let sumProduct = 0;
  let sumWeight = 0;
  for (const item of items) {
    const w = weightFn(item);
    if (w <= 0) continue;
    sumProduct += valueFn(item) * w;
    sumWeight += w;
  }
  return sumWeight > 0 ? sumProduct / sumWeight : 0;
}

export function AnalyticsPage() {
  const [dateRange, setDateRange] = useState<DateRange>('all');
  const [showReportWizard, setShowReportWizard] = useState(false);

  // Fetch properties from API
  const { data, isLoading, error, refetch } = useProperties();
  const allProperties = selectProperties(data);

  // Filter properties by date range based on acquisition date
  const properties = useMemo(() => {
    if (dateRange === 'all') return allProperties;

    const now = new Date();
    const daysAgo = parseInt(dateRange, 10);
    const cutoff = new Date(now.getTime() - daysAgo * 86400000);

    const filtered = allProperties.filter(p => {
      const acqDate = new Date(p.acquisition.date);
      return acqDate >= cutoff;
    });

    return filtered;
  }, [allProperties, dateRange]);

  // Calculate portfolio-wide KPIs
  const portfolioKPIs = useMemo(() => {
    if (properties.length === 0) {
      return { irr: 0, cashOnCash: 0, equityMultiple: 0, avgDSCR: 0 };
    }

    const equity = (p: { acquisition: { totalInvested: number }; financing: { loanAmount: number } }) =>
      p.acquisition.totalInvested - p.financing.loanAmount;

    // Filter out properties with missing data (undefined from safeOptionalNum)
    const withIRR = properties.filter(p => p.performance.leveredIrr != null);
    const withMOIC = properties.filter(p => p.performance.leveredMoic != null);
    const withCashFlow = properties.filter(p => p.operations.noi != null);

    const weightedIRR = weightedAvg(withIRR, p => p.performance.leveredIrr, equity);
    const weightedCashOnCash = weightedAvg(withCashFlow, calcCashOnCash, equity);
    const weightedEquityMultiple = weightedAvg(withMOIC, p => p.performance.leveredMoic, equity);

    // Calculate average DSCR (Debt Service Coverage Ratio)
    const propertiesWithDebt = properties.filter(p => p.financing.monthlyPayment > 0);
    const avgDSCR = propertiesWithDebt.length > 0
      ? propertiesWithDebt.reduce((sum, p) => {
          const annualNOI = p.operations.noi;
          const annualDebtService = p.financing.monthlyPayment * 12;
          return sum + (annualNOI / annualDebtService);
        }, 0) / propertiesWithDebt.length
      : 0;

    return {
      irr: weightedIRR,
      cashOnCash: weightedCashOnCash,
      equityMultiple: weightedEquityMultiple,
      avgDSCR,
    };
  }, [properties]);

  // Current portfolio NOI (no historical time-series data available)
  const portfolioNOI = useMemo(() => {
    return properties.reduce((sum, p) => sum + p.operations.noi, 0);
  }, [properties]);

  // Current average occupancy — exclude properties with missing occupancy
  const avgOccupancy = useMemo(() => {
    const withOccupancy = properties.filter(p => p.operations.occupancy != null);
    if (withOccupancy.length === 0) return 0;
    return withOccupancy.reduce((sum, p) => sum + (p.operations.occupancy ?? 0), 0) / withOccupancy.length;
  }, [properties]);


  // Value by property class
  const valueByClass = useMemo(() => {
    const classMap = properties.reduce((acc, p) => {
      const cls = `Class ${p.propertyDetails.propertyClass}`;
      acc[cls] = (acc[cls] || 0) + p.valuation.currentValue;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(classMap)
      .map(([cls, value]) => ({ class: cls, value }))
      .sort((a, b) => a.class.localeCompare(b.class));
  }, [properties]);

  // NOI by submarket — exclude properties with missing NOI
  const noiBySubmarket = useMemo(() => {
    const submarketMap = properties
      .filter(p => p.operations.noi != null && p.operations.noi > 0)
      .reduce((acc, p) => {
        const submarket = p.address.submarket;
        acc[submarket] = (acc[submarket] || 0) + (p.operations.noi ?? 0);
        return acc;
      }, {} as Record<string, number>);

    return Object.entries(submarketMap)
      .map(([submarket, noi]) => ({ submarket, noi }))
      .sort((a, b) => b.noi - a.noi);
  }, [properties]);

  // Property performance comparison — exclude properties with no financial data
  const propertyPerformance = useMemo(() => {
    return properties
      .filter(p => p.performance.leveredIrr != null || p.valuation.capRate != null || calcCashOnCash(p) !== 0)
      .map(p => ({
        name: p.name,
        irr: p.performance.leveredIrr ?? 0,
        cashOnCash: calcCashOnCash(p),
        capRate: p.valuation.capRate ?? 0,
      }));
  }, [properties]);

  // Cap Rate vs DSCR data for property analysis
  const capRateDscrData = useMemo(() => {
    return properties
      .filter(p => p.financing.monthlyPayment > 0)
      .map(p => {
        const annualDebtService = p.financing.monthlyPayment * 12;
        const dscr = annualDebtService > 0 ? p.operations.noi / annualDebtService : 0;
        return {
          name: p.name,
          capRate: p.valuation.capRate * 100,
          dscr: parseFloat(dscr.toFixed(2)),
          noi: p.operations.noi,
          propertyClass: p.propertyDetails.propertyClass,
          value: p.valuation.currentValue,
        };
      })
      .sort((a, b) => b.capRate - a.capRate);
  }, [properties]);

  // Table data with sorting
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  const sortedProperties = useMemo(() => {
    const sorted = [...properties];
    if (sortConfig) {
      sorted.sort((a, b) => {
        let aVal: string | number;
        let bVal: string | number;

        switch (sortConfig.key) {
          case 'name':
            aVal = a.name;
            bVal = b.name;
            break;
          case 'irr':
            aVal = a.performance.leveredIrr;
            bVal = b.performance.leveredIrr;
            break;
          case 'cashOnCash':
            aVal = calcCashOnCash(a);
            bVal = calcCashOnCash(b);
            break;
          case 'capRate':
            aVal = a.valuation.capRate;
            bVal = b.valuation.capRate;
            break;
          case 'occupancy':
            aVal = a.operations.occupancy;
            bVal = b.operations.occupancy;
            break;
          case 'noi':
            aVal = a.operations.noi;
            bVal = b.operations.noi;
            break;
          default:
            return 0;
        }

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sorted;
  }, [properties, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig(current => {
      if (!current || current.key !== key) {
        return { key, direction: 'desc' };
      }
      if (current.direction === 'desc') {
        return { key, direction: 'asc' };
      }
      return null;
    });
  };

  const formatCurrencyCompact = (value: number) => {
    if (value == null || value === 0) return 'N/A';
    return `$${(value / 1000000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}M`;
  };

  const formatPercentage = (value: number) => {
    if (value == null || value === 0) return 'N/A';
    return `${(value * 100).toFixed(2)}%`;
  };

  const getSortIcon = (key: string) => {
    if (!sortConfig || sortConfig.key !== key) return '⇅';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };

  const getBestWorst = (key: string) => {
    const values = properties.map(p => {
      switch (key) {
        case 'irr': return p.performance.leveredIrr;
        case 'cashOnCash': return calcCashOnCash(p);
        case 'occupancy': return p.operations.occupancy;
        default: return 0;
      }
    });
    // Exclude zero values (missing data) from best/worst determination
    const nonZero = values.filter(v => v !== 0);
    if (nonZero.length === 0) return { max: 0, min: 0 };
    const max = Math.max(...nonZero);
    const min = Math.min(...nonZero);
    return { max, min };
  };

  const highlightCell = (value: number, key: string) => {
    if (properties.length === 0) return '';
    const { max, min } = getBestWorst(key);
    if (value === max) return 'bg-green-50 font-semibold text-green-700';
    if (value === min) return 'bg-red-50 font-semibold text-red-700';
    return '';
  };

  // Show loading state
  if (isLoading) {
    return (
      <PageLoadingState
        title="Portfolio Analytics"
        subtitle="Comprehensive performance analysis and insights"
        titleClassName="text-page-title text-primary-500"
        statCards={4}
        chartHeights={[320, 320, 384]}
        className=""
      />
    );
  }

  // Show error state
  if (error) {
    return (
      <div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Data</h2>
          <p className="text-red-600">
            {error instanceof Error ? error.message : 'Failed to load portfolio data'}
          </p>
          <Button
            className="mt-4"
            onClick={() => refetch()}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">Portfolio Analytics</h1>
          <p className="text-sm text-neutral-600 mt-1">
            Comprehensive performance analysis and insights
            {dateRange !== 'all' && (
              <span className="ml-2 text-xs text-primary-600 font-medium">
                ({properties.length} of {allProperties.length} properties)
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-neutral-500" />
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as DateRange)}
              className="border border-neutral-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="30">Last 30 Days</option>
              <option value="90">Last 90 Days</option>
              <option value="365">Last Year</option>
              <option value="all">All Time</option>
            </select>
          </div>
          <Button className="flex items-center gap-2" onClick={() => setShowReportWizard(true)}>
            <Download className="h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Empty state when date filter matches nothing */}
      {properties.length === 0 && dateRange !== 'all' && (
        <div className="text-center py-8 text-neutral-500 bg-white rounded-lg border border-neutral-200">
          No properties match the selected date range. Try a wider range or select &ldquo;All Time&rdquo;.
        </div>
      )}

      {/* KPI Summary Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Portfolio IRR"
          value={portfolioKPIs.irr === 0 ? 'N/A' : `${(portfolioKPIs.irr * 100).toFixed(2)}%`}
          subtitle="Weighted average internal rate of return"
        />
        <StatCard
          label="Cash-on-Cash Return"
          value={portfolioKPIs.cashOnCash === 0 ? 'N/A' : `${(portfolioKPIs.cashOnCash * 100).toFixed(2)}%`}
          subtitle="Weighted average annual cash return"
        />
        <StatCard
          label="Equity Multiple"
          value={portfolioKPIs.equityMultiple === 0 ? 'N/A' : portfolioKPIs.equityMultiple.toFixed(2)}
          subtitle="Total return multiple on invested capital"
        />
        <StatCard
          label="Average DSCR"
          value={portfolioKPIs.avgDSCR === 0 ? 'N/A' : portfolioKPIs.avgDSCR.toFixed(2)}
          subtitle="Debt service coverage ratio"
        />
      </div>

      {/* Portfolio Summary */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Portfolio Summary</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h3 className="text-sm font-medium text-neutral-600 mb-2">Total Annual Portfolio NOI</h3>
            <p className="text-3xl font-bold text-primary-700">
              {portfolioNOI > 0 ? `$${(portfolioNOI / 1000000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}M` : 'N/A'}
            </p>
            <p className="text-xs text-neutral-500 mt-1">
              Based on current extraction data across {properties.filter(p => p.operations.noi > 0).length} properties
            </p>
          </div>
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h3 className="text-sm font-medium text-neutral-600 mb-2">Average Portfolio Occupancy</h3>
            <p className="text-3xl font-bold text-primary-700">
              {avgOccupancy > 0 ? `${(avgOccupancy * 100).toFixed(1)}%` : 'N/A'}
            </p>
            <p className="text-xs text-neutral-500 mt-1">
              Based on current extraction data across {properties.filter(p => p.operations.occupancy > 0).length} properties
            </p>
          </div>
        </div>
      </div>

      {/* Distribution Charts */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Portfolio Distribution</h2>
        <DistributionCharts valueByClass={valueByClass} noiBySubmarket={noiBySubmarket} />
      </div>

      {/* Comparison Charts */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Property Analysis</h2>
        <ComparisonCharts propertyPerformance={propertyPerformance} capRateDscr={capRateDscrData} />
      </div>

      {/* Market Insights */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Market Insights</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <MarketOverviewWidget variant="compact" />
          <EconomicIndicatorsWidget columns={2} showSparklines={false} />
        </div>
      </div>

      {/* Property Comparison Table */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Property Performance Comparison</h2>
        <div className="bg-white rounded-lg border border-neutral-200 overflow-hidden">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer hover:bg-neutral-50"
                    onClick={() => handleSort('name')}
                  >
                    Property {getSortIcon('name')}
                  </TableHead>
                  <TableHead>Class</TableHead>
                  <TableHead>Submarket</TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-neutral-50"
                    onClick={() => handleSort('irr')}
                  >
                    IRR {getSortIcon('irr')}
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-neutral-50"
                    onClick={() => handleSort('cashOnCash')}
                  >
                    Cash-on-Cash {getSortIcon('cashOnCash')}
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-neutral-50"
                    onClick={() => handleSort('capRate')}
                  >
                    Cap Rate {getSortIcon('capRate')}
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-neutral-50"
                    onClick={() => handleSort('occupancy')}
                  >
                    Occupancy {getSortIcon('occupancy')}
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer hover:bg-neutral-50"
                    onClick={() => handleSort('noi')}
                  >
                    Annual NOI {getSortIcon('noi')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedProperties.map((property) => (
                  <TableRow key={property.id}>
                    <TableCell className="font-medium">{shortPropertyName(property.name)}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-700">
                        Class {property.propertyDetails.propertyClass}
                      </span>
                    </TableCell>
                    <TableCell className="text-neutral-600">{property.address.submarket}</TableCell>
                    <TableCell className={`text-right ${highlightCell(property.performance.leveredIrr, 'irr')}`}>
                      {formatPercentage(property.performance.leveredIrr)}
                    </TableCell>
                    <TableCell className={`text-right ${highlightCell(calcCashOnCash(property), 'cashOnCash')}`}>
                      {formatPercentage(calcCashOnCash(property))}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatPercentage(property.valuation.capRate)}
                    </TableCell>
                    <TableCell className={`text-right ${highlightCell(property.operations.occupancy, 'occupancy')}`}>
                      {formatPercentage(property.operations.occupancy)}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrencyCompact(property.operations.noi)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
        <p className="text-xs text-neutral-500 mt-3">
          <span className="inline-block w-3 h-3 bg-green-50 border border-green-200 mr-1"></span>
          Best performer |
          <span className="inline-block w-3 h-3 bg-red-50 border border-red-200 mx-1"></span>
          Worst performer
        </p>
      </div>

      {/* Report Wizard Dialog - Lazy loaded */}
      {showReportWizard && (
        <Suspense fallback={null}>
          <ReportWizard
            open={showReportWizard}
            onOpenChange={setShowReportWizard}
          />
        </Suspense>
      )}
    </div>
  );
}
