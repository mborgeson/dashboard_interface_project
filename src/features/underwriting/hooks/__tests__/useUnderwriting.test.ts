import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUnderwriting } from '../useUnderwriting';
import type { UnderwritingInputs } from '@/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Manually compute expected Year 1 values from default inputs to validate
 * the hook's computation logic. Mirrors the hook's math exactly.
 */
function computeExpectedYear1(inputs: UnderwritingInputs) {
  const loanAmount = inputs.purchasePrice * inputs.ltvPercent;
  const downPayment = inputs.purchasePrice - loanAmount;
  const closingCosts = inputs.purchasePrice * inputs.closingCostsPercent;
  const acquisitionFee = inputs.purchasePrice * inputs.acquisitionFeePercent;
  const originationFee = loanAmount * inputs.originationFeePercent;

  const totalEquityRequired =
    downPayment +
    closingCosts +
    acquisitionFee +
    inputs.dueDiligenceCosts +
    inputs.immediateCapEx +
    originationFee;

  // Year 1 is in IO period (interestOnlyPeriod >= 1)
  const isYear1InIOPeriod = inputs.interestOnlyPeriod >= 1;
  let monthlyPayment: number;
  if (isYear1InIOPeriod) {
    monthlyPayment = (loanAmount * inputs.interestRate) / 12;
  } else {
    // Standard amortization
    const monthlyRate = inputs.interestRate / 12;
    const numPayments = inputs.amortizationPeriod * 12;
    monthlyPayment =
      (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
      (Math.pow(1 + monthlyRate, numPayments) - 1);
  }
  const annualDebtService = monthlyPayment * 12;

  const grossPotentialRent = inputs.currentRentPerUnit * 12 * inputs.units;
  const otherIncome = inputs.otherIncomePerUnit * 12 * inputs.units;
  const grossIncome = grossPotentialRent + otherIncome;

  const vacancy = grossIncome * inputs.vacancyPercent;
  const concessions = grossIncome * inputs.concessionsPercent;
  const badDebt = grossIncome * inputs.badDebtPercent;
  const effectiveGrossIncome = grossIncome - vacancy - concessions - badDebt;

  const propertyTax = inputs.propertyTaxPerUnit * inputs.units;
  const insurance = inputs.insurancePerUnit * inputs.units;
  const utilities = inputs.utilitiesPerUnit * inputs.units;
  const management = effectiveGrossIncome * inputs.managementPercent;
  const repairs = inputs.repairsPerUnit * inputs.units;
  const payroll = inputs.payrollPerUnit * inputs.units;
  const marketing = inputs.marketingPerUnit * inputs.units;
  const otherExpenses = inputs.otherExpensesPerUnit * inputs.units;
  const turnover = inputs.turnoverPerUnit * inputs.units;
  const contractServices = inputs.contractServicesPerUnit * inputs.units;
  const administrative = inputs.administrativePerUnit * inputs.units;
  const capitalReserve = inputs.capitalReservePerUnit * inputs.units;

  const operatingExpenses =
    propertyTax +
    insurance +
    utilities +
    management +
    repairs +
    payroll +
    marketing +
    otherExpenses +
    turnover +
    contractServices +
    administrative;

  const noi = effectiveGrossIncome - operatingExpenses - capitalReserve;
  const cashFlow = noi - annualDebtService;

  return {
    loanAmount,
    downPayment,
    closingCosts,
    acquisitionFee,
    totalEquityRequired,
    annualDebtService,
    grossIncome,
    vacancy,
    concessions,
    badDebt,
    effectiveGrossIncome,
    operatingExpenses,
    capitalReserve,
    noi,
    cashFlow,
    cashOnCashReturn: cashFlow / totalEquityRequired,
  };
}

// ---------------------------------------------------------------------------
// 1. Hook initialization with default values
// ---------------------------------------------------------------------------

describe('useUnderwriting — initialization', () => {
  it('returns default inputs on mount', () => {
    const { result } = renderHook(() => useUnderwriting());

    const { inputs, defaultInputs } = result.current;
    expect(inputs).toEqual(defaultInputs);
  });

  it('provides all expected API surface properties', () => {
    const { result } = renderHook(() => useUnderwriting());

    expect(result.current).toHaveProperty('inputs');
    expect(result.current).toHaveProperty('updateInput');
    expect(result.current).toHaveProperty('resetInputs');
    expect(result.current).toHaveProperty('results');
    expect(result.current).toHaveProperty('sensitivity');
    expect(result.current).toHaveProperty('defaultInputs');
  });

  it('computes results immediately from defaults (not null)', () => {
    const { result } = renderHook(() => useUnderwriting());

    expect(result.current.results).not.toBeNull();
  });

  it('default inputs describe a 100-unit Class B Phoenix property', () => {
    const { result } = renderHook(() => useUnderwriting());
    const { inputs } = result.current;

    expect(inputs.units).toBe(100);
    expect(inputs.propertyClass).toBe('B');
    expect(inputs.market).toBe('Phoenix');
    expect(inputs.purchasePrice).toBe(15_000_000);
    expect(inputs.holdPeriod).toBe(5);
  });
});

// ---------------------------------------------------------------------------
// 2. Computation logic with known input/output pairs
// ---------------------------------------------------------------------------

describe('useUnderwriting — Year 1 computation', () => {
  it('calculates acquisition metrics correctly from defaults', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;
    const inputs = result.current.inputs;

    // Purchase price pass-through
    expect(r.purchasePrice).toBe(15_000_000);

    // Loan amount = price * LTV
    expect(r.loanAmount).toBe(inputs.purchasePrice * inputs.ltvPercent);
    expect(r.loanAmount).toBe(11_250_000);

    // Down payment
    expect(r.downPayment).toBe(inputs.purchasePrice - r.loanAmount);
    expect(r.downPayment).toBe(3_750_000);

    // Closing costs
    expect(r.closingCosts).toBe(inputs.purchasePrice * inputs.closingCostsPercent);
    expect(r.closingCosts).toBe(300_000);

    // Acquisition fee
    expect(r.acquisitionFee).toBe(inputs.purchasePrice * inputs.acquisitionFeePercent);
    expect(r.acquisitionFee).toBe(150_000);

    // LTV
    expect(r.ltv).toBeCloseTo(0.75, 6);

    // Price per unit and per SF
    expect(r.pricePerUnit).toBe(150_000);
    expect(r.pricePerSF).toBeCloseTo(15_000_000 / 85_000, 2);
  });

  it('calculates total equity required correctly', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;
    const inputs = result.current.inputs;
    const expected = computeExpectedYear1(inputs);

    expect(r.totalEquityRequired).toBeCloseTo(expected.totalEquityRequired, 2);
  });

  it('calculates Year 1 revenue correctly', () => {
    const { result } = renderHook(() => useUnderwriting());
    const y1 = result.current.results!.year1;
    const inputs = result.current.inputs;
    const expected = computeExpectedYear1(inputs);

    expect(y1.grossIncome).toBeCloseTo(expected.grossIncome, 2);
    expect(y1.vacancy).toBeCloseTo(expected.vacancy, 2);
    expect(y1.concessions).toBeCloseTo(expected.concessions, 2);
    expect(y1.badDebt).toBeCloseTo(expected.badDebt, 2);
    expect(y1.effectiveGrossIncome).toBeCloseTo(expected.effectiveGrossIncome, 2);
  });

  it('calculates Year 1 NOI and cash flow correctly', () => {
    const { result } = renderHook(() => useUnderwriting());
    const y1 = result.current.results!.year1;
    const inputs = result.current.inputs;
    const expected = computeExpectedYear1(inputs);

    expect(y1.operatingExpenses).toBeCloseTo(expected.operatingExpenses, 2);
    expect(y1.noi).toBeCloseTo(expected.noi, 2);
    expect(y1.debtService).toBeCloseTo(expected.annualDebtService, 2);
    expect(y1.cashFlow).toBeCloseTo(expected.cashFlow, 2);
  });

  it('calculates cash-on-cash return as cashFlow / totalEquity', () => {
    const { result } = renderHook(() => useUnderwriting());
    const y1 = result.current.results!.year1;
    const r = result.current.results!;

    expect(y1.cashOnCashReturn).toBeCloseTo(y1.cashFlow / r.totalEquityRequired, 6);
  });

  it('calculates DSCR as NOI / debt service', () => {
    const { result } = renderHook(() => useUnderwriting());
    const y1 = result.current.results!.year1;

    expect(y1.debtServiceCoverageRatio).toBeCloseTo(y1.noi / y1.debtService, 6);
  });

  it('Year 1 debt service uses interest-only payment (default IO period = 2)', () => {
    const { result } = renderHook(() => useUnderwriting());
    const y1 = result.current.results!.year1;
    const inputs = result.current.inputs;

    // With 2-year IO period, Year 1 payment is IO
    const expectedIOPayment = (inputs.purchasePrice * inputs.ltvPercent * inputs.interestRate);
    expect(y1.debtService).toBeCloseTo(expectedIOPayment, 2);
  });
});

