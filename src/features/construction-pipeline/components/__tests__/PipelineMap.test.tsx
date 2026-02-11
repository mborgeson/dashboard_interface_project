import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import type { ProjectRecord } from '../../types';

// Mock leaflet and leaflet.markercluster before importing the component
vi.mock('leaflet', () => {
  const mockMap = {
    remove: vi.fn(),
    addLayer: vi.fn(),
    removeLayer: vi.fn(),
  };
  const mockTileLayer = { addTo: vi.fn() };
  const mockCircleMarker = { bindPopup: vi.fn().mockReturnThis() };
  const mockClusterGroup = {
    addLayer: vi.fn(),
  };

  return {
    default: {
      map: vi.fn(() => mockMap),
      tileLayer: vi.fn(() => mockTileLayer),
      circleMarker: vi.fn(() => mockCircleMarker),
      markerClusterGroup: vi.fn(() => mockClusterGroup),
      icon: vi.fn(() => ({})),
      Marker: { prototype: { options: {} } },
    },
    map: vi.fn(() => mockMap),
    tileLayer: vi.fn(() => mockTileLayer),
    circleMarker: vi.fn(() => mockCircleMarker),
    markerClusterGroup: vi.fn(() => mockClusterGroup),
    icon: vi.fn(() => ({})),
    Marker: { prototype: { options: {} } },
  };
});

vi.mock('leaflet.markercluster', () => ({}));

vi.mock('leaflet/dist/images/marker-icon.png', () => ({
  default: 'marker-icon.png',
}));
vi.mock('leaflet/dist/images/marker-shadow.png', () => ({
  default: 'marker-shadow.png',
}));

// Import after mocks
import { PipelineMap } from '../PipelineMap';

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

describe('PipelineMap', () => {
  it('renders without crashing', () => {
    render(<PipelineMap data={[]} isLoading={false} />);
    expect(screen.getByText('Pipeline Map')).toBeInTheDocument();
  });

  it('shows loading skeleton when isLoading is true', () => {
    const { container } = render(
      <PipelineMap data={[]} isLoading={true} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows mapped count', () => {
    const projects = [
      makeProject({ id: 1, latitude: 33.41, longitude: -111.83 }),
      makeProject({ id: 2, latitude: null, longitude: null }),
    ];
    render(<PipelineMap data={projects} isLoading={false} />);
    expect(screen.getByText(/1 mapped of 2 projects/)).toBeInTheDocument();
  });

  it('renders legend with status labels', () => {
    render(<PipelineMap data={[makeProject()]} isLoading={false} />);
    expect(screen.getByText('Proposed')).toBeInTheDocument();
    expect(screen.getByText('Under Construction')).toBeInTheDocument();
    expect(screen.getByText('Delivered')).toBeInTheDocument();
  });
});
