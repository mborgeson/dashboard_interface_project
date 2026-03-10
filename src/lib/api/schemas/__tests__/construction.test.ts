import { describe, it, expect } from 'vitest';
import {
  projectRecordSchema,
  projectsResponseSchema,
  constructionFilterOptionsSchema,
  pipelineSummaryItemSchema,
  pipelineFunnelItemSchema,
  permitTrendPointSchema,
  employmentPointSchema,
  submarketPipelineItemSchema,
  classificationBreakdownItemSchema,
  deliveryTimelineItemSchema,
  constructionDataQualitySchema,
  constructionImportStatusSchema,
  triggerConstructionImportResponseSchema,
} from '../construction';

// ---------- Helpers ----------

function makeProjectRecord(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    project_name: 'Skyline Apartments',
    project_address: '1234 E Main St',
    city: 'Tempe',
    submarket_cluster: 'Tempe/ASU',
    pipeline_status: 'Under Construction',
    primary_classification: 'Multifamily',
    number_of_units: 250,
    number_of_stories: 4,
    year_built: 2024,
    developer_name: 'ABC Dev',
    owner_name: 'XYZ Holdings',
    latitude: 33.4255,
    longitude: -111.94,
    building_sf: 225000,
    avg_unit_sf: 900,
    star_rating: '4',
    rent_type: 'Market',
    vacancy_pct: 0.05,
    estimated_delivery_date: '2025-06-01',
    construction_begin: '2023-09-15',
    for_sale_price: 75000000,
    source_type: 'CoStar',
    ...overrides,
  };
}

// ---------- projectRecordSchema ----------

describe('projectRecordSchema', () => {
  it('parses valid data and transforms snake_case to camelCase', () => {
    const result = projectRecordSchema.parse(makeProjectRecord());

    expect(result.id).toBe(1);
    expect(result.projectName).toBe('Skyline Apartments');
    expect(result.projectAddress).toBe('1234 E Main St');
    expect(result.city).toBe('Tempe');
    expect(result.submarketCluster).toBe('Tempe/ASU');
    expect(result.pipelineStatus).toBe('Under Construction');
    expect(result.primaryClassification).toBe('Multifamily');
    expect(result.numberOfUnits).toBe(250);
    expect(result.numberOfStories).toBe(4);
    expect(result.yearBuilt).toBe(2024);
    expect(result.developerName).toBe('ABC Dev');
    expect(result.ownerName).toBe('XYZ Holdings');
    expect(result.latitude).toBe(33.4255);
    expect(result.longitude).toBe(-111.94);
    expect(result.buildingSf).toBe(225000);
    expect(result.avgUnitSf).toBe(900);
    expect(result.starRating).toBe('4');
    expect(result.rentType).toBe('Market');
    expect(result.vacancyPct).toBe(0.05);
    expect(result.estimatedDeliveryDate).toBe('2025-06-01');
    expect(result.constructionBegin).toBe('2023-09-15');
    expect(result.forSalePrice).toBe(75000000);
    expect(result.sourceType).toBe('CoStar');
  });

  it('handles all nullable fields as null', () => {
    const allNulls = makeProjectRecord({
      project_name: null,
      project_address: null,
      city: null,
      submarket_cluster: null,
      pipeline_status: null,
      primary_classification: null,
      number_of_units: null,
      number_of_stories: null,
      year_built: null,
      developer_name: null,
      owner_name: null,
      latitude: null,
      longitude: null,
      building_sf: null,
      avg_unit_sf: null,
      star_rating: null,
      rent_type: null,
      vacancy_pct: null,
      estimated_delivery_date: null,
      construction_begin: null,
      for_sale_price: null,
      source_type: null,
    });
    const result = projectRecordSchema.parse(allNulls);

    expect(result.projectName).toBeNull();
    expect(result.city).toBeNull();
    expect(result.numberOfUnits).toBeNull();
    expect(result.latitude).toBeNull();
    expect(result.forSalePrice).toBeNull();
    expect(result.sourceType).toBeNull();
  });

  it('throws when id is missing', () => {
    const raw = makeProjectRecord();
    delete (raw as Record<string, unknown>).id;
    expect(() => projectRecordSchema.parse(raw)).toThrow();
  });

  it('throws when id is a string instead of number', () => {
    expect(() =>
      projectRecordSchema.parse(makeProjectRecord({ id: 'abc' }))
    ).toThrow();
  });

  it('throws when number_of_units is a string instead of number or null', () => {
    expect(() =>
      projectRecordSchema.parse(makeProjectRecord({ number_of_units: 'many' }))
    ).toThrow();
  });
});

