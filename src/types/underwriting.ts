export interface UnderwritingInputs {
  // Property Information
  propertyName: string;
  address: string;
  units: number;
  squareFeet: number;
  yearBuilt: number;

  // Financial Assumptions
  purchasePrice: number;
  downPaymentPercent: number;
  interestRate: number;
  loanTerm: number;
  closingCostsPercent: number;

  // Income Projections
  currentRentPerUnit: number;
  rentGrowthPercent: number;
  otherIncomePerUnit: number;
  otherIncomeGrowthPercent: number;
  vacancyPercent: number;

  // Operating Expenses (per unit per year)
  propertyTaxPerUnit: number;
  insurancePerUnit: number;
  utilitiesPerUnit: number;
  managementPercent: number;
  repairsPercent: number;
  payrollPerUnit: number;
  capexReservePercent: number;

  // Exit Assumptions
  holdPeriod: number;
  exitCapRate: number;
  sellingCostsPercent: number;
}

export interface UnderwritingResults {
  // Acquisition Metrics
  downPayment: number;
  loanAmount: number;
  closingCosts: number;
  totalEquityRequired: number;

  // Year 1 Metrics
  year1: {
    grossIncome: number;
    vacancy: number;
    effectiveGrossIncome: number;
    operatingExpenses: number;
    noi: number;
    debtService: number;
    cashFlow: number;
    cashOnCashReturn: number;
    debtServiceCoverageRatio: number;
  };

  // 10-Year Projections
  cashFlowProjection: YearlyProjection[];

  // Return Metrics
  leveredIRR: number;
  unleveredIRR: number;
  equityMultiple: number;
  averageAnnualReturn: number;
  totalProfit: number;

  // Exit Analysis
  exitValue: number;
  loanPaydown: number;
  saleProceeds: number;
}

export interface YearlyProjection {
  year: number;
  grossIncome: number;
  vacancy: number;
  effectiveGrossIncome: number;
  operatingExpenses: number;
  noi: number;
  debtService: number;
  cashFlow: number;
  cumulativeCashFlow: number;
  propertyValue: number;
  loanBalance: number;
  equity: number;
}

export interface SensitivityVariable {
  name: string;
  label: string;
  baseValue: number;
  lowValue: number;
  highValue: number;
  lowIRR: number;
  highIRR: number;
  impact: number;
}
