/**
 * Types for the extraction feature - UW model data extraction from SharePoint
 */

export type ExtractionStatus = 'running' | 'completed' | 'failed' | 'cancelled';
export type TriggerType = 'manual' | 'scheduled';
export type DataValueType = 'text' | 'numeric' | 'date' | 'boolean' | 'error';

export interface ExtractionRun {
  id: string;
  started_at: string;
  completed_at?: string;
  status: ExtractionStatus;
  trigger_type: TriggerType;
  files_discovered: number;
  files_processed: number;
  files_failed: number;
  error_message?: string;
}

export interface ExtractedValue {
  id: string;
  extraction_run_id: string;
  property_name: string;
  field_name: string;
  field_category: string;
  sheet_name: string;
  cell_address: string;
  value_text?: string;
  value_numeric?: number;
  value_date?: string;
  data_type: DataValueType;
  is_error: boolean;
  error_category?: string;
  error_message?: string;
  extracted_at: string;
}

export interface ExtractedProperty {
  property_name: string;
  total_fields: number;
  error_count: number;
  categories: string[];
  last_extracted_at: string;
}

export interface ExtractionStats {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  total_properties: number;
  total_fields_extracted: number;
  last_run_at?: string;
}

export interface ExtractionFilters {
  propertyName?: string;
  category?: string;
  hasErrors?: boolean;
  searchTerm?: string;
}

// API Response types
export interface ExtractionStatusResponse {
  current_run?: ExtractionRun;
  last_completed_run?: ExtractionRun;
  stats: ExtractionStats;
}

export interface ExtractionHistoryResponse {
  runs: ExtractionRun[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExtractedPropertiesResponse {
  properties: ExtractedProperty[];
  total: number;
}

export interface ExtractedPropertyValuesResponse {
  property_name: string;
  values: ExtractedValue[];
  categories: string[];
  total: number;
}

// Grouped values by category for display
export interface GroupedExtractedValues {
  category: string;
  values: ExtractedValue[];
  errorCount: number;
}
