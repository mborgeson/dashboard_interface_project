# Independent Audit — B&R Capital Dashboard

**Date:** 2026-04-08
**Commit:** `d368322` (main)
**Method:** 6 parallel specialized review agents, each reading CODE not prior audit docs
**Reviewer lens count:** backend, frontend, security, data integrity, tests, infra/ops
**Total findings:** 137 (21 Critical, 39 High, 46 Medium, 27 Low)

> This is a **fresh independent audit**. The reviewers were instructed not to read `docs/architecture-review/`, `docs/tech-debt-remediation-plan.md`, `docs/findings-and-recommendations.md`, or any `docs/AUDIT*` file. The goal was to form opinions from CODE, then compare to the existing audits in a dedicated section at the end. Treat this as a second opinion, not a status check.

---

## Executive Summary

The codebase has **strong architectural fundamentals**: Pydantic v2 + SQLAlchemy 2.0 in good form, competent JWT handling, ETag caching, request-ID propagation, loguru logging with structured fields, optimistic locking on deals, cursor pagination, RBAC at the endpoint layer, modern React patterns with Zustand + React Query separation, and Prometheus metrics exposed.

The **gaps are concentrated in three places**:

1. **Secret hygiene and deployment surface** — live credentials on disk, no TLS in prod nginx, no root `.dockerignore`, weak hardcoded dev `SECRET_KEY`.
2. **Safety infrastructure that exists but isn't wired up** — reconciliation checks, output validation, schema drift alerts, and 29 `test.fixme` blocks + 41 skip-on-404 API tests all look like protection but provide none.
3. **Sync/async boundary leakage on the event loop** — multiple `async def` handlers in extraction, construction pipeline, and sales analysis do blocking DB/pandas/openpyxl work that will freeze workers under load.

All three themes share a common pattern: the right machinery has been built, but execution paths bypass it. This is precisely what a "status check" audit would miss — items with green checkmarks in a sprint tracker look fine in isolation; only a code-level read reveals they're not connected to the pipeline that actually runs.

**Production-ready verdict:** not yet — three Critical items must be fixed before first deploy (secrets rotation, TLS termination, `.dockerignore`). Several more should be addressed in the first sprint after.

---

## Top 10 Issues — Severity × Blast Radius

Ranked by a combination of how bad it is when it triggers, how easy it is to trigger, and how silently it fails.

### 1. Live Gmail app password + production-format SECRET_KEY on disk in `.env`

- **Evidence:** `.env:42`, `.env:72`, `.env.backup.root:64-67`
- **Agent:** Security
- **What:** `.env` contains a real 16-character Gmail app password for a live account plus a production-format `SECRET_KEY`. A second copy exists in `.env.backup.root` at repo root. Both files are gitignored (verified via `git check-ignore`), so not leaked to GitHub, but any backup, filesystem sync, antivirus upload, or local breach exposes them.
- **Blast radius:** Account takeover of the Gmail sender account; ability to forge arbitrary JWTs for whatever environment that SECRET_KEY corresponds to.
- **Fix:**
  1. Revoke the Gmail app password in the Google account security settings **today**.
  2. Rotate `SECRET_KEY` to a fresh 64+ character value via `secrets.token_urlsafe(64)`.
  3. Delete `.env.backup.root` from disk.
  4. Add a pre-commit secret scanner (`gitleaks` or `detect-secrets`) so this can't recur.
  5. Long-term: move secrets to Docker secrets or an external vault.

### 2. Reconciliation checks, output validation, and schema drift alerts are dead code

- **Evidence:** `backend/app/extraction/reconciliation_checks.py:110`, `output_validation.py:292`, `group_pipeline.py:805-834`, `backend/app/crud/schema_drift.py:24`
- **Agent:** Data integrity
- **What:** Three safety modules are defined, exported, and tested — but never invoked by the execution path:
  - `run_reconciliation_checks()` never called from `group_pipeline.py` or `crud/extraction.py`. NOI vs Revenue-minus-Expenses internal consistency is never verified on live data.
  - `validate_extraction_output()` is imported only by its own test; production uses the looser `domain_validators.validate_domain_range` which logs to a single warning column.
  - `SchemaDriftDetector.check_drift()` runs, but `SchemaDriftAlertCRUD.create_alert()` is never called from the pipeline. The `/schema-drift/alerts` endpoint always returns an empty list.
- **Blast radius:** Wrong financial numbers ship to decision-makers with zero operator visibility. A cell mapping that drifts out of alignment with a modified proforma template silently produces plausible-looking but wrong cap rates, IRRs, and NOIs.
- **Fix:**
  1. In `group_pipeline.py` around line 905, call `run_reconciliation_checks(result, property_name)` before `ExtractedValueCRUD.bulk_insert`.
  2. Persist failed reconciliations and drift alerts into a warnings table so the dashboard can surface them.
  3. In the drift detection block, call `SchemaDriftAlertCRUD.create_alert(...)` on any severity != "ok" and fail-fast on `severity == "error"`.
  4. Either wire `validate_extraction_output` into the pipeline or delete it and consolidate on `domain_validators`.

### 3. Frontend `safeNum` coerces missing numeric data to `0`

