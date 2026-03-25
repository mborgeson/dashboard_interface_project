# Architecture Review v3 -- Unified Recommendations

**Date:** 2026-03-25 | **Total Items:** 41 (10 P0, 16 P1, 15 P2)

Cross-referenced and deduplicated from WS1 (10 items), WS2 (11 items), WS3 (10 items), WS4 (13 items).

---

## P0 -- Critical (Must Fix Before Production)

### UR-001: Populate error_category in Extraction Pipeline
**Source:** WS4 R-01, WS1 R-009
**What:** Wire `ErrorHandler.errors` into the `error_categories` dict parameter of `ExtractedValueCRUD.bulk_insert()` at both production call sites (`group_pipeline.py` line 818, `common.py` line 410).
**Why:** The column is always NULL. No way to distinguish missing sheets from formula errors without parsing logs.
**Effort:** S | **Dependencies:** None

### UR-002: Flag and Review Tier 1b Matches (Confidence 0.85)
**Source:** WS4 R-02
**What:** Add `label_verified = False` flag on Tier 1b matches. Log warnings for values outside domain range. Generate per-group Tier 1b review report.
**Why:** Tier 1b looks reliable (0.85 confidence) but may silently read from a shifted cell. Financial decisions at risk.
**Effort:** M | **Dependencies:** None

### UR-003: Differentiate Null Types in Error Handling
**Source:** WS4 R-03
**What:** Stop collapsing empty cells, "N/A", "TBD", and formula errors into indistinguishable `np.nan`. Preserve each as distinct: empty = not-error NULL, formula error = is_error with category, placeholder text = not-error with text.
**Why:** Conflation masks template problems and data quality issues.
**Effort:** M | **Dependencies:** UR-001

### UR-004: Enable Redis with Correct Authentication
**Source:** WS1 R-001, WS1 R-005
**What:** Install Redis on WSL2, fix `REDIS_URL` to include password, verify connectivity. Token blacklist, cache, rate limiter, and pub/sub all depend on Redis.
**Why:** Without Redis, all four subsystems silently degrade to in-memory (lost on restart). User confirmed: enable now.
**Effort:** S | **Dependencies:** None

### UR-005: Add Redis Startup Validation
**Source:** WS1 R-002
**What:** Add `REDIS_REQUIRED` config setting. If true and Redis unreachable, fail startup. Log clearly whether using Redis or fallback.
**Why:** Silent degradation to in-memory is dangerous in production.
**Effort:** S | **Dependencies:** UR-004

### UR-006: StageChangeLog Audit Trail
**Source:** WS3 R-01
**What:** Create `StageChangeLog` model recording every stage transition: old/new stage, source (sharepoint_sync, user_kanban, extraction_sync, manual_override), user ID, timestamp, reason. Create central `change_deal_stage()` function. Retrofit all 3 existing callers.
**Why:** No way to answer "When did this deal change stage?" or "Was this automatic?" Compliance and operational visibility requirement.
**Effort:** M | **Dependencies:** UR-007

### UR-007: Unify Folder Mapping to Single Source of Truth
**Source:** WS3 R-02
**What:** Create `stage_mapping.py` as canonical mapping. Replace `_infer_deal_stage()` substring matching with path-component lookup. Replace `STAGE_FOLDER_MAP` in `common.py` with derived import. Fix frontend folder names.
**Why:** Two independent mappings with different logic. Substring matching is fragile (deal name collisions).
**Effort:** S | **Dependencies:** None

### UR-008: Fix stage_updated_at Inconsistency
**Source:** WS3 R-05
**What:** Ensure `stage_updated_at` is always set on stage change, regardless of code path. Resolved automatically if UR-006 is implemented (central function sets it).
**Why:** Analytics dashboard relies on this field for recent stage movements. Currently NULL for Kanban and extraction sync paths.
**Effort:** XS | **Dependencies:** UR-006 (free with central function)

