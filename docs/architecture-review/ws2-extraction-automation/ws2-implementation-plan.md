# WS2 Deliverable 5: Implementation Plan (BMAD-Style)

**Workstream:** WS2 — Extraction Automation
**Date:** 2026-03-25
**Branch:** `main` at `5bfc8d4`
**Author:** Data Engineer Agent

---

## T-Shirt Sizing Legend

| Size | Effort | Description |
|------|--------|-------------|
| **XS** | < 0.5 day | Config change, simple method addition |
| **S** | 0.5-1 day | Single file change, straightforward logic |
| **M** | 1-3 days | Multi-file change, moderate complexity |
| **L** | 3-5 days | New module or significant refactor |
| **XL** | 5+ days | Major feature with multiple components |

---

## Epic 1: Delta Query Integration

**Priority:** P0 | **Total Estimate:** M-L (5-7 days)
**Goal:** Replace O(folders x files) full scan with O(changes) delta queries.

### Story 1.1: Delta Query Method on SharePointClient

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 1.1.1 | S | `sharepoint.py` | Add `get_delta_changes(delta_token: str \| None) -> tuple[list[dict], str]` method. Handles pagination via `@odata.nextLink`, extracts token from `@odata.deltaLink`. |
| 1.1.2 | S | `sharepoint.py` | Add `_classify_delta_item(item: dict) -> FileChange \| None` helper. Maps Graph API delta response items to existing `FileChange` dataclass. Handle deleted items (`"deleted"` facet). |
| 1.1.3 | S | `sharepoint.py` | Add `_is_uw_model_file(item: dict) -> bool` helper to filter delta results through `FileFilter` (delta returns ALL changed files in the drive, not just UW models). |

**Acceptance Criteria:**
- `get_delta_changes(None)` returns all items in the drive (initial sync).
- `get_delta_changes(token)` returns only items changed since token was issued.
- Deleted items are identified via the `deleted` facet.
- Method handles pagination for large change sets.

### Story 1.2: Delta Token Persistence

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 1.2.1 | S | New: `backend/app/models/delta_token.py` | Create `DeltaToken` SQLAlchemy model: `id`, `drive_id` (unique), `delta_token` (text), `last_sync_at`, `full_scan_at`, `changes_since_full_scan`, timestamps. |
| 1.2.2 | XS | `backend/app/db/base.py` | Register `DeltaToken` model for Alembic discovery. |
| 1.2.3 | S | `backend/alembic/versions/` | New Alembic migration creating `delta_tokens` table. |
| 1.2.4 | S | New: `backend/app/crud/crud_delta_token.py` | CRUD operations: `get_by_drive_id()`, `upsert_token()`, `clear_token()`, `get_last_full_scan()`. |

**Acceptance Criteria:**
- Delta token survives application restart.
- Only one token per drive_id (unique constraint enforced).
- `upsert_token()` updates existing record or creates new.

### Story 1.3: Delta-Aware File Monitor

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 1.3.1 | M | `file_monitor.py` | Add `check_for_changes_delta()` method. Loads delta token from DB, calls `get_delta_changes()`, classifies results, updates `monitored_files`. Falls back to full scan on 410 Gone. |
| 1.3.2 | S | `file_monitor.py` | Modify `check_for_changes()` to call `check_for_changes_delta()` first when `DELTA_QUERY_ENABLED=True`. If delta returns 410 or no token exists, fall back to existing full scan. |
| 1.3.3 | S | `monitor_scheduler.py` | Add config flag `DELTA_QUERY_ENABLED` to control delta vs. full scan behavior. Default: `True`. |
| 1.3.4 | XS | `config.py` | Add `DELTA_QUERY_ENABLED: bool = True` and `DELTA_RECONCILIATION_CRON: str = "0 2 * * *"` to `ExtractionSettings`. |

**Acceptance Criteria:**
- When delta token exists: polling makes 1-2 API calls instead of ~200+.
- When delta token is missing or expired: automatic fallback to full scan.
- `FILE_MONITOR_INTERVAL_MINUTES` still controls poll frequency.
- Delta token updated after each successful delta check.

### Story 1.4: Tests for Delta Integration

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 1.4.1 | S | New: `backend/tests/test_extraction/test_delta_query.py` | Unit tests for `get_delta_changes()`: mock Graph API responses, pagination, expired token (410), initial sync (no token). |
| 1.4.2 | S | New: `backend/tests/test_services/test_file_monitor_delta.py` | Integration tests for `check_for_changes_delta()`: delta token persistence, fallback to full scan, change classification. |
| 1.4.3 | S | `backend/tests/test_crud/test_delta_token.py` | CRUD tests: upsert, get_by_drive_id, clear_token. |

