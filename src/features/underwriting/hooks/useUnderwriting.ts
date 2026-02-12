import { useState, useMemo, useCallback } from 'react';
import type { UnderwritingInputs, UnderwritingResults, SensitivityVariable } from '@/types';
import { calculateIRR, calculateEquityMultiple } from '@/lib/calculations/irr';
import { generateCashFlowProjections } from '@/lib/calculations/cashflow';
import { calculateSensitivity } from '@/lib/calculations/sensitivity';
import {
  calculateDebtService,
  calculateDSCR,
  calculateLTV,
  calculateYieldOnCost,
  calculateBreakEvenOccupancy,
  calculatePricePerUnit,
  calculatePricePerSF,
} from '../utils/calculations';

const defaultInputs: UnderwritingInputs = {
  // Property Information
  propertyName: '',
  address: '',
  propertyClass: 'B',
  assetType: 'Garden',
  units: 100,
  averageUnitSize: 850,
  squareFeet: 85000,
  yearBuilt: 2015,
  market: 'Phoenix',
  submarket: '',

  // Acquisition Assumptions
  purchasePrice: 15000000,
  closingCostsPercent: 0.02,
  acquisitionFeePercent: 0.01,
  dueDiligenceCosts: 25000,
  immediateCapEx: 100000,

  // Financing Assumptions
  loanType: 'Agency',
  loanAmount: 11250000,
  ltvPercent: 0.75,
  interestRate: 0.065,
  loanTerm: 10,
  amortizationPeriod: 30,
  interestOnlyPeriod: 2,
  originationFeePercent: 0.01,
  prepaymentPenaltyType: 'Yield Maintenance',

  // Revenue Assumptions
  currentRentPerUnit: 1450,
  marketRentPerUnit: 1550,
  rentGrowthPercent: 0.03,
  otherIncomePerUnit: 50,
  vacancyPercent: 0.05,
  concessionsPercent: 0.02,
  badDebtPercent: 0.01,

  // Operating Expense Assumptions
  propertyTaxPerUnit: 1200,
  insurancePerUnit: 400,
  utilitiesPerUnit: 600,
  managementPercent: 0.04,
  repairsPerUnit: 500,
  payrollPerUnit: 300,
  marketingPerUnit: 100,
  otherExpensesPerUnit: 200,
  turnoverPerUnit: 150, // Make-ready/unit turnover costs
  contractServicesPerUnit: 250, // Contract services (landscaping, pest control, etc.)
  administrativePerUnit: 100, // Admin, legal, security expenses
  expenseGrowthPercent: 0.03,
  capitalReservePerUnit: 300, // Reserves for replacement

  // Exit Assumptions
  holdPeriod: 5,
  exitCapRate: 0.055,
  dispositionFeePercent: 0.02,
  capRateSpread: 0,
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

      // Calculate debt service - account for interest-only period
      // Year 1 is always within IO period if IO period >= 1
      const isYear1InIOPeriod = inputs.interestOnlyPeriod >= 1;
      const monthlyPayment = isYear1InIOPeriod
        ? (loanAmount * inputs.interestRate) / 12 // Interest-only payment
        : calculateDebtService(loanAmount, inputs.interestRate, inputs.amortizationPeriod);
      const annualDebtService = monthlyPayment * 12;

      // Year 1 Revenue
      const grossPotentialRent = inputs.currentRentPerUnit * 12 * inputs.units;
      const otherIncome = inputs.otherIncomePerUnit * 12 * inputs.units;
      const grossIncome = grossPotentialRent + otherIncome;
      
      const vacancy = grossIncome * inputs.vacancyPercent;
      const concessions = grossIncome * inputs.concessionsPercent;
      const badDebt = grossIncome * inputs.badDebtPercent;
      const effectiveGrossIncome = grossIncome - vacancy - concessions - badDebt;

      // Year 1 Expenses
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

      // Year 1 metrics
      const year1Metrics = {
        grossIncome,
        vacancy,
        concessions,
        badDebt,
        effectiveGrossIncome,
        operatingExpenses,
        noi,
        debtService: annualDebtService,
        cashFlow,
        cashOnCashReturn: cashFlow / totalEquityRequired,
        debtServiceCoverageRatio: calculateDSCR(noi, annualDebtService),
        yieldOnCost: calculateYieldOnCost(noi, inputs.purchasePrice + closingCosts + inputs.immediateCapEx),
        cashBreakEvenOccupancy: calculateBreakEvenOccupancy(
          operatingExpenses + capitalReserve,
          annualDebtService,
          grossIncome
        ),
      };

      // Generate 10-year projections
      const projections = generateCashFlowProjections(inputs);

      // Build cash flows for IRR calculation
      const cashFlows: number[] = [-totalEquityRequired];

      for (let i = 0; i < projections.length; i++) {
        const projection = projections[i];
        let yearCashFlow = projection.cashFlow;

        // Add sale proceeds in exit year
        if (projection.year === inputs.holdPeriod) {
          const exitCapRate = inputs.exitCapRate + inputs.capRateSpread;
          const exitValue = projection.noi / exitCapRate;
          const dispositionFee = exitValue * inputs.dispositionFeePercent;
          const saleProceeds = exitValue - dispositionFee - projection.loanBalance;
          yearCashFlow += saleProceeds;
        }

        cashFlows.push(yearCashFlow);
      }

      // Calculate return metrics
      const leveredIRR = calculateIRR(cashFlows);

      // Unlevered cash flows (no debt)
      const unleveredCashFlows: number[] = [-(inputs.purchasePrice + closingCosts + inputs.immediateCapEx)];
      for (let i = 0; i < projections.length; i++) {
        const projection = projections[i];
        let yearCashFlow = projection.noi;

        if (projection.year === inputs.holdPeriod) {
          const exitCapRate = inputs.exitCapRate + inputs.capRateSpread;
          const exitValue = projection.noi / exitCapRate;
          const dispositionFee = exitValue * inputs.dispositionFeePercent;
          yearCashFlow += exitValue - dispositionFee;
        }

        unleveredCashFlows.push(yearCashFlow);
      }
      const unleveredIRR = calculateIRR(unleveredCashFlows);

      // Exit analysis
      const exitYear = projections[projections.length - 1];
      const exitCapRate = inputs.exitCapRate + inputs.capRateSpread;
      const exitValue = exitYear.noi / exitCapRate;
      const loanPaydown = loanAmount - exitYear.loanBalance;
      const dispositionFee = exitValue * inputs.dispositionFeePercent;
      const saleProceeds = exitValue - dispositionFee - exitYear.loanBalance;

      // Total profit and equity multiple
      const totalCashDistributed = projections.reduce((sum, p) => sum + p.cashFlow, 0) + saleProceeds;
      const totalProfit = totalCashDistributed - totalEquityRequired;
      const equityMultiple = calculateEquityMultiple(totalCashDistributed, totalEquityRequired);
      const averageAnnualReturn = totalProfit / inputs.holdPeriod / totalEquityRequired;

      return {
        // Acquisition Metrics
        purchasePrice: inputs.purchasePrice,
        pricePerUnit: calculatePricePerUnit(inputs.purchasePrice, inputs.units),
        pricePerSF: calculatePricePerSF(inputs.purchasePrice, inputs.squareFeet),
        downPayment,
        loanAmount,
        ltv: calculateLTV(loanAmount, inputs.purchasePrice),
        closingCosts,
        acquisitionFee,
        totalEquityRequired,

        // Year 1
        year1: year1Metrics,

        // Projections
        cashFlowProjection: projections,

        // Return Metrics
        leveredIRR,
        unleveredIRR,
        equityMultiple,
        averageAnnualReturn,
        totalProfit,

        // Exit Analysis
        exitValue,
        exitCapRate,
        loanPaydown,
        dispositionFee,
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