- **Evidence:** `src/lib/api/schemas/property.ts:17-25`, downstream compensation at `src/features/analytics/AnalyticsPage.tsx:82-85,116,138,153,166`
- **Agent:** Frontend
- **What:** `safeNum` is defined as `(v) => Number.isFinite(n) ? n : 0`, applied across 70+ fields (IRR, MOIC, NOI, cap rate, monthly payment, etc.). CLAUDE.md explicitly forbids this: *"Zod pattern: `.nullable().optional()` with `?? undefined` (NOT `?? 0`)."* Downstream code is already compensating with filters like `p.performance.leveredIrr !== 0` — which conflates "missing data" with "legitimately zero" (e.g., a new acquisition with zero current NOI).
- **Blast radius:** Missing extraction values silently become `0` in weighted portfolio KPIs and best/worst highlighting. Compounds with finding #2 — if reconciliation drifts and safeNum coerces, the user sees "0% IRR" with no alarm.
- **Fix:**
  1. Rewrite `safeNum` to return `undefined` for null/NaN.
  2. Make sub-schemas preserve `number | undefined`.
  3. Update `Property` type and all downstream calculators (`calcCashOnCash`, `weightedAvg`, `AnalyticsPage` filters) to handle `undefined` explicitly.
  4. Remove the compensating `!== 0` filters once the schema is correct.

### 4. No TLS termination in production nginx

- **Evidence:** `nginx.conf:8`, `nginx/nginx.conf:104`
- **Agents:** Security + Infra (independently flagged)
- **What:** Neither nginx config has `listen 443 ssl`, `ssl_certificate`, or a TLS cipher suite. Prod compose exposes port 80 only. A previous TLS block was removed at some point (visible in `.checkpoints/.../uncommitted.diff:1373-1408`). The app sets `Strict-Transport-Security` at `backend/app/main.py:80`, but HSTS over plaintext HTTP is ignored by browsers, so HSTS is effectively absent.
- **Blast radius:** JWTs, Azure client secrets, and refresh cookies traverse cleartext on any network. Any coffee shop or untrusted hop equals session hijack.
- **Fix:**
  1. Add a `listen 443 ssl http2` server block with `ssl_protocols TLSv1.2 TLSv1.3`, modern cipher suite, `ssl_session_cache`, and OCSP stapling.
  2. Set `Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"`.
  3. Add a port 80 server block that does `return 301 https://$host$request_uri`.
  4. If fronting with Cloudflare/ALB, enforce that in deploy docs and in compose with `HSTS_PROXIED=1`.

### 5. Sync DB calls and blocking I/O inside `async def` handlers

- **Evidence:** `backend/app/api/v1/endpoints/extraction/status.py:38,111,157,241` · `construction_pipeline.py:929,1030,1056,1083,1124` · `sales_analysis.py:643`
- **Agent:** Backend architecture
- **What:** Four `async def` handlers in `extraction/status.py` use `get_sync_db` and call `db.execute(...)` directly. `async def trigger_import` at `construction_pipeline.py:929` invokes `import_construction_file` which does `pd.read_excel(...)`, `db.query(...).all()`, and `db.flush()` synchronously inside a loop. `async def fetch_all_apis` opens sync `SessionLocal()` context managers on the event loop.
- **Blast radius:** A single slow extraction query or Excel parse blocks the ENTIRE uvicorn worker for minutes. Under 4-worker concurrency (config.py:57) that's 25% of capacity gone per long call. Cascades into timeouts for unrelated traffic.
- **Fix:**
  1. Convert the handlers that are already sync-at-heart (`extraction/status.py` GETs) from `async def` to plain `def` — FastAPI will threadpool them automatically.
  2. For the import handlers, wrap sync import calls in `await asyncio.to_thread(...)` so they run off the event loop.
  3. For `fetch_all_apis`, pre-acquire `AsyncSession` via `Depends(get_db)` and use async save functions.

### 6. Test suite is lying — silent skips, fixmes, and crash-as-pass patterns

- **Evidence:**
  - 29 `test.fixme(true, ...)` in `e2e/deal-pipeline.spec.ts`, `deal-comparison.spec.ts`, `exports.spec.ts`, `deals-crud.spec.ts`, `underwriting-deal.spec.ts`
  - 41 `pytest.skip()` on 404 responses in `backend/tests/test_api/test_analytics.py`, `test_exports.py`, `test_monitoring.py`
  - 10 assertions of shape `assert response.status_code in [200, 500]` in `test_exports.py:32,74,94,133,156,193,226,245,275,296`
  - 269 `waitForTimeout` calls across 16 e2e files
  - 139 `pytest.skip` total across 15 backend test files
- **Agent:** Tests
- **What:** The 4,400+ test count overstates real protection by approximately 2-5%. Specific smoking guns:
  - Export tests that literally pass when the export service crashes with 500.
  - Analytics/monitoring/exports tests that pass when the endpoint is deleted (skip on 404) — exactly the scenario the recent commit `d368322` "delete Transactions" creates.
  - Kanban E2E tests where `test.fixme(true, ...)` fires if no cards are found, making card-absence a silent pass instead of a seed-data failure.
  - Extraction tests that `pytest.skip("No fixture files available")` — meaning a CI runner without the reference XLSX reports green with zero extraction coverage. CLAUDE.md calls extraction "the most fragile module" with template-specific cell references.
