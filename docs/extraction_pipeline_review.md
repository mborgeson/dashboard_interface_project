# Extraction Pipeline — Comprehensive Review

**Date**: 2026-02-11
**Scope**: `backend/app/extraction/`, related services, models, migrations, and automation configs
**Method**: Three-analyst parallel review (read-only), synthesized by team lead

---

## Q1: Database Existence Checks — What determines whether a deal's data already exists?

The pipeline performs existence/deduplication checks at **three layers**:

### Layer 1: File-Level Change Detection (SharePoint Monitor)

The `SharePointFileMonitor` (`services/extraction/file_monitor.py:226-318`) detects whether a **file** has changed since last seen:

1. **Path-based lookup** (`:247`): Each SharePoint file is identified by its `file_path` (unique column on `monitored_files`). Files not in `stored_paths` are classified as "added".
2. **Modified-date + size comparison** (`:294-296`): If SharePoint `lastModifiedDateTime` is newer OR `size` differs from the stored `MonitoredFile` record, it's classified as "modified".
3. **Content hash — declared but never populated**: `MonitoredFile.content_hash` is a `String(64)` column (`models/file_monitor.py:58-60`) intended for SHA-256 — but no code ever writes to it.
4. **`needs_extraction` property** (`models/file_monitor.py:106-114`): Returns `True` if `extraction_pending`, never extracted, or `modified_date > last_extracted`.

### Layer 2: Per-Deal Content Hashing (Change Detector)

`change_detector.py` performs SHA-256 hash comparison of **extracted data values**:

1. **`compute_extraction_hash()`** (`:46-64`): Filters out `_`-prefixed metadata keys, sorts `(field_name, normalized_value)` pairs, JSON-serializes, SHA-256 hex digest.
2. **`get_db_values_hash()`** (`:67-117`): Queries the latest `extraction_run_id` where `er.status = 'completed'` (ordered by `completed_at DESC`, then `created_at DESC`), fetches all `(field_name, value_text)` pairs for that run+property, hashes them identically.
3. **`should_extract_deal()`** (`:120-164`):
   - `db_hash is None` → `(True, "new_deal")`
   - `new_hash != db_hash` → `(True, "data_changed")`
   - `new_hash == db_hash` → `(False, "unchanged")` — skip

### Layer 3: DB Uniqueness Constraint

`UniqueConstraint("extraction_run_id", "property_name", "field_name")` on `extracted_values` (`models/extraction.py:160-166`) prevents duplicate field entries within the same extraction run.

---

## Q2: Complete Execution Path — Invocation to Completion

### Entry Points

- **Manual API**: `POST /api/v1/extraction/start` (`api/v1/endpoints/extraction/extract.py:31-119`)
- **Scheduled**: `ExtractionScheduler._run_scheduled_extraction()` (`services/extraction/scheduler.py:141-197`) via APScheduler cron

### Step-by-Step (Manual API Path)

