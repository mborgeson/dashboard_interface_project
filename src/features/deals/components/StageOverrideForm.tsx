/**
 * StageOverrideForm — inline form for manually changing a deal's stage.
 *
 * Sends POST /api/v1/deals/{id}/stage with { stage, reason? }.
 * On success, invalidates stage history and deal queries.
 */
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { DEAL_STAGE_LABELS, DEAL_STAGE_COLORS, type DealStage } from '@/types/deal';
import { dealKeys } from '@/hooks/api/useDeals';

// ── Types ────────────────────────────────────────────────────────────────

interface StageOverrideRequest {
  stage: string;
  reason?: string;
}

const ALL_STAGES: DealStage[] = [
  'dead',
  'initial_review',
  'active_review',
  'under_contract',
  'closed',
  'realized',
];

// ── Component ────────────────────────────────────────────────────────────

interface StageOverrideFormProps {
  dealId: string;
  currentStage: DealStage;
  onSuccess?: () => void;
}

export function StageOverrideForm({ dealId, currentStage, onSuccess }: StageOverrideFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedStage, setSelectedStage] = useState<DealStage | ''>('');
  const [reason, setReason] = useState('');

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: StageOverrideRequest) =>
      apiClient.post(`/deals/${dealId}/stage`, data),
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: dealKeys.detail(dealId) });
      queryClient.invalidateQueries({ queryKey: dealKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dealKeys.pipeline() });
      queryClient.invalidateQueries({ queryKey: ['stage-history', dealId] });
      // Reset form
      setIsOpen(false);
      setSelectedStage('');
      setReason('');
      onSuccess?.();
    },
  });

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="text-xs text-neutral-500 hover:text-neutral-700 underline transition-colors"
      >
        Change Stage
      </button>
    );
  }

  const availableStages = ALL_STAGES.filter((s) => s !== currentStage);

  return (
    <div className="p-3 rounded-lg border border-neutral-200 bg-neutral-50 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-neutral-700">Change Stage</span>
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          className="text-xs text-neutral-400 hover:text-neutral-600"
        >
          Cancel
        </button>
      </div>

      {/* Stage selection */}
      <div className="flex flex-wrap gap-1.5">
        {availableStages.map((stage) => {
          const isSelected = selectedStage === stage;
          const colors = DEAL_STAGE_COLORS[stage];
          return (
            <button
              key={stage}
              type="button"
              onClick={() => setSelectedStage(stage)}
              className={cn(
                'text-xs px-2 py-1 rounded border transition-all',
                isSelected
                  ? cn(colors, 'ring-2 ring-offset-1 ring-neutral-400')
                  : 'bg-white text-neutral-600 border-neutral-200 hover:border-neutral-400',
              )}
            >
              {DEAL_STAGE_LABELS[stage]}
            </button>
          );
        })}
      </div>

      {/* Selected stage preview */}
      {selectedStage && (
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <span>Moving to:</span>
          <Badge className={cn('text-xs border', DEAL_STAGE_COLORS[selectedStage])}>
            {DEAL_STAGE_LABELS[selectedStage]}
          </Badge>
        </div>
      )}

      {/* Reason field */}
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason for stage change (optional)"
        maxLength={500}
        rows={2}
        className="w-full text-sm border border-neutral-200 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300 resize-none"
      />

      {/* Error */}
      {mutation.error && (
        <p className="text-xs text-red-600">
          Failed to update stage. Please try again.
        </p>
      )}

      {/* Submit */}
      <button
        type="button"
        disabled={!selectedStage || mutation.isPending}
        onClick={() => {
          if (!selectedStage) return;
          mutation.mutate({
            stage: selectedStage,
            reason: reason.trim() || undefined,
          });
        }}
        className={cn(
          'w-full text-sm font-medium py-1.5 rounded-md transition-colors',
          selectedStage && !mutation.isPending
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-neutral-200 text-neutral-400 cursor-not-allowed',
        )}
      >
        {mutation.isPending ? 'Saving...' : 'Confirm Stage Change'}
      </button>
    </div>
  );
}

export default StageOverrideForm;
