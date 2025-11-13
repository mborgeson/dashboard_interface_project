import type { UnderwritingInputs, SensitivityVariable } from '@/types';
import { calculateIRR } from './irr';
import { generateCashFlowProjections, calculateLoanBalance } from './cashflow';

/**
 * Calculate sensitivity analysis for underwriting inputs
 * Tests impact of changing key variables on IRR
 * @param baseInputs - Base case underwriting inputs
 * @param baseIRR - Base case IRR
 * @returns Array of sensitivity variables sorted by impact
 */
export function calculateSensitivity(
  baseInputs: UnderwritingInputs,
  baseIRR: number
): SensitivityVariable[] {
  const variables: SensitivityVariable[] = [];

  // 1. Exit Cap Rate (±0.5%)
  const exitCapRateVar = analyzeSensitivity(
    baseInputs,
    'exitCapRate',
    'Exit Cap Rate',
    baseInputs.exitCapRate,
    baseInputs.exitCapRate - 0.005,
    baseInputs.exitCapRate + 0.005
  );
  variables.push(exitCapRateVar);

  // 2. Rent Growth % (±1%)
  const rentGrowthVar = analyzeSensitivity(
    baseInputs,
    'rentGrowthPercent',
    'Rent Growth %',
    baseInputs.rentGrowthPercent,
    baseInputs.rentGrowthPercent - 0.01,
    baseInputs.rentGrowthPercent + 0.01
  );
  variables.push(rentGrowthVar);

  // 3. Hold Period (±2 years)
  const holdPeriodVar = analyzeSensitivity(
    baseInputs,
    'holdPeriod',
    'Hold Period',
    baseInputs.holdPeriod,
    Math.max(1, baseInputs.holdPeriod - 2),
    baseInputs.holdPeriod + 2
  );
  variables.push(holdPeriodVar);

  // 4. Rent Per Unit (±10%)
  const rentPerUnitVar = analyzeSensitivity(
    baseInputs,
    'currentRentPerUnit',
    'Rent Per Unit',
    baseInputs.currentRentPerUnit,
    baseInputs.currentRentPerUnit * 0.9,
    baseInputs.currentRentPerUnit * 1.1
  );
  variables.push(rentPerUnitVar);

  // 5. Operating Expenses - represented by property tax (±10%)
  const opExVar = analyzeSensitivity(
    baseInputs,
    'propertyTaxPerUnit',
    'Operating Expenses',
    baseInputs.propertyTaxPerUnit,
    baseInputs.propertyTaxPerUnit * 0.9,
    baseInputs.propertyTaxPerUnit * 1.1
  );
  variables.push(opExVar);

  // 6. Interest Rate (±0.5%)
  const interestRateVar = analyzeSensitivity(
    baseInputs,
    'interestRate',
    'Interest Rate',
    baseInputs.interestRate,
    baseInputs.interestRate - 0.005,
    baseInputs.interestRate + 0.005
  );
  variables.push(interestRateVar);

  // Sort by absolute impact (largest impact first)
  variables.sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));

  return variables;
}

/**
 * Analyze sensitivity for a single variable
 */
function analyzeSensitivity(
  baseInputs: UnderwritingInputs,
  variableName: keyof UnderwritingInputs,
  label: string,
  baseValue: number,
  lowValue: number,
  highValue: number
): SensitivityVariable {
  // Calculate IRR with low value
  const lowInputs = { ...baseInputs, [variableName]: lowValue };
  const lowCashFlows = generateCashFlowsForIRR(lowInputs);
  const lowIRR = calculateIRR(lowCashFlows);

  // Calculate IRR with high value
  const highInputs = { ...baseInputs, [variableName]: highValue };
  const highCashFlows = generateCashFlowsForIRR(highInputs);
  const highIRR = calculateIRR(highCashFlows);

  // Calculate impact (difference between high and low IRR)
  const impact = highIRR - lowIRR;

  return {
    name: variableName as string,
    label,
    baseValue,
    lowValue,
    highValue,
    lowIRR,
    highIRR,
    impact,
  };
}

/**
 * Generate cash flows array for IRR calculation
 * @param inputs - Underwriting inputs
 * @returns Array of cash flows for IRR calculation
 */
function generateCashFlowsForIRR(inputs: UnderwritingInputs): number[] {
  const cashFlows: number[] = [];

  // Year 0: Initial investment (negative)
  const downPayment = inputs.purchasePrice * inputs.downPaymentPercent;
  const closingCosts = inputs.purchasePrice * inputs.closingCostsPercent;
  const totalEquityRequired = downPayment + closingCosts;
  cashFlows.push(-totalEquityRequired);

  // Generate projections for each year
  const projections = generateCashFlowProjections(inputs);

  for (let i = 0; i < projections.length; i++) {
    const projection = projections[i];

    // Add annual cash flow
    let yearCashFlow = projection.cashFlow;

    // If this is the exit year, add sale proceeds
    if (projection.year === inputs.holdPeriod) {
      const exitValue = projection.noi / inputs.exitCapRate;
      const sellingCosts = exitValue * inputs.sellingCostsPercent;
      const saleProceeds = exitValue - sellingCosts - projection.loanBalance;
      yearCashFlow += saleProceeds;
    }

    cashFlows.push(yearCashFlow);
  }

  return cashFlows;
}
