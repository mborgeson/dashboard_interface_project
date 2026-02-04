import { useState, useMemo, lazy, Suspense } from 'react';
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
import { KPICard } from './components/KPICard';
import { DistributionCharts } from './components/DistributionCharts';
import { ComparisonCharts } from './components/ComparisonCharts';
import { StatCardSkeleton, ChartSkeleton } from '@/components/skeletons';

type DateRange = '30' | '90' | '365' | 'all';

/** Cash-on-Cash Return = (NOI - Annual Debt Service) / Equity */
function calcCashOnCash(p: { operations: { noi: number }; financing: { monthlyPayment: number; loanAmount: number }; acquisition: { totalInvested: number } }): number {
  const equity = p.acquisition.totalInvested - p.financing.loanAmount;
  if (equity <= 0) return 0;
  const annualDebtService = p.financing.monthlyPayment * 12;
  const preTaxCashFlow = p.operations.noi - annualDebtService;
  return preTaxCashFlow / equity;
}

export function AnalyticsPage() {
  const [dateRange, setDateRange] = useState<DateRange>('365');
  const [showReportWizard, setShowReportWizard] = useState(false);

  // Fetch properties from API
  const { data, isLoading, error } = useProperties();
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

    return filtered.length > 0 ? filtered : allProperties;
  }, [allProperties, dateRange]);

  // Calculate portfolio-wide KPIs
  const portfolioKPIs = useMemo(() => {
    if (properties.length === 0) {
      return { irr: 0, cashOnCash: 0, equityMultiple: 0, avgDSCR: 0 };
    }

    const totalEquity = properties.reduce(
      (sum, p) => sum + (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    );
    if (totalEquity === 0) {
      return { irr: 0, cashOnCash: 0, equityMultiple: 0, avgDSCR: 0 };
    }
    const weightedIRR = properties.reduce(
      (sum, p) => sum + p.performance.leveredIrr * (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;
    const weightedCashOnCash = properties.reduce(
      (sum, p) => sum + calcCashOnCash(p) * (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;
    const weightedEquityMultiple = properties.reduce(
      (sum, p) => sum + p.performance.leveredMoic * (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;

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

  // Current average occupancy (no historical time-series data available)
  const avgOccupancy = useMemo(() => {
    if (properties.length === 0) return 0;
    return properties.reduce((sum, p) => sum + p.operations.occupancy, 0) / properties.length;
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

  // NOI by submarket
  const noiBySubmarket = useMemo(() => {
    const submarketMap = properties.reduce((acc, p) => {
      const submarket = p.address.submarket;
      acc[submarket] = (acc[submarket] || 0) + p.operations.noi;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(submarketMap)
      .map(([submarket, noi]) => ({ submarket, noi }))
      .sort((a, b) => b.noi - a.noi);
  }, [properties]);

  // Property performance comparison
  const propertyPerformance = useMemo(() => {
    return properties.map(p => ({
      name: p.name,
      irr: p.performance.leveredIrr,
      cashOnCash: calcCashOnCash(p),
      capRate: p.valuation.capRate,
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

  const formatCurrency = (value: number) => {
    return `$${(value / 1000000).toFixed(2)}M`;
  };

  const formatPercentage = (value: number) => {
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
    const max = Math.max(...values);
    const min = Math.min(...values);
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
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-page-title text-primary-500">Portfolio Analytics</h1>
            <p className="text-sm text-neutral-600 mt-1">
              Comprehensive performance analysis and insights
            </p>
          </div>
        </div>

        {/* KPI Summary Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>

        {/* Charts Skeleton */}
        <div className="space-y-6">
          <div>
            <div className="h-6 w-48 bg-neutral-200 animate-pulse rounded mb-4" />
            <ChartSkeleton height={320} />
          </div>
          <div>
            <div className="h-6 w-48 bg-neutral-200 animate-pulse rounded mb-4" />
            <ChartSkeleton height={320} />
          </div>
          <div>
            <div className="h-6 w-48 bg-neutral-200 animate-pulse rounded mb-4" />
            <ChartSkeleton height={384} />
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Data</h2>
          <p className="text-red-600">
            {error instanceof Error ? error.message : 'Failed to load portfolio data'}
          </p>
          <Button
            className="mt-4"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-page-title text-primary-500">Portfolio Analytics</h1>
          <p className="text-sm text-neutral-600 mt-1">
            Comprehensive performance analysis and insights
            {dateRange !== 'all' && (
              <span className="ml-2 text-xs text-primary-600 font-medium">
                ({properties.length} of {allProperties.length} properties{properties.length === allProperties.length ? ' — showing all, none match filter' : ''})
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

      {/* KPI Summary Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Portfolio IRR"
          value={portfolioKPIs.irr}
          format="percentage"
          description="Weighted average internal rate of return"
        />
        <KPICard
          title="Cash-on-Cash Return"
          value={portfolioKPIs.cashOnCash}
          format="percentage"
          description="Weighted average annual cash return"
        />
        <KPICard
          title="Equity Multiple"
          value={portfolioKPIs.equityMultiple}
          format="decimal"
          description="Total return multiple on invested capital"
        />
        <KPICard
          title="Average DSCR"
          value={portfolioKPIs.avgDSCR}
          format="decimal"
          description="Debt service coverage ratio"
        />
      </div>

      {/* Portfolio Summary */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Portfolio Summary</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h3 className="text-sm font-medium text-neutral-600 mb-2">Total Annual Portfolio NOI</h3>
            <p className="text-3xl font-bold text-primary-700">
              ${(portfolioNOI / 1000000).toFixed(2)}M
            </p>
            <p className="text-xs text-neutral-500 mt-1">
              Based on current extraction data across {properties.filter(p => p.operations.noi > 0).length} properties
            </p>
          </div>
          <div className="bg-white rounded-lg border border-neutral-200 p-6">
            <h3 className="text-sm font-medium text-neutral-600 mb-2">Average Portfolio Occupancy</h3>
            <p className="text-3xl font-bold text-primary-700">
              {(avgOccupancy * 100).toFixed(1)}%
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
                    <TableCell className="font-medium">{property.name}</TableCell>
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
                      {formatCurrency(property.operations.noi)}
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
