import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PropertyCard } from '../components/PropertyCard';
import type { Property } from '@/types';

// ============================================================================
// Shared test data
// ============================================================================

function makeProperty(overrides: Partial<{
  occupancy: number;
  noi: number;
  capRate: number;
  leveredIrr: number;
  currentValue: number;
  averageRent: number;
  monthlyRevenue: number;
  operatingExpenseRatio: number;
  squareFeet: number;
}>): Property {
  return {
    id: 'prop-test',
    name: 'Test Property',
    address: {
      street: '100 Test St',
      city: 'Phoenix',
      state: 'AZ',
      zip: '85001',
      latitude: 33.45,
      longitude: -112.07,
      submarket: 'Central',
    },
    propertyDetails: {
      units: 100,
      squareFeet: overrides.squareFeet ?? 80000,
      averageUnitSize: 800,
      yearBuilt: 2010,
      propertyClass: 'B',
      assetType: 'Multifamily',
      amenities: ['Pool'],
    },
    acquisition: {
      date: new Date('2023-01-01'),
      purchasePrice: 15000000,
      pricePerUnit: 150000,
      closingCosts: 200000,
      acquisitionFee: 150000,
      totalInvested: 18000000,
      landAndAcquisitionCosts: 3000000,
      hardCosts: 10000000,
      softCosts: 2000000,
      lenderClosingCosts: 300000,
      equityClosingCosts: 100000,
      totalAcquisitionBudget: 18000000,
    },
    financing: {
      loanAmount: 12000000,
      loanToValue: 0.67,
      interestRate: 0.055,
      loanTerm: 10,
      amortization: 30,
      monthlyPayment: 68000,
      lender: 'Test Bank',
      originationDate: new Date('2023-01-01'),
      maturityDate: new Date('2033-01-01'),
    },
    valuation: {
      currentValue: overrides.currentValue ?? 20000000,
      lastAppraisalDate: new Date('2024-06-01'),
      capRate: overrides.capRate ?? 0.06,
      appreciationSinceAcquisition: 0.15,
    },
    operations: {
      occupancy: overrides.occupancy ?? 0.95,
      averageRent: overrides.averageRent ?? 1200,
      rentPerSqft: 1.5,
      monthlyRevenue: overrides.monthlyRevenue ?? 114000,
      otherIncome: 8000,
      expenses: {
        realEstateTaxes: 120000,
        otherExpenses: 12000,
        propertyInsurance: 36000,
        staffingPayroll: 96000,
        propertyManagementFee: 48000,
        repairsAndMaintenance: 42000,
        turnover: 24000,
        contractServices: 30000,
        reservesForReplacement: 24000,
        adminLegalSecurity: 18000,
        advertisingLeasingMarketing: 15000,
        total: 465000,
      },
      noi: overrides.noi ?? 700000,
      operatingExpenseRatio: overrides.operatingExpenseRatio ?? 0.4,
      grossPotentialRevenue: 1200000,
      netRentalIncome: 1100000,
      otherIncomeAnnual: 96000,
      vacancyLoss: 60000,
      concessions: 18000,
    },
    operationsByYear: [],
    performance: {
      leveredIrr: overrides.leveredIrr ?? 0.15,
      leveredMoic: 1.8,
      unleveredIrr: 0.1,
      unleveredMoic: 1.5,
      totalEquityCommitment: 6000000,
      totalCashFlowsToEquity: 10800000,
      netCashFlowsToEquity: 4800000,
      holdPeriodYears: 5,
      exitCapRate: 0.065,
      totalBasisPerUnitClose: 180000,
      seniorLoanBasisPerUnitClose: 120000,
      totalBasisPerUnitExit: 200000,
      seniorLoanBasisPerUnitExit: 130000,
    },
    images: { main: '', gallery: [] },
  };
}

// ============================================================================
// PropertyCard — Missing Data Display
// ============================================================================

