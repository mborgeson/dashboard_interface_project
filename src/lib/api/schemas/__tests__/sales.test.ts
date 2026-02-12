import { describe, it, expect } from 'vitest';
import {
  saleRecordSchema,
  salesResponseSchema,
  timeSeriesDataPointSchema,
  submarketComparisonRowSchema,
  buyerActivityRowSchema,
  distributionBucketSchema,
  dataQualityReportSchema,
  importStatusSchema,
  reminderStatusSchema,
  triggerImportResponseSchema,
} from '../sales';

// ============================================================================
// Factory helpers (snake_case to match raw API payloads)
// ============================================================================

function makeSaleRecord(overrides: Record<string, unknown> = {}) {
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

function makeSalesResponse(overrides: Record<string, unknown> = {}) {
  return {
    data: [makeSaleRecord()],
    total: 1,
    page: 1,
    page_size: 25,
    total_pages: 1,
    ...overrides,
  };
}

function makeTimeSeriesPoint(overrides: Record<string, unknown> = {}) {
  return {
    period: '2024-Q1',
    count: 15,
    total_volume: 350000000,
    avg_price_per_unit: 210000,
    ...overrides,
  };
}

function makeSubmarketRow(overrides: Record<string, unknown> = {}) {
  return {
    submarket: 'Tempe',
    year: 2024,
    avg_price_per_unit: 225000,
    sales_count: 42,
    total_volume: 500000000,
    ...overrides,
  };
}

function makeBuyerActivityRow(overrides: Record<string, unknown> = {}) {
  return {
    buyer: 'Acme Capital',
    transaction_count: 5,
    total_volume: 120000000,
    submarkets: ['Tempe', 'Scottsdale'],
    first_purchase: '2022-03-10',
    last_purchase: '2024-09-15',
    ...overrides,
  };
}

function makeDistributionBucket(overrides: Record<string, unknown> = {}) {
  return {
    label: '100-199 units',
    count: 34,
    avg_price_per_unit: 205000,
    ...overrides,
  };
}

function makeDataQualityReport(overrides: Record<string, unknown> = {}) {
  return {
    total_records: 500,
    records_by_file: { 'file_2024_q1.csv': 200, 'file_2024_q2.csv': 300 },
    null_rates: { sale_price: 0.02, price_per_unit: 0.05 },
    flagged_outliers: { extreme_price: 3, zero_units: 1 },
    ...overrides,
  };
}

function makeImportStatus(overrides: Record<string, unknown> = {}) {
  return {
    unimported_files: ['new_data_2024_q3.csv'],
    last_imported_file: 'file_2024_q2.csv',
    last_import_date: '2024-07-01',
    ...overrides,
  };
}

function makeReminderStatus(overrides: Record<string, unknown> = {}) {
  return {
    show_reminder: true,
    last_imported_file_name: 'file_2024_q2.csv',
    last_imported_file_date: '2024-07-01',
    ...overrides,
  };
}

// ============================================================================
// saleRecordSchema
// ============================================================================

describe('saleRecordSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = saleRecordSchema.parse(makeSaleRecord());

    expect(result.id).toBe(1);
    expect(result.propertyName).toBe('Test Property');
    expect(result.propertyAddress).toBe('123 Main St');
    expect(result.propertyCity).toBe('Phoenix');
    expect(result.submarketCluster).toBe('Central Phoenix');
    expect(result.sellerTrueCompany).toBe('ABC Sellers LLC');
    expect(result.starRating).toBe('4 Star');
    expect(result.yearBuilt).toBe(2005);
    expect(result.numberOfUnits).toBe(200);
    expect(result.avgUnitSf).toBe(850);
    expect(result.saleDate).toBe('2024-06-15');
    expect(result.salePrice).toBe(45000000);
    expect(result.pricePerUnit).toBe(225000);
    expect(result.buyerTrueCompany).toBe('XYZ Buyers Inc');
    expect(result.latitude).toBe(33.4484);
    expect(result.longitude).toBe(-112.074);
    expect(result.nrsf).toBe(170000);
    expect(result.pricePerNrsf).toBe(264.71);
  });

  it('handles all nullable fields as null', () => {
    const result = saleRecordSchema.parse(
      makeSaleRecord({
        property_name: null,
        property_address: null,
        property_city: null,
        submarket_cluster: null,
        seller_true_company: null,
        star_rating: null,
        year_built: null,
        number_of_units: null,
        avg_unit_sf: null,
        sale_date: null,
        sale_price: null,
        price_per_unit: null,
        buyer_true_company: null,
        latitude: null,
        longitude: null,
        nrsf: null,
        price_per_nrsf: null,
      }),
    );

    expect(result.propertyName).toBeNull();
    expect(result.propertyAddress).toBeNull();
    expect(result.propertyCity).toBeNull();
    expect(result.submarketCluster).toBeNull();
    expect(result.sellerTrueCompany).toBeNull();
    expect(result.starRating).toBeNull();
    expect(result.yearBuilt).toBeNull();
    expect(result.numberOfUnits).toBeNull();
    expect(result.avgUnitSf).toBeNull();
    expect(result.saleDate).toBeNull();
    expect(result.salePrice).toBeNull();
    expect(result.pricePerUnit).toBeNull();
    expect(result.buyerTrueCompany).toBeNull();
    expect(result.latitude).toBeNull();
    expect(result.longitude).toBeNull();
    expect(result.nrsf).toBeNull();
    expect(result.pricePerNrsf).toBeNull();
  });

  it('throws on missing required id field', () => {
    const raw = makeSaleRecord();
    delete (raw as Record<string, unknown>).id;
    expect(() => saleRecordSchema.parse(raw)).toThrow();
  });

  it('throws on wrong type for id', () => {
    expect(() =>
      saleRecordSchema.parse(makeSaleRecord({ id: 'not-a-number' })),
    ).toThrow();
  });

  it('throws on wrong type for numeric nullable field', () => {
    expect(() =>
      saleRecordSchema.parse(makeSaleRecord({ sale_price: 'bad' })),
    ).toThrow();
  });
});

