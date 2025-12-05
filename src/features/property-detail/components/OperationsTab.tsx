import { useState } from 'react';
import { DollarSign, TrendingDown } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { Property } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils/formatters';

interface OperationsTabProps {
  property: Property;
}

type Period = 'monthly' | 'annual';

export function OperationsTab({ property }: OperationsTabProps) {
  const [period, setPeriod] = useState<Period>('monthly');
  const multiplier = period === 'annual' ? 12 : 1;

  const totalRevenue = (property.operations.monthlyRevenue + property.operations.otherIncome) * multiplier;
  const totalExpenses = property.operations.monthlyExpenses.total * multiplier;
  const noi = property.operations.noi * (period === 'annual' ? 1 : 1 / 12);

  // Expense breakdown for pie chart
  const expenseData = [
    { name: 'Property Tax', value: property.operations.monthlyExpenses.propertyTax, color: '#3B82F6' },
    { name: 'Insurance', value: property.operations.monthlyExpenses.insurance, color: '#8B5CF6' },
    { name: 'Utilities', value: property.operations.monthlyExpenses.utilities, color: '#10B981' },
    { name: 'Management', value: property.operations.monthlyExpenses.management, color: '#F59E0B' },
    { name: 'Repairs', value: property.operations.monthlyExpenses.repairs, color: '#EF4444' },
    { name: 'Payroll', value: property.operations.monthlyExpenses.payroll, color: '#06B6D4' },
    { name: 'Marketing', value: property.operations.monthlyExpenses.marketing, color: '#EC4899' },
    { name: 'Other', value: property.operations.monthlyExpenses.other, color: '#6B7280' },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Period Toggle */}
      <div className="flex justify-end">
        <div className="inline-flex rounded-lg border border-gray-300 bg-white p-1">
          <button
            onClick={() => setPeriod('monthly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              period === 'monthly'
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setPeriod('annual')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              period === 'annual'
                ? 'bg-primary-600 text-white'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            Annual
          </button>
        </div>
      </div>

      {/* Revenue & NOI Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-green-600" />
              <CardTitle>Total Revenue</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatCurrency(totalRevenue)}</div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Rental Income</span>
                <span className="font-medium">{formatCurrency(property.operations.monthlyRevenue * multiplier)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Other Income</span>
                <span className="font-medium">{formatCurrency(property.operations.otherIncome * multiplier)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-red-600" />
              <CardTitle>Total Expenses</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{formatCurrency(totalExpenses)}</div>
            <div className="mt-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Operating Expense Ratio</span>
                <span className="font-medium">{formatPercent(property.operations.operatingExpenseRatio)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-primary-50">
          <CardHeader>
            <CardTitle className="text-primary-900">Net Operating Income</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-primary-900">{formatCurrency(noi)}</div>
            <div className="mt-4">
              <div className="flex justify-between text-sm">
                <span className="text-primary-700">NOI Margin</span>
                <span className="font-medium text-primary-900">
                  {formatPercent(noi / totalRevenue)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Expense Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Expense Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={expenseData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {expenseData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => formatCurrency(value * multiplier)}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Expense Details Table */}
        <Card>
          <CardHeader>
            <CardTitle>Expense Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {expenseData.map((expense) => (
                <div key={expense.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: expense.color }}
                    />
                    <span className="text-sm text-gray-700">{expense.name}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold">{formatCurrency(expense.value * multiplier)}</div>
                    <div className="text-xs text-gray-500">
                      {formatPercent(expense.value / property.operations.monthlyExpenses.total)} of total
                    </div>
                  </div>
                </div>
              ))}
              <div className="pt-3 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900">Total Expenses</span>
                  <span className="text-sm font-bold text-gray-900">{formatCurrency(totalExpenses)}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Operational Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Operational Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-gray-600 mb-1">Occupancy Rate</div>
              <div className="text-lg font-semibold">{formatPercent(property.operations.occupancy)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Average Rent</div>
              <div className="text-lg font-semibold">{formatCurrency(property.operations.averageRent)}/month</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Rent Per Sq Ft</div>
              <div className="text-lg font-semibold">{formatCurrency(property.operations.rentPerSqft)}/sq ft</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Occupied Units</div>
              <div className="text-lg font-semibold">
                {Math.round(property.propertyDetails.units * property.operations.occupancy)} / {property.propertyDetails.units}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
