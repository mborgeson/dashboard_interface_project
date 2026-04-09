import { describe, it, expect } from 'vitest';
import { z } from 'zod';

// Import after we rename — for now, test the desired behavior
describe('safeOptionalNum', () => {
  const safeOptionalNum = z.preprocess(
    (v) => {
      if (v === null || v === undefined) return undefined;
      const n = Number(v);
      return Number.isFinite(n) ? n : undefined;
    },
    z.number().optional(),
  );

  it('returns undefined for null', () => {
    expect(safeOptionalNum.parse(null)).toBeUndefined();
  });

  it('returns undefined for undefined', () => {
    expect(safeOptionalNum.parse(undefined)).toBeUndefined();
  });

  it('returns undefined for NaN-producing strings', () => {
    expect(safeOptionalNum.parse('Period Start')).toBeUndefined();
  });

  it('returns the number for valid numeric input', () => {
    expect(safeOptionalNum.parse(0.055)).toBe(0.055);
  });

  it('returns 0 for actual zero (does NOT coerce to undefined)', () => {
    expect(safeOptionalNum.parse(0)).toBe(0);
  });

  it('returns the number for numeric strings', () => {
    expect(safeOptionalNum.parse('38000000')).toBe(38000000);
  });
});
