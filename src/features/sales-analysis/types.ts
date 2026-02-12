/** Core sale record (what the API returns, camelCase) */
export interface SaleRecord {
  id: number;
  propertyName: string | null;
  propertyAddress: string | null;
  propertyCity: string | null;
  submarketCluster: string | null;
  starRating: string | null;
  yearBuilt: number | null;
  numberOfUnits: number | null;
  avgUnitSf: number | null;
  saleDate: string | null;
  salePrice: number | null;
  pricePerUnit: number | null;
  buyerTrueCompany: string | null;
  sellerTrueCompany: string | null;
  latitude: number | null;
  longitude: number | null;
  nrsf: number | null;
  pricePerNrsf: number | null;
}

/** Paginated response */
export interface SalesResponse {
  data: SaleRecord[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

/** Filter state */
export interface SalesFilters {
  search?: string;
  submarkets?: string[];
  minUnits?: number;
  maxUnits?: number;
  minPrice?: number;
  maxPrice?: number;
  minPricePerUnit?: number;
  maxPricePerUnit?: number;
  minYearBuilt?: number;
  maxYearBuilt?: number;
  dateFrom?: string;
  dateTo?: string;
  sortBy?: string;
  sortDir?: 'asc' | 'desc';
}

/** Filter dropdown options from backend */
export interface FilterOptions {
  submarkets: string[];
}

/** Analytics response types */
export interface TimeSeriesDataPoint {
  period: string;
  count: number;
  totalVolume: number;
  avgPricePerUnit: number | null;
}

export interface SubmarketComparisonRow {
  submarket: string;
  year: number;
  avgPricePerUnit: number | null;
  salesCount: number;
  totalVolume: number;
}

export interface BuyerActivityRow {
  buyer: string;
  transactionCount: number;
  totalVolume: number;
  submarkets: string[];
  firstPurchase: string | null;
  lastPurchase: string | null;
}

export interface DistributionBucket {
  label: string;
  count: number;
  avgPricePerUnit: number | null;
}

export interface DataQualityReport {
  totalRecords: number;
  recordsByFile: Record<string, number>;
  nullRates: Record<string, number>;
  flaggedOutliers: Record<string, number>;
}

export interface ImportStatus {
  unimportedFiles: string[];
  lastImportedFile: string | null;
  lastImportDate: string | null;
}

export interface ReminderStatus {
  showReminder: boolean;
  lastImportedFileName: string | null;
  lastImportedFileDate: string | null;
}
