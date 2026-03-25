# Architecture Review v3 -- Implementation Roadmap

**Date:** 2026-03-25 | **Duration:** 8 weeks (4 two-week sprints)
**Format:** BMAD-style Epics with T-shirt sized stories
**Execution Order:** WS4 (Data Integrity) -> WS1 (Infrastructure) -> WS2 (Extraction Automation) -> WS3 (Deal Stage Sync)

---

## T-Shirt Sizing Reference

| Size | Time | Description |
|------|------|-------------|
| XS | < 1 hour | Config change, single line fix |
| S | 1-4 hours | Single feature, 2-3 files |
| M | 4-16 hours | Multi-file, new model/migration |
| L | 2-4 days | New module, cross-cutting feature |
| XL | 4+ days | Major feature with multiple components |

---

## Sprint 1 (Week 1-2): P0 Data Integrity + Infrastructure

**Theme:** Make existing data trustworthy and enable Redis.

### Epic 1.1: Error Category Population [WS4]

**Goal:** Make `error_category` a reliable diagnostic tool.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 1.1.1 | Wire `ErrorHandler.errors` into `bulk_insert()` in `group_pipeline.py` | S | UR-001 |
| 1.1.2 | Wire `ErrorHandler.errors` into `bulk_insert()` in `common.py` | S | UR-001 |
| 1.1.3 | Integration test: extract file with known errors, verify error_category in DB | S | UR-001 |

### Epic 1.2: Tier 1b Match Validation [WS4]

**Goal:** Identify and flag risky Tier 1b matches before they produce bad financial data.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 1.2.1 | Add `label_verified = False` flag on Tier 1b `MappingMatch` results | S | UR-002 |
| 1.2.2 | Log warning for Tier 1b fields with values outside expected domain range | S | UR-002 |
| 1.2.3 | Generate Tier 1b review report per group after extraction | M | UR-002 |
| 1.2.4 | Tests for Tier 1b flagging and domain range cross-check | S | UR-002 |

### Epic 1.3: Null Type Differentiation [WS4]

**Goal:** Distinguish empty cells, formula errors, and placeholder text.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 1.3.1 | Define null handling policy (empty/N-A/TBD/formula error/missing sheet/cell not found) | S | UR-003 |
| 1.3.2 | Refactor `handle_empty_value()` and `process_cell_value()` | M | UR-003 |
| 1.3.3 | Update `bulk_insert()` empty-cell handling | S | UR-003 |
| 1.3.4 | Update 10+ tests relying on NaN-to-is_error behavior | M | UR-003 |

### Epic 1.4: Redis Enablement [WS1]

**Goal:** Redis running as the active backend for cache, token blacklist, rate limiter, pub/sub.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 1.4.1 | Install Redis on WSL2, configure password, start service | S | UR-004 |
| 1.4.2 | Fix `REDIS_URL` in `.env` to include password | XS | UR-004 |
| 1.4.3 | Add `REDIS_REQUIRED` config setting with startup validation | S | UR-005 |
| 1.4.4 | Add config validator: warn if `REDIS_PASSWORD` set but not in `REDIS_URL` | S | UR-005 |
| 1.4.5 | Verify token blacklist survives restart, cache populates, rate limiter works | S | UR-004 |

### Epic 1.5: StageChangeLog Audit Trail [WS3]

**Goal:** Persistent record of every deal stage transition with unified mapping.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 1.5.1 | Create `stage_mapping.py` with canonical `FOLDER_TO_STAGE`, `resolve_stage()` | S | UR-007 |
| 1.5.2 | Replace `_infer_deal_stage()` substring matching with `resolve_stage()` | S | UR-007 |
| 1.5.3 | Fix frontend folder names to match backend canonical mapping | S | UR-007 |
| 1.5.4 | Create `StageChangeLog` model and Alembic migration | M | UR-006 |
| 1.5.5 | Create central `change_deal_stage()` function (sets stage, stage_updated_at, logs) | S | UR-006, UR-008 |
| 1.5.6 | Retrofit 3 existing callers (file_monitor, crud_deal, extraction) | M | UR-006 |
| 1.5.7 | Stage history API endpoint `GET /deals/{id}/stage-history` | S | UR-006 |
| 1.5.8 | Tests: audit log creation, all source types, stage_updated_at always set | M | UR-006 |

**Sprint 1 Deliverables:**
- Redis operational with proper auth
- error_category populated on all extraction runs
- Tier 1b matches flagged for review
- Null types differentiated in error handling
- Unified folder mapping (single source of truth)
- Audit trail for all deal stage changes
- All P0 items resolved

