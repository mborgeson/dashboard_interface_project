import { describe, it, expect } from 'vitest';
import { formatCurrency, formatPercent, formatNumber, formatDate, formatChange } from '../formatters';

describe('formatCurrency', () => {
  it('formats standard values', () => {
    expect(formatCurrency(1500)).toBe('$1,500');
    expect(formatCurrency(0)).toBe('$0');
    expect(formatCurrency(999999)).toBe('$999,999');
  });

  it('formats compact millions', () => {
    expect(formatCurrency(1500000, true)).toBe('$1.5M');
    expect(formatCurrency(25000000, true)).toBe('$25.0M');
  });

  it('formats compact thousands', () => {
    expect(formatCurrency(5000, true)).toBe('$5K');
    expect(formatCurrency(1500, true)).toBe('$2K');
  });

  it('formats small values in compact mode normally', () => {
    expect(formatCurrency(500, true)).toBe('$500');
  });
});

describe('formatPercent', () => {
  it('formats decimal as percentage', () => {
    expect(formatPercent(0.15)).toBe('15.0%');
    expect(formatPercent(0.0488)).toBe('4.9%');
  });

  it('respects decimal places', () => {
    expect(formatPercent(0.15, 0)).toBe('15%');
    expect(formatPercent(0.15, 2)).toBe('15.00%');
  });

  it('handles negative values', () => {
    expect(formatPercent(-0.049)).toBe('-4.9%');
  });
});

describe('formatNumber', () => {
  it('adds thousand separators', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
    expect(formatNumber(42)).toBe('42');
  });
});

describe('formatDate', () => {
  it('returns -- for null/undefined', () => {
    expect(formatDate(null)).toBe('--');
    expect(formatDate(undefined)).toBe('--');
  });

  it('formats medium (default)', () => {
    const d = new Date('2026-03-06T00:00:00');
    const result = formatDate(d);
    expect(result).toContain('Mar');
    expect(result).toContain('2026');
  });

  it('formats short', () => {
    const d = new Date('2026-03-06T00:00:00');
    const result = formatDate(d, 'short');
    expect(result).toContain('3');
    expect(result).toContain('26');
  });

  it('formats long', () => {
    const d = new Date('2026-03-06T00:00:00');
    const result = formatDate(d, 'long');
    expect(result).toContain('March');
    expect(result).toContain('2026');
  });
});

describe('formatChange', () => {
  it('formats positive currency change', () => {
    const r = formatChange(500000);
    expect(r.text).toContain('+');
    expect(r.colorClass).toBe('text-green-600');
  });

  it('formats negative currency change', () => {
    const r = formatChange(-200000);
    expect(r.text).not.toContain('+');
    expect(r.colorClass).toBe('text-red-600');
  });

  it('formats positive percent change', () => {
    const r = formatChange(0.05, true);
    expect(r.text).toContain('+');
    expect(r.text).toContain('%');
    expect(r.colorClass).toBe('text-green-600');
  });

  it('formats negative percent change', () => {
    const r = formatChange(-0.03, true);
    expect(r.text).toContain('%');
    expect(r.colorClass).toBe('text-red-600');
  });

  it('treats zero as positive', () => {
    const r = formatChange(0);
    expect(r.colorClass).toBe('text-green-600');
  });
});
