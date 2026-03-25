# WS4 Deliverable 6: Implementation Plan

**Workstream:** WS4 — Data Completeness & Mapping Integrity
**Date:** 2026-03-25
**Format:** BMAD-style Epics → Stories → Tasks

---

## Epic 1: Mapping Manifest & Registry

**Goal:** Make the mapping layer self-documenting, auditable, and stable.

### Story 1.1: Stabilize Duplicate Field Name Suffixes (R-12)

**Size:** M | **Priority:** P2 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 1.1.1 | Change `_clean_field_name()` suffix from `_{sheet_abbrev}_{occurrence}` to `_{sheet_abbrev}_{cell_address}` | S |
| 1.1.2 | Write migration script to update existing `extracted_values.field_name` rows | M |
| 1.1.3 | Update all test fixtures that reference field names with occurrence suffixes | S |
| 1.1.4 | Add regression test: reorder reference file rows → verify field names unchanged | S |

### Story 1.2: Create Synonym Dictionary (R-07)

**Size:** S | **Priority:** P1 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 1.2.1 | Audit unmapped fields across all 9 completed deferred groups | S |
| 1.2.2 | Build `field_synonyms.json` with ~20-30 synonym pairs | S |
| 1.2.3 | Update `run_reference_mapping()` to auto-load synonyms from file | S |
| 1.2.4 | Add unit tests for Tier 4 matching with synonyms | S |

### Story 1.3: Add Confidence Score to ExtractedValue (R-13)

**Size:** M | **Priority:** P2 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 1.3.1 | Add `mapping_confidence: Numeric(3,2)` column via Alembic migration | S |
| 1.3.2 | Pass confidence from `MappingMatch` through `extract_from_file()` to `bulk_insert()` | M |
| 1.3.3 | Update `bulk_insert()` to accept and store confidence values | S |
| 1.3.4 | Update Proforma Returns UI to show confidence indicator (icon/tooltip) | S |
| 1.3.5 | Add backend test: verify confidence is persisted correctly | S |

### Story 1.4: Correct Discovery Documentation (R-08)

**Size:** S | **Priority:** P1 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 1.4.1 | Update `04-etl-mapping.md` tier table with actual code values (1a/1b/2/3/4) | S |
| 1.4.2 | Add note about `field_synonyms.json` not existing | S |
| 1.4.3 | Document the Tier 1b risk (sheet exists, label missing, cell assumed) | S |

---

## Epic 2: Validation Framework

**Goal:** Add row-level, batch-level, and domain-aware validation to the extraction pipeline.

### Story 2.1: Populate error_category in Production (R-01)

**Size:** S | **Priority:** P0 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 2.1.1 | In `group_pipeline.py` line ~818: after extraction, build `error_categories` dict from `extractor.error_handler.errors` | S |
| 2.1.2 | Pass `error_categories` to `bulk_insert()` call in `group_pipeline.py` | S |
| 2.1.3 | Same fix in `common.py` line ~410: build and pass `error_categories` | S |
| 2.1.4 | Add integration test: extract file with known errors → verify `error_category` populated in DB | S |
| 2.1.5 | Verify existing test `test_error_category_populated` still passes | S |

### Story 2.2: Differentiate Null Types (R-03)

**Size:** M | **Priority:** P0 | **Depends on:** 2.1

| Task | Description | Size |
|------|-------------|------|
| 2.2.1 | Define null handling policy: empty → not-error, formula error → error, TBD → not-error with text | S |
| 2.2.2 | Refactor `handle_empty_value()` to return `None` (not `np.nan`) for genuinely empty cells | M |
| 2.2.3 | Refactor `process_cell_value()` to preserve "N/A"/"TBD" as text values | S |
| 2.2.4 | Update `bulk_insert()` to not set `is_error = True` when value is `None` (empty cell) | S |
| 2.2.5 | Update 10+ tests that rely on NaN → is_error behavior | M |

### Story 2.3: Financial Domain Range Validation (R-05)

**Size:** M | **Priority:** P1 | **Depends on:** 2.1

| Task | Description | Size |
|------|-------------|------|
| 2.3.1 | Create `backend/app/extraction/domain_validators.py` with `DOMAIN_RULES` and `validate_domain_range()` | M |
| 2.3.2 | Integrate validation call into `bulk_insert()` — flag out-of-range values without rejecting | S |
| 2.3.3 | Add `validation_warning` field or use `error_category = "out_of_range"` for flagged values | S |
| 2.3.4 | Write 30+ unit tests for all DOMAIN_RULES boundary conditions | M |
| 2.3.5 | Add API endpoint or report to surface validation warnings | S |

### Story 2.4: Batch-Level Reconciliation (R-11)

