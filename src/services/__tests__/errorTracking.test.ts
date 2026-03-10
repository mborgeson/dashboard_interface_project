import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  initErrorTracking,
  reportError,
  reportComponentError,
  _resetForTesting,
  _getBuffer,
  _flush,
} from '../errorTracking';

beforeEach(() => {
  _resetForTesting();
  vi.restoreAllMocks();
});

afterEach(() => {
  _resetForTesting();
});

// ---------------------------------------------------------------------------
// reportError
// ---------------------------------------------------------------------------

describe('reportError', () => {
  it('captures error details into the buffer', () => {
    const err = new Error('test failure');
    reportError(err, { page: 'dashboard' });

    const buf = _getBuffer();
    expect(buf).toHaveLength(1);
    expect(buf[0].message).toBe('test failure');
    expect(buf[0].stack).toBeDefined();
    expect(buf[0].context).toEqual({ page: 'dashboard' });
    expect(buf[0].timestamp).toBeTruthy();
    expect(buf[0].url).toBeDefined();
    expect(buf[0].userAgent).toBeDefined();
  });

  it('captures multiple errors', () => {
    reportError(new Error('err1'));
    reportError(new Error('err2'));
    expect(_getBuffer()).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// reportComponentError
// ---------------------------------------------------------------------------

describe('reportComponentError', () => {
  it('captures error with componentStack', () => {
    const err = new Error('render boom');
    reportComponentError(err, '\n    in Header\n    in App');

    const buf = _getBuffer();
    expect(buf).toHaveLength(1);
    expect(buf[0].message).toBe('render boom');
    expect(buf[0].componentStack).toBe('\n    in Header\n    in App');
  });
});

// ---------------------------------------------------------------------------
// Rate limiting
// ---------------------------------------------------------------------------

describe('rate limiting', () => {
  it('drops errors after MAX_ERRORS_PER_MINUTE (10) in the same window', () => {
    for (let i = 0; i < 15; i++) {
      reportError(new Error(`err-${i}`));
    }
    // Only the first 10 should make it through
    expect(_getBuffer()).toHaveLength(10);
  });
});

// ---------------------------------------------------------------------------
// Dev mode flush
// ---------------------------------------------------------------------------

describe('flush in dev mode', () => {
  it('logs to console.warn instead of fetching', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    reportError(new Error('dev error'));
    await _flush();

    expect(warnSpy).toHaveBeenCalledWith(
      '[ErrorTracking]',
      'dev error',
      expect.objectContaining({ message: 'dev error' }),
    );
    expect(fetchSpy).not.toHaveBeenCalled();

    // Buffer should be drained
    expect(_getBuffer()).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// initErrorTracking
// ---------------------------------------------------------------------------

describe('initErrorTracking', () => {
  it('adds global event listeners', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');
    initErrorTracking();

    const eventTypes = addSpy.mock.calls.map((c) => c[0]);
    expect(eventTypes).toContain('error');
    expect(eventTypes).toContain('unhandledrejection');
    expect(eventTypes).toContain('visibilitychange');
  });

  it('is idempotent — calling twice does not double-register', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');

    initErrorTracking();
    const firstCallCount = addSpy.mock.calls.length;

    initErrorTracking();
    expect(addSpy.mock.calls.length).toBe(firstCallCount);
  });
});
