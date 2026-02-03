export interface OperatingYearExpenses {
  realEstateTaxes: number;
  propertyInsurance: number;
  staffingPayroll: number;
  propertyManagementFee: number;
  repairsAndMaintenance: number;
  turnover: number;
  contractServices: number;
  reservesForReplacement: number;
  adminLegalSecurity: number;
  advertisingLeasingMarketing: number;
  otherExpenses: number;
  utilities: number;
}

export interface OperatingYear {
  year: number;
  grossPotentialRevenue: number;
  lossToLease: number;
  vacancyLoss: number;
  badDebts: number;
  concessions: number;
  otherLoss: number;
  netRentalIncome: number;
  otherIncome: number;
  laundryIncome: number;
  parkingIncome: number;
  petIncome: number;
  storageIncome: number;
  utilityIncome: number;
  otherMiscIncome: number;
  effectiveGrossIncome: number;
  noi: number;
  totalOperatingExpenses: number;
  expenses: OperatingYearExpenses;
}

export interface Property {
  id: string;
  name: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
    latitude: number;
    longitude: number;
    submarket: PhoenixSubmarket;
  };
  propertyDetails: {
    units: number;
    squareFeet: number;
    averageUnitSize: number;
    yearBuilt: number;
    propertyClass: 'A' | 'B' | 'C';
    assetType: 'Garden' | 'Mid-Rise' | 'High-Rise';
    amenities: string[];
  };
  acquisition: {
    date: Date;
    purchasePrice: number;
    pricePerUnit: number;
    closingCosts: number;
    acquisitionFee: number;
    totalInvested: number;
    landAndAcquisitionCosts: number;
    hardCosts: number;
    softCosts: number;
    lenderClosingCosts: number;
    equityClosingCosts: number;
    totalAcquisitionBudget: number;
  };
  financing: {
    loanAmount: number;
    loanToValue: number;
    interestRate: number;
    loanTerm: number;
    amortization: number;
    monthlyPayment: number;
    lender: string;
    originationDate: Date;
    maturityDate: Date;
  };
  valuation: {
    currentValue: number;
    lastAppraisalDate: Date;
    capRate: number;
    appreciationSinceAcquisition: number;
  };
  operations: {
    occupancy: number;
    averageRent: number;
    rentPerSqft: number;
    monthlyRevenue: number;
    otherIncome: number;
    expenses: {
      realEstateTaxes: number;
      otherExpenses: number;
      propertyInsurance: number;
      staffingPayroll: number;
      propertyManagementFee: number;
      repairsAndMaintenance: number;
      turnover: number;
      contractServices: number;
      reservesForReplacement: number;
      adminLegalSecurity: number;
      advertisingLeasingMarketing: number;
      total: number;
    };
    noi: number;
    operatingExpenseRatio: number;
    grossPotentialRevenue: number;
    netRentalIncome: number;
    otherIncomeAnnual: number;
    vacancyLoss: number;
    concessions: number;
  };
  operationsByYear: OperatingYear[];
  performance: {
    leveredIrr: number;
    leveredMoic: number;
    unleveredIrr: number | null;
    unleveredMoic: number | null;
    totalEquityCommitment: number;
    totalCashFlowsToEquity: number;
    netCashFlowsToEquity: number;
    holdPeriodYears: number;
    exitCapRate: number;
    totalBasisPerUnitClose: number;
    seniorLoanBasisPerUnitClose: number;
    totalBasisPerUnitExit: number | null;
    seniorLoanBasisPerUnitExit: number | null;
  };
  images: {
    main: string;
    gallery: string[];
  };
}

export type PhoenixSubmarket =
  | 'Tempe'
  | 'East Valley'
  | 'South West Valley'
  | 'Downtown Phoenix'
  | 'North Phoenix'
  | 'Deer Valley'
  | 'Chandler'
  | 'North Scottsdale'
  | 'Gilbert'
  | 'Old Town Scottsdale'
  | 'North West Valley'
  | 'South Phoenix'
  | 'West Maricopa County'
  | 'Camelback'
  | 'Southeast Valley';

export interface PropertySummaryStats {
  totalProperties: number;
  totalUnits: number;
  totalValue: number;
  totalInvested: number;
  totalNOI: number;
  averageOccupancy: number;
  averageCapRate: number;
  portfolioCashOnCash: number;
  portfolioIRR: number;
}
