import { useMemo, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/useToast';

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
      // Dynamic import - jsPDF is only loaded when user clicks export
      const { default: jsPDF } = await import('jspdf');

      const doc = new jsPDF({ orientation: 'landscape' });
      const deals = data.deals;

      // Title
      doc.setFontSize(20);
      doc.text('Deal Comparison Report', 20, 20);

      // Generated date
      doc.setFontSize(10);
      doc.text(`Generated: ${new Date().toLocaleDateString()}`, 20, 28);

      // Deal names
      doc.setFontSize(14);
      doc.text('Properties Compared:', 20, 40);
      doc.setFontSize(10);
      deals.forEach((deal, index) => {
        doc.text(`${index + 1}. ${deal.propertyName} - ${deal.address.city}, ${deal.address.state}`, 25, 48 + index * 6);
      });

      // Key metrics comparison table
      const startY = 48 + deals.length * 6 + 15;
      doc.setFontSize(14);
      doc.text('Key Metrics Comparison', 20, startY);

      // Table headers
      doc.setFontSize(10);
      const metrics = [
        { label: 'Deal Value', getValue: (d: typeof deals[0]) => `$${(d.value / 1000000).toFixed(1)}M` },
        { label: 'Cap Rate', getValue: (d: typeof deals[0]) => `${d.capRate.toFixed(2)}%` },
        { label: 'Projected IRR', getValue: (d: typeof deals[0]) => `${((d.projectedIrr ?? 0) * 100).toFixed(1)}%` },
        { label: 'Cash-on-Cash', getValue: (d: typeof deals[0]) => `${((d.cashOnCash ?? 0) * 100).toFixed(1)}%` },
        { label: 'Equity Multiple', getValue: (d: typeof deals[0]) => `${(d.equityMultiple ?? 0).toFixed(2)}x` },
        { label: 'Units', getValue: (d: typeof deals[0]) => `${d.units}` },
        { label: 'Occupancy', getValue: (d: typeof deals[0]) => `${((d.occupancyRate ?? 0) * 100).toFixed(1)}%` },
      ];

      // Column widths
      const metricColWidth = 40;
      const dealColWidth = (250 - metricColWidth) / deals.length;
      const tableStartY = startY + 8;

      // Header row
      doc.setFont('helvetica', 'bold');
      doc.text('Metric', 25, tableStartY);
      deals.forEach((deal, index) => {
        const x = 25 + metricColWidth + index * dealColWidth;
        const shortName = deal.propertyName.split(' ').slice(0, 2).join(' ');
        doc.text(shortName, x, tableStartY);
      });

      // Data rows
      doc.setFont('helvetica', 'normal');
      metrics.forEach((metric, rowIndex) => {
        const y = tableStartY + 8 + rowIndex * 6;
        doc.text(metric.label, 25, y);
        deals.forEach((deal, colIndex) => {
          const x = 25 + metricColWidth + colIndex * dealColWidth;
          doc.text(metric.getValue(deal), x, y);
        });
      });

      // Footer
      doc.setFontSize(8);
      doc.text('B&R Capital Analytics - Deal Comparison Report', 20, 195);

      // Save
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
      // Fallback for browsers that don't support clipboard API
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

  // Handle adding more deals
  const handleAddDeals = () => {
    setSelectorOpen(true);
  };

  // No deals selected state
  if (dealIds.length < 2) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <Link
            to="/deals"
            className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Deals
          </Link>
        </div>

        <Card className="p-12 text-center">
          <BarChart3 className="w-16 h-16 mx-auto mb-4 text-neutral-400" />
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
        </Card>

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
    return (
      <div className="p-6">
        <div className="mb-6">
          <Link
            to="/deals"
            className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Deals
          </Link>
        </div>

        <Card className="p-12">
          <div className="flex flex-col items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mb-4" />
            <p className="text-neutral-600">Loading comparison data...</p>
          </div>
        </Card>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <Link
            to="/deals"
            className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-900"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Deals
          </Link>
        </div>

        <Card className="p-12 text-center">
          <div className="text-red-500 mb-4">
            <BarChart3 className="w-16 h-16 mx-auto" />
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
        </Card>
      </div>
    );
  }

  const deals = data?.deals ?? [];

  return (
    <div className="p-6 space-y-6">
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
          <h1 className="text-2xl font-bold text-neutral-900">Deal Comparison</h1>
          <p className="text-neutral-600">
            Comparing {deals.length} deals
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex items-center border border-neutral-200 rounded-lg overflow-hidden" role="group" aria-label="View mode">
            <button
              onClick={() => setViewMode('table')}
              aria-pressed={viewMode === 'table'}
              className={cn(
                'px-3 py-2 text-sm flex items-center gap-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-inset',
                viewMode === 'table'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white text-neutral-700 hover:bg-neutral-50'
              )}
            >
              <Table2 className="w-4 h-4" />
              Table
            </button>
            <button
              onClick={() => setViewMode('charts')}
              aria-pressed={viewMode === 'charts'}
              className={cn(
                'px-3 py-2 text-sm flex items-center gap-2 transition-colors border-l border-r border-neutral-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-inset',
                viewMode === 'charts'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white text-neutral-700 hover:bg-neutral-50'
              )}
            >
              <BarChart3 className="w-4 h-4" />
              Charts
            </button>
            <button
              onClick={() => setViewMode('both')}
              aria-pressed={viewMode === 'both'}
              className={cn(
                'px-3 py-2 text-sm flex items-center gap-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-inset',
                viewMode === 'both'
                  ? 'bg-primary-500 text-white'
                  : 'bg-white text-neutral-700 hover:bg-neutral-50'
              )}
            >
              Both
            </button>
          </div>

          {/* Actions */}
          <Button variant="outline" onClick={handleAddDeals} className="gap-2">
            <Plus className="w-4 h-4" />
            Add Deals
          </Button>
          <Button
            variant="outline"
            onClick={handleShareUrl}
            className="gap-2"
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

      {/* Comparison Content */}
      {(viewMode === 'table' || viewMode === 'both') && (
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-neutral-200">
            <h2 className="text-lg font-semibold text-neutral-900">
              Metrics Comparison
            </h2>
            <p className="text-sm text-neutral-600">
              Side-by-side comparison of key deal metrics
            </p>
          </div>
          <div className="p-6">
            <ComparisonTable deals={deals} highlightBestWorst={true} />
          </div>
        </Card>
      )}

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
