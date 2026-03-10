import { describe, it, expect } from 'vitest';
import {
  calculateDebtService,
  calculateDSCR,
  calculateLTV,
  calculateYieldOnCost,
  calculateIRR,
  calculateEquityMultiple,
  calculateLoanBalance,
  calculateBreakEvenOccupancy,
  calculateEffectiveRent,
  calculatePricePerUnit,
  calculatePricePerSF,
} from '../calculations';

// =============================================================================
// Debt Service
// =============================================================================

describe('calculateDebtService', () => {
  it('calculates standard amortizing monthly payment', () => {
    // $10M loan, 5% rate, 30-year amortization
    const payment = calculateDebtService(10_000_000, 0.05, 30);
    // Expected ~$53,682/month
    expect(payment).toBeCloseTo(53682.16, 0);
  });

  it('calculates interest-only payment when amortization is 0', () => {
    // $10M loan, 5% rate, interest-only
    const payment = calculateDebtService(10_000_000, 0.05, 0);
    expect(payment).toBeCloseTo(41666.67, 0);
  });

  it('handles zero interest rate', () => {
    // $10M loan, 0% rate, 25-year amortization
    const payment = calculateDebtService(10_000_000, 0, 25);
    expect(payment).toBeCloseTo(10_000_000 / (25 * 12), 2);
  });

  it('returns 0 for zero loan amount', () => {
    const payment = calculateDebtService(0, 0.05, 30);
    expect(payment).toBe(0);
  });
});

// =============================================================================
// DSCR
// =============================================================================

describe('calculateDSCR', () => {
  it('calculates DSCR correctly', () => {
    // NOI: $750K, Debt service: $500K => DSCR 1.5x
    expect(calculateDSCR(750_000, 500_000)).toBeCloseTo(1.5);
  });

  it('returns 0 when debt service is 0', () => {
    expect(calculateDSCR(750_000, 0)).toBe(0);
  });

  it('handles negative NOI', () => {
    expect(calculateDSCR(-100_000, 500_000)).toBeCloseTo(-0.2);
  });
});

// =============================================================================
// LTV
// =============================================================================

describe('calculateLTV', () => {
  it('calculates LTV ratio', () => {
    // $7.5M loan on $10M property = 75% LTV
    expect(calculateLTV(7_500_000, 10_000_000)).toBeCloseTo(0.75);
  });

  it('returns 0 when property value is 0', () => {
    expect(calculateLTV(1_000_000, 0)).toBe(0);
  });
});

// =============================================================================
// Yield on Cost
// =============================================================================

describe('calculateYieldOnCost', () => {
  it('calculates yield on cost', () => {
    // NOI: $600K, Total basis: $10M = 6.0% yield
    expect(calculateYieldOnCost(600_000, 10_000_000)).toBeCloseTo(0.06);
  });

  it('returns 0 when total basis is 0', () => {
    expect(calculateYieldOnCost(600_000, 0)).toBe(0);
  });
});

// =============================================================================
// IRR
// =============================================================================

describe('calculateIRR', () => {
  it('calculates IRR for simple cash flows', () => {
    // -$100K investment, then $30K/year for 5 years
    const cashFlows = [-100_000, 30_000, 30_000, 30_000, 30_000, 30_000];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeCloseTo(0.1525, 2); // ~15.25%
  });

  it('returns 0 for single cash flow', () => {
    expect(calculateIRR([-100_000])).toBe(0);
  });

  it('returns 0 for empty array', () => {
    expect(calculateIRR([])).toBe(0);
  });

  it('calculates IRR for typical multifamily deal', () => {
    // $2M equity investment, 5-year hold with distributions + sale
    const cashFlows = [-2_000_000, 160_000, 170_000, 180_000, 190_000, 2_800_000];
    const irr = calculateIRR(cashFlows);
    expect(irr).toBeGreaterThan(0.10);
    expect(irr).toBeLessThan(0.25);
  });
});

// =============================================================================
// Equity Multiple
// =============================================================================

describe('calculateEquityMultiple', () => {
  it('calculates equity multiple', () => {
    // $200K total return on $100K equity = 2.0x
    expect(calculateEquityMultiple(200_000, 100_000)).toBeCloseTo(2.0);
  });

  it('returns 0 for zero initial equity', () => {
    expect(calculateEquityMultiple(200_000, 0)).toBe(0);
  });
});

// =============================================================================
// Loan Balance
// =============================================================================

describe('calculateLoanBalance', () => {
  it('returns full loan amount at month 0', () => {
    const balance = calculateLoanBalance(10_000_000, 0.05, 30, 0);
    expect(balance).toBe(10_000_000);
  });

  it('returns full balance during interest-only period', () => {
    const balance = calculateLoanBalance(10_000_000, 0.05, 30, 12, 2);
    // 12 months elapsed, 2-year IO period => still in IO
    expect(balance).toBe(10_000_000);
  });

  it('reduces balance after amortization begins', () => {
    const balance = calculateLoanBalance(10_000_000, 0.05, 30, 60, 0);
    // After 5 years of amortization, balance should be less
    expect(balance).toBeLessThan(10_000_000);
    expect(balance).toBeGreaterThan(0);
  });

  it('balance approaches 0 near end of amortization', () => {
    const balance = calculateLoanBalance(10_000_000, 0.05, 30, 359, 0);
    // Near end of 30-year term
    expect(balance).toBeLessThan(100_000);
  });
});

// =============================================================================
// Break-Even Occupancy
// =============================================================================

describe('calculateBreakEvenOccupancy', () => {
  it('calculates break-even occupancy', () => {
    // OpEx: $400K, Debt: $500K, GPI: $1.2M => 75%
    expect(calculateBreakEvenOccupancy(400_000, 500_000, 1_200_000)).toBeCloseTo(0.75);
  });

  it('returns 0 when GPI is 0', () => {
    expect(calculateBreakEvenOccupancy(400_000, 500_000, 0)).toBe(0);
  });
});

// =============================================================================
// Effective Rent
// =============================================================================

describe('calculateEffectiveRent', () => {
  it('applies concession discount', () => {
    // $1,500 market rent with 5% concession
    expect(calculateEffectiveRent(1_500, 0.05)).toBeCloseTo(1_425);
  });

  it('no concession returns full rent', () => {
    expect(calculateEffectiveRent(1_500, 0)).toBe(1_500);
  });

  it('100% concession returns 0', () => {
    expect(calculateEffectiveRent(1_500, 1.0)).toBe(0);
  });
});

// =============================================================================
// Price Per Unit / SF
// =============================================================================

describe('calculatePricePerUnit', () => {
  it('calculates price per unit', () => {
    expect(calculatePricePerUnit(10_000_000, 100)).toBe(100_000);
  });

  it('returns 0 for zero units', () => {
    expect(calculatePricePerUnit(10_000_000, 0)).toBe(0);
  });
});

describe('calculatePricePerSF', () => {
  it('calculates price per square foot', () => {
    expect(calculatePricePerSF(10_000_000, 50_000)).toBe(200);
  });

  it('returns 0 for zero square feet', () => {
    expect(calculatePricePerSF(10_000_000, 0)).toBe(0);
  });
});
