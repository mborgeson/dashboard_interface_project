/**
 * Advanced calculation utilities for underwriting analysis
 */

/**
 * Calculate monthly debt service payment
 */
export function calculateDebtService(
  loanAmount: number,
  interestRate: number,
  amortizationYears: number
): number {
  if (amortizationYears === 0) {
    // Interest-only
    return (loanAmount * interestRate) / 12;
  }

  const monthlyRate = interestRate / 12;
  const numPayments = amortizationYears * 12;

  if (monthlyRate === 0) {
    return loanAmount / numPayments;
  }

  return (
    (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
    (Math.pow(1 + monthlyRate, numPayments) - 1)
  );
}

/**
 * Calculate Debt Service Coverage Ratio
 */
export function calculateDSCR(noi: number, annualDebtService: number): number {
  if (annualDebtService === 0) return 0;
  return noi / annualDebtService;
}

/**
 * Calculate Loan-to-Value ratio
 */
export function calculateLTV(loanAmount: number, propertyValue: number): number {
  if (propertyValue === 0) return 0;
  return loanAmount / propertyValue;
}

/**
 * Calculate Yield on Cost
 */
export function calculateYieldOnCost(noi: number, totalBasis: number): number {
  if (totalBasis === 0) return 0;
  return noi / totalBasis;
}

/**
 * Calculate Internal Rate of Return using Newton-Raphson method
 */
export function calculateIRR(cashFlows: number[]): number {
  if (cashFlows.length < 2) return 0;

  let guess = 0.1;
  const maxIterations = 100;
  const tolerance = 0.0001;

  for (let i = 0; i < maxIterations; i++) {
    let npv = 0;
    let dnpv = 0;

    for (let j = 0; j < cashFlows.length; j++) {
      npv += cashFlows[j] / Math.pow(1 + guess, j);
      if (j > 0) {
        dnpv -= (j * cashFlows[j]) / Math.pow(1 + guess, j + 1);
      }
    }

    const newGuess = guess - npv / dnpv;

    if (Math.abs(newGuess - guess) < tolerance) {
      return newGuess;
    }

    guess = newGuess;
  }

  return guess;
}

/**
 * Calculate Equity Multiple
 */
export function calculateEquityMultiple(totalReturn: number, initialEquity: number): number {
  if (initialEquity === 0) return 0;
  return totalReturn / initialEquity;
}

/**
 * Calculate loan balance at a given point in time
 */
export function calculateLoanBalance(
  loanAmount: number,
  interestRate: number,
  amortizationYears: number,
  monthsElapsed: number,
  interestOnlyPeriod: number = 0
): number {
  if (monthsElapsed === 0) return loanAmount;

  const monthlyRate = interestRate / 12;
  const ioMonths = interestOnlyPeriod * 12;

  // During interest-only period
  if (monthsElapsed <= ioMonths) {
    return loanAmount;
  }

  // After interest-only period
  const amortizingMonths = monthsElapsed - ioMonths;
  const totalAmortMonths = amortizationYears * 12 - ioMonths;

  if (totalAmortMonths <= 0) return loanAmount;

  const monthlyPayment = calculateDebtService(loanAmount, interestRate, totalAmortMonths / 12);

  if (monthlyRate === 0) {
    return loanAmount - (monthlyPayment * amortizingMonths);
  }

  const balance =
    loanAmount * Math.pow(1 + monthlyRate, amortizingMonths) -
    (monthlyPayment * (Math.pow(1 + monthlyRate, amortizingMonths) - 1)) / monthlyRate;

  return Math.max(0, balance);
}

/**
 * Calculate cash break-even occupancy
 */
export function calculateBreakEvenOccupancy(
  operatingExpenses: number,
  debtService: number,
  grossPotentialIncome: number
): number {
  if (grossPotentialIncome === 0) return 0;
  return (operatingExpenses + debtService) / grossPotentialIncome;
}

/**
 * Calculate effective rent after concessions
 */
export function calculateEffectiveRent(
  marketRent: number,
  concessionPercent: number
): number {
  return marketRent * (1 - concessionPercent);
}

/**
 * Calculate Price Per Unit
 */
export function calculatePricePerUnit(purchasePrice: number, units: number): number {
  if (units === 0) return 0;
  return purchasePrice / units;
}

/**
 * Calculate Price Per Square Foot
 */
export function calculatePricePerSF(purchasePrice: number, squareFeet: number): number {
  if (squareFeet === 0) return 0;
  return purchasePrice / squareFeet;
}