**Size:** M | **Priority:** P2 | **Depends on:** 2.1, 2.3

| Task | Description | Size |
|------|-------------|------|
| 2.4.1 | Create `backend/app/extraction/batch_validators.py` with reconciliation rules | M |
| 2.4.2 | Add post-extraction reconciliation step in `group_pipeline.py` Phase 4 | S |
| 2.4.3 | Store reconciliation results in `ExtractionRun.error_summary` JSON | S |
| 2.4.4 | Add cross-property outlier detection (cap rate, price outliers) | S |
| 2.4.5 | Write tests for NOI = Revenue - OpEx and Cap Rate = NOI / Price checks | S |

### Story 2.5: Tier 1b Match Review System (R-02)

**Size:** M | **Priority:** P0 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 2.5.1 | Add `label_verified: bool` field to `MappingMatch` dataclass | S |
| 2.5.2 | Set `label_verified = False` for Tier 1b matches (sheet exists, label not found) | S |
| 2.5.3 | After extraction, log warning for every Tier 1b field with value outside domain range | S |
| 2.5.4 | Generate Tier 1b review report per group (list of field, value, expected range) | M |
| 2.5.5 | Add CLI command or API endpoint to view Tier 1b review report | S |

---

## Epic 3: Error Category Population

**Goal:** Make the `error_category` column a reliable diagnostic tool.

### Story 3.1: Backfill Historical error_category Data

**Size:** M | **Priority:** P1 | **Depends on:** Epic 2, Story 2.1

| Task | Description | Size |
|------|-------------|------|
| 3.1.1 | Write script to re-extract a sample of files and compare error categories | M |
| 3.1.2 | For `is_error = True` rows with `error_category = NULL`, classify by heuristic (missing sheet → sheet not in template, etc.) | M |
| 3.1.3 | Add monitoring query to track error_category distribution over time | S |
| 3.1.4 | Create Alembic migration adding NOT NULL default for new error rows (optional) | S |

### Story 3.2: Error Category Dashboard

**Size:** M | **Priority:** P2 | **Depends on:** 3.1

| Task | Description | Size |
|------|-------------|------|
| 3.2.1 | Add API endpoint `GET /api/v1/extraction/error-summary` with category breakdown | S |
| 3.2.2 | Add frontend component showing error category distribution chart | M |
| 3.2.3 | Add alert when a specific error category exceeds threshold (e.g., >10% missing_sheet) | S |

---

## Epic 4: Ungrouped File Resolution

**Goal:** Extract data from all 28 ungrouped files, adding ~25 deals to the dashboard.

### Story 4.1: Form Natural Clusters

**Size:** S | **Priority:** P1 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 4.1.1 | Analyze 28 ungrouped files by sheet count and structure overlap | S |
| 4.1.2 | Create 28-sheet cluster (7 files) as new group | S |
| 4.1.3 | Create 32-sheet cluster (9 files) as new group | S |
| 4.1.4 | Create 33-sheet cluster (7 files) as new group | S |
| 4.1.5 | Attempt 29-sheet pair (2 files) as mini-group | S |

### Story 4.2: Auto-Map New Groups

**Size:** M | **Priority:** P1 | **Depends on:** 4.1

| Task | Description | Size |
|------|-------------|------|
| 4.2.1 | Run `run_reference_mapping()` for each new group | S |
| 4.2.2 | Review tier distribution per group — flag any with > 20% below Tier 1 | M |
| 4.2.3 | Manually verify Tier 2/3 matches for correctness (spot-check 3-5 fields per group) | M |
| 4.2.4 | Document unmapped fields per group and assess impact | S |

### Story 4.3: Extract New Groups

**Size:** S | **Priority:** P1 | **Depends on:** 4.2

| Task | Description | Size |
|------|-------------|------|
| 4.3.1 | Run `run_conflict_check()` against existing data | S |
| 4.3.2 | Execute dry-run extraction for each group | S |
| 4.3.3 | Review dry-run results — check value ranges, completeness | S |
| 4.3.4 | Execute live extraction with `error_categories` populated (Story 2.1) | S |
| 4.3.5 | Sync extracted properties to properties table | S |

### Story 4.4: Handle Remaining Singles (3 files)

**Size:** M | **Priority:** P1 | **Depends on:** 4.1

| Task | Description | Size |
|------|-------------|------|
| 4.4.1 | Run individual `auto_map_group()` for Tides at Old Town (23 sheets) | S |
| 4.4.2 | Run individual `auto_map_group()` for Plaza 550 (24 sheets) | S |
| 4.4.3 | Run individual `auto_map_group()` for Kingsview Apartments (30 sheets) | S |
| 4.4.4 | Manual review of all three — may require custom cell mappings | M |
| 4.4.5 | Extract remaining singles after mapping verification | S |

