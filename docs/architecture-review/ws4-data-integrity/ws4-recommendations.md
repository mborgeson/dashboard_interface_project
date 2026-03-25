# WS4 Deliverable 5: Prioritized Recommendations

**Workstream:** WS4 — Data Completeness & Mapping Integrity
**Date:** 2026-03-25

---

## P0: Critical — Blocking Data Integrity

### R-01: Populate error_category in Production Extraction Paths

**What:** Wire the `ErrorHandler.errors` list into the `error_categories` dict parameter of `ExtractedValueCRUD.bulk_insert()` at both production call sites.

**Why:** The `error_category` column is always NULL in production. Without it, there is no way to distinguish missing sheets from formula errors from cell-not-found issues in the database. This is the single largest observability gap in the extraction pipeline.

**Where:**
- `backend/app/extraction/group_pipeline.py` line 818
- `backend/app/api/v1/endpoints/extraction/common.py` line 410

**How:** After calling `extractor.extract_from_file()`, iterate `extractor.error_handler.errors` to build `{field_name: error.category.value}` and pass it as `error_categories` to `bulk_insert()`.

**Effort:** Small (S)

---

### R-02: Flag and Review Tier 1b Matches (Confidence 0.85)

**What:** Tier 1b matches (sheet exists but label not found, confidence 0.85) silently use the production cell address. Add a validation step that compares the cell value type against expected type for the field.

**Why:** This is the most dangerous match tier because it looks reliable (Tier 1, 0.85 confidence) but may read from a shifted cell. Financial decisions could be based on wrong values.

**Where:** `backend/app/extraction/reference_mapper.py` lines 230-242

**How:**
1. When returning a Tier 1b match, set a flag `label_verified = False` on the `MappingMatch`
2. After extraction, log a warning for every Tier 1b value that differs significantly from expected domain range
3. Generate a report of Tier 1b fields for manual review after each group extraction

**Effort:** Medium (M)

---

### R-03: Differentiate Null Types in Error Handling

**What:** Stop collapsing all null-like values (empty cell, "N/A", "TBD", formula errors) into indistinguishable `np.nan`.

**Why:** Currently impossible to tell whether a cell was genuinely empty, had a formula error, or contained "TBD" (expected but not yet filled). This conflation masks template problems and data quality issues.

**Where:** `backend/app/extraction/error_handler.py` lines 265-300