// ============================================================================
// salesResponseSchema
// ============================================================================

describe('salesResponseSchema', () => {
  it('transforms paginated response with snake_case to camelCase', () => {
    const result = salesResponseSchema.parse(makeSalesResponse());

    expect(result.data).toHaveLength(1);
    expect(result.total).toBe(1);
    expect(result.page).toBe(1);
    expect(result.pageSize).toBe(25);
    expect(result.totalPages).toBe(1);
    // Nested sale record is also transformed
    expect(result.data[0].propertyName).toBe('Test Property');
  });

  it('parses empty data array', () => {
    const result = salesResponseSchema.parse(
      makeSalesResponse({ data: [], total: 0, total_pages: 0 }),
    );
    expect(result.data).toHaveLength(0);
    expect(result.total).toBe(0);
  });

  it('parses response with multiple records', () => {
    const records = [
      makeSaleRecord({ id: 1 }),
      makeSaleRecord({ id: 2, property_name: 'Second Property' }),
    ];
    const result = salesResponseSchema.parse(
      makeSalesResponse({ data: records, total: 2 }),
    );
    expect(result.data).toHaveLength(2);
    expect(result.data[1].propertyName).toBe('Second Property');
  });

  it('throws on missing page_size', () => {
    const raw = makeSalesResponse();
    delete (raw as Record<string, unknown>).page_size;
    expect(() => salesResponseSchema.parse(raw)).toThrow();
  });
});

// ============================================================================
// timeSeriesDataPointSchema
// ============================================================================

describe('timeSeriesDataPointSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = timeSeriesDataPointSchema.parse(makeTimeSeriesPoint());

    expect(result.period).toBe('2024-Q1');
    expect(result.count).toBe(15);
    expect(result.totalVolume).toBe(350000000);
    expect(result.avgPricePerUnit).toBe(210000);
  });

  it('handles nullable avg_price_per_unit', () => {
    const result = timeSeriesDataPointSchema.parse(
      makeTimeSeriesPoint({ avg_price_per_unit: null }),
    );
    expect(result.avgPricePerUnit).toBeNull();
  });

  it('throws on missing period', () => {
    const raw = makeTimeSeriesPoint();
    delete (raw as Record<string, unknown>).period;
    expect(() => timeSeriesDataPointSchema.parse(raw)).toThrow();
  });

  it('throws on wrong type for count', () => {
    expect(() =>
      timeSeriesDataPointSchema.parse(makeTimeSeriesPoint({ count: 'five' })),
    ).toThrow();
  });
});

