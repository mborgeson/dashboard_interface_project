import { useState, useMemo, useCallback } from 'react';
import type { UnderwritingInputs, UnderwritingResults, SensitivityVariable } from '@/types';
import { calculateIRR, calculateEquityMultiple, calculateCashOnCash } from '@/lib/calculations/irr';
import { generateCashFlowProjections, calculateMonthlyPayment, calculateDSCR, calculateLoanBalance } from '@/lib/calculations/cashflow';
import { calculateSensitivity } from '@/lib/calculations/sensitivity';

const defaultInputs: UnderwritingInputs = {
  // Property Information
  propertyName: '',
  address: '',
  units: 100,
  squareFeet: 85000,
  yearBuilt: 2015,

  // Financial Assumptions
  purchasePrice: 15000000,
  downPaymentPercent: 0.25,
  interestRate: 0.065,
  loanTerm: 30,
  closingCostsPercent: 0.02,

  // Income Projections
  currentRentPerUnit: 1500,
  rentGrowthPercent: 0.03,
  otherIncomePerUnit: 50,
  otherIncomeGrowthPercent: 0.02,
  vacancyPercent: 0.05,

  // Operating Expenses (per unit per year)
  propertyTaxPerUnit: 1200,
  insurancePerUnit: 400,
  utilitiesPerUnit: 600,
  managementPercent: 0.04,
  repairsPercent: 0.05,
  payrollPerUnit: 300,
  capexReservePercent: 0.03,

  // Exit Assumptions
  holdPeriod: 5,
  exitCapRate: 0.055,
  sellingCostsPercent: 0.02,
};

export function useUnderwriting() {
  const [inputs, setInputs] = useState<UnderwritingInputs>(defaultInputs);

  const updateInput = useCallback(<K extends keyof UnderwritingInputs>(
    key: K,
    value: UnderwritingInputs[K]
  ) => {
    setInputs(prev => ({ ...prev, [key]: value }));
  }, []);

  const resetInputs = useCallback(() => {
    setInputs(defaultInputs);
  }, []);

  const results = useMemo((): UnderwritingResults | null => {
    try {
      // Acquisition Metrics
      const downPayment = inputs.purchasePrice * inputs.downPaymentPercent;
      const loanAmount = inputs.purchasePrice - downPayment;
      const closingCosts = inputs.purchasePrice * inputs.closingCostsPercent;
      const totalEquityRequired = downPayment + closingCosts;

      // Generate projections
      const projections = generateCashFlowProjections(inputs);
      const year1 = projections[0];

      // Calculate monthly payment and annual debt service
      const monthlyPayment = calculateMonthlyPayment(loanAmount, inputs.interestRate, inputs.loanTerm);
      const annualDebtService = monthlyPayment * 12;

      // Year 1 metrics
      const year1Metrics = {
        grossIncome: year1.grossIncome,
        vacancy: year1.vacancy,
        effectiveGrossIncome: year1.effectiveGrossIncome,
        operatingExpenses: year1.operatingExpenses,
        noi: year1.noi,
        debtService: annualDebtService,
        cashFlow: year1.cashFlow,
        cashOnCashReturn: calculateCashOnCash(year1.cashFlow, totalEquityRequired),
        debtServiceCoverageRatio: calculateDSCR(year1.noi, annualDebtService),
      };

      // Build cash flows for IRR calculation
      const cashFlows: number[] = [-totalEquityRequired];

      for (let i = 0; i < projections.length; i++) {
        const projection = projections[i];
        let yearCashFlow = projection.cashFlow;

        // Add sale proceeds in exit year
        if (projection.year === inputs.holdPeriod) {
          const exitValue = projection.noi / inputs.exitCapRate;
          const sellingCosts = exitValue * inputs.sellingCostsPercent;
          const saleProceeds = exitValue - sellingCosts - projection.loanBalance;
          yearCashFlow += saleProceeds;
        }

        cashFlows.push(yearCashFlow);
      }

      // Calculate return metrics
      const leveredIRR = calculateIRR(cashFlows);

      // Unlevered cash flows (no debt)
      const unleveredCashFlows: number[] = [-inputs.purchasePrice - closingCosts];
      for (let i = 0; i < projections.length; i++) {
        const projection = projections[i];
        let yearCashFlow = projection.noi;

        if (projection.year === inputs.holdPeriod) {
          const exitValue = projection.noi / inputs.exitCapRate;
          const sellingCosts = exitValue * inputs.sellingCostsPercent;
          yearCashFlow += exitValue - sellingCosts;
        }

        unleveredCashFlows.push(yearCashFlow);
      }
      const unleveredIRR = calculateIRR(unleveredCashFlows);

      // Exit analysis
      const exitYear = projections[projections.length - 1];
      const exitValue = exitYear.noi / inputs.exitCapRate;
      const loanPaydown = loanAmount - exitYear.loanBalance;
      const sellingCosts = exitValue * inputs.sellingCostsPercent;
      const saleProceeds = exitValue - sellingCosts - exitYear.loanBalance;

      // Total profit and equity multiple
      const totalCashDistributed = projections.reduce((sum, p) => sum + p.cashFlow, 0) + saleProceeds;
      const totalProfit = totalCashDistributed - totalEquityRequired;
      const equityMultiple = calculateEquityMultiple(totalCashDistributed, totalEquityRequired);
      const averageAnnualReturn = totalProfit / inputs.holdPeriod / totalEquityRequired;

      return {
        downPayment,
        loanAmount,
        closingCosts,
        totalEquityRequired,
        year1: year1Metrics,
        cashFlowProjection: projections,
        leveredIRR,
        unleveredIRR,
        equityMultiple,
        averageAnnualReturn,
        totalProfit,
        exitValue,
        loanPaydown,
        saleProceeds,
      };
    } catch (error) {
      console.error('Error calculating underwriting results:', error);
      return null;
    }
  }, [inputs]);

  const sensitivity = useMemo((): SensitivityVariable[] => {
    if (!results) return [];
    return calculateSensitivity(inputs, results.leveredIRR);
  }, [inputs, results]);

  return {
    inputs,
    updateInput,
    resetInputs,
    results,
    sensitivity,
    defaultInputs,
  };
}
