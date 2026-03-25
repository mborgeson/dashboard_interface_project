# WS4 Deliverable 2: Mapping Manifest & Audit

**Workstream:** WS4 — Data Completeness & Mapping Integrity
**Date:** 2026-03-25

---

## 1. Mapping Data Structures

### Source: `Underwriting_Dashboard_Cell_References.xlsx`

| Attribute | Value |
|-----------|-------|
| Sheet name | `UW Model - Cell Reference Table` |
| Total mappings | ~1,179 |
| Column B (index 1) | Category |
| Column C (index 2) | Description |
| Column D (index 3) | Sheet Name |
| Column G (index 6) | Cell Address |

### Canonical `CellMapping` Record

```python
CellMapping(
    category="Revenue",
    description="Effective Gross Income",
    sheet_name="Assumptions",
    cell_address="D6",
    field_name="EFFECTIVE_GROSS_INCOME"  # auto-generated
)
```

### Field Name Derivation Rules

**File:** `backend/app/extraction/cell_mapping.py`, method `_clean_field_name()` (line 165)

| Character | Replacement |
|-----------|-------------|
| space | `_` |
| `-` | `_` |
| `(`, `)` | removed |
| `/` | `_` |
| `.`, `,`, `'`, `"`, `$` | removed |
| `#` | `NUM` |
| `%` | `PCT` |
| `&` | `AND` |

Result is UPPERCASED, consecutive underscores collapsed, leading/trailing underscores stripped.

### Duplicate Field Name Resolution

When multiple rows produce the same base `field_name`, a suffix is appended:

```
{base_name}_{sheet_abbreviation}_{occurrence_number}
```

Where `sheet_abbreviation` is the first letter of each word in the sheet name (max 4 chars). For example, "Assumptions (Summary)" becomes `AS`.

**Fragility warning**: Occurrence number is based on **row iteration order** in the reference file. Inserting, deleting, or reordering rows changes these suffixes and breaks all downstream lookups for duplicated fields.

---

## 2. Field Vocabulary

### Categories (from reference file Column B)

Based on the extraction pipeline documentation and the known field names used in the dashboard:

| Category | Examples | Typical Fields |
|----------|----------|----------------|
| Revenue | Gross potential rent, vacancy loss, concessions | GROSS_POTENTIAL_RENT, VACANCY_LOSS, EFFECTIVE_GROSS_INCOME |
| Expenses | Operating expenses, taxes, insurance | TOTAL_OPERATING_EXPENSES, REAL_ESTATE_TAXES, INSURANCE |
| Returns | Cap rates, IRR, MOIC, cash-on-cash | GOING_IN_CAP_RATE, T3_RETURN_ON_COST, UNLEVERED_RETURNS_IRR, LEVERED_RETURNS_IRR |
| Financing | Loan terms, LTV, debt service | LOAN_AMOUNT, LTV_RATIO, ANNUAL_DEBT_SERVICE, DSCR |
| Assumptions | Hold period, growth rates, renovation budget | HOLD_PERIOD, RENT_GROWTH_RATE, RENOVATION_BUDGET |
| Unit Mix | Unit counts by type, rents by type | TOTAL_UNITS, AVG_RENT_PER_UNIT, AVG_SF_PER_UNIT |
| Property | Physical attributes, location | YEAR_BUILT, TOTAL_SF, STORIES, PARKING_SPACES |
| Uncategorized | Fields with missing category in reference file | Varies |

### Sheet Names (from reference file Column D)

Common target sheets across UW model templates:

| Sheet Name | Description |
|------------|-------------|
| Assumptions | General deal assumptions |
| Assumptions (Summary) | Summary view of assumptions |
| Assumptions (Unit Matrix) | Unit mix and rent data |
| Returns Metrics (Summary) | IRR, MOIC, cash-on-cash returns |
| Executive Summary | Deal overview metrics |
| Cash Flow | Year-by-year projected cash flows |
| Tables & Graphics (IC Memo) | Investment committee presentation data |
| Error Checker | Model integrity checks |
| Rent Comp | Comparable property rents |
| Sale Comp | Comparable sales transactions |

---

## 3. Tier Confidence Assessment

### Actual Confidence Values (from code)

**File:** `backend/app/extraction/reference_mapper.py`, `_find_best_match()` (lines 192-299)

| Tier | Match Type | Confidence | Below 0.85 Threshold? | Manual Review Required? |
|------|-----------|------------|----------------------|------------------------|
| 1a | Sheet + label match | 0.95 | No | No |
| 1b | Sheet match, no label | 0.85 | **Borderline** | **Yes — cell position assumed** |
| 2 | Cross-sheet label match | 0.70 | **Yes** | **Yes — wrong sheet assumed** |
| 3 | 3-word prefix label match | 0.50 | **Yes** | **Yes — may match wrong field** |
| 4 | Synonym match | 0.40 | **Yes** | **Yes — semantic guess** |

### CRITICAL FLAGS: Fields Below 0.85 Confidence

**All Tier 2, 3, and 4 matches require manual review.**

