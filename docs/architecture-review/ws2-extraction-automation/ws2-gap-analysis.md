# WS2 Deliverable 2: Gap Analysis

**Workstream:** WS2 — Extraction Automation
**Date:** 2026-03-25
**Branch:** `main` at `5bfc8d4`
**Author:** Data Engineer Agent

---

## 1. Full Scan on Every Poll — No Delta Query Support

**Severity:** P2 (Medium) | **Impact:** Performance, API quota, latency

### Current Behavior

Every 30-minute polling cycle performs a **complete recursive scan** of the SharePoint Deals folder hierarchy:

```
discover_deal_folders()  →  1 API call
  per stage folder       →  ~6 API calls
    per deal folder      →  ~100+ API calls
      per UW subfolder   →  ~100+ API calls
                            ─────────────
                            ~200+ API calls per cycle
```

**File:** `backend/app/services/extraction/file_monitor.py`, line 145
```python
discovery_result = await self.client.find_uw_models()
```

This calls `find_uw_models()` which performs the full recursive scan every time.

### What's Missing

Microsoft Graph API provides [delta queries](https://learn.microsoft.com/en-us/graph/api/driveitem-delta) via `/drives/{id}/root/delta` that return only items that have changed since the last query. A delta token is returned with each response and used as a cursor for subsequent requests.

**Impact:** Without delta queries, the system makes ~200+ API calls every 30 minutes regardless of whether any files changed. With delta queries, this would drop to **1-2 API calls per cycle** when nothing has changed.

### Evidence

No reference to `delta` endpoint anywhere in the codebase:
```
$ grep -ri "delta" backend/app/extraction/ → 0 results
$ grep -ri "delta" backend/app/services/extraction/ → 0 results
```

---

## 2. No Webhook Endpoint for Real-Time Notifications

**Severity:** P1 (High) | **Impact:** Latency (up to 30-minute delay)

### Current Behavior

File changes are detected only when the polling cycle runs (every 30 minutes by default). If a user uploads a new UW model at minute 1, the dashboard won't reflect the new data until minute 31.

### What's Missing

Microsoft Graph API supports [webhook subscriptions](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions) that push notifications to a registered endpoint when resources change. The backend has **no webhook endpoint** for receiving Graph API change notifications.

### Requirements for Webhook

1. **Public URL**: The webhook endpoint must be accessible from the internet. The planned Hetzner CX22 deployment will have a public IP.
2. **Validation**: Graph API sends a validation request with a `validationToken` query parameter that must be echoed back as `text/plain`.
3. **Subscription renewal**: Max lifetime is 4230 minutes (~2.9 days). Must be renewed before expiry.
4. **Thin notification**: Webhook only signals that something changed — the actual changes must be fetched separately (via delta query).

### Evidence

No webhook-related code exists:
```
$ grep -ri "webhook" backend/ → 0 results (excluding unrelated security.py)
$ grep -ri "subscription" backend/app/extraction/ → 0 results
```

---

## 3. No Retry Logic for File Downloads

**Severity:** P0 (Critical) | **Impact:** Data loss — failed downloads silently skipped

### Current Behavior

**File:** `backend/app/extraction/sharepoint.py`, lines 595-629

```python
async def download_file(self, file: SharePointFile) -> bytes:
    # ...
    async with session.get(file.download_url) as response:
        response.raise_for_status()      # ← raises on 4xx/5xx
        content = await response.read()
    # ...
    return content
```

**File:** `backend/app/extraction/sharepoint.py`, lines 631-660 (`download_all_uw_models`)

```python
for file in discovery_result.files:
    try:
        content = await self.download_file(file)
        downloaded.append((file, content))
    except Exception as e:
        self.logger.error("download_failed", file=file.name, error=str(e))
        # ← silently moves to next file, no retry
```

### What's Missing

- **No exponential backoff**: A transient 429 (throttled) or 503 (service unavailable) results in immediate failure.
- **No retry count**: Failed downloads are never retried, even once.
- **No distinction between transient and permanent errors**: A 404 (file deleted) and a 503 (temporary outage) receive identical treatment.
- **No download URL refresh**: Pre-authenticated download URLs expire. If the download takes too long or is retried later, the URL may have expired without being refreshed.

### Impact

Microsoft Graph API applies [throttling](https://learn.microsoft.com/en-us/graph/throttling) when request limits are exceeded. A throttled download attempt will permanently fail for that cycle, potentially losing a critical UW model update.

---

## 4. No Dead-Letter Queue for Persistently Failing Files

**Severity:** P1 (High) | **Impact:** Silent data gaps

### Current Behavior

When a file fails to download or extract, the error is logged and the file is skipped. On the next polling cycle, the file may be detected as "modified" again (since it was never successfully extracted), but there is no mechanism to:

1. Track how many times a file has failed consecutively.
2. Quarantine files that persistently fail after N attempts.
3. Alert operators about files stuck in a failure loop.
4. Distinguish between "first failure" and "has been failing for 3 days."

### What's Missing

- **Failure counter** on `MonitoredFile`: No `failure_count`, `last_error`, or `first_failure_at` columns.
- **Dead-letter state**: No concept of a file being quarantined after repeated failures.
- **Alerting integration**: No notification when a file exceeds a failure threshold.

### Evidence

**File:** `backend/app/models/file_monitor.py` — The `MonitoredFile` model has no failure tracking columns. The `extraction_pending` flag is a binary state with no history.

---

## 5. No File Locking Detection

**Severity:** P2 (Medium) | **Impact:** Corrupted/partial extraction

### Current Behavior

The system has no awareness of whether an Excel file is currently open (locked) in SharePoint Online. If a user has the file open in Excel for the Web or the desktop client, and the monitor triggers extraction during an active edit session:

1. The downloaded content may be in an intermediate state.
2. SharePoint may return a stale version (last saved, not current edits).
3. No warning is logged about the lock state.

### What's Missing

Microsoft Graph API exposes file lock information via the [`publication` facet](https://learn.microsoft.com/en-us/graph/api/resources/driveitem) on `driveItem` resources, including `publication.level` (published vs. checkout) and the checkout user. The API also provides `lastModifiedBy` to detect if changes are still in progress.

### Evidence

The `_process_file_item()` method (line 506) reads only `name`, `size`, `lastModifiedDateTime`, and `@microsoft.graph.downloadUrl` from the Graph API response. No check for `publication`, `lock`, or `checkout` properties.

---

## 6. No Concurrent Edit Handling

**Severity:** P2 (Medium) | **Impact:** Stale data extraction

### Current Behavior

If two users edit the same UW model file simultaneously (or in quick succession):

1. The first edit triggers a "modified" detection on the next poll.
2. The extraction runs against the file at that point in time.
3. The second edit (committed after extraction started) is not detected until the next poll, 30 minutes later.
4. No version comparison is performed — the system doesn't check if the file version changed between detection and download.

### What's Missing

- **Version tracking**: Graph API returns `eTag` and `cTag` for every `driveItem`. Comparing these between detection and download would catch mid-download edits.
- **Optimistic concurrency**: No check that the file version at download time matches the version at detection time.

### Evidence

`SharePointFile` dataclass (line 30) stores only `name`, `path`, `download_url`, `size`, `modified_date`, `deal_name`, `deal_stage`. No `etag`, `ctag`, or `version` field.

---

## 7. No Partial Upload Detection

**Severity:** P2 (Medium) | **Impact:** Extraction of incomplete files

### Current Behavior

The system has no mechanism to detect whether a file upload to SharePoint is still in progress. Large Excel files (some UW models are 5-50 MB) may take noticeable time to upload, especially over slower connections. If the monitor polls while an upload is in progress:

1. The file may appear in the listing with a partial size.
2. The download URL may return incomplete content.
3. No size consistency check is performed between the listed size and the downloaded bytes.

### What's Missing

- **Size validation**: Downloaded content size is not compared against the Graph API reported size.
- **Upload session detection**: Graph API upload sessions create files with `pendingOperations` facet. Not checked.

---

## 8. Token Refresh — Handled But Not Monitored

**Severity:** P1 (Low-Medium) | **Impact:** Silent auth degradation

### Current Behavior

Token refresh works correctly at the code level:

- Proactive refresh 5 minutes before expiry (line 185).
- 401 retry with fresh token (lines 230-239).
- `SharePointAuthError` raised on auth failure (line 198).

### What's Missing

- **No alerting on repeated auth failures**: If Azure AD is rejecting tokens (expired secret, revoked permission), the only evidence is log lines. No health check endpoint exposes auth status.
- **No token refresh metrics**: No counter for token refreshes, failures, or latency.
- **Client secret expiry tracking**: Azure AD client secrets have expiration dates. No proactive warning when the secret is approaching expiry.

---

## 9. Idempotent Upserts — No Reconciliation Reporting

**Severity:** P1 (Medium) | **Impact:** Silent data drift

### Current Behavior

The `extracted_values` table has a unique constraint on `(extraction_run_id, property_name, field_name)`, ensuring idempotent upserts within a single run. The `MonitoredFile` state store tracks whether files have been extracted.

### What's Missing

- **Full reconciliation**: No mechanism to compare the set of files in SharePoint against the set of files with extracted values in the database. If a file is present in SharePoint but has no extracted values (perhaps because extraction silently failed), there's no report highlighting this gap.
- **Drift detection**: If extracted values are manually edited or deleted, no reconciliation process detects the divergence.
- **Coverage report**: No dashboard or API endpoint shows "X of Y files have been successfully extracted."

### Evidence

The `check_for_changes()` method (line 119) detects file-level changes but does not verify extraction completeness for existing files.

---

## 10. Miscellaneous Gaps

### 10a. Download URL Expiry

Pre-authenticated download URLs (`@microsoft.graph.downloadUrl`) expire after a limited time (typically ~1 hour). The `download_file()` method refreshes the URL if it's empty (line 606-611) but does not handle expired URLs (they return 403 Forbidden, not empty string).

### 10b. Content Hash Column Unused

`MonitoredFile.content_hash` (line 58-60) is declared as `String(64)` nullable — intended for SHA-256 content-based change detection. However, this column is **never populated** in any code path. Change detection relies solely on `modified_date` and `size_bytes`.

### 10c. `error_category` Column Never Populated

As documented in WS4, the `ErrorHandler` tracks 9 error categories in-memory but never passes them to the `bulk_insert()` call that persists `ExtractedValue` records. This means extraction errors cannot be categorized at the database level for monitoring or alerting.

### 10d. Rate Limiting Not Graph-Aware

The existing rate limiter in middleware (`RATE_LIMIT_REQUESTS = 100 per 60s`) applies to inbound API requests, not outbound Graph API calls. Microsoft Graph has its own throttling limits (varies by resource), but the SharePoint client has no built-in rate limiting to stay below these thresholds.

---

## Gap Summary Matrix

| # | Gap | Severity | Impact | Effort |
|---|-----|----------|--------|--------|
| 1 | Full scan every poll (no delta query) | P2 | API quota, latency | M |
| 2 | No webhook endpoint | P1 | 30-min detection delay | L |
| 3 | No download retry/backoff | P0 | Silent data loss | S |
| 4 | No dead-letter queue | P1 | Persistent silent failures | M |
| 5 | No file locking detection | P2 | Corrupted extraction | S |
| 6 | No concurrent edit handling | P2 | Stale data | M |
| 7 | No partial upload detection | P2 | Incomplete extraction | S |
| 8 | No auth failure alerting | P1 | Silent auth degradation | S |
| 9 | No reconciliation reporting | P1 | Silent data drift | M |
| 10a | Download URL expiry not handled | P2 | Intermittent download failures | S |
| 10b | content_hash column unused | P2 | Metadata-only change detection | S |
| 10c | error_category never populated | P1 | No error classification | S (WS4 scope) |
| 10d | No Graph API rate limiting | P2 | Throttling risk | S |

**Size legend:** S = days, M = 1-2 weeks, L = 2-4 weeks
