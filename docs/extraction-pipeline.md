# Extraction Pipeline System

> Data flow from Excel UW models through extraction, enrichment, and into the dashboard API.

## Architecture Overview

```
Excel UW Models (.xlsb/.xlsx)
    |
    v
[1. Discovery] --- scan monitored directories, register files
    |
    v
[2. Fingerprinting] --- structural hash of sheets, rows, columns
    |
    v
[3. Grouping] --- cluster files by template similarity (>=95% same, 80-95% sub-variant)
    |
    v
[4. Extraction] --- read cell values using CellMapping + per-group field remaps
    |
    v
[5. Validation] --- domain checks, reconciliation, output quality
    |
    v
[6. Enrichment] --- map extracted_values -> properties table + financial_data JSON
    |
    v
[7. Dashboard API] --- _property_transforms.py shapes data for frontend
```

### Key Files

| Module | Path | Purpose |
|--------|------|---------|
| GroupExtractionPipeline | `backend/app/extraction/group_pipeline.py` | Pipeline orchestrator |
| ExcelDataExtractor | `backend/app/extraction/extractor.py` | Reads cells from .xlsb/.xlsx |
| CellMappingParser | `backend/app/extraction/cell_mapping.py` | Parses reference cell table |
| Fingerprinter | `backend/app/extraction/fingerprint.py` | Structural hashing |
| Grouping | `backend/app/extraction/grouping.py` | Template clustering |
| Enrichment | `backend/app/services/enrichment.py` | Maps extracted values to properties |
| Domain Validators | `backend/app/extraction/domain_validators.py` | Flags implausible values |
| Reconciliation | `backend/app/extraction/reconciliation_checks.py` | Cross-field consistency (NOI = Rev - OpEx) |
| Output Validation | `backend/app/extraction/output_validation.py` | Phoenix MSA range checks |
| Schema Drift | `backend/app/extraction/schema_drift.py` | Detects template structural changes |
| Reference Mapper | `backend/app/extraction/reference_mapper.py` | 4-tier auto-matching for variant layouts |

---

## Cell Mappings

Cell mappings define which Excel cell contains which financial field. They are parsed from a reference Excel file's "UW Model - Cell Reference Table" sheet by `CellMappingParser`.

Each mapping is a `CellMapping` dataclass:

```python
@dataclass
class CellMapping:
    category: str       # e.g., "Acquisition", "Financing"
    description: str    # Human-readable label
    sheet_name: str     # Target sheet in UW model (e.g., "Assumptions (Summary)")
    cell_address: str   # e.g., "D387", "I47"
    field_name: str     # Canonical DB field name (e.g., "PURCHASE_PRICE")
```

The reference file defines ~1,179 mappings spanning: unit mix, acquisition, financing, returns, operations, and multi-year cashflows.

---

## Group Management

### How Groups Form

Groups are created by an automatic clustering algorithm:

1. **Fingerprint** each Excel file (sheet names, header labels, populated cell count)
2. **Cluster** by sorted sheet name signatures
3. **Score** pairwise structural overlap (Jaccard-like on headers + column-A labels)
4. **Assign**: >=95% overlap = same group, 80-95% = sub-variant, <80% = separate group

Groups are stored in `backend/data/extraction_groups/groups.json` (not in the database).

### Group Directory Structure

```
backend/data/extraction_groups/
  config.json              # Pipeline state and timestamps
  groups.json              # All group definitions + file assignments
  field_remaps.json        # Per-group cell address overrides
  fingerprints.json        # Structural fingerprints
  group_1/                 # Per-group artifacts
    reference_mapping.json # Cell mappings for this group
    variances.json         # Detected structural variances
    dry_run_report.json    # Last dry-run results
  group_26/
    ...
  group_cabana_tempe/      # Custom group for older template variant
    reference_mapping.json
```

### Creating a New Group

1. Edit `groups.json` -- move files from their current group into a new group entry
2. Create the group directory under `data/extraction_groups/{group_name}/`
3. Copy `reference_mapping.json` from the source group (if same base template)
4. Add field remaps in `field_remaps.json` for any cell address differences
5. Run extraction: `pipeline.run_group_extraction(db, "group_name", dry_run=False)`

---

## Field Remaps

When a group's UW model template has fields at different cell addresses than the production reference, **field remaps** adjust the mapping at extraction time without modifying the base reference.

Remaps are stored in `backend/data/extraction_groups/field_remaps.json`:

```json
{
  "group_cabana_tempe": {
    "file": "Older template variant (2022 acquisitions)",
    "remaps": {
      "CAP_RATE": {
        "prod_cell": "Q30",
        "group_cell": "D28",
        "type": "column_and_row_shift",
        "reason": "Q30 is empty; going-in cap rate at D28"
      },
      "NET_OPERATING_INCOME_YEAR_1": {
        "prod_cell": "I43",
        "group_cell": "I47",
        "offset": 4,
        "type": "section_shift",
        "reason": "Row 43 = Admin/Legal expense; NOI at row 47"
      },
      "TOTAL_SF": {
        "prod_cell": "J31",
        "group_cell": "G8",
        "group_sheet": "Assumptions (Summary)",
        "type": "sheet_and_cell_shift",
        "reason": "Not on Property sheet; Total NRSF at G8 on Assumptions (Summary)"
      }
    }
  }
}
```

### Remap Capabilities

| Type | Description | Example |
|------|-------------|---------|
| Row offset | Same column, different row | I43 -> I47 (offset +4) |
| Column + row | Different column and row | Q30 -> D28 |
| Cross-sheet | Different sheet entirely | Property:J31 -> Assumptions (Summary):G8 |

