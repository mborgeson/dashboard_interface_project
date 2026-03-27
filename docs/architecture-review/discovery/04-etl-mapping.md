# Discovery 04 -- ETL / Mapping Layer

## Overview

The extraction pipeline converts underwriting model Excel files into structured database rows via a multi-stage ETL process. Cell addresses are mapped from a canonical reference file, adapted per template family through a 4-tier auto-mapping system, and stored in an Entity-Attribute-Value (EAV) table. The pipeline is template-specific and inherently fragile -- changes to Excel layout silently break extraction.

---

## Pipeline Flow

```
file_filter.py (classify incoming files)
  --> fingerprint.py (identify UW model template family)
    --> reference_mapper.py (adapt cell addresses to target template)
      --> extractor.py (read cell values via openpyxl)
        --> ExtractedValue table (upsert rows, one per field per property)
```

Each stage is independently testable but tightly coupled to the Excel template structure. A shift in cell layout at any stage cascades downstream.

---

## Cell Mapping (`cell_mapping.py`)

### Parser

| Attribute | Detail |
|-----------|--------|
| Class | `CellMappingParser` |
| Source file | `Underwriting_Dashboard_Cell_References.xlsx` |
| Required sheet | `UW Model - Cell Reference Table` |
| Expected mappings | ~1,179 |
| Validation | Column count >= 7, sheet existence |

### Column Layout (by position)

| Column | Index | Content | Example |
|--------|-------|---------|---------|
| B | 1 | Category | `Revenue`, `Expenses` |
| C | 2 | Description | `Effective Gross Income` |
| D | 3 | Sheet Name (target sheet in UW model) | `Assumptions`, `Returns` |
| G | 6 | Cell Address | `D6`, `$G$10` |

### `CellMapping` Dataclass

```
CellMapping:
  category: str
  description: str
  sheet_name: str
  cell_address: str
  field_name: str       # derived, unique key
```

### Duplicate Field Name Handling

When multiple mappings produce the same `field_name`, uniqueness is enforced by appending a suffix in the format `_sheet_rowindex`. This means the generated field names are sensitive to the row ordering of the reference file -- reordering rows in the source Excel changes the suffixes and breaks downstream lookups.

### Return Type

`dict[str, CellMapping]` keyed by unique `field_name`.

---

## Reference Mapper (`reference_mapper.py`)

### 4-Tier Auto-Mapping System

The reference mapper adapts the canonical ~1,179 cell mappings to variant UW model templates. Each field is matched through progressively looser heuristics, with a confidence score reflecting match quality.

| Tier | Confidence | Strategy | Description |
|------|-----------|----------|-------------|
| 1a | 0.95 | Exact cell reference match | Same sheet exists in fingerprint + description label found in that sheet (highest confidence) |
| 1b | 0.85 | Label-based match | Same sheet exists but description label NOT found; cell address used unchanged (`label_verified=False`) -- needs manual verification |
| 2 | 0.70 | Cross-sheet label match | Description label found in a different sheet (prefers header labels over column-A labels) |
| 3 | 0.50 | Partial label match | First 3+ words of the description match a label prefix in any sheet (heuristic) |
| 4 | 0.40 | Semantic/synonym match | Description matched via `field_synonyms.json` synonym group (lowest confidence) |

**Note on Tier 1b risk:** Tier 1b matches appear reliable (Tier 1, 0.85 confidence) but may silently read from a shifted cell because the label was not verified. Financial decisions could be based on incorrect values. The `label_verified` flag on `MappingMatch` distinguishes 1a from 1b. Domain range validation (`validate_domain_ranges()`) provides a post-extraction safety net for Tier 1b fields.

### Key Function

```python
auto_map_group(
    group_name: str,
    production_mappings: dict[str, CellMapping],
    representative_fp: FileFingerprint,
    synonyms: dict
) -> GroupReferenceMapping
```

### `GroupReferenceMapping` Output

| Field | Type | Description |
|-------|------|-------------|
| `mappings` | `list[MappingMatch]` | Each match includes: `field_name`, `source_sheet`, `source_cell`, `match_tier`, `confidence`, `label_text`, `category`, `production_sheet`, `production_cell` |
| `unmapped_fields` | `list[str]` | Fields that could not be matched at any tier |
| `overall_confidence` | `float` | Weighted average across all matched fields |
| `tier_counts` | `dict[int, int]` | Count of matches per tier (e.g., `{1: 800, 2: 200, 3: 100, 4: 50}`) |

### Property Name Reconciliation

Separate from cell mapping, property names are reconciled between extracted data and existing database records via `PropertyMatch` tiers:

| Tier | Strategy |
|------|----------|
| 1 | Exact string match |
| 2 | Normalized match (case-insensitive, whitespace-normalized) |
| 3 | Fuzzy match (edit distance, token overlap) |
| 4 | Unmatched (new property) |

---

## Fingerprinting (`fingerprint.py`)

