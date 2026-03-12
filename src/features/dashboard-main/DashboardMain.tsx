import { useNavigate } from 'react-router-dom';
import { useProperties, selectProperties } from '@/hooks/api/useProperties';
import { useTransactionsWithMockFallback } from '@/hooks/api/useTransactions';
import { formatCurrency, formatPercent, formatPercentOrNA, formatNumber, formatNumberOrNA, shortPropertyName } from '@/lib/utils/formatters';
import { Card } from '@/components/ui/card';
import { TrendingUp, Building2, DollarSign, Percent } from 'lucide-react';
import { PropertyMap } from './components/PropertyMap';
import { PortfolioPerformanceChart } from './components/PortfolioPerformanceChart';
import { PropertyDistributionChart } from './components/PropertyDistributionChart';
import { PageLoadingState, StatCard } from '@/components/shared';
import { MarketTrendsWidget } from '@/features/market/components/widgets/MarketTrendsWidget';
import { MarketOverviewWidget } from '@/features/market/components/widgets/MarketOverviewWidget';
import { SubmarketComparisonWidget } from '@/features/market/components/widgets/SubmarketComparisonWidget';

export function DashboardMain() {
  const navigate = useNavigate();

  // Fetch properties from API
  const { data, isLoading, error } = useProperties();
  const properties = selectProperties(data);

  // Fetch transactions from API
  const { data: txnData } = useTransactionsWithMockFallback();
  const allTransactions = txnData?.transactions ?? [];

  // Calculate portfolio metrics — exclude properties with missing data (0 = missing)
  const totalProperties = properties.length;
  const totalUnits = properties.reduce((sum, p) => sum + p.propertyDetails.units, 0);
  const propertiesWithValue = properties.filter(p => p.valuation.currentValue > 0);
  const totalValue = propertiesWithValue.reduce((sum, p) => sum + p.valuation.currentValue, 0);
  const propertiesWithNOI = properties.filter(p => p.operations.noi > 0);
  const totalNOI = propertiesWithNOI.reduce((sum, p) => sum + p.operations.noi, 0);
  const propertiesWithOccupancy = properties.filter(p => p.operations.occupancy > 0);
  const avgOccupancy = propertiesWithOccupancy.length > 0
    ? propertiesWithOccupancy.reduce((sum, p) => sum + p.operations.occupancy, 0) / propertiesWithOccupancy.length
    : 0;
  const propertiesWithCapRate = properties.filter(p => p.valuation.capRate > 0);
  const avgCapRate = propertiesWithCapRate.length > 0
    ? propertiesWithCapRate.reduce((sum, p) => sum + p.valuation.capRate, 0) / propertiesWithCapRate.length
    : 0;

  const recentTransactions = [...allTransactions]
    .sort((a, b) => b.date.getTime() - a.date.getTime())
    .slice(0, 10);

  // Loading state
  if (isLoading) {
    return (
      <PageLoadingState
        title="Portfolio Dashboard"
        subtitle="Loading real-time performance data..."
        statCards={4}
        chartHeights={[300, 300]}
        chartLayout="grid"
      />
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">
            Portfolio Dashboard
          </h1>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Data</h2>
          <p className="text-red-600">
            {error instanceof Error ? error.message : 'Failed to load portfolio data'}
          </p>
          <button
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-neutral-900">
          Portfolio Dashboard
        </h1>
        <p className="text-neutral-600 mt-1">
          Real-time performance across {totalProperties} Phoenix MSA properties
        </p>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          variant="hero"
          icon={DollarSign}
          iconColor="text-primary-500"
          iconBgColor="bg-primary-50"
          label="Portfolio Value"
          value={formatCurrency(totalValue, true)}
          onClick={() => navigate('/investments')}
        />
        <StatCard
          variant="hero"
          icon={Building2}
          iconColor="text-accent-500"
          iconBgColor="bg-accent-50"
          label={`Total Units${avgOccupancy > 0 ? ` • ${formatPercent(avgOccupancy)} Occupied` : ''}`}
          value={formatNumber(totalUnits)}
          onClick={() => navigate('/investments')}
        />
        <StatCard
          variant="hero"
          icon={TrendingUp}
          iconColor="text-green-600"
          iconBgColor="bg-green-50"
          label="Monthly NOI"
          value={totalNOI > 0 ? formatCurrency(totalNOI / 12, true) : '--'}
          onClick={() => navigate('/analytics')}
        />
        <StatCard
          variant="hero"
          icon={Percent}
          iconColor="text-blue-600"
          iconBgColor="bg-blue-50"
          label="Average Cap Rate"
          value={avgCapRate > 0 ? formatPercent(avgCapRate) : '--'}
          onClick={() => navigate('/analytics')}
        />
      </div>

      {/* Portfolio Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Properties Table */}
        <Card className="p-6 shadow-card">
          <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
            Top Performing Properties
          </h2>
          <div className="space-y-3">
            {properties
              .filter((p) => p.performance.leveredIrr !== 0)
              .sort((a, b) => b.performance.leveredIrr - a.performance.leveredIrr)
              .slice(0, 5)
              .map((property) => (
                <div
                  key={property.id}
                  className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors cursor-pointer"
                  onClick={() => navigate(`/properties/${property.id}`)}
                >
                  <div className="flex-1">
                    <div className="font-medium text-neutral-900">
                      {shortPropertyName(property.name)}
                    </div>
                    <div className="text-sm text-neutral-600">
                      {property.address.city}, {property.address.state} • {property.address.submarket} • {formatNumberOrNA(property.propertyDetails.units)}{' '}
                      {property.propertyDetails.units > 0 ? 'units' : ''}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-semibold ${property.performance.leveredIrr >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatPercentOrNA(property.performance.leveredIrr)}
                    </div>
                    <div className="text-sm text-neutral-600">IRR</div>
                  </div>
                </div>
              ))}
          </div>
        </Card>

        {/* Recent Transactions */}
        <Card className="p-6 shadow-card">
          <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
            Recent Transactions
          </h2>
          <div className="space-y-3">
            {recentTransactions.map((txn) => (
              <div
                key={txn.id}
                className="flex items-center justify-between p-3 border-b border-neutral-100 last:border-0 cursor-pointer hover:bg-neutral-50 transition-colors"
                onClick={() => navigate('/transactions')}
              >
                <div className="flex-1">
                  <div className="font-medium text-neutral-900">
                    {txn.propertyName}
                  </div>
                  <div className="text-sm text-neutral-600">{txn.description}</div>
                  <div className="text-xs text-neutral-500 mt-1">
                    {txn.date.toLocaleDateString()}
                  </div>
                </div>
                <div
                  className={`font-semibold ${
                    txn.type === 'distribution'
                      ? 'text-green-600'
                      : txn.type === 'acquisition'
                      ? 'text-blue-600'
                      : 'text-orange-600'
                  }`}
                >
                  {formatCurrency(txn.amount, true)}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Property Distribution by Class */}
      <Card className="p-6 shadow-card">
        <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
          Portfolio Distribution
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {['A', 'B', 'C'].map((propertyClass) => {
            const propertiesInClass = properties.filter(
              (p) => p.propertyDetails.propertyClass === propertyClass
            );
            const count = propertiesInClass.length;
            const totalUnitsInClass = propertiesInClass.reduce(
              (sum, p) => sum + p.propertyDetails.units,
              0
            );
            const totalValueInClass = propertiesInClass.reduce(
              (sum, p) => sum + p.valuation.currentValue,
              0
            );

            return (
              <div key={propertyClass} className="p-4 bg-neutral-50 rounded-lg">
                <div className="text-2xl font-bold text-primary-500 mb-2">
                  Class {propertyClass}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Properties:</span>
                    <span className="font-semibold text-neutral-900">{count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Units:</span>
                    <span className="font-semibold text-neutral-900">
                      {formatNumber(totalUnitsInClass)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-600">Value:</span>
                    <span className="font-semibold text-neutral-900">
                      {formatCurrency(totalValueInClass, true)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Performance and Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Performance Chart */}
        <Card className="p-6 shadow-card">
          <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
            Top Properties by NOI
          </h2>
          <PortfolioPerformanceChart properties={properties} />
        </Card>

        {/* Property Distribution by Class Chart */}
        <Card className="p-6 shadow-card">
          <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
            Distribution by Property Class
          </h2>
          <PropertyDistributionChart type="class" properties={properties} />
        </Card>
      </div>

      {/* Property Distribution by Submarket Chart */}
      <Card className="p-6 shadow-card">
        <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
          Distribution by Submarket
        </h2>
        <PropertyDistributionChart type="submarket" properties={properties} />
      </Card>

      {/* Market Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MarketOverviewWidget variant="compact" className="shadow-card" />
        <SubmarketComparisonWidget
          className="shadow-card"
          showChart={true}
          showTable={false}
        />
      </div>

      {/* Market Trends */}
      <MarketTrendsWidget className="bg-white rounded-lg border border-neutral-200 shadow-card" />

      {/* Property Map */}
      <Card className="p-6 shadow-card">
        <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
          Property Locations
        </h2>
        <PropertyMap properties={properties} />
      </Card>
    </div>
  );
}
