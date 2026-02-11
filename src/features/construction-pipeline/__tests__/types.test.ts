import { describe, it, expect } from 'vitest';
import type {
  ProjectRecord,
  ProjectsResponse,
  ConstructionFilters,
  ConstructionFilterOptions,
  PipelineSummaryItem,
  PipelineFunnelItem,
  PermitTrendPoint,
  EmploymentPoint,
  SubmarketPipelineItem,
  ClassificationBreakdownItem,
  ConstructionDataQuality,
  ConstructionImportStatus,
} from '../types';

/**
 * Type-level smoke tests: verify interfaces compile and match expected shapes.
 * These use type assertions — if a field is missing or mistyped the test
 * will fail at compile time.
 */

describe('Construction Pipeline Types', () => {
  it('ProjectRecord matches expected shape', () => {
    const record: ProjectRecord = {
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
    };
    expect(record.id).toBe(1);
    expect(record.projectName).toBe('Mesa Gateway Apartments');
  });

  it('ProjectRecord allows null for nullable fields', () => {
    const record: ProjectRecord = {
      id: 2,
      projectName: null,
      projectAddress: null,
      city: null,
      submarketCluster: null,
      pipelineStatus: null,
      primaryClassification: null,
      numberOfUnits: null,
      numberOfStories: null,
      yearBuilt: null,
      developerName: null,
      ownerName: null,
      latitude: null,
      longitude: null,
      buildingSf: null,
      avgUnitSf: null,
      starRating: null,
      rentType: null,
      vacancyPct: null,
      estimatedDeliveryDate: null,
      constructionBegin: null,
      forSalePrice: null,
      sourceType: null,
    };
    expect(record.projectName).toBeNull();
  });

  it('ProjectsResponse matches expected shape', () => {
    const response: ProjectsResponse = {
      data: [],
      total: 0,
      page: 1,
      pageSize: 50,
      totalPages: 0,
    };
    expect(response.data).toEqual([]);
    expect(response.pageSize).toBe(50);
  });

  it('ConstructionFilters allows optional fields', () => {
    const minimal: ConstructionFilters = {};
    expect(minimal.search).toBeUndefined();

    const full: ConstructionFilters = {
      search: 'mesa',
      statuses: ['under_construction', 'delivered'],
      classifications: ['CONV_MR', 'BTR'],
      submarkets: ['East Valley'],
      cities: ['Mesa', 'Tempe'],
      minUnits: 50,
      maxUnits: 500,
      minYearBuilt: 2020,
      maxYearBuilt: 2026,
      rentType: 'Market',
      sortBy: 'number_of_units',
      sortDir: 'desc',
    };
    expect(full.statuses).toHaveLength(2);
    expect(full.sortDir).toBe('desc');
  });

  it('ConstructionFilterOptions matches expected shape', () => {
    const options: ConstructionFilterOptions = {
      submarkets: ['East Valley', 'Central Phoenix'],
      cities: ['Mesa', 'Phoenix', 'Tempe'],
      statuses: ['proposed', 'under_construction', 'delivered'],
      classifications: ['CONV_MR', 'BTR', 'LIHTC'],
      rentTypes: ['Market', 'Affordable'],
    };
    expect(options.submarkets).toHaveLength(2);
    expect(options.rentTypes).toContain('Market');
  });

  it('PipelineSummaryItem matches expected shape', () => {
    const item: PipelineSummaryItem = {
      status: 'under_construction',
      projectCount: 45,
      totalUnits: 12500,
    };
    expect(item.status).toBe('under_construction');
    expect(item.totalUnits).toBe(12500);
  });

  it('PipelineFunnelItem matches expected shape', () => {
    const item: PipelineFunnelItem = {
      status: 'proposed',
      projectCount: 20,
      totalUnits: 5000,
      cumulativeUnits: 5000,
    };
    expect(item.cumulativeUnits).toBe(5000);
  });

  it('PermitTrendPoint matches expected shape', () => {
    const point: PermitTrendPoint = {
      period: '2025-01',
      source: 'census_bps',
      seriesId: 'BLDG5O_UNITS',
      value: 1500,
    };
    expect(point.source).toBe('census_bps');
    expect(point.value).toBe(1500);
  });

  it('EmploymentPoint matches expected shape', () => {
    const point: EmploymentPoint = {
      period: '2025-06',
      seriesId: 'SMU04380602000000001',
      value: 145.3,
    };
    expect(point.seriesId).toBe('SMU04380602000000001');
  });

  it('SubmarketPipelineItem matches expected shape', () => {
    const item: SubmarketPipelineItem = {
      submarket: 'East Valley',
      totalProjects: 30,
      totalUnits: 8000,
      proposed: 2000,
      underConstruction: 4000,
      delivered: 2000,
    };
    expect(item.proposed + item.underConstruction + item.delivered).toBe(
      item.totalUnits,
    );
  });

  it('ClassificationBreakdownItem matches expected shape', () => {
    const item: ClassificationBreakdownItem = {
      classification: 'CONV_MR',
      projectCount: 60,
      totalUnits: 18000,
    };
    expect(item.classification).toBe('CONV_MR');
  });

  it('ConstructionDataQuality matches expected shape', () => {
    const report: ConstructionDataQuality = {
      totalProjects: 200,
      projectsBySource: { costar: 180, municipal: 20 },
      sourceLogs: [{ id: 1, source_name: 'costar' }],
      nullRates: { developer_name: 0.05, architect_name: 0.3 },
      permitDataCount: 500,
      employmentDataCount: 120,
    };
    expect(report.totalProjects).toBe(200);
    expect(report.projectsBySource['costar']).toBe(180);
  });

  it('ConstructionImportStatus matches expected shape', () => {
    const status: ConstructionImportStatus = {
      unimportedFiles: ['new_export.xlsx'],
      lastImportedFile: 'old_export.xlsx',
      lastImportDate: '2026-02-10',
      totalProjects: 180,
    };
    expect(status.unimportedFiles).toHaveLength(1);

    const emptyStatus: ConstructionImportStatus = {
      unimportedFiles: [],
      lastImportedFile: null,
      lastImportDate: null,
      totalProjects: 0,
    };
    expect(emptyStatus.lastImportedFile).toBeNull();
  });
});
