import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useQuickActions } from '@/contexts/QuickActionsContext';
import { GitCompare, X, ArrowRight, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useDealsWithMockFallback } from '@/hooks/api';

interface ComparisonBarProps {
  className?: string;
}

/**
 * Floating comparison bar that appears when deals are selected for comparison.
 * Shows selected deals and provides navigation to the comparison page.
 */
export function ComparisonBar({ className }: ComparisonBarProps) {
  const navigate = useNavigate();
  const {
    selectedDealsForComparison,
    removeDealFromCompare,
    clearComparisonSelection,
  } = useQuickActions();

  const { data } = useDealsWithMockFallback();

  // Don't show if no deals selected
  if (selectedDealsForComparison.length === 0) {
    return null;
  }

  // Get deal details for selected deals
  const selectedDeals = data?.deals.filter((deal) =>
    selectedDealsForComparison.includes(deal.id)
  ) ?? [];

  const canCompare = selectedDealsForComparison.length >= 2;

  const handleCompare = () => {
    if (canCompare) {
      const idsParam = selectedDealsForComparison.join(',');
      navigate(`/deals/compare?ids=${idsParam}`);
    }
  };

  const handleRemoveDeal = (dealId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    removeDealFromCompare(dealId);
  };

  return (
    <div
      className={cn(
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-50',
        'bg-white rounded-lg shadow-2xl border border-neutral-200',
        'px-4 py-3 flex items-center gap-4',
        'animate-in slide-in-from-bottom-4 duration-300',
        className
      )}
    >
      {/* Icon and label */}
      <div className="flex items-center gap-2 text-neutral-700">
        <GitCompare className="w-5 h-5 text-primary-500" />
        <span className="font-medium text-sm">
          {selectedDealsForComparison.length} deal{selectedDealsForComparison.length !== 1 ? 's' : ''} selected
        </span>
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-neutral-200" />

      {/* Selected deals chips */}
      <div className="flex items-center gap-2 max-w-md overflow-x-auto">
        {selectedDeals.map((deal) => (
          <div
            key={deal.id}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-primary-50 text-primary-700 rounded-full text-sm whitespace-nowrap"
          >
            <span className="max-w-[100px] truncate">
              {deal.propertyName.split(' ').slice(0, 2).join(' ')}
            </span>
            <button
              onClick={(e) => handleRemoveDeal(deal.id, e)}
              className="hover:text-primary-900 transition-colors"
              aria-label={`Remove ${deal.propertyName} from comparison`}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="h-8 w-px bg-neutral-200" />

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={clearComparisonSelection}
          className="text-neutral-500 hover:text-neutral-700"
        >
          <Trash2 className="w-4 h-4 mr-1" />
          Clear
        </Button>
        <Button
          onClick={handleCompare}
          disabled={!canCompare}
          size="sm"
          className="gap-2"
        >
          Compare
          <ArrowRight className="w-4 h-4" />
        </Button>
      </div>

      {/* Helper text when not enough deals */}
      {!canCompare && (
        <span className="text-xs text-neutral-500">
          Select at least 2 deals
        </span>
      )}
    </div>
  );
}
