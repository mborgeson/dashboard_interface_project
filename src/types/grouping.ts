/**
 * Types for the UW Model File Grouping pipeline — groups discovered UW model files
 * by structural similarity and manages per-group extraction, approval, and validation.
 */

// ---------------------------------------------------------------------------
// Pipeline status
// ---------------------------------------------------------------------------

export interface PipelineStatus {
  data_dir: string;
  phases: Record<string, string>; // phase name -> completion timestamp or empty
  stats: Record<string, number>; // aggregate counts
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Group summary (list view)
// ---------------------------------------------------------------------------

export interface GroupSummary {
  group_name: string;
  file_count: number;
  structural_overlap: number;
  era: string;
  sub_variant_count: number;
}

// ---------------------------------------------------------------------------
// Group detail
// ---------------------------------------------------------------------------

export interface GroupDetail {
  group_name: string;
  files: Array<Record<string, unknown>>;
  structural_overlap: number;
  era: string;
  sub_variants: string[];
  variances: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Phase responses
// ---------------------------------------------------------------------------

/** POST /extraction/grouping/discover */
export interface DiscoveryResponse {
  total_scanned: number;
  candidates_accepted: number;
  candidates_skipped: number;
  duplicates_removed: number;
  batch_info?: Record<string, unknown>;
}

/** POST /extraction/grouping/fingerprint */
export interface FingerprintResponse {
  total_fingerprinted: number;
  populated: number;
  sparse: number;
  empty_templates: number;
}

/** GET /extraction/grouping/groups */
export interface GroupListResponse {
  groups: GroupSummary[];
  total_groups: number;
  total_ungrouped: number;
  total_empty_templates: number;
}

/** POST /extraction/grouping/reference-map */
export interface ReferenceMappingResponse {
  groups_mapped: number;
  total_fields_mapped: number;
  total_fields_unmapped: number;
  per_group: Record<string, Record<string, unknown>>;
}

/** POST /extraction/grouping/conflict-check */
export interface ConflictCheckResponse {
  groups_with_conflicts: number;
  total_conflicts: number;
  conflicts: Record<string, Array<Record<string, unknown>>>;
}

// ---------------------------------------------------------------------------
// Extraction responses
// ---------------------------------------------------------------------------

/** POST /extraction/grouping/extract/{name} */
export interface GroupExtractionResponse {
  group_name: string;
  dry_run: boolean;
  files_processed: number;
  files_failed: number;
  total_values: number;
  started_at: string;
  completed_at: string;
}

/** POST /extraction/grouping/approve/{name} */
export interface GroupApprovalResponse {
  group_name: string;
  approved: boolean;
  message: string;
}

/** POST /extraction/grouping/extract-batch */
export interface BatchExtractionResponse {
  groups_processed: number;
  groups_failed: number;
  total_files: number;
  total_values: number;
  per_group: Record<string, GroupExtractionResponse>;
}

// ---------------------------------------------------------------------------
// Validation response
// ---------------------------------------------------------------------------

/** POST /extraction/grouping/validate */
export interface ValidationResponse {
  groups_validated: number;
  groups_passed: number;
  groups_failed: number;
  per_group: Record<string, Record<string, unknown>>;
}
