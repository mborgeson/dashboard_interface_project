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
    monthlyExpenses: {
      propertyTax: number;
      insurance: number;
      utilities: number;
      management: number;
      repairs: number;
      payroll: number;
      marketing: number;
      other: number;
      total: number;
    };
    noi: number;
    operatingExpenseRatio: number;
  };
  performance: {
    cashOnCashReturn: number;
    irr: number;
    equityMultiple: number;
    totalReturnDollars: number;
    totalReturnPercent: number;
  };
  images: {
    main: string;
    gallery: string[];
  };
}

export type PhoenixSubmarket =
  | 'Scottsdale'
  | 'Tempe'
  | 'Mesa'
  | 'Gilbert'
  | 'Chandler'
  | 'Phoenix Central'
  | 'Phoenix North'
  | 'Phoenix West';

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
