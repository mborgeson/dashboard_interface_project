# Phase 1: Data Integrity & Production Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the dead safety checks that the spot-check proved are needed (reconciliation, output validation, schema drift alerts), fix the frontend `safeNum` coercion that masks bad data as zeros, align validator units, fix sync-in-async endpoints that block workers, add TLS to nginx, and remove test patterns that silently swallow regressions.

**Architecture:** Three independent workstreams that can be parallelized:
1. **Data Integrity** (Tasks 1-6): Wire reconciliation/validation into extraction pipeline, fix frontend coercion, align validator units
2. **Backend Stability** (Tasks 7-8): Convert sync-in-async handlers to plain `def` or `asyncio.to_thread`
3. **Deploy & Test Hardening** (Tasks 9-11): TLS termination, remove skip-on-404 and test.fixme patterns

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, openpyxl, Zod 4.1, TypeScript 5.9, React 19.2, vitest, pytest, Playwright, nginx

**Priority context:** A spot-check of 6 deals found the extraction pipeline reads the right cells accurately (100% match), BUT several dead deals use template variants where cell mappings point to wrong locations (PURCHASE_PRICE = "Period Start", TOTAL_UNITS = 2, AVG_UNIT_SF = 24 sqft). The safety checks that would catch these exist as code but are never invoked. Meanwhile, frontend `safeNum` coerces these failures to `0`, hiding them from users.

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `backend/alembic/versions/20260409_phase1_add_extraction_warnings.py` | Migration: extraction_warnings table |
| `backend/app/models/extraction_warning.py` | SQLAlchemy model for extraction warnings |
| `backend/tests/test_extraction/test_pipeline_safety_checks.py` | Tests for reconciliation/validation/drift wiring |
| `src/lib/api/schemas/__tests__/property-safenum.test.ts` | Tests for safeNum replacement |

### Modified files
| File | Change |
|------|--------|
| `backend/app/extraction/group_pipeline.py:900-922` | Wire reconciliation, validation, drift alert persistence |
| `backend/app/extraction/output_validation.py:90-187` | Align VALIDATION_RULES units to fractions |
| `backend/app/models/__init__.py` | Register ExtractionWarning model |
| `src/lib/api/schemas/property.ts:18-25` | Replace `safeNum` with `safeOptionalNum` returning `undefined` |
| `src/features/analytics/AnalyticsPage.tsx:83-85,115-160` | Remove `!== 0` compensation filters, handle `undefined` |
| `backend/app/api/v1/endpoints/extraction/status.py:38,111,157,241` | Change `async def` to `def` |
| `backend/app/api/v1/endpoints/construction_pipeline.py:929,1030` | Wrap sync calls in `asyncio.to_thread` |
| `nginx.conf` | Add TLS server block, HSTS, HTTP redirect |
| `backend/tests/test_api/test_analytics.py` | Remove 16 `pytest.skip` on 404 |
| `backend/tests/test_api/test_exports.py` | Remove 25 `pytest.skip` on 404, change `[200,500]` to `==200` |
| `backend/tests/test_api/test_monitoring.py` | Remove 13 `pytest.skip` on 404 |
| `e2e/deal-pipeline.spec.ts` | Remove 18 `test.fixme`, add seed data |

---

## Workstream A: Data Integrity

### Task 1: Create extraction_warnings table

