import { useMemo, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useDealComparisonWithMockFallback } from '@/hooks/api/useDealComparison';
import { ComparisonTable } from './components/comparison/ComparisonTable';
import { ComparisonCharts } from './components/comparison/ComparisonCharts';
import { ComparisonSelector } from './components/comparison/ComparisonSelector';
import {
  ArrowLeft,
  Download,
  Share2,
  Plus,
  RefreshCw,
  BarChart3,
  Table2,
  Check,
  GitCompareArrows,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/useToast';
import { ComparisonSkeleton } from './components/comparison/ComparisonSkeleton';

type ViewMode = 'table' | 'charts' | 'both';

export function DealComparisonPage() {
  const [searchParams] = useSearchParams();
  const { success, error, info } = useToast();

  // Parse deal IDs from URL
  const dealIds = useMemo(() => {
    const idsParam = searchParams.get('ids');
    if (!idsParam) return [];
    return idsParam.split(',').filter((id) => id.trim() !== '');
  }, [searchParams]);

  // Fetch comparison data
  const {
    data,
    isLoading,
    isError,
    error: queryError,
    refetch,
  } = useDealComparisonWithMockFallback(dealIds);

  // UI state
  const [viewMode, setViewMode] = useState<ViewMode>('both');
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // Handle PDF export
  const handleExportPDF = async () => {
    if (!data?.deals || data.deals.length === 0) return;

    setIsExporting(true);
    try {
      const { default: jsPDF } = await import('jspdf');

      const doc = new jsPDF({ orientation: 'landscape' });
      const deals = data.deals;

      doc.setFontSize(20);
      doc.text('Deal Comparison Report', 20, 20);

      doc.setFontSize(10);
      doc.text(`Generated: ${new Date().toLocaleDateString()}`, 20, 28);

      doc.setFontSize(14);
      doc.text('Properties Compared:', 20, 40);
      doc.setFontSize(10);
      deals.forEach((deal, index) => {
        doc.text(`${index + 1}. ${deal.propertyName} - ${deal.address.city}, ${deal.address.state}`, 25, 48 + index * 6);
      });

      const startY = 48 + deals.length * 6 + 15;
      doc.setFontSize(14);
      doc.text('Key Metrics Comparison', 20, startY);

      doc.setFontSize(10);
      const fmtPct = (v: number | undefined) => v != null ? `${(v * 100).toFixed(1)}%` : 'N/A';
      const fmtCompact = (v: number | undefined) => {
        if (v == null) return 'N/A';
        if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
        if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
        return `$${v.toFixed(0)}`;
      };
      const metrics = [
        { label: 'Units', getValue: (d: typeof deals[0]) => `${d.units || 'N/A'}` },
        { label: 'Cap Rate PP (T12)', getValue: (d: typeof deals[0]) => fmtPct(d.t12CapOnPp) },
        { label: 'Cap Rate TC (T12)', getValue: (d: typeof deals[0]) => fmtPct(d.totalCostCapT12) },
        { label: 'NOI Margin', getValue: (d: typeof deals[0]) => fmtPct(d.noiMargin) },
        { label: 'Basis/Unit', getValue: (d: typeof deals[0]) => d.basisPerUnit != null ? `$${Math.round(d.basisPerUnit).toLocaleString()}` : 'N/A' },
        { label: 'Debt', getValue: (d: typeof deals[0]) => fmtCompact(d.loanAmount) },
        { label: 'Unlevered IRR', getValue: (d: typeof deals[0]) => fmtPct(d.unleveredIrr) },
        { label: 'Levered IRR', getValue: (d: typeof deals[0]) => fmtPct(d.leveredIrr) },
        { label: 'LP IRR', getValue: (d: typeof deals[0]) => fmtPct(d.lpIrr) },
      ];

      const metricColWidth = 40;
      const dealColWidth = (250 - metricColWidth) / deals.length;
      const tableStartY = startY + 8;

      doc.setFont('helvetica', 'bold');
      doc.text('Metric', 25, tableStartY);
      deals.forEach((deal, index) => {
        const x = 25 + metricColWidth + index * dealColWidth;
        const shortName = deal.propertyName.split(' ').slice(0, 2).join(' ');
        doc.text(shortName, x, tableStartY);
      });

      doc.setFont('helvetica', 'normal');
      metrics.forEach((metric, rowIndex) => {
        const y = tableStartY + 8 + rowIndex * 6;
        doc.text(metric.label, 25, y);
        deals.forEach((deal, colIndex) => {
          const x = 25 + metricColWidth + colIndex * dealColWidth;
          doc.text(metric.getValue(deal), x, y);
        });
      });

      doc.setFontSize(8);
      doc.text('B&R Capital Analytics - Deal Comparison Report', 20, 195);

      const fileName = `deal-comparison-${new Date().toISOString().split('T')[0]}.pdf`;
      doc.save(fileName);
      success('PDF exported successfully');
    } catch (err) {
      console.error('PDF export error:', err);
      error('Failed to export PDF. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  // Handle share URL
  const handleShareUrl = async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setIsCopied(true);
      info('Comparison URL copied to clipboard');
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      const textArea = document.createElement('textarea');
      textArea.value = url;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setIsCopied(true);
      info('Comparison URL copied to clipboard');
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  // No deals selected state
  if (dealIds.length < 2) {
    return (
      <div className="space-y-6">
        <div>
          <Link
            to="/deals"
            className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Deals
          </Link>
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-12 text-center">
          <div className="p-3 bg-neutral-100 rounded-xl w-fit mx-auto mb-4">
            <GitCompareArrows className="w-10 h-10 text-neutral-400" />
          </div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-2">
            No Deals Selected
          </h2>
          <p className="text-neutral-600 mb-6 max-w-md mx-auto">
            Select at least 2 deals to compare their metrics side by side.
            You can compare up to 4 deals at once.
          </p>
          <Button onClick={() => setSelectorOpen(true)} className="gap-2">
            <Plus className="w-4 h-4" />
            Select Deals to Compare
          </Button>
        </div>

        <ComparisonSelector
          open={selectorOpen}
          onOpenChange={setSelectorOpen}
          initialSelectedIds={dealIds}
        />
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return <ComparisonSkeleton dealCount={dealIds.length || 3} />;
  }

  // Error state
  if (isError) {
    return (
      <div className="space-y-6">
        <div>
          <Link
            to="/deals"
            className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Deals
          </Link>
        </div>

        <div className="bg-white rounded-lg border border-neutral-200 shadow-card p-12 text-center">
          <div className="p-3 bg-red-50 rounded-xl w-fit mx-auto mb-4">
            <BarChart3 className="w-10 h-10 text-red-400" />
          </div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-2">
            Failed to Load Comparison
          </h2>
          <p className="text-neutral-600 mb-6">
            {queryError instanceof Error
              ? queryError.message
              : 'An error occurred while loading the comparison data.'}
          </p>
          <Button onClick={() => refetch()} variant="outline" className="gap-2">
            <RefreshCw className="w-4 h-4" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  const deals = data?.deals ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            to="/deals"
            className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900 mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Deals
          </Link>
          <h1 className="text-3xl font-bold text-neutral-900">Deal Comparison</h1>
          <p className="text-neutral-600 mt-1">
            Comparing {deals.length} deals side by side
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-white rounded-lg shadow-md border border-neutral-200 p-1" role="group" aria-label="View mode">
            <button
              onClick={() => setViewMode('table')}
              aria-pressed={viewMode === 'table'}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                viewMode === 'table'
                  ? 'bg-blue-600 text-white'
                  : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
              )}
            >
              <Table2 className="w-4 h-4" />
              Table
            </button>
            <button
              onClick={() => setViewMode('charts')}
              aria-pressed={viewMode === 'charts'}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                viewMode === 'charts'
                  ? 'bg-blue-600 text-white'
                  : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
              )}
            >
              <BarChart3 className="w-4 h-4" />
              Charts
            </button>
            <button
              onClick={() => setViewMode('both')}
              aria-pressed={viewMode === 'both'}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
                viewMode === 'both'
                  ? 'bg-blue-600 text-white'
                  : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100'
              )}
            >
              Both
            </button>
          </div>

          {/* Actions */}
          <Button
            variant="outline"
            onClick={() => setSelectorOpen(true)}
            className="gap-2 bg-white"
          >
            <Plus className="w-4 h-4" />
            Add Deals
          </Button>
          <Button
            variant="outline"
            onClick={handleShareUrl}
            className="gap-2 bg-white"
          >
            {isCopied ? (
              <>
                <Check className="w-4 h-4" />
                Copied
              </>
            ) : (
              <>
                <Share2 className="w-4 h-4" />
                Share
              </>
            )}
          </Button>
          <Button
            onClick={handleExportPDF}
            disabled={isExporting}
            className="gap-2"
          >
            {isExporting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Export PDF
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Metrics Table */}
      {(viewMode === 'table' || viewMode === 'both') && (
        <div className="bg-white rounded-lg border border-neutral-200 shadow-card overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-200">
            <h2 className="text-lg font-semibold text-neutral-900">
              Metrics Comparison
            </h2>
            <p className="text-sm text-neutral-600 mt-0.5">
              Side-by-side comparison of key underwriting metrics
            </p>
          </div>
          <div className="p-6">
            <ComparisonTable deals={deals} highlightBestWorst={true} />
          </div>
        </div>
      )}

      {/* Visual Charts */}
      {(viewMode === 'charts' || viewMode === 'both') && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">
            Visual Comparison
          </h2>
          <ComparisonCharts deals={deals} chartType="both" />
        </div>
      )}

      {/* Deal Selector Modal */}
      <ComparisonSelector
        open={selectorOpen}
        onOpenChange={setSelectorOpen}
        initialSelectedIds={dealIds}
      />
    </div>
  );
}
