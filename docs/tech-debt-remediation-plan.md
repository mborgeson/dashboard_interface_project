# B&R Capital Dashboard — Technical Debt Remediation Plan

**Created:** 2026-03-10
**Baseline:** `main` at `66fbe56` | Tests: 3,804 passing | Build: clean
**Estimated Duration:** ~64 hours wall-clock (with parallelism across 12 teams)
**Items:** 62 of 76 addressed (14 deferred to future sprint)

---

## Executive Summary

Three analysis agents identified **76 technical debt items** (1 CRITICAL, 15 HIGH, 33 MEDIUM, 27 LOW) totaling ~372-450 hours of estimated work. This plan organizes 12 specialized Agent Teams into 5 execution waves with strict file ownership, safety gates, and checkpoint protocols to ensure zero regressions.

| Category          | Items        | Critical    | High         | Medium       | Low          | Est. Hours         |
| ----------------- | ------------ | ----------- | ------------ | ------------ | ------------ | ------------------ |
| Code Debt         | 22           | 0           | 4            | 10           | 8            | 72-100             |
| Architecture Debt | 27           | 0           | 3            | 12           | 12           | ~130               |
| Test Debt         | 27           | 1           | 8            | 11           | 7            | 170-220            |
| **TOTAL**   | **76** | **1** | **15** | **33** | **27** | **~372-450** |

---

## Top 10 Priority Items

| #  | ID         | Category | Severity           | Hours | Issue                                                                         |
| -- | ---------- | -------- | ------------------ | ----- | ----------------------------------------------------------------------------- |
| 1  | T-DEBT-012 | Test     | **CRITICAL** | 8-12  | E2E tests silently skip on failure (70 `test.skip()` = "green when broken") |
| 2  | C-TD-015   | Code     | HIGH               | 8     | 13 sync DB sessions in async endpoints — blocks event loop                   |
| 3  | A-TD-023   | Arch     | HIGH               | 2     | PyTorch/TensorFlow/XGBoost unused — 3-5GB Docker bloat                       |
| 4  | A-TD-001   | Arch     | HIGH               | 8     | Double-commit pattern — CRUD + session both commit, breaks atomicity         |
| 5  | A-TD-017   | Arch     | HIGH               | 8     | Unbounded dashboard query (`limit=1000`) — performance cliff               |
| 6  | T-DEBT-010 | Test     | HIGH               | 4-6   | Zod schema bypassed in hook tests — snake/camelCase untested                 |
| 7  | T-DEBT-007 | Test     | HIGH               | 4-6   | Status-code-only assertions in 30+ API tests                                  |
| 8  | T-DEBT-016 | Test     | HIGH               | 8-10  | E2E tests not in CI — 20 Playwright specs provide zero CI value              |
| 9  | C-TD-007   | Code     | HIGH               | 8     | deals.py is 1,737 lines — 4+ domain concerns in one file                     |
| 10 | T-DEBT-026 | Test     | HIGH               | 4-6   | No boundary tests for financial calculations (cap rate, IRR, MOIC)            |

---

## Agent Team Definitions

### Team 1: E2E-Reliability

- **Agents:** `playwright-expert`, `test-engineer`
- **Purpose:** Fix the "green when broken" E2E suite and integrate into CI
- **Items:** T-DEBT-012, T-DEBT-016, T-DEBT-011
- **Files owned:**
  - `e2e/*.spec.ts` (all 20 files)
  - `playwright.config.ts`
  - `.github/workflows/frontend-ci.yml` (add E2E job)
- **Dependencies:** None
- **Duration:** 20-28h

### Team 2: Backend-Async-Integrity

- **Agents:** `backend-development:backend-architect`, `database-expert`
- **Purpose:** Fix sync-in-async blocking and double-commit atomicity
- **Items:** C-TD-015, A-TD-001
- **Files owned:**
  - `backend/app/db/session.py`
  - `backend/app/crud/base.py`
  - `backend/app/crud/crud_*.py` (all CRUD modules)
- **Dependencies:** None (but all backend test teams run after this)
- **Duration:** 12-16h

### Team 3: Backend-Decomposition

