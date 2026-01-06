# SharePoint UW Model Extraction Integration Plan

## Overview

This plan integrates the SharePoint underwriting model data extraction pipeline from the prior B&R Capital Dashboard project into `dashboard_interface_project`. The goal is to replicate all 1,179 cell mappings while addressing known issues and improving upon the existing implementation.

---

## Prior Project Analysis

### What Works Well ✅

| Component | Details |
|-----------|---------|
| **Cell Mapping Architecture** | `CellMappingParser` cleanly loads 1,179 mappings from Excel reference file |
| **Error Handling System** | 9-category `ErrorHandler` with graceful `np.nan` degradation ensures extraction continues |
| **PyXLSB Extraction** | Properly handles 0-based indexing conversion (documented fix) |
| **Batch Processing** | `BatchFileProcessor` with `ThreadPoolExecutor` enables parallel extraction |
| **Structured Logging** | Uses `structlog` for consistent, queryable log output |
| **Circuit Breaker Pattern** | SharePoint auth has resilience (5 failures → OPEN, 1-min recovery) |
| **Connection Pooling** | PostgreSQL `ThreadedConnectionPool` (2-10 connections) |
| **Integer Overflow Protection** | Financial fields converted to float for large values |

### Issues & Pain Points ⚠️

| ID | Issue | Severity | Root Cause | Fix in New Implementation |
|----|-------|----------|------------|---------------------------|
| DQ-001 | 29 duplicate field names | High | `_clean_field_name()` produces identical keys → dict overwrites | Add unique suffix (e.g., sheet name or row index) |
| DQ-002 | 17+ duplicate properties in DB | High | No UNIQUE constraint on `property_name` | Add UNIQUE constraint + upsert logic |
| PERF-001 | N+1 queries in INSERT loops | Medium | Individual INSERT per comparable | Use `executemany()` or bulk insert |
| SEC-003 | f-string SQL for column names | Medium | Dynamic SQL injection risk | Use `psycopg2.sql.Identifier()` |
| DQ-003 | Hardcoded placeholder values | Medium | `portfolio_irr=0.12` etc. hardcoded | Query actual calculated values |
| ARCH-003 | Verbose `str(e)` exception handling | Low | 865+ files expose internal paths | Create centralized error handler |

### Inefficiencies to Address

1. **No database abstraction layer** – Prior project uses raw `psycopg2` everywhere
2. **Tight coupling** – Extraction, transformation, and loading intertwined
3. **Limited test coverage** – 22% current (target 60%+)
4. **No API layer for extraction** – Must run scripts manually
5. **2-minute cache TTL** – May show stale metrics

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        dashboard_interface_project                       │
├─────────────────────────────────────────────────────────────────────────┤
│  backend/                                                                │
│  ├── app/                                                                │
│  │   ├── extraction/          # NEW - Extraction module                 │
│  │   │   ├── __init__.py                                                │
│  │   │   ├── cell_mapping.py  # CellMapping dataclass + parser         │
│  │   │   ├── extractor.py     # ExcelDataExtractor                     │
│  │   │   ├── error_handler.py # ErrorHandler with 9 categories         │
│  │   │   ├── sharepoint.py    # SharePoint discovery + download        │
│  │   │   └── batch.py         # BatchProcessor                         │
│  │   ├── crud/                                                          │
│  │   │   └── extraction.py    # NEW - Extraction CRUD operations       │
│  │   ├── api/                                                           │
│  │   │   └── v1/                                                        │
│  │   │       └── extraction.py # NEW - Extraction endpoints            │
│  │   └── schemas/                                                       │
│  │       └── extraction.py    # NEW - Pydantic schemas                 │
│  └── tests/                                                             │
│      └── test_extraction/     # NEW - Extraction tests                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Proposed Changes

### Component 1: Extraction Module

#### [NEW] [cell_mapping.py](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/extraction/cell_mapping.py)

Port `CellMapping` dataclass and `CellMappingParser` class with improvements:
- Add unique field name generation (append sheet name suffix for duplicates)
- Add validation for required columns
- Use existing `Underwriting_Dashboard_Cell_References.xlsx` in project root

---

#### [NEW] [extractor.py](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/extraction/extractor.py)

Port `ExcelDataExtractor` class:
- Maintain pyxlsb 0-based indexing conversion
- Port `_extract_cell_value()` with formula error detection
- Add progress callback for API status updates

---

#### [NEW] [error_handler.py](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/extraction/error_handler.py)

Port `ErrorHandler` and `ErrorCategory`:
- Maintain all 9 error categories
- All errors → `np.nan` (graceful degradation)
- Add structured error summary generation

---

#### [NEW] [sharepoint.py](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/extraction/sharepoint.py)

Port SharePoint integration:
- MSAL authentication with circuit breaker
- File discovery with filtering (`*UW Model vCurrent.xlsb`, modified ≥ 2024-07-15)
- File download with retry logic

