import { describe, it, expect } from 'vitest';
import { calculateMonthlyPayment, generateCashFlowProjections, calculateDSCR } from '../cashflow';
import type { UnderwritingInputs } from '@/types';

// =============================================================================
// Helper: minimal valid UnderwritingInputs for testing
// =============================================================================

function makeInputs(overrides: Partial<UnderwritingInputs> = {}): UnderwritingInputs {
  return {
    // Property
    propertyName: 'Test Property',
    address: '123 Test St, Phoenix, AZ',
    propertyClass: 'B',
    assetType: 'Garden',
    units: 120,
    averageUnitSize: 850,
    squareFeet: 102_000,
    yearBuilt: 1985,
    market: 'Phoenix',
    submarket: 'Tempe',

    // Acquisition
    purchasePrice: 15_000_000,
    closingCostsPercent: 0.02,
    acquisitionFeePercent: 0.01,
    dueDiligenceCosts: 50_000,
    immediateCapEx: 500_000,

    // Financing
    loanType: 'Agency',
    loanAmount: 11_250_000,
    ltvPercent: 0.75,
    interestRate: 0.055,
    loanTerm: 10,
    amortizationPeriod: 30,
    interestOnlyPeriod: 2,
    originationFeePercent: 0.01,
    prepaymentPenaltyType: 'Yield Maintenance',

    // Revenue
    currentRentPerUnit: 1_100,
    marketRentPerUnit: 1_200,
    rentGrowthPercent: 0.03,
    otherIncomePerUnit: 75,
    vacancyPercent: 0.07,
    concessionsPercent: 0.01,
    badDebtPercent: 0.005,

    // OpEx (per unit per year)
    propertyTaxPerUnit: 800,
    insurancePerUnit: 350,
    utilitiesPerUnit: 600,
    managementPercent: 0.04,
    repairsPerUnit: 400,
    payrollPerUnit: 500,
    marketingPerUnit: 100,
    otherExpensesPerUnit: 150,
    turnoverPerUnit: 200,
    contractServicesPerUnit: 150,
    administrativePerUnit: 100,
    expenseGrowthPercent: 0.025,
    capitalReservePerUnit: 250,

    // Exit
    holdPeriod: 5,
    exitCapRate: 0.055,
    dispositionFeePercent: 0.02,
    capRateSpread: 0.005,

    ...overrides,
  };
}

// =============================================================================
// calculateMonthlyPayment
// =============================================================================

describe('calculateMonthlyPayment', () => {
  it('calculates standard 30-year amortizing payment', () => {
    // $11.25M loan at 5.5%, 30-year amort
    const payment = calculateMonthlyPayment(11_250_000, 0.055, 30);
    // Expected ~$63,900/month
    expect(payment).toBeGreaterThan(60_000);
    expect(payment).toBeLessThan(70_000);
  });

  it('calculates 25-year amortizing payment (higher than 30-year)', () => {
    const payment25 = calculateMonthlyPayment(10_000_000, 0.05, 25);
    const payment30 = calculateMonthlyPayment(10_000_000, 0.05, 30);
    expect(payment25).toBeGreaterThan(payment30);
  });

  it('handles zero interest rate (principal only)', () => {
    const payment = calculateMonthlyPayment(1_200_000, 0, 30);
    expect(payment).toBeCloseTo(1_200_000 / 360, 2);
  });

  it('returns 0 for zero principal', () => {
    const payment = calculateMonthlyPayment(0, 0.05, 30);
    expect(payment).toBe(0);
  });

  it('calculates correctly for typical bridge loan (3-year term, 7%)', () => {
    const payment = calculateMonthlyPayment(8_000_000, 0.07, 3);
    // Short amortization = much higher payment
    expect(payment).toBeGreaterThan(200_000);
  });

  it('payment increases with higher interest rate', () => {
    const low = calculateMonthlyPayment(10_000_000, 0.04, 30);
    const high = calculateMonthlyPayment(10_000_000, 0.07, 30);
    expect(high).toBeGreaterThan(low);
  });

  it('payment increases with shorter amortization', () => {
    const long = calculateMonthlyPayment(10_000_000, 0.05, 30);
    const short = calculateMonthlyPayment(10_000_000, 0.05, 15);
    expect(short).toBeGreaterThan(long);
  });
});

