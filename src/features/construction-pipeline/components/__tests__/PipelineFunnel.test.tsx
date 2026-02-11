import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PipelineFunnel } from '../PipelineFunnel';
import type { PipelineFunnelItem } from '../../types';

// Mock Recharts to avoid canvas/SVG issues in JSDOM
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 400, height: 300 }}>
        {children}
      </div>
    ),
  };
});

const sampleData: PipelineFunnelItem[] = [
  { status: 'proposed', projectCount: 20, totalUnits: 5000, cumulativeUnits: 5000 },
  { status: 'final_planning', projectCount: 15, totalUnits: 3000, cumulativeUnits: 8000 },
  { status: 'permitted', projectCount: 10, totalUnits: 2500, cumulativeUnits: 10500 },
  { status: 'under_construction', projectCount: 25, totalUnits: 7000, cumulativeUnits: 17500 },
  { status: 'delivered', projectCount: 30, totalUnits: 8000, cumulativeUnits: 25500 },
];

describe('PipelineFunnel', () => {
  it('renders without crashing when loading', () => {
    render(<PipelineFunnel data={[]} isLoading={true} />);
    expect(screen.getByText('Pipeline Funnel')).toBeInTheDocument();
  });

  it('shows loading skeleton when isLoading is true', () => {
    const { container } = render(
      <PipelineFunnel data={[]} isLoading={true} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows empty state when data is empty', () => {
    render(<PipelineFunnel data={[]} isLoading={false} />);
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('renders card title with data', () => {
    render(<PipelineFunnel data={sampleData} isLoading={false} />);
    expect(
      screen.getByText('Pipeline Funnel — Units by Stage'),
    ).toBeInTheDocument();
  });

  it('renders chart container with data', () => {
    render(<PipelineFunnel data={sampleData} isLoading={false} />);
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });
});