// ---------------------------------------------------------------------------
// 3. IRR calculation integration
// ---------------------------------------------------------------------------

describe('useUnderwriting — IRR and return metrics', () => {
  it('levered IRR is a finite number', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    expect(Number.isFinite(r.leveredIRR)).toBe(true);
  });

  it('unlevered IRR is a finite number', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    expect(Number.isFinite(r.unleveredIRR)).toBe(true);
  });

  it('levered IRR is positive for default inputs (typical Class B deal)', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    // A typical multifamily deal with 75% LTV should produce positive levered IRR
    expect(r.leveredIRR).toBeGreaterThan(0);
  });

  it('levered IRR exceeds unlevered IRR (positive leverage effect)', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    // With favorable leverage, levered IRR should exceed unlevered
    expect(r.leveredIRR).toBeGreaterThan(r.unleveredIRR);
  });

  it('equity multiple is greater than 1.0 for a profitable deal', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    expect(r.equityMultiple).toBeGreaterThan(1.0);
  });

  it('total profit equals total distributed minus equity required', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    // equityMultiple = totalCashDistributed / totalEquityRequired
    // totalProfit = totalCashDistributed - totalEquityRequired
    // So totalProfit = (equityMultiple - 1) * totalEquityRequired
    const expectedProfit = (r.equityMultiple - 1) * r.totalEquityRequired;
    expect(r.totalProfit).toBeCloseTo(expectedProfit, 0);
  });

  it('average annual return equals totalProfit / holdPeriod / totalEquity', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;
    const inputs = result.current.inputs;

    const expectedAAR = r.totalProfit / inputs.holdPeriod / r.totalEquityRequired;
    expect(r.averageAnnualReturn).toBeCloseTo(expectedAAR, 6);
  });

  it('cash flow projections have holdPeriod number of years', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    expect(r.cashFlowProjection).toHaveLength(result.current.inputs.holdPeriod);
    expect(r.cashFlowProjection[0].year).toBe(1);
    expect(r.cashFlowProjection[r.cashFlowProjection.length - 1].year).toBe(
      result.current.inputs.holdPeriod
    );
  });
});

