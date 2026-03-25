# WS4 Deliverable 4: Validation Framework Design

**Workstream:** WS4 — Data Completeness & Mapping Integrity
**Date:** 2026-03-25

---

## 1. Design Principles

1. **Fail loud, not silent**: Every validation failure must be categorized and persisted
2. **Domain-aware**: Validation rules encode B&R Capital's multifamily underwriting domain knowledge
3. **Layered**: Row-level, batch-level, and schema-level checks operate independently
4. **Non-blocking**: Validation failures should flag issues, not prevent extraction
5. **Testable**: Every rule must be unit-testable with known-good and known-bad inputs

---

## 2. Row-Level Validation

### 2.1 Pydantic Model for Extracted Values

**Proposed location:** `backend/app/extraction/value_validators.py`

```python
from pydantic import BaseModel, field_validator, model_validator
from decimal import Decimal
from datetime import date
from typing import Optional


class ExtractedValueValidation(BaseModel):
    """Validates a single extracted value before database insertion."""

    field_name: str
    field_category: str | None = None
    value_text: str | None = None
    value_numeric: Decimal | None = None
    value_date: date | None = None
    is_error: bool = False
    error_category: str | None = None

    @field_validator("value_numeric")
    @classmethod
    def numeric_must_be_finite(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and (v != v or abs(v) > Decimal("9999999999999999.9999")):
            raise ValueError(f"Numeric value out of range: {v}")
        return v

    @model_validator(mode="after")
    def error_requires_category(self) -> "ExtractedValueValidation":
        if self.is_error and not self.error_category:
            raise ValueError("is_error=True requires error_category")
        return self
```

### 2.2 Financial Domain Range Checks

**Proposed location:** `backend/app/extraction/domain_validators.py`

| Field Pattern | Valid Range | Rationale |
|---------------|-----------|-----------|
| `*CAP_RATE*` | 0.0 -- 25.0 (%) | Cap rates above 25% are implausible for multifamily |
| `*IRR*` | -100.0 -- 200.0 (%) | IRR beyond +/-200% indicates model error |
| `*MOIC*`, `*EQUITY_MULTIPLE*` | 0.0 -- 10.0 (x) | 10x equity multiple is extreme |
| `*DSCR*` | 0.0 -- 5.0 | DSCR above 5x is unusual |
| `*OCCUPANCY*` | 0.0 -- 100.0 (%) | Physical occupancy percentage |
| `*VACANCY*` | 0.0 -- 100.0 (%) | Vacancy percentage |
| `*PURCHASE_PRICE*`, `*ASKING_PRICE*` | >= 0 | No negative prices |
| `*LOAN_AMOUNT*` | >= 0 | No negative loan amounts |
| `*LTV*` | 0.0 -- 100.0 (%) | Loan-to-value ratio |
| `*RENT*` | >= 0 | No negative rents |
| `*NOI*` | No constraint | NOI can be negative (distressed property) |
| `*HOLD_PERIOD*` | 1 -- 30 (years) | Typical hold period range |
| `*YEAR_BUILT*` | 1900 -- 2030 | Reasonable construction year |
| `*TOTAL_UNITS*` | 1 -- 10000 | B&R targets 100+ but allow range |
| `*TOTAL_SF*` | > 0 | Must be positive |

### Implementation

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class RangeRule:
    pattern: str      # fnmatch-style pattern for field_name
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    unit: str = ""    # For documentation: "%", "x", "$", "years"


DOMAIN_RULES: list[RangeRule] = [
    RangeRule("*CAP_RATE*", Decimal("0"), Decimal("25"), "%"),
    RangeRule("*IRR*", Decimal("-100"), Decimal("200"), "%"),
    RangeRule("*MOIC*", Decimal("0"), Decimal("10"), "x"),
    RangeRule("*EQUITY_MULTIPLE*", Decimal("0"), Decimal("10"), "x"),
    RangeRule("*DSCR*", Decimal("0"), Decimal("5"), ""),
    RangeRule("*OCCUPANCY*", Decimal("0"), Decimal("100"), "%"),
    RangeRule("*VACANCY*", Decimal("0"), Decimal("100"), "%"),
    RangeRule("*PURCHASE_PRICE*", Decimal("0"), None, "$"),
    RangeRule("*ASKING_PRICE*", Decimal("0"), None, "$"),
    RangeRule("*LOAN_AMOUNT*", Decimal("0"), None, "$"),
    RangeRule("*LTV*", Decimal("0"), Decimal("100"), "%"),
    RangeRule("*RENT*", Decimal("0"), None, "$"),
    RangeRule("*HOLD_PERIOD*", Decimal("1"), Decimal("30"), "years"),
    RangeRule("*YEAR_BUILT*", Decimal("1900"), Decimal("2030"), ""),
    RangeRule("*TOTAL_UNITS*", Decimal("1"), Decimal("10000"), ""),
    RangeRule("*TOTAL_SF*", Decimal("1"), None, "sf"),
]