### UR-009: Download Retry with Exponential Backoff
**Source:** WS2 P0-1
**What:** Add `download_file_with_retry()` to SharePointClient. Exponential backoff (30s, 60s, 120s). Refresh URL on 403. Respect Retry-After header. Distinguish transient (429, 5xx) from permanent (404, 410) errors.
**Why:** A single transient error causes permanent failure for that file in the current cycle.
**Effort:** S | **Dependencies:** None

### UR-010: Delta Query Support (Replace Full Poll)
**Source:** WS2 P0-2
**What:** Add `get_delta_changes()` to SharePointClient using `/drives/{id}/root/delta`. Create `delta_tokens` table. Modify FileMonitor to use delta first with fallback to full scan on 410 Gone or missing token.
**Why:** ~200+ Graph API calls every 30 minutes regardless of changes. Wasteful, slow, throttling risk.
**Effort:** M | **Dependencies:** None

---

## P1 -- Important (Fix Before or Shortly After Production)

### UR-011: Unify Logging to Loguru
**Source:** WS1 R-003
**What:** Migrate 35 structlog files to loguru. Remove `setup_structlog()` and structlog dependency.
**Why:** Two logging systems produce two output formats. Loguru is the project standard (67 files).
**Effort:** M | **Dependencies:** None

### UR-012: Verify Correlation IDs in Log Output
**Source:** WS1 R-004, WS1 R-010
**What:** Set meaningful `request_id_ctx` values for background tasks (report worker, extraction scheduler, cache cleanup, market data scheduler).
**Why:** Background tasks log with `request_id = "-"`, making them hard to distinguish in aggregated logs.
**Effort:** S | **Dependencies:** None

### UR-013: Standardize Frontend API Client Imports
**Source:** WS1 R-006
**What:** Change 6 files from `@/lib/api/client` to `@/lib/api`. Optionally add ESLint rule to ban direct client imports.
**Why:** Inconsistent imports create confusion. Both paths resolve to the same module.
**Effort:** S | **Dependencies:** None

### UR-014: Webhook Endpoint for Instant Notifications
**Source:** WS2 P1-1
**What:** Add `POST /api/v1/extraction/webhook` (public, no JWT). Graph API validation handshake. clientState verification. Debounce (10s via Redis). Subscription renewal every 2 days.
**Why:** Up to 30-minute detection delay for file changes. Stale dashboard data during active work sessions.
**Effort:** L | **Dependencies:** UR-010 (delta queries), UR-004 (Redis for debounce), public URL (Hetzner)

### UR-015: Dead-Letter Tracking for Failing Files
**Source:** WS2 P1-2
**What:** Add failure tracking columns to MonitoredFile (failure_count, last_error, quarantined). After 3 consecutive failures, quarantine. Add API for listing and retrying quarantined files.
**Why:** Persistently failing files are silently retried every cycle without escalation.
**Effort:** M | **Dependencies:** None

### UR-016: Reconciliation Report (Coverage Verification)
**Source:** WS2 P1-3
**What:** Daily reconciliation job comparing `monitored_files` against `extracted_values`. Produce coverage report. Store in `reconciliation_reports` table. Expose via API.
**Why:** No mechanism verifies all files have been successfully extracted.
**Effort:** M | **Dependencies:** UR-010

### UR-017: Auth Failure Alerting
**Source:** WS2 P1-4
**What:** Add SharePoint auth status to health check. Track consecutive auth failures in Redis counter. Log CRITICAL if threshold exceeded.
**Why:** Azure AD token rejection is only visible in buried log lines.
**Effort:** S | **Dependencies:** UR-004 (Redis)

### UR-018: Stage Change WebSocket Notifications
**Source:** WS3 R-03
**What:** Emit WebSocket notifications from `_sync_deal_stages()` and `_batch_update_deal_stages()`. Bulk event for >5 deals. Use existing `ws_manager.notify_deal_update()`.
**Why:** Dashboard users do not see real-time updates for SharePoint-originated stage changes.
**Effort:** S | **Dependencies:** UR-006

