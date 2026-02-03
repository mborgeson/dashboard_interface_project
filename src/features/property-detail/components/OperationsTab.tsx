import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { Property, OperatingYear, OperatingYearExpenses } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';

interface OperationsTabProps {
  property: Property;
}

// Type helpers for safe indexing
type NumericKeysOf<T> = { [K in keyof T]: T[K] extends number ? K : never }[keyof T];
type OperatingYearNumericKey = NumericKeysOf<OperatingYear>;

// Expense line item labels and keys
const EXPENSE_LINE_ITEMS: { label: string; key: keyof OperatingYearExpenses; color: string }[] = [
  { label: 'Real Estate Taxes', key: 'realEstateTaxes', color: '#3B82F6' },
  { label: 'Property Insurance', key: 'propertyInsurance', color: '#8B5CF6' },
  { label: 'Staffing/Payroll', key: 'staffingPayroll', color: '#06B6D4' },
  { label: 'Property Management Fee', key: 'propertyManagementFee', color: '#F59E0B' },
  { label: 'Repairs & Maintenance', key: 'repairsAndMaintenance', color: '#EF4444' },
  { label: 'Turnover', key: 'turnover', color: '#EC4899' },
  { label: 'Contract Services', key: 'contractServices', color: '#10B981' },
  { label: 'Reserves For Replacement', key: 'reservesForReplacement', color: '#F97316' },
  { label: 'Admin, Legal, & Security', key: 'adminLegalSecurity', color: '#7C3AED' },
  { label: 'Advertising, Leasing, & Marketing', key: 'advertisingLeasingMarketing', color: '#0EA5E9' },
  { label: 'Utilities', key: 'utilities', color: '#14B8A6' },
  { label: 'Other Expenses', key: 'otherExpenses', color: '#6B7280' },
];

// Revenue loss items (subtracted from GPR)
const REVENUE_LOSS_ITEMS: { label: string; key: OperatingYearNumericKey }[] = [
  { label: 'Less: Loss to Lease', key: 'lossToLease' },
  { label: 'Less: Vacancy Loss', key: 'vacancyLoss' },
  { label: 'Less: Bad Debts', key: 'badDebts' },
  { label: 'Less: Concessions', key: 'concessions' },
  { label: 'Less: Other Loss', key: 'otherLoss' },
];

// Other income subcategories
const OTHER_INCOME_ITEMS: { label: string; key: OperatingYearNumericKey }[] = [
  { label: 'Laundry Income', key: 'laundryIncome' },
  { label: 'Parking Income', key: 'parkingIncome' },
  { label: 'Pet Income', key: 'petIncome' },
  { label: 'Storage Income', key: 'storageIncome' },
  { label: 'Utility Income', key: 'utilityIncome' },
  { label: 'Other Misc Income', key: 'otherMiscIncome' },
];

function CashflowRow({
  label,
  values,
  indent = false,
  bold = false,
  red = false,
  green = false,
  parentheses = false,
  borderTop = false,
  borderTopThick = false,
}: {
  label: string;
  values: number[];
  indent?: boolean;
  bold?: boolean;
  red?: boolean;
  green?: boolean;
  parentheses?: boolean;
  borderTop?: boolean;
  borderTopThick?: boolean;
}) {
  // Skip rows where all values are zero
  const allZero = values.every((v) => v === 0);
  if (allZero && !bold) return null;

  return (
    <tr
      className={`text-sm ${borderTopThick ? 'border-t-2 border-gray-400' : borderTop ? 'border-t border-gray-200' : ''}`}
    >
      <td className={`py-1.5 pr-4 whitespace-nowrap ${indent ? 'pl-4' : ''} ${bold ? 'font-bold text-gray-900' : 'text-gray-600'}`}>
        {label}
      </td>
      {values.map((v, i) => (
        <td
          key={i}
          className={`py-1.5 text-right px-3 whitespace-nowrap ${bold ? 'font-bold' : 'font-medium'} ${red ? 'text-red-600' : green ? 'text-green-600' : bold ? 'text-primary-700' : ''}`}
        >
          {parentheses ? `(${formatCurrency(v)})` : formatCurrency(v)}
        </td>
      ))}
    </tr>
  );
}