---

## Sprint 2 (Week 3-4): P0 Extraction Resilience + Security

**Theme:** Make SharePoint extraction resilient and observable.

### Epic 2.1: Download Retry Logic [WS2]

**Goal:** Transient download failures are retried; permanent failures fail fast.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 2.1.1 | Add `download_file_with_retry()` with exponential backoff (30s, 60s, 120s) | S | UR-009 |
| 2.1.2 | Add `_is_transient_error()` helper (429, 500, 502, 503, 504) | XS | UR-009 |
| 2.1.3 | Refresh download URL on 403 (expired pre-auth URL) | S | UR-009 |
| 2.1.4 | Parse `Retry-After` header on 429 responses | XS | UR-009 |
| 2.1.5 | Config settings: `DOWNLOAD_MAX_RETRIES`, `DOWNLOAD_BACKOFF_BASE_SECONDS` | XS | UR-009 |
| 2.1.6 | Tests: retry on 503, no retry on 404, backoff timing, URL refresh on 403 | S | UR-009 |

### Epic 2.2: Delta Query Support [WS2]

**Goal:** Replace O(folders x files) full scan with O(changes) delta queries.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 2.2.1 | Add `get_delta_changes()` method to SharePointClient | M | UR-010 |
| 2.2.2 | Create `DeltaToken` model and Alembic migration | S | UR-010 |
| 2.2.3 | CRUD: `get_by_drive_id()`, `upsert_token()`, `clear_token()` | S | UR-010 |
| 2.2.4 | Add `check_for_changes_delta()` to FileMonitor with fallback on 410 | M | UR-010 |
| 2.2.5 | Config: `DELTA_QUERY_ENABLED`, `DELTA_RECONCILIATION_CRON` | XS | UR-010 |
| 2.2.6 | Tests: initial sync, incremental, token expiry fallback, deleted files | M | UR-010 |

### Epic 2.3: Dead-Letter Tracking [WS2]

**Goal:** Persistently failing files are quarantined and surfaced.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 2.3.1 | Add failure tracking columns to `MonitoredFile` + Alembic migration | S | UR-015 |
| 2.3.2 | Quarantine after 3 consecutive failures; reset on success | S | UR-015 |
| 2.3.3 | Exclude quarantined files from auto-extraction | S | UR-015 |
| 2.3.4 | API: `GET /dead-letter`, `POST /dead-letter/{id}/retry` | S | UR-015 |
| 2.3.5 | Tests: quarantine lifecycle, API endpoints | S | UR-015 |

### Epic 2.4: Security Verification [WS1]

**Goal:** Confirm auth system is complete with Redis-backed blacklist.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 2.4.1 | Manual test: login, token expiry, auto-refresh, concurrent dedup | S | UR-026 |
| 2.4.2 | Verify access/refresh token separation (REFRESH_TOKEN_SECRET) | S | UR-026 |
| 2.4.3 | Create `.env.example` with documented variables (no secrets) | S | UR-026 |

**Sprint 2 Deliverables:**
- Downloads retry on transient errors (no more permanent loss)
- Delta queries reduce API calls by ~90%
- Failed files quarantined after 3 attempts (visible, not silent)
- Auth flow verified end-to-end with Redis blacklist

---

## Sprint 3 (Week 5-6): P1 Production Readiness

**Theme:** Fill data gaps, improve observability, enable real-time sync.

### Epic 3.1: Webhook Endpoint [WS2]

**Goal:** Receive instant change notifications from Microsoft Graph.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 3.1.1 | `POST /webhook` with validation handshake + clientState verification | M | UR-014 |
| 3.1.2 | WebhookSubscriptionManager (create, renew, delete lifecycle) | M | UR-014 |
| 3.1.3 | APScheduler job for subscription renewal (every 2 days) | S | UR-014 |
| 3.1.4 | Redis-based debounce (10-second window) | S | UR-014 |
| 3.1.5 | Tests: handshake, valid notification, invalid clientState, debounce | M | UR-014 |

### Epic 3.2: Ungrouped File Extraction [WS4]

