# Agent Team Reference Guide

A comprehensive reference for Claude Code's built-in team functionality, listing practical tasks, the agents needed for each, their capabilities, and workflows.

---

## Routine Maintenance

### 1. Dependency Audit & Update

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                                                    |
| ---------- | ------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Researcher | `researcher`  | Yes       | All tools                           | Scan `package.json`, `pyproject.toml` for outdated/vulnerable deps. Check changelogs for breaking changes.                      |
| Tester     | `tester`      | Yes       | Read, Write, Edit, Bash, Grep, Glob | After researcher identifies updates, run `npm audit`, `pip-audit`, bump versions, run full test suite to verify nothing breaks. |

**Flow**: Researcher identifies what's outdated/risky → reports findings → Tester applies updates one-by-one and runs tests after each → reports pass/fail.

---

### 2. Dead Code / Unused Import Cleanup

| Agent Name | subagent_type | Can Edit?          | Tools                               | Role on Team                                                                                  |
| ---------- | ------------- | ------------------ | ----------------------------------- | --------------------------------------------------------------------------------------------- |
| Explorer   | `Explore`     | **No** (read-only) | All except Edit/Write               | Scan codebase for unused exports, orphaned files, dead imports. Produce a list of candidates. |
| Coder      | `coder`       | Yes                | All tools                           | Take the explorer's list, remove dead code, update import graphs.                             |
| Tester     | `tester`      | Yes                | Read, Write, Edit, Bash, Grep, Glob | Run full test suite + type check after each removal to confirm nothing broke.                 |

**Flow**: Explorer produces dead code report → Coder removes in batches → Tester verifies after each batch → team reports summary of what was removed.

---

### 3. Type Coverage Sweep

| Agent Name | subagent_type       | Can Edit? | Tools     | Role on Team                                                                                                                                  |
| ---------- | ------------------- | --------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| TS Expert  | `typescript-expert` | Yes       | All tools | Deep knowledge of TS type system, generics, inference. Finds `any` types, missing return types, untyped API calls. Fixes complex type issues. |
| Coder      | `coder`             | Yes       | All tools | Handle bulk simple fixes (adding return types, replacing `any` with proper types).                                                            |

**Flow**: TS Expert audits the codebase for type gaps, prioritizes by severity → Coder handles straightforward fixes → TS Expert handles complex generics/conditional types → both run `tsc --noEmit` to verify.

---

### 4. Test Gap Analysis

| Agent Name    | subagent_type   | Can Edit? | Tools                               | Role on Team                                                                                                       |
| ------------- | --------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Explorer      | `Explore`       | **No**    | All except Edit/Write               | Map all functions/endpoints/components. Cross-reference against existing test files. Identify untested code paths. |
| Test Engineer | `test-engineer` | Yes       | Read, Write, Edit, Bash, Grep, Glob | Write missing tests. Specializes in test creation, coverage analysis, and validation across all testing levels.    |

**Flow**: Explorer produces a gap report (file:function → has test? branch coverage?) → Test Engineer writes tests for highest-priority gaps → runs suite to confirm coverage increase.

---

### 5. Lint & Style Enforcement

| Agent Name     | subagent_type    | Can Edit? | Tools     | Role on Team                                                                                                           |
| -------------- | ---------------- | --------- | --------- | ---------------------------------------------------------------------------------------------------------------------- |
| Linting Expert | `linting-expert` | Yes       | All tools | Expert in ESLint, Ruff, Prettier, coding standards across languages. Audits config, identifies violations, fixes them. |
| Coder          | `coder`          | Yes       | All tools | Handle bulk auto-fixable violations. Update config files if linting expert recommends rule changes.                    |

**Flow**: Linting Expert audits current config + violations → auto-fixes what's safe → Coder handles manual fixes that need context → both verify with `npm run lint` and `ruff check`.

---

## Code Quality & Health

### 6. Security Audit

| Agent Name       | subagent_type      | Can Edit? | Tools                        | Role on Team                                                                                                       |
| ---------------- | ------------------ | --------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Security Auditor | `security-auditor` | Yes       | Read, Edit, Bash, Grep, Glob | OWASP compliance, vulnerability assessment, auth flow review, dependency scanning. Specializes in threat modeling. |
| Researcher       | `researcher`       | Yes       | All tools                    | Research CVEs for current dependencies, check for known exploit patterns, verify security headers and CORS config. |

**Flow**: Security Auditor systematically checks auth flows, SQL injection, XSS, CSRF, secrets exposure → Researcher checks dependencies against CVE databases → both produce prioritized findings report with severity levels.

**Note**: The `security-auditor` type exists in multiple plugins (comprehensive-review, full-stack-orchestration, standalone). All have similar capabilities. The standalone one has: Read, Edit, Bash, Grep, Glob, Task, Skill.

---

### 7. API Contract Validation

| Agent Name        | subagent_type                           | Can Edit? | Tools                               | Role on Team                                                                                       |
| ----------------- | --------------------------------------- | --------- | ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools                           | Expert in REST/GraphQL API design. Reviews Pydantic schemas, endpoint signatures, response shapes. |
| Tester            | `tester`                                | Yes       | Read, Write, Edit, Bash, Grep, Glob | Writes contract tests that assert frontend Zod schemas match backend Pydantic schemas.             |

**Flow**: Backend Architect maps all Pydantic response models → compares field-by-field against frontend Zod schemas in `src/lib/api/schemas/` → Tester writes automated contract tests to catch future drift → reports all mismatches.

---

### 8. Performance Profiling

| Agent Name        | subagent_type       | Can Edit? | Tools                        | Role on Team                                                                                                        |
| ----------------- | ------------------- | --------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Performance Tuner | `performance-tuner` | Yes       | Read, Edit, Bash, Grep, Glob | Application profiling, bottleneck analysis, optimization. Profiles endpoints, identifies N+1 queries, slow renders. |
| Explorer          | `Explore`           | **No**    | All except Edit/Write        | Maps data flow paths, identifies where queries happen, traces request lifecycle.                                    |

**Flow**: Explorer maps hot paths (which endpoints call which queries, which components trigger re-renders) → Performance Tuner profiles them, measures timing, identifies bottlenecks → produces ranked optimization recommendations.

---

### 9. Database Query Review

| Agent Name      | subagent_type     | Can Edit? | Tools                                             | Role on Team                                                                                                               |
| --------------- | ----------------- | --------- | ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Postgres Expert | `postgres-expert` | Yes       | Bash(psql, pg_dump, pg_restore), Read, Grep, Edit | Deep PostgreSQL expertise: query optimization, indexing strategies, JSONB operations, partitioning, connection management. |
| Explorer        | `Explore`         | **No**    | All except Edit/Write                             | Find all SQLAlchemy queries across the codebase, map which endpoints trigger which queries.                                |

**Flow**: Explorer catalogs all queries → Postgres Expert analyzes each for missing indexes, N+1 patterns, suboptimal joins, unnecessary `SELECT *` → produces migration recommendations for new indexes.

---

### 10. Accessibility Audit

| Agent Name         | subagent_type        | Can Edit? | Tools                                    | Role on Team                                                                                                                      |
| ------------------ | -------------------- | --------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Frontend Developer | `frontend-developer` | Yes       | Write, Read, MultiEdit, Bash, Grep, Glob | Responsive design, component building, accessibility patterns. Fixes ARIA labels, keyboard nav, focus management.                 |
| Explorer           | `Explore`            | **No**    | All except Edit/Write                    | Scan all components for missing ARIA attributes, hardcoded colors without contrast ratios, missing `tabIndex`, non-semantic HTML. |

**Flow**: Explorer produces accessibility violation report → Frontend Developer fixes in priority order (critical: keyboard nav, screen reader → moderate: color contrast, focus indicators → low: semantic HTML improvements).

---

## Feature Development

### 11. Full-Stack Feature Build

| Agent Name    | subagent_type   | Can Edit? | Tools                               | Role on Team                                                                        |
| ------------- | --------------- | --------- | ----------------------------------- | ----------------------------------------------------------------------------------- |
| Coder         | `coder`         | Yes       | All tools                           | Implements backend endpoint + frontend component. General-purpose implementation.   |
| Test Engineer | `test-engineer` | Yes       | Read, Write, Edit, Bash, Grep, Glob | Writes unit, integration, and E2E tests for the new feature.                        |
| Reviewer      | `reviewer`      | Yes       | Read, Edit, Grep, Glob, Bash        | Code review: checks quality, patterns, security, edge cases. Suggests improvements. |