- **Agents:** `refactor-expert`, `backend-development:backend-architect`
- **Purpose:** Break apart 1,700+ line god-files
- **Items:** C-TD-007, C-TD-009, C-TD-010, C-TD-017
- **Files owned:**
  - `backend/app/api/v1/endpoints/deals.py` (split into deals_crud.py, deals_kanban.py, deals_comparison.py, deals_activity.py, deals_proforma.py)
  - `backend/app/api/v1/endpoints/construction_pipeline.py` (split)
  - `backend/app/services/market_data.py` (split)
  - `backend/app/api/v1/endpoints/extraction/` (registry pattern)
  - `backend/app/extraction/cell_mapping.py`, `reference_mapper.py`
  - `backend/app/api/v1/router.py` (update imports)
- **Dependencies:** AFTER Team 2
- **Duration:** 22-28h

### Team 4: Backend-Test-Coverage

- **Agents:** `backend-development:tdd-orchestrator`, `test-engineer`
- **Purpose:** Add tests for untested backend modules
- **Items:** T-DEBT-001, T-DEBT-003, T-DEBT-005, T-DEBT-007, T-DEBT-008, T-DEBT-025, T-DEBT-026
- **Files owned (new test files only):**
  - `backend/tests/test_crud/test_crud_activity.py` (new)
  - `backend/tests/test_crud/test_crud_activity_log.py` (new)
  - `backend/tests/test_crud/test_crud_document.py` (new)
  - `backend/tests/test_crud/test_crud_property.py` (new)
  - `backend/tests/test_crud/test_crud_report_template.py` (new)
  - `backend/tests/test_services/test_interest_rates.py` (new)
  - `backend/tests/test_services/test_market_data.py` (new)
  - `backend/tests/test_services/test_extraction_service.py` (new)
  - `backend/tests/test_extraction/test_failure_paths.py` (new)
  - `backend/tests/test_api/` (enhance existing for response body assertions)
  - `backend/tests/test_financial/` (new directory for boundary tests)
- **Dependencies:** AFTER Team 2
- **Duration:** 28-36h

### Team 5: Frontend-Test-Coverage

- **Agents:** `react-expert`, `typescript-expert`, `test-engineer`
- **Purpose:** Add tests for 6 untested frontend features
- **Items:** T-DEBT-004, T-DEBT-010, T-DEBT-027
- **Files owned (new test files + existing test fixes):**
  - `src/features/auth/__tests__/` (new)
  - `src/features/documents/__tests__/` (new)
  - `src/features/interest-rates/__tests__/` (new)
  - `src/features/reporting-suite/__tests__/` (new)
  - `src/features/search/__tests__/` (new)
  - `src/features/transactions/__tests__/` (new)
  - `src/hooks/api/__tests__/useDeals.test.ts` (fix Zod bypass)
  - `src/hooks/api/__tests__/useProperties.test.ts` (fix Zod bypass)
  - `src/hooks/api/__tests__/useDealComparison.test.ts` (fix Zod bypass)
  - `src/hooks/api/__tests__/usePropertyActivities.test.ts` (fix Zod bypass)
- **Dependencies:** None
- **Duration:** 24-32h

### Team 6: Docker-Deps-Cleanup

- **Agents:** `config-safety-reviewer`, `backend-development:backend-architect`
- **Purpose:** Remove unused dependencies, pin versions, clean Docker
- **Items:** A-TD-023, A-TD-020, A-TD-024, A-TD-022, A-TD-021
- **Files owned:**
  - `backend/requirements.txt`
  - `backend/Dockerfile`, `backend/Dockerfile.prod`
  - `package.json`
  - `backend/app/services/ml/model_manager.py`, `rent_growth_predictor.py`
- **Dependencies:** None
- **Duration:** 4-6h

### Team 7: Query-Performance

- **Agents:** `performance-tuner`, `database-expert`
- **Purpose:** Fix unbounded queries and inconsistent pagination
- **Items:** A-TD-017, A-TD-005, C-TD-004, C-TD-005
- **Files owned:**
  - `backend/app/api/v1/endpoints/properties.py`
  - `backend/app/api/v1/endpoints/exports.py`
  - `backend/app/api/v1/endpoints/analytics.py`
  - `backend/app/api/v1/endpoints/sales_analysis.py`
  - `backend/app/api/v1/endpoints/transactions.py`
  - `backend/app/api/v1/endpoints/users.py`
  - `backend/app/schemas/pagination.py`