### UR-019: Deletion Policy (Mark DEAD When Files Removed)
**Source:** WS3 R-04
**What:** When all files for a deal are removed from SharePoint, move deal to DEAD (unless CLOSED/REALIZED). Configurable via `STAGE_SYNC_DELETE_POLICY`.
**Why:** Orphaned deals remain in their last stage indefinitely, cluttering the Kanban board.
**Effort:** S | **Dependencies:** UR-006

### UR-020: Bulk Move Batch Query Optimization
**Source:** WS3 R-06
**What:** Replace N-query-per-deal pattern in `_sync_deal_stages()` with single batch SELECT + in-memory matching.
**Why:** Performance optimization for bulk folder reorganizations. Current: O(n) queries.
**Effort:** S | **Dependencies:** None

### UR-021: Extract 28 Ungrouped Files
**Source:** WS4 R-04
**What:** Form 3-4 new groups by sheet count (28/32/33/29-sheet clusters). Run fingerprinting, mapping, and extraction. Handle 3 singleton files individually.
**Why:** 28 files represent ~25 deals with zero extracted data, invisible on dashboard.
**Effort:** M | **Dependencies:** UR-001 (error_category for new extractions)

### UR-022: Financial Domain Range Validation
**Source:** WS4 R-05
**What:** Implement Pydantic-based domain range validators (cap rate < 25%, price > 0, DSCR < 5). Flag out-of-range values without rejecting. Integrate into `bulk_insert()`.
**Why:** Any numeric value is currently accepted without question.
**Effort:** M | **Dependencies:** UR-001

### UR-023: Schema Drift Detection
**Source:** WS4 R-06
**What:** Create `SchemaDriftDetector` comparing file fingerprints against stored baselines. Alert when structural overlap < 90%. Integrate as pre-extraction check.
**Why:** Template changes silently break extraction, producing wrong values.
**Effort:** L | **Dependencies:** None

### UR-024: Create field_synonyms.json
**Source:** WS4 R-07
**What:** Build synonym dictionary mapping field name variations to canonical names, activating Tier 4 matching.
**Why:** Tier 4 matching is completely inoperative because the synonym file does not exist.
**Effort:** S | **Dependencies:** None

### UR-025: Fix Discovery Document Tier Descriptions
**Source:** WS4 R-08
**What:** Correct tier confidence values in `04-etl-mapping.md` to match actual code. Add Tier 1a/1b distinction.
**Why:** Documentation states wrong confidence values, leading to wrong risk assessments.
**Effort:** S | **Dependencies:** None

### UR-026: Verify Auth System End-to-End
**Source:** WS1 Epic 4
**What:** Manually verify refresh token flow (auto-refresh, concurrent dedup, refresh failure -> logout). Verify REFRESH_TOKEN_SECRET separation.
**Why:** Auth flow has not been end-to-end tested with Redis-backed blacklist.
**Effort:** S | **Dependencies:** UR-004 (Redis)

---

## P2 -- Nice to Have (Technical Debt / Post-Launch)

### UR-027: Remove deploy.yml.disabled Artifact
**Source:** WS1 R-007
**What:** Delete `.github/workflows/deploy.yml.disabled`.
**Effort:** XS | **Dependencies:** None

### UR-028: Structured SharePoint Health Check
**Source:** WS1 R-008
**What:** Extend health check to attempt actual Graph API call with 3-second timeout.
**Effort:** M | **Dependencies:** None

### UR-029: File Locking Detection
**Source:** WS2 P2-1
**What:** Check `publication.level` in Graph API response. Skip locked files with reason, retry on next cycle.
**Effort:** S | **Dependencies:** None

### UR-030: ETag-Based Version Comparison
**Source:** WS2 P2-2
**What:** Store `eTag` from Graph API. Compare before extraction. Re-download on mismatch.
**Effort:** S | **Dependencies:** None

### UR-031: Content Hash Population
**Source:** WS2 P2-3
**What:** Compute SHA-256 after download, store in `MonitoredFile.content_hash`. Add as tertiary change detection signal.
**Effort:** S | **Dependencies:** None

### UR-032: Graph API Rate Limiting
**Source:** WS2 P2-4
**What:** Add asyncio semaphore (10 concurrent). Handle 429 with Retry-After parsing. 100ms delay between batch calls.
**Effort:** S | **Dependencies:** None

