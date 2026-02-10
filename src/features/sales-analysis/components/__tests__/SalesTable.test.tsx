import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { SalesTable } from '../SalesTable';
import type { SaleRecord } from '../../types';

function makeSaleRecord(overrides: Partial<SaleRecord> = {}): SaleRecord {
  return {
    id: 1,
    propertyName: 'Phoenix Gateway',
    propertyAddress: '123 Main St',
    propertyCity: 'Phoenix',
    submarketCluster: 'Central Phoenix',
    sellerTrueCompany: 'ABC Sellers',
    starRating: '4 Star',
    yearBuilt: 2005,
    numberOfUnits: 200,
    avgUnitSf: 850,
    saleDate: '2024-06-15',
    salePrice: 45000000,
    pricePerUnit: 225000,
    buyerTrueCompany: 'XYZ Buyers',
    latitude: 33.4484,
    longitude: -112.074,
    nrsf: 170000,
    pricePerNrsf: 264.71,
    ...overrides,
  };
}

describe('SalesTable', () => {
  it('renders without crashing', () => {
    render(<SalesTable data={[]} isLoading={false} />);
    expect(screen.getByText('Sales Data')).toBeInTheDocument();
  });

  it('shows loading skeleton rows when isLoading is true', () => {
    const { container } = render(
      <SalesTable data={[]} isLoading={true} />,
    );
    // Skeleton rows use the Skeleton component with animate-pulse class
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('does not show record count when loading', () => {
    render(<SalesTable data={[]} isLoading={true} />);
    expect(screen.queryByText('0 records')).not.toBeInTheDocument();
  });

  it('shows empty state when data is empty and not loading', () => {
    render(<SalesTable data={[]} isLoading={false} />);
    expect(
      screen.getByText('No sales data matches your filters.'),
    ).toBeInTheDocument();
  });

  it('renders record count when data is present', () => {
    const records = [makeSaleRecord({ id: 1 }), makeSaleRecord({ id: 2 })];
    render(<SalesTable data={records} isLoading={false} />);
    expect(screen.getByText('2 records')).toBeInTheDocument();
  });

  it('renders data rows with property names', () => {
    const records = [
      makeSaleRecord({ id: 1, propertyName: 'Phoenix Gateway' }),
      makeSaleRecord({ id: 2, propertyName: 'Mesa Ridge' }),
    ];
    render(<SalesTable data={records} isLoading={false} />);
    expect(screen.getByText('Phoenix Gateway')).toBeInTheDocument();
    expect(screen.getByText('Mesa Ridge')).toBeInTheDocument();
  });

  it('renders column headers', () => {
    render(<SalesTable data={[]} isLoading={false} />);
    expect(screen.getByText('Property Name')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
    expect(screen.getByText('Submarket')).toBeInTheDocument();
    expect(screen.getByText('Sale Price')).toBeInTheDocument();
    expect(screen.getByText('Price/Unit')).toBeInTheDocument();
    expect(screen.getByText('# Units')).toBeInTheDocument();
  });

  it('displays -- for null values', () => {
    const record = makeSaleRecord({
      id: 1,
      propertyName: null,
      propertyCity: null,
      salePrice: null,
    });
    render(<SalesTable data={[record]} isLoading={false} />);
    // Multiple '--' cells should appear for null values
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('formats sale date correctly', () => {
    const record = makeSaleRecord({ saleDate: '2024-06-15' });
    render(<SalesTable data={[record]} isLoading={false} />);
    expect(screen.getByText('06/15/2024')).toBeInTheDocument();
  });
});
