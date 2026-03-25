# WS2 Deliverable 4: Prioritized Recommendations

**Workstream:** WS2 — Extraction Automation
**Date:** 2026-03-25
**Branch:** `main` at `5bfc8d4`
**Author:** Data Engineer Agent

---

## Priority Legend

| Priority | Meaning | Timeline |
|----------|---------|----------|
| **P0** | Must fix before production deployment | This sprint |
| **P1** | Should fix before production or within first month | Next 2-4 weeks |
| **P2** | Technical debt to address post-launch | Backlog |

---

## P0 — Critical (Production Blockers)

### P0-1: Download Retry Logic with Exponential Backoff

**Gap:** #3 in gap analysis
**Files affected:**
- `backend/app/extraction/sharepoint.py` (lines 595-660)

**Problem:** File downloads have zero retry logic. A single transient error (429 throttled, 503 unavailable, network timeout) causes permanent failure for that file in the current cycle. On a ~100-file scan, even a 1% transient failure rate means 1 file lost per cycle.

**Recommendation:**
1. Add a `download_with_retry()` method to `SharePointClient` with configurable max retries (default 3).
2. Use exponential backoff: `base_delay * 2^attempt` (30s, 60s, 120s).
3. Refresh download URL on 403 (expired pre-auth URL).
4. Distinguish transient errors (429, 500, 502, 503, 504, timeout) from permanent errors (404, 410).
5. Log each retry attempt with structured fields (attempt number, delay, error code).

**Effort:** S (1-2 days)
**Dependencies:** None

### P0-2: Delta Query Support (Replace Full Poll)

**Gap:** #1 in gap analysis
**Files affected:**
- `backend/app/extraction/sharepoint.py` (add `get_delta_changes()`)
- `backend/app/services/extraction/file_monitor.py` (add `check_for_changes_delta()`)
- New: `backend/app/models/delta_token.py`
- New: Alembic migration for `delta_tokens` table

**Problem:** Every 30-minute poll makes ~200+ Graph API calls regardless of whether anything changed. This is wasteful, slow, and risks hitting Microsoft's throttling limits as the deal count grows.

**Recommendation:**
1. Add `get_delta_changes(delta_token)` to `SharePointClient` using `/drives/{id}/root/delta`.
2. Create `delta_tokens` table to persist the delta token across restarts.
3. Modify `FileMonitor.check_for_changes()` to use delta query first, with automatic fallback to full scan when:
   - No delta token exists (first run).
   - Delta token expired (410 Gone response).
   - Configured full-reconciliation interval exceeded (daily).
4. Keep the existing full-scan code path as the fallback — do not delete it.

**Effort:** M (3-5 days)
**Dependencies:** None

---

## P1 — High (Should Fix Before or Shortly After Production)

### P1-1: Webhook Endpoint for Instant Notifications

**Gap:** #2 in gap analysis
**Files affected:**
- New: `backend/app/api/v1/endpoints/extraction/webhook.py`
- New: `backend/app/services/extraction/webhook_manager.py`
- `backend/app/services/extraction/monitor_scheduler.py` (add renewal job)
- `backend/app/core/config.py` (add `GRAPH_WEBHOOK_*` settings)

**Problem:** File changes are not detected until the next polling cycle (up to 30 minutes). For time-sensitive deal updates, this delay can cause stale dashboard data during active work sessions.

**Recommendation:**
1. Add `POST /api/v1/extraction/webhook` endpoint (public, no JWT).
2. Implement Graph API validation handshake (echo `validationToken`).
3. Verify `clientState` on every notification for security.
4. On notification: debounce (10-second window), then trigger delta query.
5. Add `WebhookSubscriptionManager` for create/renew/delete lifecycle.
6. APScheduler job to renew subscription every 2 days (max lifetime 4230 min).
7. Requires `PUBLIC_BASE_URL` configured (Hetzner public IP + domain).

**Effort:** L (5-8 days)
**Dependencies:** P0-2 (delta query must exist for webhook to trigger)
**Note:** Can only be activated after Hetzner deployment (needs public URL).