- **Dependencies:** AFTER Teams 2, 3
- **Duration:** 14-18h

### Team 8: Frontend-Code-Quality

- **Agents:** `react-expert`, `typescript-expert`, `refactor-expert`
- **Purpose:** Clean up frontend hooks, naming, patterns
- **Items:** C-TD-006, C-TD-014, C-TD-013, C-TD-021, C-TD-022, A-TD-009, A-TD-010
- **Files owned:**
  - `src/hooks/api/*.ts` (all hook files)
  - `src/hooks/api/index.ts`
  - `src/lib/queryClient.ts`
  - `src/stores/authStore.ts`
  - `src/hooks/usePrefetch.ts`, `usePrefetchDashboard.ts`
  - Feature-level hooks (construction-pipeline, sales-analysis, market, interest-rates, documents)
  - `src/services/errorTracking.ts` (global error handler)
  - `src/app/` (error boundary provider)
- **Dependencies:** AFTER Team 5
- **Duration:** 16-22h

### Team 9: Backend-Code-Quality

- **Agents:** `refactor-expert`, `backend-development:backend-architect`
- **Purpose:** Clean up backend code smells and configuration
- **Items:** C-TD-001, C-TD-003, C-TD-008, C-TD-002, C-TD-018, C-TD-019, C-TD-020, A-TD-002, A-TD-006, A-TD-011, A-TD-013, A-TD-014, A-TD-015
- **Files owned:**
  - `backend/app/schemas/*.py` (extract inline schemas)
  - `backend/app/models/*.py` (uncomment relationships)
  - `backend/app/core/config.py` (split Settings)
  - `backend/app/api/v1/endpoints/reporting.py`
  - `backend/app/api/v1/endpoints/documents.py`
  - `backend/app/api/v1/endpoints/market_data.py`, `market_data_admin.py`
  - `backend/app/api/v1/endpoints/interest_rates.py`
  - `backend/app/api/v1/endpoints/monitoring.py`
  - `backend/app/api/v1/endpoints/admin.py`
  - `backend/app/api/v1/endpoints/health.py`
  - `backend/app/api/v1/endpoints/ws.py`
  - `backend/app/services/enrichment.py`
  - `backend/app/extraction/extractor.py`
- **Dependencies:** AFTER Teams 2, 3
- **Duration:** 18-24h

### Team 10: Backend-Test-Quality

- **Agents:** `test-engineer`, `backend-development:tdd-orchestrator`
- **Purpose:** Fix test quality issues
- **Items:** T-DEBT-009, T-DEBT-013, T-DEBT-014, T-DEBT-019, T-DEBT-022, T-DEBT-024, T-DEBT-006, T-DEBT-021
- **Files owned:**
  - `backend/tests/conftest.py`
  - `backend/tests/fixtures/`
  - `backend/tests/test_services/test_*.py` (refactor mocks)
  - `backend/tests/test_core/test_token_blacklist.py`
  - `backend/tests/test_middleware/test_*.py`
  - `backend/tests/test_api/test_auth.py`
  - `backend/tests/test_api/test_deal_optimistic_locking.py`
  - `backend/tests/api/` (consolidation)
- **Dependencies:** AFTER Teams 2, 3, 4
- **Duration:** 18-24h

### Team 11: Mock-Data-Cleanup

- **Agents:** `refactor-expert`, `react-expert`
- **Purpose:** Remove mock data from production code
- **Items:** C-TD-012, C-TD-016, A-TD-007, C-TD-011
- **Files owned:**
  - `src/data/mockDeals.ts`, `mockProperties.ts`, `mockReportingData.ts`, `mockTransactions.ts`
  - `src/types/` (extract reporting types)
  - `backend/app/api/v1/endpoints/_property_transforms.py`
- **Dependencies:** AFTER Teams 5, 8
- **Duration:** 8-12h

### Team 12: Infrastructure-Hardening

