/**
 * Factory functions for test data.
 *
 * Each factory returns a minimal valid object matching the raw backend API
 * shape (snake_case). Pass overrides to customise individual fields.
 *
 * Usage:
 *   const deal = createMockBackendDeal({ asking_price: '25000000' });
 *   const prop = createMockProperty({ name: 'Sunset Apartments' });
 */
import type { Deal } from '@/types/deal';
import type { Property } from '@/types/property';

// ---------------------------------------------------------------------------
// Backend deal (snake_case, matches backendDealSchema input)
// ---------------------------------------------------------------------------

/** Create a raw backend deal payload (snake_case) for schema tests. */
export function createMockBackendDeal(
  overrides: Record<string, unknown> = {},
) {
  return {
    id: 1,
    name: 'Test Property (Phoenix, AZ)',
    deal_type: 'acquisition',
    property_id: null,
    assigned_user_id: null,
    stage: 'active_review',
    stage_order: 2,
    asking_price: '5000000',
    offer_price: null,
    final_price: null,
    projected_irr: null,
    projected_coc: null,
    projected_equity_multiple: null,
    hold_period_years: null,
    initial_contact_date: null,
    actual_close_date: null,
    source: null,
    broker_name: null,
    notes: null,
    investment_thesis: null,
    deal_score: null,
    priority: null,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-02-01T12:00:00Z',
    stage_updated_at: null,
    total_units: 100,
    avg_unit_sf: null,
    current_owner: null,
    last_sale_price_per_unit: null,
    last_sale_date: null,
    t12_return_on_cost: null,
    levered_irr: null,
    levered_moic: null,
    total_equity_commitment: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Frontend Deal (camelCase, after Zod transform)
// ---------------------------------------------------------------------------

/** Create a frontend Deal object (camelCase, post-transform). */
export function createMockDeal(overrides?: Partial<Deal>): Deal {
  return {
    id: '1',
    propertyName: 'Test Property (Phoenix, AZ)',
    address: { street: 'Test Property', city: 'Phoenix', state: 'AZ' },
    value: 5000000,
    capRate: 0,
    stage: 'active_review',
    daysInStage: 0,
    totalDaysInPipeline: 0,
    assignee: '',
    propertyType: 'acquisition',
    createdAt: new Date('2025-01-15T10:00:00Z'),
    timeline: [],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Backend property (matches raw API payload for propertySchema)
// ---------------------------------------------------------------------------

/** Create a raw backend property payload for schema tests. */
export function createMockBackendProperty(
  overrides: Record<string, unknown> = {},
) {
  return {
    id: 'prop-1',
    name: 'Test Property',
    address: {
      street: '123 Main St',
      city: 'Phoenix',
      state: 'AZ',
      zip: '85001',
      latitude: 33.45,
      longitude: -112.07,
      submarket: 'Central Phoenix',
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
    operationsByYear: [],
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

// ---------------------------------------------------------------------------
// Frontend Property (camelCase, post-transform)
// ---------------------------------------------------------------------------

/** Create a frontend Property object (post-Zod-transform). */
export function createMockProperty(overrides?: Partial<Property>): Property {
  return {
    id: 'prop-1',
    name: 'Test Property',
    address: {
      street: '123 Main St',
      city: 'Phoenix',
      state: 'AZ',
      zip: '85001',
      latitude: 33.45,
      longitude: -112.07,
      submarket: 'Central Phoenix',
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
      date: new Date('2023-01-15T00:00:00Z'),
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
      originationDate: new Date('2023-01-15T00:00:00Z'),
      maturityDate: new Date('2033-01-15T00:00:00Z'),
    },
    valuation: {
      currentValue: 52000000,
      lastAppraisalDate: new Date('2024-06-01T00:00:00Z'),
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
    operationsByYear: [],
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

// ---------------------------------------------------------------------------
// Backend sale record (snake_case, matches saleRecordSchema input)
// ---------------------------------------------------------------------------

/** Create a raw backend sale record for schema/hook tests. */
export function createMockBackendSaleRecord(
  overrides: Record<string, unknown> = {},
) {
  return {
    id: 1,
    property_name: 'Test Property',
    property_address: '123 Main St',
    property_city: 'Phoenix',
    submarket_cluster: 'Central Phoenix',
    seller_true_company: 'ABC Sellers LLC',
    star_rating: '4 Star',
    year_built: 2005,
    number_of_units: 200,
    avg_unit_sf: 850,
    sale_date: '2024-06-15',
    sale_price: 45000000,
    price_per_unit: 225000,
    buyer_true_company: 'XYZ Buyers Inc',
    latitude: 33.4484,
    longitude: -112.074,
    nrsf: 170000,
    price_per_nrsf: 264.71,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Paginated API response wrapper
// ---------------------------------------------------------------------------

/** Wrap data in a paginated response envelope. */
export function createMockPaginatedResponse<T>(
  data: T[],
  meta?: { total?: number; page?: number; pageSize?: number },
) {
  const total = meta?.total ?? data.length;
  const pageSize = meta?.pageSize ?? 25;
  const page = meta?.page ?? 1;
  return {
    data,
    total,
    page,
    page_size: pageSize,
    total_pages: Math.ceil(total / pageSize),
  };
}