### P1-2: Dead-Letter Tracking for Persistently Failing Files

**Gap:** #4 in gap analysis
**Files affected:**
- `backend/app/models/file_monitor.py` (add columns to `MonitoredFile`)
- New: Alembic migration
- `backend/app/services/extraction/file_monitor.py` (failure tracking logic)

**Problem:** Files that fail extraction repeatedly are silently retried every cycle without any escalation. Operators have no visibility into which files are stuck.

**Recommendation:**
1. Add columns to `MonitoredFile`:
   - `failure_count: int = 0`
   - `last_error: str | None`
   - `last_failure_at: datetime | None`
   - `quarantined: bool = False`
   - `quarantined_at: datetime | None`
2. After `MAX_RETRIES` (default 3) consecutive failures, set `quarantined=True`.
3. Quarantined files are excluded from auto-extraction but remain visible.
4. Add API endpoint `GET /api/v1/extraction/dead-letter` to list quarantined files.
5. Add `POST /api/v1/extraction/dead-letter/{id}/retry` to manually retry.

**Effort:** M (2-3 days)
**Dependencies:** None

### P1-3: Reconciliation Report (Coverage Verification)

**Gap:** #9 in gap analysis
**Files affected:**
- New: `backend/app/services/extraction/reconciliation.py`
- New: `backend/app/api/v1/endpoints/extraction/reconciliation.py`

**Problem:** No mechanism verifies that all files in SharePoint have been successfully extracted. If extraction silently fails for a file, the gap is never surfaced.

**Recommendation:**
1. Daily reconciliation job (via APScheduler, after the daily full scan):
   - List all active files in `monitored_files`.
   - For each file, check if corresponding `extracted_values` exist in the latest run.
   - Produce a coverage report: `{total_files, extracted_files, missing_files, stale_files}`.
2. `stale_files` = files where `monitored_files.modified_date > extracted_values.created_at` for the latest run.
3. Store report in new `reconciliation_reports` table.
4. Expose via `GET /api/v1/extraction/reconciliation/latest`.
5. Optionally trigger re-extraction for missing/stale files.

**Effort:** M (2-3 days)
**Dependencies:** P0-2 (integrates with delta query reconciliation)

### P1-4: Auth Failure Alerting

**Gap:** #8 in gap analysis
**Files affected:**
- `backend/app/extraction/sharepoint.py` (add metrics/alerting hooks)
- `backend/app/api/v1/endpoints/health.py` (add SharePoint auth check)

**Problem:** If Azure AD starts rejecting tokens (expired client secret, revoked permission, misconfigured tenant), the only evidence is log lines buried in output. No proactive notification.

**Recommendation:**
1. Add SharePoint auth status to the deep health check endpoint:
   ```json
   { "sharepoint": { "status": "ok", "last_token_refresh": "...", "token_expires_in_seconds": 2400 } }
   ```
2. Track consecutive auth failures in Redis counter (`extraction:auth_failures`).
3. If auth failures exceed threshold (3 in 10 minutes), log at CRITICAL level.
4. Future: integrate with email alerting service (already exists in codebase).

**Effort:** S (1-2 days)
**Dependencies:** Redis

---

## P2 — Medium (Technical Debt / Post-Launch)

### P2-1: File Locking Detection

**Gap:** #5 in gap analysis
**Files affected:**
- `backend/app/extraction/sharepoint.py` (`_process_file_item`)
- `backend/app/services/extraction/file_monitor.py`

**Problem:** Extracting a file while it's open in Excel Online can yield stale or intermediate data.

**Recommendation:**
1. When processing file items, check for `publication.level` in the Graph API response.
2. If `publication.level == "checkout"`, add to `SkippedFile` with reason `"file_locked"`.
3. Log the lock holder user if available.
4. Locked files should be retried on the next poll cycle.

**Effort:** S (1 day)
**Dependencies:** May require `Sites.ReadWrite.All` scope to read publication facet (verify).

### P2-2: Concurrent Edit Handling (Version Comparison)

