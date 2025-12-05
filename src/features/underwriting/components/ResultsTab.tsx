import type { UnderwritingResults } from '@/types';
import { TrendingUp, TrendingDown, DollarSign, Percent, BarChart3 } from 'lucide-react';

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

  return (
    <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-2">
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
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="Down Payment"
            value={formatCurrency(results.downPayment)}
            subtitle={formatPercent(results.downPayment / (results.downPayment + results.loanAmount))}
          />
          <MetricCard
            label="Loan Amount"
            value={formatCurrency(results.loanAmount)}
            subtitle="Total financing"
          />
          <MetricCard
            label="Closing Costs"
            value={formatCurrency(results.closingCosts)}
            subtitle="Transaction fees"
          />
          <MetricCard
            label="Total Equity Required"
            value={formatCurrency(results.totalEquityRequired)}
            subtitle="All-in capital"
            highlight="neutral"
          />
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
            subtitle={`After ${formatCurrency(results.year1.vacancy)} vacancy`}
          />
          <MetricCard
            label="Net Operating Income"
            value={formatCurrency(results.year1.noi)}
            subtitle={`Expenses: ${formatCurrency(results.year1.operatingExpenses)}`}
            highlight="positive"
          />
          <MetricCard
            label="Cash Flow"
            value={formatCurrency(results.year1.cashFlow)}
            subtitle={`After ${formatCurrency(results.year1.debtService)} debt service`}
            highlight={results.year1.cashFlow > 0 ? 'positive' : 'negative'}
          />
        </div>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <MetricCard
            label="Cash-on-Cash Return"
            value={formatPercent(results.year1.cashOnCashReturn)}
            subtitle="Year 1 yield on equity"
            highlight={results.year1.cashOnCashReturn >= 0.08 ? 'positive' : 'neutral'}
          />
          <MetricCard
            label="Debt Service Coverage Ratio"
            value={results.year1.debtServiceCoverageRatio.toFixed(2)}
            subtitle="NOI / Debt Service"
            highlight={dscrHighlight}
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
            subtitle="Based on exit cap rate"
          />
          <MetricCard
            label="Loan Paydown"
            value={formatCurrency(results.loanPaydown)}
            subtitle="Principal reduction"
          />
          <MetricCard
            label="Sale Proceeds"
            value={formatCurrency(results.saleProceeds)}
            subtitle="Net to equity"
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
