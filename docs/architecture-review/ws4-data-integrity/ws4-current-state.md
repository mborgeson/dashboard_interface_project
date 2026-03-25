# WS4 Deliverable 1: Current State Assessment

**Workstream:** WS4 — Data Completeness & Mapping Integrity
**Date:** 2026-03-25
**Branch:** `main` at `5bfc8d4`

---

## 1. Cell Mapping System

**File:** `backend/app/extraction/cell_mapping.py`

### Architecture

The `CellMappingParser` class reads a canonical Excel reference file (`Underwriting_Dashboard_Cell_References.xlsx`) and produces a `dict[str, CellMapping]` keyed by unique field names.

| Component | Detail |
|-----------|--------|
| Class | `CellMappingParser` (line 33) |
| Source file | `Underwriting_Dashboard_Cell_References.xlsx` |
| Required sheet | `UW Model - Cell Reference Table` |
| Expected mappings | ~1,179 |
| Output type | `dict[str, CellMapping]` |

### Column Layout

| Column | Index | Content |
|--------|-------|---------|
| B | 1 | Category (e.g., Revenue, Expenses, Returns) |
| C | 2 | Description (human-readable field label) |
| D | 3 | Sheet Name (target worksheet in UW model) |
| G | 6 | Cell Address (e.g., D6, $G$10) |

### `CellMapping` Dataclass (line 23)

```python
@dataclass
class CellMapping:
    category: str
    description: str
    sheet_name: str
    cell_address: str
    field_name: str  # derived, unique key
```

### Field Name Generation

Field names are auto-generated via `_clean_field_name()` (line 165):
- Strip whitespace, replace special chars with underscores
- Convert to UPPERCASE
- Remove consecutive underscores

### Duplicate Handling (lines 104-131)

Two-pass approach:
1. **First pass**: Count occurrences of each base field name
2. **Second pass**: For duplicates, append `_{sheet_abbrev}_{occurrence_number}` suffix

The `_abbreviate_sheet_name()` method (line 208) takes the first letter of each word in the sheet name (max 4 chars). This means field uniqueness depends on **row ordering** in the reference file -- reordering rows changes the occurrence number and breaks downstream lookups.

### Validation (lines 253-295)

`validate_mappings()` checks:
- Non-empty mapping set
- Missing sheet names (sheet_name is "nan" or empty)
- Invalid cell addresses (regex `^[A-Z]+\d+$`)

Returns a quality report dict but does **not** validate financial domain ranges.

---

## 2. Reference Mapper — 4-Tier Auto-Mapping

**File:** `backend/app/extraction/reference_mapper.py`

### Actual Implementation (lines 192-299)

The 4-tier system adapts canonical mappings to variant UW model templates. **Important correction**: the actual tier definitions in code differ from the discovery document's description.

| Tier | Confidence | Code Condition | Description |
|------|-----------|----------------|-------------|
| 1a | 0.95 | Sheet exists AND label found in same sheet (line 224) | Full structural match |
| 1b | 0.85 | Sheet exists but label NOT found (line 237) | Sheet match, label mismatch |
| 2 | 0.70 | Sheet missing, label found in any sheet (line 254) | Cross-sheet label match |
| 3 | 0.50 | First 3+ words of label match a label prefix (line 273) | Partial label match |
| 4 | 0.40 | Synonym lookup via `field_synonyms.json` (line 291) | Semantic match |

### Critical Finding: Tier 1b Confidence

Tier 1b (0.85) is assigned when a sheet exists but the description label is **not found** in that sheet. The code uses `prod_cell` (the production cell address) as `source_cell`, meaning it assumes the cell is in the same position. This assumption is dangerous because:
- The label's absence may indicate the sheet layout has changed
- Using the production cell address blindly can extract the wrong value

### Synonym Support

`field_synonyms.json` does **not exist** in the repository (confirmed by file glob search). Tier 4 matching is therefore inoperative unless synonyms are explicitly passed to `auto_map_group()`.

### `GroupReferenceMapping` Output (line 45)

```python
@dataclass
class GroupReferenceMapping:
    group_name: str
    mappings: list[MappingMatch]
    unmapped_fields: list[str]
    overall_confidence: float  # Weighted avg including unmapped (denominator includes them)
    tier_counts: dict[int, int]
```

### Property Name Reconciliation (lines 302-366)

Four-tier property name matching:
1. Exact (case-insensitive)
2. Normalized (strip suffixes: -Phoenix, -Tempe, Apartments, LLC, LP, Phase X)
3. Fuzzy (Levenshtein distance <= 3 OR token overlap >= 90%)
4. Unmatched

Uses a hand-rolled Levenshtein implementation (line 446).

---

## 3. Validation System

**File:** `backend/app/extraction/validation.py`

### Current Capabilities