**Gap:** #6 in gap analysis
**Files affected:**
- `backend/app/extraction/sharepoint.py` (`SharePointFile` dataclass, `download_file`)

**Problem:** File may change between detection and download, leading to stale extraction.

**Recommendation:**
1. Add `etag` field to `SharePointFile` dataclass.
2. Store `eTag` from the Graph API `driveItem` response during discovery.
3. Before extraction, fetch current `eTag` and compare against stored value.
4. If `eTag` differs, re-download the file before extracting.
5. Add `etag` column to `MonitoredFile` model.

**Effort:** S (1-2 days)
**Dependencies:** None

### P2-3: Content Hash Population

**Gap:** #10b in gap analysis
**Files affected:**
- `backend/app/services/extraction/file_monitor.py` (`_update_stored_state`)

**Problem:** `MonitoredFile.content_hash` column exists but is never populated. Content-based change detection would catch edits that don't change file size or are uploaded with the same timestamp (rare but possible).

**Recommendation:**
1. After downloading a file for extraction, compute SHA-256 hash.
2. Store in `MonitoredFile.content_hash`.
3. Add content hash comparison as a third change detection signal (alongside modified_date and size).

**Effort:** S (half day)
**Dependencies:** None

### P2-4: Graph API Rate Limiting

**Gap:** #10d in gap analysis
**Files affected:**
- `backend/app/extraction/sharepoint.py` (`_make_request`)

**Problem:** No outbound rate limiting for Graph API calls. If extraction processes many files simultaneously, throttling (429) responses are handled reactively rather than proactively.

**Recommendation:**
1. Add an asyncio semaphore to limit concurrent Graph API requests (default: 10).
2. Handle 429 responses with `Retry-After` header parsing.
3. Add a short delay between batch API calls (100ms) to stay below burst limits.

**Effort:** S (1 day)
**Dependencies:** None

### P2-5: Download URL Expiry Handling

**Gap:** #10a in gap analysis
**Files affected:**
- `backend/app/extraction/sharepoint.py` (`download_file`)

**Problem:** Pre-authenticated download URLs expire (~1 hour). If extraction is queued and starts after the URL expires, the download fails with 403.

**Recommendation:**
1. On 403 response during download, refresh the download URL via Graph API.
2. Retry the download with the fresh URL (count as one retry attempt).
3. This should be integrated with P0-1 retry logic.

**Effort:** S (included in P0-1)
**Dependencies:** P0-1

---

## Recommendation Summary

| ID | Recommendation | Priority | Effort | Dependencies |
|----|---------------|----------|--------|--------------|
| P0-1 | Download retry with exponential backoff | **P0** | S | None |
| P0-2 | Delta query support | **P0** | M | None |
| P1-1 | Webhook endpoint | **P1** | L | P0-2 |
| P1-2 | Dead-letter tracking | **P1** | M | None |
| P1-3 | Reconciliation report | **P1** | M | P0-2 |
| P1-4 | Auth failure alerting | **P1** | S | Redis |
| P2-1 | File locking detection | **P2** | S | None |
| P2-2 | Version comparison (eTag) | **P2** | S | None |
| P2-3 | Content hash population | **P2** | S | None |
| P2-4 | Graph API rate limiting | **P2** | S | None |
| P2-5 | Download URL expiry handling | **P2** | S | P0-1 |

### Execution Order

```
P0-1 (retry) ──┐
               ├──> P1-2 (dead letter) ──> P1-3 (reconciliation)
P0-2 (delta) ──┤
               └──> P1-1 (webhook) ──> P2-1 (locking)
                                   ──> P2-2 (eTag)
P1-4 (auth alerting) ── independent
P2-3 (content hash) ── independent
P2-4 (rate limiting) ── independent
```

### Total Effort Estimate

| Priority | Items | Estimated Days |
|----------|-------|---------------|
| P0 | 2 | 5-7 days |
| P1 | 4 | 7-11 days |
| P2 | 5 | 4-6 days |
| **Total** | **11** | **16-24 days** |