**Goal:** Extract data from all 28 ungrouped files (~25 new deals).

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 3.2.1 | Form natural clusters by sheet count (28/32/33/29-sheet groups) | S | UR-021 |
| 3.2.2 | Run fingerprinting and reference mapping for each new group | M | UR-021 |
| 3.2.3 | Review Tier 2/3 matches, spot-check fields per group | M | UR-021 |
| 3.2.4 | Execute extraction with error_categories populated | S | UR-021 |
| 3.2.5 | Handle 3 singleton files (Tides, Plaza 550, Kingsview) individually | M | UR-021 |
| 3.2.6 | Sync extracted properties to properties table | S | UR-021 |

### Epic 3.3: Logging Unification [WS1]

**Goal:** Single logging system (loguru) across entire backend.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 3.3.1 | Migrate extraction core (13 structlog files) to loguru | M | UR-011 |
| 3.3.2 | Migrate extraction services, data extraction, construction API (14 files) | M | UR-011 |
| 3.3.3 | Migrate middleware/db (2 files) | S | UR-011 |
| 3.3.4 | Remove `setup_structlog()` and structlog dependency | S | UR-011 |
| 3.3.5 | Set correlation IDs for background tasks (report worker, scheduler, cache) | S | UR-012 |
| 3.3.6 | Run full test suite to verify no regressions | S | UR-011 |

### Epic 3.4: Stage Change Notifications [WS3]

**Goal:** Real-time WebSocket updates when stages change from SharePoint sync.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 3.4.1 | Emit `notify_deal_update()` from `_sync_deal_stages()` and `_batch_update_deal_stages()` | S | UR-018 |
| 3.4.2 | Emit batch event for bulk moves (>5 deals) | S | UR-018 |
| 3.4.3 | Implement deletion policy (mark DEAD when all files removed) | S | UR-019 |
| 3.4.4 | Config: `STAGE_SYNC_DELETE_POLICY`, `STAGE_SYNC_PROTECT_CLOSED` | XS | UR-019 |
| 3.4.5 | Frontend: handle `stage_changed` events in Kanban WebSocket listener | S | UR-018 |
| 3.4.6 | Tests: notification emission, deletion policy, CLOSED protection | M | UR-018, UR-019 |

### Epic 3.5: Supporting P1 Items [WS1, WS2, WS4]

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 3.5.1 | Create `field_synonyms.json` with ~20-30 synonym pairs | S | UR-024 |
| 3.5.2 | Update `run_reference_mapping()` to auto-load synonyms | S | UR-024 |
| 3.5.3 | Correct discovery document tier descriptions | S | UR-025 |
| 3.5.4 | Auth failure alerting (SharePoint auth status in health check) | S | UR-017 |
| 3.5.5 | Batch query optimization for `_sync_deal_stages()` | S | UR-020 |
| 3.5.6 | Reconciliation report service + daily scheduler | M | UR-016 |
| 3.5.7 | Reconciliation API: latest, history, manual trigger | S | UR-016 |

**Sprint 3 Deliverables:**
- ~25 new deals visible on dashboard (ungrouped files extracted)
- Near-instant file change detection via webhooks (if public URL available)
- Unified loguru logging across all backend files
- Real-time Kanban updates from SharePoint sync
- Daily reconciliation surfaces missing/stale extractions
- Tier 4 synonym matching operational

---

## Sprint 4 (Week 7-8): P1/P2 Polish

**Theme:** Advanced automation, validation, and tech debt reduction.

### Epic 4.1: Schema Drift Detection [WS4]

**Goal:** Catch template structure changes before they corrupt extracted data.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 4.1.1 | Store baseline fingerprints for each completed group | S | UR-023 |
| 4.1.2 | Create `SchemaDriftDetector` with `check_drift()` method | M | UR-023 |
| 4.1.3 | Define thresholds: >= 0.95 OK, 0.90-0.94 info, 0.80-0.89 warning, < 0.80 error | S | UR-023 |
| 4.1.4 | Integrate pre-extraction drift check into group_pipeline Phase 4 | S | UR-023 |
| 4.1.5 | Drift alert persistence (model, migration, CRUD, API endpoint) | M | UR-023 |
| 4.1.6 | Tests: OK drift, warning drift, error drift, alert persistence | M | UR-023 |

### Epic 4.2: Domain Validation Framework [WS4]