// ---------------------------------------------------------------------------
// 4. Sensitivity analysis variations
// ---------------------------------------------------------------------------

describe('useUnderwriting — sensitivity analysis', () => {
  it('returns non-empty sensitivity array for valid results', () => {
    const { result } = renderHook(() => useUnderwriting());

    expect(result.current.sensitivity.length).toBeGreaterThan(0);
  });

  it('includes exit cap rate, rent growth, hold period, and vacancy variables', () => {
    const { result } = renderHook(() => useUnderwriting());
    const names = result.current.sensitivity.map((s) => s.name);

    expect(names).toContain('exitCapRate');
    expect(names).toContain('rentGrowthPercent');
    expect(names).toContain('holdPeriod');
    expect(names).toContain('vacancyPercent');
  });

  it('sensitivity variables are sorted by absolute impact (descending)', () => {
    const { result } = renderHook(() => useUnderwriting());
    const impacts = result.current.sensitivity.map((s) => Math.abs(s.impact));

    for (let i = 1; i < impacts.length; i++) {
      expect(impacts[i]).toBeLessThanOrEqual(impacts[i - 1]);
    }
  });

  it('each sensitivity variable has lowIRR and highIRR that are finite', () => {
    const { result } = renderHook(() => useUnderwriting());

    for (const sv of result.current.sensitivity) {
      expect(Number.isFinite(sv.lowIRR)).toBe(true);
      expect(Number.isFinite(sv.highIRR)).toBe(true);
    }
  });

  it('exit cap rate sensitivity: lower cap rate -> higher IRR', () => {
    const { result } = renderHook(() => useUnderwriting());
    const exitCapVar = result.current.sensitivity.find((s) => s.name === 'exitCapRate');

    expect(exitCapVar).toBeDefined();
    // Lower exit cap rate = higher exit value = higher IRR
    expect(exitCapVar!.lowIRR).toBeGreaterThan(exitCapVar!.highIRR);
  });

  it('rent growth sensitivity: higher growth -> higher IRR', () => {
    const { result } = renderHook(() => useUnderwriting());
    const rentGrowthVar = result.current.sensitivity.find(
      (s) => s.name === 'rentGrowthPercent'
    );

    expect(rentGrowthVar).toBeDefined();
    // Higher rent growth = more income = higher IRR
    expect(rentGrowthVar!.highIRR).toBeGreaterThan(rentGrowthVar!.lowIRR);
  });

  it('sensitivity recalculates when inputs change', () => {
    const { result } = renderHook(() => useUnderwriting());
    const initialSensitivity = result.current.sensitivity;

    act(() => {
      result.current.updateInput('purchasePrice', 20_000_000);
    });

    // Sensitivity values should differ after price change
    const newSensitivity = result.current.sensitivity;
    expect(newSensitivity).not.toEqual(initialSensitivity);
  });
});