---

## Epic 5: Schema Drift Detection

**Goal:** Automatically detect when UW model templates change structure, preventing silent data corruption.

### Story 5.1: Baseline Fingerprint Storage

**Size:** S | **Priority:** P1 | **Depends on:** None

| Task | Description | Size |
|------|-------------|------|
| 5.1.1 | For each completed group, store current representative fingerprint as `baseline_fingerprint.json` | S |
| 5.1.2 | Add `baseline_fingerprint` field to `PipelineConfig` tracking | S |
| 5.1.3 | Add test: verify baseline is stored after extraction | S |

### Story 5.2: Drift Detector Implementation (R-06)

**Size:** L | **Priority:** P1 | **Depends on:** 5.1

| Task | Description | Size |
|------|-------------|------|
| 5.2.1 | Create `backend/app/extraction/drift_detector.py` with `SchemaDriftDetector` class | M |
| 5.2.2 | Implement `check_drift()` comparing current vs baseline fingerprint | M |
| 5.2.3 | Define alert thresholds: >= 0.95 OK, 0.90-0.94 info, 0.80-0.89 warning, < 0.80 error | S |
| 5.2.4 | Integrate pre-extraction drift check into `group_pipeline.py` Phase 4 | S |
| 5.2.5 | Write 10+ unit tests for drift detection scenarios | M |

### Story 5.3: Drift Alert Persistence

**Size:** M | **Priority:** P2 | **Depends on:** 5.2

| Task | Description | Size |
|------|-------------|------|
| 5.3.1 | Create `schema_drift_alerts` SQLAlchemy model | S |
| 5.3.2 | Create Alembic migration for `schema_drift_alerts` table | S |
| 5.3.3 | Add CRUD for drift alerts (create, list, resolve) | S |
| 5.3.4 | Add API endpoint `GET /api/v1/extraction/drift-alerts` | S |
| 5.3.5 | Add frontend notification for unresolved drift alerts | M |

### Story 5.4: Run-over-Run Comparison

**Size:** M | **Priority:** P2 | **Depends on:** 5.2

| Task | Description | Size |
|------|-------------|------|
| 5.4.1 | Add `compare_runs()` method to `ExtractionValidator` | M |
| 5.4.2 | Detect value changes > 50% between runs for same property/field | S |
| 5.4.3 | Detect field count changes > 10% between runs | S |
| 5.4.4 | Store comparison results in `ExtractionRun.error_summary` | S |
| 5.4.5 | Add test: two runs with different values → verify comparison detects change | S |

---

## Execution Sequence

```
Phase A (P0 — Do First):
  Story 2.1 (error_category population)     → S, no dependencies
  Story 2.5 (Tier 1b review)                → M, no dependencies
  Story 2.2 (null type differentiation)     → M, depends on 2.1

Phase B (P1 — Production Readiness):
  Story 1.2 (synonyms file)                 → S, no dependencies
  Story 1.4 (doc correction)                → S, no dependencies
  Story 4.1 (form clusters)                 → S, no dependencies
  Story 4.2 (auto-map new groups)           → M, depends on 4.1
  Story 4.3 (extract new groups)            → S, depends on 4.2 + 2.1
  Story 4.4 (handle singles)                → M, depends on 4.1
  Story 2.3 (domain validation)             → M, depends on 2.1
  Story 5.1 (baseline storage)              → S, no dependencies
  Story 5.2 (drift detector)                → L, depends on 5.1
  Story 3.1 (backfill error_category)       → M, depends on 2.1

Phase C (P2 — Improvements):
  Story 1.1 (stable suffixes)               → M
  Story 1.3 (confidence on ExtractedValue)  → M
  Story 2.4 (batch reconciliation)          → M
  Story 3.2 (error category dashboard)      → M
  Story 5.3 (drift alert persistence)       → M
  Story 5.4 (run-over-run comparison)       → M
```

---

## Effort Summary

| Epic | Stories | Total Tasks | Estimated Effort |
|------|---------|-------------|-----------------|
| Epic 1: Mapping Manifest | 4 | 16 | M-L |
| Epic 2: Validation Framework | 5 | 25 | L |
| Epic 3: Error Category | 2 | 7 | M |
| Epic 4: Ungrouped Files | 4 | 18 | M-L |
| Epic 5: Schema Drift | 4 | 18 | L |
| **Total** | **19** | **84** | **XL** |

### T-Shirt Size Key

| Size | Scope |
|------|-------|
| S | < 2 hours, single file change, < 20 lines |
| M | 2-8 hours, 2-5 files, 50-200 lines |
| L | 1-3 days, 5+ files, 200-500 lines, new module |
| XL | 3+ days, cross-cutting, multiple modules |