**Goal:** Reject or flag unreasonable financial values at extraction time.

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 4.2.1 | Create `domain_validators.py` with `DOMAIN_RULES` and `validate_domain_range()` | M | UR-022 |
| 4.2.2 | Integrate validation into `bulk_insert()` (flag, don't reject) | S | UR-022 |
| 4.2.3 | 30+ unit tests for all domain rule boundary conditions | M | UR-022 |
| 4.2.4 | API endpoint or report to surface validation warnings | S | UR-022 |

### Epic 4.3: Frontend & Code Health [WS1, WS3]

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 4.3.1 | Standardize 6 frontend API client imports | S | UR-013 |
| 4.3.2 | Delete `deploy.yml.disabled` artifact | XS | UR-027 |
| 4.3.3 | Structured SharePoint health check (actual Graph API call) | M | UR-028 |
| 4.3.4 | Stage history timeline component in Deal Detail Modal | M | UR-033 |
| 4.3.5 | Manual stage override with optional reason field | S | UR-034 |
| 4.3.6 | Stage mapping API endpoint | XS | UR-035 |
| 4.3.7 | Handle non-canonical stages via alias mapping | XS | UR-036 |

### Epic 4.4: Remaining P2 Items [WS2, WS4]

| Story | Description | Size | UR |
|-------|-------------|------|----|
| 4.4.1 | File locking detection (check `publication.level`) | S | UR-029 |
| 4.4.2 | ETag-based version comparison before extraction | S | UR-030 |
| 4.4.3 | Content hash population (SHA-256 after download) | S | UR-031 |
| 4.4.4 | Graph API rate limiting (semaphore + Retry-After) | S | UR-032 |
| 4.4.5 | Close XLSB workbooks after extraction | S | UR-037 |
| 4.4.6 | Increase fingerprint row scan limit to 500 | S | UR-038 |
| 4.4.7 | Batch-level sum reconciliation (NOI = Revenue - OpEx) | M | UR-039 |
| 4.4.8 | Stabilize duplicate field name suffixes (cell-address-based) | M | UR-040 |
| 4.4.9 | Add confidence score column to ExtractedValue | M | UR-041 |

**Sprint 4 Deliverables:**
- Template layout changes detected before extraction
- Out-of-range financial values flagged at extraction time
- Stage history visible in Deal Detail Modal
- File locking, eTag, and content hash change detection
- All remaining P2 items addressed

---

## Sprint Summary

| Sprint | Weeks | Focus | Epics | Stories |
|--------|-------|-------|-------|---------|
| 1 | 1-2 | P0: Data Integrity + Redis + Audit Trail | 5 | 24 |
| 2 | 3-4 | P0: Extraction Resilience + Security | 4 | 20 |
| 3 | 5-6 | P1: Webhooks + Files + Logging + Notifications | 5 | 30 |
| 4 | 7-8 | P1/P2: Drift Detection + Validation + Polish | 4 | 26 |
| **Total** | **8** | | **18** | **100** |

---

## Success Metrics

| Metric | Current | After Sprint 2 | After Sprint 4 |
|--------|---------|----------------|----------------|
| error_category populated | 0% | 100% | 100% |
| Redis operational | No | Yes | Yes |
| Stage changes audited | 0% | 100% | 100% |
| Folder mapping sources | 2 (divergent) | 1 (canonical) | 1 |
| Graph API calls per cycle | ~200+ | ~5-10 (delta) | ~1 (webhook) |
| Failed downloads recovered | 0% | ~95% (retry) | ~99% |
| Ungrouped files | 28 | 28 | 0 |
| Logging systems | 2 (loguru + structlog) | 2 | 1 (loguru) |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Redis config breaks existing in-memory fallback | Low | Medium | Test fallback path after enabling Redis |
| Graph API delta token expires mid-operation | Medium | Low | Automatic fallback to full scan |
| Webhook endpoint unreachable (no public URL) | Medium | Medium | Delta polling continues as backup; defer to Hetzner deploy |
| Alembic migration conflicts between workstreams | Low | Low | Coordinate migration chain; one branch at a time |
| structlog -> loguru migration breaks log format | Low | Medium | Migrate in batches, run full test suite after each |
| Ungrouped files have novel template structures | Medium | Medium | Run fingerprinting first; singleton handling for outliers |
| Azure AD client secret expires during extraction | Medium | High | Auth health check + CRITICAL alerting (UR-017) |

---

## Definition of Done (per Sprint)

- [ ] All stories implemented
- [ ] Backend tests pass: `cd backend && python -m pytest`
- [ ] Frontend tests pass: `npm run test:run`
- [ ] Build clean: `npm run build` (zero errors/warnings)
- [ ] Alembic migrations tested (up + downgrade)
- [ ] No new ruff or ESLint warnings
- [ ] Feature flags allow disabling new functionality
- [ ] Structured logging for all new operations