// ---------- projectsResponseSchema ----------

describe('projectsResponseSchema', () => {
  it('parses paginated response and transforms keys', () => {
    const raw = {
      data: [makeProjectRecord()],
      total: 1,
      page: 1,
      page_size: 25,
      total_pages: 1,
    };
    const result = projectsResponseSchema.parse(raw);

    expect(result.data).toHaveLength(1);
    expect(result.total).toBe(1);
    expect(result.page).toBe(1);
    expect(result.pageSize).toBe(25);
    expect(result.totalPages).toBe(1);
    // Nested record should also be transformed
    expect(result.data[0].projectName).toBe('Skyline Apartments');
  });

  it('parses empty data array', () => {
    const raw = {
      data: [],
      total: 0,
      page: 1,
      page_size: 25,
      total_pages: 0,
    };
    const result = projectsResponseSchema.parse(raw);
    expect(result.data).toHaveLength(0);
    expect(result.total).toBe(0);
  });

  it('throws when total is missing', () => {
    const raw = {
      data: [],
      page: 1,
      page_size: 25,
      total_pages: 0,
    };
    expect(() => projectsResponseSchema.parse(raw)).toThrow();
  });

  it('throws when page_size is missing', () => {
    const raw = {
      data: [],
      total: 0,
      page: 1,
      total_pages: 0,
    };
    expect(() => projectsResponseSchema.parse(raw)).toThrow();
  });
});

// ---------- constructionFilterOptionsSchema ----------

describe('constructionFilterOptionsSchema', () => {
  it('parses valid filter options and transforms rent_types', () => {
    const raw = {
      submarkets: ['Tempe/ASU', 'Scottsdale'],
      cities: ['Tempe', 'Phoenix'],
      statuses: ['Under Construction', 'Proposed'],
      classifications: ['Multifamily', 'Mixed Use'],
      rent_types: ['Market', 'Affordable'],
    };
    const result = constructionFilterOptionsSchema.parse(raw);

    expect(result.submarkets).toEqual(['Tempe/ASU', 'Scottsdale']);
    expect(result.cities).toEqual(['Tempe', 'Phoenix']);
    expect(result.statuses).toEqual(['Under Construction', 'Proposed']);
    expect(result.classifications).toEqual(['Multifamily', 'Mixed Use']);
    expect(result.rentTypes).toEqual(['Market', 'Affordable']);
  });

  it('parses empty arrays', () => {
    const raw = {
      submarkets: [],
      cities: [],
      statuses: [],
      classifications: [],
      rent_types: [],
    };
    const result = constructionFilterOptionsSchema.parse(raw);
    expect(result.rentTypes).toEqual([]);
  });

  it('throws when rent_types is missing', () => {
    const raw = {
      submarkets: [],
      cities: [],
      statuses: [],
      classifications: [],
    };
    expect(() => constructionFilterOptionsSchema.parse(raw)).toThrow();
  });
});

// ---------- pipelineSummaryItemSchema ----------

describe('pipelineSummaryItemSchema', () => {
  it('parses valid data and transforms keys', () => {
    const result = pipelineSummaryItemSchema.parse({
      status: 'Under Construction',
      project_count: 15,
      total_units: 3200,
    });
    expect(result.status).toBe('Under Construction');
    expect(result.projectCount).toBe(15);
    expect(result.totalUnits).toBe(3200);
  });

  it('throws when project_count is missing', () => {
    expect(() =>
      pipelineSummaryItemSchema.parse({
        status: 'Proposed',
        total_units: 500,
      })
    ).toThrow();
  });
});

// ---------- pipelineFunnelItemSchema ----------

