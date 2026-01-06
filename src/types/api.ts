/**
 * API Types for React-Query hooks
 * These types represent the API request/response shapes
 */

// ============================================================================
// Common API Types
// ============================================================================

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasMore: boolean;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, string[]>;
}

export interface SortParams {
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

// ============================================================================
// Property Types
// ============================================================================

export interface PropertyFilters extends PaginationParams, SortParams {
  submarket?: string;
  propertyClass?: 'A' | 'B' | 'C';
  assetType?: 'Garden' | 'Mid-Rise' | 'High-Rise';
  minUnits?: number;
  maxUnits?: number;
  minValue?: number;
  maxValue?: number;
  search?: string;
}

export interface PropertyApiResponse {
  id: string;
  name: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
    latitude: number;
    longitude: number;
    submarket: string;
  };
  propertyDetails: {
    units: number;
    squareFeet: number;
    averageUnitSize: number;
    yearBuilt: number;
    propertyClass: 'A' | 'B' | 'C';
    assetType: 'Garden' | 'Mid-Rise' | 'High-Rise';
    amenities: string[];
  };
  acquisition: {
    date: string; // ISO date string from API
    purchasePrice: number;
    pricePerUnit: number;
    closingCosts: number;
    acquisitionFee: number;
    totalInvested: number;
  };
  financing: {
    loanAmount: number;
    loanToValue: number;
    interestRate: number;
    loanTerm: number;
    amortization: number;
    monthlyPayment: number;
    lender: string;
    originationDate: string;
    maturityDate: string;
  };
  valuation: {
    currentValue: number;
    lastAppraisalDate: string;
    capRate: number;
    appreciationSinceAcquisition: number;
  };
  operations: {
    occupancy: number;
    averageRent: number;
    rentPerSqft: number;
    monthlyRevenue: number;
    otherIncome: number;
    monthlyExpenses: {
      propertyTax: number;
      insurance: number;
      utilities: number;
      management: number;
      repairs: number;
      payroll: number;
      marketing: number;
      other: number;
      total: number;
    };
    noi: number;
    operatingExpenseRatio: number;
  };
  performance: {
    cashOnCashReturn: number;
    irr: number;
    equityMultiple: number;
    totalReturnDollars: number;
    totalReturnPercent: number;
  };
  images: {
    main: string;
    gallery: string[];
  };
}

export type PropertyListResponse = PaginatedResponse<PropertyApiResponse>;

export interface PropertyCreateInput {
  name: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
    latitude: number;
    longitude: number;
    submarket: string;
  };
  propertyDetails: {
    units: number;
    squareFeet: number;
    yearBuilt: number;
    propertyClass: 'A' | 'B' | 'C';
    assetType: 'Garden' | 'Mid-Rise' | 'High-Rise';
    amenities: string[];
  };
  acquisition: {
    date: string;
    purchasePrice: number;
    closingCosts: number;
    acquisitionFee: number;
  };
  financing: {
    loanAmount: number;
    interestRate: number;
    loanTerm: number;
    amortization: number;
    lender: string;
  };
}

export interface PropertyUpdateInput extends Partial<PropertyCreateInput> {
  id: string;
}

// ============================================================================
// Deal Types
// ============================================================================

export type DealStageApi =
  | 'lead'
  | 'underwriting'
  | 'loi'
  | 'due_diligence'
  | 'closing'
  | 'closed_won'
  | 'closed_lost';

export interface DealFilters extends PaginationParams, SortParams {
  stage?: DealStageApi;
  assignee?: string;
  propertyType?: string;
  minValue?: number;
  maxValue?: number;
  search?: string;
  createdAfter?: string;
  createdBefore?: string;
}

export interface DealTimelineEventApi {
  id: string;
  date: string;
  stage: DealStageApi;
  description: string;
  user?: string;
}

export interface DealApiResponse {
  id: string;
  propertyName: string;
  address: {
    street: string;
    city: string;
    state: string;
  };
  value: number;
  capRate: number;
  stage: DealStageApi;
  daysInStage: number;
  totalDaysInPipeline: number;
  assignee: string;
  propertyType: string;
  units: number;
  createdAt: string;
  timeline: DealTimelineEventApi[];
  notes?: string;
}

export type DealListResponse = PaginatedResponse<DealApiResponse>;

export interface DealCreateInput {
  propertyName: string;
  address: {
    street: string;
    city: string;
    state: string;
  };
  value: number;
  capRate: number;
  propertyType: string;
  units: number;
  assignee: string;
  notes?: string;
}

export interface DealUpdateInput extends Partial<DealCreateInput> {
  id: string;
}

export interface DealStageUpdateInput {
  id: string;
  stage: DealStageApi;
  note?: string;
}

// ============================================================================
// Extraction Types
// ============================================================================

export type ExtractionStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type ExtractionSource =
  | 'costar'
  | 'yardi'
  | 'mls'
  | 'zillow'
  | 'manual'
  | 'api';

export interface ExtractedValue {
  id: string;
  fieldName: string;
  value: string | number | boolean | null;
  confidence: number; // 0-1
  source: ExtractionSource;
  extractedAt: string;
  rawValue?: string;
  validated: boolean;
  validatedBy?: string;
  validatedAt?: string;
}

export interface ExtractionRun {
  id: string;
  propertyId?: string;
  dealId?: string;
  source: ExtractionSource;
  status: ExtractionStatus;
  startedAt: string;
  completedAt?: string;
  totalFields: number;
  extractedFields: number;
  failedFields: number;
  values: ExtractedValue[];
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface ExtractionHistoryFilters extends PaginationParams {
  propertyId?: string;
  dealId?: string;
  source?: ExtractionSource;
  status?: ExtractionStatus;
  startedAfter?: string;
  startedBefore?: string;
}

export type ExtractionHistoryResponse = PaginatedResponse<ExtractionRun>;

export interface StartExtractionInput {
  propertyId?: string;
  dealId?: string;
  source: ExtractionSource;
  fields?: string[]; // Specific fields to extract, or all if omitted
  options?: {
    validateResults?: boolean;
    overwriteExisting?: boolean;
    notifyOnComplete?: boolean;
  };
}

export interface ExtractionStatusResponse {
  runId: string;
  status: ExtractionStatus;
  progress: number; // 0-100
  currentField?: string;
  estimatedTimeRemaining?: number; // seconds
}

// ============================================================================
// Auth Types (for completeness)
// ============================================================================

export interface LoginInput {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  avatar?: string;
}