Additionally, Tier 1b (0.85) should be flagged because:
- The sheet exists but the description label was **not found** in that sheet
- The production cell address is used as-is, with no verification that the cell still contains the expected data
- This is the most insidious failure mode: the extraction "succeeds" but may read from the wrong cell

### Risk Matrix

| Tier | Risk Level | Failure Mode |
|------|-----------|--------------|
| 1a (0.95) | Low | Only fails if template is fundamentally different |
| 1b (0.85) | **Medium** | Cell may have shifted within the sheet — silent wrong data |
| 2 (0.70) | **High** | Cell address from sheet A applied to sheet B — likely wrong data |
| 3 (0.50) | **Very High** | Partial text match may connect unrelated fields |
| 4 (0.40) | **Very High** | Synonym database doesn't exist, so this tier is inoperative |

---

## 4. Tier Distribution Across Completed Groups

### Initial Production Run (13 files)

The initial extraction used the canonical reference file directly, so all mappings are effectively Tier 1a (0.95) — the reference file was built from the same template family.

### Deferred Groups (9 groups, 66 files)

The 9 deferred groups (1, 7, 9, 14, 15, 17, 20, 21, 23) used `auto_map_group()` which produces per-group tier distributions stored in `reference_mapping.json` files under each group directory.

Expected distribution pattern (based on pipeline architecture):
- Majority of fields: Tier 1a/1b (template families share most sheet names)
- Some fields: Tier 2 (sheets renamed across template eras)
- Few fields: Tier 3 (partial matches -- high false positive risk)
- Zero fields: Tier 4 (no `field_synonyms.json` file exists)

### Per-Group Reference Mapping Artifacts

Each completed group has mapping data at:
```
backend/data/extraction_groups/{group_name}/reference_mapping.json
```

These files contain `tier_counts`, `overall_confidence`, `unmapped_fields`, and per-field `MappingMatch` records.

---

## 5. Unmapped Fields

### Definition

A field is "unmapped" when `_find_best_match()` returns `None` — no tier match was found. These fields are listed in `GroupReferenceMapping.unmapped_fields`.

### Causes of Unmapped Fields

| Cause | Likelihood | Example |
|-------|-----------|---------|
| Sheet completely absent from template | High | New template family missing "Cash Flow" sheet |
| Label text changed entirely | Medium | "Net Operating Income" renamed to "NOI" without synonym |
| Description has < 3 words | Medium | Short field labels can't trigger Tier 3 prefix matching |
| Template from a different underwriting platform | Low | Non-B&R model with totally different structure |

### Impact

Unmapped fields produce **no extracted value** for that property. If a critical financial metric (e.g., GOING_IN_CAP_RATE) is unmapped, the dashboard shows N/A for that deal.

---

## 6. Discovery Document Correction

The Phase 1 discovery document (`04-etl-mapping.md`) describes the tiers as:

| Tier | Discovery Doc Says | Actual Code |
|------|-------------------|-------------|
| 1 | 0.95, Same sheet + same cell | Correct for 1a; 1b is 0.85 with no label match |
| 2 | 0.85, Same sheet + same label at different cell | **Wrong** — actual is 0.70, label in different sheet |
| 3 | 0.70, Different sheet + same label | **Wrong** — actual is 0.50, 3-word prefix match |
| 4 | 0.40-0.50, Synonym | Partially correct — always 0.40, and inoperative (no synonyms file) |

This mismatch means the discovery document overstates the confidence of Tier 2 and Tier 3 matches. Tier 2 (0.70) is actually what the discovery doc calls Tier 3, and the real Tier 3 (partial prefix match at 0.50) is undocumented.

---

## 7. Synonym System Status

### `field_synonyms.json`

- **Does not exist** in the repository
- The `auto_map_group()` function accepts `synonyms: dict[str, list[str]] | None = None`
- When `None` (which it always is), Tier 4 matching is skipped
- **Impact**: Any fields that require semantic equivalence (e.g., "Cap Rate" vs "Going-In Cap Rate") will be unmapped

### Recommendation

Creating `field_synonyms.json` with known B&R Capital field aliases would activate Tier 4 matching and potentially resolve some currently unmapped fields. However, given the 0.40 confidence level, all Tier 4 matches would still require manual verification.

---

## 8. Mapping Quality Summary

| Aspect | Status | Risk |
|--------|--------|------|
| Canonical reference file (~1,179 mappings) | Healthy | Low — well-structured |
| Tier 1a matches (0.95) | Reliable | Low |
| Tier 1b matches (0.85) | **Needs review** | Medium — cell position assumed |
| Tier 2 matches (0.70) | **Needs review** | High — cross-sheet assumption |
| Tier 3 matches (0.50) | **Needs review** | Very High — prefix match unreliable |
| Tier 4 matches (0.40) | Inoperative | N/A — no synonyms file |
| Duplicate field name handling | Fragile | Medium — row-order dependent |
| Error category tracking | Broken | High — never populated in production |
| Unmapped field visibility | Present | Low — tracked in GroupReferenceMapping |
