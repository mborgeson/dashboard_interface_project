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

      {/* Detailed Projection Table - Transposed (Years as columns, Line Items as rows) */}
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
                <th className="px-3 py-2 text-left font-medium text-neutral-600 sticky left-0 bg-neutral-50 min-w-[160px]">
                  Line Item
                </th>
                {projections.map((p) => (
                  <th key={p.year} className="px-3 py-2 text-right font-medium text-neutral-600 min-w-[100px]">
                    Year {p.year}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Gross Potential Rent */}
              <tr className="bg-white">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-white">
                  Gross Potential Rent
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-neutral-700">
                    {formatTableCurrency(p.grossPotentialRent)}
                  </td>
                ))}
              </tr>
              {/* Loss to Lease */}
              <tr className="bg-neutral-50">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-neutral-50">
                  Loss to Lease
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-error-600">
                    ({formatTableCurrency(p.lossToLease)})
                  </td>
                ))}
              </tr>
              {/* Gross Income */}
              <tr className="bg-white">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-white">
                  Gross Income
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-neutral-700">
                    {formatTableCurrency(p.grossIncome)}
                  </td>
                ))}
              </tr>
              {/* Vacancy */}
              <tr className="bg-neutral-50">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-neutral-50">
                  Vacancy
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-error-600">
                    ({formatTableCurrency(p.vacancy)})
                  </td>
                ))}
              </tr>
              {/* Concessions */}
              <tr className="bg-white">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-white">
                  Concessions
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-error-600">
                    ({formatTableCurrency(p.concessions)})
                  </td>
                ))}
              </tr>
              {/* Bad Debt */}
              <tr className="bg-neutral-50">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-neutral-50">
                  Bad Debt
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-error-600">
                    ({formatTableCurrency(p.badDebt)})
                  </td>
                ))}
              </tr>
              {/* EGI */}
              <tr className="bg-white border-t border-neutral-200">
                <td className="px-3 py-2 font-semibold text-neutral-900 sticky left-0 bg-white">
                  Effective Gross Income
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right font-semibold text-neutral-900">
                    {formatTableCurrency(p.effectiveGrossIncome)}
                  </td>
                ))}
              </tr>
              {/* Operating Expenses */}
              <tr className="bg-neutral-50">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-neutral-50">
                  Operating Expenses
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-error-600">
                    ({formatTableCurrency(p.operatingExpenses)})
                  </td>
                ))}
              </tr>
              {/* NOI */}
              <tr className="bg-white border-t border-neutral-200">
                <td className="px-3 py-2 font-semibold text-neutral-900 sticky left-0 bg-white">
                  Net Operating Income
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right font-semibold text-success-600">
                    {formatTableCurrency(p.noi)}
                  </td>
                ))}
              </tr>
              {/* Debt Service */}
              <tr className="bg-neutral-50">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-neutral-50">
                  Debt Service
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-neutral-600">
                    ({formatTableCurrency(p.debtService)})
                  </td>
                ))}
              </tr>
              {/* Cash Flow */}
              <tr className="bg-white border-t border-neutral-200">
                <td className="px-3 py-2 font-semibold text-neutral-900 sticky left-0 bg-white">
                  Cash Flow After Debt
                </td>
                {projections.map((p) => (
                  <td key={p.year} className={`px-3 py-2 text-right font-semibold ${p.cashFlow >= 0 ? 'text-success-600' : 'text-error-600'}`}>
                    {formatTableCurrency(p.cashFlow)}
                  </td>
                ))}
              </tr>
              {/* Cumulative Cash Flow */}
              <tr className="bg-neutral-50">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-neutral-50">
                  Cumulative Cash Flow
                </td>
                {projections.map((p) => (
                  <td key={p.year} className={`px-3 py-2 text-right ${p.cumulativeCashFlow >= 0 ? 'text-success-600' : 'text-error-600'}`}>
                    {formatTableCurrency(p.cumulativeCashFlow)}
                  </td>
                ))}
              </tr>
              {/* Property Value */}
              <tr className="bg-white border-t border-neutral-200">
                <td className="px-3 py-2 font-semibold text-neutral-900 sticky left-0 bg-white">
                  Property Value
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right font-semibold text-neutral-900">
                    {formatTableCurrency(p.propertyValue)}
                  </td>
                ))}
              </tr>
              {/* Loan Balance */}
              <tr className="bg-neutral-50">
                <td className="px-3 py-2 font-medium text-neutral-900 sticky left-0 bg-neutral-50">
                  Loan Balance
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right text-neutral-700">
                    {formatTableCurrency(p.loanBalance)}
                  </td>
                ))}
              </tr>
              {/* Equity */}
              <tr className="bg-white border-t border-neutral-200">
                <td className="px-3 py-2 font-semibold text-neutral-900 sticky left-0 bg-white">
                  Equity
                </td>
                {projections.map((p) => (
                  <td key={p.year} className="px-3 py-2 text-right font-semibold text-primary-600">
                    {formatTableCurrency(p.equity)}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