---

#### [NEW] [batch.py](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/extraction/batch.py)

Port `BatchFileProcessor`:
- ThreadPoolExecutor with configurable workers
- Progress tracking for API integration
- Error aggregation and reporting

---

### Component 2: Database Integration

#### [NEW] [extraction.py (crud)](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/crud/extraction.py)

Create CRUD layer for extraction data:
- Use SQLAlchemy ORM (matching existing project patterns)
- Implement bulk insert with `Session.bulk_insert_mappings()`
- Add upsert logic with PostgreSQL `ON CONFLICT`

---

#### [MODIFY] Database Models

Create **NEW database** `br_extraction_data` with fresh schema via Alembic migrations.

**Fresh Schema Design** (avoiding prior project issues):

```sql
-- Properties table with UNIQUE constraint (fixes DQ-002)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_name VARCHAR(255) NOT NULL UNIQUE,  -- UNIQUE prevents duplicates
    property_address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extraction runs (batch tracking)
CREATE TABLE extraction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'running',  -- running, completed, failed, cancelled
    trigger_type VARCHAR(50) NOT NULL,  -- manual, scheduled
    files_discovered INTEGER DEFAULT 0,
    files_processed INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    error_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extracted values (normalized, not 1000+ columns)
CREATE TABLE extracted_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_run_id UUID REFERENCES extraction_runs(id) ON DELETE CASCADE,
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    field_name VARCHAR(255) NOT NULL,
    field_category VARCHAR(100),
    sheet_name VARCHAR(100),
    cell_address VARCHAR(20),
    value_text TEXT,  -- Store all as text, cast on read
    value_numeric DECIMAL(20, 4),  -- For numeric fields (fixes integer overflow)
    value_date DATE,  -- For date fields
    is_error BOOLEAN DEFAULT FALSE,
    error_category VARCHAR(50),
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(extraction_run_id, property_id, field_name)  -- Prevent duplicate fields
);

-- Index for fast lookups
CREATE INDEX idx_extracted_values_property ON extracted_values(property_id);
CREATE INDEX idx_extracted_values_field ON extracted_values(field_name);
CREATE INDEX idx_extracted_values_run ON extracted_values(extraction_run_id);
```

> [!TIP]
> This normalized schema stores each field as a row (EAV pattern) instead of 1,179 columns. This:
> - Avoids column limit issues
> - Makes adding new fields trivial
> - Enables easy field-by-field error tracking
> - Simplifies queries with proper indexing

---

### Component 3: API Endpoints

#### [NEW] [extraction.py (api)](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/api/v1/extraction.py)

FastAPI endpoints:
```python
POST /api/v1/extraction/start     # Trigger extraction (manual)
GET  /api/v1/extraction/status    # Get extraction status
GET  /api/v1/extraction/history   # List past extractions
POST /api/v1/extraction/cancel    # Cancel running extraction
GET  /api/v1/extraction/schedule  # Get scheduler status
POST /api/v1/extraction/schedule  # Update scheduler settings
```

---

### Component 4: Scheduler

#### [NEW] [scheduler.py](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/app/extraction/scheduler.py)

APScheduler integration for automated extraction:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class ExtractionScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        # Default: 2 AM daily
        self.scheduler.add_job(
            run_scheduled_extraction,
            CronTrigger.from_crontab(settings.EXTRACTION_SCHEDULE_CRON),
            id="nightly_extraction",
            replace_existing=True
        )
        self.scheduler.start()
