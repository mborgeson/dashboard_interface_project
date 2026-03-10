import { describe, it, expect } from 'vitest';
import { calculateSensitivity } from '../sensitivity';
import type { UnderwritingInputs } from '@/types';

// =============================================================================
// Helper: minimal valid UnderwritingInputs for testing
// =============================================================================

function makeInputs(overrides: Partial<UnderwritingInputs> = {}): UnderwritingInputs {
  return {
    // Property
    propertyName: 'Sensitivity Test Property',
    address: '456 Test Blvd, Phoenix, AZ',
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
// calculateSensitivity
// =============================================================================

describe('calculateSensitivity', () => {
  it('returns 8 sensitivity variables', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    expect(result).toHaveLength(8);
  });

  it('returns all expected variable labels', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const labels = result.map(v => v.label);
    expect(labels).toContain('Exit Cap Rate');
    expect(labels).toContain('Rent Growth %');
    expect(labels).toContain('Hold Period');
    expect(labels).toContain('Current Rent');
    expect(labels).toContain('Vacancy Rate');
    expect(labels).toContain('Interest Rate');
    expect(labels).toContain('Property Tax');
    expect(labels).toContain('Expense Growth');
  });

  it('returns variables sorted by absolute impact (largest first)', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    for (let i = 1; i < result.length; i++) {
      expect(Math.abs(result[i - 1].impact)).toBeGreaterThanOrEqual(
        Math.abs(result[i].impact)
      );
    }
  });

  it('each variable has low and high IRR values', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    for (const v of result) {
      expect(typeof v.lowIRR).toBe('number');
      expect(typeof v.highIRR).toBe('number');
      expect(Number.isFinite(v.lowIRR)).toBe(true);
      expect(Number.isFinite(v.highIRR)).toBe(true);
    }
  });

  it('impact equals highIRR minus lowIRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    for (const v of result) {
      expect(v.impact).toBeCloseTo(v.highIRR - v.lowIRR, 6);
    }
  });

  // --- Exit Cap Rate sensitivity ---

  it('exit cap rate: lower cap = higher property value = higher IRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const exitCapVar = result.find(v => v.label === 'Exit Cap Rate');
    expect(exitCapVar).toBeDefined();
    // Lower exit cap rate means higher exit value, so lowIRR should actually be higher
    // (lowValue = exitCapRate - 0.005, which is a LOWER cap rate = HIGHER value)
    expect(exitCapVar!.lowIRR).toBeGreaterThan(exitCapVar!.highIRR);
  });

  it('exit cap rate varies by +/- 0.5%', () => {
    const inputs = makeInputs({ exitCapRate: 0.055 });
    const result = calculateSensitivity(inputs, 0.15);
    const exitCapVar = result.find(v => v.label === 'Exit Cap Rate');
    expect(exitCapVar!.lowValue).toBeCloseTo(0.05, 3);
    expect(exitCapVar!.highValue).toBeCloseTo(0.06, 3);
  });

  // --- Rent Growth sensitivity ---

  it('higher rent growth increases IRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const rentVar = result.find(v => v.label === 'Rent Growth %');
    expect(rentVar).toBeDefined();
    expect(rentVar!.highIRR).toBeGreaterThan(rentVar!.lowIRR);
  });

  // --- Vacancy Rate sensitivity ---

  it('higher vacancy decreases IRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const vacancyVar = result.find(v => v.label === 'Vacancy Rate');
    expect(vacancyVar).toBeDefined();
    // Higher vacancy = lower IRR
    expect(vacancyVar!.highIRR).toBeLessThan(vacancyVar!.lowIRR);
  });

  it('vacancy low value is floored at 0%', () => {
    const inputs = makeInputs({ vacancyPercent: 0.01 });
    const result = calculateSensitivity(inputs, 0.15);
    const vacancyVar = result.find(v => v.label === 'Vacancy Rate');
    expect(vacancyVar!.lowValue).toBeGreaterThanOrEqual(0);
  });

  // --- Interest Rate sensitivity ---

  it('higher interest rate decreases IRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const interestVar = result.find(v => v.label === 'Interest Rate');
    expect(interestVar).toBeDefined();
    expect(interestVar!.highIRR).toBeLessThan(interestVar!.lowIRR);
  });

  // --- Hold Period sensitivity ---

  it('hold period varies by +/- 2 years', () => {
    const inputs = makeInputs({ holdPeriod: 5 });
    const result = calculateSensitivity(inputs, 0.15);
    const holdVar = result.find(v => v.label === 'Hold Period');
    expect(holdVar!.lowValue).toBe(3);
    expect(holdVar!.highValue).toBe(7);
  });

  it('hold period low value is floored at 3', () => {
    const inputs = makeInputs({ holdPeriod: 3 });
    const result = calculateSensitivity(inputs, 0.15);
    const holdVar = result.find(v => v.label === 'Hold Period');
    expect(holdVar!.lowValue).toBe(3); // max(3, 3-2) = 3
  });

  it('hold period high value is capped at 10', () => {
    const inputs = makeInputs({ holdPeriod: 10 });
    const result = calculateSensitivity(inputs, 0.15);
    const holdVar = result.find(v => v.label === 'Hold Period');
    expect(holdVar!.highValue).toBe(10); // min(10, 10+2) = 10
  });

  // --- Current Rent sensitivity ---

  it('higher current rent increases IRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const rentVar = result.find(v => v.label === 'Current Rent');
    expect(rentVar).toBeDefined();
    expect(rentVar!.highIRR).toBeGreaterThan(rentVar!.lowIRR);
  });

  it('current rent varies by +/- 10%', () => {
    const inputs = makeInputs({ currentRentPerUnit: 1_100 });
    const result = calculateSensitivity(inputs, 0.15);
    const rentVar = result.find(v => v.label === 'Current Rent');
    expect(rentVar!.lowValue).toBeCloseTo(990, 0);
    expect(rentVar!.highValue).toBeCloseTo(1_210, 0);
  });

  // --- Property Tax sensitivity ---

  it('higher property tax decreases IRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const taxVar = result.find(v => v.label === 'Property Tax');
    expect(taxVar).toBeDefined();
    expect(taxVar!.highIRR).toBeLessThan(taxVar!.lowIRR);
  });

  // --- Expense Growth sensitivity ---

  it('higher expense growth decreases IRR', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    const expVar = result.find(v => v.label === 'Expense Growth');
    expect(expVar).toBeDefined();
    expect(expVar!.highIRR).toBeLessThan(expVar!.lowIRR);
  });

  // --- Realistic B&R Capital scenarios ---

  it('exit cap rate is the most impactful variable for typical deal', () => {
    // Exit cap rate typically has the largest impact on IRR for value-add deals
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    // Exit cap rate should be in top 3 most impactful
    const exitCapIdx = result.findIndex(v => v.label === 'Exit Cap Rate');
    expect(exitCapIdx).toBeLessThan(3);
  });

  it('all IRR values are in reasonable range (-50% to 100%)', () => {
    const inputs = makeInputs();
    const result = calculateSensitivity(inputs, 0.15);
    for (const v of result) {
      expect(v.lowIRR).toBeGreaterThan(-0.5);
      expect(v.lowIRR).toBeLessThan(1.0);
      expect(v.highIRR).toBeGreaterThan(-0.5);
      expect(v.highIRR).toBeLessThan(1.0);
    }
  });

  it('works with aggressive value-add assumptions', () => {
    const inputs = makeInputs({
      currentRentPerUnit: 900,
      marketRentPerUnit: 1_300,
      rentGrowthPercent: 0.05,
      immediateCapEx: 1_500_000,
      holdPeriod: 3,
      exitCapRate: 0.05,
    });
    const result = calculateSensitivity(inputs, 0.20);
    expect(result).toHaveLength(8);
    // All should have finite values
    for (const v of result) {
      expect(Number.isFinite(v.impact)).toBe(true);
    }
  });

  it('works with conservative underwriting assumptions', () => {
    const inputs = makeInputs({
      vacancyPercent: 0.10,
      rentGrowthPercent: 0.01,
      expenseGrowthPercent: 0.04,
      exitCapRate: 0.065,
      holdPeriod: 7,
    });
    const result = calculateSensitivity(inputs, 0.08);
    expect(result).toHaveLength(8);
    for (const v of result) {
      expect(Number.isFinite(v.impact)).toBe(true);
    }
  });

  it('handles $50M deal at scale', () => {
    const inputs = makeInputs({
      purchasePrice: 50_000_000,
      units: 400,
      currentRentPerUnit: 1_050,
      marketRentPerUnit: 1_150,
    });
    const result = calculateSensitivity(inputs, 0.15);
    expect(result).toHaveLength(8);
    for (const v of result) {
      expect(Number.isFinite(v.lowIRR)).toBe(true);
      expect(Number.isFinite(v.highIRR)).toBe(true);
    }
  });
});
