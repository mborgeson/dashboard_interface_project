import { TrendingUp, DollarSign, Percent, Award } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { Property } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';

interface PerformanceTabProps {
  property: Property;
}

export function PerformanceTab({ property }: PerformanceTabProps) {
  // Generate simple performance trend data (mock data for visualization)
  const performanceData = [
    { year: 2020, value: property.acquisition.purchasePrice },
    { year: 2021, value: property.acquisition.purchasePrice * 1.08 },
    { year: 2022, value: property.acquisition.purchasePrice * 1.16 },
    { year: 2023, value: property.acquisition.purchasePrice * 1.22 },
    { year: 2024, value: property.valuation.currentValue },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Performance Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">IRR</CardTitle>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatPercent(property.performance.irr)}</div>
            <p className="text-xs text-gray-600 mt-1">Internal Rate of Return</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Equity Multiple</CardTitle>
            <Award className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary-600">{property.performance.equityMultiple.toFixed(2)}x</div>
            <p className="text-xs text-gray-600 mt-1">Total return multiplier</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Cash-on-Cash</CardTitle>
            <Percent className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-accent-600">{formatPercent(property.performance.cashOnCashReturn)}</div>
            <p className="text-xs text-gray-600 mt-1">Annual cash yield</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Return</CardTitle>
            <DollarSign className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatPercent(property.performance.totalReturnPercent)}</div>
            <p className="text-xs text-gray-600 mt-1">{formatCurrency(property.performance.totalReturnDollars)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Performance Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Return Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-sm text-gray-600 mb-2">Total Return</div>
              <div className="text-2xl font-bold text-gray-900 mb-1">
                {formatCurrency(property.performance.totalReturnDollars)}
              </div>
              <div className="text-sm text-green-600">
                +{formatPercent(property.performance.totalReturnPercent)} total return
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-2">Initial Investment</div>
              <div className="text-2xl font-bold text-gray-900 mb-1">
                {formatCurrency(property.acquisition.totalInvested)}
              </div>
              <div className="text-sm text-gray-600">
                Original equity invested
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-2">Current Equity</div>
              <div className="text-2xl font-bold text-gray-900 mb-1">
                {formatCurrency(property.valuation.currentValue - property.financing.loanAmount)}
              </div>
              <div className="text-sm text-gray-600">
                Current value - loan balance
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Performance Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Property Value Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="year"
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
                tickFormatter={(value) => `$${(value / 1000000).toFixed(0)}M`}
              />
              <Tooltip
                formatter={(value: number) => formatCurrency(value)}
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#2563eb"
                strokeWidth={2}
                dot={{ fill: '#2563eb', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Additional Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Investment Metrics Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-600 mb-1">Holding Period</div>
                <div className="text-lg font-semibold">
                  {new Date().getFullYear() - property.acquisition.date.getFullYear()} years
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Annual Appreciation</div>
                <div className="text-lg font-semibold text-green-600">
                  {formatPercent(
                    property.valuation.appreciationSinceAcquisition /
                    (new Date().getFullYear() - property.acquisition.date.getFullYear())
                  )}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Current Loan Balance</div>
                <div className="text-lg font-semibold">
                  {formatCurrency(property.financing.loanAmount)}
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-600 mb-1">Equity Position</div>
                <div className="text-lg font-semibold">
                  {formatPercent(
                    (property.valuation.currentValue - property.financing.loanAmount) /
                    property.valuation.currentValue
                  )}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Current Cap Rate</div>
                <div className="text-lg font-semibold">
                  {formatPercent(property.valuation.capRate)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Annual NOI</div>
                <div className="text-lg font-semibold">
                  {formatCurrency(property.operations.noi)}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
