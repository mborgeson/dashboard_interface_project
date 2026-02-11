/** Core project record (camelCase, from API + Zod transform) */
export interface ProjectRecord {
  id: number;
  projectName: string | null;
  projectAddress: string | null;
  city: string | null;
  submarketCluster: string | null;
  pipelineStatus: string | null;
  primaryClassification: string | null;
  numberOfUnits: number | null;
  numberOfStories: number | null;
  yearBuilt: number | null;
  developerName: string | null;
  ownerName: string | null;
  latitude: number | null;
  longitude: number | null;
  buildingSf: number | null;
  avgUnitSf: number | null;
  starRating: string | null;
  rentType: string | null;
  vacancyPct: number | null;
  estimatedDeliveryDate: string | null;
  constructionBegin: string | null;
  forSalePrice: number | null;
  sourceType: string | null;
}

/** Paginated response */
export interface ProjectsResponse {
  data: ProjectRecord[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

/** Filter state */
export interface ConstructionFilters {
  search?: string;
  statuses?: string[];
  classifications?: string[];
  submarkets?: string[];
  cities?: string[];
  minUnits?: number;
  maxUnits?: number;
  minYearBuilt?: number;
  maxYearBuilt?: number;
  rentType?: string;
  sortBy?: string;
  sortDir?: 'asc' | 'desc';
}

/** Filter dropdown options from backend */
export interface ConstructionFilterOptions {
  submarkets: string[];
  cities: string[];
  statuses: string[];
  classifications: string[];
  rentTypes: string[];
}

/** Analytics types */
export interface PipelineSummaryItem {
  status: string;
  projectCount: number;
  totalUnits: number;
}

export interface PipelineFunnelItem {
  status: string;
  projectCount: number;
  totalUnits: number;
  cumulativeUnits: number;
}

export interface PermitTrendPoint {
  period: string;
  source: string;
  seriesId: string;
  value: number;
}

export interface EmploymentPoint {
  period: string;
  seriesId: string;
  value: number;
}

export interface SubmarketPipelineItem {
  submarket: string;
  totalProjects: number;
  totalUnits: number;
  proposed: number;
  underConstruction: number;
  delivered: number;
}

export interface ClassificationBreakdownItem {
  classification: string;
  projectCount: number;
  totalUnits: number;
}

export interface DeliveryTimelineItem {
  quarter: string;
  totalUnits: number;
  projectCount: number;
}

export interface ConstructionDataQuality {
  totalProjects: number;
  projectsBySource: Record<string, number>;
  sourceLogs: Array<Record<string, unknown>>;
  nullRates: Record<string, number>;
  permitDataCount: number;
  employmentDataCount: number;
}

export interface ConstructionImportStatus {
  unimportedFiles: string[];
  lastImportedFile: string | null;
  lastImportDate: string | null;
  totalProjects: number;
}