| Component | Description | Status |
|-----------|-------------|--------|
| `ExtractionValidator` (line 104) | Post-extraction validation engine | Implemented but underused |
| `compare_with_source()` (line 118) | Compare extracted values against source Excel | Requires source file access |
| `validate_completeness()` (line 204) | Check all mappings were attempted | Functional |
| `generate_accuracy_report()` (line 256) | Comprehensive accuracy reporting | Functional |

### What Validation Exists

1. **Value comparison** (line 327): Type-dispatched comparison with tolerances
   - Numeric: 0.01% relative tolerance (`NUMERIC_TOLERANCE = 0.0001`)
   - Dates: Exact date match (time ignored)
   - Text: Whitespace-normalized exact match
   - Empty: Both-null counts as match

2. **Completeness checking**: Counts attempted vs total mappings

3. **Accuracy threshold**: 95% accuracy rate required (`is_valid` property, line 58)

### What Validation Does NOT Exist

- **No financial domain range checks** (cap rates 0-100%, prices >= 0, etc.)
- **No batch-level reconciliation** (sum-of-amounts, row counts)
- **No schema drift detection** (template structure change alerts)
- **No pre-extraction field validation** (Pydantic models)
- **No null handling policy** (empty cells silently become `np.nan`)

---

## 4. Fingerprinting System

**File:** `backend/app/extraction/fingerprint.py`

### `SheetFingerprint` (line 25)

Per-sheet structural data:
- `name`, `row_count`, `col_count`
- `header_labels` (first row values, max 50)
- `col_a_labels` (column A values, max 100)
- `populated_cell_count`
- `signature`: MD5 hash of `name|row_count|col_count|sorted_headers|sorted_col_a`

### `FileFingerprint` (line 56)

Per-file structural data:
- `file_path`, `file_name`, `file_size`, `content_hash` (SHA-256)
- `sheets: list[SheetFingerprint]`
- `sheet_signatures`, `combined_signature`
- `sheet_name_key`: Sorted sheet names (used for grouping)
- `population_status`: populated (>=20 cells), sparse, empty, error

### Performance