// Custom pie chart label renderer
function renderCustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }: {
  cx: number; cy: number; midAngle: number; innerRadius: number; outerRadius: number; percent: number; name: string;
}) {
  if (percent < 0.05) return null; // Don't show labels for slices < 5%
  const RADIAN = Math.PI / 180;
  const radius = outerRadius + 25;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="#374151" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" fontSize={11}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

export function OperationsTab({ property }: OperationsTabProps) {
  const years = property.operationsByYear ?? [];
  const hasMultiYear = years.length > 0;

  // Year 1 expense data for pie chart (from the first year or fallback to operations.expenses)
  const yr1Expenses: OperatingYearExpenses = hasMultiYear
    ? years[0].expenses
    : property.operations.expenses;
  const expenseChartData = EXPENSE_LINE_ITEMS
    .map((item) => ({
      name: item.label,
      value: yr1Expenses[item.key] ?? 0,
      color: item.color,
    }))
    .filter((e) => e.value > 0);

  // Calculate actual total from individual line items for expense details
  const expenseDetailsTotal = expenseChartData.reduce((sum, e) => sum + e.value, 0);

  return (
    <div className="p-6 space-y-6">
      {/* Multi-Year Annual Cashflows Table */}
      <Card>
        <CardHeader>
          <CardTitle>Annual Cashflows</CardTitle>
        </CardHeader>
        <CardContent>
          {hasMultiYear ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-gray-300">
                    <th className="text-left py-2 pr-4 font-semibold text-gray-900 min-w-[220px]"></th>
                    {years.map((yr) => (
                      <th key={yr.year} className="text-right py-2 px-3 font-semibold text-gray-900 min-w-[120px]">
                        Year {yr.year}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Revenue Section Header */}
                  <tr>
                    <td colSpan={years.length + 1} className="pt-3 pb-1 font-semibold text-gray-900 border-b border-gray-300">
                      Revenue
                    </td>
                  </tr>
                  <CashflowRow
                    label="Gross Potential Revenue"
                    values={years.map((yr) => yr.grossPotentialRevenue)}
                    indent
                  />
                  {/* Revenue loss items */}
                  {REVENUE_LOSS_ITEMS.map((item) => (
                    <CashflowRow
                      key={item.key}
                      label={item.label}
                      values={years.map((yr) => (yr[item.key] as number) ?? 0)}
                      indent red parentheses
                    />
                  ))}
                  <CashflowRow
                    label="Net Rental Income"
                    values={years.map((yr) => yr.netRentalIncome)}
                    indent bold borderTop
                  />

                  {/* Other Income Section */}
                  <tr>
                    <td colSpan={years.length + 1} className="pt-3 pb-1 font-semibold text-gray-900 border-b border-gray-300">
                      Other Income
                    </td>
                  </tr>
                  {OTHER_INCOME_ITEMS.map((item) => (
                    <CashflowRow
                      key={item.key}
                      label={item.label}
                      values={years.map((yr) => (yr[item.key] as number) ?? 0)}
                      indent green
                    />
                  ))}
                  <CashflowRow
                    label="Total Other Income"
                    values={years.map((yr) => yr.otherIncome)}
                    indent bold borderTop
                  />

                  {/* Effective Gross Income */}
                  <CashflowRow
                    label="Effective Gross Income"
                    values={years.map((yr) => yr.effectiveGrossIncome || (yr.netRentalIncome + yr.otherIncome))}
                    bold borderTopThick
                  />

                  {/* Expenses Section Header */}
                  <tr>
                    <td colSpan={years.length + 1} className="pt-4 pb-1 font-semibold text-gray-900 border-b border-gray-300">
                      Operating Expenses
                    </td>
                  </tr>
                  {EXPENSE_LINE_ITEMS.map((item) => (
                    <CashflowRow
                      key={item.key}
                      label={item.label}
                      values={years.map((yr) => yr.expenses[item.key] ?? 0)}
                      indent red parentheses
                    />
                  ))}
                  <CashflowRow
                    label="Total Operating Expenses"
                    values={years.map((yr) => yr.totalOperatingExpenses)}
                    indent bold red parentheses borderTop
                  />

                  {/* NOI */}
                  <CashflowRow
                    label="Net Operating Income (NOI)"
                    values={years.map((yr) => yr.noi)}
                    bold borderTopThick
                  />
                </tbody>
              </table>
            </div>
          ) : (
            /* Fallback: single-year display from operations object */
            <div className="space-y-1">
              <div className="text-sm font-semibold text-gray-900 border-b border-gray-300 pb-1 mb-1">Revenue</div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-gray-600 pl-4">Gross Potential Revenue</span>
                <span className="font-medium">{formatCurrency(property.operations.grossPotentialRevenue)}</span>
              </div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-gray-600 pl-4">Less: Vacancy Loss</span>
                <span className="font-medium text-red-600">({formatCurrency(property.operations.vacancyLoss)})</span>
              </div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-gray-600 pl-4">Less: Concessions</span>
                <span className="font-medium text-red-600">({formatCurrency(property.operations.concessions)})</span>
              </div>
              <div className="flex justify-between text-sm py-1 border-t border-gray-200">
                <span className="text-gray-700 pl-4 font-medium">Net Rental Income</span>
                <span className="font-semibold">{formatCurrency(property.operations.netRentalIncome)}</span>
              </div>
              <div className="flex justify-between text-sm py-1">
                <span className="text-gray-600 pl-4">Other Income</span>
                <span className="font-medium">{formatCurrency(property.operations.otherIncomeAnnual)}</span>
              </div>
              <div className="text-sm font-semibold text-gray-900 border-b border-gray-300 pb-1 mb-1 mt-4">Operating Expenses</div>
              <div className="flex justify-between text-sm py-1 border-t border-gray-200">
                <span className="text-gray-700 pl-4 font-medium">Total Operating Expenses</span>
                <span className="font-semibold text-red-600">({formatCurrency(property.operations.expenses.total)})</span>
              </div>
              <div className="flex justify-between text-sm py-2 border-t-2 border-gray-400 mt-2">
                <span className="text-gray-900 font-bold">Net Operating Income (NOI)</span>
                <span className="font-bold text-primary-700 text-base">{formatCurrency(property.operations.noi)}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Expense Breakdown Charts (Year 1) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Expense Breakdown (Year 1)</CardTitle>
          </CardHeader>
          <CardContent>
            {expenseChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={380}>
                <PieChart>
                  <Pie
                    data={expenseChartData}
                    cx="50%"
                    cy="45%"
                    labelLine
                    label={renderCustomLabel}
                    innerRadius={60}
                    outerRadius={110}
                    paddingAngle={2}
                    dataKey="value"
                    strokeWidth={2}
                    stroke="#fff"
                  >
                    {expenseChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{
                      borderRadius: '8px',
                      border: '1px solid #e5e7eb',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                      fontSize: '13px',
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    align="center"
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: '11px', paddingTop: '12px' }}
                    formatter={(value: string) => <span className="text-gray-700">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[380px] text-gray-400 text-sm">
                No expense data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Expense Details Table */}
        <Card>
          <CardHeader>
            <CardTitle>Expense Details (Year 1)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {EXPENSE_LINE_ITEMS.map((item) => {
                const value = yr1Expenses[item.key] ?? 0;
                return (
                  <div key={item.key} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-sm text-gray-700">{item.label}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold">{formatCurrency(value)}</div>
                      <div className="text-xs text-gray-500">
                        {expenseDetailsTotal > 0 ? formatPercent(value / expenseDetailsTotal) : '0%'} of total
                      </div>
                    </div>
                  </div>
                );
              })}
              <div className="pt-3 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900">Total Expenses</span>
                  <span className="text-sm font-bold text-gray-900">
                    {formatCurrency(expenseDetailsTotal)}
                  </span>
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
              <div className="text-sm text-gray-600 mb-1">T12 Occupancy Rate</div>
              <div className="text-lg font-semibold">{formatPercent(property.operations.occupancy)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Average Rent</div>
              <div className="text-lg font-semibold">{formatCurrency(property.operations.averageRent)}/month</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Rent Per Sq Ft</div>
              <div className="text-lg font-semibold">
                ${(property.operations.rentPerSqft ?? 0).toFixed(2)}/sq ft
              </div>
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