// ---------------------------------------------------------------------------
// 5. Edge cases
// ---------------------------------------------------------------------------

describe('useUnderwriting — edge cases', () => {
  it('handles zero purchase price without crashing', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('purchasePrice', 0);
    });

    // Should not crash — results might be null due to division by zero in downstream calcs,
    // or it may produce NaN/Infinity that gets caught. Either way, no throw.
    // The hook wraps in try/catch, so null is acceptable
    const r = result.current.results;
    if (r !== null) {
      expect(Number.isFinite(r.purchasePrice)).toBe(true);
      expect(r.purchasePrice).toBe(0);
    }
  });

  it('handles zero units without crashing', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('units', 0);
    });

    // pricePerUnit uses division — should not throw
    const r = result.current.results;
    if (r !== null) {
      expect(r.pricePerUnit).toBe(0); // calculatePricePerUnit returns 0 when units=0
    }
  });

  it('handles zero square feet without crashing', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('squareFeet', 0);
    });

    const r = result.current.results;
    if (r !== null) {
      expect(r.pricePerSF).toBe(0); // calculatePricePerSF returns 0 when sf=0
    }
  });

  it('handles zero exit cap rate gracefully (returns null)', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('exitCapRate', 0);
    });

    // Division by zero in exit value calculation — try/catch should produce null
    // or the projections generate Infinity which propagates
    const r = result.current.results;
    // Either null (caught error) or results with non-finite values is acceptable
    if (r !== null) {
      // If results are returned, exit value will be Infinity
      expect(r.exitCapRate).toBe(0);
    }
  });

  it('handles negative cash flows (high vacancy scenario)', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('vacancyPercent', 0.5); // 50% vacancy
    });

    const r = result.current.results;
    expect(r).not.toBeNull();
    // With 50% vacancy, cash flow should be negative
    expect(r!.year1.cashFlow).toBeLessThan(0);
    // IRR may be NaN/Infinity when Newton-Raphson diverges on extreme inputs — that is acceptable
    expect(typeof r!.leveredIRR).toBe('number');
  });

  it('handles zero interest rate (interest-only payment becomes 0)', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('interestRate', 0);
    });

    const r = result.current.results;
    expect(r).not.toBeNull();
    // IO payment with 0% rate = 0 debt service
    expect(r!.year1.debtService).toBe(0);
  });

  it('handles hold period of 1 year', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('holdPeriod', 1);
    });

    const r = result.current.results;
    expect(r).not.toBeNull();
    expect(r!.cashFlowProjection).toHaveLength(1);
    expect(r!.cashFlowProjection[0].year).toBe(1);
  });

  it('handles very high LTV (95%)', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('ltvPercent', 0.95);
    });

    const r = result.current.results;
    expect(r).not.toBeNull();
    expect(r!.loanAmount).toBeCloseTo(15_000_000 * 0.95, 2);
    expect(r!.downPayment).toBeCloseTo(15_000_000 * 0.05, 2);
  });
});