- Row scanning stops at 200 rows per sheet (lines 209, 267) -- labels beyond row 200 are missed
- Parallel fingerprinting via `ThreadPoolExecutor` (not Process -- pyxlsb isn't picklable)
- Max 4 workers by default

---

## 5. Group Pipeline

**File:** `backend/app/extraction/group_pipeline.py`

### 4-Phase Pipeline

| Phase | Method | Description |
|-------|--------|-------------|
| 1 | `run_discovery()` | File filter + deduplication |
| 2.1 | `run_fingerprinting()` | Structural fingerprinting |
| 2.2 | `run_grouping()` | Cluster by structural similarity |
| 3 | `run_reference_mapping()` | Auto-map fields to canonical vocabulary |
| 4 | `run_extraction()` | Extract data into `extracted_values` |

### State Persistence

Pipeline state is stored in `backend/data/extraction_groups/`:
- `config.json` — phase completion timestamps and stats
- `discovery_manifest.json` — discovered candidate files
- `fingerprints.json` — file fingerprints
- `groups.json` — grouping results (153K lines)
- Per-group: `reference_mapping.json`, `variances.json`, `conflicts.json`

### Grouping Algorithm (`backend/app/extraction/grouping.py`)

Uses `sheet_name_key` (sorted sheet names) for initial clustering, then computes Jaccard structural overlap:
- >= 95% overlap: Same group
- 80-95% overlap: Sub-variant (flagged)
- < 80% overlap: Separate group / ungrouped

---

## 6. Error Handler

**File:** `backend/app/extraction/error_handler.py`

### 9 Error Categories (line 22)

```python
class ErrorCategory(StrEnum):
    MISSING_SHEET = "missing_sheet"
    INVALID_CELL_ADDRESS = "invalid_cell_address"
    CELL_NOT_FOUND = "cell_not_found"
    FORMULA_ERROR = "formula_error"
    DATA_TYPE_ERROR = "data_type_error"
    EMPTY_VALUE = "empty_value"
    FILE_ACCESS_ERROR = "file_access_error"
    PARSING_ERROR = "parsing_error"
    UNKNOWN_ERROR = "unknown_error"
```

### Design: All errors return `np.nan`

Every error handler method returns `np.nan` for graceful degradation. Errors are tracked in an in-memory list on the `ErrorHandler` instance. Thread-safe via `threading.Lock`.

### Critical Gap: error_category Column Never Populated in Production

The `ErrorHandler` tracks error categories internally but this information is **never passed** to the database. Evidence:

- `ExtractedValueCRUD.bulk_insert()` accepts an optional `error_categories: dict[str, str]` parameter (line 200)
- **Neither production call site passes it**:
  - `group_pipeline.py` line 818: `bulk_insert(db, ..., source_file=file_path)` -- no `error_categories`
  - `common.py` line 410: `extracted_value_crud.bulk_insert(db, ..., source_file=source_file)` -- no `error_categories`
- The `ErrorHandler` instance is reset per file (`reset()` at line 462) and its `errors` list is never serialized to the `error_categories` parameter

**Result**: The `error_category` column in `extracted_values` is always NULL in production, making error diagnosis impossible at the database level.

---

## 7. ExtractedValue EAV Schema

**File:** `backend/app/models/extraction.py`

### Table: `extracted_values`

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `id` | UUID | No | Primary key |
| `extraction_run_id` | UUID FK | No | References `extraction_runs.id` (CASCADE) |
| `property_id` | Integer FK | Yes | References `properties.id` (SET NULL) |
| `property_name` | String(255) | No | Denormalized property identifier |
| `field_name` | String(255) | No | The metric name (e.g., GOING_IN_CAP_RATE) |
| `field_category` | String(100) | Yes | Grouping category |
| `sheet_name` | String(100) | Yes | Source Excel sheet |
| `cell_address` | String(20) | Yes | Source cell reference |
| `value_text` | Text | Yes | String representation |
| `value_numeric` | Numeric(20,4) | Yes | Parsed numeric value |
| `value_date` | Date | Yes | Parsed date value |
| `is_error` | Boolean | No | Whether extraction errored |
| `error_category` | String(50) | Yes | Error classification (always NULL in production) |
| `source_file` | String(500) | Yes | Full path to source file |

### Constraints

| Constraint | Columns | Purpose |
|-----------|---------|---------|
| `uq_extracted_value` | `(extraction_run_id, property_name, field_name)` | Unique per field per property per run |
| `idx_extracted_values_lookup` | `(property_name, field_name)` | Fast lookups for UI |

### Value Resolution (line 183)

The `value` property returns: `value_numeric` if not None, else `value_date` if not None, else `value_text`.

---

## 8. Completed Extraction Summary

### Initial Run (`72c301bd`)

| Metric | Value |
|--------|-------|
| Files processed | 13/13 |
| Extracted values | 12,881 |
| Properties covered | 11 |
| Failures | 0 |
| Fields per file | ~45 average |

### Deferred Groups Expansion (9 groups)

| Metric | Value |
|--------|-------|
| Files processed | 66/66 |
| Extracted values | 2,970 |
| Groups completed | 1, 7, 9, 14, 15, 17, 20, 21, 23 |
| Failures | 0 |
| Fields per file | ~45 average |

### Active Groups (current groups.json)

| Metric | Value |
|--------|-------|
| Active groups | 39 |
| Active files | 310 |
| Excluded groups | 2 (4 files) |
| Deferred groups | 0 (66 files completed) |

---

## 9. Ungrouped Files: 28 Remaining

All 28 ungrouped files are populated `.xlsb` files following the naming convention `{Property} UW Model vCurrent.xlsb`.

### Clustering by Sheet Count

| Sheet Count | Files | Example Properties |
|-------------|-------|-------------------|
| 23 | 1 | Tides at Old Town |
| 24 | 1 | Plaza 550 |
| 28 | 7 | Canyon Greens, Duo, Gateway Village, Oasis Palms, Point at Cypress Woods, Riverpark, Sandal Ridge, West Station |
| 29 | 2 | Cranbrook Forest, Riverton Terrace |
| 30 | 1 | Kingsview Apartments |
| 32 | 9 | Brio on Ray, Copper Palms, Escondido, Lemon & Pear Tree, Mountainside, Pine Forest, Ravinia, Seneca Terrace, Tides on West Indian School |
| 33 | 7 | Sunrise Chandler, Clarendon Park, Artisan Downtown Chandler, Arts District, Coral Point, Sanctuary on Broadway, (+ 1) |

### Common Sheet Names Across Ungrouped Files

All share core sheets: `Error Checker`, `Executive Summary`, `Returns Metrics (Summary)`, `Assumptions (Summary)`, `Assumptions (Unit Matrix)`.

The 32-sheet and 33-sheet groups additionally include `Tables & Graphics (IC Memo)`.

### Why They Were Ungrouped

The grouping algorithm uses `sheet_name_key` (sorted sheet names) for initial clustering. Single files with unique sheet sets that fail the >= 80% structural overlap threshold against existing groups become ungrouped. The 28 files likely represent template variants with slightly different sheet compositions that fall below the overlap threshold relative to the 39 established groups.

---

## 10. Error Category Column — Impact Assessment

### Current State

- Column exists: `error_category: String(50)`, nullable (line 156 of `extraction.py`)
- Column is **always NULL** in production data
- 9 well-defined error categories exist in `ErrorCategory` enum (`error_handler.py` line 22)
- `ErrorHandler` tracks categories in-memory but never passes them to `bulk_insert()`

### Impact

1. **Debugging**: Cannot query `SELECT error_category, COUNT(*) FROM extracted_values WHERE is_error = TRUE GROUP BY error_category` -- all results would be NULL
2. **Monitoring**: Cannot alert on spikes in specific error categories (e.g., missing_sheet spike = template change)
3. **Remediation**: Cannot prioritize fixes by error type
4. **Audit**: Cannot assess extraction quality by error category over time
