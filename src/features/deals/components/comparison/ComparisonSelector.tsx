import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { useDealsWithMockFallback } from '@/hooks/api';
import { DEAL_STAGE_LABELS, DEAL_STAGE_COLORS } from '@/types/deal';
import { cn } from '@/lib/utils';
import {
  Search,
  X,
  ArrowRight,
  Building2,
  MapPin,
  DollarSign,
} from 'lucide-react';

interface ComparisonSelectorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialSelectedIds?: string[];
  maxSelections?: number;
  minSelections?: number;
}

export function ComparisonSelector({
  open,
  onOpenChange,
  initialSelectedIds = [],
  maxSelections = 4,
  minSelections = 2,
}: ComparisonSelectorProps) {
  const navigate = useNavigate();
  const { data, isLoading } = useDealsWithMockFallback();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    new Set(initialSelectedIds)
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [stageFilter, setStageFilter] = useState<string>('all');

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  // Get deals from data
  const deals = data?.deals;

  // Filter deals based on search and stage
  const filteredDeals = useMemo(() => {
    if (!deals) return [];

    return deals.filter((deal) => {
      const matchesSearch =
        searchQuery === '' ||
        deal.propertyName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        deal.address.city.toLowerCase().includes(searchQuery.toLowerCase()) ||
        deal.address.state.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStage =
        stageFilter === 'all' || deal.stage === stageFilter;

      return matchesSearch && matchesStage;
    });
  }, [deals, searchQuery, stageFilter]);

  // Get unique stages for filter
  const stages = useMemo(() => {
    if (!deals) return [];
    const uniqueStages = [...new Set(deals.map((d) => d.stage))];
    return uniqueStages;
  }, [deals]);

  const handleToggleDeal = (dealId: string) => {
    setSelectedIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(dealId)) {
        newSet.delete(dealId);
      } else {
        if (newSet.size < maxSelections) {
          newSet.add(dealId);
        }
      }
      return newSet;
    });
  };

  const handleCompare = () => {
    if (selectedIds.size >= minSelections) {
      const idsParam = Array.from(selectedIds).join(',');
      navigate(`/deals/compare?ids=${idsParam}`);
      onOpenChange(false);
    }
  };

  const handleClearSelection = () => {
    setSelectedIds(new Set());
  };

  const canCompare = selectedIds.size >= minSelections;
  const isAtMax = selectedIds.size >= maxSelections;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold text-neutral-900">
            Select Deals to Compare
          </DialogTitle>
          <DialogDescription>
            Choose {minSelections}-{maxSelections} deals to compare side by side.
            Selected: {selectedIds.size} / {maxSelections}
          </DialogDescription>
        </DialogHeader>

        {/* Filters */}
        <div className="flex gap-4 items-center py-4 border-b border-neutral-200">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
            <Input
              placeholder="Search deals by name, city, or state..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="h-10 px-3 rounded-md border border-input bg-background text-sm"
          >
            <option value="all">All Stages</option>
            {stages.map((stage) => (
              <option key={stage} value={stage}>
                {DEAL_STAGE_LABELS[stage]}
              </option>
            ))}
          </select>
        </div>

        {/* Selected Deals Preview */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2 py-3 flex-wrap">
            <span className="text-sm font-medium text-neutral-700">Selected:</span>
            {Array.from(selectedIds).map((id) => {
              const deal = data?.deals.find((d) => d.id === id);
              if (!deal) return null;
              return (
                <span
                  key={id}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-primary-100 text-primary-700 rounded-md text-sm"
                >
                  {deal.propertyName.split(' ').slice(0, 2).join(' ')}
                  <button
                    onClick={() => handleToggleDeal(id)}
                    className="ml-1 hover:text-primary-900"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}
            <button
              onClick={handleClearSelection}
              className="text-sm text-neutral-500 hover:text-neutral-700 underline ml-2"
            >
              Clear all
            </button>
          </div>
        )}

        {/* Deal List */}
        <div className="flex-1 overflow-y-auto min-h-[300px]">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
            </div>
          ) : filteredDeals.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-neutral-500">
              <Building2 className="w-12 h-12 mb-2 opacity-50" />
              <p>No deals found matching your criteria</p>
            </div>
          ) : (
            <div className="space-y-2 py-2">
              {filteredDeals.map((deal) => {
                const isSelected = selectedIds.has(deal.id);
                const isDisabled = !isSelected && isAtMax;

                return (
                  <div
                    key={deal.id}
                    onClick={() => !isDisabled && handleToggleDeal(deal.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        if (!isDisabled) handleToggleDeal(deal.id);
                      }
                    }}
                    role="checkbox"
                    aria-checked={isSelected}
                    tabIndex={0}
                    className={cn(
                      'flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-all',
                      isSelected
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-neutral-200 hover:border-neutral-300',
                      isDisabled && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    <Checkbox
                      checked={isSelected}
                      disabled={isDisabled}
                      onCheckedChange={() => handleToggleDeal(deal.id)}
                      className="pointer-events-none"
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-neutral-900 truncate">
                          {deal.propertyName}
                        </h4>
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded text-xs font-medium border',
                            DEAL_STAGE_COLORS[deal.stage]
                          )}
                        >
                          {DEAL_STAGE_LABELS[deal.stage]}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-neutral-600">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5" />
                          {deal.address.city}, {deal.address.state}
                        </span>
                        <span className="flex items-center gap-1">
                          <Building2 className="w-3.5 h-3.5" />
                          {deal.propertyType}
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="flex items-center gap-1 font-semibold text-neutral-900">
                        <DollarSign className="w-4 h-4" />
                        {formatCurrency(deal.value)}
                      </div>
                      <div className="text-sm text-neutral-600">
                        {deal.capRate.toFixed(1)}% Cap Rate
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <DialogFooter className="border-t border-neutral-200 pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleCompare}
            disabled={!canCompare}
            className="flex items-center gap-2"
          >
            Compare {selectedIds.size > 0 ? `(${selectedIds.size})` : ''}
            <ArrowRight className="w-4 h-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