**Flow**: Coder implements backend → Coder implements frontend → Test Engineer writes tests in parallel with frontend work → Reviewer reviews all changes → team iterates on feedback.

---

### 12. API Endpoint Scaffold

| Agent Name        | subagent_type                           | Can Edit? | Tools                               | Role on Team                                                                                                   |
| ----------------- | --------------------------------------- | --------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools                           | Designs endpoint: route, request/response schemas, error handling, auth requirements. Implements the endpoint. |
| Test Engineer     | `test-engineer`                         | Yes       | Read, Write, Edit, Bash, Grep, Glob | Writes tests for the new endpoint (happy path, error cases, auth, validation).                                 |

**Flow**: Backend Architect designs + implements → Test Engineer writes comprehensive tests → both verify tests pass.

---

### 13. Component Library Extraction

| Agent Name   | subagent_type  | Can Edit? | Tools                                          | Role on Team                                                                                                   |
| ------------ | -------------- | --------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| React Expert | `react-expert` | Yes       | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Expert in React patterns, hooks, component design. Identifies repeated patterns and designs shared components. |
| Coder        | `coder`        | Yes       | All tools                                      | Handles the bulk refactoring: extract components, update all consumers, verify props.                          |

**Flow**: React Expert audits components for duplication → designs shared component APIs (props, variants) → Coder extracts and updates all consumers → React Expert reviews final component design.

---

### 14. E2E Test Suite Expansion

| Agent Name        | subagent_type       | Can Edit? | Tools                                          | Role on Team                                                                                  |
| ----------------- | ------------------- | --------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Playwright Expert | `playwright-expert` | Yes       | Bash, Read, Write, Edit, MultiEdit, Grep, Glob | Expert in Playwright: cross-browser automation, selectors, visual regression, CI integration. |
| Explorer          | `Explore`           | **No**    | All except Edit/Write                          | Map all user flows in the app, identify which have E2E coverage and which don't.              |

**Flow**: Explorer maps user flows → identifies uncovered flows → Playwright Expert writes specs prioritized by importance (auth flows, critical paths first) → runs them to verify they pass.

---

## Documentation & Knowledge

### 15. API Documentation Generation

| Agent Name  | subagent_type | Can Edit? | Tools                                         | Role on Team                                                                                                         |
| ----------- | ------------- | --------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Explorer    | `Explore`     | **No**    | All except Edit/Write                         | Crawl all endpoint files, extract routes, params, request/response types, auth requirements.                         |
| Docs Writer | `docs-writer` | Yes       | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Technical documentation specialist. Takes explorer's raw data and produces clean, structured API docs with examples. |

**Flow**: Explorer extracts all endpoint metadata → Docs Writer organizes into structured documentation with request/response examples, auth requirements, error codes.

---

### 16. Architecture Diagram Update

| Agent Name | subagent_type | Can Edit? | Tools                 | Role on Team                                                                                                             |
| ---------- | ------------- | --------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Explorer   | `Explore`     | **No**    | All except Edit/Write | Map module dependencies, data flow, service boundaries, database relationships.                                          |
| Researcher | `researcher`  | Yes       | All tools             | Synthesize explorer's findings into coherent architecture description. Can use WebSearch for diagramming best practices. |

**Flow**: Explorer traces imports, DB models, API routes, frontend route tree → Researcher synthesizes into architecture narrative with Mermaid diagrams.

---

### 17. Onboarding Guide

| Agent Name  | subagent_type | Can Edit? | Tools                                         | Role on Team                                                                                   |
| ----------- | ------------- | --------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Explorer    | `Explore`     | **No**    | All except Edit/Write                         | Catalog all env vars, setup scripts, config files, required services (Postgres, Redis, etc.).  |
| Docs Writer | `docs-writer` | Yes       | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Write clear step-by-step guide covering setup, common workflows, gotchas, and troubleshooting. |

**Flow**: Explorer inventories everything a new dev needs → Docs Writer produces a structured onboarding guide.

---

## DevOps & Infrastructure

### 18. CI Pipeline Review

| Agent Name          | subagent_type                                  | Can Edit? | Tools     | Role on Team                                                                  |
| ------------------- | ---------------------------------------------- | --------- | --------- | ----------------------------------------------------------------------------- |
| Deployment Engineer | `full-stack-orchestration:deployment-engineer` | Yes       | All tools | CI/CD expert: GitHub Actions, caching, parallel jobs, deployment automation.  |
| Researcher          | `researcher`                                   | Yes       | All tools | Research best practices, compare against current config, identify slow steps. |

**Flow**: Researcher benchmarks current CI times and identifies slow steps → Deployment Engineer optimizes caching, parallelism, job splitting → both verify pipeline still passes.

---

### 19. Docker Config Hardening

| Agent Name          | subagent_type                                  | Can Edit? | Tools                        | Role on Team                                                                                          |
| ------------------- | ---------------------------------------------- | --------- | ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| Security Auditor    | `security-auditor`                             | Yes       | Read, Edit, Bash, Grep, Glob | Check for secrets in images, excessive permissions, unnecessary packages, base image vulnerabilities. |
| Deployment Engineer | `full-stack-orchestration:deployment-engineer` | Yes       | All tools                    | Optimize multi-stage builds, minimize image size, add health checks, improve layer caching.           |

**Flow**: Security Auditor scans Dockerfiles + compose files for security issues → Deployment Engineer optimizes for size and performance → both verify containers build and run correctly.

---

### 20. Environment Config Audit

| Agent Name             | subagent_type            | Can Edit? | Tools                        | Role on Team                                                                                                              |
| ---------------------- | ------------------------ | --------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Config Safety Reviewer | `config-safety-reviewer` | Yes       | Read, Edit, Grep, Glob, Bash | Specializes in production reliability: magic numbers, pool sizes, timeouts, connection limits. Checks all config is safe. |
| Explorer               | `Explore`                | **No**    | All except Edit/Write        | Find every env var reference, every config file, every hardcoded value across the codebase.                               |

**Flow**: Explorer catalogs all config → Config Safety Reviewer checks: documented? has default? safe default? no secrets in code? consistent across environments?

---

## Refactoring & Tech Debt

### 21. Large File Decomposition

| Agent Name         | subagent_type        | Can Edit? | Tools                                   | Role on Team                                                                                                                             |
| ------------------ | -------------------- | --------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Refactoring Expert | `refactoring-expert` | Yes       | Read, Grep, Glob, Edit, MultiEdit, Bash | Systematic code refactoring, code smell detection. Identifies extraction points, applies refactoring patterns without changing behavior. |
| Tester             | `tester`             | Yes       | Read, Write, Edit, Bash, Grep, Glob     | Runs tests after each refactoring step to ensure behavior is preserved. Adds tests if coverage would drop.                               |

**Flow**: Refactoring Expert identifies files >500 lines → plans decomposition (which functions/classes move where) → extracts in small steps → Tester verifies tests pass after each step.

---

### 22. Error Handling Standardization

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                           |
| ---------- | ------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Coder      | `coder`       | Yes       | All tools                           | Implements standardized error types, updates handlers.                                                 |
| Explorer   | `Explore`     | **No**    | All except Edit/Write               | Catalog all current error patterns: bare `raise`, inconsistent HTTP status codes, missing error types. |
| Tester     | `tester`      | Yes       | Read, Write, Edit, Bash, Grep, Glob | Verifies error responses match new standard. Writes tests for error paths.                             |

**Flow**: Explorer audits current error patterns → team agrees on standard → Coder implements standard error classes + updates all handlers → Tester verifies.

---

### 23. State Management Cleanup

| Agent Name   | subagent_type  | Can Edit? | Tools                                          | Role on Team                                                                                                    |
| ------------ | -------------- | --------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| React Expert | `react-expert` | Yes       | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Expert in hooks, state management, re-rendering. Identifies redundant state, prop drilling, unnecessary stores. |
| Coder        | `coder`        | Yes       | All tools                                      | Applies the cleanup: removes redundant stores, simplifies data flow, updates consumers.                         |

