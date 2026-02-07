import { describe, it, expect } from 'vitest';
import {
  propertySchema,
  propertiesResponseSchema,
  propertySummaryStatsSchema,
} from '../property';

/** Minimal valid property matching the API shape */
function makeProperty(overrides: Record<string, unknown> = {}) {
  return {
    id: 'prop-1',
    name: 'Test Property',
    address: {
      street: '123 Main St',
      city: 'Tempe',
      state: 'AZ',
      zip: '85281',
      latitude: 33.4255,
      longitude: -111.94,
      submarket: 'Tempe',
    },
    propertyDetails: {
      units: 200,
      squareFeet: 180000,
      averageUnitSize: 900,
      yearBuilt: 2005,
      propertyClass: 'B',
      assetType: 'Garden',
      amenities: ['Pool', 'Gym'],
    },
    acquisition: {
      date: '2023-01-15T00:00:00Z',
      purchasePrice: 45000000,
      pricePerUnit: 225000,
      closingCosts: 500000,
      acquisitionFee: 250000,
      totalInvested: 15000000,
      landAndAcquisitionCosts: 46000000,
      hardCosts: 2000000,
      softCosts: 500000,
      lenderClosingCosts: 100000,
      equityClosingCosts: 50000,
      totalAcquisitionBudget: 49000000,
    },
    financing: {
      loanAmount: 30000000,
      loanToValue: 0.667,
      interestRate: 0.045,
      loanTerm: 10,
      amortization: 30,
      monthlyPayment: 152000,
      lender: 'Wells Fargo',
      originationDate: '2023-01-15T00:00:00Z',
      maturityDate: '2033-01-15T00:00:00Z',
    },
    valuation: {
      currentValue: 52000000,
      lastAppraisalDate: '2024-06-01T00:00:00Z',
      capRate: 0.055,
      appreciationSinceAcquisition: 0.155,
    },
    operations: {
      occupancy: 0.94,
      averageRent: 1500,
      rentPerSqft: 1.67,
      monthlyRevenue: 282000,
      otherIncome: 15000,
      expenses: {
        realEstateTaxes: 400000,
        otherExpenses: 50000,
        propertyInsurance: 120000,
        staffingPayroll: 350000,
        propertyManagementFee: 100000,
        repairsAndMaintenance: 80000,
        turnover: 40000,
        contractServices: 60000,
        reservesForReplacement: 50000,
        adminLegalSecurity: 30000,
        advertisingLeasingMarketing: 25000,
        total: 1305000,
      },
      noi: 2259000,
      operatingExpenseRatio: 0.366,
      grossPotentialRevenue: 3600000,
      netRentalIncome: 3384000,
      otherIncomeAnnual: 180000,
      vacancyLoss: 216000,
      concessions: 0,
    },
    operationsByYear: [
      {
        year: 2023,
        grossPotentialRevenue: 3600000,
        lossToLease: 0,
        vacancyLoss: 216000,
        badDebts: 18000,
        concessions: 0,
        otherLoss: 0,
        netRentalIncome: 3366000,
        otherIncome: 180000,
        laundryIncome: 24000,
        parkingIncome: 48000,
        petIncome: 36000,
        storageIncome: 12000,
        utilityIncome: 60000,
        otherMiscIncome: 0,
        effectiveGrossIncome: 3546000,
        noi: 2241000,
        totalOperatingExpenses: 1305000,
        expenses: {
          realEstateTaxes: 400000,
          propertyInsurance: 120000,
          staffingPayroll: 350000,
          propertyManagementFee: 100000,
          repairsAndMaintenance: 80000,
          turnover: 40000,
          contractServices: 60000,
          reservesForReplacement: 50000,
          adminLegalSecurity: 30000,
          advertisingLeasingMarketing: 25000,
          otherExpenses: 50000,
          utilities: 0,
        },
      },
    ],
    performance: {
      leveredIrr: 0.18,
      leveredMoic: 2.1,
      unleveredIrr: null,
      unleveredMoic: null,
      totalEquityCommitment: 15000000,
      totalCashFlowsToEquity: 31500000,
      netCashFlowsToEquity: 16500000,
      holdPeriodYears: 5,
      exitCapRate: 0.06,
      totalBasisPerUnitClose: 245000,
      seniorLoanBasisPerUnitClose: 150000,
      totalBasisPerUnitExit: null,
      seniorLoanBasisPerUnitExit: null,
    },
    images: {
      main: '/images/property1.jpg',
      gallery: ['/images/p1-1.jpg', '/images/p1-2.jpg'],
    },
    ...overrides,
  };
}