// ============================================================================
// submarketComparisonRowSchema
// ============================================================================

describe('submarketComparisonRowSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = submarketComparisonRowSchema.parse(makeSubmarketRow());

    expect(result.submarket).toBe('Tempe');
    expect(result.year).toBe(2024);
    expect(result.avgPricePerUnit).toBe(225000);
    expect(result.salesCount).toBe(42);
    expect(result.totalVolume).toBe(500000000);
  });

  it('handles nullable avg_price_per_unit', () => {
    const result = submarketComparisonRowSchema.parse(
      makeSubmarketRow({ avg_price_per_unit: null }),
    );
    expect(result.avgPricePerUnit).toBeNull();
  });

  it('throws on missing submarket', () => {
    const raw = makeSubmarketRow();
    delete (raw as Record<string, unknown>).submarket;
    expect(() => submarketComparisonRowSchema.parse(raw)).toThrow();
  });
});

// ============================================================================
// buyerActivityRowSchema
// ============================================================================

describe('buyerActivityRowSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = buyerActivityRowSchema.parse(makeBuyerActivityRow());

    expect(result.buyer).toBe('Acme Capital');
    expect(result.transactionCount).toBe(5);
    expect(result.totalVolume).toBe(120000000);
    expect(result.submarkets).toEqual(['Tempe', 'Scottsdale']);
    expect(result.firstPurchase).toBe('2022-03-10');
    expect(result.lastPurchase).toBe('2024-09-15');
  });

  it('handles nullable first_purchase and last_purchase', () => {
    const result = buyerActivityRowSchema.parse(
      makeBuyerActivityRow({ first_purchase: null, last_purchase: null }),
    );
    expect(result.firstPurchase).toBeNull();
    expect(result.lastPurchase).toBeNull();
  });

  it('handles empty submarkets array', () => {
    const result = buyerActivityRowSchema.parse(
      makeBuyerActivityRow({ submarkets: [] }),
    );
    expect(result.submarkets).toEqual([]);
  });

  it('throws on missing buyer', () => {
    const raw = makeBuyerActivityRow();
    delete (raw as Record<string, unknown>).buyer;
    expect(() => buyerActivityRowSchema.parse(raw)).toThrow();
  });
});

// ============================================================================
// distributionBucketSchema
// ============================================================================

describe('distributionBucketSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = distributionBucketSchema.parse(makeDistributionBucket());

    expect(result.label).toBe('100-199 units');
    expect(result.count).toBe(34);
    expect(result.avgPricePerUnit).toBe(205000);
  });

  it('handles nullable avg price', () => {
    const result = distributionBucketSchema.parse(
      makeDistributionBucket({
        avg_price_per_unit: null,
      }),
    );
    expect(result.avgPricePerUnit).toBeNull();
  });

  it('throws on missing label', () => {
    const raw = makeDistributionBucket();
    delete (raw as Record<string, unknown>).label;
    expect(() => distributionBucketSchema.parse(raw)).toThrow();
  });

  it('throws on wrong type for count', () => {
    expect(() =>
      distributionBucketSchema.parse(
        makeDistributionBucket({ count: 'many' }),
      ),
    ).toThrow();
  });
});

// ============================================================================
// dataQualityReportSchema
// ============================================================================

