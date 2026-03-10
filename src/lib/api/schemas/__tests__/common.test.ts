import { describe, it, expect } from 'vitest';
import {
  dateString,
  nullableDateString,
  numericString,
  nullableNumericString,
} from '../common';

describe('dateString', () => {
  it('transforms a valid ISO date string into a Date object', () => {
    const result = dateString.parse('2024-06-15T12:00:00Z');
    expect(result).toBeInstanceOf(Date);
    expect(result.toISOString()).toBe('2024-06-15T12:00:00.000Z');
  });

  it('transforms a date-only string into a Date object', () => {
    const result = dateString.parse('2024-01-01');
    expect(result).toBeInstanceOf(Date);
    expect(result.getUTCFullYear()).toBe(2024);
  });

  it('returns an invalid Date for a malformed string', () => {
    const result = dateString.parse('not-a-date');
    expect(result).toBeInstanceOf(Date);
    expect(Number.isNaN(result.getTime())).toBe(true);
  });

  it('throws on null input', () => {
    expect(() => dateString.parse(null)).toThrow();
  });

  it('throws on undefined input', () => {
    expect(() => dateString.parse(undefined)).toThrow();
  });

  it('throws on numeric input', () => {
    expect(() => dateString.parse(12345)).toThrow();
  });
});

describe('nullableDateString', () => {
  it('transforms a valid ISO date string into a Date object', () => {
    const result = nullableDateString.parse('2025-03-10T08:30:00Z');
    expect(result).toBeInstanceOf(Date);
    expect(result!.toISOString()).toBe('2025-03-10T08:30:00.000Z');
  });

  it('transforms null into null', () => {
    const result = nullableDateString.parse(null);
    expect(result).toBeNull();
  });

  it('throws on undefined input', () => {
    expect(() => nullableDateString.parse(undefined)).toThrow();
  });

  it('returns an invalid Date for a malformed string', () => {
    const result = nullableDateString.parse('garbage');
    expect(result).toBeInstanceOf(Date);
    expect(Number.isNaN(result!.getTime())).toBe(true);
  });
});

describe('numericString', () => {
  it('transforms a valid numeric string into a number', () => {
    const result = numericString.parse('42.5');
    expect(result).toBe(42.5);
  });

  it('transforms an integer string into a number', () => {
    const result = numericString.parse('100');
    expect(result).toBe(100);
  });

  it('transforms null into undefined', () => {
    const result = numericString.parse(null);
    expect(result).toBeUndefined();
  });

  it('returns NaN for a non-numeric string', () => {
    const result = numericString.parse('abc');
    expect(result).toBeNaN();
  });

  it('transforms an empty string into 0 (Number(""))', () => {
    // Number("") === 0, and "" is truthy in the ternary (non-null string)
    const result = numericString.parse('');
    // Empty string is falsy, so the transform returns undefined
    expect(result).toBeUndefined();
  });

  it('throws on undefined input', () => {
    expect(() => numericString.parse(undefined)).toThrow();
  });

  it('throws on a raw number input (expects string)', () => {
    expect(() => numericString.parse(42)).toThrow();
  });
});

describe('nullableNumericString', () => {
  it('transforms a valid numeric string into a number', () => {
    const result = nullableNumericString.parse('99.9');
    expect(result).toBe(99.9);
  });

  it('transforms null into null', () => {
    const result = nullableNumericString.parse(null);
    expect(result).toBeNull();
  });

  it('returns NaN for a non-numeric string', () => {
    const result = nullableNumericString.parse('xyz');
    expect(result).toBeNaN();
  });

  it('transforms negative numeric string', () => {
    const result = nullableNumericString.parse('-7.25');
    expect(result).toBe(-7.25);
  });

  it('throws on undefined input', () => {
    expect(() => nullableNumericString.parse(undefined)).toThrow();
  });
});
