import type { UnderwritingInputs, YearlyProjection } from '@/types';
import { calculateLoanBalance } from '@/features/underwriting/utils/calculations';

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
 * Generate 10-year cash flow projections for an investment property
 * @param inputs - Underwriting inputs
 * @returns Array of yearly projections
 */
export function generateCashFlowProjections(
  inputs: UnderwritingInputs
): YearlyProjection[] {
  const projections: YearlyProjection[] = [];

  // Calculate loan metrics
  const loanAmount = inputs.purchasePrice * inputs.ltvPercent;

  // Calculate both IO and amortizing payments
  const ioMonthlyPayment = (loanAmount * inputs.interestRate) / 12;
  const amortizingMonthlyPayment = calculateMonthlyPayment(
    loanAmount,
    inputs.interestRate,
    inputs.amortizationPeriod
  );

  let cumulativeCashFlow = 0;

  for (let year = 1; year <= inputs.holdPeriod; year++) {
    // Determine debt service based on interest-only period
    // Year is in IO period if year <= IO period (e.g., Year 1 and 2 for 2-year IO)
    const isInIOPeriod = year <= inputs.interestOnlyPeriod;
    const monthlyPayment = isInIOPeriod ? ioMonthlyPayment : amortizingMonthlyPayment;
    const annualDebtService = monthlyPayment * 12;

    // Project rent growth - in-place rent grows toward market rent
    const inPlaceRentGrown =
      inputs.currentRentPerUnit * Math.pow(1 + inputs.rentGrowthPercent, year - 1);
    const marketRentGrown =
      inputs.marketRentPerUnit * Math.pow(1 + inputs.rentGrowthPercent, year - 1);

    // Use the lesser of grown in-place rent or market rent (rent converges to market)
    const effectiveMonthlyRent = Math.min(inPlaceRentGrown, marketRentGrown);
    const monthlyOtherIncome = inputs.otherIncomePerUnit;

    // Gross Potential Rent at market rate
    const grossPotentialRent = marketRentGrown * inputs.units * 12;

    // Loss to Lease = (Market Rent - Effective Rent) * Units * 12
    const lossToLease = Math.max(0, (marketRentGrown - effectiveMonthlyRent) * inputs.units * 12);

    const otherIncome = monthlyOtherIncome * inputs.units * 12;

    // Gross income after loss-to-lease
    const grossIncome = grossPotentialRent - lossToLease + otherIncome;

    // Apply vacancy, concessions, bad debt
    const vacancy = grossIncome * inputs.vacancyPercent;
    const concessions = grossIncome * inputs.concessionsPercent;
    const badDebt = grossIncome * inputs.badDebtPercent;
    const effectiveGrossIncome = grossIncome - vacancy - concessions - badDebt;

    // Calculate operating expenses (grown by expense growth rate)
    const expenseGrowth = Math.pow(1 + inputs.expenseGrowthPercent, year - 1);

    const propertyTax = inputs.propertyTaxPerUnit * inputs.units * expenseGrowth;
    const insurance = inputs.insurancePerUnit * inputs.units * expenseGrowth;
    const utilities = inputs.utilitiesPerUnit * inputs.units * expenseGrowth;
    const management = effectiveGrossIncome * inputs.managementPercent;
    const repairs = inputs.repairsPerUnit * inputs.units * expenseGrowth;
    const payroll = inputs.payrollPerUnit * inputs.units * expenseGrowth;
    const marketing = inputs.marketingPerUnit * inputs.units * expenseGrowth;
    const otherExpenses = inputs.otherExpensesPerUnit * inputs.units * expenseGrowth;
    const turnover = inputs.turnoverPerUnit * inputs.units * expenseGrowth;
    const contractServices = inputs.contractServicesPerUnit * inputs.units * expenseGrowth;
    const administrative = inputs.administrativePerUnit * inputs.units * expenseGrowth;
    const capitalReserve = inputs.capitalReservePerUnit * inputs.units * expenseGrowth;

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
    cumulativeCashFlow += cashFlow;

    // Calculate property value using exit cap rate as a proxy for current value
    const propertyValue = noi / inputs.exitCapRate;

    // Calculate loan balance considering interest-only period
    const monthsElapsed = year * 12;
    const loanBalance = calculateLoanBalance(
      loanAmount,
      inputs.interestRate,
      inputs.amortizationPeriod,
      monthsElapsed,
      inputs.interestOnlyPeriod
    );

    const equity = propertyValue - loanBalance;

    projections.push({
      year,
      grossPotentialRent,
      lossToLease,
      grossIncome,
      vacancy,
      concessions,
      badDebt,
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
