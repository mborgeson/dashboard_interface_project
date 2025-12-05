import { useState, useMemo } from 'react';
import { mockProperties } from '@/data/mockProperties';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Download, Calendar } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { KPICard } from './components/KPICard';
import { PerformanceCharts } from './components/PerformanceCharts';
import { DistributionCharts } from './components/DistributionCharts';
import { ComparisonCharts } from './components/ComparisonCharts';

type DateRange = '30' | '90' | '365' | 'all';

export function AnalyticsPage() {
  const [dateRange, setDateRange] = useState<DateRange>('365');

  // Calculate portfolio-wide KPIs
  const portfolioKPIs = useMemo(() => {
    const totalEquity = mockProperties.reduce(
      (sum, p) => sum + (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    );
    const weightedIRR = mockProperties.reduce(
      (sum, p) => sum + p.performance.irr * (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;
    const weightedCashOnCash = mockProperties.reduce(
      (sum, p) => sum + p.performance.cashOnCashReturn * (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;
    const weightedEquityMultiple = mockProperties.reduce(
      (sum, p) => sum + p.performance.equityMultiple * (p.acquisition.totalInvested - p.financing.loanAmount),
      0
    ) / totalEquity;
    
    // Calculate average DSCR (Debt Service Coverage Ratio)
    const avgDSCR = mockProperties.reduce((sum, p) => {
      const annualNOI = p.operations.noi;
      const annualDebtService = p.financing.monthlyPayment * 12;
      const dscr = annualNOI / annualDebtService;
      return sum + dscr;
    }, 0) / mockProperties.length;

    return {
      irr: weightedIRR,
      cashOnCash: weightedCashOnCash,
      equityMultiple: weightedEquityMultiple,
      avgDSCR,
    };
  }, []);

  // Generate NOI trend data (last 12 months)
  const noiTrendData = useMemo(() => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const currentMonth = new Date().getMonth();
    
    return months.map((month, idx) => {
      // Calculate month offset from current
      const monthOffset = idx - currentMonth;
      const portfolioNOI = mockProperties.reduce((sum, p) => sum + p.operations.noi, 0);
      
      // Add some realistic variation (±5%)
      const variation = 1 + (Math.sin(monthOffset * 0.5) * 0.05);
      const monthlyNOI = (portfolioNOI / 12) * variation;
      
      return {
        month,
        noi: Math.round(monthlyNOI),
      };
    });
  }, []);

  // Generate occupancy trend data (last 12 months)
  const occupancyTrendData = useMemo(() => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const currentMonth = new Date().getMonth();
    const avgOccupancy = mockProperties.reduce((sum, p) => sum + p.operations.occupancy, 0) / mockProperties.length;
    
    return months.map((month, idx) => {
      const monthOffset = idx - currentMonth;
      // Slight seasonal variation
      const variation = Math.sin(monthOffset * 0.3) * 0.02;
      
      return {
        month,
        occupancy: Math.min(0.99, Math.max(0.88, avgOccupancy + variation)),
      };
    });
  }, []);

  // Value by property class
  const valueByClass = useMemo(() => {
    const classMap = mockProperties.reduce((acc, p) => {
      const cls = `Class ${p.propertyDetails.propertyClass}`;
      acc[cls] = (acc[cls] || 0) + p.valuation.currentValue;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(classMap)
      .map(([cls, value]) => ({ class: cls, value }))
      .sort((a, b) => a.class.localeCompare(b.class));
  }, []);

  // NOI by submarket
  const noiBySubmarket = useMemo(() => {
    const submarketMap = mockProperties.reduce((acc, p) => {
      const submarket = p.address.submarket;
      acc[submarket] = (acc[submarket] || 0) + p.operations.noi;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(submarketMap)
      .map(([submarket, noi]) => ({ submarket, noi }))
      .sort((a, b) => b.noi - a.noi);
  }, []);

  // Property performance comparison
  const propertyPerformance = useMemo(() => {
    return mockProperties.map(p => ({
      name: p.name,
      irr: p.performance.irr,
      cashOnCash: p.performance.cashOnCashReturn,
      capRate: p.valuation.capRate,
    }));
  }, []);

  // Risk vs Return scatter data
  const riskReturnData = useMemo(() => {
    return mockProperties.map(p => {
      // Calculate risk score based on occupancy variance from optimal (96%)
      const occupancyVariance = Math.abs(p.operations.occupancy - 0.96);
      // Include property class as risk factor (C=higher risk)
      const classRisk = p.propertyDetails.propertyClass === 'C' ? 0.3 : 
                        p.propertyDetails.propertyClass === 'B' ? 0.15 : 0;
      const riskScore = (occupancyVariance * 10) + classRisk + (Math.random() * 0.1);
      
      return {
        name: p.name,
        risk: riskScore,
        return: p.performance.irr,
        size: p.valuation.currentValue,
      };
    });
  }, []);

  // Table data with sorting
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  const sortedProperties = useMemo(() => {
    const sorted = [...mockProperties];
    if (sortConfig) {
      sorted.sort((a, b) => {
        let aVal: any, bVal: any;
        
        switch (sortConfig.key) {
          case 'name':
            aVal = a.name;
            bVal = b.name;
            break;
          case 'irr':
            aVal = a.performance.irr;
            bVal = b.performance.irr;
            break;
          case 'cashOnCash':
            aVal = a.performance.cashOnCashReturn;
            bVal = b.performance.cashOnCashReturn;
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
  }, [sortConfig]);

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
    const values = mockProperties.map(p => {
      switch (key) {
        case 'irr': return p.performance.irr;
        case 'cashOnCash': return p.performance.cashOnCashReturn;
        case 'occupancy': return p.operations.occupancy;
        default: return 0;
      }
    });
    const max = Math.max(...values);
    const min = Math.min(...values);
    return { max, min };
  };

  const highlightCell = (value: number, key: string) => {
    const { max, min } = getBestWorst(key);
    if (value === max) return 'bg-green-50 font-semibold text-green-700';
    if (value === min) return 'bg-red-50 font-semibold text-red-700';
    return '';
  };

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
          <Button className="flex items-center gap-2">
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
          trend={5.2}
          description="Weighted average internal rate of return"
        />
        <KPICard
          title="Cash-on-Cash Return"
          value={portfolioKPIs.cashOnCash}
          format="percentage"
          trend={3.1}
          description="Weighted average annual cash return"
        />
        <KPICard
          title="Equity Multiple"
          value={portfolioKPIs.equityMultiple}
          format="decimal"
          trend={2.8}
          description="Total return multiple on invested capital"
        />
        <KPICard
          title="Average DSCR"
          value={portfolioKPIs.avgDSCR}
          format="decimal"
          description="Debt service coverage ratio"
        />
      </div>

      {/* Performance Charts */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Performance Trends</h2>
        <PerformanceCharts noiData={noiTrendData} occupancyData={occupancyTrendData} />
      </div>

      {/* Distribution Charts */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Portfolio Distribution</h2>
        <DistributionCharts valueByClass={valueByClass} noiBySubmarket={noiBySubmarket} />
      </div>

      {/* Comparison Charts */}
      <div>
        <h2 className="text-section-title text-primary-500 mb-4">Property Analysis</h2>
        <ComparisonCharts propertyPerformance={propertyPerformance} riskReturn={riskReturnData} />
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
                    <TableCell className={`text-right ${highlightCell(property.performance.irr, 'irr')}`}>
                      {formatPercentage(property.performance.irr)}
                    </TableCell>
                    <TableCell className={`text-right ${highlightCell(property.performance.cashOnCashReturn, 'cashOnCash')}`}>
                      {formatPercentage(property.performance.cashOnCashReturn)}
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
    </div>
  );
}