- **Agents:** `systems-architect`, `security-auditor`, `performance-tuner`
- **Purpose:** Logging, cache, security, health checks
- **Items:** A-TD-012, A-TD-016, A-TD-019, A-TD-026, A-TD-003, A-TD-004, A-TD-018, A-TD-008
- **Files owned:**
  - `backend/app/core/logging.py`
  - `backend/app/core/token_blacklist.py`
  - `backend/app/middleware/etag.py`
  - `backend/app/core/cache.py`
- **Dependencies:** AFTER Teams 2, 3, 9
- **Duration:** 14-18h

### Review/Validation/Audit Team

- **Agents:** `code-review-expert`, `reviewer`, `linting-expert`
- **Purpose:** Verify all work after each wave
- **Runs:** After every wave gate
- **Responsibilities:**
  1. Post-commit review of every commit
  2. File ownership enforcement (no team modified files outside assignment)
  3. Test regression check (compare pre/post counts)
  4. Lint/format enforcement (ruff + ESLint)
  5. Conventional commit message verification
  6. Documentation cross-check

### Documentation Team

- **Agents:** `docs-writer`
- **Purpose:** Document everything
- **Runs:** After each wave completes
- **Outputs:**
  - Updated `docs/findings-and-recommendations.md` (commit hashes, status)
  - New ADRs in `docs/adr/` for significant decisions
  - Final `docs/tech-debt-remediation-report.md`

---

## Execution Waves

### Wave 0: Baseline Verification (30 min)

| Step | Command                                          | Expected     |
| ---- | ------------------------------------------------ | ------------ |
| 1    | `cd backend && python -m pytest --tb=short -q` | 2,538 pass   |
| 2    | `npm run test:run`                             | 1,266 pass   |
| 3    | `npm run build`                                | 0 errors     |
| 4    | `npm run lint`                                 | 0 errors     |
| 5    | `cd backend && ruff check app/`                | 0 errors     |
| 6    | `git tag tech-debt-baseline`                   | Tag baseline |

Record: `BASELINE_BACKEND=2538`, `BASELINE_FRONTEND=1266`, `BASELINE_TOTAL=3804`

---

### Wave 1: Foundation & Zero-Risk (~6h elapsed)

**All three teams run in parallel. Zero file overlap.**

