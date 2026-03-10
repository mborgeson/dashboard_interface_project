import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  parseDate,
  isValidDate,
  formatDate,
  formatDateTime,
  formatTime,
  formatRelativeTime,
  getDateGroupLabel,
} from '../dateUtils';

// Pin "now" so relative-time tests are deterministic.
const NOW = new Date('2026-03-09T14:30:00.000Z');

describe('parseDate', () => {
  it('returns null for null', () => {
    expect(parseDate(null)).toBeNull();
  });

  it('returns null for undefined', () => {
    expect(parseDate(undefined)).toBeNull();
  });

  it('returns null for an invalid string', () => {
    expect(parseDate('not-a-date')).toBeNull();
  });

  it('returns null for an invalid Date object', () => {
    expect(parseDate(new Date('nope'))).toBeNull();
  });

  it('parses ISO strings', () => {
    const d = parseDate('2026-03-09T12:00:00Z');
    expect(d).toBeInstanceOf(Date);
    expect(d!.toISOString()).toBe('2026-03-09T12:00:00.000Z');
  });

  it('passes through valid Date objects', () => {
    const original = new Date('2026-01-15');
    expect(parseDate(original)).toBe(original);
  });

  it('parses date-only strings', () => {
    const d = parseDate('2025-12-25');
    expect(d).toBeInstanceOf(Date);
    expect(d!.getFullYear()).toBe(2025);
  });
});

describe('isValidDate', () => {
  it('returns false for null/undefined', () => {
    expect(isValidDate(null)).toBe(false);
    expect(isValidDate(undefined)).toBe(false);
  });

  it('returns false for nonsense strings', () => {
    expect(isValidDate('hello')).toBe(false);
    expect(isValidDate('')).toBe(false);
  });

  it('returns true for valid ISO string', () => {
    expect(isValidDate('2026-03-09')).toBe(true);
  });

  it('returns true for valid Date object', () => {
    expect(isValidDate(new Date())).toBe(true);
  });

  it('returns false for invalid Date object', () => {
    expect(isValidDate(new Date('nope'))).toBe(false);
  });

  it('returns true for numeric timestamps', () => {
    expect(isValidDate(Date.now())).toBe(true);
  });

  it('returns false for objects and arrays', () => {
    expect(isValidDate({})).toBe(false);
    expect(isValidDate([])).toBe(false);
  });
});

describe('formatDate', () => {
  it('returns empty string for null/undefined', () => {
    expect(formatDate(null)).toBe('');
    expect(formatDate(undefined)).toBe('');
  });

  it('returns empty string for invalid date string', () => {
    expect(formatDate('garbage')).toBe('');
  });

  it('formats medium (default) style', () => {
    // "Mar 9, 2026" or "Mar 10, 2026" depending on TZ — just check shape
    const result = formatDate('2026-03-10T00:00:00Z');
    expect(result).toMatch(/Mar \d{1,2}, 2026/);
  });

  it('formats short style', () => {
    const result = formatDate('2026-03-10T00:00:00Z', 'short');
    expect(result).toMatch(/3\/\d{1,2}\/26/);
  });

  it('formats long style', () => {
    const result = formatDate('2026-03-10T00:00:00Z', 'long');
    expect(result).toMatch(/March \d{1,2}, 2026/);
  });

  it('accepts Date objects', () => {
    const d = new Date('2025-12-25T12:00:00Z');
    const result = formatDate(d);
    expect(result).toMatch(/Dec 25, 2025/);
  });
});

describe('formatDateTime', () => {
  it('returns empty string for null', () => {
    expect(formatDateTime(null)).toBe('');
  });

  it('includes date and time components', () => {
    const result = formatDateTime('2026-03-10T14:30:00Z');
    // Should contain month, day, year, and a time component
    expect(result).toMatch(/Mar/);
    expect(result).toMatch(/2026/);
    expect(result).toMatch(/(AM|PM)/);
  });
});

