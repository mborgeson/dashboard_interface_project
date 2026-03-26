# Architecture Review v3 -- Implementation Tasks

## Sprint 1: Data Integrity + Infrastructure (Week 1-2)

### Epic 1.1: Error Category Population [WS4] ✅ (2026-03-26)
- [x] UR-001: Wire ErrorHandler.errors into bulk_insert() in group_pipeline.py [WS4] [S]
- [x] UR-001: Wire ErrorHandler.errors into bulk_insert() in common.py [WS4] [S]
- [x] UR-001: Integration test -- extract file with known errors, verify error_category in DB [WS4] [S]

### Epic 1.2: Tier 1b Match Validation [WS4] ✅ (2026-03-26)
- [x] UR-002: Add label_verified=False flag on Tier 1b MappingMatch results [WS4] [S]
- [x] UR-002: Log warning for Tier 1b fields outside expected domain range [WS4] [S]
- [x] UR-002: Generate Tier 1b review report per group after extraction [WS4] [M]
- [x] UR-002: Tests for Tier 1b flagging and domain range cross-check [WS4] [S]

### Epic 1.3: Null Type Differentiation [WS4] ✅ (2026-03-26)
- [x] UR-003: Define null handling policy (empty/N-A/TBD/formula error/missing sheet) [WS4] [S]
- [x] UR-003: Refactor handle_empty_value() and process_cell_value() [WS4] [M]
- [x] UR-003: Update bulk_insert() empty-cell handling [WS4] [S]
- [x] UR-003: Update 10+ tests relying on NaN-to-is_error behavior [WS4] [M]

### Epic 1.4: Redis Enablement [WS1] ✅ (2026-03-26)
- [x] UR-004: Install Redis on WSL2, configure password, start service [WS1] [S]
- [x] UR-004: Fix REDIS_URL in .env to include password [WS1] [XS]
- [x] UR-005: Add REDIS_REQUIRED config setting with startup validation [WS1] [S]
- [x] UR-005: Add config validator -- warn if REDIS_PASSWORD set but not in REDIS_URL [WS1] [S]
- [x] UR-004: Verify token blacklist survives restart, cache populates, rate limiter works [WS1] [S]

### Epic 1.5: StageChangeLog Audit Trail [WS3] ✅ (2026-03-26)
- [x] UR-007: Create stage_mapping.py with canonical FOLDER_TO_STAGE and resolve_stage() [WS3] [S]
- [x] UR-007: Replace _infer_deal_stage() substring matching with resolve_stage() [WS3] [S]
- [x] UR-007: Fix frontend folder names to match backend canonical mapping [WS3] [S]
- [x] UR-006: Create StageChangeLog model and Alembic migration [WS3] [M]
- [x] UR-006: Create central change_deal_stage() function (stage + stage_updated_at + log) [WS3] [S]
- [x] UR-006: Retrofit 3 existing callers (file_monitor, crud_deal, extraction) [WS3] [M]
- [x] UR-006: Stage history API endpoint GET /deals/{id}/stage-history [WS3] [S]
- [x] UR-006: Tests -- audit log creation, all source types, stage_updated_at always set [WS3] [M]

---

## Sprint 2: Extraction Resilience + Security (Week 3-4)

### Epic 2.1: Download Retry Logic [WS2]
- [ ] UR-009: Add download_file_with_retry() with exponential backoff [WS2] [S]
- [ ] UR-009: Add _is_transient_error() helper (429, 5xx) [WS2] [XS]
- [ ] UR-009: Refresh download URL on 403 (expired pre-auth URL) [WS2] [S]
- [ ] UR-009: Parse Retry-After header on 429 responses [WS2] [XS]
- [ ] UR-009: Config: DOWNLOAD_MAX_RETRIES, DOWNLOAD_BACKOFF_BASE_SECONDS [WS2] [XS]
- [ ] UR-009: Tests -- retry on 503, no retry on 404, backoff, URL refresh on 403 [WS2] [S]

