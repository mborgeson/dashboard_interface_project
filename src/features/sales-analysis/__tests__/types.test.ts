import { describe, it, expect } from 'vitest';
import type {
  SaleRecord,
  SalesResponse,
  SalesFilters,
  TimeSeriesDataPoint,
  SubmarketComparisonRow,
  BuyerActivityRow,
  DistributionBucket,
  DataQualityReport,
  ImportStatus,
  ReminderStatus,
} from '../types';

/**
 * Type-level smoke tests: verify interfaces compile and match expected shapes.
 * These use type assertions — if a field is missing or mistyped the test
 * will fail at compile time.
 */

describe('Sales Analysis Types', () => {
  it('SaleRecord matches expected shape', () => {
    const record: SaleRecord = {
      id: 1,
      propertyName: 'Test',
      propertyAddress: '123 Main',
      propertyCity: 'Phoenix',
      submarketCluster: 'Central',
      starRating: '4 Star',
      yearBuilt: 2005,
      numberOfUnits: 200,
      avgUnitSf: 850,
      saleDate: '2024-01-01',
      salePrice: 45000000,
      pricePerUnit: 225000,
      buyerTrueCompany: 'Buyer LLC',
      sellerTrueCompany: 'Seller LLC',
      latitude: 33.4,
      longitude: -112.0,
      nrsf: 170000,
      pricePerNrsf: 264.71,
    };
    expect(record.id).toBe(1);
    expect(record.propertyName).toBe('Test');
  });

  it('SaleRecord allows null for nullable fields', () => {
    const record: SaleRecord = {
      id: 2,
      propertyName: null,
      propertyAddress: null,
      propertyCity: null,
      submarketCluster: null,
      starRating: null,
      yearBuilt: null,
      numberOfUnits: null,
      avgUnitSf: null,
      saleDate: null,
      salePrice: null,
      pricePerUnit: null,
      buyerTrueCompany: null,
      sellerTrueCompany: null,
      latitude: null,
      longitude: null,
      nrsf: null,
      pricePerNrsf: null,
    };
    expect(record.propertyName).toBeNull();
  });

  it('SalesResponse matches expected shape', () => {
    const response: SalesResponse = {
      data: [],
      total: 0,
      page: 1,
      pageSize: 25,
      totalPages: 0,
    };
    expect(response.data).toEqual([]);
    expect(response.pageSize).toBe(25);
  });

  it('SalesFilters allows optional fields', () => {
    const minimal: SalesFilters = {};
    expect(minimal.search).toBeUndefined();

    const full: SalesFilters = {
      search: 'phoenix',
      submarkets: ['Tempe', 'Scottsdale'],
      starRatings: ['4 Star'],
      minUnits: 100,
      maxUnits: 500,
      minPrice: 10000000,
      maxPrice: 100000000,
      dateFrom: '2023-01-01',
      dateTo: '2024-12-31',
      sortBy: 'sale_price',
      sortDir: 'desc',
    };
    expect(full.submarkets).toHaveLength(2);
    expect(full.sortDir).toBe('desc');
  });

  it('TimeSeriesDataPoint matches expected shape', () => {
    const point: TimeSeriesDataPoint = {
      period: '2024-Q1',
      count: 15,
      totalVolume: 350000000,
      medianPricePerUnit: 210000,
    };
    expect(point.period).toBe('2024-Q1');
    expect(point.medianPricePerUnit).toBe(210000);
  });

  it('SubmarketComparisonRow matches expected shape', () => {
    const row: SubmarketComparisonRow = {
      submarket: 'Tempe',
      year: 2024,
      medianPricePerUnit: null,
      salesCount: 42,
      totalVolume: 500000000,
    };
    expect(row.medianPricePerUnit).toBeNull();
  });

  it('BuyerActivityRow matches expected shape', () => {
    const row: BuyerActivityRow = {
      buyer: 'Acme Capital',
      transactionCount: 5,
      totalVolume: 120000000,
      submarkets: ['Tempe'],
      firstPurchase: '2022-03-10',
      lastPurchase: null,
    };
    expect(row.lastPurchase).toBeNull();
    expect(row.submarkets).toHaveLength(1);
  });

  it('DistributionBucket matches expected shape', () => {
    const bucket: DistributionBucket = {
      label: '100-199',
      count: 34,
      medianPricePerUnit: null,
      avgPricePerUnit: 205000,
    };
    expect(bucket.medianPricePerUnit).toBeNull();
    expect(bucket.avgPricePerUnit).toBe(205000);
  });

  it('DataQualityReport matches expected shape', () => {
    const report: DataQualityReport = {
      totalRecords: 500,
      recordsByFile: { 'file.csv': 500 },
      nullRates: { sale_price: 0.02 },
      flaggedOutliers: { extreme_price: 3 },
    };
    expect(report.totalRecords).toBe(500);
    expect(report.recordsByFile['file.csv']).toBe(500);
  });

  it('ImportStatus matches expected shape', () => {
    const status: ImportStatus = {
      unimportedFiles: ['new.csv'],
      lastImportedFile: 'old.csv',
      lastImportDate: '2024-07-01',
    };
    expect(status.unimportedFiles).toHaveLength(1);

    const emptyStatus: ImportStatus = {
      unimportedFiles: [],
      lastImportedFile: null,
      lastImportDate: null,
    };
    expect(emptyStatus.lastImportedFile).toBeNull();
  });

  it('ReminderStatus matches expected shape', () => {
    const status: ReminderStatus = {
      showReminder: true,
      lastImportedFileName: 'file.csv',
      lastImportedFileDate: '2024-07-01',
    };
    expect(status.showReminder).toBe(true);

    const noReminder: ReminderStatus = {
      showReminder: false,
      lastImportedFileName: null,
      lastImportedFileDate: null,
    };
    expect(noReminder.showReminder).toBe(false);
  });
});