Remaps are applied by `_apply_field_remaps()` in `GroupExtractionPipeline` via deep-copy of `CellMapping` objects before extraction begins. The `group_sheet` key (optional) overrides `CellMapping.sheet_name`.

---

## Enrichment: Extracted Values to Dashboard

### Field Aliases

The extraction pipeline stores values using descriptive field names from UW templates (e.g., `NET_OPERATING_INCOME`), but the enrichment service uses canonical abbreviated names (e.g., `NOI`). The `FIELD_ALIASES` dict bridges this gap:

| Extraction Name | Canonical Name |
|-----------------|---------------|
| `NET_OPERATING_INCOME` | `NOI` |
| `CAP_RATE` | `GOING_IN_CAP_RATE` |
| `AVERAGE_RENT_PER_UNIT_INPLACE` | `AVG_RENT_PER_UNIT` |
| `AVERAGE_RENT_PER_UNIT_MARKET` | `AVG_RENT_PER_UNIT` |
| `AVERAGE_RENT_PER_SF_INPLACE` | `AVG_RENT_PER_SF` |
| `AVERAGE_RENT_PER_SF_MARKET` | `AVG_RENT_PER_SF` |
| `VACANCY_LOSS` | `VACANCY_RATE` |
| `TOTAL_OPERATING_EXPENSES` | `TOTAL_EXPENSES` |

Alias resolution is additive (original key preserved) and canonical-first (if both `NOI` and `NET_OPERATING_INCOME` exist, `NOI` wins).

### Overwrite Strategy

Enrichment **always overwrites** property columns with the latest extraction data. If a newer extraction provides a concrete (non-None) value, it replaces the existing value -- even if the column was already populated. This ensures bad early extractions are corrected by subsequent runs.

Safeguards:
- NULL extraction values do **not** blank out existing data
- No-op when new value equals old value (avoids unnecessary DB writes)
- All overwrites logged via loguru (`enrichment_overwrite` event) with property ID, column, old/new values

### Hydration Flow

```
extracted_values table
    |
    v
fetch_base_field_values() --- SQL query with ALL_HYDRATION_FIELDS + alias keys
    |
    v
resolve_field_aliases() --- copies alias keys to canonical keys
    |
    v
update_property_columns() --- writes to properties table columns
    |
    v
build_financial_data_json() --- builds/updates financial_data JSON column
    |
    v
_property_transforms.py --- shapes into nested frontend format (snake_case -> camelCase)
```

---

## Validation Pipeline

Three validation stages run after extraction (non-blocking -- warnings logged, extraction continues):

### Domain Validators
- Rules defined as `DomainRule(field_pattern, min, max, expected_type, description)`
- Types: numeric, percentage, currency, count, year
- Calibrated for Phoenix MSA Class B multifamily
- Flags implausible values with warnings

### Reconciliation Checks
- Cross-field consistency: NOI = Revenue - Operating Expenses
- Default tolerance: 5% relative difference
- Results stored as `ExtractionWarning` with `warning_type="reconciliation"`

### Output Validation
- Range checks against Phoenix MSA benchmarks
- Status enum: Error, Warning, Valid
- Results stored as `ExtractionWarning` with `warning_type="validation"`

### Schema Drift Detection
- Pre-extraction gate comparing file structure to baseline fingerprint
- Thresholds: >=0.95 OK, >=0.90 info, >=0.80 warning, <0.80 error (skip file)
- Results stored as `ExtractionWarning` with `warning_type="drift"`

---

## Recent Changes (April 2026)

### New Group: group_cabana_tempe
Created for Cabana on 99th and Tempe Metro -- 2022-era acquisitions with an older UW template variant where:
- CAP_RATE was at Q30 (empty) -- remapped to D28 (Market Cap Rate - Close)
- NOI_YEAR_1-5 were at row 43 (Admin/Legal expense line) -- remapped to row 47
- TOTAL_SF was missing -- mapped to G8 on Assumptions (Summary)

### Field Alias System
Added `FIELD_ALIASES` in `enrichment.py` to bridge extraction-side names to canonical enrichment names. Applied in three code paths: `enrichment.py` (async), `crud_property.py` (bulk), `crud/extraction.py` (sync hydration).

### Enrichment Overwrite Logic
Removed all "only fill when empty" guards. Enrichment now always writes the latest extraction value, logging overwrites for auditability. Prevents stale data from early bad extractions persisting indefinitely.

### Data Cleanup
- Soft-deleted 3 garbage properties (template placeholders, NullValue parse errors)
- Fixed 5 property names with `[City]` placeholder suffixes
- Nulled bad `total_units` for 12 properties where extraction grabbed wrong cells
- Cleared 118 placeholder `[Market (MSA)]` values and 100 `[Submarket]` values

---

## Running Extraction

### Single Group
```python
from app.db.session import SessionLocal
from app.extraction.group_pipeline import GroupExtractionPipeline

pipeline = GroupExtractionPipeline()
db = SessionLocal()

# Dry run (no DB writes)
result = pipeline.run_group_extraction(db, "group_cabana_tempe", dry_run=True)

# Live run (writes to DB + runs hydration)
result = pipeline.run_group_extraction(db, "group_cabana_tempe", dry_run=False)
db.commit()
db.close()
```

### Full Batch (all groups)
Orchestrated by `group_pipeline.py` via the extraction scheduler or manual trigger through the API.

### Scheduled Extraction
Configured via environment variables:
- `EXTRACTION_SCHEDULE_ENABLED` (default: false)
- `EXTRACTION_SCHEDULE_CRON` (default: `0 2 * * 1` -- Monday 2 AM)
- `EXTRACTION_SCHEDULE_TIMEZONE` (default: America/Phoenix)