### Epic 2.2: Delta Query Support [WS2]
- [ ] UR-010: Add get_delta_changes() method to SharePointClient [WS2] [M]
- [ ] UR-010: Create DeltaToken model and Alembic migration [WS2] [S]
- [ ] UR-010: CRUD -- get_by_drive_id(), upsert_token(), clear_token() [WS2] [S]
- [ ] UR-010: Add check_for_changes_delta() to FileMonitor with 410 fallback [WS2] [M]
- [ ] UR-010: Config -- DELTA_QUERY_ENABLED, DELTA_RECONCILIATION_CRON [WS2] [XS]
- [ ] UR-010: Tests -- initial sync, incremental, token expiry fallback, deleted files [WS2] [M]

### Epic 2.3: Dead-Letter Tracking [WS2]
- [ ] UR-015: Add failure tracking columns to MonitoredFile + Alembic migration [WS2] [S]
- [ ] UR-015: Quarantine after 3 consecutive failures; reset on success [WS2] [S]
- [ ] UR-015: Exclude quarantined files from auto-extraction [WS2] [S]
- [ ] UR-015: API -- GET /dead-letter, POST /dead-letter/{id}/retry [WS2] [S]
- [ ] UR-015: Tests -- quarantine lifecycle, API endpoints [WS2] [S]

### Epic 2.4: Security Verification [WS1]
- [ ] UR-026: Manual test -- login, token expiry, auto-refresh, concurrent dedup [WS1] [S]
- [ ] UR-026: Verify access/refresh token separation (REFRESH_TOKEN_SECRET) [WS1] [S]
- [ ] UR-026: Create .env.example with documented variables (no secrets) [WS1] [S]

---

## Sprint 3: Production Readiness (Week 5-6)

### Epic 3.1: Webhook Endpoint [WS2]
- [ ] UR-014: POST /webhook with validation handshake + clientState verification [WS2] [M]
- [ ] UR-014: WebhookSubscriptionManager (create, renew, delete lifecycle) [WS2] [M]
- [ ] UR-014: APScheduler job for subscription renewal (every 2 days) [WS2] [S]
- [ ] UR-014: Redis-based debounce (10-second window) [WS2] [S]
- [ ] UR-014: Tests -- handshake, valid notification, invalid clientState, debounce [WS2] [M]

### Epic 3.2: Ungrouped File Extraction [WS4]
- [ ] UR-021: Form natural clusters by sheet count (28/32/33/29-sheet groups) [WS4] [S]
- [ ] UR-021: Run fingerprinting and reference mapping for each new group [WS4] [M]
- [ ] UR-021: Review Tier 2/3 matches, spot-check fields per group [WS4] [M]
- [ ] UR-021: Execute extraction with error_categories populated [WS4] [S]
- [ ] UR-021: Handle 3 singleton files (Tides, Plaza 550, Kingsview) individually [WS4] [M]
- [ ] UR-021: Sync extracted properties to properties table [WS4] [S]

### Epic 3.3: Logging Unification [WS1]
- [ ] UR-011: Migrate extraction core (13 structlog files) to loguru [WS1] [M]
- [ ] UR-011: Migrate extraction services, data extraction, construction API (14 files) [WS1] [M]
- [ ] UR-011: Migrate middleware/db (2 files) [WS1] [S]
- [ ] UR-011: Remove setup_structlog() and structlog dependency [WS1] [S]
- [ ] UR-012: Set correlation IDs for background tasks (report worker, scheduler, cache) [WS1] [S]
- [ ] UR-011: Run full test suite to verify no logging regressions [WS1] [S]

### Epic 3.4: Stage Change Notifications [WS3]
- [ ] UR-018: Emit notify_deal_update() from _sync_deal_stages() [WS3] [S]
- [ ] UR-018: Emit batch event for bulk moves (>5 deals) [WS3] [S]
- [ ] UR-019: Implement deletion policy -- mark DEAD when all files removed [WS3] [S]
- [ ] UR-019: Config -- STAGE_SYNC_DELETE_POLICY, STAGE_SYNC_PROTECT_CLOSED [WS3] [XS]
- [ ] UR-018: Frontend -- handle stage_changed events in Kanban WebSocket listener [WS3] [S]
- [ ] UR-018: Tests -- notification emission, deletion policy, CLOSED protection [WS3] [M]