**Flow**: React Expert audits all Zustand stores + component state → identifies redundancies and simplification opportunities → Coder applies changes → React Expert reviews.

---

### 24. Migration Consolidation

| Agent Name      | subagent_type     | Can Edit? | Tools                                | Role on Team                                                                                                   |
| --------------- | ----------------- | --------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Postgres Expert | `postgres-expert` | Yes       | Bash(psql, pg\_\*), Read, Grep, Edit | Reviews Alembic migration chain for squash opportunities, checks for conflicts, validates migration integrity. |
| Explorer        | `Explore`         | **No**    | All except Edit/Write                | Map the full migration chain, identify dependencies, find migrations that could be combined.                   |

**Flow**: Explorer maps migration history → Postgres Expert identifies squash candidates → produces recommendation (which to squash, risks, rollback plan).

---

## Ongoing / Recurring

### 25. Pre-PR Quality Gate

| Agent Name       | subagent_type      | Can Edit? | Tools                               | Role on Team                                                          |
| ---------------- | ------------------ | --------- | ----------------------------------- | --------------------------------------------------------------------- |
| Reviewer         | `reviewer`         | Yes       | Read, Edit, Grep, Glob, Bash        | Code quality review: patterns, readability, edge cases, consistency.  |
| Tester           | `tester`           | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full test suite, check coverage delta, verify no regressions.     |
| Security Auditor | `security-auditor` | Yes       | Read, Edit, Bash, Grep, Glob        | Check diff for security issues: injection, auth bypass, secrets, XSS. |

**Flow**: All three work in parallel on the current diff → each produces findings → team consolidates into a go/no-go recommendation.

---

### 26. Weekly Health Check

| Agent Name        | subagent_type       | Can Edit? | Tools                               | Role on Team                                                       |
| ----------------- | ------------------- | --------- | ----------------------------------- | ------------------------------------------------------------------ |
| Explorer          | `Explore`           | **No**    | All except Edit/Write               | Quick scan for new warnings, deprecations, type errors.            |
| Tester            | `tester`            | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full backend + frontend test suites, report results.           |
| Performance Tuner | `performance-tuner` | Yes       | Read, Edit, Bash, Grep, Glob        | Profile key endpoints, compare against baseline, flag regressions. |

**Flow**: All three run in parallel → produce a consolidated health report (test results, new warnings, performance changes).

---

### 27. Post-Merge Verification

| Agent Name           | subagent_type          | Can Edit? | Tools                               | Role on Team                                                                                                                      |
| -------------------- | ---------------------- | --------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Tester               | `tester`               | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full test suite on merged code.                                                                                               |
| Production Validator | `production-validator` | Yes       | All tools                           | Ensures application is fully implemented and deployment-ready. Checks build succeeds, no runtime errors, all features functional. |

**Flow**: Tester runs tests → Production Validator does build check + smoke test → both report results.

---

## Quick Reference: Agent Capabilities

| subagent_type                                  | Can Edit Files? | Can Run Bash? | Can Search Web? | Best For                               |
| ---------------------------------------------- | --------------- | ------------- | --------------- | -------------------------------------- |
| `Explore`                                      | No              | No            | No              | Fast codebase search, mapping, reading |
| `researcher`                                   | Yes             | Yes           | Yes             | Deep research, web lookups, analysis   |
| `coder`                                        | Yes             | Yes           | No              | General implementation                 |
| `tester`                                       | Yes             | Yes           | No              | Test writing + running                 |
| `test-engineer`                                | Yes             | Yes           | No              | Test creation + coverage analysis      |
| `reviewer`                                     | Yes             | Yes           | No              | Code review, quality checks            |
| `docs-writer`                                  | Yes             | Yes           | Yes             | Documentation writing                  |
| `security-auditor`                             | Yes             | Yes           | No              | Security scanning                      |
| `refactoring-expert`                           | Yes             | Yes           | No              | Safe refactoring                       |
| `performance-tuner`                            | Yes             | Yes           | No              | Profiling + optimization               |
| `typescript-expert`                            | Yes             | Yes           | No              | TS type system mastery                 |
| `react-expert`                                 | Yes             | Yes           | No              | React patterns + hooks                 |
| `postgres-expert`                              | Yes             | Yes (psql)    | No              | PostgreSQL optimization                |
| `playwright-expert`                            | Yes             | Yes           | No              | E2E test authoring                     |
| `linting-expert`                               | Yes             | Yes           | No              | Code style enforcement                 |
| `config-safety-reviewer`                       | Yes             | Yes           | No              | Config + production safety             |
| `frontend-developer`                           | Yes             | Yes           | No              | UI components + accessibility          |
| `production-validator`                         | Yes             | Yes           | No              | Deployment readiness                   |
| `backend-development:backend-architect`        | Yes             | Yes           | No              | API design + implementation            |
| `full-stack-orchestration:deployment-engineer` | Yes             | Yes           | No              | CI/CD + Docker + deploy                |

Given where your project is — just finished a major Deals overhaul, auth system is new, production deployment is next — here's my ranked
recommendation:

Top 5 to Start With (in order)

