/**
 * Hook that listens for WebSocket stage_changed / batch_stage_changed events
 * and invalidates the Kanban React Query cache so the board stays in sync
 * with server-side stage transitions (e.g. SharePoint folder moves).
 */

import { useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { useWebSocket } from '@/hooks/useWebSocket';
import type { WSMessage } from '@/hooks/useWebSocket';
import { useToast } from '@/hooks/useToast';
import { dealKeys } from '@/hooks/api/useDeals';

/** Payload shape for an individual stage_changed notification. */
export interface StageChangedEvent extends WSMessage {
  type: 'deal_update';
  action: 'stage_changed';
  deal_id: number;
  data: {
    deal_name: string;
    old_stage: string | null;
    new_stage: string;
    source: string;
  };
}

/** Payload shape for a batch_stage_changed notification. */
export interface BatchStageChangedEvent extends WSMessage {
  type: 'batch_stage_changed';
  count: number;
  deals: Array<{
    deal_id: number;
    deal_name: string;
    old_stage: string | null;
    new_stage: string;
  }>;
  source: string;
}

/**
 * Connect to the "deals" WebSocket channel and listen for stage change
 * events.  When received, the Kanban and deal list queries are invalidated
 * so React Query refetches fresh data.
 *
 * @param enabled - Whether to maintain the WebSocket connection (default true).
 */
export function useStageChangeNotifications(enabled = true): void {
  const queryClient = useQueryClient();
  const { info } = useToast();

  // Debounce invalidation so rapid-fire individual events don't trigger
  // dozens of refetches within the same tick.
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const invalidateDeals = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: dealKeys.all });
      debounceTimerRef.current = null;
    }, 300);
  }, [queryClient]);

  const handleMessage = useCallback(
    (message: WSMessage) => {
      // Individual stage change (sent as deal_update with action=stage_changed)
      if (message.type === 'deal_update' && message.action === 'stage_changed') {
        const data = message.data as StageChangedEvent['data'] | undefined;
        const dealName = data?.deal_name ?? 'A deal';
        const newStage = data?.new_stage
          ? String(data.new_stage).replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
          : 'a new stage';
        info(`${dealName} moved to ${newStage}`);
        invalidateDeals();
        return;
      }

      // Batch stage change
      if (message.type === 'batch_stage_changed') {
        const count = (message as BatchStageChangedEvent).count ?? 0;
        info(`${count} deal${count === 1 ? '' : 's'} moved to new stages`);
        invalidateDeals();
      }
    },
    [info, invalidateDeals],
  );

  // The useWebSocket hook manages connection lifecycle; we just need to
  // supply the onMessage callback.
  useWebSocket('deals', {
    enabled,
    onMessage: handleMessage,
  });
}
