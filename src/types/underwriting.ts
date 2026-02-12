export type PropertyClass = 'A' | 'B' | 'C';
export type AssetType = 'Garden' | 'Mid-Rise' | 'High-Rise';
export type LoanType = 'Agency' | 'CMBS' | 'Bridge' | 'Bank';
export type PrepaymentPenaltyType = 'Yield Maintenance' | 'Defeasance' | 'Step-Down' | 'None';

export interface UnderwritingInputs {
  // Property Information
  propertyName: string;
  address: string;
  propertyClass: PropertyClass;
  assetType: AssetType;
  units: number;
  averageUnitSize: number;
  squareFeet: number;
  yearBuilt: number;
  market: string;
  submarket: string;

  // Acquisition Assumptions
  purchasePrice: number;
  closingCostsPercent: number;
  acquisitionFeePercent: number;
  dueDiligenceCosts: number;
  immediateCapEx: number;

  // Financing Assumptions
  loanType: LoanType;
  loanAmount: number;
  ltvPercent: number; // Loan-to-Value
  interestRate: number;
  loanTerm: number;
  amortizationPeriod: number;
  interestOnlyPeriod: number;
  originationFeePercent: number;
  prepaymentPenaltyType: PrepaymentPenaltyType;

  // Revenue Assumptions
  currentRentPerUnit: number;
  marketRentPerUnit: number;
  rentGrowthPercent: number;
  otherIncomePerUnit: number;
  vacancyPercent: number;
  concessionsPercent: number;
  badDebtPercent: number;

  // Operating Expense Assumptions (per unit per year)
  propertyTaxPerUnit: number;
  insurancePerUnit: number;
  utilitiesPerUnit: number;
  managementPercent: number;
  repairsPerUnit: number;
  payrollPerUnit: number;
  marketingPerUnit: number;
  otherExpensesPerUnit: number;
  turnoverPerUnit: number; // Make-ready/unit turnover costs
  contractServicesPerUnit: number; // Contract services (landscaping, pest control, etc.)
  administrativePerUnit: number; // Admin, legal, security expenses
  expenseGrowthPercent: number;
  capitalReservePerUnit: number; // Reserves for replacement

  // Exit Assumptions
  holdPeriod: number;
  exitCapRate: number;
  dispositionFeePercent: number;
  capRateSpread: number; // Spread from entry cap rate
}

export interface UnderwritingResults {
  // Acquisition Metrics
  purchasePrice: number;
  pricePerUnit: number;
  pricePerSF: number;
  downPayment: number;
  loanAmount: number;
  ltv: number;
  closingCosts: number;
  acquisitionFee: number;
  totalEquityRequired: number;

  // Year 1 Metrics
  year1: {
    grossIncome: number;
    vacancy: number;
    concessions: number;
    badDebt: number;
    effectiveGrossIncome: number;
    operatingExpenses: number;
    noi: number;
    debtService: number;
    cashFlow: number;
    cashOnCashReturn: number;
    debtServiceCoverageRatio: number;
    yieldOnCost: number;
    cashBreakEvenOccupancy: number;
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
  exitCapRate: number;
  loanPaydown: number;
  dispositionFee: number;
  saleProceeds: number;
}

export interface YearlyProjection {
  year: number;
  grossPotentialRent: number;
  lossToLease: number; // Difference between market rent and in-place rent
  grossIncome: number;
  vacancy: number;
  concessions: number;
  badDebt: number;
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

export interface AssumptionPreset {
  name: string;
  description: string;
  inputs: Partial<UnderwritingInputs>;
}