describe('formatTime', () => {
  it('returns empty string for null', () => {
    expect(formatTime(null)).toBe('');
  });

  it('returns time with AM/PM', () => {
    const result = formatTime('2026-03-10T14:30:00Z');
    expect(result).toMatch(/(AM|PM)/);
  });
});

describe('formatRelativeTime', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns empty string for null/undefined', () => {
    expect(formatRelativeTime(null)).toBe('');
    expect(formatRelativeTime(undefined)).toBe('');
  });

  it('returns "just now" for very recent dates', () => {
    vi.useFakeTimers({ now: NOW });
    const thirtySecsAgo = new Date(NOW.getTime() - 30_000);
    expect(formatRelativeTime(thirtySecsAgo)).toBe('just now');
  });

  it('returns minutes ago', () => {
    vi.useFakeTimers({ now: NOW });
    const fiveMinsAgo = new Date(NOW.getTime() - 5 * 60_000);
    expect(formatRelativeTime(fiveMinsAgo)).toBe('5m ago');
  });

  it('returns hours ago', () => {
    vi.useFakeTimers({ now: NOW });
    const threeHoursAgo = new Date(NOW.getTime() - 3 * 3_600_000);
    expect(formatRelativeTime(threeHoursAgo)).toBe('3h ago');
  });

  it('returns days ago', () => {
    vi.useFakeTimers({ now: NOW });
    const twoDaysAgo = new Date(NOW.getTime() - 2 * 86_400_000);
    expect(formatRelativeTime(twoDaysAgo)).toBe('2d ago');
  });

  it('falls back to short date for >7 days', () => {
    vi.useFakeTimers({ now: NOW });
    const twoWeeksAgo = new Date(NOW.getTime() - 14 * 86_400_000);
    const result = formatRelativeTime(twoWeeksAgo);
    // Should be a formatted date, not "14d ago"
    expect(result).toMatch(/Feb/);
    expect(result).not.toMatch(/ago/);
  });

  it('includes year for dates in a different year', () => {
    vi.useFakeTimers({ now: NOW });
    const lastYear = new Date('2025-06-15T12:00:00Z');
    const result = formatRelativeTime(lastYear);
    expect(result).toMatch(/2025/);
  });

  it('accepts string input', () => {
    vi.useFakeTimers({ now: NOW });
    const isoStr = new Date(NOW.getTime() - 120_000).toISOString();
    expect(formatRelativeTime(isoStr)).toBe('2m ago');
  });
});

describe('getDateGroupLabel', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns empty string for null/undefined', () => {
    expect(getDateGroupLabel(null)).toBe('');
    expect(getDateGroupLabel(undefined)).toBe('');
  });

  it('returns "Today" for today', () => {
    vi.useFakeTimers({ now: NOW });
    expect(getDateGroupLabel(NOW)).toBe('Today');
  });

  it('returns "Yesterday" for yesterday', () => {
    vi.useFakeTimers({ now: NOW });
    const yesterday = new Date(NOW.getTime() - 86_400_000);
    expect(getDateGroupLabel(yesterday)).toBe('Yesterday');
  });

  it('returns weekday name for dates within 7 days', () => {
    vi.useFakeTimers({ now: NOW });
    // 3 days ago
    const threeDaysAgo = new Date(NOW.getTime() - 3 * 86_400_000);
    const result = getDateGroupLabel(threeDaysAgo);
    // Should be a weekday name like "Friday", "Saturday", etc.
    expect(result).toMatch(
      /^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)$/,
    );
  });

  it('returns long date for older dates in same year', () => {
    vi.useFakeTimers({ now: NOW });
    const twoWeeksAgo = new Date('2026-02-15T12:00:00Z');
    const result = getDateGroupLabel(twoWeeksAgo);
    expect(result).toMatch(/February 15/);
    // Should NOT include year since it's same year
    expect(result).not.toMatch(/2026/);
  });

  it('includes year for dates in a different year', () => {
    vi.useFakeTimers({ now: NOW });
    const result = getDateGroupLabel('2025-06-15T12:00:00Z');
    expect(result).toMatch(/June 15, 2025/);
  });
});
