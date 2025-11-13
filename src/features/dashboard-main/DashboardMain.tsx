import { mockProperties } from '@/data/mockProperties';
import { mockTransactions } from '@/data/mockTransactions';
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils/formatters';
import { Card } from '@/components/ui/card';
import { TrendingUp, Building2, DollarSign, Percent } from 'lucide-react';

export function DashboardMain(){
  // Calculate portfolio metrics
  const totalProperties = mockProperties.length;
  const totalUnits = mockProperties.reduce((sum, p) => sum + p.propertyDetails.units, 0);
  const totalValue = mockProperties.reduce((sum, p) => sum + p.valuation.currentValue, 0);
  const totalNOI = mockProperties.reduce((sum, p) => sum + p.operations.noi, 0);
  const avgOccupancy =
    mockProperties.reduce((sum, p) => sum + p.operations.occupancy, 0) / totalProperties;
  const avgCapRate =
    mockProperties.reduce((sum, p) => sum + p.valuation.capRate, 0) / totalProperties;

  const recentTransactions = mockTransactions
    .sort((a, b) => b.date.getTime() - a.date.getTime())
    .slice(0, 10);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-page-title text-neutral-900 font-semibold">
          Portfolio Dashboard
        </h1>
        <p className="text-neutral-600 mt-1">
          Real-time performance across 12 Phoenix MSA properties
        </p>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6 shadow-card hover:shadow-card-hover transition-shadow">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-primary-50 rounded-lg">
              <DollarSign className="w-6 h-6 text-primary-500" />
            </div>
            <div className="flex items-center gap-1 text-sm text-green-600">
              <TrendingUp className="w-4 h-4" />
              +12.4%
            </div>
          </div>
          <div className="text-hero-stat text-neutral-900">
            {formatCurrency(totalValue, true)}
          </div>
          <div className="text-sm text-neutral-600 mt-1">Portfolio Value</div>
        </Card>

        <Card className="p-6 shadow-card hover:shadow-card-hover transition-shadow">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-accent-50 rounded-lg">
              <Building2 className="w-6 h-6 text-accent-500" />
            </div>
          </div>
          <div className="text-hero-stat text-neutral-900">
            {formatNumber(totalUnits)}
          </div>
          <div className="text-sm text-neutral-600 mt-1">
            Total Units • {formatPercent(avgOccupancy)} Occupied
          </div>
        </Card>

        <Card className="p-6 shadow-card hover:shadow-card-hover transition-shadow">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-50 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
            <div className="flex items-center gap-1 text-sm text-green-600">
              <TrendingUp className="w-4 h-4" />
              +8.2%
            </div>
          </div>
          <div className="text-hero-stat text-neutral-900">
            {formatCurrency(totalNOI / 12, true)}
          </div>
          <div className="text-sm text-neutral-600 mt-1">Monthly NOI</div>
        </Card>

        <Card className="p-6 shadow-card hover:shadow-card-hover transition-shadow">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <Percent className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <div className="text-hero-stat text-neutral-900">
            {formatPercent(avgCapRate)}
          </div>
          <div className="text-sm text-neutral-600 mt-1">Average Cap Rate</div>
        </Card>
      </div>

      {/* Portfolio Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Properties Table */}
        <Card className="p-6 shadow-card">
          <h2 className="text-card-title text-neutral-800 font-semibold mb-4">
            Top Performing Properties
          </h2>
          <div className="space-y-3">
            {mockProperties
              .sort((a, b) => b.performance.irr - a.performance.irr)
              .slice(0, 5)
              .map((property) => (
                <div
                  key={property.id}
                  className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors"
                >
                  <div className="flex-1">
                    <div className="font-medium text-neutral-900">
                      {property.name}
                    </div>
                    <div className="text-sm text-neutral-600">
                      {property.address.submarket} • {property.propertyDetails.units}{' '}
                      units
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-green-600">
                      {formatPercent(property.performance.irr)}
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
                className="flex items-center justify-between p-3 border-b border-neutral-100 last:border-0"
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
            const propertiesInClass = mockProperties.filter(
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
    </div>
  );
}