- **Blast radius:** CI gives false confidence. Regressions in export, analytics, monitoring, extraction, and deal Kanban modal interaction can ship unnoticed.
- **Fix:**
  1. Remove all 41 `if response.status_code == 404: pytest.skip(...)` branches. Delete obsolete tests or fail hard.
  2. Change all `[200, 500]` assertions to `== 200` and mock underlying services.
  3. Convert `test.fixme` blocks to hard failures; seed required deal data in `beforeAll`.
  4. Replace `waitForTimeout` with `waitFor` / `expect().toBeVisible()`.
  5. Commit extraction fixtures to the test tree or fail hard if missing.

### 7. Zod validation bypassed in 8 of 10 API hook files

- **Evidence:** `src/hooks/api/useProperties.ts:62-72,99-110,132-141` · `useMarketData.ts:121-174` · `useReporting.ts` · `useTransactions.ts` · `useInterestRates.ts` · `useDocuments.ts` · `useExtraction.ts` (only `useDeals.ts` and `useDealComparison.ts` call `backendDealSchema.safeParse`)
- **Agent:** Frontend
- **What:** Most hooks use raw `get<T>()` which trusts the TypeScript generic at compile time but never validates shape at runtime. `useMarketData.ts` works around this with hand-written transform functions (`transformMSAOverview`, `transformSubmarket`, etc.) that diverge from the Zod pattern declared in CLAUDE.md. When backend renames or drops a snake_case field, the frontend silently receives `undefined` and components render NaN or blank.
- **Blast radius:** Silent contract drift across the majority of the application. Combined with finding #3 (`safeNum → 0`), this is the second half of the "wrong numbers silently reach users" picture.
- **Fix:** Migrate each hook to parse via a Zod schema in `queryFn`, or at minimum move `transformXxx` helpers into `.transform()` blocks in `src/lib/api/schemas/`.

### 8. Dev compose hardcodes weak `SECRET_KEY`

- **Evidence:** `docker-compose.yml:64`
- **Agents:** Infra + Security (independently flagged)
- **What:** `SECRET_KEY=dev-secret-key-change-in-production` as a literal default. If an operator ever runs this compose file against a reachable DB (CI runner, contractor laptop, exposed dev host), any JWT signed with this key is trivially forgeable by anyone reading this repo.
- **Blast radius:** Full auth bypass on any reachable host running dev compose.
- **Fix:** Change to `${SECRET_KEY:?SECRET_KEY is required}` just like `docker-compose.prod.yml:112` already does. Fail startup if not set.

### 9. No root `.dockerignore`

- **Evidence:** Missing `/.dockerignore`; `Dockerfile.frontend:26` does `COPY . .`
- **Agent:** Infra
- **What:** The frontend Dockerfile copies the entire project root into the build context. With no root `.dockerignore`, this pulls in `.env*`, `.env.backup.root`, `backend/venv/`, `.git/`, `antigravity/brain/`, `.checkpoints/`, and every `docs/` file.
- **Blast radius:** (a) secrets baked into image layers — once in a layer, they're in every image digest that shares that layer and very hard to scrub retroactively; (b) build context bloat = slow builds; (c) cache-bust on any file change anywhere in the repo.
- **Fix:** Create `/.dockerignore` mirroring `backend/.dockerignore` plus frontend-specific ignores: `backend/`, `docs/`, `.checkpoints/`, `antigravity/`, `.env*`, `.git`, `node_modules`, `dist`.

### 10. Cap rate / IRR unit ambiguity between validators

- **Evidence:** `backend/app/extraction/domain_validators.py:64-68` vs `output_validation.py:90-100`
- **Agent:** Data integrity
- **What:** `DOMAIN_RULES` encodes cap rate as a fraction (`0.03-0.15`), but `VALIDATION_RULES` encodes it as a percentage (`0-20`, warning at `2-15`). Same for IRR and occupancy. Whichever validator runs depends on which fields the extractor produces. A cap rate stored as `5.5` (meaning "5.5%") passes `domain_validators` as a massive outlier AND passes `output_validation` as a normal value. Or a stored fraction `0.055` passes `domain_validators` but triggers a different warning in `output_validation`.
- **Blast radius:** Different validators disagree on what a valid number looks like. Any future author wiring up these validators will import inconsistent rules and pick whichever happens to pass.
- **Fix:** Pick one convention (recommend fractions since `T12_RETURN_ON_COST` from Excel is typically a fraction) and enforce it in a single validator at write time. Align `domain_validators` and `output_validation` to the same units or delete one.

---

## Cross-Cutting Themes

Six patterns emerged consistently across the six independent reviews. These are the "why" behind the top 10.

### Theme 1: Dead safety code

Multiple safety systems exist as code but aren't connected to the execution path:

