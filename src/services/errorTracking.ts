/**
 * Lightweight frontend error tracking service.
 *
 * Captures unhandled errors, promise rejections, and React error boundary
 * catches, then batch-sends them to the backend for logging.
 */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const ERRORS_ENDPOINT = `${API_BASE_URL}/errors/report`;

const MAX_ERRORS_PER_MINUTE = 10;
const FLUSH_INTERVAL_MS = 5_000;
const MAX_BUFFER_SIZE = 50;

interface ErrorReport {
  message: string;
  stack: string | undefined;
  componentStack?: string;
  context?: Record<string, unknown>;
  timestamp: string;
  url: string;
  userAgent: string;
}

// ---------------------------------------------------------------------------
// Internal state
// ---------------------------------------------------------------------------

let buffer: ErrorReport[] = [];
let errorCountThisWindow = 0;
let windowResetTimer: ReturnType<typeof setTimeout> | null = null;
let flushTimer: ReturnType<typeof setInterval> | null = null;
let initialized = false;

// ---------------------------------------------------------------------------
// Rate limiting
// ---------------------------------------------------------------------------

function startRateLimitWindow(): void {
  if (windowResetTimer !== null) return;
  windowResetTimer = setTimeout(() => {
    errorCountThisWindow = 0;
    windowResetTimer = null;
  }, 60_000);
}

function isRateLimited(): boolean {
  return errorCountThisWindow >= MAX_ERRORS_PER_MINUTE;
}

function incrementErrorCount(): void {
  startRateLimitWindow();
  errorCountThisWindow++;
}

// ---------------------------------------------------------------------------
// Buffer & flush
// ---------------------------------------------------------------------------

function enqueue(report: ErrorReport): void {
  if (buffer.length >= MAX_BUFFER_SIZE) {
    // Drop oldest to prevent unbounded growth
    buffer.shift();
  }
  buffer.push(report);
}

async function flush(): Promise<void> {
  if (buffer.length === 0) return;

  const batch = buffer.splice(0, buffer.length);

  if (import.meta.env.DEV) {
    // In development, log to console instead of sending to backend
    for (const report of batch) {
      console.warn('[ErrorTracking]', report.message, report);
    }
    return;
  }

  try {
    await fetch(ERRORS_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ errors: batch }),
      // Fire-and-forget; don't block the app
      keepalive: true,
    });
  } catch {
    // Silently drop — we don't want error tracking to cause errors
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Report an error. If the rate limit has been hit the error is silently
 * dropped. In dev mode, errors are logged to the console on the next flush
 * rather than sent over the network.
 */
export function reportError(
  error: Error,
  context?: Record<string, unknown>,
): void {
  if (isRateLimited()) return;
  incrementErrorCount();

  const report: ErrorReport = {
    message: error.message,
    stack: error.stack,
    context,
    timestamp: new Date().toISOString(),
    url: globalThis.location?.href ?? '',
    userAgent: globalThis.navigator?.userAgent ?? '',
  };

  enqueue(report);
}

/**
 * Report an error caught by a React error boundary, including the React
 * component stack trace.
 */
export function reportComponentError(
  error: Error,
  componentStack: string,
): void {
  if (isRateLimited()) return;
  incrementErrorCount();

  const report: ErrorReport = {
    message: error.message,
    stack: error.stack,
    componentStack,
    timestamp: new Date().toISOString(),
    url: globalThis.location?.href ?? '',
    userAgent: globalThis.navigator?.userAgent ?? '',
  };

  enqueue(report);
}

/**
 * Set up global error listeners and start the flush interval.
 * Safe to call multiple times — subsequent calls are no-ops.
 */
export function initErrorTracking(): void {
  if (initialized) return;
  initialized = true;

  // Capture uncaught errors
  window.addEventListener('error', (event: ErrorEvent) => {
    const error =
      event.error instanceof Error
        ? event.error
        : new Error(event.message || 'Unknown error');
    reportError(error, { source: 'window.onerror' });
  });

  // Capture unhandled promise rejections
  window.addEventListener(
    'unhandledrejection',
    (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const error =
        reason instanceof Error
          ? reason
          : new Error(String(reason ?? 'Unhandled promise rejection'));
      reportError(error, { source: 'unhandledrejection' });
    },
  );

  // Periodically flush the buffer
  flushTimer = setInterval(() => {
    void flush();
  }, FLUSH_INTERVAL_MS);

  // Flush on page unload so we don't lose errors
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      void flush();
    }
  });
}

// ---------------------------------------------------------------------------
// Test helpers — only exported for unit tests
// ---------------------------------------------------------------------------

export function _resetForTesting(): void {
  buffer = [];
  errorCountThisWindow = 0;
  if (windowResetTimer !== null) {
    clearTimeout(windowResetTimer);
    windowResetTimer = null;
  }
  if (flushTimer !== null) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
  initialized = false;
}

export function _getBuffer(): ErrorReport[] {
  return buffer;
}

export function _flush(): Promise<void> {
  return flush();
}