| Team                     | Items                                            | Key Files                                   | Est.   |
| ------------------------ | ------------------------------------------------ | ------------------------------------------- | ------ |
| Team 6 (Docker/Deps)     | A-TD-023, A-TD-020, A-TD-024, A-TD-022, A-TD-021 | requirements.txt, package.json, Dockerfiles | 4-6h   |
| Team 2 (Async/Atomicity) | C-TD-015, A-TD-001                               | db/session.py, crud/*.py                    | 12-16h |
| Team 1 (E2E Phase 1)     | T-DEBT-012                                       | e2e/*.spec.ts                               | 4-6h   |

**Wave 1 Commits:**

```
fix(deps): remove unused ML/npm deps, pin versions [A-TD-023,020,024,022,021]
refactor(db): fix double-commit and sync-in-async patterns [C-TD-015, A-TD-001]
test(e2e): remove 70 silent test.skip() calls [T-DEBT-012]
```

**Gate:** All 3,804 existing tests pass. Build clean. Tag `tech-debt-wave-1-complete`.

---

### Wave 2: Structural Refactoring (~24h elapsed)

**Depends on Wave 1. Three teams in parallel — no file overlap.**

| Team                    | Items                                  | Key Files                                          | Est.   |
| ----------------------- | -------------------------------------- | -------------------------------------------------- | ------ |
| Team 3 (Decomposition)  | C-TD-007, C-TD-009, C-TD-010, C-TD-017 | deals.py, market_data.py, construction_pipeline.py | 22-28h |
| Team 5 (Frontend Tests) | T-DEBT-004, T-DEBT-010, T-DEBT-027     | src/features/*/__tests__/, hook test fixes   | 24-32h |
| Team 1 (E2E Phase 2)    | T-DEBT-016, T-DEBT-011                 | e2e/*.spec.ts, playwright.config.ts, CI yml        | 16-22h |

**Wave 2 Commits:**

```
refactor(api): decompose deals.py into 5 sub-modules [C-TD-007]
refactor(services): split MarketDataService into focused services [C-TD-009]
refactor(api): split construction_pipeline.py, extract schemas [C-TD-010]
refactor(extraction): declarative field registry [C-TD-017]
test(frontend): add tests for auth, docs, interest-rates, reporting, search, transactions [T-DEBT-004]
test(hooks): remove Zod schema bypass, add null/empty tests [T-DEBT-010, T-DEBT-027]
test(e2e): add CI job, replace 269 waitForTimeout with waitFor [T-DEBT-016, T-DEBT-011]
```

**Gate:** Backend 2,538+. Frontend 1,266 + ~200-400 new. Build clean. Tag `tech-debt-wave-2-complete`.

---

### Wave 3: Test Coverage & Query Performance (~36h elapsed)

**Depends on Wave 2.**

| Team                   | Items                                                                              | Key Files                                  | Est.   |
| ---------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------ | ------ |
| Team 4 (Backend Tests) | T-DEBT-001, T-DEBT-003, T-DEBT-005, T-DEBT-007, T-DEBT-008, T-DEBT-025, T-DEBT-026 | backend/tests/ (new files only)            | 28-36h |
| Team 7 (Query Perf)    | A-TD-017, A-TD-005, C-TD-004, C-TD-005                                             | properties.py, analytics.py, pagination.py | 14-18h |

**Wave 3 Commits:**

```
test(crud): add tests for activity, activity_log, document, property, report_template [T-DEBT-001]
test(services): add tests for InterestRatesService, MarketDataService [T-DEBT-003]
test(extraction): add failure path and service layer tests [T-DEBT-005, T-DEBT-025]
test(api): add response body assertions to 30+ tests [T-DEBT-007, T-DEBT-008]
test(financial): add boundary tests for cap rate, IRR, MOIC [T-DEBT-026]
perf(api): paginate dashboard endpoint, standardize pagination [A-TD-017, A-TD-005]
refactor(api): extract shared pagination and filter utilities [C-TD-004, C-TD-005]
```

**Gate:** Backend 2,538 + ~150-250 new. Frontend stable. Build clean. Tag `tech-debt-wave-3-complete`.

---

### Wave 4: Code Quality Pass (~48h elapsed)

**Depends on Waves 2-3.**

| Team                      | Items                                                                                                                            | Key Files                                  | Est.   |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | ------ |
| Team 8 (Frontend Quality) | C-TD-006, C-TD-014, C-TD-013, C-TD-021, C-TD-022, A-TD-009, A-TD-010                                                             | src/hooks/api/*.ts, authStore, queryClient | 16-22h |
| Team 9 (Backend Quality)  | C-TD-001, C-TD-003, C-TD-008, C-TD-002, C-TD-018, C-TD-019, C-TD-020, A-TD-002, A-TD-006, A-TD-011, A-TD-013, A-TD-014, A-TD-015 | schemas, models, config, endpoints         | 18-24h |

**Wave 4 Commits:**

```
refactor(hooks): extract staleTime constants, unify hook naming [C-TD-006, C-TD-013, C-TD-021]
refactor(hooks): consolidate useProperties/usePropertiesApi [C-TD-014]
fix(hooks): fix DocumentApiResponse dual-casing [C-TD-022]
refactor(auth): unify auth state management [A-TD-009]
feat(ui): add global error handling and error boundaries [A-TD-010]
refactor(api): merge PUT/PATCH deal endpoints [C-TD-001]
refactor(schemas): extract inline Pydantic schemas to app/schemas/ [C-TD-003]
refactor(extraction): make field mapping declarative [C-TD-008]
refactor(api): extract deal comparison to service layer [C-TD-018]
refactor(models): uncomment ORM relationships [A-TD-002]
refactor(api): add response_model to untyped endpoints [A-TD-006]
fix(config): split Settings class, remove demo defaults, fix SQLite default [A-TD-013, A-TD-014, A-TD-015]
fix(middleware): sanitize ValueError messages [A-TD-011]
```

**Gate:** All 4,000+ tests pass. Build clean. Lint clean. Tag `tech-debt-wave-4-complete`.

---

### Wave 5: Cleanup & Hardening (~60h elapsed)

**Depends on Wave 4.**

| Team                   | Items                                                                                          | Key Files                                             | Est.   |
| ---------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------ |
| Team 10 (Test Quality) | T-DEBT-009, T-DEBT-013, T-DEBT-014, T-DEBT-019, T-DEBT-022, T-DEBT-024, T-DEBT-006, T-DEBT-021 | backend/tests/ (existing files)                       | 18-24h |
| Team 11 (Mock Cleanup) | C-TD-012, C-TD-016, A-TD-007, C-TD-011                                                         | src/data/*.ts, src/types/, _property_transforms.py    | 8-12h  |
| Team 12 (Infra)        | A-TD-012, A-TD-016, A-TD-019, A-TD-026, A-TD-003, A-TD-004, A-TD-018, A-TD-008                 | core/logging, token_blacklist, middleware, enrichment | 14-18h |

**Wave 5 Commits:**

```
test(services): refactor excessive mocks, use test doubles [T-DEBT-009]
test(auth): fix token blacklist shared state, use fakeredis [T-DEBT-013]
test(misc): replace sleep-based sync with events [T-DEBT-014]
test(api): standardize auth fixture patterns [T-DEBT-019]
test(services): decouple from private internals [T-DEBT-022]
test(deals): add concurrent stage transition tests [T-DEBT-024]
test(middleware): complete etag and error handler tests [T-DEBT-006]
chore(tests): consolidate api/v1/ into test_api/ [T-DEBT-021]
chore(frontend): remove 3,717 lines of dead mock data [C-TD-012]
refactor(types): extract reporting types from mock file [C-TD-016]
refactor(api): move submarket mappings to config [C-TD-011]
refactor(logging): standardize on loguru [A-TD-012]
fix(auth): add TTL eviction to in-memory token blacklist [A-TD-016]
perf(api): increase ETag cache to 500 [A-TD-019]
fix(health): add deep health checks for DB and Redis [A-TD-026]
refactor(services): extract business logic from properties endpoints [A-TD-003]
refactor(crud): move enrichment orchestration to service [A-TD-004]
perf(crud): fix N+1 residual in batch enrichment [A-TD-018]
docs: update CLAUDE.md — API client is now unified [A-TD-008]
```

**Gate:** Final test count 4,200-4,550. Build clean. Lint clean. Docker build succeeds. Tag `tech-debt-wave-5-complete`.

---

### Wave 6: Documentation & Final Review (~64h elapsed)

| Team               | Action                                                                   |
| ------------------ | ------------------------------------------------------------------------ |
| Documentation Team | Update findings-and-recommendations.md, write ADRs, produce final report |
| Review Team        | Final audit of all commits, produce sign-off report                      |

**Final Commit:**

```
docs: tech debt remediation report — 62/76 items resolved
```

---

## Safety Protocol

### Pre-Wave Checklist

```bash
git stash  # if uncommitted work
cd backend && python -m pytest --tb=short -q   # record count
npm run test:run                                 # record count
npm run build                                    # verify 0 errors
npm run lint                                     # verify 0 errors
cd backend && ruff check app/                    # verify 0 errors
git tag wave-N-pre
```

### During-Wave Rules

1. Each team runs tests for affected modules after every logical sub-task
2. Backend teams: `cd backend && python -m pytest tests/test_<module>/ -v`
3. Frontend teams: `npx vitest run src/<affected-path>/`
4. E2E team: `npx playwright test <specific-spec>.spec.ts`
5. **If any existing test breaks: STOP, diagnose, fix before proceeding**
6. **Never suppress or skip a previously-passing test**

### Post-Wave Checklist

```bash
cd backend && python -m pytest --tb=short -q   # must be >= pre-wave count
npm run test:run                                 # must be >= pre-wave count
npm run build                                    # 0 errors
npm run lint                                     # 0 errors
cd backend && ruff check app/ && ruff format app/ --check  # 0 errors
git tag wave-N-post
# Record: test counts, diff summary, time elapsed
```

### Rollback Procedure

1. **Team-local break:** Fix in place (expected)
2. **Cross-team break:** `git revert <commit>` for breaking commit, escalate to Review team
3. **Wave gate fail:** `git reset --soft wave-N-pre` to undo wave, diagnose, re-plan
4. **Nuclear:** `git reset --hard tech-debt-baseline` (last resort, destroys all wave work)

---

## Communication Protocol

### Progress Reporting

Each team updates progress after each sub-task:

```
[Team-N] [ITEM-ID] [STATUS: in-progress|blocked|done] [test delta: +X/-0] [notes]
```

Example: `[Team-4] [T-DEBT-001] [done] [+47 tests] crud_activity, crud_activity_log complete`

### Conflict Resolution

1. If a team discovers it needs a file owned by another team: **STOP**
2. Report: `[Team-N] CONFLICT: need to modify <file> owned by Team-M for <reason>`
3. Review team arbitrates (reassign file or sequence work)
4. **Never have two teams editing the same file simultaneously**

### Escalation Path

- **Level 1:** Team-internal resolution
- **Level 2:** Review team mediates cross-team conflicts
- **Level 3:** Architectural scope expansion → decide: expand, defer, or accept risk

---

## Checkpoint Protocol

### Git Commit Cadence

- **Sub-task:** After each individual debt item is resolved
- **Wave:** Tag after wave gate passes
- **Format:** `<type>(<scope>): <description> [ITEM-ID,ITEM-ID]`

### Commit Message Template

```
<type>(<scope>): <summary> [ITEM-ID,ITEM-ID]

- <what changed>
- <why>
- Tests: +N new, 0 regressions
```

### Memory Save Triggers

Save to project memory after:

1. Each wave gate passes (mandatory)
2. Any significant architectural decision
3. Any deferred-item decision
4. Session end

### Push Schedule

- Push to remote after each wave gate passes
- Branch: `tech-debt/remediation-phase1`
- PR created after Wave 5 completes, targeting `main`

---

## Review Team Acceptance Criteria

Each resolved debt item must have:

1. The specific code change that resolves it
2. At least one test that would catch regression
3. Zero decrease in existing test count
4. Clean lint/format
5. Commit message referencing the debt item ID

### Wave Sign-Off Template

```
Wave N Sign-Off
- Items completed: [list]
- Items deferred: [list with reason]
- Test delta: +X backend, +Y frontend
- Build: PASS
- Lint: PASS
- Conflicts resolved: [list]
- Approved: YES/NO
```

---

## Deferred Items (Future Sprint)

| ID                   | Severity | Hours | Reason for Deferral                                                              |
| -------------------- | -------- | ----- | -------------------------------------------------------------------------------- |
| T-DEBT-015           | HIGH     | 12-16 | PostgreSQL integration tests — requires CI infra (PG service in GitHub Actions) |
| A-TD-025             | MEDIUM   | 16    | External task queue (ARQ) — architectural, needs design phase                   |
| A-TD-027             | LOW      | 12    | Domain event system — architectural, needs design phase                         |
| T-DEBT-017           | LOW      | 8-12  | Performance/load tests — needs production-like environment                      |
| T-DEBT-018           | MEDIUM   | 10-14 | Dynamic security tests — needs security tooling                                 |
| T-DEBT-002           | MEDIUM   | 6-8   | Schema validation tests — partially addressed by Teams 4+5                      |
| T-DEBT-020           | LOW      | 3-4   | Shared frontend test utilities — can be done incrementally                      |
| T-DEBT-023           | MEDIUM   | N/A   | SQLite workarounds — inherent to test strategy, addressed by T-DEBT-015         |
| And 6 more LOW items | LOW      | ~20   | Diminishing returns — address during regular feature work                       |

---

## Expected Outcomes

| Metric                   | Before         | After         |
| ------------------------ | -------------- | ------------- |
| Total tests              | 3,804          | ~4,200-4,550  |
| E2E in CI                | No             | Yes           |
| Silent E2E skips         | 70             | 0             |
| waitForTimeout calls     | 269            | 0             |
| Sync DB in async         | 13 endpoints   | 0             |
| Double-commit sites      | 41             | 0             |
| Largest file (backend)   | 1,737 lines    | <500 lines    |
| Docker image bloat       | +3-5GB ML deps | Removed       |
| Unpinned deps            | All            | All pinned    |
| Phantom npm deps         | 3              | 0             |
| Mock data in prod bundle | 3,717 lines    | 0             |
| Untyped API responses    | 6+ endpoints   | 0             |
| staleTime magic numbers  | 45+            | 0 (constants) |