describe('pipelineFunnelItemSchema', () => {
  it('parses valid data and transforms keys', () => {
    const result = pipelineFunnelItemSchema.parse({
      status: 'Delivered',
      project_count: 8,
      total_units: 1800,
      cumulative_units: 5000,
    });
    expect(result.status).toBe('Delivered');
    expect(result.projectCount).toBe(8);
    expect(result.totalUnits).toBe(1800);
    expect(result.cumulativeUnits).toBe(5000);
  });

  it('throws when cumulative_units is missing', () => {
    expect(() =>
      pipelineFunnelItemSchema.parse({
        status: 'Delivered',
        project_count: 8,
        total_units: 1800,
      })
    ).toThrow();
  });
});

// ---------- permitTrendPointSchema ----------

describe('permitTrendPointSchema', () => {
  it('parses valid data and transforms series_id', () => {
    const result = permitTrendPointSchema.parse({
      period: '2024-Q1',
      source: 'Census',
      series_id: 'PERMIT-AZ-001',
      value: 1250,
    });
    expect(result.period).toBe('2024-Q1');
    expect(result.source).toBe('Census');
    expect(result.seriesId).toBe('PERMIT-AZ-001');
    expect(result.value).toBe(1250);
  });

  it('throws when value is a string', () => {
    expect(() =>
      permitTrendPointSchema.parse({
        period: '2024-Q1',
        source: 'Census',
        series_id: 'X',
        value: 'not-a-number',
      })
    ).toThrow();
  });
});

// ---------- employmentPointSchema ----------

describe('employmentPointSchema', () => {
  it('parses valid data and transforms series_id', () => {
    const result = employmentPointSchema.parse({
      period: '2024-01',
      series_id: 'EMP-AZ-002',
      value: 2500000,
    });
    expect(result.period).toBe('2024-01');
    expect(result.seriesId).toBe('EMP-AZ-002');
    expect(result.value).toBe(2500000);
  });

  it('throws when period is missing', () => {
    expect(() =>
      employmentPointSchema.parse({
        series_id: 'EMP-AZ-002',
        value: 2500000,
      })
    ).toThrow();
  });
});

// ---------- submarketPipelineItemSchema ----------

describe('submarketPipelineItemSchema', () => {
  it('parses valid data and transforms keys', () => {
    const result = submarketPipelineItemSchema.parse({
      submarket: 'Tempe/ASU',
      total_projects: 12,
      total_units: 3000,
      proposed: 4,
      under_construction: 5,
      delivered: 3,
    });
    expect(result.submarket).toBe('Tempe/ASU');
    expect(result.totalProjects).toBe(12);
    expect(result.totalUnits).toBe(3000);
    expect(result.proposed).toBe(4);
    expect(result.underConstruction).toBe(5);
    expect(result.delivered).toBe(3);
  });

  it('throws when under_construction is missing', () => {
    expect(() =>
      submarketPipelineItemSchema.parse({
        submarket: 'Tempe/ASU',
        total_projects: 12,
        total_units: 3000,
        proposed: 4,
        delivered: 3,
      })
    ).toThrow();
  });
});

// ---------- classificationBreakdownItemSchema ----------

describe('classificationBreakdownItemSchema', () => {
  it('parses valid data and transforms keys', () => {
    const result = classificationBreakdownItemSchema.parse({
      classification: 'Multifamily',
      project_count: 20,
      total_units: 5000,
    });
    expect(result.classification).toBe('Multifamily');
    expect(result.projectCount).toBe(20);
    expect(result.totalUnits).toBe(5000);
  });

  it('throws on missing classification', () => {
    expect(() =>
      classificationBreakdownItemSchema.parse({
        project_count: 20,
        total_units: 5000,
      })
    ).toThrow();
  });
});

// ---------- deliveryTimelineItemSchema ----------