// =============================================================================
// calculateDSCR
// =============================================================================

describe('calculateDSCR', () => {
  it('calculates healthy DSCR (1.25x lender minimum)', () => {
    expect(calculateDSCR(750_000, 600_000)).toBeCloseTo(1.25);
  });

  it('calculates DSCR at agency threshold (1.20x)', () => {
    expect(calculateDSCR(600_000, 500_000)).toBeCloseTo(1.20);
  });

  it('calculates DSCR below 1.0x (negative leverage)', () => {
    expect(calculateDSCR(400_000, 500_000)).toBeCloseTo(0.80);
  });

  it('returns 0 when debt service is 0 (all-cash deal)', () => {
    expect(calculateDSCR(500_000, 0)).toBe(0);
  });

  it('handles negative NOI', () => {
    const dscr = calculateDSCR(-100_000, 500_000);
    expect(dscr).toBeCloseTo(-0.20);
  });

  it('handles zero NOI', () => {
    expect(calculateDSCR(0, 500_000)).toBe(0);
  });

  it('calculates high DSCR for well-performing deal', () => {
    // Strong NOI relative to debt
    expect(calculateDSCR(1_200_000, 600_000)).toBeCloseTo(2.0);
  });
});

// =============================================================================
// generateCashFlowProjections
// =============================================================================

