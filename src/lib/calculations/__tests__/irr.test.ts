import { describe, it, expect } from 'vitest';
import { calculateIRR, calculateNPV, calculateEquityMultiple, calculateCashOnCash } from '../irr';

// =============================================================================
// calculateIRR — Newton-Raphson IRR
// =============================================================================

describe('calculateIRR', () => {
  // --- Normal cases ---

  it('calculates IRR for a simple 5-year investment', () => {
    // -$100K upfront, $30K/year for 5 years => ~15.24% IRR
    const cashFlows = [-100_000, 30_000, 30_000, 30_000, 30_000, 30_000];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeCloseTo(0.1524, 2);
  });

  it('calculates IRR for a typical B&R Capital Class B multifamily deal', () => {
    // $15M purchase, 75% LTV => ~$3.75M equity
    // 5-year hold: annual cash flows from operations + sale proceeds in year 5
    const cashFlows = [
      -3_750_000, // Year 0: equity investment
       300_000,   // Year 1: cash flow after debt service
       330_000,   // Year 2: rent growth kicks in
       360_000,   // Year 3
       390_000,   // Year 4
       5_200_000, // Year 5: cash flow + sale proceeds (exit at lower cap rate)
    ];
    const irr = calculateIRR(cashFlows);
    // Typical Class B Phoenix deal targets 15-20% levered IRR
    expect(irr).toBeGreaterThan(0.10);
    expect(irr).toBeLessThan(0.30);
  });

  it('calculates IRR for a large 200-unit Phoenix deal', () => {
    // $25M purchase, $6.25M equity, 7-year hold
    const cashFlows = [
      -6_250_000,
       500_000,
       550_000,
       600_000,
       650_000,
       700_000,
       750_000,
       9_500_000, // Year 7: operations + sale
    ];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeGreaterThan(0.08);
    expect(irr).toBeLessThan(0.25);
  });

  it('calculates zero IRR when total returns equal investment', () => {
    // -$100K invested, get back exactly $100K over time => IRR ~ 0%
    const cashFlows = [-100_000, 20_000, 20_000, 20_000, 20_000, 20_000];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeCloseTo(0, 1);
  });

  it('calculates high IRR for value-add deal with quick turnaround', () => {
    // Aggressive value-add: heavy reno, lease-up, flip in 3 years
    const cashFlows = [-2_000_000, -100_000, 200_000, 4_500_000];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeGreaterThan(0.20);
  });

  it('calculates negative IRR for underperforming deal', () => {
    // Money-losing deal — bought at wrong basis
    const cashFlows = [-5_000_000, 100_000, 50_000, 80_000, 60_000, 3_000_000];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeLessThan(0);
  });

  // --- Single period / minimal cash flows ---

  it('handles two-period cash flow', () => {
    // -$100 now, $110 in one year => 10% IRR
    const cashFlows = [-100, 110];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeCloseTo(0.10, 2);
  });

  it('handles doubling investment in one year', () => {
    const cashFlows = [-100, 200];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeCloseTo(1.0, 2); // 100% IRR
  });

  // --- Many periods ---

  it('handles 10-year hold period', () => {
    // 10-year hold with growing cash flows
    const cashFlows = [
      -4_000_000,
       300_000, 320_000, 340_000, 360_000, 380_000,
       400_000, 420_000, 440_000, 460_000,
       6_500_000, // Year 10: cash flow + sale
    ];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeGreaterThan(0.05);
    expect(irr).toBeLessThan(0.20);
  });

  // --- Edge cases ---

  it('handles all positive cash flows', () => {
    // No initial investment — unusual but should not crash
    const cashFlows = [100, 200, 300];
    const result = calculateIRR(cashFlows);
    // Result may be very large or NaN-ish; just ensure it returns a number
    expect(typeof result).toBe('number');
  });

  it('handles all negative cash flows', () => {
    const cashFlows = [-100, -200, -300];
    const result = calculateIRR(cashFlows);
    expect(typeof result).toBe('number');
  });

  it('handles all zero cash flows', () => {
    const cashFlows = [0, 0, 0, 0];
    const result = calculateIRR(cashFlows);
    expect(typeof result).toBe('number');
  });

  it('handles very large cash flows ($50M deal)', () => {
    const cashFlows = [
      -12_500_000,
       1_000_000,
       1_100_000,
       1_200_000,
       1_300_000,
       18_000_000,
    ];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeGreaterThan(0.05);
    expect(irr).toBeLessThan(0.30);
  });

  it('handles very small cash flows', () => {
    const cashFlows = [-1, 0.05, 0.05, 0.05, 0.05, 1.2];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeGreaterThan(0);
  });
});

// =============================================================================
// calculateNPV
// =============================================================================

