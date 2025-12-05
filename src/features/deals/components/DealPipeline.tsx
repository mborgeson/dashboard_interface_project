import type { Deal, DealStage } from '@/types/deal';
import { DEAL_STAGE_LABELS } from '@/types/deal';
import { DealCard } from './DealCard';

interface DealPipelineProps {
  dealsByStage: Record<DealStage, Deal[]>;
}

const PIPELINE_STAGES: DealStage[] = [
  'lead',
  'underwriting',
  'loi',
  'due_diligence',
  'closing',
  'closed_won',
];

export function DealPipeline({ dealsByStage }: DealPipelineProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
      notation: 'compact',
      compactDisplay: 'short',
    }).format(value);
  };

  const getStageTotal = (stage: DealStage) => {
    return dealsByStage[stage].reduce((sum, deal) => sum + deal.value, 0);
  };

  return (
    <div className="bg-white rounded-lg border border-neutral-200 shadow-card">
      {/* Pipeline Header */}
      <div className="grid grid-cols-6 border-b border-neutral-200">
        {PIPELINE_STAGES.map((stage) => {
          const deals = dealsByStage[stage];
          const total = getStageTotal(stage);

          return (
            <div
              key={stage}
              className="p-4 border-r border-neutral-200 last:border-r-0"
            >
              <div className="text-sm font-semibold text-neutral-900 mb-1">
                {DEAL_STAGE_LABELS[stage]}
              </div>
              <div className="text-xs text-neutral-600">
                {deals.length} {deals.length === 1 ? 'deal' : 'deals'}
              </div>
              {total > 0 && (
                <div className="text-sm font-semibold text-accent-600 mt-1">
                  {formatCurrency(total)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pipeline Columns */}
      <div className="grid grid-cols-6">
        {PIPELINE_STAGES.map((stage) => {
          const deals = dealsByStage[stage];

          return (
            <div
              key={stage}
              className="p-4 space-y-3 border-r border-neutral-200 last:border-r-0 min-h-[400px] bg-neutral-50"
            >
              {deals.length === 0 ? (
                <div className="text-center text-sm text-neutral-400 py-8">
                  No deals
                </div>
              ) : (
                deals.map((deal) => <DealCard key={deal.id} deal={deal} />)
              )}
            </div>
          );
        })}
      </div>

      {/* Lost Deals Section */}
      {dealsByStage.closed_lost.length > 0 && (
        <div className="border-t border-neutral-200">
          <div className="p-4 bg-neutral-50">
            <div className="flex items-center justify-between mb-3">
              <div className="text-sm font-semibold text-neutral-900">
                Closed Lost
              </div>
              <div className="text-xs text-neutral-600">
                {dealsByStage.closed_lost.length}{' '}
                {dealsByStage.closed_lost.length === 1 ? 'deal' : 'deals'}
              </div>
            </div>
            <div className="grid grid-cols-6 gap-3">
              {dealsByStage.closed_lost.map((deal) => (
                <DealCard key={deal.id} deal={deal} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