- Identifies UW model type/template family from sheet-level metadata
- `FileFingerprint` dataclass captures structural characteristics of each file
- Used by `reference_mapper` to determine which cell addresses apply to a given file
- **Groups system**: files sharing the same fingerprint are grouped together
  - 9 deferred groups completed (66 files, 2,970 extracted values)
  - 28 ungrouped files remain (24 exact group matches + 4 near-matches)

---

## Group Pipeline (`group_pipeline.py`)

Orchestrates batch extraction for files that share a template family.

### Process

1. **Discover groups** -- cluster files by fingerprint similarity
2. **Select representative** -- pick one file per group as the mapping anchor
3. **Auto-map** -- run `reference_mapper.auto_map_group()` against the representative
4. **Extract all members** -- apply the resolved mappings to every file in the group

### Extraction Statistics

| Metric | Value |
|--------|-------|
| Initial run (run `72c301bd`) | 13/13 files, 12,881 values, 11 properties |
| Deferred groups expansion | 66/66 files, 2,970 values, 9 groups |
| Average values per file | ~45 |
| Ungrouped remaining | 28 files |

---

## ExtractedValue Storage (EAV Pattern)

### Table: `extracted_values`

Each cell mapping result is stored as a row (not a column). This EAV pattern allows the schema to accommodate any number of fields without DDL changes.

| Column | Type | Notes |
|--------|------|-------|
| `property_name` | `String(255)` | Indexed |
| `field_name` | `String(255)` | Indexed |
| `field_category` | `String(100)` | Nullable |
| `sheet_name` | `String(100)` | Nullable |
| `cell_address` | `String(20)` | Nullable |
| `value_text` | `Text` | Nullable; all values stored as text |
| `value_numeric` | `Numeric(20,4)` | Nullable; financial precision |
| `value_date` | `Date` | Nullable |
| `is_error` | `Boolean` | Default `False` |
| `error_category` | `String(50)` | Nullable; underutilized |
| `source_file` | `String(500)` | Nullable |

### Constraints and Indexes

- **Unique constraint**: `(extraction_run_id, property_name, field_name)`
- **Lookup index**: `(property_name, field_name)`

---

## Transform Logic

### Reading

- `openpyxl` reads raw cell values from `.xlsx` / `.xlsb` files
- Graceful handling of corrupt files (added in commit `b22d1b9`)

### Type Coercion

| Excel Type | Python Type | Storage Column |
|------------|-------------|----------------|
| Date/datetime | `datetime` | `value_date` |
| Percentage | `float` | `value_numeric` |
| Currency | `Decimal` | `value_numeric` |
| Text/string | `str` | `value_text` |
| Null/empty cell | `None` | All value columns `NULL` |

### Financial Precision

`Numeric(20,4)` provides 20 total digits with 4 decimal places -- sufficient for large dollar amounts (up to trillions) without floating-point drift.

---

## Validation (`validation.py`)

Post-extraction validation checks applied to `ExtractedValue` rows:

| Validation Type | Description |
|-----------------|-------------|
| Type checking | Numeric fields should have non-null `value_numeric` |
| Range checking | Cap rates, percentages within valid ranges |
| Required field enforcement | Key fields (e.g., `GOING_IN_CAP_RATE`) must be present |

---

## Known Fragility Points

1. **Template-specific cell references** -- a new Excel template version shifts cells and breaks extraction without warning.
2. **Single canonical reference file** -- all ~1,179 mappings derive from `Underwriting_Dashboard_Cell_References.xlsx`. If this file is lost or corrupted, the entire mapping layer is unrecoverable without reconstruction.
3. **Low-confidence matches need manual review** -- Tier 3 (0.70) and Tier 4 (0.40--0.50) matches may produce incorrect cell addresses. These variant mappings should be spot-checked against actual cell content.
4. **Underutilized error tracking** -- `error_category` on `ExtractedValue` is often `NULL`, reducing the ability to diagnose extraction failures at scale.
5. **No schema drift detection** -- if an Excel template changes structure (sheets renamed, rows inserted), extraction either fails silently or produces wrong values. There is no automated check that the template still matches expectations.
6. **Row-index-dependent deduplication** -- duplicate `field_name` handling appends `_sheet_rowindex` suffixes. Reordering rows in the reference file changes these suffixes and breaks all downstream field lookups.
7. **28 ungrouped files** -- these may require custom mappings or new group definitions before they can be extracted.

---

## Key Source Files

| File | Role |
|------|------|
| `backend/app/extraction/cell_mapping.py` | Parse canonical reference Excel into `CellMapping` dict |
| `backend/app/extraction/reference_mapper.py` | 4-tier auto-mapping, `GroupReferenceMapping` output |
| `backend/app/extraction/fingerprint.py` | Template family identification |
| `backend/app/extraction/extractor.py` | Read cell values from Excel files |
| `backend/app/extraction/group_pipeline.py` | Batch extraction orchestration |
| `backend/app/extraction/file_filter.py` | File classification (entry point) |
| `backend/app/extraction/validation.py` | Post-extraction value validation |
| `backend/app/models/extracted_value.py` | SQLAlchemy model for `extracted_values` table |