### UR-033: Stage History Dashboard Widget
**Source:** WS3 R-07
**What:** Timeline component in Deal Detail Modal showing chronological stage changes with source icons.
**Effort:** M | **Dependencies:** UR-006

### UR-034: Manual Stage Override with Reason
**Source:** WS3 R-08
**What:** Optional reason field on Kanban stage move. Warning if deal was recently auto-synced.
**Effort:** S | **Dependencies:** UR-006

### UR-035: Stage Mapping API Endpoint
**Source:** WS3 R-09
**What:** `GET /api/v1/extraction/stage-mapping` exposing canonical folder mapping as JSON.
**Effort:** XS | **Dependencies:** UR-007

### UR-036: Handle Non-Canonical Stages Explicitly
**Source:** WS3 R-10
**What:** Define explicit behavior for folders mapped to non-DealStage values (archive, pipeline, loi). Recommend alias mapping to closest canonical stage.
**Effort:** XS | **Dependencies:** UR-007

### UR-037: Close XLSB Workbooks After Extraction
**Source:** WS4 R-09
**What:** Add explicit workbook close for XLSB files (currently only XLSX closed).
**Effort:** S | **Dependencies:** None

### UR-038: Increase Fingerprint Row Scan Limit
**Source:** WS4 R-10
**What:** Increase 200-row limit to 500 or make configurable. Labels below row 200 are missed.
**Effort:** S | **Dependencies:** None

### UR-039: Batch-Level Sum Reconciliation
**Source:** WS4 R-11
**What:** Post-extraction consistency check: NOI = Revenue - OpEx, Cap Rate = NOI / Price, etc.
**Effort:** M | **Dependencies:** UR-001

### UR-040: Stabilize Duplicate Field Name Suffixes
**Source:** WS4 R-12
**What:** Change suffix from occurrence-based to `_{sheet_abbrev}_{cell_address}` for deterministic naming.
**Effort:** M | **Dependencies:** Requires re-extraction of all data

### UR-041: Add Confidence Score to ExtractedValue
**Source:** WS4 R-13
**What:** Store mapping confidence (0.40-0.95) on each `ExtractedValue` row. Enables UI confidence indicators.
**Effort:** M | **Dependencies:** Alembic migration

---

## Dependency Map

```
UR-004 (Redis) ────> UR-005 (Redis validation)
       │
       ├───> UR-014 (Webhook debounce)
       ├───> UR-017 (Auth alerting)
       └───> UR-026 (Auth verification)

UR-007 (Unified mapping) ──> UR-006 (Audit trail) ──> UR-008 (stage_updated_at)
                                      │
                                      ├───> UR-018 (WS notifications)
                                      ├───> UR-019 (Deletion policy)
                                      ├───> UR-033 (History UI)
                                      └───> UR-034 (Override with reason)

UR-001 (error_category) ──> UR-003 (Null types)
       │
       ├───> UR-021 (Ungrouped files)
       ├───> UR-022 (Domain validation)
       └───> UR-039 (Sum reconciliation)

UR-010 (Delta queries) ──> UR-014 (Webhook)
       │
       └───> UR-016 (Reconciliation)

UR-009 (Download retry) ── standalone
UR-011 (Logging) ── standalone
UR-023 (Schema drift) ── standalone
```

---

## Effort Distribution

| Effort | Count | Items |
|--------|-------|-------|
| XS | 5 | UR-008, UR-027, UR-035, UR-036 |
| S | 18 | UR-001, UR-004, UR-005, UR-007, UR-009, UR-012, UR-013, UR-017, UR-018, UR-019, UR-020, UR-024, UR-025, UR-026, UR-029, UR-030, UR-031, UR-032, UR-034, UR-037, UR-038 |
| M | 14 | UR-002, UR-003, UR-006, UR-010, UR-011, UR-015, UR-016, UR-021, UR-022, UR-028, UR-033, UR-039, UR-040, UR-041 |
| L | 2 | UR-014, UR-023 |
