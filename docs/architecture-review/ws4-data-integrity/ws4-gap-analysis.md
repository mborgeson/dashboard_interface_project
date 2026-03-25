# WS4 Deliverable 3: Gap Analysis

**Workstream:** WS4 — Data Completeness & Mapping Integrity
**Date:** 2026-03-25

---

## 1. Fields in Excel Templates Not Mapped to DB Columns

### Context

The extraction pipeline uses an EAV (Entity-Attribute-Value) pattern, so "mapped to DB columns" means "extracted into the `extracted_values` table as a row." There is no wide table with named columns per field.

### Unmapped Fields

| Gap Type | Description | Impact |
|----------|-------------|--------|
| **Unmapped in auto_map_group** | Fields in `GroupReferenceMapping.unmapped_fields` that could not be matched at any tier | These fields produce no data for properties in that group |
| **Absent from reference file** | Fields present in UW model sheets that are not listed in the ~1,179 canonical mappings | Invisible to the extraction pipeline entirely |
| **Below row 200** | Labels in rows 201+ are not captured during fingerprinting (scan limit at line 209/267 of `fingerprint.py`) | Tier 2/3 matching cannot find these labels |

### Specific Known Gaps

| Field / Area | Status | Evidence |
|-------------|--------|----------|
| `GOING_IN_CAP_RATE` | Extracted but 0.0% for 2 properties (Broadstone 7th Street, Park on Bell) | May indicate missing cell in those specific templates |
| `T3_RETURN_ON_COST` | 0.0 for same 2 properties | Same root cause |
| Supplemental return fields (6 total) | Only available in 11 of 13 initial files | Cabana/Tempe Metro templates lack these cells |
| Construction-era fields | Not in reference file | Newer UW model versions may have added fields |

---

## 2. DB Columns with No Excel Source (Orphaned Columns)

### Properties Table

Several columns on the `properties` table can be populated from extraction OR from manual entry / other data sources:

| Column | Extraction Source | Other Source | Orphan Risk |
|--------|------------------|-------------|-------------|
| `purchase_price` | Yes (from UW model) | Manual entry | Low |
| `current_value` | No direct extraction | Manual / appraisal | Medium |
| `cap_rate` | Yes (GOING_IN_CAP_RATE) | Derived field | Low |
| `occupancy_rate` | Depends on template | Market data | Medium |
| `avg_rent_per_unit` | Yes (from unit mix) | Manual entry | Low |
| `avg_rent_per_sf` | May be calculated | Manual entry | Medium |
| `latitude`, `longitude` | Not in UW model | Geocoding service | Not applicable |
| `county` | Not in UW model | Lookup service | Not applicable |

### Underwriting Model Tables (11 tables)

The `UnderwritingModel` and its child tables (`GeneralAssumptions`, `ExitAssumptions`, etc.) are **structured** schema models that exist alongside the EAV `extracted_values` table. Currently:

- These tables appear to be populated independently (not from the extraction pipeline)
- The extraction pipeline writes to `extracted_values` only
- There is no automated sync from `extracted_values` to the structured underwriting tables

This creates a **dual representation**: financial data exists both as EAV rows in `extracted_values` AND as structured columns in the underwriting model tables. The two may diverge.

---

## 3. Silent Failure Points

### 3.1 Tier 1b: Sheet Exists, Label Missing

**File:** `reference_mapper.py`, lines 230-242

When a sheet exists in the fingerprint but the description label is NOT found, the code assigns Tier 1 with confidence 0.85 and uses the **production cell address unchanged**. This is a silent failure because:
- No warning is logged at this point
- The cell address may point to a completely different value
- The match is still recorded as Tier 1 (looks reliable)

### 3.2 NaN Swallowing

**File:** `extractor.py`, lines 254-273

The extraction loop catches all exceptions and replaces values with `np.nan`:

```python
except Exception as e:
    extracted_data[field_name] = np.nan
    extracted_data["_extraction_errors"].append({...})
```

Errors are appended to `_extraction_errors` in the result dict, but this list is stored in the `ExtractionRun.error_summary` JSON column (if at all) — not in the per-value `error_category` column. Individual `ExtractedValue` rows with `is_error = True` have no `error_category`, making it impossible to distinguish "missing sheet" from "formula error" from "cell not found" at the database level.

### 3.3 Empty Cell Handling

**File:** `error_handler.py`, lines 178-197

`handle_empty_value()` returns `np.nan` by default. The `treat_as_error` parameter defaults to `False`, meaning empty cells are silently treated as extraction failures without being flagged as errors unless explicitly requested. In the extractor (line 505), empty cells from XLSB extraction always call `handle_empty_value()` without `treat_as_error=True`.

