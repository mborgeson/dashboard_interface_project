import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PropertyDetailPanel } from '../components/PropertyDetailPanel';
import type { Property } from '@/types';

// Factory for a complete property with sane defaults
function makeProperty(overrides: Partial<Property> = {}): Property {
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
      submarket: 'Tempe',
    },
    propertyDetails: {
      units: 200,
      squareFeet: 150000,
      averageUnitSize: 750,
      yearBuilt: 2005,
      propertyClass: 'A',
      assetType: 'Multifamily',
      amenities: [],
    },
    acquisition: {
      date: new Date('2021-01-01'),
      purchasePrice: 25000000,
      pricePerUnit: 125000,
      closingCosts: 500000,
      acquisitionFee: 250000,
      totalInvested: 10000000,
      landAndAcquisitionCosts: 5000000,
      hardCosts: 3000000,
      softCosts: 1000000,
      lenderClosingCosts: 200000,
      equityClosingCosts: 100000,
      totalAcquisitionBudget: 26000000,
    },
    financing: {
      loanAmount: 18000000,
      loanToValue: 0.72,
      interestRate: 0.045,
      loanTerm: 10,
      amortization: 30,
      monthlyPayment: 91000,
      lender: 'Test Bank',
      originationDate: new Date('2021-01-01'),
      maturityDate: new Date('2031-01-01'),
    },
    valuation: {
      currentValue: 30000000,
      lastAppraisalDate: new Date('2024-06-01'),
      capRate: 0.055,
      appreciationSinceAcquisition: 0.2,
    },
    operations: {
      occupancy: 0.95,
      averageRent: 1200,
      rentPerSqft: 1.6,
      monthlyRevenue: 228000,
      otherIncome: 15000,
      expenses: {
        realEstateTaxes: 300000,
        otherExpenses: 50000,
        propertyInsurance: 80000,
        staffingPayroll: 200000,
        propertyManagementFee: 100000,
        repairsAndMaintenance: 75000,
        turnover: 25000,
        contractServices: 30000,
        reservesForReplacement: 50000,
        adminLegalSecurity: 40000,
        advertisingLeasingMarketing: 20000,
        total: 970000,
      },
      noi: 1766000,
      operatingExpenseRatio: 0.35,
      grossPotentialRevenue: 2880000,
      netRentalIncome: 2736000,
      otherIncomeAnnual: 180000,
      vacancyLoss: 144000,
      concessions: 0,
    },
    operationsByYear: [],
    performance: {
      leveredIrr: 0.15,
      leveredMoic: 2.1,
      unleveredIrr: 0.09,
      unleveredMoic: 1.5,
      totalEquityCommitment: 10000000,
      totalCashFlowsToEquity: 21000000,
      netCashFlowsToEquity: 11000000,
      holdPeriodYears: 5,
      exitCapRate: 0.05,
      totalBasisPerUnitClose: 130000,
      seniorLoanBasisPerUnitClose: 90000,
      totalBasisPerUnitExit: 150000,
      seniorLoanBasisPerUnitExit: 95000,
    },
    images: { main: '', gallery: [] },
    ...overrides,
  };
}

describe('PropertyDetailPanel', () => {
  const onClose = vi.fn();

  it('renders property name and address', () => {
    render(<PropertyDetailPanel property={makeProperty()} onClose={onClose} />);
    expect(screen.getByText('Test Property')).toBeInTheDocument();
    expect(screen.getByText(/123 Main St/)).toBeInTheDocument();
    expect(screen.getByText(/Phoenix, AZ 85001/)).toBeInTheDocument();
  });

  it('renders formatted financial metrics for a property with data', () => {
    render(<PropertyDetailPanel property={makeProperty()} onClose={onClose} />);
    // Value: $30M → "$30.0M"
    expect(screen.getByText('$30.0M')).toBeInTheDocument();
    // NOI: $1,766,000 → "$1.8M"
    expect(screen.getByText('$1.8M')).toBeInTheDocument();
    // Cap Rate: 0.055 → "5.5%"
    expect(screen.getByText('5.5%')).toBeInTheDocument();
    // IRR: 0.15 → "15.0%"
    expect(screen.getByText('15.0%')).toBeInTheDocument();
    // Occupancy: 0.95 → "95.0%"
    expect(screen.getByText('95.0%')).toBeInTheDocument();
  });

  it('renders "N/A" for missing/zero financial metrics', () => {
    const prop = makeProperty({
      valuation: {
        currentValue: 0,
        lastAppraisalDate: new Date(),
        capRate: 0,
        appreciationSinceAcquisition: 0,
      },
      operations: {
        ...makeProperty().operations,
        noi: 0,
        occupancy: 0,
      },
      performance: {
        ...makeProperty().performance,
        leveredIrr: 0,
      },
    });
    render(<PropertyDetailPanel property={prop} onClose={onClose} />);

    // All four financial metrics + occupancy should show N/A
    const naElements = screen.getAllByText('N/A');
    // Property Value, NOI, Cap Rate, IRR, Occupancy = 5 instances
    expect(naElements.length).toBeGreaterThanOrEqual(5);
  });

  it('hides occupancy bar when occupancy is 0 (missing data)', () => {
    const prop = makeProperty({
      operations: { ...makeProperty().operations, occupancy: 0 },
    });
    const { container } = render(
      <PropertyDetailPanel property={prop} onClose={onClose} />
    );
    // The progress bar div should not exist
    const progressBar = container.querySelector('.bg-primary-600.h-2');
    expect(progressBar).toBeNull();
  });

  it('shows occupancy bar when occupancy is > 0', () => {
    const { container } = render(
      <PropertyDetailPanel property={makeProperty()} onClose={onClose} />
    );
    const progressBar = container.querySelector('.bg-primary-600.h-2');
    expect(progressBar).not.toBeNull();
  });

  it('"View Full Details" links to /properties/:id', () => {
    const prop = makeProperty({ id: 'prop-42' });
    render(<PropertyDetailPanel property={prop} onClose={onClose} />);
    const link = screen.getByText('View Full Details').closest('a');
    expect(link).toHaveAttribute('href', '/properties/prop-42');
  });

  it('calls onClose when close button is clicked', async () => {
    render(<PropertyDetailPanel property={makeProperty()} onClose={onClose} />);
    const closeBtn = screen.getByLabelText('Close');
    closeBtn.click();
    expect(onClose).toHaveBeenCalled();
  });
});