**How:**
1. Empty cells: `is_error = False`, `value_text = NULL`
2. "N/A"/"TBD" strings: `is_error = False`, `value_text = "N/A"` or `"TBD"`
3. Formula errors (#REF!, etc.): `is_error = True`, `error_category = "formula_error"`, `value_text = "#REF!"`
4. Missing sheet: `is_error = True`, `error_category = "missing_sheet"`
5. Cell not found: `is_error = True`, `error_category = "cell_not_found"`

**Effort:** Medium (M)

---

## P1: Important — Production Readiness

### R-04: Extract the 28 Ungrouped Files

**What:** Form 3-4 new groups from the natural clusters within the 28 ungrouped files and run `auto_map_group()` on each.

**Why:** 28 files represent ~25 deals with zero extracted data. These deals are invisible on the dashboard.

**Where:** `backend/data/extraction_groups/groups.json`, `backend/app/extraction/group_pipeline.py`

**How:**
1. Group by sheet count: 28-sheet (7 files), 32-sheet (9 files), 33-sheet (7 files), 29-sheet (2 files)
2. Run `run_fingerprinting()` + `run_grouping()` with lowered thresholds if needed
3. Run `run_reference_mapping()` for each new group
4. Manually review any Tier 2/3 matches (confidence < 0.85)
5. Run `run_extraction()` for each group

**Effort:** Medium (M)

---

### R-05: Add Financial Domain Range Validation

**What:** Implement Pydantic-based domain range validators for extracted values before database insertion.

**Why:** Values outside reasonable ranges (cap rate > 25%, negative purchase price, DSCR > 5) indicate extraction errors or template mismatches. Currently, any numeric value is accepted without question.

**Where:** New file `backend/app/extraction/domain_validators.py`, integrated into `crud/extraction.py` `bulk_insert()`

**How:** See validation framework design (ws4-validation-framework.md, Section 2.2). Add `validate_domain_range()` call during `bulk_insert()` iteration. Out-of-range values should be flagged (not rejected) via a new `validation_warning` field or JSON column.

**Effort:** Medium (M)

---

### R-06: Implement Schema Drift Detection

**What:** Compare file fingerprints against stored baselines before extraction. Alert when structural overlap drops below 90%.

**Why:** If a UW model template changes layout (sheets renamed, rows inserted), extraction silently produces wrong values. Schema drift detection catches this before bad data enters the database.

**Where:** New class `SchemaDriftDetector` in `backend/app/extraction/drift_detector.py`, integrated into `group_pipeline.py` Phase 4 pre-extraction check.

**How:** See validation framework design (ws4-validation-framework.md, Section 4). Store baseline fingerprints per group. On each extraction, compare current fingerprint to baseline. Alert on overlap < 0.90.

**Effort:** Large (L)

---

### R-07: Create field_synonyms.json

**What:** Build a synonym dictionary mapping common field name variations to canonical field names, activating Tier 4 matching.

**Why:** Tier 4 matching is completely inoperative because the synonym file does not exist. Some unmapped fields may match via known aliases.

**Where:** New file `backend/app/extraction/field_synonyms.json`, referenced by `reference_mapper.py` `auto_map_group()`

**How:**
1. Audit unmapped fields across all completed groups
2. Identify synonym pairs (e.g., "Cap Rate" = "Going-In Cap Rate", "NOI" = "Net Operating Income")
3. Build JSON mapping: `{"GOING_IN_CAP_RATE": ["CAP_RATE", "ENTRY_CAP_RATE", "ACQUISITION_CAP"]}`
4. Update `run_reference_mapping()` to load and pass synonyms automatically

**Effort:** Small (S)

---

### R-08: Fix Discovery Document Tier Descriptions

**What:** Correct the tier confidence values and descriptions in `docs/architecture-review/discovery/04-etl-mapping.md` to match the actual code.

**Why:** The discovery document states Tier 2 = 0.85 and Tier 3 = 0.70, but the code implements Tier 2 = 0.70 (cross-sheet label match) and Tier 3 = 0.50 (3-word prefix match). Incorrect documentation leads to wrong risk assessments.

**Where:** `docs/architecture-review/discovery/04-etl-mapping.md` lines 71-76

**How:** Update the tier table to reflect actual code values. Add Tier 1a/1b distinction.

**Effort:** Small (S)

---

## P2: Nice-to-Have Improvements

### R-09: Close XLSB Workbooks After Extraction

**What:** Add explicit workbook close for XLSB files in the extraction path.

**Why:** Currently only XLSX workbooks are closed (`extractor.py` lines 280-281). XLSB workbooks may leak file handles and memory.

**Where:** `backend/app/extraction/extractor.py` line 280

**How:** Add `if is_xlsb and hasattr(workbook, "close"): workbook.close()` or better, use a context manager.

**Effort:** Small (S)

---

### R-10: Increase Fingerprint Row Scan Limit

**What:** Increase the 200-row scan limit in `fingerprint.py` to 500 or make it configurable.

**Why:** Labels below row 200 are missed during fingerprinting, preventing Tier 2/3 matching for those fields. Some UW models have data layouts extending well beyond row 200.

**Where:** `backend/app/extraction/fingerprint.py` lines 209, 267

**How:** Add a `max_scan_rows` parameter to `fingerprint_file()` with a higher default, or make it a settings value.

**Effort:** Small (S)

---

### R-11: Add Batch-Level Sum Reconciliation

**What:** After extraction, verify internal consistency of related financial fields (NOI = Revenue - OpEx, Cap Rate = NOI / Price, etc.).

**Why:** Even if individual cell extraction is correct, the overall financial model may be inconsistent due to formula errors or template version mismatches.

**Where:** New validation pass in `group_pipeline.py` after Phase 4 extraction, or in `validation.py`.

**How:** Define reconciliation rules (see ws4-validation-framework.md, Section 3.2). Run post-extraction. Log discrepancies.

**Effort:** Medium (M)

---

### R-12: Stabilize Duplicate Field Name Suffixes

**What:** Change the duplicate field name suffix from `_{sheet_abbrev}_{occurrence_number}` to a deterministic format based on (sheet_name, cell_address) rather than row iteration order.

**Why:** Current suffixes change when rows in the reference file are reordered, breaking all downstream field lookups.

**Where:** `backend/app/extraction/cell_mapping.py` lines 124-129

**How:** Replace occurrence-based suffix with `_{sheet_abbrev}_{cell_address}` (e.g., `EFFECTIVE_GROSS_INCOME_AS_D6`). This ties uniqueness to the structural identity of the mapping rather than its position in the file.

**Effort:** Medium (M) — requires re-extracting all data to update field names

---

### R-13: Add Confidence Score to ExtractedValue Table

**What:** Store the mapping confidence (0.40-0.95) on each `ExtractedValue` row for downstream filtering.

**Why:** Dashboard consumers have no way to know whether a value came from a Tier 1 (0.95, reliable) or Tier 3 (0.50, unreliable) match. Adding confidence allows UI to show confidence indicators and filter out low-confidence values.

**Where:** New column `mapping_confidence: Numeric(3,2)` on `extracted_values` table

**How:** Pass confidence from `MappingMatch` through extraction pipeline to `bulk_insert()`. Requires Alembic migration.

**Effort:** Medium (M)

---

## Summary Table

| # | Recommendation | Priority | Effort | Category |
|---|---------------|----------|--------|----------|
| R-01 | Populate error_category | P0 | S | Error tracking |
| R-02 | Review Tier 1b matches | P0 | M | Mapping integrity |
| R-03 | Differentiate null types | P0 | M | Error handling |
| R-04 | Extract 28 ungrouped files | P1 | M | Data completeness |
| R-05 | Domain range validation | P1 | M | Validation |
| R-06 | Schema drift detection | P1 | L | Monitoring |
| R-07 | Create field_synonyms.json | P1 | S | Mapping coverage |
| R-08 | Fix discovery doc tiers | P1 | S | Documentation |
| R-09 | Close XLSB workbooks | P2 | S | Resource management |
| R-10 | Increase fingerprint row limit | P2 | S | Mapping coverage |
| R-11 | Batch sum reconciliation | P2 | M | Validation |
| R-12 | Stabilize duplicate suffixes | P2 | M | Mapping stability |
| R-13 | Confidence on ExtractedValue | P2 | M | Observability |