describe('propertySchema', () => {
  it('parses a valid property and transforms dates', () => {
    const result = propertySchema.parse(makeProperty());

    // Date transforms
    expect(result.acquisition.date).toBeInstanceOf(Date);
    expect(result.financing.originationDate).toBeInstanceOf(Date);
    expect(result.financing.maturityDate).toBeInstanceOf(Date);
    expect(result.valuation.lastAppraisalDate).toBeInstanceOf(Date);

    // Values preserved
    expect(result.id).toBe('prop-1');
    expect(result.name).toBe('Test Property');
    expect(result.propertyDetails.units).toBe(200);
    expect(result.address.submarket).toBe('Tempe');
  });

  it('handles null maturityDate', () => {
    const raw = makeProperty({
      financing: {
        ...makeProperty().financing,
        maturityDate: null,
      },
    });
    const result = propertySchema.parse(raw);
    expect(result.financing.maturityDate).toBeNull();
  });

  it('handles nullable performance fields', () => {
    const result = propertySchema.parse(makeProperty());
    expect(result.performance.unleveredIrr).toBeNull();
    expect(result.performance.unleveredMoic).toBeNull();
  });

  it('validates operationsByYear as array', () => {
    const result = propertySchema.parse(makeProperty());
    expect(Array.isArray(result.operationsByYear)).toBe(true);
    expect(result.operationsByYear).toHaveLength(1);
    expect(result.operationsByYear[0].year).toBe(2023);
  });

  it('throws on missing required field', () => {
    const raw = makeProperty();
    delete (raw as Record<string, unknown>).name;
    expect(() => propertySchema.parse(raw)).toThrow();
  });

  it('throws on invalid property class', () => {
    const raw = makeProperty({
      propertyDetails: {
        ...makeProperty().propertyDetails,
        propertyClass: 'D',
      },
    });
    expect(() => propertySchema.parse(raw)).toThrow();
  });
});

describe('propertiesResponseSchema', () => {
  it('parses response with array of properties', () => {
    const raw = { properties: [makeProperty()], total: 1 };
    const result = propertiesResponseSchema.parse(raw);
    expect(result.properties).toHaveLength(1);
    expect(result.total).toBe(1);
    expect(result.properties[0].acquisition.date).toBeInstanceOf(Date);
  });

  it('parses empty response', () => {
    const raw = { properties: [], total: 0 };
    const result = propertiesResponseSchema.parse(raw);
    expect(result.properties).toHaveLength(0);
    expect(result.total).toBe(0);
  });
});

describe('propertySummaryStatsSchema', () => {
  it('parses valid summary stats', () => {
    const raw = {
      totalProperties: 10,
      totalUnits: 2500,
      totalValue: 500000000,
      totalInvested: 200000000,
      totalNOI: 25000000,
      averageOccupancy: 0.94,
      averageCapRate: 0.055,
      portfolioCashOnCash: 0.08,
      portfolioIRR: 0.18,
    };
    const result = propertySummaryStatsSchema.parse(raw);
    expect(result.totalProperties).toBe(10);
    expect(result.portfolioIRR).toBe(0.18);
  });

  it('throws on missing field', () => {
    const raw = { totalProperties: 10 };
    expect(() => propertySummaryStatsSchema.parse(raw)).toThrow();
  });
});
