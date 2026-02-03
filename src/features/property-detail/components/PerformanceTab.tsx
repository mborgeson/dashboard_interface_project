import { TrendingUp, DollarSign, Percent, Award } from 'lucide-react';
import type { Property } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent } from '@/lib/utils/formatters';

interface PerformanceTabProps {
  property: Property;
}

export function PerformanceTab({ property }: PerformanceTabProps) {
  const perf = property.performance;

  return (
    <div className="p-6 space-y-6">
      {/* Performance Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">IRR (Levered)</CardTitle>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{formatPercent(perf.leveredIrr)}</div>
            <p className="text-xs text-gray-600 mt-1">Levered Internal Rate of Return</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">MOIC (Levered)</CardTitle>
            <Award className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary-600">{perf.leveredMoic ? `${perf.leveredMoic.toFixed(2)}x` : '--'}</div>
            <p className="text-xs text-gray-600 mt-1">Levered Multiple on Invested Capital</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">IRR (Unlevered)</CardTitle>
            <Percent className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-accent-600">{perf.unleveredIrr != null ? formatPercent(perf.unleveredIrr) : '--'}</div>
            <p className="text-xs text-gray-600 mt-1">Unlevered Internal Rate of Return</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">MOIC (Unlevered)</CardTitle>
            <DollarSign className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {perf.unleveredMoic ? `${perf.unleveredMoic.toFixed(2)}x` : '--'}
            </div>
            <p className="text-xs text-gray-600 mt-1">Unlevered Multiple on Invested Capital</p>
          </CardContent>
        </Card>
      </div>

      {/* Return Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Return Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-sm text-gray-600 mb-2">Total Equity Commitment</div>
              <div className="text-2xl font-bold text-gray-900 mb-1">
                {formatCurrency(perf.totalEquityCommitment)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-2">Total Cash Flows to Equity</div>
              <div className="text-2xl font-bold text-gray-900 mb-1">
                {formatCurrency(perf.totalCashFlowsToEquity)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-2">Net Cash Flows to Equity</div>
              <div className="text-2xl font-bold text-green-600 mb-1">
                {formatCurrency(perf.netCashFlowsToEquity)}
              </div>
              <div className="text-xs text-gray-500">
                Total Cash Flows minus Total Equity Commitment
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Investment Metrics Summary */}
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
                  {perf.holdPeriodYears} years
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Total Basis/Unit @ Close</div>
                <div className="text-lg font-semibold">
                  {formatCurrency(perf.totalBasisPerUnitClose)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Senior Loan Basis/Unit @ Close</div>
                <div className="text-lg font-semibold">
                  {formatCurrency(perf.seniorLoanBasisPerUnitClose)}
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-600 mb-1">Exit Cap Rate</div>
                <div className="text-lg font-semibold">
                  {perf.exitCapRate ? formatPercent(perf.exitCapRate) : '--'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Total Basis/Unit @ Exit</div>
                <div className="text-lg font-semibold">
                  {perf.totalBasisPerUnitExit ? formatCurrency(perf.totalBasisPerUnitExit) : '--'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600 mb-1">Senior Loan Basis/Unit @ Exit</div>
                <div className="text-lg font-semibold">
                  {perf.seniorLoanBasisPerUnitExit ? formatCurrency(perf.seniorLoanBasisPerUnitExit) : '--'}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