describe('deliveryTimelineItemSchema', () => {
  it('parses valid data and transforms keys', () => {
    const result = deliveryTimelineItemSchema.parse({
      quarter: '2025-Q2',
      total_units: 800,
      project_count: 3,
    });
    expect(result.quarter).toBe('2025-Q2');
    expect(result.totalUnits).toBe(800);
    expect(result.projectCount).toBe(3);
  });

  it('throws on missing quarter', () => {
    expect(() =>
      deliveryTimelineItemSchema.parse({
        total_units: 800,
        project_count: 3,
      })
    ).toThrow();
  });
});

// ---------- constructionDataQualitySchema ----------

describe('constructionDataQualitySchema', () => {
  it('parses valid data and transforms keys', () => {
    const raw = {
      total_projects: 50,
      projects_by_source: { CoStar: 30, Manual: 20 },
      source_logs: [{ file: 'import_2024.csv', rows: 30 }],
      null_rates: { city: 0.02, developer_name: 0.1 },
      permit_data_count: 120,
      employment_data_count: 60,
    };
    const result = constructionDataQualitySchema.parse(raw);

    expect(result.totalProjects).toBe(50);
    expect(result.projectsBySource).toEqual({ CoStar: 30, Manual: 20 });
    expect(result.sourceLogs).toHaveLength(1);
    expect(result.nullRates).toEqual({ city: 0.02, developer_name: 0.1 });
    expect(result.permitDataCount).toBe(120);
    expect(result.employmentDataCount).toBe(60);
  });

  it('parses with empty collections', () => {
    const raw = {
      total_projects: 0,
      projects_by_source: {},
      source_logs: [],
      null_rates: {},
      permit_data_count: 0,
      employment_data_count: 0,
    };
    const result = constructionDataQualitySchema.parse(raw);
    expect(result.totalProjects).toBe(0);
    expect(result.sourceLogs).toEqual([]);
  });

  it('throws when permit_data_count is missing', () => {
    expect(() =>
      constructionDataQualitySchema.parse({
        total_projects: 50,
        projects_by_source: {},
        source_logs: [],
        null_rates: {},
        employment_data_count: 60,
      })
    ).toThrow();
  });
});

// ---------- constructionImportStatusSchema ----------

describe('constructionImportStatusSchema', () => {
  it('parses valid data and transforms keys', () => {
    const raw = {
      unimported_files: ['file1.csv', 'file2.csv'],
      last_imported_file: 'import_2024.csv',
      last_import_date: '2024-12-01T10:00:00Z',
      total_projects: 50,
    };
    const result = constructionImportStatusSchema.parse(raw);

    expect(result.unimportedFiles).toEqual(['file1.csv', 'file2.csv']);
    expect(result.lastImportedFile).toBe('import_2024.csv');
    expect(result.lastImportDate).toBe('2024-12-01T10:00:00Z');
    expect(result.totalProjects).toBe(50);
  });

  it('handles nullable fields as null', () => {
    const raw = {
      unimported_files: [],
      last_imported_file: null,
      last_import_date: null,
      total_projects: 0,
    };
    const result = constructionImportStatusSchema.parse(raw);

    expect(result.lastImportedFile).toBeNull();
    expect(result.lastImportDate).toBeNull();
  });

  it('throws when unimported_files is missing', () => {
    expect(() =>
      constructionImportStatusSchema.parse({
        last_imported_file: null,
        last_import_date: null,
        total_projects: 0,
      })
    ).toThrow();
  });
});

// ---------- triggerConstructionImportResponseSchema ----------

describe('triggerConstructionImportResponseSchema', () => {
  it('parses a success response', () => {
    const result = triggerConstructionImportResponseSchema.parse({
      success: true,
      message: 'Import completed successfully',
    });
    expect(result.success).toBe(true);
    expect(result.message).toBe('Import completed successfully');
  });

  it('parses a failure response', () => {
    const result = triggerConstructionImportResponseSchema.parse({
      success: false,
      message: 'No new files to import',
    });
    expect(result.success).toBe(false);
  });

  it('throws when success is missing', () => {
    expect(() =>
      triggerConstructionImportResponseSchema.parse({
        message: 'Import completed',
      })
    ).toThrow();
  });

  it('throws when message is missing', () => {
    expect(() =>
      triggerConstructionImportResponseSchema.parse({
        success: true,
      })
    ).toThrow();
  });
});