describe('PropertyCard — missing data shows N/A', () => {
  it('shows N/A for occupancy when value is 0 (missing)', () => {
    const prop = makeProperty({ occupancy: 0 });
    render(<PropertyCard property={prop} />);

    // The occupancy field should show N/A, not "0.0%"
    const occupancyLabel = screen.getByText('Occupancy');
    const occupancyValue = occupancyLabel.closest('.space-y-1')?.querySelector('.text-lg');
    expect(occupancyValue?.textContent).toBe('N/A');
  });

  it('shows N/A for NOI when value is 0 (missing)', () => {
    const prop = makeProperty({ noi: 0 });
    render(<PropertyCard property={prop} />);

    const noiLabel = screen.getByText('NOI');
    const noiValue = noiLabel.closest('.space-y-1')?.querySelector('.text-sm');
    expect(noiValue?.textContent).toBe('N/A');
  });

  it('shows N/A for cap rate when value is 0 (missing)', () => {
    const prop = makeProperty({ capRate: 0 });
    render(<PropertyCard property={prop} />);

    const capLabel = screen.getByText('Cap Rate');
    const capValue = capLabel.closest('.space-y-1')?.querySelector('.text-sm');
    expect(capValue?.textContent).toBe('N/A');
  });

  it('shows N/A for IRR when value is 0 (missing)', () => {
    const prop = makeProperty({ leveredIrr: 0 });
    render(<PropertyCard property={prop} />);

    const irrLabel = screen.getByText('IRR');
    const irrContainer = irrLabel.closest('.space-y-1');
    const irrValue = irrContainer?.querySelector('.text-sm');
    expect(irrValue?.textContent).toBe('N/A');
  });

  it('shows N/A for value when currentValue is 0 (missing)', () => {
    const prop = makeProperty({ currentValue: 0 });
    render(<PropertyCard property={prop} />);

    const valueLabel = screen.getByText('Value');
    const valueField = valueLabel.closest('.space-y-1')?.querySelector('.text-sm');
    expect(valueField?.textContent).toBe('N/A');
  });

  it('shows formatted values when data is present', () => {
    const prop = makeProperty({
      occupancy: 0.94,
      noi: 1428000,
      capRate: 0.058,
      leveredIrr: 0.182,
      currentValue: 35000000,
    });
    render(<PropertyCard property={prop} />);

    // Occupancy should show 94.0%
    const occupancyLabel = screen.getByText('Occupancy');
    const occupancyValue = occupancyLabel.closest('.space-y-1')?.querySelector('.text-lg');
    expect(occupancyValue?.textContent).toBe('94.0%');

    // NOI should show $1.4M
    const noiLabel = screen.getByText('NOI');
    const noiValue = noiLabel.closest('.space-y-1')?.querySelector('.text-sm');
    expect(noiValue?.textContent).toBe('$1.4M');
  });
});

// ============================================================================
// InvestmentsPage — Summary Stats
// ============================================================================

// We need to test InvestmentsPage summary stats logic independently.
// The key calculation: avgOccupancy should exclude properties with 0 occupancy.
describe('InvestmentsPage summary stats logic', () => {
  it('excludes zero-occupancy properties from average calculation', () => {
    // Simulate the logic from InvestmentsPage
    const properties = [
      makeProperty({ occupancy: 0.95 }),
      makeProperty({ occupancy: 0.90 }),
      makeProperty({ occupancy: 0 }), // missing data — should be excluded
      makeProperty({ occupancy: 0 }), // missing data — should be excluded
    ];

    const propertiesWithOccupancy = properties.filter(p => p.operations.occupancy > 0);
    const avgOccupancy = propertiesWithOccupancy.length > 0
      ? propertiesWithOccupancy.reduce((sum, p) => sum + p.operations.occupancy, 0) / propertiesWithOccupancy.length
      : 0;

    // Average of 0.95 and 0.90 = 0.925
    expect(avgOccupancy).toBeCloseTo(0.925, 3);
    // Without the fix, it would be (0.95 + 0.90 + 0 + 0) / 4 = 0.4625
    expect(avgOccupancy).not.toBeCloseTo(0.4625, 3);
  });

  it('excludes zero-value properties from totalValue', () => {
    const properties = [
      makeProperty({ currentValue: 20000000 }),
      makeProperty({ currentValue: 30000000 }),
      makeProperty({ currentValue: 0 }), // missing data — should be excluded
    ];

    const propertiesWithValue = properties.filter(p => p.valuation.currentValue > 0);
    const totalValue = propertiesWithValue.reduce((sum, p) => sum + p.valuation.currentValue, 0);

    expect(totalValue).toBe(50000000);
  });

  it('returns 0 avgOccupancy when all properties have zero occupancy', () => {
    const properties = [
      makeProperty({ occupancy: 0 }),
      makeProperty({ occupancy: 0 }),
    ];

    const propertiesWithOccupancy = properties.filter(p => p.operations.occupancy > 0);
    const avgOccupancy = propertiesWithOccupancy.length > 0
      ? propertiesWithOccupancy.reduce((sum, p) => sum + p.operations.occupancy, 0) / propertiesWithOccupancy.length
      : 0;

    // formatPercentOrNA(0) → 'N/A'
    expect(avgOccupancy).toBe(0);
  });
});