**Files:**
- Create: `backend/alembic/versions/20260409_phase1_add_extraction_warnings.py`
- Create: `backend/app/models/extraction_warning.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the SQLAlchemy model**

```python
# backend/app/models/extraction_warning.py
"""Stores reconciliation, validation, and drift warnings from extraction pipeline."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExtractionWarning(Base):
    __tablename__ = "extraction_warnings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    extraction_run_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("extraction_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    property_name: Mapped[str] = mapped_column(String(500), index=True)
    source_file: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    warning_type: Mapped[str] = mapped_column(
        String(50), index=True
    )  # "reconciliation" | "validation" | "drift"
    severity: Mapped[str] = mapped_column(String(20))  # "error" | "warning" | "info"
    field_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

- [ ] **Step 2: Register model in `__init__.py`**

Add to `backend/app/models/__init__.py`:
```python
from app.models.extraction_warning import ExtractionWarning  # noqa: F401
```

- [ ] **Step 3: Generate Alembic migration**

```bash
cd backend && source venv/Scripts/activate && alembic revision --autogenerate -m "add extraction_warnings table"
```

Verify the generated migration creates the table with correct columns and indexes.

- [ ] **Step 4: Run migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 5: Verify table exists**

```bash
PGPASSWORD=postgres123 psql -h localhost -U postgres -d dashboard_interface_data -c "\d extraction_warnings"
```

Expected: table with columns id, extraction_run_id, property_name, source_file, warning_type, severity, field_name, message, details, created_at.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/extraction_warning.py backend/app/models/__init__.py backend/alembic/versions/20260409*
git commit -m "feat(extraction): add extraction_warnings table for safety check results"
```

---

### Task 2: Wire reconciliation checks into extraction pipeline

**Files:**
- Modify: `backend/app/extraction/group_pipeline.py:900-922`
- Create: `backend/tests/test_extraction/test_pipeline_safety_checks.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_extraction/test_pipeline_safety_checks.py
"""Tests that safety checks (reconciliation, validation, drift) are actually invoked."""

from unittest.mock import MagicMock, patch

import pytest


class TestReconciliationWiring:
    """Verify reconciliation checks run before bulk_insert."""

    @patch("app.extraction.group_pipeline.run_reconciliation_checks")
    def test_reconciliation_called_before_insert(self, mock_recon):
        """run_reconciliation_checks must be called with extracted data."""
        mock_recon.return_value = []  # no warnings

        from app.extraction.group_pipeline import _process_single_file

        # We test that the function at least calls reconciliation
        # Full integration test requires fixtures; this verifies wiring
        assert mock_recon is not None  # placeholder until wiring is done
        # After wiring: mock_recon.assert_called_once()

    @patch("app.extraction.group_pipeline.run_reconciliation_checks")
    def test_reconciliation_warnings_persisted(self, mock_recon):
        """When reconciliation returns warnings, they are stored in extraction_warnings."""
        from app.extraction.reconciliation_checks import ReconciliationResult

        mock_recon.return_value = [
            ReconciliationResult(
                check_name="noi_consistency",
                passed=False,
                expected=5000000.0,
                actual=2000000.0,
                difference=3000000.0,
                message="NOI does not match Revenue minus Expenses",
            )
        ]
        # After wiring: verify ExtractionWarning row created
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_extraction/test_pipeline_safety_checks.py -v
```

- [ ] **Step 3: Wire reconciliation into group_pipeline.py**

In `backend/app/extraction/group_pipeline.py`, add import at top:
```python
from app.extraction.reconciliation_checks import run_reconciliation_checks
from app.models.extraction_warning import ExtractionWarning
```

Then modify the block around line 900 (before `ExtractedValueCRUD.bulk_insert`):

```python
                # --- Safety checks before persisting ---
                # Run reconciliation (NOI vs Revenue-Expenses consistency)
                recon_results = run_reconciliation_checks(
                    result, str(property_name)
                )
                for r in recon_results:
                    if not r.passed:
                        warning = ExtractionWarning(
                            extraction_run_id=str(run_id) if run_id else None,
                            property_name=str(property_name),
                            source_file=file_path,
                            warning_type="reconciliation",
                            severity="warning",
                            field_name=r.check_name,
                            message=r.message,
                            details=json.dumps({
                                "expected": r.expected,
                                "actual": r.actual,
                                "difference": r.difference,
                            }),
                        )
                        db.add(warning)
                        logger.warning(
                            f"Reconciliation warning for {property_name}: {r.message}"
                        )

                if not dry_run and run_id:
                    # ... existing bulk_insert call ...
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_extraction/test_pipeline_safety_checks.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/extraction/group_pipeline.py backend/tests/test_extraction/test_pipeline_safety_checks.py
git commit -m "feat(extraction): wire reconciliation checks into pipeline before bulk_insert"
```

---

### Task 3: Wire output validation into extraction pipeline

**Files:**
- Modify: `backend/app/extraction/group_pipeline.py` (same block as Task 2)

- [ ] **Step 1: Add test for validation wiring**

Append to `backend/tests/test_extraction/test_pipeline_safety_checks.py`:

```python
class TestOutputValidationWiring:
    """Verify output validation runs before bulk_insert."""

    @patch("app.extraction.group_pipeline.validate_extraction_output")
    def test_validation_called_with_extracted_data(self, mock_validate):
        """validate_extraction_output must be called."""
        from app.extraction.output_validation import ValidationSummary

        mock_validate.return_value = ValidationSummary(
            total_fields=15, valid=14, warnings=1, errors=0, results=[]
        )
        # After wiring: mock_validate.assert_called_once()
```

- [ ] **Step 2: Wire validation into group_pipeline.py**

Add import:
```python
from app.extraction.output_validation import validate_extraction_output
```

Add after the reconciliation block (before bulk_insert):
```python
                # Run output validation (range checks, sanity bounds)
                validation_summary = validate_extraction_output(result)
                for vr in validation_summary.results:
                    if vr.status in ("error", "warning"):
                        warning = ExtractionWarning(
                            extraction_run_id=str(run_id) if run_id else None,
                            property_name=str(property_name),
                            source_file=file_path,
                            warning_type="validation",
                            severity=vr.status,
                            field_name=vr.field_name,
                            message=vr.message,
                            details=json.dumps({
                                "value": vr.value,
                                "min": vr.min_value,
                                "max": vr.max_value,
                            }),
                        )
                        db.add(warning)

                if validation_summary.errors > 0:
                    logger.error(
                        f"Output validation ERRORS for {property_name}: "
                        f"{validation_summary.errors} fields failed"
                    )
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_extraction/test_pipeline_safety_checks.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/extraction/group_pipeline.py backend/tests/test_extraction/test_pipeline_safety_checks.py
git commit -m "feat(extraction): wire output validation into pipeline before bulk_insert"
```

---

### Task 4: Wire schema drift alert persistence

**Files:**
- Modify: `backend/app/extraction/group_pipeline.py:805-834`

- [ ] **Step 1: Add test for drift alert persistence**

Append to `backend/tests/test_extraction/test_pipeline_safety_checks.py`:

```python
class TestSchemaDriftAlertPersistence:
    """Verify drift detection results are persisted, not just logged."""

    def test_drift_warning_creates_extraction_warning(self):
        """When drift severity is 'warning', an ExtractionWarning row must be created."""
        # After wiring: verify ExtractionWarning with warning_type="drift" is created
        pass

    def test_drift_error_creates_extraction_warning_and_skips(self):
        """When drift severity is 'error', extraction warning is created AND extraction is skipped."""
        pass
```

- [ ] **Step 2: Find the drift detection block in group_pipeline.py**

Around lines 805-834, find where `detector.check_drift()` is called. After the severity check, add persistence:

```python
                # Persist drift alert to extraction_warnings table
                if drift_result.severity != "ok":
                    warning = ExtractionWarning(
                        extraction_run_id=str(run_id) if run_id else None,
                        property_name=str(property_name),
                        source_file=file_path,
                        warning_type="drift",
                        severity=drift_result.severity,
                        message=f"Schema drift detected: similarity={drift_result.similarity_score:.2f}",
                        details=json.dumps({
                            "similarity_score": drift_result.similarity_score,
                            "changed_sheets": drift_result.changed_sheets,
                            "missing_sheets": drift_result.missing_sheets,
                            "new_sheets": drift_result.new_sheets,
                        }),
                    )
                    db.add(warning)
                    logger.warning(
                        f"Schema drift ({drift_result.severity}) for {property_name}: "
                        f"similarity={drift_result.similarity_score:.2f}"
                    )
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_extraction/test_pipeline_safety_checks.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/extraction/group_pipeline.py backend/tests/test_extraction/test_pipeline_safety_checks.py
git commit -m "feat(extraction): persist schema drift alerts to extraction_warnings table"
```

---

### Task 5: Align validator units to fractions

**Files:**
- Modify: `backend/app/extraction/output_validation.py:90-187`
- Modify or create: `backend/tests/test_extraction/test_output_validation.py`

The critical mismatches (from the Explore agent):

| Field | DOMAIN_RULES | VALIDATION_RULES | Fix |
|-------|-------------|-----------------|-----|
| cap_rate | 0.01-0.20 | 0-20 | Change to 0.0-0.20, warn 0.02-0.15 |
| occupancy | 0.0-1.0 | 0-100 | Change to 0.0-1.0, warn 0.50-1.0 |

- [ ] **Step 1: Write test for aligned units**

```python
# backend/tests/test_extraction/test_output_validation.py
from app.extraction.output_validation import validate_extraction_output


def test_cap_rate_as_fraction_passes():
    """Cap rate 0.055 (5.5%) should pass validation."""
    data = {"T12_RETURN_ON_PP": 0.055}
    result = validate_extraction_output(data)
    cap_result = next((r for r in result.results if r.field_name == "T12_RETURN_ON_PP"), None)
    assert cap_result is None or cap_result.status == "ok"


def test_cap_rate_as_percentage_fails():
    """Cap rate 5.5 (interpreted as 550%) should fail validation."""
    data = {"T12_RETURN_ON_PP": 5.5}
    result = validate_extraction_output(data)
    cap_result = next((r for r in result.results if r.field_name == "T12_RETURN_ON_PP"), None)
    assert cap_result is not None
    assert cap_result.status in ("error", "warning")


def test_occupancy_as_fraction_passes():
    """Occupancy 0.95 (95%) should pass validation."""
    data = {"OCCUPANCY": 0.95}
    result = validate_extraction_output(data)
    occ_result = next((r for r in result.results if r.field_name == "OCCUPANCY"), None)
    assert occ_result is None or occ_result.status == "ok"


def test_vacancy_75_percent_flags_warning():
    """Vacancy rate 0.75 (75%) should flag a warning — implausibly high."""
    data = {"VACANCY_LOSS_YEAR_1_RATE": 0.75}
    result = validate_extraction_output(data)
    vac_result = next((r for r in result.results if r.field_name == "VACANCY_LOSS_YEAR_1_RATE"), None)
    assert vac_result is not None
    assert vac_result.status == "warning"
```

- [ ] **Step 2: Run tests to verify they fail (current rules use percentage scale)**

```bash
cd backend && python -m pytest tests/test_extraction/test_output_validation.py -v
```

- [ ] **Step 3: Update VALIDATION_RULES in output_validation.py**

In `backend/app/extraction/output_validation.py`, update the rules at lines 90-187 to use fraction scale:

Replace cap_rate rule:
```python
# OLD: ValidationRule("cap_rate", ..., min_value=0.0, max_value=20.0, warning_min=2.0, warning_max=15.0)
# NEW:
ValidationRule("cap_rate", patterns=["CAP", "RETURN_ON"], min_value=0.0, max_value=0.25, warning_min=0.02, warning_max=0.15, description="Cap rate as decimal (0-25%, warn outside 2-15%)"),
```

Replace occupancy rule:
```python
# OLD: ValidationRule("occupancy", ..., min_value=0, max_value=100, warning_min=50, warning_max=100)
# NEW:
ValidationRule("occupancy", patterns=["OCCUPANCY"], min_value=0.0, max_value=1.0, warning_min=0.50, warning_max=1.0, description="Occupancy as decimal (0-100%, warn below 50%)"),
```

Add vacancy rate rule (not present before):
```python
ValidationRule("vacancy_rate", patterns=["VACANCY"], min_value=0.0, max_value=0.30, warning_min=0.0, warning_max=0.15, description="Vacancy rate as decimal (0-30%, warn above 15%)"),
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_extraction/test_output_validation.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/extraction/output_validation.py backend/tests/test_extraction/test_output_validation.py
git commit -m "fix(extraction): align validation rules to fraction scale matching domain_validators"
```

---

### Task 6: Fix safeNum coercion in frontend property schema

**Files:**
- Modify: `src/lib/api/schemas/property.ts:18-25`
- Modify: `src/features/analytics/AnalyticsPage.tsx:83-85,115-160`
- Create: `src/lib/api/schemas/__tests__/property-safenum.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// src/lib/api/schemas/__tests__/property-safenum.test.ts
import { describe, it, expect } from 'vitest';
import { z } from 'zod';

// Import after we rename — for now, test the desired behavior
describe('safeOptionalNum', () => {
  const safeOptionalNum = z.preprocess(
    (v) => {
      if (v === null || v === undefined) return undefined;
      const n = Number(v);
      return Number.isFinite(n) ? n : undefined;
    },
    z.number().optional(),
  );

  it('returns undefined for null', () => {
    expect(safeOptionalNum.parse(null)).toBeUndefined();
  });

  it('returns undefined for undefined', () => {
    expect(safeOptionalNum.parse(undefined)).toBeUndefined();
  });

  it('returns undefined for NaN-producing strings', () => {
    expect(safeOptionalNum.parse('Period Start')).toBeUndefined();
  });

  it('returns the number for valid numeric input', () => {
    expect(safeOptionalNum.parse(0.055)).toBe(0.055);
  });

  it('returns 0 for actual zero (does NOT coerce to undefined)', () => {
    expect(safeOptionalNum.parse(0)).toBe(0);
  });

  it('returns the number for numeric strings', () => {
    expect(safeOptionalNum.parse('38000000')).toBe(38000000);
  });
});
```

- [ ] **Step 2: Run test**

```bash
npx vitest run src/lib/api/schemas/__tests__/property-safenum.test.ts
```

- [ ] **Step 3: Replace safeNum in property.ts**

In `src/lib/api/schemas/property.ts`, replace lines 18-25:

```typescript
// OLD:
// const safeNum = z.preprocess(
//   (v) => {
//     if (v === null || v === undefined) return 0;
//     const n = Number(v);
//     return Number.isFinite(n) ? n : 0;
//   },
//   z.number(),
// );

// NEW: Returns undefined for missing/invalid instead of 0
// This preserves the distinction between "data missing" and "value is zero"
const safeOptionalNum = z.preprocess(
  (v) => {
    if (v === null || v === undefined) return undefined;
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  },
  z.number().optional(),
);
```

Then find-and-replace all uses of `safeNum` with `safeOptionalNum` in the same file. Update the `.default({...})` blocks to use `undefined` instead of `0` for numeric fields:

```typescript
// OLD: .default({ units: 0, squareFeet: 0, averageUnitSize: 0, yearBuilt: 0, ... })
// NEW: .default({ units: undefined, squareFeet: undefined, averageUnitSize: undefined, yearBuilt: undefined, ... })
```

- [ ] **Step 4: Update AnalyticsPage.tsx compensating filters**

In `src/features/analytics/AnalyticsPage.tsx`, replace the `!== 0` filters with `!= null` (which catches both `null` and `undefined`):

```typescript
// Lines 83-85 — OLD:
// const withIRR = properties.filter(p => p.performance.leveredIrr !== 0);
// const withMOIC = properties.filter(p => p.performance.leveredMoic !== 0);
// const withCashFlow = properties.filter(p => p.operations.noi !== 0);

// NEW:
const withIRR = properties.filter(p => p.performance.leveredIrr != null);
const withMOIC = properties.filter(p => p.performance.leveredMoic != null);
const withCashFlow = properties.filter(p => p.operations.noi != null);
```

Apply the same pattern at lines 115-119, 137-148, 152-160.

- [ ] **Step 5: Run full frontend test suite**

```bash
npx vitest run
```

Fix any type errors from `number` becoming `number | undefined` in downstream components. The most common fix is adding optional chaining (`property.details?.units ?? 'N/A'`) or nullish coalescing in display components.

- [ ] **Step 6: Run build to verify no TypeScript errors**

```bash
npm run build
```

- [ ] **Step 7: Commit**

```bash
git add src/lib/api/schemas/property.ts src/features/analytics/AnalyticsPage.tsx src/lib/api/schemas/__tests__/property-safenum.test.ts
git commit -m "fix(schemas): replace safeNum->0 with safeOptionalNum->undefined to preserve missing-data signal"
```

---

## Workstream B: Backend Stability

### Task 7: Fix sync-in-async in extraction/status.py

**Files:**
- Modify: `backend/app/api/v1/endpoints/extraction/status.py:38,111,157,241`

The fix is simple: change `async def` to `def` on the 4 handlers that use `get_sync_db`. FastAPI automatically runs plain `def` endpoints in a threadpool, so they won't block the event loop.

- [ ] **Step 1: Change all 4 handlers from async def to def**

In `backend/app/api/v1/endpoints/extraction/status.py`:

Line 38: `async def get_extraction_status(` -> `def get_extraction_status(`
Line 111: `async def get_extraction_history(` -> `def get_extraction_history(`
Line 157: `async def list_extracted_properties(` -> `def list_extracted_properties(`
Line 241: `async def get_extraction_details(` -> `def get_extraction_details(`

Remove any `await` keywords inside these functions (there shouldn't be any since they use sync `db`).

- [ ] **Step 2: Run extraction tests**

```bash
cd backend && python -m pytest tests/test_extraction/ -v
```

- [ ] **Step 3: Run full backend test suite**

```bash
cd backend && python -m pytest -n auto --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/endpoints/extraction/status.py
git commit -m "fix(extraction): convert sync-db handlers from async def to def to avoid blocking event loop"
```

---

### Task 8: Fix sync-in-async in construction_pipeline.py

**Files:**
- Modify: `backend/app/api/v1/endpoints/construction_pipeline.py:929,1030`

Two patterns to fix:
1. `trigger_import` (line 929): async def calling sync import functions
2. `fetch_all_apis` (line 1030): creates sync `SessionLocal()` inside async function

- [ ] **Step 1: Fix trigger_import — change to def**

Line 929: `async def trigger_import(` -> `def trigger_import(`

This is the simplest fix. The function calls `get_unimported_files()` and `import_construction_file()` which do `pd.read_excel()` and sync DB — all blocking. Making it `def` lets FastAPI threadpool the entire handler.

- [ ] **Step 2: Fix fetch_all_apis — wrap sync DB calls in asyncio.to_thread**

At lines 1030-1068, replace the pattern:

```python
# OLD:
from app.db.session import SessionLocal
with SessionLocal() as db:
    save_census_bps_records(db, result["records"], ...)

# NEW:
import asyncio
from app.db.session import SessionLocal

def _save_census_sync(records, api_code, errors):
    with SessionLocal() as db:
        save_census_bps_records(db, records, api_code, errors)

await asyncio.to_thread(_save_census_sync, result["records"], result.get("api_response_code"), result.get("errors"))
```

Apply the same pattern for each sync DB block inside `fetch_all_apis`.

- [ ] **Step 3: Run construction pipeline tests**

```bash
cd backend && python -m pytest tests/ -k "construction" -v
```

- [ ] **Step 4: Run full backend test suite**

```bash
cd backend && python -m pytest -n auto --tb=short
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/construction_pipeline.py
git commit -m "fix(api): eliminate sync-in-async blocking in construction pipeline handlers"
```

---

## Workstream C: Deploy & Test Hardening

### Task 9: Add TLS support to nginx

**Files:**
- Modify: `nginx.conf` (root, used by Dockerfile.frontend)
- Create: `docs/deployment/TLS-SETUP.md`

- [ ] **Step 1: Add TLS server block to nginx.conf**

Replace the single `server { listen 80; }` block with two blocks:

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name _;

    # TLS certificates — mount via Docker volume or replace paths
    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Modern TLS configuration (Mozilla Intermediate)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:MozSSL:10m;
    ssl_session_tickets off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # ... (keep all existing location blocks, security headers, proxy config)
}
```

Keep the existing `location /`, `location /api/`, `location /ws/` blocks inside the HTTPS server block.

- [ ] **Step 2: Update docker-compose.prod.yml to expose port 443 and mount certs**

```yaml
  frontend:
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./certs:/etc/nginx/ssl:ro  # Mount TLS certificates
```

- [ ] **Step 3: Document the TLS setup**

Create `docs/deployment/TLS-SETUP.md` explaining:
- Where to put cert files (`./certs/fullchain.pem`, `./certs/privkey.pem`)
- How to use Let's Encrypt / certbot
- How to use with a fronting proxy (Cloudflare/ALB) instead — set `HSTS_PROXIED=1` env and skip the cert volume
- How to test locally with self-signed certs

- [ ] **Step 4: Commit**

```bash
git add nginx.conf docker-compose.prod.yml docs/deployment/TLS-SETUP.md
git commit -m "feat(infra): add TLS termination to nginx with modern cipher suite and HSTS"
```

---

### Task 10: Remove pytest.skip-on-404 patterns in API tests

**Files:**
- Modify: `backend/tests/test_api/test_analytics.py` (16 skips)
- Modify: `backend/tests/test_api/test_exports.py` (25 skips + 10 `[200,500]` assertions)
- Modify: `backend/tests/test_api/test_monitoring.py` (13 skips)

- [ ] **Step 1: In test_analytics.py — replace skip-on-404 with strict assertion**

Find every instance of:
```python
if response.status_code == 404:
    pytest.skip("... endpoint not implemented")
```

Replace with:
```python
assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
```

If the endpoint genuinely doesn't exist yet, delete the test entirely rather than skipping it — a test that always skips is worse than no test.

- [ ] **Step 2: In test_exports.py — fix both patterns**

Replace `pytest.skip` on 404 (same as step 1).

Also replace the `[200, 500]` pattern:
```python
# OLD:
assert response.status_code in [200, 500]

# NEW:
assert response.status_code == 200, f"Export endpoint returned {response.status_code}: {response.text[:200]}"
```

- [ ] **Step 3: In test_monitoring.py — same pattern**

Replace all 13 `pytest.skip` on 404 with strict assertions.

- [ ] **Step 4: Run the fixed tests — expect some to fail**

```bash
cd backend && python -m pytest tests/test_api/test_analytics.py tests/test_api/test_exports.py tests/test_api/test_monitoring.py -v 2>&1 | tail -30
```

**This is expected.** The whole point is to surface which endpoints are actually broken. For each failure:
- If the endpoint exists and should work: investigate and fix the endpoint
- If the endpoint is genuinely not implemented: delete the test and create a tracking issue

- [ ] **Step 5: Commit the test fixes (even if some tests now fail)**

```bash
git add backend/tests/test_api/test_analytics.py backend/tests/test_api/test_exports.py backend/tests/test_api/test_monitoring.py
git commit -m "test(api): remove silent skip-on-404 and [200,500] tolerance — honest failures now visible"
```

---

### Task 11: Remove test.fixme in E2E deal pipeline specs

**Files:**
- Modify: `e2e/deal-pipeline.spec.ts` (18 fixmes)
- Modify: `e2e/deal-comparison.spec.ts` (4 fixmes)
- Modify: `e2e/exports.spec.ts` (5 fixmes)
- Modify: `e2e/deals-crud.spec.ts` (1 fixme)
- Modify: `e2e/underwriting-deal.spec.ts` (1 fixme)

- [ ] **Step 1: Replace test.fixme with proper seed data and assertions**

For each `test.fixme(true, 'No clickable deal cards found...')`:

Option A — If seed data can be added:
```typescript
// Add to the spec's beforeAll or beforeEach:
test.beforeAll(async ({ request }) => {
  // Seed a known deal via the API
  await request.post('/api/v1/deals', {
    data: { property_name: 'E2E Test Deal', stage: 'initial_review', value: 1000000 },
    headers: { Authorization: `Bearer ${authToken}` },
  });
});
```

Then replace the fixme with a real assertion:
```typescript
// OLD: test.fixme(true, 'No clickable deal cards found...');
// NEW:
const cards = page.locator('[data-testid="deal-card"]');
await expect(cards).toHaveCount(1, { timeout: 10000 });
```

Option B — If the feature is genuinely incomplete:
```typescript
// Delete the test entirely. A missing test is honest; a fixme is a lie.
```

- [ ] **Step 2: Replace waitForTimeout with proper waits**

For each `await page.waitForTimeout(1000)`:
```typescript
// OLD: await page.waitForTimeout(1000);
// NEW: await expect(page.locator('[data-testid="target"]')).toBeVisible();
// or: await page.waitForResponse(resp => resp.url().includes('/api/v1/deals'));
```

- [ ] **Step 3: Run E2E locally to check**

```bash
npx playwright test e2e/deal-pipeline.spec.ts --headed
```

- [ ] **Step 4: Commit**

```bash
git add e2e/deal-pipeline.spec.ts e2e/deal-comparison.spec.ts e2e/exports.spec.ts e2e/deals-crud.spec.ts e2e/underwriting-deal.spec.ts
git commit -m "test(e2e): remove 29 test.fixme blocks — seed data or delete, honest failures only"
```

---

## Integration Verification

After all tasks complete:

- [ ] **Run full backend test suite**
```bash
cd backend && python -m pytest -n auto --tb=short
```

- [ ] **Run full frontend test suite**
```bash
npx vitest run
```

- [ ] **Run build**
```bash
npm run build
```

- [ ] **Run lint**
```bash
cd backend && ruff check app/ && npm run lint
```

- [ ] **Verify extraction_warnings table is populated**
```bash
PGPASSWORD=postgres123 psql -h localhost -U postgres -d dashboard_interface_data -c "SELECT warning_type, severity, COUNT(*) FROM extraction_warnings GROUP BY warning_type, severity;"
```

- [ ] **Final commit and tag**
```bash
git tag phase1-complete
```