**Acceptance Criteria:**
- All existing file_monitor tests continue to pass (backward compat).
- Delta-specific tests cover: initial sync, incremental sync, token expiry fallback, deleted file detection, pagination.

---

## Epic 2: Retry & Error Resilience

**Priority:** P0-P1 | **Total Estimate:** M (4-6 days)
**Goal:** Download failures are retried with backoff. Persistent failures are quarantined.

### Story 2.1: Download Retry with Exponential Backoff

**Size:** S-M

| Task | Size | File | Description |
|------|------|------|-------------|
| 2.1.1 | S | `sharepoint.py` | Add `download_file_with_retry(file, max_retries=3, base_delay=30)` method. Wraps `download_file()` with retry loop. Exponential backoff: `base_delay * 2^attempt`. |
| 2.1.2 | XS | `sharepoint.py` | Add `_is_transient_error(status_code: int) -> bool` helper. Returns True for 429, 500, 502, 503, 504. |
| 2.1.3 | S | `sharepoint.py` | On 403 during download: call `_refresh_download_url(file)` before retry (pre-auth URL may have expired). |
| 2.1.4 | XS | `sharepoint.py` | On 429: parse `Retry-After` header and use it as delay (instead of exponential backoff) when available. |
| 2.1.5 | S | `config.py` | Add `DOWNLOAD_MAX_RETRIES: int = 3`, `DOWNLOAD_BACKOFF_BASE_SECONDS: int = 30`, `DOWNLOAD_TIMEOUT_SECONDS: int = 120` to `ExtractionSettings`. |

**Acceptance Criteria:**
- Transient errors are retried up to `MAX_RETRIES` times.
- Permanent errors (404, 410) fail immediately without retry.
- `Retry-After` header is respected when present.
- Each retry attempt is logged with structured fields.

### Story 2.2: Dead-Letter Tracking

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 2.2.1 | S | `file_monitor.py` (model) | Add columns to `MonitoredFile`: `failure_count` (int, default 0), `last_error` (text, nullable), `last_failure_at` (datetime, nullable), `quarantined` (bool, default False), `quarantined_at` (datetime, nullable). |
| 2.2.2 | S | `backend/alembic/versions/` | New Alembic migration adding failure tracking columns. |
| 2.2.3 | S | `file_monitor.py` (service) | After extraction failure: increment `failure_count`, set `last_error`. If `failure_count >= MAX_RETRIES`: set `quarantined=True`, `quarantined_at=now()`. |
| 2.2.4 | S | `file_monitor.py` (service) | After successful extraction: reset `failure_count=0`, `last_error=None`, `quarantined=False`. |
| 2.2.5 | S | `file_monitor.py` (service) | Exclude quarantined files from auto-extraction (`_detect_changes` skips them). |

**Acceptance Criteria:**
- File failing 3 times consecutively is quarantined.
- Quarantined files stop being auto-retried.
- Successful extraction resets failure state.
- Quarantine state is visible in API responses.

### Story 2.3: Dead-Letter API Endpoints

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 2.3.1 | S | New: `backend/app/api/v1/endpoints/extraction/dead_letter.py` | `GET /dead-letter` — list quarantined files with failure details. `POST /dead-letter/{id}/retry` — reset failure state and re-trigger extraction. `DELETE /dead-letter/{id}` — permanently dismiss (set `is_active=False`). |
| 2.3.2 | XS | `backend/app/api/v1/api.py` | Register dead-letter router. |

**Acceptance Criteria:**
- List endpoint returns quarantined files with `failure_count`, `last_error`, `quarantined_at`.
- Retry endpoint resets state and enqueues extraction.
- Requires `require_manager` auth guard.

### Story 2.4: Tests for Error Resilience

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 2.4.1 | S | New: `backend/tests/test_extraction/test_download_retry.py` | Tests: retry on 503, no retry on 404, backoff timing, Retry-After parsing, URL refresh on 403. |
| 2.4.2 | S | New: `backend/tests/test_services/test_dead_letter.py` | Tests: quarantine after N failures, reset on success, exclude from auto-extraction, API endpoints. |

---

## Epic 3: Webhook Endpoint

**Priority:** P1 | **Total Estimate:** L (5-8 days)
**Goal:** Receive instant change notifications from Microsoft Graph.
**Prerequisite:** Epic 1 (delta queries) + public URL (Hetzner deployment).