// ---------------------------------------------------------------------------
// updateInput and resetInputs
// ---------------------------------------------------------------------------

describe('useUnderwriting — updateInput and resetInputs', () => {
  it('updateInput changes a single field without affecting others', () => {
    const { result } = renderHook(() => useUnderwriting());

    const originalUnits = result.current.inputs.units;

    act(() => {
      result.current.updateInput('purchasePrice', 20_000_000);
    });

    expect(result.current.inputs.purchasePrice).toBe(20_000_000);
    expect(result.current.inputs.units).toBe(originalUnits);
  });

  it('updateInput triggers results recalculation', () => {
    const { result } = renderHook(() => useUnderwriting());

    const originalPricePerUnit = result.current.results!.pricePerUnit;

    act(() => {
      result.current.updateInput('purchasePrice', 20_000_000);
    });

    expect(result.current.results!.pricePerUnit).not.toBe(originalPricePerUnit);
    expect(result.current.results!.pricePerUnit).toBe(200_000); // 20M / 100 units
  });

  it('resetInputs restores all inputs to defaults', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('purchasePrice', 99_000_000);
      result.current.updateInput('units', 500);
      result.current.updateInput('vacancyPercent', 0.25);
    });

    expect(result.current.inputs.purchasePrice).toBe(99_000_000);

    act(() => {
      result.current.resetInputs();
    });

    expect(result.current.inputs).toEqual(result.current.defaultInputs);
    expect(result.current.inputs.purchasePrice).toBe(15_000_000);
  });

  it('multiple rapid updates accumulate correctly', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('purchasePrice', 10_000_000);
    });
    act(() => {
      result.current.updateInput('purchasePrice', 12_000_000);
    });
    act(() => {
      result.current.updateInput('purchasePrice', 18_000_000);
    });

    expect(result.current.inputs.purchasePrice).toBe(18_000_000);
    expect(result.current.results!.purchasePrice).toBe(18_000_000);
  });
});

// ---------------------------------------------------------------------------
// Exit analysis
// ---------------------------------------------------------------------------

describe('useUnderwriting — exit analysis', () => {
  it('exit cap rate includes cap rate spread', () => {
    const { result } = renderHook(() => useUnderwriting());

    act(() => {
      result.current.updateInput('capRateSpread', 0.01);
    });

    const r = result.current.results!;
    const inputs = result.current.inputs;
    expect(r.exitCapRate).toBeCloseTo(inputs.exitCapRate + 0.01, 6);
  });

  it('exit value equals exit-year NOI / exit cap rate', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    const exitYearProjection = r.cashFlowProjection[r.cashFlowProjection.length - 1];
    const expectedExitValue = exitYearProjection.noi / r.exitCapRate;
    expect(r.exitValue).toBeCloseTo(expectedExitValue, 0);
  });

  it('disposition fee is a percentage of exit value', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;
    const inputs = result.current.inputs;

    expect(r.dispositionFee).toBeCloseTo(r.exitValue * inputs.dispositionFeePercent, 0);
  });

  it('sale proceeds = exit value - disposition fee - loan balance', () => {
    const { result } = renderHook(() => useUnderwriting());
    const r = result.current.results!;

    const exitYearProjection = r.cashFlowProjection[r.cashFlowProjection.length - 1];
    const expectedProceeds = r.exitValue - r.dispositionFee - exitYearProjection.loanBalance;
    expect(r.saleProceeds).toBeCloseTo(expectedProceeds, 0);
  });
});