describe('calculateNPV', () => {
  it('calculates NPV at 0% discount rate (sum of cash flows)', () => {
    const cashFlows = [-100_000, 30_000, 30_000, 30_000, 30_000, 30_000];
    const npv = calculateNPV(cashFlows, 0);
    expect(npv).toBeCloseTo(50_000, 0);
  });

  it('calculates NPV at 10% discount rate', () => {
    const cashFlows = [-100_000, 30_000, 30_000, 30_000, 30_000, 30_000];
    const npv = calculateNPV(cashFlows, 0.10);
    // NPV should be positive but less than undiscounted sum
    expect(npv).toBeGreaterThan(0);
    expect(npv).toBeLessThan(50_000);
  });

  it('NPV is zero at the IRR', () => {
    const cashFlows = [-100_000, 30_000, 30_000, 30_000, 30_000, 30_000];
    const irr = calculateIRR(cashFlows);
    const npv = calculateNPV(cashFlows, irr);
    expect(npv).toBeCloseTo(0, 0);
  });

  it('NPV decreases as discount rate increases', () => {
    const cashFlows = [-100_000, 40_000, 40_000, 40_000];
    const npv5 = calculateNPV(cashFlows, 0.05);
    const npv10 = calculateNPV(cashFlows, 0.10);
    const npv20 = calculateNPV(cashFlows, 0.20);
    expect(npv5).toBeGreaterThan(npv10);
    expect(npv10).toBeGreaterThan(npv20);
  });

  it('handles empty cash flow array', () => {
    expect(calculateNPV([], 0.1)).toBe(0);
  });

  it('handles single cash flow (present value of lump sum)', () => {
    // $100 today at any rate is just $100
    expect(calculateNPV([100], 0.10)).toBe(100);
  });

  it('calculates NPV for multifamily acquisition', () => {
    // $20M deal, 5-year hold
    const cashFlows = [
      -5_000_000,  // equity
       400_000,
       440_000,
       480_000,
       520_000,
       7_000_000,  // exit year
    ];
    const npv = calculateNPV(cashFlows, 0.08);
    // Should be positive if deal exceeds 8% hurdle
    expect(npv).toBeGreaterThan(0);
  });

  it('returns negative NPV when discount rate exceeds returns', () => {
    const cashFlows = [-100_000, 20_000, 20_000, 20_000, 20_000, 20_000];
    // These flows have ~0% IRR, so 10% discount => negative NPV
    const npv = calculateNPV(cashFlows, 0.10);
    expect(npv).toBeLessThan(0);
  });
});

// =============================================================================
// calculateEquityMultiple
// =============================================================================

describe('calculateEquityMultiple', () => {
  it('calculates 2.0x equity multiple', () => {
    // $4M total distributions on $2M investment
    expect(calculateEquityMultiple(4_000_000, 2_000_000)).toBeCloseTo(2.0);
  });

  it('calculates typical Class B multifamily MOIC (1.7-2.2x)', () => {
    // $3.75M equity, total distributions over 5 years = $6.75M
    const multiple = calculateEquityMultiple(6_750_000, 3_750_000);
    expect(multiple).toBeCloseTo(1.8, 1);
  });

  it('calculates 1.0x (break-even)', () => {
    expect(calculateEquityMultiple(100_000, 100_000)).toBeCloseTo(1.0);
  });

  it('calculates less than 1.0x (loss)', () => {
    expect(calculateEquityMultiple(80_000, 100_000)).toBeCloseTo(0.8);
  });

  it('handles large deal equity ($10M+)', () => {
    const multiple = calculateEquityMultiple(25_000_000, 12_500_000);
    expect(multiple).toBeCloseTo(2.0);
  });

  it('handles zero distributions', () => {
    expect(calculateEquityMultiple(0, 100_000)).toBe(0);
  });

  it('handles division by zero (zero investment)', () => {
    // This function does raw division — may return Infinity
    const result = calculateEquityMultiple(100_000, 0);
    expect(result).toBe(Infinity);
  });
});

// =============================================================================
// calculateCashOnCash
// =============================================================================

describe('calculateCashOnCash', () => {
  it('calculates 8% cash-on-cash return', () => {
    // $300K annual cash flow on $3.75M equity
    expect(calculateCashOnCash(300_000, 3_750_000)).toBeCloseTo(0.08, 2);
  });

  it('calculates typical Year 1 CoC for Class B Phoenix deal', () => {
    // Typical target: 6-8% Year 1 CoC
    const coc = calculateCashOnCash(240_000, 3_000_000);
    expect(coc).toBeCloseTo(0.08, 2);
  });

  it('handles zero annual cash flow', () => {
    expect(calculateCashOnCash(0, 1_000_000)).toBe(0);
  });

  it('handles negative cash flow (operational loss)', () => {
    const coc = calculateCashOnCash(-50_000, 1_000_000);
    expect(coc).toBeCloseTo(-0.05);
  });

  it('handles division by zero investment', () => {
    const result = calculateCashOnCash(100_000, 0);
    expect(result).toBe(Infinity);
  });

  it('handles large-scale deal', () => {
    // 200-unit deal: $50K/unit => $10M, 75% LTV, $2.5M equity
    // Year 1 NOI after debt: $200K
    const coc = calculateCashOnCash(200_000, 2_500_000);
    expect(coc).toBeCloseTo(0.08, 2);
  });
});
