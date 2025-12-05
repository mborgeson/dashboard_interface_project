import type { YearlyProjection } from '@/types';
import {
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Area,
} from 'recharts';

interface ProjectionsTabProps {
  projections: YearlyProjection[];
}

function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

function formatTableCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

const chartColors = {
  noi: '#059669',
  cashFlow: '#3b82f6',
  equity: '#8b5cf6',
  propertyValue: '#f59e0b',
  loanBalance: '#ef4444',
  debtService: '#6b7280',
};

export function ProjectionsTab({ projections }: ProjectionsTabProps) {
  const chartData = projections.map((p) => ({
    year: `Year ${p.year}`,
    yearNum: p.year,
    noi: p.noi,
    cashFlow: p.cashFlow,
    cumulativeCashFlow: p.cumulativeCashFlow,
    propertyValue: p.propertyValue,
    loanBalance: p.loanBalance,
    equity: p.equity,
    grossIncome: p.grossIncome,
    operatingExpenses: p.operatingExpenses,
  }));

  return (
    <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-2">
      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* NOI & Cash Flow Chart */}
        <div className="bg-neutral-50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-neutral-800 mb-4">
            NOI & Cash Flow Projections
          </h4>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: number) => formatTableCurrency(value)}
                contentStyle={{ fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="noi" name="NOI" fill={chartColors.noi} radius={[4, 4, 0, 0]} />
              <Line
                type="monotone"
                dataKey="cashFlow"
                name="Cash Flow"
                stroke={chartColors.cashFlow}
                strokeWidth={2}
                dot={{ fill: chartColors.cashFlow, r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Equity Build Chart */}
        <div className="bg-neutral-50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-neutral-800 mb-4">
            Property Value & Equity Build
          </h4>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: number) => formatTableCurrency(value)}
                contentStyle={{ fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area
                type="monotone"
                dataKey="equity"
                name="Equity"
                fill={chartColors.equity}
                fillOpacity={0.3}
                stroke={chartColors.equity}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="propertyValue"
                name="Property Value"
                stroke={chartColors.propertyValue}
                strokeWidth={2}
                dot={{ fill: chartColors.propertyValue, r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="loanBalance"
                name="Loan Balance"
                stroke={chartColors.loanBalance}
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ fill: chartColors.loanBalance, r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cumulative Cash Flow Chart */}
      <div className="bg-neutral-50 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-neutral-800 mb-4">
          Cumulative Cash Flow
        </h4>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={formatCurrency} tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value: number) => formatTableCurrency(value)}
              contentStyle={{ fontSize: 12 }}
            />
            <Bar
              dataKey="cumulativeCashFlow"
              name="Cumulative Cash Flow"
              fill={chartColors.cashFlow}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed Projection Table */}
      <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-200">
          <h4 className="text-sm font-semibold text-neutral-800">
            Year-by-Year Projection Details
          </h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50">
                <th className="px-3 py-2 text-left font-medium text-neutral-600">Year</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">Gross Income</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">Vacancy</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">EGI</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">OpEx</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">NOI</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">Debt Svc</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">Cash Flow</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">Property Value</th>
                <th className="px-3 py-2 text-right font-medium text-neutral-600">Equity</th>
              </tr>
            </thead>
            <tbody>
              {projections.map((p, idx) => (
                <tr
                  key={p.year}
                  className={idx % 2 === 0 ? 'bg-white' : 'bg-neutral-50'}
                >
                  <td className="px-3 py-2 font-medium text-neutral-900">{p.year}</td>
                  <td className="px-3 py-2 text-right text-neutral-700">
                    {formatTableCurrency(p.grossIncome)}
                  </td>
                  <td className="px-3 py-2 text-right text-error-600">
                    ({formatTableCurrency(p.vacancy)})
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-700">
                    {formatTableCurrency(p.effectiveGrossIncome)}
                  </td>
                  <td className="px-3 py-2 text-right text-error-600">
                    ({formatTableCurrency(p.operatingExpenses)})
                  </td>
                  <td className="px-3 py-2 text-right font-medium text-success-600">
                    {formatTableCurrency(p.noi)}
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-600">
                    ({formatTableCurrency(p.debtService)})
                  </td>
                  <td className={`px-3 py-2 text-right font-medium ${p.cashFlow >= 0 ? 'text-success-600' : 'text-error-600'}`}>
                    {formatTableCurrency(p.cashFlow)}
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-700">
                    {formatTableCurrency(p.propertyValue)}
                  </td>
                  <td className="px-3 py-2 text-right font-medium text-primary-600">
                    {formatTableCurrency(p.equity)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