### 3.4 Missing Indicator Swallowing

**File:** `error_handler.py`, lines 288-290

The string values "n/a", "na", "null", "none", "", "-", "tbd", "tba" are all treated as empty and return `np.nan`. This means:
- A cell containing the text "N/A" (which might be a legitimate Excel-reported error) is silently dropped
- "TBD" fields (which indicate the value is expected but not yet filled) are indistinguishable from truly empty cells

### 3.5 Fingerprint Row Limit

**File:** `fingerprint.py`, lines 209, 267

Scanning stops at row 200. If labels used for Tier 2/3 matching are located below row 200, they will not be found, and the mapping will fall to a lower tier or be unmapped entirely. No warning is emitted.

### 3.6 Workbook Close in XLSB

**File:** `extractor.py`, lines 280-281

The XLSB workbook is never explicitly closed in the extraction path. Only XLSX workbooks are closed:

```python
if not is_xlsb and hasattr(workbook, "close"):
    workbook.close()
```

For XLSB files, the workbook handle may leak, consuming memory and potentially locking files.

---

## 4. error_category Never Populated — Impact Assessment

### Root Cause Chain

1. `ErrorHandler` (error_handler.py) classifies errors into 9 categories
2. `ErrorHandler.errors` list accumulates `ExtractionError` objects with `.category` fields
3. `ExcelDataExtractor.extract_from_file()` calls `self.error_handler.get_error_summary()` and stores it in `_extraction_metadata`
4. The `_extraction_metadata` dict goes into `ExtractionRun.error_summary` (JSON)
5. **But**: The per-field `error_category` mapping is **never constructed** from `ErrorHandler.errors` and passed to `bulk_insert()`
6. The `error_categories` parameter on `bulk_insert()` receives `None` at both call sites

### Impact Severity: HIGH

| Area | Impact |
|------|--------|
| **Production debugging** | Cannot query which error type affects which fields/properties |
| **Error trending** | Cannot track if missing_sheet errors increase over time (template drift) |
| **Automated alerting** | Cannot trigger alerts on specific error categories |
| **Extraction quality dashboard** | Cannot show error breakdown charts |
| **Manual review prioritization** | Cannot identify which properties need attention by error type |

### Fix Complexity: SMALL

The fix requires:
1. After extraction, iterate `error_handler.errors` to build `{field_name: error.category.value}` dict
2. Pass this dict as `error_categories` to `bulk_insert()`
3. Two call sites to update: `group_pipeline.py` line 818 and `common.py` line 410

---

## 5. The 28 Ungrouped Files — Mapping Effort Assessment

### File Distribution

| Sheet Count | Files | Assessment |
|-------------|-------|-----------|
| 23 | 1 | Likely a stripped-down template variant |
| 24 | 1 | Likely a stripped-down template variant |
| 28 | 7 | Probable group — share identical sheet structure |
| 29 | 2 | May be 28+1 variant |
| 30 | 1 | Near-match to 28/29 group |
| 32 | 9 | Probable group — share identical sheet structure |
| 33 | 7 | Probable group — share identical sheet structure |

### Recommended Approach

**Natural clusters within the 28 files:**

1. **28-sheet cluster** (7 files): Canyon Greens, Duo, Gateway Village, Oasis Palms, Point at Cypress Woods, Riverpark, Sandal Ridge, West Station
   - Shared sheets: Error Checker, Executive Summary, Returns Metrics (Summary), Assumptions (Summary), Assumptions (Unit Matrix)
   - Missing: Tables & Graphics (IC Memo) — present in 32/33-sheet templates
   - **Effort: Small** — run `auto_map_group()` on this cluster

2. **32-sheet cluster** (9 files): Brio on Ray, Copper Palms, Escondido, Lemon & Pear Tree, Mountainside, Pine Forest, Ravinia, Seneca Terrace, Tides on West Indian School
   - **Effort: Small** — run `auto_map_group()` on this cluster

3. **33-sheet cluster** (7 files): Sunrise Chandler, Clarendon Park, Artisan Downtown Chandler, Arts District, Coral Point, Sanctuary on Broadway, +1
   - **Effort: Small** — run `auto_map_group()` on this cluster

4. **Remaining singles** (5 files): Tides at Old Town (23), Plaza 550 (24), Kingsview (30), Cranbrook Forest (29), Riverton Terrace (29)
   - 29-sheet pair: Cranbrook Forest + Riverton Terrace may form a mini-group
   - Others: need individual `auto_map_group()` runs or manual mapping
   - **Effort: Medium** — individual analysis required

### Total Effort Estimate

