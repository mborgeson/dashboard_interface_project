import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { DataQualitySummary } from '../DataQualitySummary';
import type { DataQualityReport } from '../../types';

function makeReport(overrides: Partial<DataQualityReport> = {}): DataQualityReport {
  return {
    totalRecords: 500,
    recordsByFile: {
      'file_2024_q1.csv': 200,
      'file_2024_q2.csv': 300,
    },
    nullRates: {
      sale_price: 0.02,
      price_per_unit: 0.12,
      avg_unit_sf: 0.25,
    },
    flaggedOutliers: {
      extreme_price: 3,
      zero_units: 1,
    },
    ...overrides,
  };
}

describe('DataQualitySummary', () => {
  it('renders without crashing', () => {
    render(<DataQualitySummary data={makeReport()} isLoading={false} />);
    expect(screen.getByText('Data Quality Summary')).toBeInTheDocument();
  });

  it('shows loading state with skeleton', () => {
    render(<DataQualitySummary data={undefined} isLoading={true} />);
    expect(screen.getByText('Data Quality Summary')).toBeInTheDocument();
    // ChartSkeleton renders with animate-pulse
  });

  it('shows empty state when data is undefined and not loading', () => {
    render(<DataQualitySummary data={undefined} isLoading={false} />);
    expect(
      screen.getByText('No data quality information available.'),
    ).toBeInTheDocument();
  });

  it('renders total records stat card', () => {
    render(<DataQualitySummary data={makeReport()} isLoading={false} />);
    expect(screen.getByText('Total Records')).toBeInTheDocument();
    expect(screen.getByText('500')).toBeInTheDocument();
  });

  it('renders source files count', () => {
    render(<DataQualitySummary data={makeReport()} isLoading={false} />);
    expect(screen.getByText('Source Files')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders flagged outliers total', () => {
    render(<DataQualitySummary data={makeReport()} isLoading={false} />);
    // "Flagged Outliers" appears both as a stat card label and an h4 heading
    const matches = screen.getAllByText('Flagged Outliers');
    expect(matches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('4')).toBeInTheDocument(); // 3 + 1
  });

  it('renders null rate bars', () => {
    render(<DataQualitySummary data={makeReport()} isLoading={false} />);
    expect(
      screen.getByText('Field Completeness (Null Rates)'),
    ).toBeInTheDocument();
    // sale_price at 2% should display
    expect(screen.getByText('2.0%')).toBeInTheDocument();
    // price_per_unit at 12%
    expect(screen.getByText('12.0%')).toBeInTheDocument();
    // avg_unit_sf at 25%
    expect(screen.getByText('25.0%')).toBeInTheDocument();
  });

  it('renders flagged outlier categories', () => {
    render(<DataQualitySummary data={makeReport()} isLoading={false} />);
    expect(screen.getByText('extreme price')).toBeInTheDocument();
    expect(screen.getByText('zero units')).toBeInTheDocument();
  });

  it('does not render flagged outliers section when empty', () => {
    render(
      <DataQualitySummary
        data={makeReport({ flaggedOutliers: {} })}
        isLoading={false}
      />,
    );
    expect(screen.queryByText('Flagged Outliers', { selector: 'h4' })).not.toBeInTheDocument();
  });
});