1. Security Audit (#6)

Why first: You just shipped an auth system (JWT, OAuth2, role guards). Auth is the #1 thing to get right before production. A security audit
now catches issues when they're cheap to fix — not after deployment. It also covers your extraction endpoints (file uploads, OneDrive paths),
which are high-risk attack surface.

2. API Contract Validation (#7)

Why second: You just added 24 new fields to DealResponse with matching Zod schemas. You have Pydantic on one side and Zod on the other, and
they were updated in the same session under time pressure. This is exactly when field name mismatches, missing nullable annotations, and type
mismatches sneak in. A contract validation team catches drift before users see undefined values in the UI.

3. Test Gap Analysis (#4)

Why third: You have 2177 tests, but you just rewrote large portions of test_deals.py and test_properties.py and added auth to every endpoint.
There are likely edge cases that got lost in the rewrite — error paths, permission boundaries (analyst vs admin vs viewer), and the new
enrichment fields. A gap analysis finds what's missing while the code is fresh.

4. Environment Config Audit (#20)

Why fourth: Production deployment is your next major milestone. You have .env, .env.prod.example, Docker configs, CORS origins, database URLs,
OneDrive paths, FRED API keys — a lot of config spread across many files. Before you docker compose up on a real server, you need to know
every env var is documented, has a safe default, and no secrets are hardcoded.

5. Pre-PR Quality Gate (#25)

Why fifth: Once the above four are done and fixes applied, run this as the final checkpoint before your deployment PR. It's the "measure
twice, cut once" step — reviewer + tester + security auditor all look at the full diff from main to confirm it's ready.

---

Why NOT the others yet

┌──────────────────────┬────────────────────────────────────────────────────────────────┐
│ Skipped │ Reason │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│ Performance (#8, #9) │ Premature — optimize after real users generate load patterns │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│ Dead code (#2) │ Nice-to-have but won't cause production bugs │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│ Type coverage (#3) │ You already have zero tsc errors; this is polish │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│ Docs (#15-17) │ Important but doesn't block deployment │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│ CI/Docker (#18-19) │ Your Docker config is already built; harden after first deploy │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│ Refactoring (#21-24) │ Tech debt can wait until post-launch │
└──────────────────────┴────────────────────────────────────────────────────────────────┘

---

Suggested Execution Order

Week 1: #6 Security Audit + #7 API Contract Validation (parallel)
Week 1: #4 Test Gap Analysis (can overlap with above)
Week 2: #20 Environment Config Audit (before deployment)
Week 2: #25 Pre-PR Quality Gate (final gate before deploy)

Want me to spin up the security audit and API contract validation teams right now? They can run in parallel

---
---

# Codebase-Wide Review, Testing & Error Resolution Runbook

A structured 4-phase pipeline that combines 10 of the 27 tasks above into a comprehensive codebase audit, fix, and verification cycle. This is designed to be run as a single coordinated effort — paste the prompt at the bottom into a Claude Code terminal to execute.

---

## Phase 1: Discovery (read-only, all parallel)

| # | Task | What It Finds |
|---|---|---|
| #7 | API Contract Validation | Pydantic ↔ Zod schema mismatches, missing fields, wrong types |
| #4 | Test Gap Analysis | Untested endpoints, uncovered branches, missing error path tests |
| #20 | Environment Config Audit | Undocumented env vars, hardcoded secrets, missing defaults |
| #2 | Dead Code Cleanup | Unused exports, orphaned files, stale imports |
| #3 | Type Coverage Sweep | `any` types, missing return types, untyped API responses |
| #5 | Lint & Style Enforcement | Lint violations, inconsistent formatting, config gaps |
| #22 | Error Handling Standardization | Inconsistent error patterns, bare raises, wrong HTTP status codes |

**Why all at once**: These are all primarily read/audit tasks. Running them in parallel gives a complete picture of every issue before anyone starts fixing anything.

---

## Phase 2: Fix (sequential by risk, each with testing)

| # | Task | What It Fixes | Why This Order |
|---|---|---|---|
| #7 | API Contract Validation | Schema mismatches → runtime bugs | Highest user-facing impact |
| #22 | Error Handling Standardization | Inconsistent errors → confusing API responses | Affects all endpoints |
| #3 | Type Coverage Sweep | Type gaps → potential runtime crashes | Catches bugs statically |
| #2 | Dead Code Cleanup | Cruft removal → smaller codebase | Reduces noise for remaining work |
| #5 | Lint & Style Enforcement | Style violations → clean baseline | Cosmetic, do last |
| #20 | Environment Config Audit | Config gaps → document & add defaults | Config, not code |

Each fix phase runs with a **Tester agent** that verifies all existing tests still pass after changes.

---

## Phase 3: Fill Gaps

| # | Task | What It Adds |
|---|---|---|
| #4 | Test Gap Analysis | Writes missing tests for everything found in Phase 1 |
| #21 | Large File Decomposition | Splits any files that grew too large during fixes |

---

## Phase 4: Final Gate

| # | Task | What It Checks |
|---|---|---|
| #25 | Pre-PR Quality Gate | Reviewer + Tester + Security Auditor validate the full diff |
| #27 | Post-Merge Verification | Production Validator confirms build + smoke tests pass |

---

## Full Agent Roster (12 unique agent types across all phases)

| Agent | subagent_type | Phases | Role |
|---|---|---|---|
| Explorer | `Explore` | 1, 2, 3 | Read-only scanning, mapping, cataloging across the entire codebase |
| Backend Architect | `backend-development:backend-architect` | 1, 2 | Pydantic schema analysis, API contract comparison, endpoint review |
| TS Expert | `typescript-expert` | 1, 2 | Find and fix type gaps, `any` usage, missing return types |
| Config Safety Reviewer | `config-safety-reviewer` | 1 | Env var audit, config safety, production readiness |
| Linting Expert | `linting-expert` | 1, 2 | Lint violations, style enforcement, config updates |
| Coder | `coder` | 2, 3 | Bulk fixes: dead code removal, error handling, schema updates |
| Refactoring Expert | `refactoring-expert` | 3 | Large file decomposition, safe structural changes |
| Test Engineer | `test-engineer` | 3 | Write missing tests for gaps identified in Phase 1 |
| Tester | `tester` | 2, 3, 4 | Run test suite after every change, verify no regressions |
| Reviewer | `reviewer` | 4 | Final code quality review of all changes |
| Security Auditor | `security-auditor` | 4 | Final security check on the full diff |
| Production Validator | `production-validator` | 4 | Build verification, deployment readiness |

---

## Tasks Excluded From This Pipeline (and why)

| Category | Tasks | Reason |
|---|---|---|
| Feature Development | #11-14 | Building new features, not auditing existing code |
| Documentation | #15-17 | Important but doesn't fix bugs or catch errors |
| Infrastructure | #18-19 | CI/CD and Docker hardening — separate focused effort |
| Specialized Audits | #6, #8-10, #23-24 | Security, performance, accessibility, state management, migrations — each deserves its own dedicated run |
| Recurring | #26 | Weekly health check — run on a schedule, not as part of a one-time audit |

---

## Optimal Prompt for Execution

Copy and paste the following prompt into a Claude Code terminal to execute the full pipeline. Adjust the project-specific details in the `PROJECT CONTEXT` section to match your codebase.

### Tips for Maximum Effectiveness

1. **Run on a clean branch**: Commit or stash all changes first. The audit should run against a stable baseline.
2. **No other terminals editing**: Make sure no other Claude Code sessions or editors are modifying files during the run.
3. **Give permission upfront**: When prompted, approve bash commands (test runs, linting, type checking) to avoid blocking the pipeline.
4. **Worktree isolation for Phase 1**: Phase 1 is read-only, so it can safely run in a worktree if you need to keep working on main.
5. **Review Phase 1 report before Phase 2**: The discovery report will list all findings. Review it to confirm priorities before the fix phase begins.
6. **Don't rush Phase 2**: Each fix step should be followed by a full test run. Skipping verification creates cascading failures.

---

### The Prompt

```
I need you to run a comprehensive codebase-wide review, testing, and error resolution pipeline on this project. Follow all 4 phases below exactly. Use Claude Code's built-in TeamCreate and Task tools to create agent teams. Communicate progress at every phase boundary.

## PROJECT CONTEXT
- Backend: FastAPI + SQLAlchemy async + Alembic (Python, in `backend/`)
- Frontend: React + TypeScript + Vite (in `src/`)
- Backend schemas: Pydantic models in `backend/app/schemas/`
- Frontend schemas: Zod schemas in `src/lib/api/schemas/`
- Tests: Backend uses pytest (`backend/tests/`), Frontend uses vitest (`src/`)
- Config: `.env` in project root, `.env.prod.example`, Docker configs
- Auth: JWT with role-based guards (require_analyst, require_manager)
- Test commands: `npm run test` (frontend), `conda run -n dashboard-backend pytest backend/tests/` (backend)
- Build command: `npm run build`
- Lint commands: `npm run lint` (frontend), `ruff check backend/` (backend)
- Type check: `npx tsc --noEmit`

## PHASE 1: DISCOVERY (read-only, all parallel)

Create a team called "codebase-audit". Create tasks for all 7 discovery workstreams below, then spawn agents to work them IN PARALLEL. No file edits in this phase — audit only.

1. **API Contract Validation**: Spawn a `backend-development:backend-architect` agent. It must:
   - Read every Pydantic response model in `backend/app/schemas/`
   - Read every Zod schema in `src/lib/api/schemas/`
   - Compare field-by-field: name, type, nullable/optional, default values
   - List every mismatch (field name differs, type differs, nullable on one side but not other, field exists in Pydantic but missing from Zod or vice versa)
   - Report findings as a structured list

2. **Test Gap Analysis**: Spawn an `Explore` agent. It must:
   - Map every backend endpoint (route + method + auth requirement)
   - Map every frontend component and hook
   - Cross-reference against existing test files
   - Identify: endpoints with no tests, endpoints with no error-path tests, components with no tests, hooks with no tests
   - Report the gap list with priority (critical: auth endpoints untested, high: CRUD endpoints, medium: UI components)

3. **Environment Config Audit**: Spawn an `Explore` agent. It must:
   - Find every env var reference across the entire codebase (grep for `os.environ`, `os.getenv`, `process.env`, `settings.`, `config.`)
   - Check each against `.env.example` and `.env.prod.example`
   - Flag: undocumented vars, vars with no default, hardcoded secrets, vars referenced but never defined in examples
   - Report findings

4. **Dead Code Scan**: Spawn an `Explore` agent. It must:
   - Find exported functions/classes/components that are never imported elsewhere
   - Find files that are never imported by any other file
   - Find unused imports within files
   - Report the dead code candidates list

5. **Type Coverage Scan**: Spawn an `Explore` agent. It must:
   - Find all `any` type annotations in TypeScript files
   - Find functions with no return type annotation
   - Find API response types that are `unknown` or `any`
   - Report findings with file:line references

6. **Lint Audit**: Spawn an `Explore` agent. It must:
   - Run `npm run lint -- --format json` and `ruff check backend/ --output-format json` (read output only)
   - Catalog all violations by rule, severity, and file
   - Report summary + full violation list

7. **Error Handling Audit**: Spawn an `Explore` agent. It must:
   - Find all `raise` statements in backend code — catalog what exception types are used
   - Find all HTTP status codes returned by endpoints — check for consistency
   - Find all try/except blocks — check for bare `except:` or overly broad `except Exception`
   - Find frontend error handling patterns — how API errors are caught and displayed
   - Report inconsistencies

After ALL 7 agents complete, consolidate their findings into a single summary report. Present it to me and WAIT for my approval before proceeding to Phase 2.

## PHASE 2: FIX (sequential, tested after each step)

After I approve the Phase 1 report, fix issues in this order. For each fix step:
- Spawn the appropriate agent to make fixes
- After fixes, spawn a `tester` agent to run the FULL test suite (both backend and frontend)
- Only proceed to the next step if all tests pass
- If tests fail, fix the failures before moving on

Fix order:
1. **API Contract Fixes** (`coder`): Fix all Pydantic ↔ Zod mismatches found in Phase 1
2. **Error Handling Fixes** (`coder`): Standardize error patterns across backend endpoints
3. **Type Coverage Fixes** (`typescript-expert`): Fix all `any` types and missing return types
4. **Dead Code Removal** (`coder`): Remove confirmed dead code (only items with zero references)
5. **Lint Fixes** (`linting-expert`): Auto-fix all lint violations, manually fix what can't be auto-fixed
6. **Config Fixes** (`coder`): Add missing env var documentation, add safe defaults

Report progress after each fix step. If any fix step causes test failures that can't be resolved, skip it and report it as blocked.

## PHASE 3: FILL GAPS

After Phase 2 is complete:
1. Spawn a `test-engineer` agent to write tests for all gaps identified in Phase 1 step 2. Focus on:
   - Auth boundary tests (analyst vs admin vs viewer vs unauthenticated)
   - Error path tests (400, 401, 403, 404, 422 responses)
   - Edge cases for new fields (null values, empty strings, boundary values)
2. Spawn a `refactoring-expert` agent to check if any files now exceed 500 lines and need decomposition.
3. Run the full test suite one final time to confirm everything passes.

Report the test count before and after (should increase).

## PHASE 4: FINAL GATE

After Phase 3:
1. Spawn a `reviewer` agent to review ALL changes made in Phases 2-3 for code quality
2. Spawn a `security-auditor` agent to check ALL changes for security issues
3. Spawn a `production-validator` agent to verify: `npm run build` succeeds, `npx tsc --noEmit` passes, full test suite passes
4. Consolidate all three reports into a final go/no-go recommendation

Present the final report to me. Do NOT commit or push — I will decide what to do with the changes.

## COMMUNICATION RULES
- Report progress at every phase boundary
- If any agent encounters an error it can't resolve, report it immediately — don't silently skip
- After Phase 1, WAIT for my approval before starting Phase 2
- After Phase 4, present the final summary and STOP
```

---

### Prompt Customization Notes

Before running, update these sections to match your project:

| Section | What to Change | This Project's Value |
|---|---|---|
| `Backend: FastAPI + SQLAlchemy...` | Your actual backend framework and structure | `FastAPI + SQLAlchemy async + Alembic (Python, in backend/)` |
| `Frontend: React + TypeScript...` | Your actual frontend framework and structure | `React + TypeScript + Vite (in src/)` |
| `Backend schemas: Pydantic models in...` | Path to your backend response models | `backend/app/schemas/` (deal.py, comparison.py, property.py, etc.) |
| `Frontend schemas: Zod schemas in...` | Path to your frontend validation schemas | `src/lib/api/schemas/` (deal.ts, property.ts, etc.) |
| `Test commands:` | Your actual test runner commands | Frontend: `npm run test` — Backend: `conda run -n dashboard-backend pytest backend/tests/` |
| `Build command:` | Your actual build command | `npm run build` (runs tsc + vite) |
| `Lint commands:` | Your actual linting commands | Frontend: `npm run lint` — Backend: `ruff check backend/` |
| `Type check:` | Your actual type check command | `npx tsc --noEmit` |
| `Auth: JWT with role-based guards...` | Your actual auth pattern (or remove if no auth) | JWT via `src/stores/authStore.ts`, backend guards: `require_analyst` (GET), `require_manager` (mutations) |
| `Config:` | Your env/config file locations | `.env` in project root, `.env.prod.example`, Docker configs in `docker/` |
| `Dev server:` | Your local dev command | `npm run dev:all` (runs backend + frontend concurrently) |

### Expected Duration

| Phase | Agents | Estimated Time |
|---|---|---|
| Phase 1: Discovery | 7 parallel | 5-10 minutes |
| Review break | You | As long as you need |
| Phase 2: Fix | 6 sequential | 15-30 minutes |
| Phase 3: Fill Gaps | 2-3 agents | 10-20 minutes |
| Phase 4: Final Gate | 3 parallel | 5-10 minutes |
| **Total** | | **~35-70 minutes + your review time** |

### What Success Looks Like

After a successful run, you should have:
- Zero Pydantic ↔ Zod schema mismatches
- Consistent error handling across all endpoints
- Zero `any` types in TypeScript (or documented exceptions)
- No dead code or unused imports
- Zero lint violations
- All env vars documented with safe defaults
- Increased test count covering previously untested paths
- All tests passing
- Build succeeding
- A go/no-go report from the reviewer, security auditor, and production validator

---
---

# Cap Rate TC T3 Extraction Re-Run — Agent Teams & Execution Guide

A dedicated set of agent teams designed to safely execute, verify, and validate the Cap Rate TC T3 extraction pipeline re-run. These teams cover the full lifecycle: pre-flight checks → code audit → execution → data verification → frontend display validation → regression test hardening.

**Task Summary**: Execute `POST /api/v1/extraction/start` with `{"source": "local"}` to re-run the local OneDrive extraction pipeline, then comprehensively verify that Cap Rate, TC T3 returns data (IRR, MOIC, Return on Cost), and all supplemental fields are correctly parsed from UW model Excel files and stored in the database.

**Why This Needs Dedicated Teams**: The extraction pipeline touches 7+ subsystems (API endpoint → background task → file discovery → Excel parsing → change detection → database sync → property/deal creation). A failure at any stage silently corrupts downstream data. Each team below isolates one concern so nothing is missed.

---

## Extraction Pipeline Teams

### 28. Extraction Pre-Flight Check

| Agent Name             | subagent_type            | Can Edit? | Tools                        | Role on Team                                                                                                                                                              |
| ---------------------- | ------------------------ | --------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Explorer               | `Explore`                | **No**    | All except Edit/Write        | Scan for `LOCAL_DEALS_ROOT` env var, verify OneDrive folder structure exists and contains `.xlsb`/`.xlsx` files. Map deal stage folders. Count files per stage.            |
| Config Safety Reviewer | `config-safety-reviewer` | Yes       | Read, Edit, Grep, Glob, Bash | Validate all extraction-related env vars are set and safe: `LOCAL_DEALS_ROOT`, `MAX_WORKERS`, `EXTRACTION_TIMEOUT`. Check `.env` and `.env.prod.example` for completeness. |

**Flow**: Explorer checks the filesystem and codebase config references → Config Safety Reviewer validates all env vars are present, documented, and have safe defaults → team produces a go/no-go for extraction readiness.

**Pre-Conditions**: Access to the local OneDrive path. Backend virtualenv activated.

**Output**: Pre-flight report listing: files discovered per stage, env var status, any missing config.

---

### 29. Extraction Pipeline Code Audit

| Agent Name        | subagent_type                           | Can Edit? | Tools              | Role on Team                                                                                                                                                                             |
| ----------------- | --------------------------------------- | --------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools          | Review `extract.py`, `common.py`, `extractor.py` for logic errors, race conditions, incorrect indexing. Verify the background task properly handles all error paths and edge cases.       |
| Researcher        | `researcher`                            | Yes       | All tools          | Cross-reference supplemental cell mappings (T3_RETURN_ON_COST at G27, IRR at E39/E43, MOIC at E40/E44) against actual UW model sheet structure. Verify pyxlsb 0-based indexing is correct. |

**Flow**: Backend Architect reviews extraction code for correctness (especially `run_extraction_task()` in `common.py` — 756 lines) → Researcher validates cell references against known UW model layouts → both report issues that could cause silent data corruption.

**Key Files**:
- `backend/app/api/v1/endpoints/extraction/extract.py` — API endpoint
- `backend/app/api/v1/endpoints/extraction/common.py` — Background task orchestration (756 lines)
- `backend/app/extraction/extractor.py` — Excel parsing engine (632 lines)
- `backend/app/extraction/sharepoint.py` — SharePoint integration (705 lines)

**Output**: Code audit report with any bugs, incorrect cell references, or logic issues that must be fixed before running extraction.

---

### 30. Cell Mapping & Reference File Validation

| Agent Name | subagent_type | Can Edit? | Tools                 | Role on Team                                                                                                                                                                           |
| ---------- | ------------- | --------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Explorer   | `Explore`     | **No**    | All except Edit/Write | Find every cell mapping definition across the codebase: reference CSV/JSON files, hardcoded supplemental mappings in `common.py`, and any test fixture mappings. Catalog all of them.    |
| Researcher | `researcher`  | Yes       | All tools             | For each mapping, verify: sheet name exists in typical UW models, cell address is plausible for the data type, category label is correct. Flag any mappings that reference nonexistent sheets. |

**Flow**: Explorer catalogs every cell mapping source (reference files, supplemental dicts, test fixtures) → Researcher validates each mapping's sheet/cell/type is correct → team produces a validated mapping table.

**Critical Supplemental Mappings to Verify**:
| Field Name               | Sheet                    | Cell | Expected Data Type |
| ------------------------ | ------------------------ | ---- | ------------------ |
| T3_RETURN_ON_COST        | Assumptions Summary      | G27  | numeric (%)        |
| UNLEVERED_RETURNS_IRR    | Returns Metrics Summary  | E39  | numeric (%)        |
| UNLEVERED_RETURNS_MOIC   | Returns Metrics Summary  | E40  | numeric (x)        |
| LEVERED_RETURNS_IRR      | Returns Metrics Summary  | E43  | numeric (%)        |
| LEVERED_RETURNS_MOIC     | Returns Metrics Summary  | E44  | numeric (x)        |

**Output**: Validated mapping table with pass/fail per field. Any "fail" items must be fixed before extraction.

---

### 31. Database State Snapshot (Pre-Extraction Baseline)

| Agent Name | subagent_type | Can Edit? | Tools              | Role on Team                                                                                                                                                                    |
| ---------- | ------------- | --------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coder      | `coder`       | Yes       | All tools          | Query the database for current state: count of ExtractionRun records, count of ExtractedValue records, count of Property/Deal records. Snapshot existing cap rate and returns values. |
| Explorer   | `Explore`     | **No**    | All except Edit/Write | Map the CRUD functions used for querying extraction data. Identify the exact queries needed to capture baseline metrics.                                                          |

**Flow**: Explorer identifies the right CRUD methods and query patterns → Coder executes queries to capture baseline counts and sample values → team produces a baseline snapshot for comparison after extraction.

**Baseline Metrics to Capture**:
- Total `ExtractionRun` records and latest run status
- Total `ExtractedValue` records (overall + per property)
- Count of properties with cap rate fields populated
- Count of properties with TC T3 returns fields populated
- Sample of 3-5 known property values for spot-checking after extraction

**Output**: Baseline snapshot document with counts and sample values.

---

### 32. Extraction Execution & Monitoring

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                                                                                                       |
| ---------- | ------------- | --------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coder      | `coder`       | Yes       | All tools                           | Start the backend server if needed. Execute `POST /api/v1/extraction/start {"source": "local"}`. Poll `GET /api/v1/extraction/status/{run_id}` until completion. Log all responses. |
| Tester     | `tester`      | Yes       | Read, Write, Edit, Bash, Grep, Glob | Monitor backend logs during extraction for errors/warnings. After completion, verify the ExtractionRun record has correct stats (files_discovered, files_processed, success_rate).  |

**Flow**: Coder starts extraction → polls status endpoint every 10-15 seconds → Tester watches logs for errors → both verify final status is "completed" (not "failed") → team reports extraction summary.

**Expected Success Criteria**:
- ExtractionRun status = `"completed"`
- `files_failed` = 0 (or acceptably low)
- `success_rate` ≥ 95%
- No unhandled exceptions in backend logs

**Output**: Extraction run report with: run_id, duration, files processed, files failed, success rate, any errors.

---

### 33. Post-Extraction Data Integrity Validation

| Agent Name        | subagent_type                           | Can Edit? | Tools              | Role on Team                                                                                                                                                            |
| ----------------- | --------------------------------------- | --------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools          | Query ExtractedValue table for the new run_id. Verify: correct property count, correct field count per property, no orphaned records, all property_ids are backfilled.    |
| Tester            | `tester`                                | Yes       | Read, Write, Edit, Bash, Grep, Glob | Compare post-extraction counts against pre-extraction baseline. Verify net-new properties were created. Spot-check 3-5 known property values against expected values. |

**Flow**: Backend Architect runs data integrity queries (null checks, orphan checks, count validations) → Tester compares against Team 31 baseline → both verify no data corruption occurred.

**Integrity Checks**:
1. Every `ExtractedValue` record has a non-null `property_name`
2. Every `ExtractedValue` with `is_error=False` has at least one non-null value column
3. All properties have a corresponding `Property` record (property_id backfilled)
4. All properties have a corresponding `Deal` record with correct stage
5. No duplicate `(extraction_run_id, property_name, field_name)` tuples
6. `files_processed` in ExtractionRun matches actual distinct `source_file` values in ExtractedValue

**Output**: Data integrity report with pass/fail per check.

---

### 34. Cap Rate & Returns Field Verification

| Agent Name        | subagent_type                           | Can Edit? | Tools     | Role on Team                                                                                                                                                                                        |
| ----------------- | --------------------------------------- | --------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools | Query the specific cap rate and TC T3 returns fields from ExtractedValue. Verify values are numeric, in expected ranges (IRR: -50% to +100%, MOIC: 0x to 10x, Cap Rate: 0% to 20%). Flag outliers. |
| Researcher        | `researcher`                            | Yes       | All tools | Cross-reference a sample of extracted values against manually-read values from the source Excel files. Confirm the extraction engine is reading the correct cells.                                    |

**Flow**: Backend Architect queries all cap rate and returns fields → validates value ranges → Researcher manually spot-checks 2-3 files against extracted values → team confirms extraction accuracy.

**Fields to Verify**:
| Field Name               | Expected Range      | Value Column          |
| ------------------------ | ------------------- | --------------------- |
| CAP_RATE                 | 0.0 – 0.20 (0-20%) | `value_numeric`       |
| T3_RETURN_ON_COST        | 0.0 – 0.50 (0-50%) | `value_numeric`       |
| UNLEVERED_RETURNS_IRR    | -0.50 – 1.00        | `value_numeric`       |
| UNLEVERED_RETURNS_MOIC   | 0.0 – 10.0          | `value_numeric`       |
| LEVERED_RETURNS_IRR      | -0.50 – 1.00        | `value_numeric`       |
| LEVERED_RETURNS_MOIC     | 0.0 – 10.0          | `value_numeric`       |

**Output**: Field verification report with value distributions, outlier flags, and spot-check confirmation.

---

### 35. Property & Deal Record Sync Verification

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                                                                                                   |
| ---------- | ------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Coder      | `coder`       | Yes       | All tools                           | Query Property and Deal tables to verify sync: every extracted property has a Property record, every Property has a Deal record, deal stages match source folder structure.      |
| Tester     | `tester`      | Yes       | Read, Write, Edit, Bash, Grep, Glob | Verify the API endpoints that serve property/deal data return the newly extracted data. Test `GET /api/v1/deals/`, `GET /api/v1/properties/` to confirm frontend-visible data. |

**Flow**: Coder verifies DB-level sync (Property ↔ Deal ↔ ExtractedValue relationships) → Tester verifies API-level responses include the new data → team confirms the full pipeline from Excel to API is working.

**Sync Checks**:
1. Every property in ExtractedValue has a matching Property record
2. Every Property has a Deal with correct `stage` (initial_review, active_review, under_contract, closed)
3. Deal financial fields (cap_rate, irr, moic) are populated from ExtractedValue
4. API responses include the new properties with correct values

**Output**: Sync verification report with pass/fail per check.

---

### 36. Frontend Display & Rendering Validation

| Agent Name         | subagent_type        | Can Edit? | Tools                                          | Role on Team                                                                                                                                                                               |
| ------------------ | -------------------- | --------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Frontend Developer | `frontend-developer` | Yes       | Write, Read, MultiEdit, Bash, Grep, Glob       | Verify that frontend components correctly display extracted cap rate and returns data. Check KPICard rendering, deal detail pages, kanban card fields, and any comparison views.             |
| React Expert       | `react-expert`       | Yes       | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Audit data binding: verify Zod schemas parse the API response correctly, check for `?? 0` bugs (should be `?? undefined` for "N/A" display), confirm trend calculations handle null values. |

**Flow**: Frontend Developer traces data from API response → Zustand store → component props → rendered output for cap rate and returns fields → React Expert checks for known rendering bugs (KPICard trend guard, Zod nullable handling) → team confirms correct display.

**Known Bug Patterns to Check**:
- `?? 0` instead of `?? undefined` causes "0.0%" instead of "N/A" for missing values
- `trend && trend > 0` is falsy for `trend === 0` — must use `!== undefined && !== 0`
- shadcn CSS vars must be in `:root` or components render transparent

**Output**: Frontend rendering report confirming correct display or listing display bugs.

---

### 37. Extraction Regression Test Suite

| Agent Name    | subagent_type   | Can Edit? | Tools                               | Role on Team                                                                                                                                                                                    |
| ------------- | --------------- | --------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Test Engineer | `test-engineer` | Yes       | Read, Write, Edit, Bash, Grep, Glob | Write comprehensive tests for: extraction endpoint (start/cancel/status), Excel parsing (xlsb/xlsx with known cell values), database sync (property/deal creation), and supplemental field extraction. |
| Tester        | `tester`        | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run the full backend + frontend test suite after new tests are added. Verify no regressions. Report final test count delta.                                                                      |

**Flow**: Test Engineer writes tests covering all extraction pipeline stages using test fixtures → Tester runs full suite → both confirm all tests pass and coverage increased.

**Test Categories to Write**:
1. **API endpoint tests**: Start extraction (happy path, already running → 409, missing config → 400)
2. **Excel extractor tests**: Known .xlsx fixture → verify specific cell values extracted correctly
3. **Cell mapping tests**: Supplemental fields (G27, E39, E40, E43, E44) → verify correct values
4. **Database sync tests**: Extracted data → Property/Deal records created with correct relationships
5. **Change detection tests**: Re-extraction of same file → verify dedup (upsert, not duplicate)
6. **Error handling tests**: Corrupt file → verify graceful failure with error categorization

**Output**: Test count before and after. All tests passing.

---

### 38. Post-Run Full Verification Gate

| Agent Name           | subagent_type          | Can Edit? | Tools                               | Role on Team                                                                                                                                                  |
| -------------------- | ---------------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reviewer             | `reviewer`             | Yes       | Read, Edit, Grep, Glob, Bash        | Review all code changes made during the extraction task (bug fixes, new tests, any config updates). Check quality, patterns, edge cases.                       |
| Tester               | `tester`               | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full backend + frontend test suite one final time. Report total test count and pass rate.                                                                  |
| Production Validator | `production-validator` | Yes       | All tools                           | Verify `npm run build` succeeds, `npx tsc --noEmit` passes, backend starts cleanly, extraction endpoint responds to health checks. Confirm deployment-ready. |

**Flow**: All three work in parallel → Reviewer checks code quality → Tester verifies all tests pass → Production Validator confirms build + startup → team produces final go/no-go report.

**Output**: Final verification report with go/no-go recommendation.

---

## Quick Reference: Extraction Teams

| # | Team Name | Agents | Phase | Parallel? | Purpose |
|---|---|---|---|---|---|
| 28 | Pre-Flight Check | Explorer, Config Safety Reviewer | Pre-Run | Yes | Verify env vars, file paths, config |
| 29 | Pipeline Code Audit | Backend Architect, Researcher | Pre-Run | Yes | Review code for bugs before running |
| 30 | Cell Mapping Validation | Explorer, Researcher | Pre-Run | Yes | Verify Excel cell references are correct |
| 31 | Database Baseline Snapshot | Coder, Explorer | Pre-Run | Yes | Capture pre-extraction metrics |
| 32 | Extraction Execution | Coder, Tester | Execute | Sequential | Run extraction, monitor progress |
| 33 | Data Integrity Validation | Backend Architect, Tester | Post-Run | Yes | Verify data completeness and correctness |
| 34 | Cap Rate & Returns Verify | Backend Architect, Researcher | Post-Run | Yes | Validate specific financial fields |
| 35 | Property/Deal Sync Verify | Coder, Tester | Post-Run | Yes | Verify Property ↔ Deal ↔ ExtractedValue sync |
| 36 | Frontend Display Validation | Frontend Developer, React Expert | Post-Run | Yes | Verify UI renders data correctly |
| 37 | Regression Test Suite | Test Engineer, Tester | Hardening | Sequential | Write new tests, run full suite |
| 38 | Final Verification Gate | Reviewer, Tester, Production Validator | Final | Yes | Go/no-go quality gate |

---

## Execution Plan: Step-by-Step Instructions

### Overview

The teams are organized into **5 phases**. Within each phase, teams that can run in parallel should be launched together in a single message. Phases are sequential — each phase depends on the previous phase's output.

```
PHASE A: PRE-RUN VALIDATION (Teams 28-31)     ← Can I safely run extraction?
    ↓
PHASE B: EXECUTION (Team 32)                   ← Run it
    ↓
PHASE C: POST-RUN VERIFICATION (Teams 33-36)   ← Did it work correctly?
    ↓
PHASE D: HARDENING (Team 37)                   ← Prevent future regressions
    ↓
PHASE E: FINAL GATE (Team 38)                  ← Is everything clean?
```

---

### Phase A: Pre-Run Validation (Teams 28, 29, 30, 31 — ALL PARALLEL)

**What**: Verify everything is ready before running extraction. All 4 teams run simultaneously because they are read-only and independent.

**Launch Command** (single message with 4 Task calls):

```
Task("Pre-Flight Check", "Team 28: Check LOCAL_DEALS_ROOT env var is set and points to a valid directory with .xlsb/.xlsx files. Verify all extraction-related env vars exist in .env. Count files per deal stage folder (0-Dead, 1-Initial, 2-Active, 3-Under Contract, 4-Closed). Report file counts and config status.", "Explore")

Task("Pipeline Code Audit", "Team 29: Review backend/app/api/v1/endpoints/extraction/common.py and backend/app/extraction/extractor.py for logic errors. Specifically verify: (1) pyxlsb 0-based indexing conversion is correct, (2) supplemental cell mappings in common.py match expected sheet/cell locations, (3) background task error handling covers all failure modes, (4) change detection (SHA-256 hashing) works correctly. Report any bugs found.", "backend-development:backend-architect")

Task("Cell Mapping Validation", "Team 30: Find ALL cell mapping definitions in the codebase (reference files, supplemental dicts in common.py, test fixtures). For each mapping verify sheet name and cell address are plausible. Pay special attention to: T3_RETURN_ON_COST (Assumptions Summary!G27), UNLEVERED_RETURNS_IRR (Returns Metrics Summary!E39), UNLEVERED_RETURNS_MOIC (E40), LEVERED_RETURNS_IRR (E43), LEVERED_RETURNS_MOIC (E44). Report a validated mapping table.", "researcher")

Task("Database Baseline Snapshot", "Team 31: Query the database for current extraction state. Capture: total ExtractionRun records, latest run status, total ExtractedValue records, count of properties with cap rate fields, count of properties with returns fields (IRR/MOIC). Save 3-5 sample property values for post-extraction spot-checking. Use the CRUD methods in backend/app/crud/extraction.py.", "coder")
```

**Decision Point**: Review all 4 reports. If any team finds a blocking issue (missing config, code bug, wrong cell reference), fix it before proceeding to Phase B.

**Expected Duration**: 3-8 minutes (all parallel).

---

### Phase B: Execution (Team 32 — SEQUENTIAL, requires Phase A clean)

**What**: Execute the extraction pipeline and monitor it to completion.

**Pre-Condition**: All Phase A teams reported clean (no blocking issues).

**Launch Command**:

```
Task("Run Extraction", "Team 32: (1) Ensure the backend server is running (or start it with `conda run -n dashboard-backend uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`). (2) Execute: curl -X POST http://localhost:8000/api/v1/extraction/start -H 'Content-Type: application/json' -H 'Authorization: Bearer <token>' -d '{\"source\": \"local\"}'. (3) Capture the run_id from the response. (4) Poll GET /api/v1/extraction/status/{run_id} every 15 seconds until status is 'completed' or 'failed'. (5) Monitor backend logs for errors. (6) Report final status, files_discovered, files_processed, files_failed, success_rate, and duration.", "coder")
```

**Auth Note**: The extraction endpoint requires `require_manager` role. Use the admin user (`matt@bandrcapital.com` / `Wildcats777!!`) to obtain a JWT token first via `POST /api/v1/auth/login`.

**Decision Point**: If extraction fails or success_rate < 95%, investigate errors before proceeding. The `error_summary` and `per_file_status` fields in the ExtractionRun record contain diagnostic details.

**Expected Duration**: 2-15 minutes depending on file count.

---

### Phase C: Post-Run Verification (Teams 33, 34, 35, 36 — ALL PARALLEL)

**What**: Comprehensively verify the extraction produced correct, complete data. All 4 teams run simultaneously because they check independent aspects.

**Pre-Condition**: Team 32 reported extraction completed successfully.

**Launch Command** (single message with 4 Task calls):

```
Task("Data Integrity Check", "Team 33: Query ExtractedValue table for the latest extraction run_id. Verify: (1) every record has non-null property_name, (2) non-error records have at least one non-null value column, (3) all property_ids are backfilled (not null), (4) no duplicate (run_id, property_name, field_name) tuples, (5) files_processed matches distinct source_file count. Compare total counts against the baseline from Phase A.", "backend-development:backend-architect")

Task("Cap Rate & Returns Verify", "Team 34: Query ExtractedValue for these specific fields: CAP_RATE, T3_RETURN_ON_COST, UNLEVERED_RETURNS_IRR, UNLEVERED_RETURNS_MOIC, LEVERED_RETURNS_IRR, LEVERED_RETURNS_MOIC. For each: (1) count how many properties have this field, (2) check value_numeric is in expected range (IRR: -0.5 to 1.0, MOIC: 0 to 10, cap rates: 0 to 0.20), (3) flag any null/error values, (4) spot-check 2-3 values against source Excel files if accessible.", "researcher")

Task("Property Deal Sync Check", "Team 35: Verify database sync: (1) every property_name in ExtractedValue has a matching Property record, (2) every Property has a Deal with correct stage, (3) Deal financial fields are populated from extracted values, (4) test API endpoints GET /api/v1/deals/ and GET /api/v1/properties/ return the newly extracted data with correct values.", "coder")

Task("Frontend Display Check", "Team 36: Review frontend components that display cap rate and returns data. Check: (1) Zod schemas in src/lib/api/schemas/ parse the fields correctly (nullable handling), (2) KPICard components handle null/zero values (no '0.0%' for missing data), (3) Deal detail pages show returns fields, (4) Kanban cards display relevant financial metrics. Report any rendering bugs.", "frontend-developer")
```

**Decision Point**: Review all 4 reports. If data integrity issues are found (Team 33), determine if re-extraction is needed. If display bugs are found (Team 36), create fix tasks.

**Expected Duration**: 5-10 minutes (all parallel).

---

### Phase D: Hardening (Team 37 — SEQUENTIAL)

**What**: Write regression tests to prevent future extraction issues.

**Pre-Condition**: Phase C verified data is correct.

**Launch Command**:

```
Task("Write Extraction Tests", "Team 37: Write comprehensive tests for the extraction pipeline in backend/tests/. Cover: (1) POST /api/v1/extraction/start happy path and error cases (already running → 409, bad source → 400), (2) ExcelDataExtractor with test fixtures (verify specific cell values), (3) supplemental field extraction (G27, E39, E40, E43, E44), (4) sync_extracted_to_properties creates correct Property/Deal records, (5) change detection dedup (re-extraction doesn't create duplicates), (6) error handling for corrupt files. Use test fixtures in backend/tests/fixtures/. After writing, run full test suite: conda run -n dashboard-backend pytest backend/tests/ -v AND npm run test. Report test count before and after.", "test-engineer")
```

**Expected Duration**: 10-20 minutes.

---

### Phase E: Final Gate (Team 38 — ALL PARALLEL)

**What**: Final quality gate before declaring the task complete.

**Pre-Condition**: Phase D tests all pass.

**Launch Command** (single message with 3 Task calls):

```
Task("Code Review", "Team 38 - Reviewer: Review all code changes made during this extraction task (bug fixes, new tests, config updates). Check for: code quality, consistent patterns, edge case handling, no hardcoded values, proper error handling.", "reviewer")

Task("Full Test Suite", "Team 38 - Tester: Run the complete test suite: (1) conda run -n dashboard-backend pytest backend/tests/ -v (2) npm run test. Report total test count and pass rate. Both must be 100% pass.", "tester")

Task("Production Readiness", "Team 38 - Validator: Verify: (1) npm run build succeeds with zero errors, (2) npx tsc --noEmit passes, (3) backend starts cleanly, (4) extraction endpoint responds to requests. Confirm deployment-ready.", "production-validator")
```

**Decision Point**: All three must report clean for the task to be considered complete.

**Expected Duration**: 5-10 minutes (all parallel).

---

## Troubleshooting Guide

### Common Issues and Resolution

| Issue | Symptom | Team That Catches It | Resolution |
|---|---|---|---|
| `LOCAL_DEALS_ROOT` not set | Extraction falls back to test fixtures | Team 28 | Set env var in `.env` pointing to OneDrive Deals folder |
| pyxlsb 0-based indexing bug | Cap rate values are from wrong cells | Team 29, 30 | Fix index conversion in `extractor.py` |
| Sheet name mismatch | `np.nan` for all values from that sheet | Team 30 | Update sheet name in cell mapping to match actual Excel sheet tab name |
| Auth token expired/missing | 401 response from extraction endpoint | Team 32 | Re-login via `POST /api/v1/auth/login` with admin credentials |
| Extraction already running | 409 response | Team 32 | Cancel via `POST /api/v1/extraction/cancel` or wait for completion |
| Property name collision | Last-file-wins overwrites data | Team 33 | Investigate duplicate property names across deal stages |
| `?? 0` bug in frontend | "0.0%" displayed instead of "N/A" | Team 36 | Change to `?? undefined` in Zod schema transform |
| Missing Property record | Extracted values have null property_id | Team 35 | Debug `sync_extracted_to_properties()` name matching logic |

### If Extraction Fails Mid-Run

1. Check `ExtractionRun.error_summary` for error categories
2. Check `ExtractionRun.per_file_status` for which files failed and why
3. Most common causes: file locked by OneDrive sync, corrupt Excel file, missing sheet
4. Fix the issue, then re-run extraction (change detection will skip already-processed files)

### If Data Looks Wrong After Extraction

1. Query `ExtractedValue` for the specific property and field to see raw extracted value
2. Check `is_error` flag — if true, the extraction failed for that cell
3. Open the source Excel file manually and verify the cell reference
4. If the cell reference is wrong, update the mapping and re-run extraction

---

## Summary: Total Agent Count for This Task

| Phase | Teams | Unique Agent Types | Total Agent Instances |
|---|---|---|---|
| A: Pre-Run | 28, 29, 30, 31 | 5 (Explore, config-safety-reviewer, backend-architect, researcher, coder) | 8 |
| B: Execute | 32 | 2 (coder, tester) | 2 |
| C: Post-Run | 33, 34, 35, 36 | 5 (backend-architect, researcher, coder, tester, frontend-developer) | 8 |
| D: Hardening | 37 | 2 (test-engineer, tester) | 2 |
| E: Final Gate | 38 | 3 (reviewer, tester, production-validator) | 3 |
| **Total** | **11 teams** | **10 unique types** | **23 agent instances** |

**Optimal execution with full parallelism**: ~25-55 minutes + review time between phases.