describe('dataQualityReportSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = dataQualityReportSchema.parse(makeDataQualityReport());

    expect(result.totalRecords).toBe(500);
    expect(result.recordsByFile).toEqual({
      'file_2024_q1.csv': 200,
      'file_2024_q2.csv': 300,
    });
    expect(result.nullRates).toEqual({
      sale_price: 0.02,
      price_per_unit: 0.05,
    });
    expect(result.flaggedOutliers).toEqual({
      extreme_price: 3,
      zero_units: 1,
    });
  });

  it('handles empty dicts', () => {
    const result = dataQualityReportSchema.parse(
      makeDataQualityReport({
        records_by_file: {},
        null_rates: {},
        flagged_outliers: {},
      }),
    );
    expect(Object.keys(result.recordsByFile)).toHaveLength(0);
    expect(Object.keys(result.nullRates)).toHaveLength(0);
    expect(Object.keys(result.flaggedOutliers)).toHaveLength(0);
  });

  it('throws on missing total_records', () => {
    const raw = makeDataQualityReport();
    delete (raw as Record<string, unknown>).total_records;
    expect(() => dataQualityReportSchema.parse(raw)).toThrow();
  });

  it('throws on wrong type for records_by_file values', () => {
    expect(() =>
      dataQualityReportSchema.parse(
        makeDataQualityReport({
          records_by_file: { 'file.csv': 'not-a-number' },
        }),
      ),
    ).toThrow();
  });
});

// ============================================================================
// importStatusSchema
// ============================================================================

describe('importStatusSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = importStatusSchema.parse(makeImportStatus());

    expect(result.unimportedFiles).toEqual(['new_data_2024_q3.csv']);
    expect(result.lastImportedFile).toBe('file_2024_q2.csv');
    expect(result.lastImportDate).toBe('2024-07-01');
  });

  it('handles nullable last_imported_file and last_import_date', () => {
    const result = importStatusSchema.parse(
      makeImportStatus({
        last_imported_file: null,
        last_import_date: null,
      }),
    );
    expect(result.lastImportedFile).toBeNull();
    expect(result.lastImportDate).toBeNull();
  });

  it('handles empty unimported_files array', () => {
    const result = importStatusSchema.parse(
      makeImportStatus({ unimported_files: [] }),
    );
    expect(result.unimportedFiles).toEqual([]);
  });

  it('throws on missing unimported_files', () => {
    const raw = makeImportStatus();
    delete (raw as Record<string, unknown>).unimported_files;
    expect(() => importStatusSchema.parse(raw)).toThrow();
  });
});

// ============================================================================
// reminderStatusSchema
// ============================================================================

describe('reminderStatusSchema', () => {
  it('transforms snake_case to camelCase', () => {
    const result = reminderStatusSchema.parse(makeReminderStatus());

    expect(result.showReminder).toBe(true);
    expect(result.lastImportedFileName).toBe('file_2024_q2.csv');
    expect(result.lastImportedFileDate).toBe('2024-07-01');
  });

  it('handles nullable file name and date', () => {
    const result = reminderStatusSchema.parse(
      makeReminderStatus({
        last_imported_file_name: null,
        last_imported_file_date: null,
      }),
    );
    expect(result.lastImportedFileName).toBeNull();
    expect(result.lastImportedFileDate).toBeNull();
  });

  it('parses show_reminder as false', () => {
    const result = reminderStatusSchema.parse(
      makeReminderStatus({ show_reminder: false }),
    );
    expect(result.showReminder).toBe(false);
  });

  it('throws on missing show_reminder', () => {
    const raw = makeReminderStatus();
    delete (raw as Record<string, unknown>).show_reminder;
    expect(() => reminderStatusSchema.parse(raw)).toThrow();
  });
});

// ============================================================================
// triggerImportResponseSchema
// ============================================================================

describe('triggerImportResponseSchema', () => {
  it('parses a valid response', () => {
    const result = triggerImportResponseSchema.parse({
      success: true,
      message: 'Imported 150 records from 1 file',
    });
    expect(result.success).toBe(true);
    expect(result.message).toBe('Imported 150 records from 1 file');
  });

  it('parses a failure response', () => {
    const result = triggerImportResponseSchema.parse({
      success: false,
      message: 'No files to import',
    });
    expect(result.success).toBe(false);
  });

  it('throws on missing success', () => {
    expect(() =>
      triggerImportResponseSchema.parse({ message: 'hello' }),
    ).toThrow();
  });

  it('throws on missing message', () => {
    expect(() =>
      triggerImportResponseSchema.parse({ success: true }),
    ).toThrow();
  });
});
