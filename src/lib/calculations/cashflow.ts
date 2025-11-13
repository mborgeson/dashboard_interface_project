import type { UnderwritingInputs, YearlyProjection } from '@/types';

/**
 * Calculate monthly loan payment using amortization formula
 * @param principal - Loan amount
 * @param annualRate - Annual interest rate as decimal (e.g., 0.05 = 5%)
 * @param termYears - Loan term in years
 * @returns Monthly payment amount
 */
export function calculateMonthlyPayment(
  principal: number,
  annualRate: number,
  termYears: number
): number {
  const monthlyRate = annualRate / 12;
  const numPayments = termYears * 12;

  if (monthlyRate === 0) {
    return principal / numPayments;
  }

  return (
    (principal * monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
    (Math.pow(1 + monthlyRate, numPayments) - 1)
  );
}

/**
 * Calculate remaining loan balance after n payments
 * @param principal - Original loan amount
 * @param annualRate - Annual interest rate as decimal
 * @param termYears - Loan term in years
 * @param paymentsMade - Number of payments made
 * @returns Remaining loan balance
 */
export function calculateLoanBalance(
  principal: number,
  annualRate: number,
  termYears: number,
  paymentsMade: number
): number {
  const monthlyRate = annualRate / 12;
  const numPayments = termYears * 12;
  const monthlyPayment = calculateMonthlyPayment(principal, annualRate, termYears);

  if (monthlyRate === 0) {
    return principal - monthlyPayment * paymentsMade;
  }

  const balance =
    principal * Math.pow(1 + monthlyRate, paymentsMade) -
    (monthlyPayment * (Math.pow(1 + monthlyRate, paymentsMade) - 1)) / monthlyRate;

  return Math.max(0, balance);
}

/**
 * Generate 10-year cash flow projections for an investment property
 * @param inputs - Underwriting inputs
 * @returns Array of yearly projections
 */
export function generateCashFlowProjections(
  inputs: UnderwritingInputs
): YearlyProjection[] {
  const projections: YearlyProjection[] = [];

  // Calculate initial metrics
  const loanAmount = inputs.purchasePrice * (1 - inputs.downPaymentPercent);
  const monthlyPayment = calculateMonthlyPayment(
    loanAmount,
    inputs.interestRate,
    inputs.loanTerm
  );
  const annualDebtService = monthlyPayment * 12;

  let cumulativeCashFlow = 0;

  for (let year = 1; year <= inputs.holdPeriod; year++) {
    // Project income growth
    const monthlyRent =
      inputs.currentRentPerUnit * Math.pow(1 + inputs.rentGrowthPercent, year - 1);
    const monthlyOtherIncome =
      inputs.otherIncomePerUnit * Math.pow(1 + inputs.otherIncomeGrowthPercent, year - 1);

    const grossIncome = (monthlyRent + monthlyOtherIncome) * inputs.units * 12;
    const vacancy = grossIncome * inputs.vacancyPercent;
    const effectiveGrossIncome = grossIncome - vacancy;

    // Calculate operating expenses
    const propertyTax = inputs.propertyTaxPerUnit * inputs.units;
    const insurance = inputs.insurancePerUnit * inputs.units;
    const utilities = inputs.utilitiesPerUnit * inputs.units;
    const management = effectiveGrossIncome * inputs.managementPercent;
    const repairs = effectiveGrossIncome * inputs.repairsPercent;
    const payroll = inputs.payrollPerUnit * inputs.units;
    const capex = effectiveGrossIncome * inputs.capexReservePercent;

    const operatingExpenses =
      propertyTax + insurance + utilities + management + repairs + payroll + capex;

    const noi = effectiveGrossIncome - operatingExpenses;
    const cashFlow = noi - annualDebtService;
    cumulativeCashFlow += cashFlow;

    // Calculate property value and loan balance
    const propertyValue = noi / inputs.exitCapRate;
    const loanBalance = calculateLoanBalance(
      loanAmount,
      inputs.interestRate,
      inputs.loanTerm,
      year * 12
    );
    const equity = propertyValue - loanBalance;

    projections.push({
      year,
      grossIncome,
      vacancy,
      effectiveGrossIncome,
      operatingExpenses,
      noi,
      debtService: annualDebtService,
      cashFlow,
      cumulativeCashFlow,
      propertyValue,
      loanBalance,
      equity,
    });
  }

  return projections;
}

/**
 * Calculate Debt Service Coverage Ratio (DSCR)
 * @param noi - Net Operating Income
 * @param debtService - Annual debt service
 * @returns DSCR
 */
export function calculateDSCR(noi: number, debtService: number): number {
  if (debtService === 0) return 0;
  return noi / debtService;
}