### Story 3.1: Webhook Route

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 3.1.1 | S | New: `backend/app/api/v1/endpoints/extraction/webhook.py` | `POST /webhook` endpoint. Handles validation handshake (echo `validationToken` as `text/plain`). Handles change notification (verify `clientState`, enqueue delta check). |
| 3.1.2 | XS | `backend/app/api/v1/api.py` | Register webhook router (no auth prefix — endpoint is public). |
| 3.1.3 | S | `webhook.py` | Add `clientState` validation. Reject notifications where `clientState != settings.GRAPH_WEBHOOK_SECRET`. |
| 3.1.4 | XS | `webhook.py` | Respond with 202 Accepted within 3 seconds (Graph API requirement). Process actual work asynchronously. |

**Acceptance Criteria:**
- Validation request: returns `validationToken` as `text/plain` with 200.
- Notification: validates `clientState`, enqueues delta check, returns 202.
- Invalid `clientState`: logs warning, returns 202 (don't reveal validation to attacker).

### Story 3.2: Subscription Manager

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 3.2.1 | M | New: `backend/app/services/extraction/webhook_manager.py` | `WebhookSubscriptionManager` class with `create_subscription()`, `renew_subscription()`, `delete_subscription()`, `get_subscription()`. |
| 3.2.2 | S | `webhook_manager.py` | Store subscription ID and expiry in `delta_tokens` table (add `webhook_subscription_id` and `webhook_expiry` columns) or new table. |
| 3.2.3 | XS | `config.py` | Add settings: `GRAPH_WEBHOOK_ENABLED`, `GRAPH_WEBHOOK_SECRET`, `PUBLIC_BASE_URL`. |

**Acceptance Criteria:**
- `create_subscription()` calls `POST /subscriptions` with correct payload.
- `renew_subscription()` calls `PATCH /subscriptions/{id}` to extend expiry.
- Subscription ID is persisted for renewal across restarts.

### Story 3.3: Subscription Renewal Job

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 3.3.1 | S | `monitor_scheduler.py` | Add APScheduler job for subscription renewal (every 2 days). Uses `IntervalTrigger(days=2)`. |
| 3.3.2 | XS | `monitor_scheduler.py` | On startup: check if subscription exists and is valid. If expired or missing, create new subscription. |
| 3.3.3 | XS | `monitor_scheduler.py` | On shutdown: optionally delete subscription (configurable — useful for dev, not prod). |

**Acceptance Criteria:**
- Subscription is renewed before 4230-minute expiry.
- Startup creates subscription if none exists.
- Renewal failure is logged at ERROR level with retry on next interval.

### Story 3.4: Webhook Debouncing

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 3.4.1 | S | `webhook.py` or new `debounce.py` | Redis-based debounce: when webhook fires, check `extraction:last_delta_check` key in Redis. If less than 10 seconds ago, skip. Otherwise, set key and enqueue delta check. |
| 3.4.2 | XS | N/A | Configure debounce window via `WEBHOOK_DEBOUNCE_SECONDS: int = 10`. |

**Acceptance Criteria:**
- Rapid webhook notifications (Graph may send multiple for one save) are coalesced into a single delta check.
- Debounce state uses Redis TTL for automatic cleanup.

### Story 3.5: Webhook Tests

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 3.5.1 | S | New: `backend/tests/test_api/test_webhook.py` | Tests: validation handshake, valid notification, invalid clientState, debounce. |
| 3.5.2 | S | New: `backend/tests/test_services/test_webhook_manager.py` | Tests: create subscription (mock Graph API), renew subscription, handle expired subscription. |

---

## Epic 4: Reconciliation & Reporting

**Priority:** P1 | **Total Estimate:** M (3-5 days)
**Goal:** Verify extraction coverage and detect drift.

### Story 4.1: Reconciliation Service

**Size:** M

| Task | Size | File | Description |
|------|------|------|-------------|
| 4.1.1 | M | New: `backend/app/services/extraction/reconciliation.py` | `ReconciliationService` with `run_reconciliation()` method. Compares `monitored_files` (active) against `extracted_values` (latest run). Produces coverage stats. |
| 4.1.2 | S | `reconciliation.py` | Identify: (a) files with no extracted values, (b) files where extracted values are stale (file modified after last extraction), (c) files with extraction errors. |
| 4.1.3 | S | New: `backend/app/models/reconciliation.py` | `ReconciliationReport` model: `id`, `run_at`, `total_files`, `extracted_files`, `missing_files`, `stale_files`, `error_files`, `details_json`, timestamps. |
| 4.1.4 | S | `backend/alembic/versions/` | New Alembic migration for `reconciliation_reports` table. |

**Acceptance Criteria:**
- Reconciliation identifies all coverage gaps.
- Report is persisted for historical comparison.
- `details_json` contains per-file breakdown for debugging.

### Story 4.2: Reconciliation Scheduler

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 4.2.1 | S | `monitor_scheduler.py` | Add daily reconciliation job (cron: `DELTA_RECONCILIATION_CRON`, default `0 2 * * *`). This runs a full scan + reconciliation comparison. |
| 4.2.2 | XS | `reconciliation.py` | If missing/stale files found and `AUTO_EXTRACT_ON_CHANGE=True`, optionally trigger re-extraction. |

**Acceptance Criteria:**
- Daily reconciliation runs at 2 AM MST.
- Missing files are flagged (not silently re-extracted unless configured).

### Story 4.3: Reconciliation API

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 4.3.1 | S | New: `backend/app/api/v1/endpoints/extraction/reconciliation.py` | `GET /reconciliation/latest` — return latest reconciliation report. `GET /reconciliation/history` — paginated report history. `POST /reconciliation/trigger` — manually trigger reconciliation. |
| 4.3.2 | XS | `backend/app/api/v1/api.py` | Register reconciliation router. |

**Acceptance Criteria:**
- Latest report shows coverage percentage and lists missing files.
- Manual trigger runs reconciliation on-demand.
- Requires `require_analyst` auth guard.

### Story 4.4: Reconciliation Tests

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 4.4.1 | S | New: `backend/tests/test_services/test_reconciliation.py` | Tests: full coverage (no gaps), missing files detected, stale files detected, report persistence. |
| 4.4.2 | XS | New: `backend/tests/test_api/test_reconciliation_endpoint.py` | API tests: get latest, get history, trigger manual reconciliation. |

---

## Epic 5: File Locking & Concurrent Edits

**Priority:** P2 | **Total Estimate:** S-M (3-4 days)
**Goal:** Detect and handle files that are locked or being edited.

### Story 5.1: File Lock Detection

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 5.1.1 | S | `sharepoint.py` | In `_process_file_item()`, check for `publication` facet in Graph API response. If `publication.level == "checkout"`, add to `SkippedFile` with reason `"file_locked"`. |
| 5.1.2 | XS | `sharepoint.py` | Add `locked_by: str \| None` field to `SharePointFile` dataclass. Populate from `lastModifiedBy.user.displayName` when file is locked. |
| 5.1.3 | XS | `file_monitor.py` | Log locked files as a structured warning with deal name and lock holder. |

**Acceptance Criteria:**
- Locked files are skipped during extraction with clear reason.
- Locked files are retried on next poll cycle.
- Lock state is visible in monitoring logs and API response.

### Story 5.2: ETag-Based Version Comparison

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 5.2.1 | XS | `sharepoint.py` | Add `etag: str \| None` field to `SharePointFile` dataclass. Populate from Graph API `eTag` property in `_process_file_item()`. |
| 5.2.2 | S | `file_monitor.py` (model) | Add `etag: str \| None` column to `MonitoredFile`. Alembic migration. |
| 5.2.3 | S | `sharepoint.py` | In `download_file_with_retry()`: before extraction, fetch current `eTag` via `GET /drives/{id}/root:/{path}`. If `eTag` differs from stored value, re-download. |
| 5.2.4 | XS | `file_monitor.py` (service) | Store `eTag` in `MonitoredFile` during state update. |

**Acceptance Criteria:**
- Files that change between detection and download are re-fetched.
- ETag mismatch is logged as a warning.
- ETag stored in DB for historical tracking.

### Story 5.3: Content Hash Population

**Size:** XS

| Task | Size | File | Description |
|------|------|------|-------------|
| 5.3.1 | XS | `file_monitor.py` (service) | After successful download, compute SHA-256 hash of file content. Store in `MonitoredFile.content_hash`. |
| 5.3.2 | XS | `file_monitor.py` (service) | Add content hash comparison as tertiary change detection signal (after modified_date and size). |

**Acceptance Criteria:**
- `content_hash` is populated for all successfully downloaded files.
- Content hash mismatch (same date/size but different hash) triggers extraction.

### Story 5.4: Tests for Locking & Versioning

**Size:** S

| Task | Size | File | Description |
|------|------|------|-------------|
| 5.4.1 | S | New: `backend/tests/test_extraction/test_file_locking.py` | Tests: locked file skipped, lock holder logged, retry on next cycle. |
| 5.4.2 | S | New: `backend/tests/test_extraction/test_version_check.py` | Tests: eTag mismatch triggers re-download, content hash change detected. |

---

## Implementation Timeline

### Sprint 1 (Week 1-2): P0 Foundation

| Day | Epic | Story | Focus |
|-----|------|-------|-------|
| 1-2 | E2 | 2.1 | Download retry with backoff |
| 3-4 | E1 | 1.1 | Delta query method |
| 5 | E1 | 1.2 | Delta token model + migration |
| 6-7 | E1 | 1.3 | Delta-aware FileMonitor |
| 8 | E1 | 1.4 | Delta integration tests |
| 9-10 | E2 | 2.2-2.3 | Dead-letter tracking + API |

### Sprint 2 (Week 3-4): P1 Webhook + Reconciliation

| Day | Epic | Story | Focus |
|-----|------|-------|-------|
| 1-2 | E3 | 3.1 | Webhook route |
| 3-4 | E3 | 3.2-3.3 | Subscription manager + renewal |
| 5 | E3 | 3.4 | Debouncing |
| 6-7 | E4 | 4.1-4.2 | Reconciliation service + scheduler |
| 8 | E4 | 4.3 | Reconciliation API |
| 9-10 | E3-E4 | 3.5, 4.4 | Tests for webhook + reconciliation |

### Sprint 3 (Week 5, partial): P2 Polish

| Day | Epic | Story | Focus |
|-----|------|-------|-------|
| 1 | E5 | 5.1 | File lock detection |
| 2 | E5 | 5.2 | ETag version comparison |
| 3 | E5 | 5.3 | Content hash population |
| 4 | E5 | 5.4 | Tests |

---

## Definition of Done (per Epic)

- [ ] All stories implemented and code reviewed
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Existing test suite unaffected (zero regressions)
- [ ] Alembic migrations created and tested (up + down)
- [ ] Configuration documented in `.env.example`
- [ ] Feature flags allow disabling new functionality
- [ ] Structured logging for all new operations
- [ ] No new linter warnings (ruff, ESLint)

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Graph API delta token expires mid-operation | Medium | Low | Automatic fallback to full scan (Story 1.3) |
| Webhook endpoint not reachable (firewall/DNS) | Medium | Medium | Delta polling continues to work as backup |
| Redis unavailable | Low | High | Task queue falls back to inline processing; debounce skipped |
| Graph API throttling during delta sync | Low | Medium | Retry-After parsing + backoff (Story 2.1) |
| Azure AD client secret expires | Medium | High | Auth health check + alerting (P1-4) |
| Alembic migration conflicts with other workstreams | Low | Low | Coordinate migration chain with WS1/WS3/WS4 |

---

## New Files Created (Summary)

| File | Epic | Purpose |
|------|------|---------|
| `backend/app/models/delta_token.py` | E1 | DeltaToken SQLAlchemy model |
| `backend/app/crud/crud_delta_token.py` | E1 | Delta token CRUD operations |
| `backend/app/api/v1/endpoints/extraction/webhook.py` | E3 | Graph API webhook endpoint |
| `backend/app/services/extraction/webhook_manager.py` | E3 | Subscription lifecycle management |
| `backend/app/services/extraction/reconciliation.py` | E4 | Coverage verification service |
| `backend/app/models/reconciliation.py` | E4 | ReconciliationReport model |
| `backend/app/api/v1/endpoints/extraction/reconciliation.py` | E4 | Reconciliation API endpoints |
| `backend/app/api/v1/endpoints/extraction/dead_letter.py` | E2 | Dead-letter management endpoints |
| `backend/app/services/extraction/task_queue.py` | Cross-cutting | Asyncio + Redis task queue |

## Existing Files Modified (Summary)

| File | Epics | Changes |
|------|-------|---------|
| `backend/app/extraction/sharepoint.py` | E1, E2, E5 | Delta query, retry, lock detection, eTag |
| `backend/app/services/extraction/file_monitor.py` | E1, E2, E5 | Delta-aware check, failure tracking, content hash |
| `backend/app/services/extraction/monitor_scheduler.py` | E1, E3, E4 | Delta config, renewal job, reconciliation job |
| `backend/app/models/file_monitor.py` | E2, E5 | Failure columns, eTag column |
| `backend/app/core/config.py` | E1, E2, E3 | New settings for delta, retry, webhook |
| `backend/app/db/base.py` | E1, E4 | Register new models |
| `backend/app/api/v1/api.py` | E2, E3, E4 | Register new routers |
