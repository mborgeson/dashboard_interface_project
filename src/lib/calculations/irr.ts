/**
 * Calculate Internal Rate of Return (IRR) using Newton-Raphson method
 * @param cashFlows - Array of cash flows where first value is typically negative (investment)
 * @returns The IRR as a decimal (e.g., 0.15 = 15%)
 */
export function calculateIRR(cashFlows: number[]): number {
  let guess = 0.1; // Initial guess of 10%
  const maxIterations = 100;
  const tolerance = 0.0001;

  for (let i = 0; i < maxIterations; i++) {
    let npv = 0;
    let dnpv = 0;

    // Calculate NPV and derivative of NPV at current guess
    for (let t = 0; t < cashFlows.length; t++) {
      npv += cashFlows[t] / Math.pow(1 + guess, t);
      dnpv -= (t * cashFlows[t]) / Math.pow(1 + guess, t + 1);
    }

    // Newton-Raphson formula: x_new = x_old - f(x) / f'(x)
    const newGuess = guess - npv / dnpv;

    // Check for convergence
    if (Math.abs(newGuess - guess) < tolerance) {
      return newGuess;
    }

    guess = newGuess;
  }

  // If we didn't converge, return the last guess
  return guess;
}

/**
 * Calculate Net Present Value (NPV)
 * @param cashFlows - Array of cash flows
 * @param discountRate - The discount rate as a decimal (e.g., 0.1 = 10%)
 * @returns The NPV
 */
export function calculateNPV(cashFlows: number[], discountRate: number): number {
  let npv = 0;
  for (let t = 0; t < cashFlows.length; t++) {
    npv += cashFlows[t] / Math.pow(1 + discountRate, t);
  }
  return npv;
}

/**
 * Calculate equity multiple
 * @param totalCashDistributions - Total cash distributed over investment period
 * @param initialInvestment - Initial equity investment (positive number)
 * @returns The equity multiple
 */
export function calculateEquityMultiple(
  totalCashDistributions: number,
  initialInvestment: number
): number {
  return totalCashDistributions / initialInvestment;
}

/**
 * Calculate cash-on-cash return
 * @param annualCashFlow - Annual cash flow from operations
 * @param initialInvestment - Initial equity investment
 * @returns Cash-on-cash return as a decimal
 */
export function calculateCashOnCash(
  annualCashFlow: number,
  initialInvestment: number
): number {
  return annualCashFlow / initialInvestment;
}