def validate_domain_range(
    field_name: str,
    value_numeric: Decimal | None,
) -> tuple[bool, str | None]:
    """
    Validate a numeric value against domain rules.

    Returns:
        (is_valid, error_message)
    """
    if value_numeric is None:
        return True, None

    import fnmatch
    for rule in DOMAIN_RULES:
        if fnmatch.fnmatch(field_name, rule.pattern):
            if rule.min_value is not None and value_numeric < rule.min_value:
                return False, (
                    f"{field_name}={value_numeric} below minimum "
                    f"{rule.min_value}{rule.unit}"
                )
            if rule.max_value is not None and value_numeric > rule.max_value:
                return False, (
                    f"{field_name}={value_numeric} above maximum "
                    f"{rule.max_value}{rule.unit}"
                )
    return True, None
```

### 2.3 Type Validation

| Expected Type | Check | Error Category |
|--------------|-------|----------------|
| Numeric field with text value | `value_numeric is None AND value_text is not None AND value_text not in missing_indicators` | `data_type_error` |
| Date field with numeric value | `value_date is None AND value_numeric is not None` | `data_type_error` |
| Percentage stored as decimal > 1 | `field matches *_RATE and value > 1.0` | `data_type_error` (possible 0.05 vs 5% confusion) |

---

## 3. Batch-Level Validation

### 3.1 Before/After Record Counts

After each extraction run, validate:

```python
@dataclass
class BatchValidation:
    extraction_run_id: UUID
    files_expected: int     # files_discovered from ExtractionRun
    files_processed: int    # files_processed from ExtractionRun
    values_expected: int    # files_processed * avg_fields_per_file
    values_actual: int      # COUNT(*) from extracted_values for this run
    missing_properties: list[str]  # Properties with 0 values
    sparse_properties: list[str]   # Properties with < 50% of expected fields
```

### 3.2 Sum-of-Amounts Reconciliation

For groups of related financial fields, validate internal consistency:

| Reconciliation Rule | Formula | Tolerance |
|---------------------|---------|-----------|
| Revenue = EGI + Vacancy + Concessions | `EGI = GPR - Vacancy - Concessions` | 1% |
| NOI = Revenue - OpEx | `NOI = EGI - Total_OpEx` | 1% |
| DSCR = NOI / ADS | `DSCR = NOI / Annual_Debt_Service` | 5% |
| Cap Rate = NOI / Price | `Cap_Rate = NOI / Purchase_Price` | 5% |
| LTV = Loan / Price | `LTV = Loan_Amount / Purchase_Price` | 1% |

### 3.3 Cross-Property Sanity Checks

| Check | Threshold | Alert |
|-------|-----------|-------|
| Cap rate outlier | > 2 std dev from group mean | Warning |
| Purchase price outlier | > 3x or < 0.33x group median | Warning |
| NOI negative | Any property | Info (may be valid for distressed assets) |
| 0.0% cap rate | Any property | Warning (likely missing data, not truly zero) |
| 0.0% occupancy | Any property | Error (likely missing data) |

### 3.4 Run-over-Run Comparison

Compare current run against previous run for same property:

| Check | Threshold | Alert |
|-------|-----------|-------|
| Value changed > 50% | Any financial field | Warning — investigate |
| New fields appeared | Count > 10% of total | Info — template may have changed |
| Fields disappeared | Count > 10% of total | Warning — possible template regression |
| Total values decreased > 20% | Per property | Error — extraction degradation |

---

## 4. Schema Drift Detection

### 4.1 Template Structure Monitoring

**Purpose**: Detect when an Excel template's structure changes (sheets renamed, rows inserted, columns shifted).

### Architecture

```
On each extraction run:
  1. Fingerprint the file → SheetFingerprint
  2. Compare against stored fingerprint for the same group
  3. If structural overlap < threshold → ALERT
```

### Implementation

```python
@dataclass
class DriftAlert:
    file_path: str
    group_name: str
    drift_type: str         # "sheet_renamed", "sheet_added", "sheet_removed",
                            # "structure_changed"
    previous_signature: str
    current_signature: str
    overlap_score: float
    affected_fields: list[str]
    detected_at: datetime