| Step | Location | Action |
|------|----------|--------|
| 1. Pre-flight | `extract.py:47-51` | Check for already-running extraction via `ExtractionRunCRUD.get_running(db)` → HTTP 409 if exists |
| 2. File discovery | `extract.py:54-100` | If `source="sharepoint"`: authenticate MSAL → get site/drive IDs → enumerate stage/deal/UW-model folders → apply `FileFilter.should_process()`. If `source="local"`: use provided paths. |
| 3. Create run | `extract.py:103-105` | `ExtractionRunCRUD.create()` → `extraction_runs` row with `status="running"` |
| 4. Launch background | `extract.py:109-111` | `background_tasks.add_task(common.run_extraction_task, ...)` → returns immediately |
| 5. Load mappings | `common.py` | `CellMappingParser` parses reference Excel → ~1,179 `CellMapping` objects |
| 6. Download files | `common.py:273-285` | For SharePoint: downloads each file to temp dir sequentially |
| 7. Per-file extract | `extractor.py:119-298` | Pre-validate via `FileFilter`, load workbook (.xlsb via pyxlsb / .xlsx via openpyxl), extract each of ~1,179 cells → `ErrorHandler.process_cell_value()` |
| 8. Resolve property | `common.py:133-135` | `PROPERTY_NAME` from Excel → deal folder name → file stem (priority order) |
| 9. Change detection | `common.py:138` | `should_extract_deal()` — SHA-256 hash compare. If unchanged → skip. |
| 10. Bulk upsert | `crud/extraction.py:138-222` | PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` on `uq_extracted_value` |
| 11. Update progress | `common.py:185-194` | `ExtractionRunCRUD.update_progress()` per file |
| 12. Complete run | `common.py:205-211` | `ExtractionRunCRUD.complete()` with final counts and error summary |
| 13. Cleanup | `common.py:367-368` | Close DB session, auto-clean temp directory |

---

## Q3: Persisted Metadata Beyond Extracted Data Points

### Level 1: `extraction_runs` (per-batch)

| Column | Type | Source |
|--------|------|--------|
| `id` | UUID PK | Auto-generated |
| `started_at` | DateTime(tz) | `datetime.now(UTC)` default |
| `completed_at` | DateTime(tz) | Set at run completion |
| `status` | String(50) | `running` → `completed`/`failed`/`cancelled` |
| `trigger_type` | String(50) | `"manual"` or `"scheduled"` |
| `files_discovered` | Integer | Count at discovery time |
| `files_processed` / `files_failed` | Integer | Updated per-file |
| `error_summary` | JSON | `{failed_files: [...], total_failures: N}` |
| `created_at` / `updated_at` | DateTime(tz) | `TimestampMixin` |

### Level 2: `extracted_values` (per-field)

| Column | Type | Source |
|--------|------|--------|
| `source_file` | String(500) | SharePoint path or local path |
| `extraction_run_id` | UUID FK | Links to batch run |
| `property_name` | String(255) | Derived from Excel / folder / stem |
| `field_category` | String(100) | From mapping reference file |
| `sheet_name` / `cell_address` | String | From mapping reference file |
| `is_error` | Boolean | True when value is NaN/None |
| `error_category` | String(50) | **Column exists but never populated** |
| `created_at` / `updated_at` | DateTime(tz) | `TimestampMixin` — serves as extraction timestamp |

### Level 3: `monitored_files` (file tracking)

| Column | Type | Source |
|--------|------|--------|
| `file_path` | String(500) UNIQUE | SharePoint path |
| `file_name` / `deal_name` / `deal_stage` | String | From discovery |
| `size_bytes` | BigInteger | **File size** |
| `modified_date` | DateTime(tz) | **Source file modified date** |
| `content_hash` | String(64) | **Declared but never populated** |
| `first_seen` / `last_checked` / `last_extracted` | DateTime(tz) | Tracking timestamps |
| `extraction_pending` | Boolean | Set on change detection |
| `extraction_run_id` | UUID FK | Last extraction run |

### Level 4: `file_change_logs` (audit trail)

| Column | Type | Source |
|--------|------|--------|
| `change_type` | String(20) | `"added"` / `"modified"` / `"deleted"` |
| `old_modified_date` / `new_modified_date` | DateTime(tz) | Before/after |
| `old_size_bytes` / `new_size_bytes` | BigInteger | Before/after |
| `detected_at` | DateTime(tz) | When change was detected |
| `extraction_triggered` | Boolean | **Always defaults to False** |

### Level 5: `underwriting_models` (via `SourceTrackingMixin`)

| Column | Type | Notes |
|--------|------|-------|
| `source_file_name` / `source_file_path` | String/Text | Source tracking |
| `source_file_modified_at` / `extracted_at` | DateTime(tz) | Timestamps |
| `extraction_version` | String(50) | Version identifier |
| `extraction_status` | String(20) | pending/success/partial/error |
| `extraction_errors` | Text | Error details |

**Gap**: `SourceTrackingMixin` fields are defined in the schema but the extraction pipeline writes ONLY to `extracted_values` (EAV pattern). It does **not** create/update `underwriting_models` rows.

### Transient metadata (NOT persisted)

`_file_path`, `_extraction_timestamp`, `_extraction_errors`, `_extraction_metadata`, `_deal_name`, `_deal_stage`, `_file_modified_date` — available during processing but discarded.

---

## Q4: Every Conditional Check in the Extraction Workflow

### extractor.py — `ExcelDataExtractor`

| Location | Condition | True Path | False Path |
|----------|-----------|-----------|------------|
| `:61-64` | `self._file_filter is None` | Lazy-create `FileFilter` | Return existing |
| `:91-96` | `file_content is not None` / `Path.exists()` | Use `len(file_content)` for size | Use `stat().st_size` or default 0 |
| `:109` | `not filter_result.should_process` | Return early, `_validation_skipped=True` | Continue to workbook loading |
| `:162` | `validate` param | Run `validate_file()` pre-check | Skip validation |
| `:168` | `not is_valid` | Return with skip metadata | Proceed to file loading |
| `:188-191` | `file_content is None` + `not path.exists()` | Raise `FileNotFoundError` | Continue |
| `:196-201` | `file_ext == ".xlsb"` | `_load_xlsb()`, `is_xlsb=True` | `_load_xlsx()`, `is_xlsb=False` |
| `:229-236` | Value is not NaN/None | `successful += 1` | `failed += 1` |
| `:238` | `except Exception` on cell | `np.nan`, append error | Normal |
| `:383` | Sheet not in workbook (xlsb) | `handle_missing_sheet()` → `np.nan` | Continue |
| `:392` | Invalid cell address regex | `handle_invalid_cell_address()` → `np.nan` | Continue |
| `:408-412` | Sheet not in cache | **Cache miss**: build full sheet cache | **Cache hit**: reuse, increment hits |
| `:444` | `cell_value is not None` | `process_cell_value()` | `handle_empty_value()` → `np.nan` |
| `:459` | Sheet not in sheetnames (xlsx) | `handle_missing_sheet()` → `np.nan` | Continue |

### file_filter.py — Sequential filter chain (first failure short-circuits)

| Order | Check | Fail Result |
|-------|-------|-------------|
| 1 | Extension in `{.xlsb, .xlsx, .xlsm}` | `INVALID_EXTENSION` |
| 2 | Filename not matching exclude patterns | `EXCLUDED_PATTERN` |
| 3 | Filename matches configured regex | `PATTERN_MISMATCH` |
| 4 | Size ≤ `MAX_FILE_SIZE_MB` (100MB) | `TOO_LARGE` |
| 5 | Modified date ≥ cutoff date | `TOO_OLD` |
| 6 | All passed | `should_process=True` |

### sharepoint.py — Key conditionals

| Location | Condition | Action |
|----------|-----------|--------|
| `:152-157` | Token exists AND not expired (5min buffer) | Return cached token / Acquire new |
| `:196-208` | Response status 401 | Retry once: clear token, re-auth, retry |
| `:252-261` | Library not found in drives | Fall back to default site drive |
| `:411-415` | Subfolder name contains "uw" or "model" | Scan for UW model files |
| `:487-512` | `use_filter=True` | Apply `FileFilter` / Use legacy regex patterns |
| `:637-658` | Path keywords ("dead", "active_review", etc.) | Map to deal stage string / Return `None` |

### error_handler.py — Value processing chain

| Check | Result |
|-------|--------|
| `value is None or ""` | `np.nan` (empty) |
| String contains Excel error (#REF!, etc.) | `np.nan` (formula error) |
| String in missing indicators (n/a, null, etc.) | `np.nan` (empty) |
| Numeric + `isnan`/`isinf` | `np.nan` (empty) |
| datetime | Pass through |
| bool | Pass through |
| All else | `str(value)` or `np.nan` on failure |

### common.py — Background task

| Location | Condition | Action |
|----------|-----------|--------|
| `:46-48` | `not settings.sharepoint_configured` | Raise `ValueError` |
| `:138-149` | `not needs_update` (change detection) | Skip file, `skipped += 1` |
| `:262-267` | Empty SharePoint discovery | Complete run with 0 files, return early |
| `:172-182` | Per-file `except Exception` | `failed += 1`, log, continue |
| `:354-368` | Outer `except Exception` | Mark run as failed in DB |

---

## Q5: Identical Data Handling — Skip, Overwrite, or Duplicate?

**Answer: SKIP — no database write occurs.**

### Two-stage gate

**Stage 1 — Hash comparison** (`change_detector.py:120-164`):
- Computes SHA-256 of freshly extracted `{field_name: normalized_value}` pairs
- Computes SHA-256 of latest completed run's `{field_name: value_text}` from DB
- If hashes match → `(False, "unchanged")` → calling code in `common.py:140-149` **skips entirely**

**Stage 2 — Upsert safety net** (only reached if hash says "changed"):
`ON CONFLICT DO UPDATE` on `(extraction_run_id, property_name, field_name)` unique constraint. Overwrites on conflict — never duplicates.

### Hash normalization mismatch (potential false positives)

- Extraction hash normalizes floats to 4 decimal places: `1234.5` → `"1234.5000"`
- DB stores `value_text` as `str(value)`: `1234.5` → `"1234.5"`
- Hashes can differ even when values are semantically identical → causes unnecessary (but harmless) overwrites

### Summary

| Scenario | DB Operation |
|----------|-------------|
| Brand new deal | INSERT all ~1,179 values |
| Deal exists, data changed | ON CONFLICT UPDATE all values |
| Deal exists, data identical | **SKIP — no DB write** |
| Same run+property+field conflict | UPDATE (overwrite) |
| File fails filter | No DB write |

---

## Q6: Automated Triggers

### Active at Runtime

| Trigger | Active? | Config |
|---------|---------|--------|
| **UW Extraction Scheduler** | **YES** | Daily 5 PM Phoenix, `EXTRACTION_SCHEDULE_ENABLED=True` |
| **File Monitor Scheduler** | **NO** (default) | 30min interval, `FILE_MONITOR_ENABLED=False` |
| **Market Data Scheduler** | **NO** | Not wired into `main.py` lifespan |
| **General Task Scheduler** | **NO** | Not started in `main.py` |
| **Manual API** | **YES** | `POST /api/v1/extraction/start` always available |

### UW Extraction Scheduler (`services/extraction/scheduler.py`)

- APScheduler `CronTrigger`, default `"0 17 * * *"` (5 PM Phoenix)
- Initialized in `main.py:111-123` during FastAPI lifespan
- Overlap prevention: checks `self._state.running` flag + DB for running extraction
- API endpoints for enable/disable/config at `/api/v1/extraction/scheduler/`

### File Monitor Scheduler (`services/extraction/monitor_scheduler.py`)

- APScheduler `IntervalTrigger`, default 30 minutes
- Disabled by default — requires `FILE_MONITOR_ENABLED=True`
- Calls `SharePointFileMonitor.check_for_changes()` which polls via Graph API
- API endpoints at `/api/v1/extraction/monitor/`

**No event-based triggers exist** — no OS cron jobs, no Celery/beat, no Docker scheduled tasks. All scheduling is in-process via APScheduler.

---

## Q7: Version Selection for Dashboard Display

**There is NO single consistent version-selection strategy.** Three different query paths use three different mechanisms:

### Extraction Dashboard — Latest run by `started_at`

`/extraction/properties` (`api/v1/endpoints/extraction/status.py:166-170`):
```
ExtractionRunCRUD.get_latest() → ORDER BY started_at DESC LIMIT 1
```
Returns the most recent run **regardless of status** — even if `"running"` or `"failed"`.

### Deal Dashboard — Non-deterministic

`_enrich_deals_with_extraction()` (`api/v1/endpoints/deals.py:60-71`):
```
SELECT * FROM extracted_values WHERE property_id IN (...) AND field_name IN (...)
```
**No `run_id` filter. No ordering.** Dict overwrite means the "winning" row depends on database scan order — effectively **arbitrary**.

### Change Detection — Latest completed run

`get_db_values_hash()` (`change_detector.py:82-90`):
```
ORDER BY er.completed_at DESC NULLS LAST, er.created_at DESC LIMIT 1
WHERE er.status = 'completed'
```
Most rigorous: latest **completed** run only.

---

## Q8: Multiple UW Model Files for the Same Property

### (a) How are they identified as the same property?

Property matching uses `property_name` derived at `common.py:133-135`:
1. **`PROPERTY_NAME`** extracted from Excel cell (highest priority)
2. **`deal_name`** from SharePoint folder name
3. **File stem** as last resort

Two files match if they produce the same `property_name` string. **No fuzzy matching, no canonical property ID lookup.** The `property_id` FK on `extracted_values` is nullable and **never populated** by the extraction pipeline.

### (b) How are both stored?

**Within the same run**: The second file's values **silently overwrite** the first via `ON CONFLICT DO UPDATE` on `(extraction_run_id, property_name, field_name)`. The `source_file` column reflects whichever file was processed last.

**Across different runs**: Both versions persist with separate `extraction_run_id` values.

### (c) Which is used for dashboard display?

- **Extraction dashboard**: Scoped to latest run → last-file-wins within that run
- **Deal dashboard**: Queries by `property_id` with no run filter → non-deterministic (and `property_id` is never populated, so enrichment only works if manually linked)

---

## Q9: File System / SharePoint Change Monitoring

**SharePoint change monitoring IS implemented** via **polling** — not webhooks or real-time subscriptions.

### Implementation: `SharePointFileMonitor` (`services/extraction/file_monitor.py`)

1. **Poll**: Calls `find_uw_models()` via Graph API to enumerate all files
2. **Diff**: Compares against `monitored_files` DB table
   - New files (not in DB) → `change_type="added"`
   - Missing files (in DB, not in SharePoint) → `change_type="deleted"`
   - Modified files (newer date OR different size) → `change_type="modified"`
3. **Update state**: Writes changes to `monitored_files` and `file_change_logs`
4. **Trigger extraction**: If `AUTO_EXTRACT_ON_CHANGE=True` → marks files `extraction_pending=True`

### What is NOT implemented

- No watchdog (local filesystem monitoring)
- No Microsoft Graph webhooks/subscriptions (real-time push)
- No Microsoft Graph delta queries (incremental change tracking)
- No WebSocket push
- `_trigger_extraction()` is **incomplete** — marks files pending but does not actually invoke extraction (comment: "Full integration would call the extraction service here")

### Scheduling

Polling via `FileMonitorScheduler` using APScheduler `IntervalTrigger` (default 30 minutes). **Disabled by default** (`FILE_MONITOR_ENABLED=False`).

---

## Q10: Parallel Processing, Batch Operations, Async I/O

### What exists in the codebase

| Feature | Present? | Location | Used in main extraction flow? |
|---------|----------|----------|------------------------------|
| ThreadPoolExecutor | YES | `extractor.py:541` (`BatchProcessor`) | **NO** — `run_extraction_task` uses sequential `process_files()` |
| asyncio.Semaphore | YES | `batch_processor.py:229` | **NO** — generic batch processor, not wired |
| asyncio worker pool | YES | `task_executor.py:89` | **NO** — not started in `main.py` |
| Async SharePoint (aiohttp) | YES | `sharepoint.py` | YES |
| Async DB sessions | YES | `file_monitor.py` | YES |
| DB connection pooling | YES | SQLAlchemy default `QueuePool` | YES (implicit) |
| HTTP connection pooling | **NO** | `sharepoint.py:192` | New `aiohttp.ClientSession()` per request |
| Redis-backed queue | YES | `job_queue.py:170` | Optional, not initialized |

### What actually runs sequentially in the main flow

- **Excel cell extraction** within a single file: sequential loop over ~1,179 mappings
- **`process_files()` in `common.py`**: files processed one at a time in a `for` loop
- **SharePoint download**: files downloaded one at a time in a `for` loop
- **The `BatchProcessor` with `ThreadPoolExecutor` exists but is NOT used** by `run_extraction_task()`

---

## Q11: Prioritized Material Improvements

### Priority 1 — Critical Bugs / Data Integrity

#### 1.1 Non-deterministic version selection in deal dashboard
- **Gap**: `_enrich_deals_with_extraction()` (`deals.py:60-71`) queries `extracted_values` with no `run_id` filter and no ordering. Which extraction "wins" is arbitrary.
- **Fix**: Add `JOIN extraction_runs` with `ORDER BY completed_at DESC LIMIT 1` per property, or filter to the latest completed `extraction_run_id` — consistent with `change_detector.py`'s approach.
- **Impact**: Prevents incorrect/stale data from appearing on the deal dashboard.
- **Complexity**: Low — single query change.

#### 1.2 Hash normalization mismatch causes unnecessary writes
- **Gap**: `compute_extraction_hash()` normalizes floats to 4 decimal places (`"1234.5000"`), but `value_text` stores full `str()` output (`"1234.5"`). Hashes diverge on semantically identical data.
- **Fix**: Normalize `value_text` the same way before hashing in `get_db_values_hash()`, or store the hash alongside the extraction run and compare directly.
- **Impact**: Eliminates unnecessary DB writes on every extraction cycle for unchanged deals.
- **Complexity**: Low — one normalization function alignment.

#### 1.3 Extraction status endpoint returns any-status runs
- **Gap**: `ExtractionRunCRUD.get_latest()` orders by `started_at DESC` with no status filter. A running or failed run is returned as the "latest", potentially showing incomplete data.
- **Fix**: Filter to `status='completed'` (or at minimum exclude `'failed'`).
- **Impact**: Dashboard shows only complete, reliable extraction data.
- **Complexity**: Low — one WHERE clause.

### Priority 2 — Incomplete Implementations

#### 2.1 `property_id` never populated on `extracted_values`
- **Gap**: The `property_id` FK column exists but the extraction pipeline never links extracted values to `properties` rows. Deal dashboard enrichment depends on this link.
- **Fix**: After resolving `property_name`, look up (or create) the corresponding `properties.id` and set `property_id` during `bulk_insert()`.
- **Impact**: Enables deal dashboard enrichment to work without manual linking. Foundational for any property-centric queries.
- **Complexity**: Medium — requires property name → ID resolution logic, handling of new vs. existing properties.

#### 2.2 `content_hash` on `monitored_files` never populated
- **Gap**: SHA-256 column declared but no code writes to it. File change detection relies solely on date+size, which can miss content-only changes (e.g., re-saved file with same timestamp).
- **Fix**: Compute SHA-256 of file bytes during download, store in `content_hash`, include in change detection comparison.
- **Impact**: Catches content changes that date+size miss. Low frequency but high value for data integrity.
- **Complexity**: Low — hash computation + one column write.

#### 2.3 `_trigger_extraction()` in file monitor is incomplete
- **Gap**: `file_monitor.py:432-457` only marks files as `extraction_pending=True`. Comment says "Full integration would call the extraction service here." No actual extraction is triggered.
- **Fix**: Wire `_trigger_extraction()` to invoke `run_extraction_task()` or queue it via the task executor for changed files only.
- **Impact**: Enables the file monitor → extraction pipeline to work end-to-end.
- **Complexity**: Medium — needs to handle concurrency with scheduled/manual runs.

#### 2.4 `error_category` and `extraction_triggered` columns never written
- **Gap**: `error_category` on `extracted_values` and `extraction_triggered` on `file_change_logs` exist in schema but are never populated.
- **Fix**: Populate `error_category` from `ErrorHandler` classification during `bulk_insert()`. Set `extraction_triggered=True` when extraction is actually triggered from monitor.
- **Impact**: Enables error analytics and audit completeness.
- **Complexity**: Low.

### Priority 3 — Performance

#### 3.1 Main extraction flow is fully sequential
- **Gap**: `process_files()` in `common.py` processes files one at a time. `BatchProcessor` with `ThreadPoolExecutor(max_workers=4)` exists but is **never called** by the main flow.
- **Fix**: Replace the sequential `for` loop in `process_files()` with `BatchProcessor.process_batch()`, or at minimum use `ThreadPoolExecutor` for the Excel parsing step (which is CPU-bound).
- **Impact**: 3-4x throughput improvement for multi-file extractions. Critical as file count grows.
- **Complexity**: Medium — the `BatchProcessor` already exists; wiring it in requires handling per-file DB writes and progress tracking.

#### 3.2 SharePoint downloads are sequential
- **Gap**: `common.py:273-285` downloads files one at a time in a `for` loop, despite SharePoint client being fully async.
- **Fix**: Use `asyncio.gather()` with a semaphore to download files concurrently (e.g., 5 at a time).
- **Impact**: Significant reduction in wall-clock time for SharePoint-sourced extractions.
- **Complexity**: Low — async patterns already exist in the codebase.

#### 3.3 No HTTP connection reuse for SharePoint
- **Gap**: `sharepoint.py:192-195` creates a new `aiohttp.ClientSession()` per request. No connection pooling.
- **Fix**: Create one `ClientSession` per `SharePointClient` lifecycle, reuse across requests, close on teardown.
- **Impact**: Reduces TCP/TLS handshake overhead. Meaningful when polling frequently or downloading many files.
- **Complexity**: Low.

### Priority 4 — Architectural Gaps

#### 4.1 EAV pattern without structured model integration
- **Gap**: All extracted data is stored in `extracted_values` as `(property_name, field_name, value_text)` rows (Entity-Attribute-Value). The `underwriting_models` table with `SourceTrackingMixin` exists but is never populated. This makes queries slow and complex.
- **Fix**: After EAV extraction, materialize key fields into `underwriting_models` (or a dedicated structured table). Use EAV as the raw archive; structured table for dashboard queries.
- **Impact**: Simpler queries, better performance, enables proper FK relationships.
- **Complexity**: High — requires defining which fields to materialize, migration, and dual-write logic.

#### 4.2 Silent last-file-wins for same-property conflicts
- **Gap**: When two files produce the same `property_name` within one extraction run, the second silently overwrites the first via upsert. No logging, no user notification, no conflict resolution.
- **Fix**: Log a warning when a same-run property collision occurs. Optionally store both (version the `source_file`) and let the user choose.
- **Impact**: Prevents silent data loss. Important as deal file counts grow.
- **Complexity**: Medium.

#### 4.3 No retry/resume for failed extractions
- **Gap**: If extraction fails mid-run (e.g., network error during SharePoint download), the entire run is marked `"failed"`. There is no mechanism to resume from where it left off.
- **Fix**: Track per-file status within a run. Add a "resume" mode that skips already-processed files.
- **Impact**: Critical for reliability with large file sets or flaky network conditions.
- **Complexity**: Medium — requires per-file status tracking in DB.

#### 4.4 Market Data Scheduler not wired into app startup
- **Gap**: `MarketDataScheduler` exists with cron configs but `start()` is never called in `main.py` lifespan.
- **Fix**: Add `MarketDataScheduler` initialization alongside UW and file monitor schedulers in `main.py`.
- **Impact**: Enables automated market data refresh without manual triggers.
- **Complexity**: Low — pattern already established by UW scheduler.

### Priority 5 — Monitoring & Observability

#### 5.1 No extraction metrics or alerting
- **Gap**: No Prometheus metrics, no structured logging for extraction duration/throughput/error rates, no alerting on failures.
- **Fix**: Add metrics (files processed/sec, extraction duration, error rate) and alert on consecutive failures or abnormal skip rates.
- **Impact**: Essential for production reliability.
- **Complexity**: Medium.

#### 5.2 Transient metadata discarded
- **Gap**: `_extraction_errors`, `_extraction_metadata` (duration, success/fail counts) are available per-file but never persisted.
- **Fix**: Store per-file extraction metadata (duration, error count, cell success rate) in a dedicated column or table.
- **Impact**: Enables extraction quality monitoring and debugging.
- **Complexity**: Low.

---

*Report generated by 3-analyst parallel review team. All findings are read-only observations with exact code references.*