| Action | Files | Effort |
|--------|-------|--------|
| Form 3 new groups from natural clusters | 23 | Small (automated) |
| Form 1 mini-group from 29-sheet pair | 2 | Small |
| Individual auto-mapping for 3 singles | 3 | Medium |
| Manual review of low-confidence matches | All 28 | Medium (ongoing) |
| **Total** | **28** | **Medium overall** |

---

## 6. Precision Issues: Numeric(20,4) vs Financial Data

### Current Schema

`value_numeric: Numeric(20,4)` — 20 total digits, 4 decimal places.

### Range Assessment

| Data Type | Typical Range | Max Value | Numeric(20,4) Max | Sufficient? |
|-----------|-------------|-----------|-------------------|-------------|
| Purchase price | $1M - $500M | ~$999,999,999,999,999.9999 | 10^16 - 1 | Yes |
| Rent per unit | $500 - $5,000 | < $100,000 | Yes | Yes |
| Cap rate | 0.0% - 20% | < 100% | Yes | Yes |
| IRR | -100% to 999% | < 1,000% | Yes | Yes |
| MOIC | 0x - 10x | < 1,000x | Yes | Yes |
| DSCR | 0 - 5 | < 100 | Yes | Yes |
| NOI | $100K - $50M | < $1B | Yes | Yes |

### Precision Concern

4 decimal places is sufficient for percentages (0.0001 = 0.01%) and dollar amounts ($0.0001 precision). However:
- IRR values like -4.9123456% would be truncated to -4.9123% — losing 3+ significant digits
- Basis point precision (0.0001 = 0.01%) is at the limit
- **Assessment**: Acceptable for the current use case but would need revisiting for more precise financial modeling

---

## 7. Null Handling Gaps

### Fields That Silently Drop Nulls

| Scenario | Code Location | Behavior | Impact |
|----------|--------------|----------|--------|
| Empty Excel cell | `error_handler.py` line 266 | Returns `np.nan` | `is_error = True`, no `error_category` |
| Cell contains None | `error_handler.py` line 265 | Returns `np.nan` | Same as above |
| Cell contains "N/A" | `error_handler.py` line 289 | Returns `np.nan` | Treated as empty, not as Excel error |
| Cell contains "TBD" | `error_handler.py` line 289 | Returns `np.nan` | Expected-but-missing conflated with empty |
| Cell contains NaN float | `error_handler.py` line 298 | Returns `np.nan` | Infinite/NaN collapsed to empty |
| Cell formula error (#REF!) | `error_handler.py` line 283 | Returns `np.nan` | Properly flagged as FORMULA_ERROR in handler, but error_category not persisted |

### The Core Problem

All null-like values are collapsed into `np.nan` → `is_error = True` with `error_category = NULL`. This makes it impossible to distinguish:
- A cell that genuinely contains no data (expected)
- A cell that contains "TBD" (data expected but not yet available)
- A cell that has a formula error (#REF!) (broken model)
- A cell that doesn't exist (template mismatch)

### Recommended Null Policy

| Scenario | Should Set | is_error | error_category |
|----------|-----------|----------|----------------|
| Cell empty / None | `value_text = NULL` | `False` | `NULL` |
| Cell contains "N/A" | `value_text = "N/A"` | `False` | `NULL` |
| Cell contains "TBD" | `value_text = "TBD"` | `False` | `NULL` |
| Cell formula error | `value_text = "#REF!"` | `True` | `formula_error` |
| Cell not found | `value_text = NULL` | `True` | `cell_not_found` |
| Sheet missing | `value_text = NULL` | `True` | `missing_sheet` |

---

## 8. Summary of Gaps

| # | Gap | Severity | Effort to Fix |
|---|-----|----------|--------------|
| G-01 | error_category never populated in production | **Critical** | Small |
| G-02 | Tier 1b (0.85) uses production cell without label verification | **High** | Medium |
| G-03 | 28 ungrouped files = ~25 deals with no extracted data | **High** | Medium |
| G-04 | No schema drift detection | **High** | Large |
| G-05 | All null-like values collapsed into indistinguishable NaN | **Medium** | Medium |
| G-06 | Synonym file missing — Tier 4 inoperative | **Medium** | Small |
| G-07 | Discovery doc tier descriptions incorrect | **Medium** | Small |
| G-08 | Fingerprint 200-row scan limit may miss labels | **Medium** | Small |
| G-09 | XLSB workbook not explicitly closed | **Low** | Small |
| G-10 | Dual representation (EAV + structured UW tables) may diverge | **Low** | Large |
| G-11 | Duplicate field suffixes depend on row ordering | **Low** | Medium |
| G-12 | No batch-level sum reconciliation | **Low** | Medium |