class SchemaDriftDetector:
    """Detects structural changes in UW model templates."""

    DRIFT_THRESHOLD = 0.90  # Below this overlap → alert

    def check_drift(
        self,
        current_fp: FileFingerprint,
        baseline_fp: FileFingerprint,
        group_name: str,
    ) -> DriftAlert | None:
        """Compare current fingerprint against baseline."""
        overlap = compute_structural_overlap(current_fp, baseline_fp)

        if overlap >= self.DRIFT_THRESHOLD:
            return None

        # Determine drift type
        current_sheets = {s.name for s in current_fp.sheets}
        baseline_sheets = {s.name for s in baseline_fp.sheets}

        if current_sheets - baseline_sheets:
            drift_type = "sheet_added"
        elif baseline_sheets - current_sheets:
            drift_type = "sheet_removed"
        else:
            drift_type = "structure_changed"

        return DriftAlert(
            file_path=current_fp.file_path,
            group_name=group_name,
            drift_type=drift_type,
            previous_signature=baseline_fp.combined_signature,
            current_signature=current_fp.combined_signature,
            overlap_score=overlap,
            affected_fields=[],  # Populated by cross-referencing mappings
            detected_at=datetime.now(UTC),
        )
```

### 4.2 Baseline Storage

Store the baseline fingerprint for each group (first extraction or last verified-good extraction) in:
```
backend/data/extraction_groups/{group_name}/baseline_fingerprint.json
```

### 4.3 Alert Actions

| Overlap | Action |
|---------|--------|
| >= 0.95 | No action — normal variation |
| 0.90 - 0.94 | Info log — minor structural change |
| 0.80 - 0.89 | Warning — review mapping accuracy for affected fields |
| < 0.80 | Error — halt extraction for this group, require manual review |

---

## 5. Integration Points

### 5.1 Where Validation Hooks In

```
extractor.py → extract_from_file()
  ↓
  Row-level: validate each value before insertion
  ↓
crud/extraction.py → bulk_insert()
  ↓
  Batch-level: post-insertion reconciliation
  ↓
group_pipeline.py → run_extraction()
  ↓
  Schema drift: pre-extraction fingerprint comparison
```

### 5.2 Validation Result Storage

| Result Type | Storage Location | Queryable? |
|-------------|-----------------|------------|
| Row validation failures | `extracted_values.error_category` | Yes (SQL) |
| Domain range violations | New: `extracted_values.validation_flags` (JSON) | Yes (JSON query) |
| Batch reconciliation | `extraction_runs.error_summary` (JSON) | Yes (JSON query) |
| Schema drift alerts | New: `schema_drift_alerts` table | Yes (SQL) |

### 5.3 Proposed `schema_drift_alerts` Table

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `extraction_run_id` | UUID FK | Run that detected the drift |
| `group_name` | String | Affected group |
| `file_path` | String | Affected file |
| `drift_type` | String | Type of structural change |
| `overlap_score` | Numeric | Structural similarity score |
| `previous_signature` | Text | Baseline fingerprint signature |
| `current_signature` | Text | Current fingerprint signature |
| `resolved_at` | DateTime | When the alert was acknowledged/resolved |
| `resolution_notes` | Text | How the drift was handled |

---

## 6. Testing Strategy

### Unit Tests

| Test Category | Count | Description |
|---------------|-------|-------------|
| Range rules | ~30 | Each DOMAIN_RULES entry with boundary, within, and out-of-range values |
| Type validation | ~10 | Numeric/date/text type mismatches |
| Null handling | ~10 | Empty, N/A, TBD, None, NaN edge cases |
| Batch reconciliation | ~10 | Sum-of-amounts formulas with tolerance |
| Schema drift | ~10 | Overlap thresholds and alert generation |

### Integration Tests

| Test | Description |
|------|-------------|
| End-to-end extraction with validation | Run extraction and verify all validation outputs |
| Regression test with known-good file | Extract from canonical file, compare against known values |
| Drift detection with modified template | Modify a template, verify drift alert fires |
| Cross-run comparison | Extract twice, verify delta detection works |

---

## 7. Financial Domain Constraints Reference

### B&R Capital Multifamily Specifics

| Metric | Typical Range | Alert Threshold | Notes |
|--------|-------------|----------------|-------|
| Cap Rate (Going-In) | 4% - 9% | < 3% or > 12% | Phoenix MSA Class B multifamily |
| IRR (Levered) | 10% - 25% | < 0% or > 40% | Negative = distressed deal |
| IRR (Unlevered) | 5% - 15% | < -5% or > 25% | |
| MOIC (LP) | 1.5x - 3.0x | < 1.0x or > 5.0x | Below 1.0x = loss |
| DSCR | 1.2 - 2.5 | < 1.0 or > 4.0 | Below 1.0 = insufficient debt coverage |
| Occupancy | 85% - 98% | < 70% or > 100% | |
| Hold Period | 3 - 10 years | < 1 or > 20 | |
| Purchase Price / Unit | $50K - $300K | < $30K or > $500K | Phoenix MSA range |
| NOI / Unit | $3K - $15K | < $0 or > $25K | Annual per unit |
| Rent / Unit | $700 - $2,500 | < $400 or > $4,000 | Monthly |
| Year Built | 1970 - 2000 | < 1950 or > 2025 | Class B vintage target |
| Total Units | 100 - 500 | < 50 or > 1,000 | B&R targets 100+ |