```

---

### Component 5: Tests

#### [NEW] [test_extraction.py](file:///wsl.localhost/Ubuntu/home/mattb/projects/dashboard_interface_project/backend/tests/test_extraction/)

Create comprehensive test suite:
- Unit tests for `CellMappingParser`
- Unit tests for `ErrorHandler` (all 9 categories)
- Integration tests for `ExcelDataExtractor`
- API endpoint tests

---

## Verification Plan

### Automated Tests

#### 1. Unit Tests (pytest)

```bash
# Run from backend directory
cd backend
source venv/bin/activate
pytest tests/test_extraction/ -v --tb=short
```

**Test cases to implement:**
- `test_cell_mapping_load` - Verify 1,179 mappings loaded
- `test_cell_mapping_unique_names` - Verify no duplicate field names
- `test_error_handler_all_categories` - Test all 9 error types → `np.nan`
- `test_pyxlsb_indexing` - Verify row-1, col-1 conversion
- `test_integer_overflow_protection` - Large values → float

#### 2. Integration Tests

```bash
# Requires test PostgreSQL database
pytest tests/test_extraction/test_integration.py -v --tb=short
```

**Test cases:**
- `test_extraction_to_database` - Full pipeline with mock Excel file
- `test_bulk_insert_performance` - Verify batch insert vs N+1

#### 3. API Tests

```bash
pytest tests/test_api/test_extraction.py -v --tb=short
```

**Test cases:**
- `test_start_extraction_endpoint`
- `test_extraction_status_endpoint`
- `test_extraction_cancel_endpoint`

### Manual Verification

#### 1. Cell Mapping Validation

```bash
# Verify mapping count matches expected
python -c "
from app.extraction.cell_mapping import CellMappingParser
parser = CellMappingParser('../Underwriting_Dashboard_Cell_References.xlsx')
mappings = parser.load_mappings()
print(f'Loaded {len(mappings)} mappings')
assert len(mappings) == 1179, f'Expected 1179, got {len(mappings)}'
print('✓ All mappings loaded successfully')
"
```

#### 2. SharePoint Connectivity

```bash
# Test SharePoint authentication (requires credentials in .env)
python -c "
from app.extraction.sharepoint import SharePointClient
client = SharePointClient()
files = client.discover_files()
print(f'Discovered {len(files)} UW model files')
"
```

#### 3. End-to-End Extraction

1. Start the backend: `uvicorn app.main:app --reload`
2. Open browser to `http://localhost:8000/docs`
3. Execute `POST /api/v1/extraction/start`
4. Poll `GET /api/v1/extraction/status` until complete
5. Verify data in PostgreSQL: `SELECT COUNT(*) FROM extracted_values;`

---

## Implementation Phases

### Phase 1: Standalone Module (3-4 hours)
1. Create `backend/app/extraction/` directory structure
2. Port core classes: `CellMapping`, `CellMappingParser`, `ErrorHandler`, `ExcelDataExtractor`
3. Add unit tests for each class
4. Verify: `pytest tests/test_extraction/test_unit.py`

### Phase 2: Database Integration (2-3 hours)
1. Create Alembic migration for extraction tables
2. Create CRUD layer with bulk insert
3. Add integration tests
4. Verify: `pytest tests/test_extraction/test_integration.py`

### Phase 3: API Integration (2-3 hours)
1. Create FastAPI endpoints
2. Add background task handling
3. Add API tests
4. Verify: `pytest tests/test_api/test_extraction.py`

### Phase 4: SharePoint Integration (2-3 hours)
1. Port SharePoint discovery and download
2. Configure MSAL authentication
3. Add E2E tests
4. Verify: Manual SharePoint connectivity test

---

## Configuration Requirements

> [!NOTE]
> **User Decision**: Create a NEW separate PostgreSQL database with a fresh schema (not reusing `br_capital_dashboard` schema due to prior issues).

Add to `backend/.env`:
```bash
# SharePoint Configuration (copy from prior project)
AZURE_CLIENT_ID=5a620cea-31fe-40f6-8b48-d55bc5465dc9
AZURE_CLIENT_SECRET=<copy from prior project .env>
AZURE_TENANT_ID=<copy from prior project .env>
SHAREPOINT_SITE_URL=bandrcapital.sharepoint.com/sites/BRCapital-Internal

# NEW Extraction Database (separate from dashboard DB)
EXTRACTION_DB_NAME=br_extraction_data
EXTRACTION_DB_HOST=localhost
EXTRACTION_DB_PORT=5432
EXTRACTION_DB_USER=postgres
EXTRACTION_DB_PASSWORD=<password>

# Extraction Settings
EXTRACTION_WORKERS=4
EXTRACTION_BATCH_SIZE=10
EXTRACTION_DATE_FILTER=2024-07-15

# Scheduler Settings (for automated extraction)
EXTRACTION_SCHEDULE_ENABLED=true
EXTRACTION_SCHEDULE_CRON="0 2 * * *"  # 2 AM daily
```

---

## Dependencies to Add

Add to `backend/requirements.txt`:
```
pyxlsb>=1.0.10
openpyxl>=3.1.0
msal>=1.24.0
structlog>=23.1.0
aiohttp>=3.8.0
apscheduler>=3.10.0  # For scheduled extraction
psycopg2-binary>=2.9.0  # For extraction database
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SharePoint token expiration | Medium | Medium | Implement token refresh + circuit breaker |
| Excel file format changes | Low | High | Add schema validation on extraction |
| Large file extraction timeout | Medium | Medium | Use chunked processing + progress tracking |
| Database migration conflicts | Low | Medium | Review existing migrations before adding new |

---

## User Decisions (Confirmed)

| Item | Decision |
|------|----------|
| **SharePoint credentials** | Copy from prior project's `.env` (credentials still valid) |
| **Database** | New separate database `br_extraction_data` with fresh schema |
| **Schema approach** | EAV pattern (field per row) to avoid prior issues |
| **Extraction trigger** | Both manual API and scheduled (nightly at 2 AM) |
| **Test files** | Pending clarification |