- `run_reconciliation_checks()` — defined, exported, never called.
- `validate_extraction_output()` — imported only in its own test file.
- `SchemaDriftAlertCRUD.create_alert()` — has a CRUD wrapper, but no writer.
- 29 `test.fixme(true, ...)` — Playwright tests that look like tests but pass unconditionally.
- 41 `if response.status_code == 404: pytest.skip(...)` — API tests that pass when endpoints are deleted.

The pattern: **the hard work of designing and implementing safety was done, but the last mile of wiring was skipped**. This is worse than no safety at all because it creates false confidence in both reviewers and operators.

### Theme 2: Financial data can corrupt silently end-to-end

Five independent findings combine into one silent-failure pipeline:

1. Cell mapping drifts because drift alerts aren't persisted → wrong cells extracted.
2. `error_category` isn't populated on `unknown_error` paths (`extractor.py:258-263` bypasses the error handler) → no way to diagnose what happened.
3. Reconciliation checks don't run → NOI vs Rev-OpEx mismatches pass.
4. Float rounding in `value_numeric = float(value)` (`crud/extraction.py:262`) → small precision drift on sums.
5. Frontend `safeNum → 0` → remaining None values become zero.

A user sees "2.8% cap rate" and has no idea whether that's real, a mapping drift, or a missing-value coercion. Fixing any one link does not fix the pipeline — they compound.

### Theme 3: Test suite overstates coverage

- 4,400+ tests is the headline number.
- After removing silent skips on 404, silent 5xx-as-pass, defensive `isVisible().catch()` guards, fixture-gated extraction tests, and content-free status-only assertions, the real protective count is probably **3-5% lower**.
- The remaining tests are high quality in the covered areas (`test_services/test_financial_boundaries.py`, `test_core/test_token_blacklist.py`, `useDeals.test.ts` Zod roundtrip, optimistic locking tests).
- The problem is distribution: hot paths are tested; cold paths that are most likely to regress (export, analytics, monitoring, extraction edge cases, deal E2E) are the ones with the silent skip patterns.

### Theme 4: Deployment surface isn't production-ready

Independent of code quality, the deploy story has gaps that would bite on first prod push:

