/**
 * React hook for connecting to WebSocket channels with auto-reconnect.
 *
 * Usage:
 *   const { status, lastMessage, sendMessage } = useWebSocket('deals');
 *
 * Features:
 * - Auto-reconnect with exponential backoff
 * - Typed message discrimination via `type` field
 * - Connection state tracking (connecting, open, closing, closed)
 * - Automatic pong response to server pings
 * - Subscribe/unsubscribe to additional channels at runtime
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { API_URL } from '@/lib/config';
import { useAuthStore } from '@/stores/authStore';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Connection status mirroring WebSocket readyState semantics. */
export type ConnectionStatus = 'connecting' | 'open' | 'closing' | 'closed';

/** Base shape for every message coming from the server. */
export interface WSMessage {
  type: string;
  timestamp?: string;
  [key: string]: unknown;
}

/** Options for the hook. */
export interface UseWebSocketOptions {
  /** Whether the connection should be active (default true). */
  enabled?: boolean;
  /** Max reconnect attempts before giving up (default 10). */
  maxRetries?: number;
  /** Base delay in ms for exponential backoff (default 1000). */
  baseDelay?: number;
  /** Maximum backoff delay in ms (default 30000). */
  maxDelay?: number;
  /** Called when the connection opens. */
  onOpen?: () => void;
  /** Called when the connection closes. */
  onClose?: (event: CloseEvent) => void;
  /** Called on every incoming message. */
  onMessage?: (message: WSMessage) => void;
  /** Called on connection error. */
  onError?: (event: Event) => void;
}

export interface UseWebSocketReturn {
  /** Current connection status. */
  status: ConnectionStatus;
  /** Most recent message received from the server. */
  lastMessage: WSMessage | null;
  /** Send a JSON message to the server. */
  sendMessage: (data: Record<string, unknown>) => void;
  /** Subscribe to an additional channel. */
  subscribe: (channel: string) => void;
  /** Unsubscribe from a channel. */
  unsubscribe: (channel: string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive the WebSocket base URL from the HTTP API URL. */
function getWsBaseUrl(): string {
  // API_URL is e.g. "http://localhost:8000/api/v1"
  // We need "ws://localhost:8000/api/v1"
  return API_URL.replace(/^http/, 'ws');
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWebSocket(
  channel: string,
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const {
    enabled = true,
    maxRetries = 10,
    baseDelay = 1_000,
    maxDelay = 30_000,
    onOpen,
    onClose,
    onMessage,
    onError,
  } = options;

  const [status, setStatus] = useState<ConnectionStatus>('closed');
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  // Stable references for callbacks so effect doesn't re-run on every render
  const callbacksRef = useRef({ onOpen, onClose, onMessage, onError });
  callbacksRef.current = { onOpen, onClose, onMessage, onError };

  // -----------------------------------------------------------------------
  // Connect / reconnect
  // -----------------------------------------------------------------------

  const connectWs = useCallback(() => {
    if (unmountedRef.current) return;

    const accessToken = useAuthStore.getState().accessToken;
    const base = getWsBaseUrl();
    const params = accessToken ? `?token=${encodeURIComponent(accessToken)}` : '';
    const url = `${base}/ws/${encodeURIComponent(channel)}${params}`;

    setStatus('connecting');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmountedRef.current) return;
      setStatus('open');
      retriesRef.current = 0;
      callbacksRef.current.onOpen?.();
    };

    ws.onmessage = (event: MessageEvent) => {
      if (unmountedRef.current) return;
      try {
        const msg: WSMessage = JSON.parse(event.data as string);

        // Auto-respond to server pings
        if (msg.type === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }

        setLastMessage(msg);
        callbacksRef.current.onMessage?.(msg);
      } catch {
        // Non-JSON message — ignore
      }
    };

    ws.onerror = (event: Event) => {
      if (unmountedRef.current) return;
      callbacksRef.current.onError?.(event);
    };

    ws.onclose = (event: CloseEvent) => {
      if (unmountedRef.current) return;
      setStatus('closed');
      wsRef.current = null;
      callbacksRef.current.onClose?.(event);

      // Attempt reconnect with exponential backoff
      if (enabled && retriesRef.current < maxRetries) {
        const delay = Math.min(
          baseDelay * 2 ** retriesRef.current,
          maxDelay,
        );
        retriesRef.current += 1;
        reconnectTimerRef.current = setTimeout(connectWs, delay);
      }
    };
  }, [channel, enabled, maxRetries, baseDelay, maxDelay]);

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  useEffect(() => {
    unmountedRef.current = false;

    if (enabled) {
      connectWs();
    }

    return () => {
      unmountedRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connectWs, enabled]);

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const subscribe = useCallback(
    (ch: string) => sendMessage({ type: 'subscribe', channel: ch }),
    [sendMessage],
  );

  const unsubscribe = useCallback(
    (ch: string) => sendMessage({ type: 'unsubscribe', channel: ch }),
    [sendMessage],
  );

  return { status, lastMessage, sendMessage, subscribe, unsubscribe };
}
