import type { UnderwritingResults } from '@/types';
import { TrendingUp, TrendingDown, DollarSign, Percent, BarChart3, Home, Calculator } from 'lucide-react';

interface ResultsTabProps {
  results: UnderwritingResults;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function MetricCard({
  label,
  value,
  subtitle,
  icon: Icon,
  trend,
  highlight,
}: {
  label: string;
  value: string;
  subtitle?: string;
  icon?: React.ElementType;
  trend?: 'up' | 'down' | 'neutral';
  highlight?: 'positive' | 'negative' | 'neutral';
}) {
  const highlightColors = {
    positive: 'text-success-600 bg-success-50',
    negative: 'text-error-600 bg-error-50',
    neutral: 'text-neutral-700 bg-neutral-50',
  };

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between mb-2">
        <span className="text-sm text-neutral-600">{label}</span>
        {Icon && (
          <div className={`p-1.5 rounded-md ${highlightColors[highlight || 'neutral']}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-neutral-900">{value}</span>
        {trend && (
          <span className={trend === 'up' ? 'text-success-600' : 'text-error-600'}>
            {trend === 'up' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          </span>
        )}
      </div>
      {subtitle && <p className="text-xs text-neutral-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return (
    <h4 className="text-sm font-semibold text-neutral-800 mb-3 flex items-center gap-2">
      <div className="w-1 h-4 bg-primary-500 rounded-full" />
      {title}
    </h4>
  );
}

export function ResultsTab({ results }: ResultsTabProps) {
  const irrHighlight = results.leveredIRR > 0.15 ? 'positive' : results.leveredIRR < 0.08 ? 'negative' : 'neutral';
  const dscrHighlight = results.year1.debtServiceCoverageRatio >= 1.25 ? 'positive' : results.year1.debtServiceCoverageRatio < 1.0 ? 'negative' : 'neutral';
  const cocHighlight = results.year1.cashOnCashReturn >= 0.08 ? 'positive' : results.year1.cashOnCashReturn < 0.05 ? 'negative' : 'neutral';

  return (
    <div className="space-y-6">
      {/* Investment Summary Box */}
      <div className="bg-gradient-to-br from-primary-50 to-accent-50 border border-primary-200 rounded-lg p-5">
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">Investment Summary</h3>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="text-xs text-neutral-600 mb-1">Purchase Price</div>
            <div className="text-xl font-bold text-neutral-900">{formatCurrency(results.purchasePrice)}</div>
            <div className="text-xs text-neutral-500 mt-1">
              {formatCurrency(results.pricePerUnit)}/unit | ${results.pricePerSF.toFixed(0)}/SF
            </div>
          </div>
          <div>
            <div className="text-xs text-neutral-600 mb-1">Total Equity Required</div>
            <div className="text-xl font-bold text-neutral-900">{formatCurrency(results.totalEquityRequired)}</div>
            <div className="text-xs text-neutral-500 mt-1">
              {formatPercent(results.totalEquityRequired / results.purchasePrice)} of purchase
            </div>
          </div>
          <div>
            <div className="text-xs text-neutral-600 mb-1">Levered IRR</div>
            <div className={`text-xl font-bold ${irrHighlight === 'positive' ? 'text-success-600' : irrHighlight === 'negative' ? 'text-error-600' : 'text-neutral-900'}`}>
              {formatPercent(results.leveredIRR)}
            </div>
            <div className="text-xs text-neutral-500 mt-1">
              {results.equityMultiple.toFixed(2)}x equity multiple
            </div>
          </div>
        </div>
      </div>

      {/* Key Return Metrics */}
      <div>
        <SectionTitle title="Return Metrics" />
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="Levered IRR"
            value={formatPercent(results.leveredIRR)}
            subtitle="After debt service"
            icon={TrendingUp}
            highlight={irrHighlight}
          />
          <MetricCard
            label="Unlevered IRR"
            value={formatPercent(results.unleveredIRR)}
            subtitle="Before debt"
            icon={BarChart3}
            highlight="neutral"
          />
          <MetricCard
            label="Equity Multiple"
            value={`${results.equityMultiple.toFixed(2)}x`}
            subtitle="Total return on equity"
            icon={DollarSign}
            highlight={results.equityMultiple >= 2 ? 'positive' : 'neutral'}
          />
          <MetricCard
            label="Avg Annual Return"
            value={formatPercent(results.averageAnnualReturn)}
            subtitle="Simple average"
            icon={Percent}
            highlight="neutral"
          />
        </div>
      </div>

      {/* Acquisition Metrics */}
      <div>
        <SectionTitle title="Acquisition Metrics" />
        <div className="grid grid-cols-5 gap-4">
          <MetricCard
            label="Purchase Price"
            value={formatCurrency(results.purchasePrice)}
            subtitle={`${formatCurrency(results.pricePerUnit)}/unit`}
            icon={Home}
          />
          <MetricCard
            label="Down Payment"
            value={formatCurrency(results.downPayment)}
            subtitle={formatPercent(1 - results.ltv)}
          />
          <MetricCard
            label="Loan Amount"
            value={formatCurrency(results.loanAmount)}
            subtitle={`${formatPercent(results.ltv)} LTV`}
          />
          <MetricCard
            label="Closing & Fees"
            value={formatCurrency(results.closingCosts + results.acquisitionFee)}
            subtitle="Transaction costs"
          />
          <MetricCard
            label="Total Equity"
            value={formatCurrency(results.totalEquityRequired)}
            subtitle="All-in capital"
            highlight="neutral"
          />
        </div>
      </div>

      {/* Loan Summary */}
      <div>
        <SectionTitle title="Loan Details" />
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4">
          <div className="grid grid-cols-4 gap-6">
            <div>
              <div className="text-xs text-neutral-600 mb-1">Loan Amount</div>
              <div className="text-lg font-semibold text-neutral-900">{formatCurrency(results.loanAmount)}</div>
            </div>
            <div>
              <div className="text-xs text-neutral-600 mb-1">LTV Ratio</div>
              <div className="text-lg font-semibold text-neutral-900">{formatPercent(results.ltv)}</div>
            </div>
            <div>
              <div className="text-xs text-neutral-600 mb-1">Annual Debt Service</div>
              <div className="text-lg font-semibold text-neutral-900">{formatCurrency(results.year1.debtService)}</div>
            </div>
            <div>
              <div className="text-xs text-neutral-600 mb-1">Year 1 DSCR</div>
              <div className={`text-lg font-semibold ${dscrHighlight === 'positive' ? 'text-success-600' : dscrHighlight === 'negative' ? 'text-error-600' : 'text-neutral-900'}`}>
                {results.year1.debtServiceCoverageRatio.toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Year 1 Operating Metrics */}
      <div>
        <SectionTitle title="Year 1 Operating Performance" />
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="Gross Income"
            value={formatCurrency(results.year1.grossIncome)}
            subtitle="Potential rent + other"
          />
          <MetricCard
            label="Effective Gross Income"
            value={formatCurrency(results.year1.effectiveGrossIncome)}
            subtitle={`After vacancy & loss to lease`}
          />
          <MetricCard
            label="Net Operating Income"
            value={formatCurrency(results.year1.noi)}
            subtitle={`OpEx: ${formatCurrency(results.year1.operatingExpenses)}`}
            highlight="positive"
          />
          <MetricCard
            label="Cash Flow"
            value={formatCurrency(results.year1.cashFlow)}
            subtitle={`After debt service`}
            highlight={results.year1.cashFlow > 0 ? 'positive' : 'negative'}
          />
        </div>
      </div>

      {/* Year 1 Performance Ratios */}
      <div>
        <SectionTitle title="Year 1 Performance Ratios" />
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="Cash-on-Cash Return"
            value={formatPercent(results.year1.cashOnCashReturn)}
            subtitle="Year 1 yield on equity"
            icon={Percent}
            highlight={cocHighlight}
          />
          <MetricCard
            label="DSCR"
            value={results.year1.debtServiceCoverageRatio.toFixed(2)}
            subtitle="NOI / Debt Service"
            icon={Calculator}
            highlight={dscrHighlight}
          />
          <MetricCard
            label="Yield on Cost"
            value={formatPercent(results.year1.yieldOnCost)}
            subtitle="NOI / Total Basis"
            icon={BarChart3}
            highlight="neutral"
          />
          <MetricCard
            label="Break-Even Occupancy"
            value={formatPercent(results.year1.cashBreakEvenOccupancy)}
            subtitle="Cash flow break-even"
            icon={Home}
            highlight={results.year1.cashBreakEvenOccupancy < 0.85 ? 'positive' : 'negative'}
          />
        </div>
      </div>

      {/* Exit Analysis */}
      <div>
        <SectionTitle title="Exit Analysis" />
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="Exit Value"
            value={formatCurrency(results.exitValue)}
            subtitle={`Exit cap: ${formatPercent(results.exitCapRate)}`}
          />
          <MetricCard
            label="Loan Paydown"
            value={formatCurrency(results.loanPaydown)}
            subtitle="Principal reduction"
          />
          <MetricCard
            label="Sale Proceeds"
            value={formatCurrency(results.saleProceeds)}
            subtitle={`After ${formatCurrency(results.dispositionFee)} fee`}
            highlight="positive"
          />
          <MetricCard
            label="Total Profit"
            value={formatCurrency(results.totalProfit)}
            subtitle="Cash flows + sale"
            highlight={results.totalProfit > 0 ? 'positive' : 'negative'}
          />
        </div>
      </div>
    </div>
  );
}