- No TLS (see #4)
- No root `.dockerignore` (see #9)
- Weak dev `SECRET_KEY` (see #8)
- Prod compose lacks `user:`, `read_only: true`, `cap_drop`, `security_opt: [no-new-privileges:true]`
- No observability stack (Prometheus endpoint exists but no scraper, no Grafana, no Sentry wired up)
- CI runs tests against SQLite; prod runs Postgres (SQLite doesn't enforce enum values, JSONB, lock semantics the same way)
- Backend Dockerfile uses `python:3.11-slim` while `backend-ci.yml:19` and CLAUDE.md target 3.12 — **you test on 3.12 and ship 3.11**
- Dev Postgres/Redis bound to `0.0.0.0` with hardcoded `postgres123` password

### Theme 5: Sync/async boundary is leaking

The backend has genuinely strong SQLAlchemy 2.0 async fundamentals — `AsyncSession`, proper `await`, good base CRUD, cursor pagination, optimistic locking — but the extraction and construction-pipeline domains have crept into a hybrid model:

- `extraction/status.py` GET handlers are declared `async def` but use `get_sync_db`.
- `construction_pipeline.py:929` calls pandas/openpyxl on the event loop.
- `extraction/common.py:647-682` spins up `asyncio.new_event_loop()` inside a FastAPI BackgroundTask to call async SharePoint code from a sync context — fragile across threading models.

This is the kind of drift that happens when a feature is added by someone who doesn't fully trust the async model. Under low concurrent load it looks fine. Under real traffic it blocks workers.

### Theme 6: Repository hygiene is drifting

73 uncommitted entries on `main`:

- **Stale environment migration**: `.pre-commit-config.yaml` changed from WSL/conda paths to bare `mypy`, `.mcp.json` changed server paths, `backend/.env.example` changed. This looks like a WSL → Windows dev migration that never got committed atomically.
- **`CLAUDE.md` has UTF-8 → CP1252 mojibake**: characters like `â€"` instead of `—`. An editor re-saved without BOM. The reference doc for the project is now literally corrupted.
- **Tracked noise**: ~40 modified files under `antigravity/brain/*.md.resolved.*` are automated agent scratch output that should be `.gitignore`d.
- **Untracked debug scratch**: `backend/test_import.py`, `backend/test_uvicorn.py`, `backend/test_uvicorn2.py` are ad-hoc "does uvicorn start" scripts.
- **Stale checkpoints**: `.checkpoints/index.json` shows 4 entries from `20260113_*`, now 3 months old.

Individually minor. Combined: the project is in a state where `git status` perpetually shows 73 entries, so the signal of "something important is unstaged" is lost in noise. **The maintainer stops reading `git status` because it's always dirty**, and real in-progress work hides in the noise.

---

## Findings by Dimension — Critical & High Only

*(Medium and Low findings are recorded per-agent in the task output files at `C:\Users\MATTBO~1\AppData\Local\Temp\claude\...\tasks\*.output` and can be pulled into follow-up work as desired.)*

### Backend Architecture & Async — 5 Critical / 6 High

**Critical**
- **Sync DB in 4 async `extraction/status.py` endpoints** — `extraction/status.py:38,111,157,241` — see top-10 #5.
- **`construction_pipeline.py:929` async import blocking on pandas** — see top-10 #5.
- **`construction_pipeline.py:1030,1056,1083,1124` sync `SessionLocal()` inside `fetch_all_apis`** — see top-10 #5.
- **Double-commit pattern**: `db/session.py:100-108` commits on success, but endpoints also call `await db.commit()` explicitly (`deals/crud.py:517`, `dead_letter.py:102`, `construction_pipeline.py:1174`). `crud_user.update_last_login` (`crud_user.py:69`) also does its own rollback on failure. Impact: double commits partially persist on mid-flight failures; nested rollback can corrupt the outer session.
- **Unbounded query `/construction-pipeline/all`** — `construction_pipeline.py:347` has no `.limit()` on list_all_projects. OOM + long event-loop blocks as the table grows.

**High**
- **God-files >1000 lines**: `market_data.py` (1720), `group_pipeline.py` (1431), `construction_pipeline.py` (1180), `extraction/file_monitor.py` (1040), `crud/extraction.py` (1038), `extraction/sharepoint.py` (1016), `properties.py` (1010).
- **Business logic leaking into endpoints**: `properties.py:79-166` (`_build_projected_trends`) and `properties.py:263-344` (`get_portfolio_summary` with NOI-per-unit math). Code even has TODOs at lines 93 and 271.
- **Endpoint reaching into CRUD private method**: `deals/crud.py:153` calls `deal_crud._build_deal_conditions(...)`; `properties.py:465` calls `property_crud._build_property_conditions(...)`.
- **~72 endpoints missing `response_model`**: 198 routes, 126 annotated. OpenAPI schema gaps, no response validation.
- **`extraction/common.py:647-682` spawns own event loop in FastAPI BackgroundTask**: `asyncio.new_event_loop(); loop.run_until_complete(...)`. Fragile in any already-looped context (e.g., tests).
- **Deal list `page_size` allows 500** — `deals/crud.py:55` — `le=500` while cursor variant caps at 100. Combined with per-deal enrichment lookups, a single request can fan out to hundreds of queries.

### Frontend & React — 2 Critical / 5 High

**Critical**
- **Zod bypass in 8 of 10 API hooks** — see top-10 #7.
- **`safeNum → 0` silent financial data coercion** — see top-10 #3.

**High**
- **`useKanbanBoardWithMockFallback` silently drops invalid deals**: `useDeals.ts:114-130` console-warns and skips deals that fail `safeParse`. Data loss invisible in production.
- **Auth token side-channel via `localStorage`**: `client.ts:40,58-59,117,168-200` reads token directly from localStorage while `authStore.ts:25-124` holds it in Zustand. Two paths can drift after refresh — stale token can appear in components.
- **ETag cache retained across logout**: `client.ts:14-29,198-201` — module-scoped `etagCache` never cleared on `auth:unauthorized`. Cross-user data leakage risk on shared browsers: new user can get a 304 + cached data from prior user.
- **Leaflet tile effect uses non-null assertion in cleanup**: `MappingPage.tsx:153-170` — `mapInstanceRef.current!.removeLayer(...)` inside a callback. In strict mode double-mount, `mapInstanceRef.current` can be null and `!` throws.
- **Quadratic render in GlobalSearch**: `GlobalSearch.tsx:150-151,189-190` — `results.findIndex(r => r.id === result.id)` inside `.map()`. O(n²) per keystroke.

### Security & Dependencies — 4 Critical / 11 High

**Critical**
- **Live Gmail password + SECRET_KEY on disk** — see top-10 #1.
- **Dev compose hardcoded SECRET_KEY** — see top-10 #8.
- **No TLS in prod nginx** — see top-10 #4.
- **Prod compose lacks container hardening**: `docker-compose.prod.yml:9-190` — no `user:`, `read_only: true`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, no tmpfs isolation. Backend Dockerfile.prod uses USER appuser but compose doesn't enforce.

**High**
- **JWT tokens lack `iat` claim**: `security.py:66-76` — no `iat`, which means `token_blacklist.is_user_revoked` can't filter by issuance time (see comment at `token_blacklist.py:115` admitting `token_iat` is "unused for now"). User-level revocation is effectively a no-op.
- **JWT `decode_token` swallows all exceptions**: `security.py:110-111,130-131` — `except (PyJWTError, Exception): return None`. Any programming bug in validation looks like invalid token.
- **JWT decode has no `require=[...]`**: `security.py:108` — no `options={"require": ["exp","sub","jti"]}`. Forged tokens missing `exp` could pass if library default changes.
- **JWT algorithm from settings not code constant**: `security.py:75,108` — `algorithms=[settings.ALGORITHM]`. Classic "alg confusion" vector if config leaks.
- **File upload buffers entire file in memory before size validation**: `documents.py:282-290` — `file_content = await file.read()` runs before `validate_upload` checks length. Root `nginx.conf:43` has no `client_max_body_size`. Single attacker can OOM backend with 10GB upload.
- **Login username enumeration via distinct error messages**: `auth.py:97` returns "User account is disabled" (403) vs `auth.py:160` "Incorrect email or password" (401). Also logs `email=form_data.username` on every failure.
- **`X-Forwarded-For` trusted without proxy allowlist**: `middleware/rate_limiter.py:302-305` — takes first IP unconditionally. Rate limiter bypassable via header spoofing if backend port 8000 is reachable or proxy misconfigured.
- **CORS default includes localhost with `allow_credentials=True`**: `config.py:103-111` + `main.py:364`. Production env override helps but code default is phishing-friendly.
- **`X-Request-ID` accepted verbatim — log injection**: `middleware/request_id.py:46` — client-supplied value formatted into log lines. `X-Request-ID: "\n[WARN] fake log entry"` pollutes audit logs.
- **`python-multipart>=0.0.6` in `requirements-ci.txt:8`** — CVE-2024-24762 ReDoS in versions < 0.0.7. Main requirements pin `>=0.0.22` (safe) but CI lane could resolve older.
- **`.env.example` placeholders look real** — `your_fred_api_key_here` at `.env.example:27` passes grep-based secret scanners.

### Data Integrity & Extraction — 4 Critical / 5 High

**Critical**
- **Reconciliation checks never run** — see top-10 #2.
- **`validate_extraction_output()` dead code** — see top-10 #2.
- **Schema drift alerts never persisted** — see top-10 #2.
- **Percentage unit ambiguity across validators** — see top-10 #10.

**High**
- **IRR Newton-Raphson can divide by zero**: `src/lib/calculations/irr.ts:22` and `src/features/underwriting/utils/calculations.ts:76` — `newGuess = guess - npv / dnpv` never guards against `dnpv === 0`. No bisection fallback. No sign-change check on cash flows. Tests at `src/lib/calculations/__tests__/irr.test.ts:119-123` only assert `typeof result === 'number'` — NaN is a number.
- **Enrichment double-maps `T12_RETURN_ON_COST`**: `deals/enrichment.py:296-298,378-380` — same extracted field assigned to both `deal.t12_return_on_cost` and `deal.total_cost_cap_t12`. Dashboard shows identical values in two columns labeled differently.
- **Missing `GOING_IN_CAP_RATE` read in enrichment**: `enrichment.py:399-401` reads `EXIT_CAP_RATE` but not going-in. Deal cards hide the spread that defines the value-creation thesis. The field exists in `domain_validators.py:64` and is referenced in test fixtures.
- **`DealResponse.projected_irr/coc` typed as `Decimal` backend but Zod transform silently drops**: `schemas/deal.py:171-173` vs `src/lib/api/schemas/deal.ts:53-55` + transform at `deal.ts:111` — the legacy field never reaches the frontend.
- **`value_numeric = float(value)` loses precision**: `crud/extraction.py:262` — should be `Decimal(str(value))` to preserve exactness into a `Numeric(20,4)` column.

### Test Quality — 3 Critical / 5 High

**Critical**
- **29 `test.fixme(true, ...)` in E2E** — see top-10 #6.
- **41 `pytest.skip(...)` on 404 in API tests** — see top-10 #6.
- **10 `assert response.status_code in [200, 500]` in exports** — see top-10 #6.

**High**
- **Export tests only validate Content-Type inside `if status == 200`**: `test_exports.py:34-37` — zero of the 15 export tests actually prove export content is correct. No assertion on workbook byte count, sheet structure, row count, or column headers.
- **269 `waitForTimeout` calls across 16 e2e files**: `deal-comparison.spec.ts` (16), `cross-feature.spec.ts` (29), `construction-pipeline.spec.ts` (28), `sales-analysis.spec.ts` (37), `reporting-suite.spec.ts` (46), `underwriting-deal.spec.ts` (24), `market-widgets.spec.ts` (19). Playwright's own anti-pattern — flakes on slow CI, hides bugs on fast CI.
- **Deal pipeline E2E wraps assertions in `isVisible().catch(() => false)` guards**: `deal-pipeline.spec.ts:200-296` and 13 more blocks through line 598 — assertions only run if the element happens to be visible. A missing metric label fails nothing.
- **139 `pytest.skip` across 15 backend test files**: including fixture-gated extraction tests. Extraction (the most fragile module) can silently have zero coverage in CI.
- **Status-code-only tests dominate `test_deals.py`**: 43 status checks, 32 body reads, most body reads check 1-2 keys. `test_list_deals_sort_order` has zero assertions on actual sort order. Filter/sort could be broken and tests would pass.

### Infrastructure & Ops — 3 Critical / 7 High

**Critical**
- **No TLS in prod nginx** — see top-10 #4.
- **No root `.dockerignore`** — see top-10 #9.
- **Dev compose hardcoded SECRET_KEY** — see top-10 #8.

**High**
- **Working tree in undefined state on main** — see Theme 6. 73 uncommitted entries, corrupted `CLAUDE.md` encoding, stale WSL→Windows migration, tracked scratch files.
- **`CORS_ORIGINS=${CORS_ORIGINS:-}` silently becomes empty**: `docker-compose.prod.yml:119`. Should be `${CORS_ORIGINS:?CORS_ORIGINS is required}`.
- **Postgres `log_statement=mod` in prod**: `docker-compose.prod.yml:53` — logs every mutating statement to container stdout, which persists via json-file driver. Potential PII in unencrypted container logs.
- **No CI concurrency groups**: `backend-ci.yml:3-18`, `frontend-ci.yml:3-32`, `e2e.yml:10-19` — rapid force-pushes queue parallel runs, wasted runner minutes, racy coverage.
- **Token blacklist falls back to in-memory on Redis error**: `token_blacklist.py:61-65,99-107,185-187` — with 4 workers (`WORKERS=4` in `docker-compose.prod.yml:117`), a logout on worker A doesn't invalidate the token on workers B-D. Restart loses all blacklisted tokens.
- **No observability stack — only `/metrics` endpoint exists**: `monitoring.py:35-56` exposes Prometheus metrics, but no scraper in compose, no Grafana, no Sentry (`.env.prod.example:89` has it commented out).
- **CI never runs against PostgreSQL for main test job**: `backend-ci.yml:63-64` only runs `-m pg`-marked subset in a separate `test-pg` job that exercises isolated query tests, not API/CRUD layer. False greens for enum values, JSONB operators, server_defaults.

---

## Comparison to Existing Audits

The user explicitly asked for a fresh audit independent of `docs/architecture-review/` and `docs/tech-debt-remediation-plan.md`. Comparison was performed only after agents returned their findings.

### CONFIRMS (existing audits were right)

- **Redis fallback to in-memory risk** — Architecture Review v3 listed this as Top-5 critical. My review confirms: token blacklist and cache both still silently degrade on Redis outage, and the fallback is per-worker under 4-worker gunicorn.
- **Sync DB sessions in async endpoints** — Tech Debt C-TD-015 listed "13 sync DB sessions in async endpoints". My review found this *plus new sites* that the remediation didn't reach: `extraction/status.py`, `construction_pipeline.py:929,1030,1056,1083,1124`, `sales_analysis.py:643`. **Status: partially fixed; new sites introduced since.**
- **Unbounded queries** — Tech Debt A-TD-017. My review confirms `construction_pipeline.py:347` list_all_projects is still unbounded; `deals/crud.py:55` allows `le=500` while cursor variant caps at 100.
- **God-files** — Tech Debt C-TD-007 listed deals.py at 1,737 lines and was scheduled for decomposition. `deals.py` has been split (good — decomposed into `deals/crud.py`, etc.). But other god-files grew: `market_data.py` (1720), `group_pipeline.py` (1431), `construction_pipeline.py` (1180). **Status: moved rather than resolved.**

### CONTRADICTS (claimed fixed, still present)

- **Tech Debt claimed C-TD-015 "13 sync DB sessions" was being resolved by Team 2 in Wave 1.** Reality: still present in extraction, construction pipeline, sales analysis. At least 4 new sites.
- **Architecture Review v3 Top-5 #1 was "error_category never populated".** Reality: `error_category` IS now populated for explicit error paths through `error_handler`, BUT the `unknown_error` catch-all at `extractor.py:258-263` bypasses the error handler and leaves `error_category=None`. **Status: partially fixed.**
- **Tech Debt T-DEBT-016 was "E2E tests not in CI — 20 Playwright specs provide zero CI value".** Reality: there is now an `e2e.yml` workflow. But 29 `test.fixme(true, ...)` calls and 269 `waitForTimeout` calls mean E2E now runs in CI *and silently passes while broken*. **Status: worse than before — previously non-running tests are now running-but-lying tests.**
- **Tech Debt C-TD-022 was "fix DocumentApiResponse dual-casing".** I did not verify this one directly; the frontend agent found broader Zod bypass patterns across 8 of 10 hooks, which may include this module or not.

### EXTENDS (new findings beyond existing audits)

Fresh eyes found items not in the prior audits:

- **Live credentials on disk in `.env` and `.env.backup.root`** — neither audit flagged this. **Immediate priority.**
- **`safeNum → 0` silent financial data coercion** in `property.ts` — not in prior audits, violates CLAUDE.md rules directly.
- **Reconciliation/output validation/drift alerts are dead code** — Architecture Review v3 mentioned drift detection but didn't catch that the *alerts are never persisted*.
- **No TLS in prod nginx** — not in prior audits. Possibly assumed to be handled by a fronting proxy, but neither compose nor nginx configs reflect that assumption.
- **No root `.dockerignore`** — not in prior audits.
- **29 `test.fixme(true, ...)` in E2E** — prior audits found 70 `test.skip()`, which may have been converted to `test.fixme` as a "fix" that preserved the silent-pass pattern.
- **Cap rate / IRR unit ambiguity between validators** — not in prior audits.
- **Real Gmail password on disk** — not in prior audits.
- **IRR div-by-zero in Newton-Raphson** — not in prior audits.
- **Working tree corruption** (CLAUDE.md mojibake, stale WSL migration) — not in prior audits. This is a "now" state issue, not something a structural audit would catch.

### Overall comparison verdict

The existing Architecture Review v3 and Tech Debt Plan are **solid structural audits** that caught the right architectural issues. The fresh audit **did not invalidate them** — it extended them with:

1. **Secret hygiene and deploy surface issues** that a code-only review would miss.
2. **"Fixed items that weren't really fixed"** — the gap between "closed in sprint tracker" and "actually wired up in the execution path".
3. **Current-moment repository state issues** (corrupted files, dirty tree, stale migration).

If the existing audits had been treated as truly complete, several severe issues would have shipped to production undetected. The fresh lens validated the cost of periodic independent review.

---

## Recommended Order of Attack

Three phases ordered by dependency: do the first phase before anything else, then work the second phase before the third. Items within each phase can be worked in parallel where they touch different files.

### Phase 0 — Immediate (do first, before next deploy)

1. **Revoke the Gmail app password now** (`.env:42`).
2. **Rotate `SECRET_KEY`** (`.env:72`).
3. **Delete `.env.backup.root`**.
4. **Add a pre-commit secret scanner** (`gitleaks` or `detect-secrets`).
5. **Change dev compose `SECRET_KEY` to required-from-env** (`docker-compose.yml:64`).
6. **Create root `/.dockerignore`** mirroring `backend/.dockerignore` plus frontend excludes (`backend/`, `docs/`, `.checkpoints/`, `antigravity/`, `.env*`).
7. **Clean up working tree**: commit or revert the WSL→Windows migration atomically; gitignore `antigravity/brain/*.resolved*`; delete `backend/test_uvicorn*.py`; fix `CLAUDE.md` encoding.
8. **Require `CORS_ORIGINS` in prod compose**: `${CORS_ORIGINS:?CORS_ORIGINS is required}`.

### Phase 1 — Short-term (before first production deploy)

9. **Wire up reconciliation checks, output validation, and schema drift alerts** in `group_pipeline.py`. Persist failures to a warnings table.
10. **Add TLS to prod nginx** (or document + enforce fronting proxy).
11. **Fix sync-in-async endpoints** in `extraction/status.py`, `construction_pipeline.py`, `sales_analysis.py` — convert to `def` or wrap in `await asyncio.to_thread(...)`.
12. **Replace `safeNum` with `undefined` path** in `src/lib/api/schemas/property.ts`; update downstream calculators and remove compensating `!== 0` filters.
13. **Remove `test.fixme(true, ...)` blocks** from E2E specs; seed test data in `beforeAll`; convert to hard failures.
14. **Remove 41 `pytest.skip` on 404** in backend API tests; change `[200, 500]` assertions to `== 200`.
15. **Align cap rate / IRR units** across `domain_validators.py` and `output_validation.py` — pick fractions or percentages, enforce at write time.

### Phase 2 — Medium-term (post-launch hardening)

16. **Migrate remaining hooks to Zod validation** (`useProperties`, `useMarketData`, `useReporting`, `useTransactions`, `useInterestRates`, `useDocuments`, `useExtraction`).
17. **Add container hardening** to `docker-compose.prod.yml` (`user:`, `read_only:`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`).
18. **Add observability stack**: Prometheus + Grafana compose profile; wire Sentry DSN as required-if-set env.
19. **Move CI main test job to Postgres service**; keep SQLite as a fast smoke job.
20. **Pin backend Dockerfiles to Python 3.12** to match CI.
21. **Bound `deals/crud.py:55` page_size to 100**; bound `construction_pipeline.py:347` `list_all_projects`.
22. **Add `iat` to JWTs; require `exp`/`sub`/`jti` in decode**.
23. **JWT decode exception narrowing** (`security.py:110-111`).
24. **Login response unification** (remove 403 vs 401 distinction on `auth.py:97,160`).
25. **Trusted-hosts check for `X-Forwarded-For`** in `rate_limiter.py:302-305`.
26. **`X-Request-ID` regex validation** in `middleware/request_id.py:46`.
27. **IRR div-by-zero guard** in `irr.ts:22` and underwriting calculations.
28. **Split god-files**: `market_data.py`, `group_pipeline.py`, `construction_pipeline.py`, `file_monitor.py`.

Medium and Low findings are documented in the agent output files and can be pulled into the backlog as capacity allows.

---

## Appendix: Raw Agent Output Files

For detail beyond Critical and High (Medium and Low findings, verbatim agent commentary, additional file:line references):

- Backend architecture: `C:\Users\MATTBO~1\AppData\Local\Temp\claude\...\tasks\a63465150ebd6bd8b.output`
- Frontend React: `C:\Users\MATTBO~1\AppData\Local\Temp\claude\...\tasks\a96c2c9c000ad18e0.output`
- Security: `C:\Users\MATTBO~1\AppData\Local\Temp\claude\...\tasks\aeafda6a5debd6539.output`
- Data integrity & extraction: `C:\Users\MATTBO~1\AppData\Local\Temp\claude\...\tasks\a3d6e767e48907e48.output`
- Test quality: `C:\Users\MATTBO~1\AppData\Local\Temp\claude\...\tasks\ade2f84022092bb1d.output`
- Infrastructure & ops: `C:\Users\MATTBO~1\AppData\Local\Temp\claude\...\tasks\a3fcaa77bde0e1d52.output`

*(The temporary paths will expire with the session. If you want the full raw agent reports preserved permanently, say the word and I'll export each to `docs/reviews/raw/`.)*
