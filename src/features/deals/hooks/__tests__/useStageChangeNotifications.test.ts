/**
 * Tests for the useStageChangeNotifications hook.
 *
 * Verifies that WebSocket stage_changed and batch_stage_changed events
 * trigger React Query cache invalidation for the Kanban board.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { dealKeys } from '@/hooks/api/useDeals';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Capture the onMessage callback passed to useWebSocket
let capturedOnMessage: ((msg: Record<string, unknown>) => void) | undefined;

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: vi.fn((_channel: string, options?: { onMessage?: (msg: Record<string, unknown>) => void }) => {
    capturedOnMessage = options?.onMessage;
    return {
      status: 'open' as const,
      lastMessage: null,
      sendMessage: vi.fn(),
      subscribe: vi.fn(),
      unsubscribe: vi.fn(),
    };
  }),
}));

const mockInvalidateQueries = vi.fn();
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    invalidateQueries: mockInvalidateQueries,
  }),
}));

const mockInfo = vi.fn();
vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({
    info: mockInfo,
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  }),
}));

// Import AFTER mocks are set up
import { useStageChangeNotifications } from '../useStageChangeNotifications';
import { useWebSocket } from '@/hooks/useWebSocket';

// ---------------------------------------------------------------------------
// Test Suite
// ---------------------------------------------------------------------------

describe('useStageChangeNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOnMessage = undefined;
    // Reset timers for debounce
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('connects to the "deals" WebSocket channel', () => {
    renderHook(() => useStageChangeNotifications());

    expect(useWebSocket).toHaveBeenCalledWith(
      'deals',
      expect.objectContaining({ enabled: true }),
    );
  });

  it('passes enabled=false when disabled', () => {
    renderHook(() => useStageChangeNotifications(false));

    expect(useWebSocket).toHaveBeenCalledWith(
      'deals',
      expect.objectContaining({ enabled: false }),
    );
  });

  it('invalidates deal queries on stage_changed event', () => {
    renderHook(() => useStageChangeNotifications());

    expect(capturedOnMessage).toBeDefined();

    act(() => {
      capturedOnMessage!({
        type: 'deal_update',
        action: 'stage_changed',
        deal_id: 42,
        data: {
          deal_name: 'The Clubhouse',
          old_stage: 'active_review',
          new_stage: 'under_contract',
          source: 'sharepoint_sync',
        },
      });
    });

    // Advance past the 300ms debounce
    act(() => {
      vi.advanceTimersByTime(350);
    });

    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: dealKeys.all,
    });
  });

  it('shows a toast notification on stage_changed event', () => {
    renderHook(() => useStageChangeNotifications());

    act(() => {
      capturedOnMessage!({
        type: 'deal_update',
        action: 'stage_changed',
        deal_id: 42,
        data: {
          deal_name: 'The Clubhouse',
          old_stage: 'initial_review',
          new_stage: 'under_contract',
          source: 'sharepoint_sync',
        },
      });
    });

    expect(mockInfo).toHaveBeenCalledWith(
      expect.stringContaining('The Clubhouse'),
    );
  });

  it('invalidates deal queries on batch_stage_changed event', () => {
    renderHook(() => useStageChangeNotifications());

    act(() => {
      capturedOnMessage!({
        type: 'batch_stage_changed',
        count: 7,
        deals: [
          { deal_id: 1, deal_name: 'Deal A', old_stage: 'initial_review', new_stage: 'dead' },
          { deal_id: 2, deal_name: 'Deal B', old_stage: 'initial_review', new_stage: 'dead' },
        ],
        source: 'sharepoint_sync',
      });
    });

    act(() => {
      vi.advanceTimersByTime(350);
    });

    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: dealKeys.all,
    });
  });

  it('shows toast with count for batch events', () => {
    renderHook(() => useStageChangeNotifications());

    act(() => {
      capturedOnMessage!({
        type: 'batch_stage_changed',
        count: 7,
        deals: [],
        source: 'sharepoint_sync',
      });
    });

    expect(mockInfo).toHaveBeenCalledWith('7 deals moved to new stages');
  });

  it('shows singular label for batch with count=1', () => {
    renderHook(() => useStageChangeNotifications());

    act(() => {
      capturedOnMessage!({
        type: 'batch_stage_changed',
        count: 1,
        deals: [],
        source: 'sharepoint_sync',
      });
    });

    expect(mockInfo).toHaveBeenCalledWith('1 deal moved to new stages');
  });

  it('ignores unrelated message types', () => {
    renderHook(() => useStageChangeNotifications());

    act(() => {
      capturedOnMessage!({
        type: 'deal_update',
        action: 'created',
        deal_id: 99,
        data: {},
      });
    });

    act(() => {
      vi.advanceTimersByTime(350);
    });

    expect(mockInvalidateQueries).not.toHaveBeenCalled();
    expect(mockInfo).not.toHaveBeenCalled();
  });

  it('debounces rapid successive events', () => {
    renderHook(() => useStageChangeNotifications());

    // Fire 5 events in quick succession
    for (let i = 0; i < 5; i++) {
      act(() => {
        capturedOnMessage!({
          type: 'deal_update',
          action: 'stage_changed',
          deal_id: i,
          data: {
            deal_name: `Deal ${i}`,
            old_stage: 'initial_review',
            new_stage: 'dead',
            source: 'sharepoint_sync',
          },
        });
      });
    }

    act(() => {
      vi.advanceTimersByTime(350);
    });

    // invalidateQueries should only be called once due to debouncing
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(1);
  });
});