describe('generateCashFlowProjections', () => {
  it('returns correct number of years', () => {
    const inputs = makeInputs({ holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    expect(projections).toHaveLength(5);
  });

  it('returns 10 years for 10-year hold', () => {
    const inputs = makeInputs({ holdPeriod: 10 });
    const projections = generateCashFlowProjections(inputs);
    expect(projections).toHaveLength(10);
  });

  it('years are numbered sequentially starting at 1', () => {
    const inputs = makeInputs({ holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    expect(projections.map(p => p.year)).toEqual([1, 2, 3, 4, 5]);
  });

  // --- Revenue projections ---

  it('gross potential rent grows each year', () => {
    const inputs = makeInputs({ holdPeriod: 5, rentGrowthPercent: 0.03 });
    const projections = generateCashFlowProjections(inputs);
    for (let i = 1; i < projections.length; i++) {
      expect(projections[i].grossPotentialRent).toBeGreaterThan(
        projections[i - 1].grossPotentialRent
      );
    }
  });

  it('loss to lease is non-negative', () => {
    const inputs = makeInputs();
    const projections = generateCashFlowProjections(inputs);
    for (const p of projections) {
      expect(p.lossToLease).toBeGreaterThanOrEqual(0);
    }
  });

  it('effective gross income is less than gross income (due to vacancy/concessions/bad debt)', () => {
    const inputs = makeInputs({ vacancyPercent: 0.07, concessionsPercent: 0.01 });
    const projections = generateCashFlowProjections(inputs);
    for (const p of projections) {
      expect(p.effectiveGrossIncome).toBeLessThan(p.grossIncome);
    }
  });

  it('vacancy is calculated as percentage of gross income', () => {
    const inputs = makeInputs({ vacancyPercent: 0.10 });
    const projections = generateCashFlowProjections(inputs);
    const p = projections[0];
    expect(p.vacancy).toBeCloseTo(p.grossIncome * 0.10, 0);
  });

  // --- NOI and expenses ---

  it('NOI is positive for reasonable inputs', () => {
    const inputs = makeInputs();
    const projections = generateCashFlowProjections(inputs);
    for (const p of projections) {
      expect(p.noi).toBeGreaterThan(0);
    }
  });

  it('operating expenses grow with expense growth rate', () => {
    const inputs = makeInputs({ holdPeriod: 5, expenseGrowthPercent: 0.03 });
    const projections = generateCashFlowProjections(inputs);
    // Expenses should increase year-over-year (excluding management which is % of EGI)
    // Check total OpEx trend
    for (let i = 1; i < projections.length; i++) {
      expect(projections[i].operatingExpenses).toBeGreaterThan(
        projections[i - 1].operatingExpenses * 0.99 // allow small variance from management %
      );
    }
  });

  it('NOI equals EGI minus OpEx minus capital reserves', () => {
    const inputs = makeInputs();
    const projections = generateCashFlowProjections(inputs);
    const p = projections[0];
    // NOI = EGI - OpEx - capital reserves
    // Capital reserve is separate from operatingExpenses in this calc
    // noi = effectiveGrossIncome - operatingExpenses - capitalReserve
    const expectedCapitalReserve = inputs.capitalReservePerUnit * inputs.units;
    expect(p.noi).toBeCloseTo(p.effectiveGrossIncome - p.operatingExpenses - expectedCapitalReserve, 0);
  });

  // --- Debt service and interest-only period ---

  it('debt service is lower during IO period', () => {
    const inputs = makeInputs({ interestOnlyPeriod: 2, holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    // Year 1-2 should have IO payment, Year 3+ amortizing
    expect(projections[0].debtService).toBeLessThan(projections[2].debtService);
    expect(projections[1].debtService).toBeLessThan(projections[2].debtService);
  });

  it('debt service is constant within IO period', () => {
    const inputs = makeInputs({ interestOnlyPeriod: 3, holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    expect(projections[0].debtService).toBeCloseTo(projections[1].debtService, 2);
    expect(projections[1].debtService).toBeCloseTo(projections[2].debtService, 2);
  });

  it('debt service is constant in amortizing period', () => {
    const inputs = makeInputs({ interestOnlyPeriod: 0, holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    // All years should have same debt service
    for (let i = 1; i < projections.length; i++) {
      expect(projections[i].debtService).toBeCloseTo(projections[0].debtService, 2);
    }
  });

  it('zero IO period means full amortization from year 1', () => {
    const inputs = makeInputs({ interestOnlyPeriod: 0, holdPeriod: 3 });
    const projections = generateCashFlowProjections(inputs);
    const ioPayment = (inputs.purchasePrice * inputs.ltvPercent * inputs.interestRate);
    // Amortizing payment should be higher than IO payment
    expect(projections[0].debtService).toBeGreaterThan(ioPayment);
  });

  // --- Cash flow ---

  it('cash flow equals NOI minus debt service', () => {
    const inputs = makeInputs();
    const projections = generateCashFlowProjections(inputs);
    for (const p of projections) {
      expect(p.cashFlow).toBeCloseTo(p.noi - p.debtService, 0);
    }
  });

  it('cumulative cash flow accumulates correctly', () => {
    const inputs = makeInputs({ holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    let cumulative = 0;
    for (const p of projections) {
      cumulative += p.cashFlow;
      expect(p.cumulativeCashFlow).toBeCloseTo(cumulative, 0);
    }
  });

  // --- Property value and equity ---

  it('property value is NOI divided by exit cap rate', () => {
    const inputs = makeInputs({ exitCapRate: 0.055 });
    const projections = generateCashFlowProjections(inputs);
    for (const p of projections) {
      expect(p.propertyValue).toBeCloseTo(p.noi / 0.055, 0);
    }
  });

  it('equity equals property value minus loan balance', () => {
    const inputs = makeInputs();
    const projections = generateCashFlowProjections(inputs);
    for (const p of projections) {
      expect(p.equity).toBeCloseTo(p.propertyValue - p.loanBalance, 0);
    }
  });

  it('loan balance stays flat during IO period', () => {
    const inputs = makeInputs({ interestOnlyPeriod: 2, holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    const loanAmount = inputs.purchasePrice * inputs.ltvPercent;
    // During IO years (1 & 2), balance should be full loan amount
    expect(projections[0].loanBalance).toBeCloseTo(loanAmount, 0);
    expect(projections[1].loanBalance).toBeCloseTo(loanAmount, 0);
  });

  it('loan balance decreases after IO period', () => {
    const inputs = makeInputs({ interestOnlyPeriod: 1, holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    // Year 2 onward should show declining balance
    expect(projections[2].loanBalance).toBeLessThan(projections[1].loanBalance);
    expect(projections[3].loanBalance).toBeLessThan(projections[2].loanBalance);
  });

  // --- Edge cases ---

  it('handles 1-year hold period', () => {
    const inputs = makeInputs({ holdPeriod: 1 });
    const projections = generateCashFlowProjections(inputs);
    expect(projections).toHaveLength(1);
    expect(projections[0].year).toBe(1);
    expect(projections[0].noi).toBeGreaterThan(0);
  });

  it('handles zero vacancy', () => {
    const inputs = makeInputs({ vacancyPercent: 0, concessionsPercent: 0, badDebtPercent: 0 });
    const projections = generateCashFlowProjections(inputs);
    const p = projections[0];
    expect(p.vacancy).toBe(0);
    expect(p.concessions).toBe(0);
    expect(p.badDebt).toBe(0);
    expect(p.effectiveGrossIncome).toBe(p.grossIncome);
  });

  it('handles zero rent growth', () => {
    const inputs = makeInputs({ rentGrowthPercent: 0, holdPeriod: 5 });
    const projections = generateCashFlowProjections(inputs);
    // GPR should be constant (market rent * units * 12 each year)
    const year1GPR = projections[0].grossPotentialRent;
    for (const p of projections) {
      expect(p.grossPotentialRent).toBeCloseTo(year1GPR, 0);
    }
  });

  it('handles in-place rent equal to market rent (no loss to lease)', () => {
    const inputs = makeInputs({
      currentRentPerUnit: 1_200,
      marketRentPerUnit: 1_200,
    });
    const projections = generateCashFlowProjections(inputs);
    expect(projections[0].lossToLease).toBe(0);
  });

  it('handles in-place rent above market rent', () => {
    // In-place rent exceeds market — should use market rent (no negative loss-to-lease)
    const inputs = makeInputs({
      currentRentPerUnit: 1_500,
      marketRentPerUnit: 1_200,
    });
    const projections = generateCashFlowProjections(inputs);
    // effectiveMonthlyRent = min(inPlaceGrown, marketGrown) = market
    // So lossToLease = max(0, market - market) = 0
    expect(projections[0].lossToLease).toBe(0);
  });

  // --- Realistic B&R Capital scenario ---

  it('produces realistic numbers for 120-unit Class B Phoenix deal', () => {
    const inputs = makeInputs();
    const projections = generateCashFlowProjections(inputs);
    const year1 = projections[0];

    // Year 1 GPR should be ~$1,728,000 (1200 * 120 * 12)
    expect(year1.grossPotentialRent).toBeCloseTo(1_200 * 120 * 12, -2);

    // Year 1 NOI should be in reasonable range for Class B ($4K-$8K per unit)
    const noiPerUnit = year1.noi / 120;
    expect(noiPerUnit).toBeGreaterThan(2_000);
    expect(noiPerUnit).toBeLessThan(10_000);

    // Debt service should be positive
    expect(year1.debtService).toBeGreaterThan(0);

    // Cash flow should be positive for a well-underwritten deal
    expect(year1.cashFlow).toBeGreaterThan(0);

    // Property value should be in reasonable range
    expect(year1.propertyValue).toBeGreaterThan(10_000_000);
    expect(year1.propertyValue).toBeLessThan(30_000_000);
  });
});
