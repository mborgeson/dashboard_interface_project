import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PipelineTable } from '../PipelineTable';
import type { ProjectRecord } from '../../types';

function makeProject(overrides: Partial<ProjectRecord> = {}): ProjectRecord {
  return {
    id: 1,
    projectName: 'Mesa Gateway Apartments',
    projectAddress: '1234 E Main St',
    city: 'Mesa',
    submarketCluster: 'East Valley',
    pipelineStatus: 'under_construction',
    primaryClassification: 'CONV_MR',
    numberOfUnits: 280,
    numberOfStories: 4,
    yearBuilt: 2025,
    developerName: 'Acme Development',
    ownerName: 'Acme Holdings',
    latitude: 33.41,
    longitude: -111.83,
    buildingSf: 250000,
    avgUnitSf: 893,
    starRating: '4 Star',
    rentType: 'Market',
    vacancyPct: 5.2,
    estimatedDeliveryDate: '2026-03-01',
    constructionBegin: '2024-06-15',
    forSalePrice: null,
    sourceType: 'costar',
    ...overrides,
  };
}

describe('PipelineTable', () => {
  it('renders without crashing', () => {
    render(<PipelineTable data={[]} isLoading={false} />);
    expect(screen.getByText('Construction Projects')).toBeInTheDocument();
  });

  it('shows loading skeleton when isLoading is true', () => {
    const { container } = render(
      <PipelineTable data={[]} isLoading={true} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows empty state when data is empty and not loading', () => {
    render(<PipelineTable data={[]} isLoading={false} />);
    expect(screen.getByText('No projects found')).toBeInTheDocument();
  });

  it('renders column headers', () => {
    render(<PipelineTable data={[]} isLoading={false} />);
    expect(screen.getByText('Project Name')).toBeInTheDocument();
    expect(screen.getByText('City')).toBeInTheDocument();
    expect(screen.getByText('Submarket')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Units')).toBeInTheDocument();
    expect(screen.getByText('Developer')).toBeInTheDocument();
    expect(screen.getByText('Rent Type')).toBeInTheDocument();
  });

  it('renders data rows with project names', () => {
    const projects = [
      makeProject({ id: 1, projectName: 'Mesa Gateway Apartments' }),
      makeProject({ id: 2, projectName: 'Tempe Towers' }),
    ];
    render(<PipelineTable data={projects} isLoading={false} />);
    expect(screen.getByText('Mesa Gateway Apartments')).toBeInTheDocument();
    expect(screen.getByText('Tempe Towers')).toBeInTheDocument();
  });

  it('renders status badges', () => {
    const projects = [
      makeProject({ id: 1, pipelineStatus: 'under_construction' }),
      makeProject({ id: 2, pipelineStatus: 'delivered' }),
    ];
    render(<PipelineTable data={projects} isLoading={false} />);
    expect(screen.getByText('Under Construction')).toBeInTheDocument();
    expect(screen.getByText('Delivered')).toBeInTheDocument();
  });

  it('displays -- for null values', () => {
    const project = makeProject({
      id: 1,
      projectName: null,
      city: null,
      numberOfUnits: null,
    });
    render(<PipelineTable data={[project]} isLoading={false} />);
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('formats unit counts with comma separators', () => {
    const project = makeProject({ id: 1, numberOfUnits: 1250 });
    render(<PipelineTable data={[project]} isLoading={false} />);
    expect(screen.getByText('1,250')).toBeInTheDocument();
  });

  it('renders multiple rows correctly', () => {
    const projects = [
      makeProject({ id: 1, city: 'Mesa' }),
      makeProject({ id: 2, city: 'Tempe' }),
      makeProject({ id: 3, city: 'Scottsdale' }),
    ];
    render(<PipelineTable data={projects} isLoading={false} />);
    expect(screen.getByText('Mesa')).toBeInTheDocument();
    expect(screen.getByText('Tempe')).toBeInTheDocument();
    expect(screen.getByText('Scottsdale')).toBeInTheDocument();
  });
});
