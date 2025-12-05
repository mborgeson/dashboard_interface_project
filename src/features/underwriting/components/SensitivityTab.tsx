import type { SensitivityVariable } from '@/types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';

interface SensitivityTabProps {
  sensitivity: SensitivityVariable[];
  baseIRR: number;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function SensitivityTab({ sensitivity, baseIRR }: SensitivityTabProps) {
  // Format value for display based on variable type
  const formatValue = (name: string, value: number): string => {
    if (name.includes('Percent') || name.includes('Rate') || name === 'exitCapRate') {
      return `${(value * 100).toFixed(2)}%`;
    }
    if (name.includes('PerUnit') || name === 'currentRentPerUnit') {
      return `$${value.toLocaleString()}`;
    }
    return value.toFixed(1);
  };

  // Prepare tornado chart data
  const tornadoData = sensitivity.map((s) => ({
    name: s.label,
    low: (s.lowIRR - baseIRR) * 100,
    high: (s.highIRR - baseIRR) * 100,
    lowScenario: formatValue(s.name, s.lowValue),
    highScenario: formatValue(s.name, s.highValue),
    impact: Math.abs(s.highIRR - s.lowIRR) * 100,
  }));

  // Sort by impact for tornado chart
  const sortedData = [...tornadoData].sort((a, b) => b.impact - a.impact);

  return (
    <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-2">
      {/* Header with Base IRR */}
      <div className="flex items-center justify-between bg-neutral-50 rounded-lg p-4">
        <div>
          <h4 className="text-sm font-semibold text-neutral-800">Sensitivity Analysis</h4>
          <p className="text-sm text-neutral-600 mt-1">
            Impact of key variables on Levered IRR
          </p>
        </div>
        <div className="text-right">
          <div className="text-sm text-neutral-600">Base Case IRR</div>
          <div className="text-2xl font-semibold text-primary-600">{formatPercent(baseIRR)}</div>
        </div>
      </div>

      {/* Tornado Chart */}
      <div className="bg-white border border-neutral-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-neutral-800 mb-4">
          IRR Tornado Chart (% point change from base)
        </h4>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={sortedData}
            layout="vertical"
            margin={{ top: 20, right: 30, left: 120, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              type="number"
              tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
              tick={{ fontSize: 11 }}
              domain={['dataMin - 1', 'dataMax + 1']}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11 }}
              width={110}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                `${value > 0 ? '+' : ''}${value.toFixed(2)}%`,
                name === 'low' ? 'Downside' : 'Upside',
              ]}
              contentStyle={{ fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <ReferenceLine x={0} stroke="#6b7280" strokeWidth={2} />
            <Bar dataKey="low" name="Downside" stackId="stack">
              {sortedData.map((_, index) => (
                <Cell key={`low-${index}`} fill="#ef4444" />
              ))}
            </Bar>
            <Bar dataKey="high" name="Upside" stackId="stack">
              {sortedData.map((_, index) => (
                <Cell key={`high-${index}`} fill="#22c55e" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Sensitivity Table */}
      <div className="bg-white border border-neutral-200 rounded-lg overflow-hidden">
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-200">
          <h4 className="text-sm font-semibold text-neutral-800">
            Detailed Sensitivity Scenarios
          </h4>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50">
                <th className="px-4 py-3 text-left font-medium text-neutral-600">Variable</th>
                <th className="px-4 py-3 text-center font-medium text-error-600">Downside Scenario</th>
                <th className="px-4 py-3 text-center font-medium text-error-600">Downside IRR</th>
                <th className="px-4 py-3 text-center font-medium text-neutral-600">Base IRR</th>
                <th className="px-4 py-3 text-center font-medium text-success-600">Upside IRR</th>
                <th className="px-4 py-3 text-center font-medium text-success-600">Upside Scenario</th>
                <th className="px-4 py-3 text-center font-medium text-neutral-600">Total Range</th>
              </tr>
            </thead>
            <tbody>
              {sensitivity.map((s, idx) => {
                const impact = Math.abs(s.highIRR - s.lowIRR) * 100;
                return (
                  <tr
                    key={s.name}
                    className={idx % 2 === 0 ? 'bg-white' : 'bg-neutral-50'}
                  >
                    <td className="px-4 py-3 font-medium text-neutral-900">{s.label}</td>
                    <td className="px-4 py-3 text-center text-neutral-600">{formatValue(s.name, s.lowValue)}</td>
                    <td className="px-4 py-3 text-center font-medium text-error-600">
                      {formatPercent(s.lowIRR)}
                    </td>
                    <td className="px-4 py-3 text-center font-medium text-neutral-700">
                      {formatPercent(baseIRR)}
                    </td>
                    <td className="px-4 py-3 text-center font-medium text-success-600">
                      {formatPercent(s.highIRR)}
                    </td>
                    <td className="px-4 py-3 text-center text-neutral-600">{formatValue(s.name, s.highValue)}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          impact >= 5
                            ? 'bg-error-100 text-error-700'
                            : impact >= 2
                            ? 'bg-warning-100 text-warning-700'
                            : 'bg-success-100 text-success-700'
                        }`}
                      >
                        {impact.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Key Insights */}
      <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-primary-800 mb-3">Key Sensitivity Insights</h4>
        <ul className="space-y-2 text-sm text-primary-700">
          <li className="flex items-start gap-2">
            <span className="text-primary-500">•</span>
            <span>
              <strong>Exit Cap Rate</strong> and <strong>Purchase Price</strong> typically have the largest
              impact on returns due to leverage amplification.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-500">•</span>
            <span>
              Variables with total range &gt; 5% represent high-risk factors that warrant
              additional due diligence.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-primary-500">•</span>
            <span>
              The tornado chart shows relative impact - longer bars indicate higher sensitivity
              to that variable.
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