### Epic 3.5: Supporting P1 Items [WS1, WS2, WS3, WS4]
- [ ] UR-024: Create field_synonyms.json with ~20-30 synonym pairs [WS4] [S]
- [ ] UR-024: Update run_reference_mapping() to auto-load synonyms [WS4] [S]
- [ ] UR-025: Correct discovery document tier descriptions [WS4] [S]
- [ ] UR-017: Auth failure alerting -- SharePoint auth status in health check [WS2] [S]
- [ ] UR-020: Batch query optimization for _sync_deal_stages() [WS3] [S]
- [ ] UR-016: Reconciliation report service + daily scheduler [WS2] [M]
- [ ] UR-016: Reconciliation API -- latest, history, manual trigger [WS2] [S]

---

## Sprint 4: Polish + Technical Debt (Week 7-8)

### Epic 4.1: Schema Drift Detection [WS4]
- [ ] UR-023: Store baseline fingerprints for each completed group [WS4] [S]
- [ ] UR-023: Create SchemaDriftDetector with check_drift() method [WS4] [M]
- [ ] UR-023: Define thresholds -- >=0.95 OK, 0.90-0.94 info, 0.80-0.89 warn, <0.80 error [WS4] [S]
- [ ] UR-023: Integrate pre-extraction drift check into group_pipeline Phase 4 [WS4] [S]
- [ ] UR-023: Drift alert persistence -- model, migration, CRUD, API endpoint [WS4] [M]
- [ ] UR-023: Tests -- OK drift, warning drift, error drift, alert persistence [WS4] [M]

### Epic 4.2: Domain Validation Framework [WS4]
- [ ] UR-022: Create domain_validators.py with DOMAIN_RULES and validate_domain_range() [WS4] [M]
- [ ] UR-022: Integrate validation into bulk_insert() -- flag, don't reject [WS4] [S]
- [ ] UR-022: 30+ unit tests for all domain rule boundary conditions [WS4] [M]
- [ ] UR-022: API endpoint or report to surface validation warnings [WS4] [S]

### Epic 4.3: Frontend & Code Health [WS1, WS3]
- [ ] UR-013: Standardize 6 frontend API client imports [WS1] [S]
- [ ] UR-027: Delete deploy.yml.disabled artifact [WS1] [XS]
- [ ] UR-028: Structured SharePoint health check -- actual Graph API call [WS1] [M]
- [ ] UR-033: Stage history timeline component in Deal Detail Modal [WS3] [M]
- [ ] UR-034: Manual stage override with optional reason field [WS3] [S]
- [ ] UR-035: Stage mapping API endpoint [WS3] [XS]
- [ ] UR-036: Handle non-canonical stages via alias mapping [WS3] [XS]

### Epic 4.4: Remaining P2 Items [WS2, WS4]
- [ ] UR-029: File locking detection -- check publication.level [WS2] [S]
- [ ] UR-030: ETag-based version comparison before extraction [WS2] [S]
- [ ] UR-031: Content hash population -- SHA-256 after download [WS2] [S]
- [ ] UR-032: Graph API rate limiting -- semaphore + Retry-After [WS2] [S]
- [ ] UR-037: Close XLSB workbooks after extraction [WS4] [S]
- [ ] UR-038: Increase fingerprint row scan limit to 500 [WS4] [S]
- [ ] UR-039: Batch-level sum reconciliation (NOI = Revenue - OpEx) [WS4] [M]
- [ ] UR-040: Stabilize duplicate field name suffixes -- cell-address-based [WS4] [M]
- [ ] UR-041: Add confidence score column to ExtractedValue [WS4] [M]
