# Agent Team Reference Guide

A comprehensive reference for Claude Code's built-in team functionality, listing practical tasks, the agents needed for each, their capabilities, and workflows.

---

## Routine Maintenance

### 1. Dependency Audit & Update

| Agent Name | subagent_type  | Can Edit? | Tools                               | Role on Team                                                                                                                        |
| ---------- | -------------- | --------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Researcher | `researcher` | Yes       | All tools                           | Scan `package.json`, `pyproject.toml` for outdated/vulnerable deps. Check changelogs for breaking changes.                      |
| Tester     | `tester`     | Yes       | Read, Write, Edit, Bash, Grep, Glob | After researcher identifies updates, run `npm audit`, `pip-audit`, bump versions, run full test suite to verify nothing breaks. |

**Flow**: Researcher identifies what's outdated/risky → reports findings → Tester applies updates one-by-one and runs tests after each → reports pass/fail.

---

### 2. Dead Code / Unused Import Cleanup

| Agent Name | subagent_type | Can Edit?                | Tools                               | Role on Team                                                                                  |
| ---------- | ------------- | ------------------------ | ----------------------------------- | --------------------------------------------------------------------------------------------- |
| Explorer   | `Explore`   | **No** (read-only) | All except Edit/Write               | Scan codebase for unused exports, orphaned files, dead imports. Produce a list of candidates. |
| Coder      | `coder`     | Yes                      | All tools                           | Take the explorer's list, remove dead code, update import graphs.                             |
| Tester     | `tester`    | Yes                      | Read, Write, Edit, Bash, Grep, Glob | Run full test suite + type check after each removal to confirm nothing broke.                 |

**Flow**: Explorer produces dead code report → Coder removes in batches → Tester verifies after each batch → team reports summary of what was removed.

---

### 3. Type Coverage Sweep

| Agent Name | subagent_type         | Can Edit? | Tools     | Role on Team                                                                                                                                    |
| ---------- | --------------------- | --------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| TS Expert  | `typescript-expert` | Yes       | All tools | Deep knowledge of TS type system, generics, inference. Finds `any` types, missing return types, untyped API calls. Fixes complex type issues. |
| Coder      | `coder`             | Yes       | All tools | Handle bulk simple fixes (adding return types, replacing `any` with proper types).                                                            |

**Flow**: TS Expert audits the codebase for type gaps, prioritizes by severity → Coder handles straightforward fixes → TS Expert handles complex generics/conditional types → both run `tsc --noEmit` to verify.

---

### 4. Test Gap Analysis

| Agent Name    | subagent_type     | Can Edit?    | Tools                               | Role on Team                                                                                                       |
| ------------- | ----------------- | ------------ | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Explorer      | `Explore`       | **No** | All except Edit/Write               | Map all functions/endpoints/components. Cross-reference against existing test files. Identify untested code paths. |
| Test Engineer | `test-engineer` | Yes          | Read, Write, Edit, Bash, Grep, Glob | Write missing tests. Specializes in test creation, coverage analysis, and validation across all testing levels.    |

**Flow**: Explorer produces a gap report (file:function → has test? branch coverage?) → Test Engineer writes tests for highest-priority gaps → runs suite to confirm coverage increase.

---

### 5. Lint & Style Enforcement

| Agent Name     | subagent_type      | Can Edit? | Tools     | Role on Team                                                                                                           |
| -------------- | ------------------ | --------- | --------- | ---------------------------------------------------------------------------------------------------------------------- |
| Linting Expert | `linting-expert` | Yes       | All tools | Expert in ESLint, Ruff, Prettier, coding standards across languages. Audits config, identifies violations, fixes them. |
| Coder          | `coder`          | Yes       | All tools | Handle bulk auto-fixable violations. Update config files if linting expert recommends rule changes.                    |

**Flow**: Linting Expert audits current config + violations → auto-fixes what's safe → Coder handles manual fixes that need context → both verify with `npm run lint` and `ruff check`.

---

## Code Quality & Health

### 6. Security Audit

| Agent Name       | subagent_type        | Can Edit? | Tools                        | Role on Team                                                                                                       |
| ---------------- | -------------------- | --------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Security Auditor | `security-auditor` | Yes       | Read, Edit, Bash, Grep, Glob | OWASP compliance, vulnerability assessment, auth flow review, dependency scanning. Specializes in threat modeling. |
| Researcher       | `researcher`       | Yes       | All tools                    | Research CVEs for current dependencies, check for known exploit patterns, verify security headers and CORS config. |

**Flow**: Security Auditor systematically checks auth flows, SQL injection, XSS, CSRF, secrets exposure → Researcher checks dependencies against CVE databases → both produce prioritized findings report with severity levels.

**Note**: The `security-auditor` type exists in multiple plugins (comprehensive-review, full-stack-orchestration, standalone). All have similar capabilities. The standalone one has: Read, Edit, Bash, Grep, Glob, Task, Skill.

---

### 7. API Contract Validation

| Agent Name        | subagent_type                             | Can Edit? | Tools                               | Role on Team                                                                                       |
| ----------------- | ----------------------------------------- | --------- | ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools                           | Expert in REST/GraphQL API design. Reviews Pydantic schemas, endpoint signatures, response shapes. |
| Tester            | `tester`                                | Yes       | Read, Write, Edit, Bash, Grep, Glob | Writes contract tests that assert frontend Zod schemas match backend Pydantic schemas.             |

**Flow**: Backend Architect maps all Pydantic response models → compares field-by-field against frontend Zod schemas in `src/lib/api/schemas/` → Tester writes automated contract tests to catch future drift → reports all mismatches.

---

### 8. Performance Profiling

| Agent Name        | subagent_type         | Can Edit?    | Tools                        | Role on Team                                                                                                        |
| ----------------- | --------------------- | ------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Performance Tuner | `performance-tuner` | Yes          | Read, Edit, Bash, Grep, Glob | Application profiling, bottleneck analysis, optimization. Profiles endpoints, identifies N+1 queries, slow renders. |
| Explorer          | `Explore`           | **No** | All except Edit/Write        | Maps data flow paths, identifies where queries happen, traces request lifecycle.                                    |

**Flow**: Explorer maps hot paths (which endpoints call which queries, which components trigger re-renders) → Performance Tuner profiles them, measures timing, identifies bottlenecks → produces ranked optimization recommendations.

---

### 9. Database Query Review

| Agent Name      | subagent_type       | Can Edit?    | Tools                                             | Role on Team                                                                                                               |
| --------------- | ------------------- | ------------ | ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Postgres Expert | `postgres-expert` | Yes          | Bash(psql, pg_dump, pg_restore), Read, Grep, Edit | Deep PostgreSQL expertise: query optimization, indexing strategies, JSONB operations, partitioning, connection management. |
| Explorer        | `Explore`         | **No** | All except Edit/Write                             | Find all SQLAlchemy queries across the codebase, map which endpoints trigger which queries.                                |

**Flow**: Explorer catalogs all queries → Postgres Expert analyzes each for missing indexes, N+1 patterns, suboptimal joins, unnecessary `SELECT *` → produces migration recommendations for new indexes.

---

### 10. Accessibility Audit

| Agent Name         | subagent_type          | Can Edit?    | Tools                                    | Role on Team                                                                                                                        |
| ------------------ | ---------------------- | ------------ | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Frontend Developer | `frontend-developer` | Yes          | Write, Read, MultiEdit, Bash, Grep, Glob | Responsive design, component building, accessibility patterns. Fixes ARIA labels, keyboard nav, focus management.                   |
| Explorer           | `Explore`            | **No** | All except Edit/Write                    | Scan all components for missing ARIA attributes, hardcoded colors without contrast ratios, missing `tabIndex`, non-semantic HTML. |

**Flow**: Explorer produces accessibility violation report → Frontend Developer fixes in priority order (critical: keyboard nav, screen reader → moderate: color contrast, focus indicators → low: semantic HTML improvements).

---

## Feature Development

### 11. Full-Stack Feature Build

| Agent Name    | subagent_type     | Can Edit? | Tools                               | Role on Team                                                                        |
| ------------- | ----------------- | --------- | ----------------------------------- | ----------------------------------------------------------------------------------- |
| Coder         | `coder`         | Yes       | All tools                           | Implements backend endpoint + frontend component. General-purpose implementation.   |
| Test Engineer | `test-engineer` | Yes       | Read, Write, Edit, Bash, Grep, Glob | Writes unit, integration, and E2E tests for the new feature.                        |
| Reviewer      | `reviewer`      | Yes       | Read, Edit, Grep, Glob, Bash        | Code review: checks quality, patterns, security, edge cases. Suggests improvements. |

**Flow**: Coder implements backend → Coder implements frontend → Test Engineer writes tests in parallel with frontend work → Reviewer reviews all changes → team iterates on feedback.

---

### 12. API Endpoint Scaffold

| Agent Name        | subagent_type                             | Can Edit? | Tools                               | Role on Team                                                                                                   |
| ----------------- | ----------------------------------------- | --------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools                           | Designs endpoint: route, request/response schemas, error handling, auth requirements. Implements the endpoint. |
| Test Engineer     | `test-engineer`                         | Yes       | Read, Write, Edit, Bash, Grep, Glob | Writes tests for the new endpoint (happy path, error cases, auth, validation).                                 |

**Flow**: Backend Architect designs + implements → Test Engineer writes comprehensive tests → both verify tests pass.

---

### 13. Component Library Extraction

| Agent Name   | subagent_type    | Can Edit? | Tools                                          | Role on Team                                                                                                   |
| ------------ | ---------------- | --------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| React Expert | `react-expert` | Yes       | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Expert in React patterns, hooks, component design. Identifies repeated patterns and designs shared components. |
| Coder        | `coder`        | Yes       | All tools                                      | Handles the bulk refactoring: extract components, update all consumers, verify props.                          |

**Flow**: React Expert audits components for duplication → designs shared component APIs (props, variants) → Coder extracts and updates all consumers → React Expert reviews final component design.

---

### 14. E2E Test Suite Expansion

| Agent Name        | subagent_type         | Can Edit?    | Tools                                          | Role on Team                                                                                  |
| ----------------- | --------------------- | ------------ | ---------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Playwright Expert | `playwright-expert` | Yes          | Bash, Read, Write, Edit, MultiEdit, Grep, Glob | Expert in Playwright: cross-browser automation, selectors, visual regression, CI integration. |
| Explorer          | `Explore`           | **No** | All except Edit/Write                          | Map all user flows in the app, identify which have E2E coverage and which don't.              |

**Flow**: Explorer maps user flows → identifies uncovered flows → Playwright Expert writes specs prioritized by importance (auth flows, critical paths first) → runs them to verify they pass.

---

## Documentation & Knowledge

### 15. API Documentation Generation

| Agent Name  | subagent_type   | Can Edit?    | Tools                                         | Role on Team                                                                                                         |
| ----------- | --------------- | ------------ | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Explorer    | `Explore`     | **No** | All except Edit/Write                         | Crawl all endpoint files, extract routes, params, request/response types, auth requirements.                         |
| Docs Writer | `docs-writer` | Yes          | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Technical documentation specialist. Takes explorer's raw data and produces clean, structured API docs with examples. |

**Flow**: Explorer extracts all endpoint metadata → Docs Writer organizes into structured documentation with request/response examples, auth requirements, error codes.

---

### 16. Architecture Diagram Update

| Agent Name | subagent_type  | Can Edit?    | Tools                 | Role on Team                                                                                                             |
| ---------- | -------------- | ------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Explorer   | `Explore`    | **No** | All except Edit/Write | Map module dependencies, data flow, service boundaries, database relationships.                                          |
| Researcher | `researcher` | Yes          | All tools             | Synthesize explorer's findings into coherent architecture description. Can use WebSearch for diagramming best practices. |

**Flow**: Explorer traces imports, DB models, API routes, frontend route tree → Researcher synthesizes into architecture narrative with Mermaid diagrams.

---

### 17. Onboarding Guide

| Agent Name  | subagent_type   | Can Edit?    | Tools                                         | Role on Team                                                                                   |
| ----------- | --------------- | ------------ | --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Explorer    | `Explore`     | **No** | All except Edit/Write                         | Catalog all env vars, setup scripts, config files, required services (Postgres, Redis, etc.).  |
| Docs Writer | `docs-writer` | Yes          | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Write clear step-by-step guide covering setup, common workflows, gotchas, and troubleshooting. |

**Flow**: Explorer inventories everything a new dev needs → Docs Writer produces a structured onboarding guide.

---

## DevOps & Infrastructure

### 18. CI Pipeline Review

| Agent Name          | subagent_type                                    | Can Edit? | Tools     | Role on Team                                                                  |
| ------------------- | ------------------------------------------------ | --------- | --------- | ----------------------------------------------------------------------------- |
| Deployment Engineer | `full-stack-orchestration:deployment-engineer` | Yes       | All tools | CI/CD expert: GitHub Actions, caching, parallel jobs, deployment automation.  |
| Researcher          | `researcher`                                   | Yes       | All tools | Research best practices, compare against current config, identify slow steps. |

**Flow**: Researcher benchmarks current CI times and identifies slow steps → Deployment Engineer optimizes caching, parallelism, job splitting → both verify pipeline still passes.

---

### 19. Docker Config Hardening

| Agent Name          | subagent_type                                    | Can Edit? | Tools                        | Role on Team                                                                                          |
| ------------------- | ------------------------------------------------ | --------- | ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| Security Auditor    | `security-auditor`                             | Yes       | Read, Edit, Bash, Grep, Glob | Check for secrets in images, excessive permissions, unnecessary packages, base image vulnerabilities. |
| Deployment Engineer | `full-stack-orchestration:deployment-engineer` | Yes       | All tools                    | Optimize multi-stage builds, minimize image size, add health checks, improve layer caching.           |

**Flow**: Security Auditor scans Dockerfiles + compose files for security issues → Deployment Engineer optimizes for size and performance → both verify containers build and run correctly.

---

### 20. Environment Config Audit

| Agent Name             | subagent_type              | Can Edit?    | Tools                        | Role on Team                                                                                                              |
| ---------------------- | -------------------------- | ------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Config Safety Reviewer | `config-safety-reviewer` | Yes          | Read, Edit, Grep, Glob, Bash | Specializes in production reliability: magic numbers, pool sizes, timeouts, connection limits. Checks all config is safe. |
| Explorer               | `Explore`                | **No** | All except Edit/Write        | Find every env var reference, every config file, every hardcoded value across the codebase.                               |

**Flow**: Explorer catalogs all config → Config Safety Reviewer checks: documented? has default? safe default? no secrets in code? consistent across environments?

---

## Refactoring & Tech Debt

### 21. Large File Decomposition

| Agent Name         | subagent_type          | Can Edit? | Tools                                   | Role on Team                                                                                                                             |
| ------------------ | ---------------------- | --------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Refactoring Expert | `refactoring-expert` | Yes       | Read, Grep, Glob, Edit, MultiEdit, Bash | Systematic code refactoring, code smell detection. Identifies extraction points, applies refactoring patterns without changing behavior. |
| Tester             | `tester`             | Yes       | Read, Write, Edit, Bash, Grep, Glob     | Runs tests after each refactoring step to ensure behavior is preserved. Adds tests if coverage would drop.                               |

**Flow**: Refactoring Expert identifies files >500 lines → plans decomposition (which functions/classes move where) → extracts in small steps → Tester verifies tests pass after each step.

---

### 22. Error Handling Standardization

| Agent Name | subagent_type | Can Edit?    | Tools                               | Role on Team                                                                                             |
| ---------- | ------------- | ------------ | ----------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Coder      | `coder`     | Yes          | All tools                           | Implements standardized error types, updates handlers.                                                   |
| Explorer   | `Explore`   | **No** | All except Edit/Write               | Catalog all current error patterns: bare `raise`, inconsistent HTTP status codes, missing error types. |
| Tester     | `tester`    | Yes          | Read, Write, Edit, Bash, Grep, Glob | Verifies error responses match new standard. Writes tests for error paths.                               |

**Flow**: Explorer audits current error patterns → team agrees on standard → Coder implements standard error classes + updates all handlers → Tester verifies.

---

### 23. State Management Cleanup

| Agent Name   | subagent_type    | Can Edit? | Tools                                          | Role on Team                                                                                                    |
| ------------ | ---------------- | --------- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| React Expert | `react-expert` | Yes       | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Expert in hooks, state management, re-rendering. Identifies redundant state, prop drilling, unnecessary stores. |
| Coder        | `coder`        | Yes       | All tools                                      | Applies the cleanup: removes redundant stores, simplifies data flow, updates consumers.                         |

**Flow**: React Expert audits all Zustand stores + component state → identifies redundancies and simplification opportunities → Coder applies changes → React Expert reviews.

---

### 24. Migration Consolidation

| Agent Name      | subagent_type       | Can Edit?    | Tools                                | Role on Team                                                                                                   |
| --------------- | ------------------- | ------------ | ------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Postgres Expert | `postgres-expert` | Yes          | Bash(psql, pg\_\*), Read, Grep, Edit | Reviews Alembic migration chain for squash opportunities, checks for conflicts, validates migration integrity. |
| Explorer        | `Explore`         | **No** | All except Edit/Write                | Map the full migration chain, identify dependencies, find migrations that could be combined.                   |

**Flow**: Explorer maps migration history → Postgres Expert identifies squash candidates → produces recommendation (which to squash, risks, rollback plan).

---

## Ongoing / Recurring

### 25. Pre-PR Quality Gate

| Agent Name       | subagent_type        | Can Edit? | Tools                               | Role on Team                                                          |
| ---------------- | -------------------- | --------- | ----------------------------------- | --------------------------------------------------------------------- |
| Reviewer         | `reviewer`         | Yes       | Read, Edit, Grep, Glob, Bash        | Code quality review: patterns, readability, edge cases, consistency.  |
| Tester           | `tester`           | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full test suite, check coverage delta, verify no regressions.     |
| Security Auditor | `security-auditor` | Yes       | Read, Edit, Bash, Grep, Glob        | Check diff for security issues: injection, auth bypass, secrets, XSS. |

**Flow**: All three work in parallel on the current diff → each produces findings → team consolidates into a go/no-go recommendation.

---

### 26. Weekly Health Check

| Agent Name        | subagent_type         | Can Edit?    | Tools                               | Role on Team                                                       |
| ----------------- | --------------------- | ------------ | ----------------------------------- | ------------------------------------------------------------------ |
| Explorer          | `Explore`           | **No** | All except Edit/Write               | Quick scan for new warnings, deprecations, type errors.            |
| Tester            | `tester`            | Yes          | Read, Write, Edit, Bash, Grep, Glob | Run full backend + frontend test suites, report results.           |
| Performance Tuner | `performance-tuner` | Yes          | Read, Edit, Bash, Grep, Glob        | Profile key endpoints, compare against baseline, flag regressions. |

**Flow**: All three run in parallel → produce a consolidated health report (test results, new warnings, performance changes).

---

### 27. Post-Merge Verification

| Agent Name           | subagent_type            | Can Edit? | Tools                               | Role on Team                                                                                                                      |
| -------------------- | ------------------------ | --------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Tester               | `tester`               | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full test suite on merged code.                                                                                               |
| Production Validator | `production-validator` | Yes       | All tools                           | Ensures application is fully implemented and deployment-ready. Checks build succeeds, no runtime errors, all features functional. |

**Flow**: Tester runs tests → Production Validator does build check + smoke test → both report results.

---

## Quick Reference: Agent Capabilities

| subagent_type                                    | Can Edit Files? | Can Run Bash? | Can Search Web? | Best For                               |
| ------------------------------------------------ | --------------- | ------------- | --------------- | -------------------------------------- |
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

| #   | Task                           | What It Finds                                                     |
| --- | ------------------------------ | ----------------------------------------------------------------- |
| #7  | API Contract Validation        | Pydantic ↔ Zod schema mismatches, missing fields, wrong types    |
| #4  | Test Gap Analysis              | Untested endpoints, uncovered branches, missing error path tests  |
| #20 | Environment Config Audit       | Undocumented env vars, hardcoded secrets, missing defaults        |
| #2  | Dead Code Cleanup              | Unused exports, orphaned files, stale imports                     |
| #3  | Type Coverage Sweep            | `any` types, missing return types, untyped API responses        |
| #5  | Lint & Style Enforcement       | Lint violations, inconsistent formatting, config gaps             |
| #22 | Error Handling Standardization | Inconsistent error patterns, bare raises, wrong HTTP status codes |

**Why all at once**: These are all primarily read/audit tasks. Running them in parallel gives a complete picture of every issue before anyone starts fixing anything.

---

## Phase 2: Fix (sequential by risk, each with testing)

| #   | Task                           | What It Fixes                                  | Why This Order                   |
| --- | ------------------------------ | ---------------------------------------------- | -------------------------------- |
| #7  | API Contract Validation        | Schema mismatches → runtime bugs              | Highest user-facing impact       |
| #22 | Error Handling Standardization | Inconsistent errors → confusing API responses | Affects all endpoints            |
| #3  | Type Coverage Sweep            | Type gaps → potential runtime crashes         | Catches bugs statically          |
| #2  | Dead Code Cleanup              | Cruft removal → smaller codebase              | Reduces noise for remaining work |
| #5  | Lint & Style Enforcement       | Style violations → clean baseline             | Cosmetic, do last                |
| #20 | Environment Config Audit       | Config gaps → document & add defaults         | Config, not code                 |

Each fix phase runs with a **Tester agent** that verifies all existing tests still pass after changes.

---

## Phase 3: Fill Gaps

| #   | Task                     | What It Adds                                         |
| --- | ------------------------ | ---------------------------------------------------- |
| #4  | Test Gap Analysis        | Writes missing tests for everything found in Phase 1 |
| #21 | Large File Decomposition | Splits any files that grew too large during fixes    |

---

## Phase 4: Final Gate

| #   | Task                    | What It Checks                                              |
| --- | ----------------------- | ----------------------------------------------------------- |
| #25 | Pre-PR Quality Gate     | Reviewer + Tester + Security Auditor validate the full diff |
| #27 | Post-Merge Verification | Production Validator confirms build + smoke tests pass      |

---

## Full Agent Roster (12 unique agent types across all phases)

| Agent                  | subagent_type                             | Phases  | Role                                                               |
| ---------------------- | ----------------------------------------- | ------- | ------------------------------------------------------------------ |
| Explorer               | `Explore`                               | 1, 2, 3 | Read-only scanning, mapping, cataloging across the entire codebase |
| Backend Architect      | `backend-development:backend-architect` | 1, 2    | Pydantic schema analysis, API contract comparison, endpoint review |
| TS Expert              | `typescript-expert`                     | 1, 2    | Find and fix type gaps,`any` usage, missing return types         |
| Config Safety Reviewer | `config-safety-reviewer`                | 1       | Env var audit, config safety, production readiness                 |
| Linting Expert         | `linting-expert`                        | 1, 2    | Lint violations, style enforcement, config updates                 |
| Coder                  | `coder`                                 | 2, 3    | Bulk fixes: dead code removal, error handling, schema updates      |
| Refactoring Expert     | `refactoring-expert`                    | 3       | Large file decomposition, safe structural changes                  |
| Test Engineer          | `test-engineer`                         | 3       | Write missing tests for gaps identified in Phase 1                 |
| Tester                 | `tester`                                | 2, 3, 4 | Run test suite after every change, verify no regressions           |
| Reviewer               | `reviewer`                              | 4       | Final code quality review of all changes                           |
| Security Auditor       | `security-auditor`                      | 4       | Final security check on the full diff                              |
| Production Validator   | `production-validator`                  | 4       | Build verification, deployment readiness                           |

---

## Tasks Excluded From This Pipeline (and why)

| Category            | Tasks             | Reason                                                                                                    |
| ------------------- | ----------------- | --------------------------------------------------------------------------------------------------------- |
| Feature Development | #11-14            | Building new features, not auditing existing code                                                         |
| Documentation       | #15-17            | Important but doesn't fix bugs or catch errors                                                            |
| Infrastructure      | #18-19            | CI/CD and Docker hardening — separate focused effort                                                     |
| Specialized Audits  | #6, #8-10, #23-24 | Security, performance, accessibility, state management, migrations — each deserves its own dedicated run |
| Recurring           | #26               | Weekly health check — run on a schedule, not as part of a one-time audit                                 |

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

| Section                                    | What to Change                                  | This Project's Value                                                                                            |
| ------------------------------------------ | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `Backend: FastAPI + SQLAlchemy...`       | Your actual backend framework and structure     | `FastAPI + SQLAlchemy async + Alembic (Python, in backend/)`                                                  |
| `Frontend: React + TypeScript...`        | Your actual frontend framework and structure    | `React + TypeScript + Vite (in src/)`                                                                         |
| `Backend schemas: Pydantic models in...` | Path to your backend response models            | `backend/app/schemas/` (deal.py, comparison.py, property.py, etc.)                                            |
| `Frontend schemas: Zod schemas in...`    | Path to your frontend validation schemas        | `src/lib/api/schemas/` (deal.ts, property.ts, etc.)                                                           |
| `Test commands:`                         | Your actual test runner commands                | Frontend:`npm run test` — Backend: `conda run -n dashboard-backend pytest backend/tests/`                  |
| `Build command:`                         | Your actual build command                       | `npm run build` (runs tsc + vite)                                                                             |
| `Lint commands:`                         | Your actual linting commands                    | Frontend:`npm run lint` — Backend: `ruff check backend/`                                                   |
| `Type check:`                            | Your actual type check command                  | `npx tsc --noEmit`                                                                                            |
| `Auth: JWT with role-based guards...`    | Your actual auth pattern (or remove if no auth) | JWT via `src/stores/authStore.ts`, backend guards: `require_analyst` (GET), `require_manager` (mutations) |
| `Config:`                                | Your env/config file locations                  | `.env` in project root, `.env.prod.example`, Docker configs in `docker/`                                  |
| `Dev server:`                            | Your local dev command                          | `npm run dev:all` (runs backend + frontend concurrently)                                                      |

### Expected Duration

| Phase               | Agents       | Estimated Time                              |
| ------------------- | ------------ | ------------------------------------------- |
| Phase 1: Discovery  | 7 parallel   | 5-10 minutes                                |
| Review break        | You          | As long as you need                         |
| Phase 2: Fix        | 6 sequential | 15-30 minutes                               |
| Phase 3: Fill Gaps  | 2-3 agents   | 10-20 minutes                               |
| Phase 4: Final Gate | 3 parallel   | 5-10 minutes                                |
| **Total**     |              | **~35-70 minutes + your review time** |

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

| Agent Name             | subagent_type              | Can Edit?    | Tools                        | Role on Team                                                                                                                                                                        |
| ---------------------- | -------------------------- | ------------ | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Explorer               | `Explore`                | **No** | All except Edit/Write        | Scan for `LOCAL_DEALS_ROOT` env var, verify OneDrive folder structure exists and contains `.xlsb`/`.xlsx` files. Map deal stage folders. Count files per stage.               |
| Config Safety Reviewer | `config-safety-reviewer` | Yes          | Read, Edit, Grep, Glob, Bash | Validate all extraction-related env vars are set and safe:`LOCAL_DEALS_ROOT`, `MAX_WORKERS`, `EXTRACTION_TIMEOUT`. Check `.env` and `.env.prod.example` for completeness. |

**Flow**: Explorer checks the filesystem and codebase config references → Config Safety Reviewer validates all env vars are present, documented, and have safe defaults → team produces a go/no-go for extraction readiness.

**Pre-Conditions**: Access to the local OneDrive path. Backend virtualenv activated.

**Output**: Pre-flight report listing: files discovered per stage, env var status, any missing config.

---

### 29. Extraction Pipeline Code Audit

| Agent Name        | subagent_type                             | Can Edit? | Tools     | Role on Team                                                                                                                                                                               |
| ----------------- | ----------------------------------------- | --------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools | Review `extract.py`, `common.py`, `extractor.py` for logic errors, race conditions, incorrect indexing. Verify the background task properly handles all error paths and edge cases.  |
| Researcher        | `researcher`                            | Yes       | All tools | Cross-reference supplemental cell mappings (T3_RETURN_ON_COST at G27, IRR at E39/E43, MOIC at E40/E44) against actual UW model sheet structure. Verify pyxlsb 0-based indexing is correct. |

**Flow**: Backend Architect reviews extraction code for correctness (especially `run_extraction_task()` in `common.py` — 756 lines) → Researcher validates cell references against known UW model layouts → both report issues that could cause silent data corruption.

**Key Files**:

- `backend/app/api/v1/endpoints/extraction/extract.py` — API endpoint
- `backend/app/api/v1/endpoints/extraction/common.py` — Background task orchestration (756 lines)
- `backend/app/extraction/extractor.py` — Excel parsing engine (632 lines)
- `backend/app/extraction/sharepoint.py` — SharePoint integration (705 lines)

**Output**: Code audit report with any bugs, incorrect cell references, or logic issues that must be fixed before running extraction.

---

### 30. Cell Mapping & Reference File Validation

| Agent Name | subagent_type  | Can Edit?    | Tools                 | Role on Team                                                                                                                                                                                   |
| ---------- | -------------- | ------------ | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Explorer   | `Explore`    | **No** | All except Edit/Write | Find every cell mapping definition across the codebase: reference CSV/JSON files, hardcoded supplemental mappings in `common.py`, and any test fixture mappings. Catalog all of them.        |
| Researcher | `researcher` | Yes          | All tools             | For each mapping, verify: sheet name exists in typical UW models, cell address is plausible for the data type, category label is correct. Flag any mappings that reference nonexistent sheets. |

**Flow**: Explorer catalogs every cell mapping source (reference files, supplemental dicts, test fixtures) → Researcher validates each mapping's sheet/cell/type is correct → team produces a validated mapping table.

**Critical Supplemental Mappings to Verify**:

| Field Name             | Sheet                   | Cell | Expected Data Type |
| ---------------------- | ----------------------- | ---- | ------------------ |
| T3_RETURN_ON_COST      | Assumptions Summary     | G27  | numeric (%)        |
| UNLEVERED_RETURNS_IRR  | Returns Metrics Summary | E39  | numeric (%)        |
| UNLEVERED_RETURNS_MOIC | Returns Metrics Summary | E40  | numeric (x)        |
| LEVERED_RETURNS_IRR    | Returns Metrics Summary | E43  | numeric (%)        |
| LEVERED_RETURNS_MOIC   | Returns Metrics Summary | E44  | numeric (x)        |

**Output**: Validated mapping table with pass/fail per field. Any "fail" items must be fixed before extraction.

---

### 31. Database State Snapshot (Pre-Extraction Baseline)

| Agent Name | subagent_type | Can Edit?    | Tools                 | Role on Team                                                                                                                                                                          |
| ---------- | ------------- | ------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coder      | `coder`     | Yes          | All tools             | Query the database for current state: count of ExtractionRun records, count of ExtractedValue records, count of Property/Deal records. Snapshot existing cap rate and returns values. |
| Explorer   | `Explore`   | **No** | All except Edit/Write | Map the CRUD functions used for querying extraction data. Identify the exact queries needed to capture baseline metrics.                                                              |

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

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                                                                                                            |
| ---------- | ------------- | --------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coder      | `coder`     | Yes       | All tools                           | Start the backend server if needed. Execute `POST /api/v1/extraction/start {"source": "local"}`. Poll `GET /api/v1/extraction/status/{run_id}` until completion. Log all responses. |
| Tester     | `tester`    | Yes       | Read, Write, Edit, Bash, Grep, Glob | Monitor backend logs during extraction for errors/warnings. After completion, verify the ExtractionRun record has correct stats (files_discovered, files_processed, success_rate).      |

**Flow**: Coder starts extraction → polls status endpoint every 10-15 seconds → Tester watches logs for errors → both verify final status is "completed" (not "failed") → team reports extraction summary.

**Expected Success Criteria**:

- ExtractionRun status = `"completed"`
- `files_failed` = 0 (or acceptably low)
- `success_rate` ≥ 95%
- No unhandled exceptions in backend logs

**Output**: Extraction run report with: run_id, duration, files processed, files failed, success rate, any errors.

---

### 33. Post-Extraction Data Integrity Validation

| Agent Name        | subagent_type                             | Can Edit? | Tools                               | Role on Team                                                                                                                                                           |
| ----------------- | ----------------------------------------- | --------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools                           | Query ExtractedValue table for the new run_id. Verify: correct property count, correct field count per property, no orphaned records, all property_ids are backfilled. |
| Tester            | `tester`                                | Yes       | Read, Write, Edit, Bash, Grep, Glob | Compare post-extraction counts against pre-extraction baseline. Verify net-new properties were created. Spot-check 3-5 known property values against expected values.  |

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

| Agent Name        | subagent_type                             | Can Edit? | Tools     | Role on Team                                                                                                                                                                                       |
| ----------------- | ----------------------------------------- | --------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools | Query the specific cap rate and TC T3 returns fields from ExtractedValue. Verify values are numeric, in expected ranges (IRR: -50% to +100%, MOIC: 0x to 10x, Cap Rate: 0% to 20%). Flag outliers. |
| Researcher        | `researcher`                            | Yes       | All tools | Cross-reference a sample of extracted values against manually-read values from the source Excel files. Confirm the extraction engine is reading the correct cells.                                 |

**Flow**: Backend Architect queries all cap rate and returns fields → validates value ranges → Researcher manually spot-checks 2-3 files against extracted values → team confirms extraction accuracy.

**Fields to Verify**:

| Field Name             | Expected Range      | Value Column      |
| ---------------------- | ------------------- | ----------------- |
| CAP_RATE               | 0.0 – 0.20 (0-20%) | `value_numeric` |
| T3_RETURN_ON_COST      | 0.0 – 0.50 (0-50%) | `value_numeric` |
| UNLEVERED_RETURNS_IRR  | -0.50 – 1.00       | `value_numeric` |
| UNLEVERED_RETURNS_MOIC | 0.0 – 10.0         | `value_numeric` |
| LEVERED_RETURNS_IRR    | -0.50 – 1.00       | `value_numeric` |
| LEVERED_RETURNS_MOIC   | 0.0 – 10.0         | `value_numeric` |

**Output**: Field verification report with value distributions, outlier flags, and spot-check confirmation.

---

### 35. Property & Deal Record Sync Verification

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                                                                                                       |
| ---------- | ------------- | --------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coder      | `coder`     | Yes       | All tools                           | Query Property and Deal tables to verify sync: every extracted property has a Property record, every Property has a Deal record, deal stages match source folder structure.        |
| Tester     | `tester`    | Yes       | Read, Write, Edit, Bash, Grep, Glob | Verify the API endpoints that serve property/deal data return the newly extracted data. Test `GET /api/v1/deals/`, `GET /api/v1/properties/` to confirm frontend-visible data. |

**Flow**: Coder verifies DB-level sync (Property ↔ Deal ↔ ExtractedValue relationships) → Tester verifies API-level responses include the new data → team confirms the full pipeline from Excel to API is working.

**Sync Checks**:

1. Every property in ExtractedValue has a matching Property record
2. Every Property has a Deal with correct `stage` (initial_review, active_review, under_contract, closed)
3. Deal financial fields (cap_rate, irr, moic) are populated from ExtractedValue
4. API responses include the new properties with correct values

**Output**: Sync verification report with pass/fail per check.

---

### 36. Frontend Display & Rendering Validation

| Agent Name         | subagent_type          | Can Edit? | Tools                                          | Role on Team                                                                                                                                                                                    |
| ------------------ | ---------------------- | --------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend Developer | `frontend-developer` | Yes       | Write, Read, MultiEdit, Bash, Grep, Glob       | Verify that frontend components correctly display extracted cap rate and returns data. Check KPICard rendering, deal detail pages, kanban card fields, and any comparison views.                |
| React Expert       | `react-expert`       | Yes       | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Audit data binding: verify Zod schemas parse the API response correctly, check for `?? 0` bugs (should be `?? undefined` for "N/A" display), confirm trend calculations handle null values. |

**Flow**: Frontend Developer traces data from API response → Zustand store → component props → rendered output for cap rate and returns fields → React Expert checks for known rendering bugs (KPICard trend guard, Zod nullable handling) → team confirms correct display.

**Known Bug Patterns to Check**:

- `?? 0` instead of `?? undefined` causes "0.0%" instead of "N/A" for missing values
- `trend && trend > 0` is falsy for `trend === 0` — must use `!== undefined && !== 0`
- shadcn CSS vars must be in `:root` or components render transparent

**Output**: Frontend rendering report confirming correct display or listing display bugs.

---

### 37. Extraction Regression Test Suite

| Agent Name    | subagent_type     | Can Edit? | Tools                               | Role on Team                                                                                                                                                                                           |
| ------------- | ----------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Test Engineer | `test-engineer` | Yes       | Read, Write, Edit, Bash, Grep, Glob | Write comprehensive tests for: extraction endpoint (start/cancel/status), Excel parsing (xlsb/xlsx with known cell values), database sync (property/deal creation), and supplemental field extraction. |
| Tester        | `tester`        | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run the full backend + frontend test suite after new tests are added. Verify no regressions. Report final test count delta.                                                                            |

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

| Agent Name           | subagent_type            | Can Edit? | Tools                               | Role on Team                                                                                                                                                     |
| -------------------- | ------------------------ | --------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reviewer             | `reviewer`             | Yes       | Read, Edit, Grep, Glob, Bash        | Review all code changes made during the extraction task (bug fixes, new tests, any config updates). Check quality, patterns, edge cases.                         |
| Tester               | `tester`               | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full backend + frontend test suite one final time. Report total test count and pass rate.                                                                    |
| Production Validator | `production-validator` | Yes       | All tools                           | Verify `npm run build` succeeds, `npx tsc --noEmit` passes, backend starts cleanly, extraction endpoint responds to health checks. Confirm deployment-ready. |

**Flow**: All three work in parallel → Reviewer checks code quality → Tester verifies all tests pass → Production Validator confirms build + startup → team produces final go/no-go report.

**Output**: Final verification report with go/no-go recommendation.

---

## Quick Reference: Extraction Teams

| #  | Team Name                   | Agents                                 | Phase     | Parallel?  | Purpose                                        |
| -- | --------------------------- | -------------------------------------- | --------- | ---------- | ---------------------------------------------- |
| 28 | Pre-Flight Check            | Explorer, Config Safety Reviewer       | Pre-Run   | Yes        | Verify env vars, file paths, config            |
| 29 | Pipeline Code Audit         | Backend Architect, Researcher          | Pre-Run   | Yes        | Review code for bugs before running            |
| 30 | Cell Mapping Validation     | Explorer, Researcher                   | Pre-Run   | Yes        | Verify Excel cell references are correct       |
| 31 | Database Baseline Snapshot  | Coder, Explorer                        | Pre-Run   | Yes        | Capture pre-extraction metrics                 |
| 32 | Extraction Execution        | Coder, Tester                          | Execute   | Sequential | Run extraction, monitor progress               |
| 33 | Data Integrity Validation   | Backend Architect, Tester              | Post-Run  | Yes        | Verify data completeness and correctness       |
| 34 | Cap Rate & Returns Verify   | Backend Architect, Researcher          | Post-Run  | Yes        | Validate specific financial fields             |
| 35 | Property/Deal Sync Verify   | Coder, Tester                          | Post-Run  | Yes        | Verify Property ↔ Deal ↔ ExtractedValue sync |
| 36 | Frontend Display Validation | Frontend Developer, React Expert       | Post-Run  | Yes        | Verify UI renders data correctly               |
| 37 | Regression Test Suite       | Test Engineer, Tester                  | Hardening | Sequential | Write new tests, run full suite                |
| 38 | Final Verification Gate     | Reviewer, Tester, Production Validator | Final     | Yes        | Go/no-go quality gate                          |

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

| Issue                        | Symptom                                   | Team That Catches It | Resolution                                                             |
| ---------------------------- | ----------------------------------------- | -------------------- | ---------------------------------------------------------------------- |
| `LOCAL_DEALS_ROOT` not set | Extraction falls back to test fixtures    | Team 28              | Set env var in `.env` pointing to OneDrive Deals folder              |
| pyxlsb 0-based indexing bug  | Cap rate values are from wrong cells      | Team 29, 30          | Fix index conversion in `extractor.py`                               |
| Sheet name mismatch          | `np.nan` for all values from that sheet | Team 30              | Update sheet name in cell mapping to match actual Excel sheet tab name |
| Auth token expired/missing   | 401 response from extraction endpoint     | Team 32              | Re-login via `POST /api/v1/auth/login` with admin credentials        |
| Extraction already running   | 409 response                              | Team 32              | Cancel via `POST /api/v1/extraction/cancel` or wait for completion   |
| Property name collision      | Last-file-wins overwrites data            | Team 33              | Investigate duplicate property names across deal stages                |
| `?? 0` bug in frontend     | "0.0%" displayed instead of "N/A"         | Team 36              | Change to `?? undefined` in Zod schema transform                     |
| Missing Property record      | Extracted values have null property_id    | Team 35              | Debug `sync_extracted_to_properties()` name matching logic           |

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

| Phase           | Teams              | Unique Agent Types                                                        | Total Agent Instances        |
| --------------- | ------------------ | ------------------------------------------------------------------------- | ---------------------------- |
| A: Pre-Run      | 28, 29, 30, 31     | 5 (Explore, config-safety-reviewer, backend-architect, researcher, coder) | 8                            |
| B: Execute      | 32                 | 2 (coder, tester)                                                         | 2                            |
| C: Post-Run     | 33, 34, 35, 36     | 5 (backend-architect, researcher, coder, tester, frontend-developer)      | 8                            |
| D: Hardening    | 37                 | 2 (test-engineer, tester)                                                 | 2                            |
| E: Final Gate   | 38                 | 3 (reviewer, tester, production-validator)                                | 3                            |
| **Total** | **11 teams** | **10 unique types**                                                 | **23 agent instances** |

**Optimal execution with full parallelism**: ~25-55 minutes + review time between phases.

---

---

# UW Model Grouping Expansion — Deferred & Ungrouped Template Families

A dedicated set of agent teams designed to systematically identify, analyze, map, and extract data from UW model files that do **not** match the initial extraction criteria (the ~1,169 cell mappings from the production reference file). These teams address the **9 deferred groups (66 files)** and **2 excluded groups (4 files)** that were identified by the grouping pipeline but not yet extracted.

**Task Summary**: Expand extraction coverage beyond the current 30 active groups (244 files) by analyzing the structural differences of deferred/excluded groups, creating new cell mappings for each template family, and extracting their data into the database.

**Why This Needs Dedicated Teams**: The deferred groups use different Excel template layouts — different sheet names, different cell locations for the same data fields, and sometimes entirely different data organization. Each template family requires its own cell mapping before data can be extracted. This is a multi-phase effort: structural analysis → mapping creation → validation → extraction → integration.

---

## Current State: Grouping Pipeline Inventory

### Summary (from `groups.json`)

| Category           | Groups | Files | Status                                         |
| ------------------ | ------ | ----- | ---------------------------------------------- |
| **Active**   | 30     | 244   | Extracting with production reference file      |
| **Deferred** | 9      | 66    | Structurally different — need new mappings    |
| **Excluded** | 2      | 4     | Too different or corrupt — need investigation |
| **Total**    | 41     | 314   |                                                |

### Active Groups (currently extracting — no action needed)

These 30 groups share the production template layout and are already extracting ~1,169 fields per file using the existing cell mappings. Groups include: group_5, group_10, group_12, group_13, group_16, group_18, group_19, group_22, group_26–47.

### Deferred Groups (target of this effort)

| Group    | Files | Reason Deferred                                                   |
| -------- | ----- | ----------------------------------------------------------------- |
| group_1  | 10    | Different sheet structure — likely older "Proforma" template era |
| group_7  | 13    | Different sheet names/layout — likely a mid-era template variant |
| group_9  | 8     | Structural overlap below 80% with production template             |
| group_14 | 3     | Small cluster with unique sheet organization                      |
| group_15 | 6     | Different template family — distinct header/label structure      |
| group_17 | 8     | Alternative sheet naming convention                               |
| group_20 | ~8    | Structural variant — different column organization               |
| group_21 | ~5    | Distinct template family                                          |
| group_23 | ~5    | Low overlap with any active group                                 |

### Excluded Groups (need investigation)

| Group        | Files | Reason Excluded                                  |
| ------------ | ----- | ------------------------------------------------ |
| (excluded_1) | ~2    | Corrupt or unreadable — fingerprinting errored  |
| (excluded_2) | ~2    | Too structurally different from all other groups |

---

## Existing Infrastructure

### Backend Pipeline Code (fully built, operational)

| Component                       | File                                           | Purpose                                                                      |
| ------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------- |
| **Pipeline Orchestrator** | `backend/app/extraction/group_pipeline.py`   | 4-phase pipeline: discovery → fingerprint → group → extract               |
| **Fingerprinter**         | `backend/app/extraction/fingerprint.py`      | Structural fingerprinting (sheet names, headers, col-A labels, cell counts)  |
| **Grouping Algorithm**    | `backend/app/extraction/grouping.py`         | Jaccard overlap clustering (≥95% identity, ≥80% variant, <80% separate)    |
| **Reference Mapper**      | `backend/app/extraction/reference_mapper.py` | 4-tier auto-mapping (same sheet+cell → shifted → renamed sheet → synonym) |
| **Cell Mapping Parser**   | `backend/app/extraction/cell_mapping.py`     | Parses production reference file (~1,169 mappings)                           |
| **File Filter**           | `backend/app/extraction/file_filter.py`      | Candidate file filtering (name patterns, size, date)                         |
| **Excel Extractor**       | `backend/app/extraction/extractor.py`        | Excel parsing engine with sheet caching                                      |
| **Validation**            | `backend/app/extraction/validation.py`       | Cross-group validation                                                       |

### API Endpoints (fully built)

| Endpoint                                | Method | Purpose                                           |
| --------------------------------------- | ------ | ------------------------------------------------- |
| `/extraction/grouping/status`         | GET    | Pipeline status                                   |
| `/extraction/grouping/discover`       | POST   | Phase 1: Discover files                           |
| `/extraction/grouping/fingerprint`    | POST   | Phase 2: Fingerprint + auto-group                 |
| `/extraction/grouping/groups`         | GET    | List all groups                                   |
| `/extraction/grouping/groups/{name}`  | GET    | Group detail                                      |
| `/extraction/grouping/reference-map`  | POST   | Phase 3: Auto-map fields                          |
| `/extraction/grouping/reconcile`      | POST   | Phase 3.4: Property name reconciliation           |
| `/extraction/grouping/conflict-check` | POST   | Phase 4.1: Conflict check                         |
| `/extraction/grouping/extract/{name}` | POST   | Phase 4.2: Extract single group (dry-run default) |
| `/extraction/grouping/approve/{name}` | POST   | Approve group for live extraction                 |
| `/extraction/grouping/extract-batch`  | POST   | Batch extract multiple groups                     |
| `/extraction/grouping/validate`       | POST   | Cross-group validation                            |

### Frontend Components (fully built)

| Component                | File                                                            | Purpose                                                   |
| ------------------------ | --------------------------------------------------------------- | --------------------------------------------------------- |
| `GroupPipelineTab`     | `src/features/extraction/components/GroupPipelineTab.tsx`     | Main pipeline UI with stepper + action bar                |
| `GroupPipelineStepper` | `src/features/extraction/components/GroupPipelineStepper.tsx` | Visual phase progress indicator                           |
| `GroupList`            | `src/features/extraction/components/GroupList.tsx`            | Sortable group table with dry-run/approve/extract actions |
| `GroupDetail`          | `src/features/extraction/components/GroupDetail.tsx`          | Detailed view of a single group                           |
| `ConflictReport`       | `src/features/extraction/components/ConflictReport.tsx`       | Conflict check results display                            |
| `DryRunPreview`        | `src/features/extraction/components/DryRunPreview.tsx`        | Dry-run extraction preview                                |
| `BatchExtractionPanel` | `src/features/extraction/components/BatchExtractionPanel.tsx` | Multi-group batch extraction UI                           |
| `useGroupPipeline`     | `src/features/extraction/hooks/useGroupPipeline.ts`           | All query + mutation hooks                                |
| Types                    | `src/types/grouping.ts`                                       | TypeScript interfaces for all responses                   |

### Existing Tests

| Test File                                                                      | Coverage Area            |
| ------------------------------------------------------------------------------ | ------------------------ |
| `backend/tests/test_extraction/test_fingerprint.py`                          | Fingerprinting logic     |
| `backend/tests/test_extraction/test_grouping.py`                             | Grouping algorithm       |
| `backend/tests/test_extraction/test_group_discovery.py`                      | Discovery phase          |
| `backend/tests/test_extraction/test_group_extraction.py`                     | Group extraction         |
| `backend/tests/test_api/test_grouping.py`                                    | Grouping API endpoints   |
| `backend/tests/test_api/test_grouping_phase4.py`                             | Phase 4 API endpoints    |
| `backend/tests/test_extraction/test_phase4_extraction.py`                    | Phase 4 extraction logic |
| `src/features/extraction/components/__tests__/GroupList.test.tsx`            | GroupList component      |
| `src/features/extraction/components/__tests__/GroupPipelineStepper.test.tsx` | Stepper component        |
| `src/features/extraction/hooks/__tests__/useGroupPipeline.test.ts`           | Hook tests               |

### Data Artifacts

| Artifact              | Path                                                 | Contents                                             |
| --------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `groups.json`       | `backend/data/extraction_groups/groups.json`       | All 41 groups with fingerprints, overlaps, variances |
| `fingerprints.json` | `backend/data/extraction_groups/fingerprints.json` | Per-file fingerprints for all 314 files              |
| `config.json`       | `backend/data/extraction_groups/config.json`       | Pipeline state                                       |

---

## Next Steps: Expanding Extraction to Deferred Groups

### Phase 1: Structural Analysis of Deferred Groups

**Goal**: Understand what makes each deferred group structurally different from the active groups.

1. For each of the 9 deferred groups, extract and compare:
   - Sheet names vs production template sheet names
   - Header labels vs production template headers
   - Column-A labels vs production template row labels
   - Overall structural overlap percentage with the closest active group
2. Classify each deferred group into a **template family** (e.g., "older Proforma template", "mid-era variant", "alternative vendor template")
3. Identify which deferred groups are structurally similar to **each other** (could share a single new mapping)
4. Rank groups by extraction value: (file count × estimated unique data fields)

### Phase 2: Cell Mapping Creation for Each Template Family

**Goal**: Create new cell mapping files for each distinct template family.

1. For each template family, open 1-2 representative Excel files manually
2. Locate the equivalent fields: where does this template store cap rate, IRR, MOIC, unit count, purchase price, etc.?
3. Create a mapping file (CSV or JSON) in the same format as the production reference
4. Use the existing 4-tier auto-mapper (`reference_mapper.py`) to bootstrap — it will auto-map fields where labels match, leaving only truly different fields for manual mapping
5. Validate mappings with dry-run extraction on each representative file

### Phase 3: Extraction & Validation

**Goal**: Extract data from deferred groups using new mappings.

1. Run dry-run extraction per group using the grouping pipeline API
2. Verify extracted values against manually-read values from source files
3. Approve groups that pass validation
4. Run live extraction
5. Verify Property/Deal records are created correctly

### Phase 4: Integration & Regression Testing

**Goal**: Ensure expanded extraction doesn't break existing data.

1. Run cross-group validation to detect property name collisions
2. Verify frontend displays new properties correctly
3. Add regression tests for new template families
4. Update extraction documentation

---

## Grouping Expansion Agent Teams

### 39. Deferred Group Structural Analysis

| Agent Name | subagent_type  | Can Edit?    | Tools                 | Role on Team                                                                                                                                                                                                                                                     |
| ---------- | -------------- | ------------ | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Explorer   | `Explore`    | **No** | All except Edit/Write | Read `groups.json` deferred_groups section. For each deferred group: extract sheet names, header labels, col-A labels, structural overlap scores, and variance data. Compare against active group sheet structures.                                            |
| Researcher | `researcher` | Yes          | All tools             | For each deferred group, open 1-2 representative `.xlsb`/`.xlsx` files (using pyxlsb/openpyxl in a Python script). Document the sheet layout, key data locations (cap rate, IRR, MOIC, unit count, price), and how they differ from the production template. |

**Flow**: Explorer catalogs all 9 deferred groups' fingerprint data from `groups.json` → Researcher opens representative files and maps their actual data layout → team produces a **Template Family Classification Report** with: family name, member groups, sheet differences, estimated mapping effort.

**Output**: Template Family Classification Report — a structured table showing each deferred group's template family, key structural differences, and priority ranking.

---

### 40. Excluded Group Investigation

| Agent Name | subagent_type | Can Edit?    | Tools                 | Role on Team                                                                                                                                                                                                                   |
| ---------- | ------------- | ------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Explorer   | `Explore`   | **No** | All except Edit/Write | Find the excluded groups in `groups.json`. Extract file paths, error messages, and any fingerprint data available. Determine if exclusion was due to corrupt files, unreadable format, or extreme structural divergence.     |
| Coder      | `coder`     | Yes          | All tools             | Attempt to open each excluded file with pyxlsb/openpyxl in a diagnostic script. Report: does the file open? What sheets exist? Is data present? Is it a valid UW model or a non-model file (e.g., investor memo, closing doc)? |

**Flow**: Explorer identifies excluded files and reasons → Coder runs diagnostic script on each file → team produces a disposition report: reclassify as deferred (if salvageable), confirm exclusion (if not a UW model), or flag as corrupt (if unreadable).

**Output**: Excluded File Disposition Report — per-file: open/fail, sheet list, data present, recommendation (reclassify / confirm exclusion / flag corrupt).

---

### 41. Auto-Mapping Bootstrap for New Template Families

| Agent Name        | subagent_type                             | Can Edit? | Tools     | Role on Team                                                                                                                                                                                                                                                                       |
| ----------------- | ----------------------------------------- | --------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools | For each new template family, run the existing `auto_map_group()` function from `reference_mapper.py` against the production mappings. Analyze which fields auto-map (Tier 1-2), which partially map (Tier 3-4), and which have no match.                                      |
| Researcher        | `researcher`                            | Yes       | All tools | For unmapped fields, cross-reference the representative file's actual cell contents against known field names. Identify the correct sheet + cell for each unmapped field. Produce a supplemental mapping dict (like the existing `GOING_IN_CAP_RATE` override in `common.py`). |

**Flow**: Backend Architect runs auto-mapper on each deferred group → reports Tier 1-4 mapping counts → Researcher manually locates unmapped fields in representative files → team produces per-family supplemental mapping files.

**Key Context**: The existing auto-mapper already handles Tier 1 (same sheet+cell), Tier 2 (same label, different position), Tier 3 (partial label), and Tier 4 (synonym). Fields that don't match any tier need manual cell location from representative files.

**Output**: Per-family mapping report with auto-mapped fields, supplemental mappings for unmapped fields, and confidence scores.

---

### 42. Supplemental Mapping Integration

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                                                                                                                                                                                                                                        |
| ---------- | ------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Coder      | `coder`     | Yes       | All tools                           | Integrate new supplemental mappings into the extraction pipeline. Either extend the existing supplemental overrides dict in `common.py` or create per-family mapping files in `backend/data/extraction_groups/{family_name}/`. Update `group_pipeline.py` to load family-specific mappings during extraction. |
| Tester     | `tester`    | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run dry-run extraction for each deferred group using the new mappings. Verify extracted values match expected values from representative files. Run full backend test suite to confirm no regressions.                                                                                                              |

**Flow**: Coder integrates mappings → Tester runs dry-run extraction per group → both verify correctness → Coder fixes any mapping errors found during dry-run → Tester re-runs until clean.

**Output**: Updated extraction pipeline with per-family mappings. Dry-run reports showing extracted value counts and sample values per group.

---

### 43. Deferred Group Extraction Execution

| Agent Name | subagent_type | Can Edit? | Tools                               | Role on Team                                                                                                                                                                                                                                                                                                 |
| ---------- | ------------- | --------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Coder      | `coder`     | Yes       | All tools                           | For each validated deferred group: (1) run dry-run via `POST /extraction/grouping/extract/{name}?dry_run=true`, (2) review dry-run report, (3) if clean, approve via `POST /extraction/grouping/approve/{name}`, (4) run live extraction via `POST /extraction/grouping/extract/{name}?dry_run=false`. |
| Tester     | `tester`    | Yes       | Read, Write, Edit, Bash, Grep, Glob | After each live extraction: query ExtractedValue table for new records, verify property_id backfill, verify Property/Deal records created, spot-check 2-3 values per group against source files.                                                                                                             |

**Flow**: Coder runs extraction group-by-group (dry-run → approve → live) → Tester validates each group's data → both escalate any data issues before proceeding to next group.

**Auth Note**: Extraction endpoints require `require_manager`. Use admin credentials (`matt@bandrcapital.com` / `Wildcats777!!`).

**Output**: Per-group extraction report: files processed, values extracted, properties created, spot-check results.

---

### 44. Cross-Group Validation & Conflict Resolution

| Agent Name        | subagent_type                             | Can Edit? | Tools     | Role on Team                                                                                                                                                                                                |
| ----------------- | ----------------------------------------- | --------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend Architect | `backend-development:backend-architect` | Yes       | All tools | Run `POST /extraction/grouping/validate` to check for: property name collisions between deferred and active groups, duplicate field extractions, inconsistent values for the same property across groups. |
| Coder             | `coder`                                 | Yes       | All tools | Resolve any conflicts found: merge duplicate properties, reconcile conflicting values (prefer newer extraction or higher-confidence mapping), update Property/Deal records as needed.                       |

**Flow**: Backend Architect runs cross-group validation → identifies all conflicts → Coder resolves each conflict per the reconciliation rules → Backend Architect re-validates to confirm clean.

**Reconciliation Rules**:

- Property name collision: Use `reconcile_property_names()` from `reference_mapper.py` (exact → normalized → fuzzy → unmatched)
- Duplicate field values: Prefer the extraction with higher mapping confidence (Tier 1 > Tier 2 > Tier 3 > Tier 4)
- Conflicting numeric values: Flag for manual review (don't auto-resolve financial data)

**Output**: Conflict resolution report with actions taken per conflict.

---

### 45. Frontend Display Verification for Expanded Data

| Agent Name         | subagent_type          | Can Edit? | Tools                                          | Role on Team                                                                                                                                                                                                                                                                             |
| ------------------ | ---------------------- | --------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend Developer | `frontend-developer` | Yes       | Write, Read, MultiEdit, Bash, Grep, Glob       | Verify that newly extracted properties from deferred groups appear correctly in: Deals kanban board, property detail pages, deal comparison view, extraction dashboard group list. Check that GroupPipelineTab shows deferred groups transitioning to active.                            |
| React Expert       | `react-expert`       | Yes       | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Audit data flow for edge cases: properties with partial data (some fields extracted, others not), properties with zero/null financial values, groups with sub-variants that have different field coverage. Verify no rendering bugs (`?? 0` vs `?? undefined`, null trend handling). |

**Flow**: Frontend Developer checks all views display new data → React Expert audits edge cases → both report any display bugs.

**Output**: Frontend verification report with screenshots/descriptions of correct rendering or bugs found.

---

### 46. Regression Test Suite for New Template Families

| Agent Name    | subagent_type     | Can Edit? | Tools                               | Role on Team                                                                                                                                                                                                                                                                                                                                                |
| ------------- | ----------------- | --------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Test Engineer | `test-engineer` | Yes       | Read, Write, Edit, Bash, Grep, Glob | Write tests for: (1) new supplemental mappings extract correct values from test fixtures, (2) auto-mapper produces correct tier assignments for each template family, (3) deferred groups can be extracted via API without errors, (4) cross-group validation catches known conflict scenarios, (5) property reconciliation handles the new property names. |
| Tester        | `tester`        | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full backend + frontend test suite after new tests are added. Verify no regressions. Report final test count delta.                                                                                                                                                                                                                                     |

**Flow**: Test Engineer writes tests per category → Tester runs full suite → both confirm all tests pass and coverage increased.

**Test Fixtures Needed**: At minimum, one representative `.xlsx` file per new template family, stored in `backend/tests/fixtures/` with known cell values for spot-checking.

**Output**: Test count before and after. All tests passing.

---

### 47. Grouping Expansion Final Gate

| Agent Name           | subagent_type            | Can Edit? | Tools                               | Role on Team                                                                                                                                                                                                |
| -------------------- | ------------------------ | --------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reviewer             | `reviewer`             | Yes       | Read, Edit, Grep, Glob, Bash        | Review all code changes: new mappings, pipeline modifications, test additions, any conflict resolution logic. Check for quality, consistency, and edge cases.                                               |
| Tester               | `tester`               | Yes       | Read, Write, Edit, Bash, Grep, Glob | Run full backend + frontend test suite one final time. Report total test count and pass rate.                                                                                                               |
| Production Validator | `production-validator` | Yes       | All tools                           | Verify:`npm run build` succeeds, `npx tsc --noEmit` passes, backend starts cleanly, extraction endpoints respond, all 41 groups (30 active + 9 formerly deferred + 2 investigated) have correct status. |

**Flow**: All three work in parallel → Reviewer checks code quality → Tester verifies all tests pass → Production Validator confirms build + startup → team produces final go/no-go report.

**Output**: Final verification report with go/no-go recommendation.

---

## Quick Reference: Grouping Expansion Teams

| #  | Team Name                          | Agents                                 | Phase        | Parallel?  | Purpose                                          |
| -- | ---------------------------------- | -------------------------------------- | ------------ | ---------- | ------------------------------------------------ |
| 39 | Deferred Group Structural Analysis | Explorer, Researcher                   | Analysis     | Yes        | Classify template families, rank by value        |
| 40 | Excluded Group Investigation       | Explorer, Coder                        | Analysis     | Yes        | Determine if excluded files are salvageable      |
| 41 | Auto-Mapping Bootstrap             | Backend Architect, Researcher          | Mapping      | Sequential | Run auto-mapper, manually locate unmapped fields |
| 42 | Supplemental Mapping Integration   | Coder, Tester                          | Mapping      | Sequential | Integrate new mappings, dry-run verify           |
| 43 | Deferred Group Extraction          | Coder, Tester                          | Extraction   | Sequential | Run live extraction group-by-group               |
| 44 | Cross-Group Validation             | Backend Architect, Coder               | Validation   | Sequential | Resolve property collisions and data conflicts   |
| 45 | Frontend Display Verification      | Frontend Developer, React Expert       | Verification | Yes        | Confirm UI displays expanded data correctly      |
| 46 | Regression Test Suite              | Test Engineer, Tester                  | Hardening    | Sequential | Write tests for new template families            |
| 47 | Final Gate                         | Reviewer, Tester, Production Validator | Final        | Yes        | Go/no-go quality gate                            |

---

## Execution Plan: Step-by-Step Instructions

### Overview

The teams are organized into **6 phases**. Within each phase, teams that can run in parallel should be launched together. Phases are sequential — each depends on the previous phase's output.

```
PHASE A: ANALYSIS (Teams 39-40)              <- What template families exist? Are excluded files salvageable?
    |
PHASE B: MAPPING (Teams 41-42)              <- Create cell mappings for each new template family
    |
PHASE C: EXTRACTION (Team 43)               <- Run extraction on deferred groups
    |
PHASE D: VALIDATION (Teams 44-45)           <- Resolve conflicts, verify frontend display
    |
PHASE E: HARDENING (Team 46)                <- Write regression tests
    |
PHASE F: FINAL GATE (Team 47)               <- Quality gate before declaring complete
```

---

### Phase A: Analysis (Teams 39, 40 — PARALLEL)

**What**: Understand the structural landscape of deferred and excluded groups. Both teams run simultaneously.

**Launch Command** (single message with 2 Task calls):

```
Task("Deferred Group Analysis", "Team 39: Read backend/data/extraction_groups/groups.json — find the 'deferred_groups' section. For each of the 9 deferred groups: (1) extract group_name, file_count, sheet names from representative file fingerprints, (2) compare sheet names against the active group template (sheets like 'Error Checker', 'Summary', 'Cash Flow', 'Returns Metrics Summary', 'Assumptions Summary'), (3) compute what percentage of production sheets exist in each deferred group, (4) identify what EXTRA sheets exist that aren't in production, (5) classify each group into a template family. Also read backend/app/extraction/reference_mapper.py to understand the 4-tier auto-mapping system. Produce a Template Family Classification Report.", "researcher")

Task("Excluded Group Investigation", "Team 40: Read backend/data/extraction_groups/groups.json — find the 'excluded_groups' or files with population_status='error'. For each excluded file: (1) try to open it with a Python script using pyxlsb or openpyxl, (2) report if it opens, what sheets exist, if data is present, (3) determine if it's a real UW model or a non-model file, (4) recommend: reclassify as deferred, confirm exclusion, or flag as corrupt. Use bash to run the diagnostic script.", "coder")
```

**Decision Point**: Review the Template Family Classification Report. Determine which template families to prioritize (highest file count × most valuable data fields). The user may want to focus on the 2-3 largest families first.

**Expected Duration**: 10-20 minutes (both parallel).

---

### Phase B: Mapping (Teams 41, 42 — SEQUENTIAL)

**What**: Create cell mappings for each new template family. Team 41 runs first (auto-mapping + manual identification), then Team 42 integrates.

**Pre-Condition**: Phase A Template Family Classification Report reviewed and priorities approved.

**Launch Command** (sequential — run 41 first, then 42):

```
Task("Auto-Map Bootstrap", "Team 41: For each prioritized deferred template family from Phase A: (1) use the representative file's fingerprint to run auto_map_group() from backend/app/extraction/reference_mapper.py against the production mappings in backend/app/extraction/cell_mapping.py, (2) report Tier 1-4 counts (how many fields auto-mapped vs unmapped), (3) for unmapped fields, open the representative .xlsb/.xlsx file and locate where cap rate, IRR, MOIC, unit count, purchase price, and other key fields are stored (sheet name + cell address), (4) create a supplemental mapping dict for each family (same format as the GOING_IN_CAP_RATE override in backend/app/api/v1/endpoints/extraction/common.py). Focus on the 6 supplemental financial fields first: GOING_IN_CAP_RATE, T3_RETURN_ON_COST, UNLEVERED_RETURNS_IRR, UNLEVERED_RETURNS_MOIC, LEVERED_RETURNS_IRR, LEVERED_RETURNS_MOIC.", "backend-development:backend-architect")

Task("Integrate Mappings", "Team 42: Take the supplemental mapping dicts from Team 41 and integrate them into the extraction pipeline. Options: (a) extend the supplemental overrides in common.py with per-family conditionals, or (b) create per-family mapping JSON files in backend/data/extraction_groups/{family_name}/ and update group_pipeline.py to load them. After integration, run dry-run extraction for each deferred group: POST /extraction/grouping/extract/{name} with dry_run=true. Verify extracted value counts are reasonable. Run full backend test suite to confirm no regressions.", "coder")
```

**Decision Point**: Review dry-run results. If extracted value counts are significantly lower than active groups (~1,169 per file), investigate which fields are still unmapped.

**Expected Duration**: 20-40 minutes total (sequential).

---

### Phase C: Extraction (Team 43 — SEQUENTIAL)

**What**: Run live extraction on validated deferred groups, one at a time.

**Pre-Condition**: Phase B dry-runs show reasonable extraction counts.

**Launch Command**:

```
Task("Extract Deferred Groups", "Team 43: For each deferred group that passed dry-run validation: (1) Approve: POST /extraction/grouping/approve/{name}, (2) Extract: POST /extraction/grouping/extract/{name} with dry_run=false, (3) After each: query ExtractedValue for the group's properties, verify property_id backfill, verify Property/Deal records created with correct stage, spot-check 2-3 financial values against source files. Use admin auth (matt@bandrcapital.com / Wildcats777!!). Process groups in priority order (largest families first). Report per-group: files_processed, values_extracted, properties_created.", "coder")
```

**Expected Duration**: 10-30 minutes depending on group count.

---

### Phase D: Validation (Teams 44, 45 — PARALLEL)

**What**: Cross-group validation and frontend verification. Both teams run simultaneously.

**Pre-Condition**: Phase C extraction completed.

**Launch Command** (single message with 2 Task calls):

```
Task("Cross-Group Validation", "Team 44: Run POST /extraction/grouping/validate to check for property name collisions between newly extracted deferred groups and existing active groups. Also query ExtractedValue for duplicate (property_name, field_name) tuples across different extraction runs. For any conflicts: (1) if same property appears in multiple groups, verify values are consistent, (2) if values differ, flag for manual review — do NOT auto-resolve financial data, (3) if property names are similar but not identical, run reconcile_property_names() to determine if they should be merged. Report all conflicts and resolutions.", "backend-development:backend-architect")

Task("Frontend Verification", "Team 45: Verify newly extracted properties from deferred groups appear correctly in the frontend: (1) check that GroupPipelineTab shows updated group counts (deferred → active), (2) verify new properties appear in Deals kanban board with correct stage, (3) check property detail pages show financial metrics from extraction, (4) verify deal comparison works with new properties, (5) check for rendering bugs: null values showing as '0.0%', missing N/A display, trend calculation errors. Review Zod schemas in src/lib/api/schemas/ and components in src/features/deals/ and src/features/extraction/.", "frontend-developer")
```

**Expected Duration**: 10-15 minutes (both parallel).

---

### Phase E: Hardening (Team 46 — SEQUENTIAL)

**What**: Write regression tests for new template families.

**Pre-Condition**: Phase D validation clean.

**Launch Command**:

```
Task("Write Grouping Expansion Tests", "Team 46: Write tests covering: (1) auto-mapper produces correct tier assignments for each new template family (test with fixture fingerprints), (2) supplemental mappings extract correct values from test fixtures (create minimal .xlsx fixtures with known cell values per family), (3) deferred group extraction via API returns expected response shape, (4) cross-group validation detects known conflict scenarios (duplicate property names across groups), (5) property name reconciliation handles the naming patterns in deferred groups. Add tests to backend/tests/test_extraction/ and backend/tests/test_api/. After writing, run: conda run -n dashboard-backend pytest backend/tests/ -v AND npm run test. Report test count before and after.", "test-engineer")
```

**Expected Duration**: 15-25 minutes.

---

### Phase F: Final Gate (Team 47 — ALL PARALLEL)

**What**: Final quality gate.

**Pre-Condition**: Phase E tests all pass.

**Launch Command** (single message with 3 Task calls):

```
Task("Code Review", "Team 47 - Reviewer: Review all code changes from this grouping expansion effort: new mappings, pipeline modifications, conflict resolution logic, new tests. Check for code quality, consistent patterns, no hardcoded values, proper error handling.", "reviewer")

Task("Full Test Suite", "Team 47 - Tester: Run the complete test suite: (1) conda run -n dashboard-backend pytest backend/tests/ -v (2) npm run test. Report total test count and pass rate. Both must be 100% pass.", "tester")

Task("Production Readiness", "Team 47 - Validator: Verify: (1) npm run build succeeds with zero errors, (2) npx tsc --noEmit passes, (3) backend starts cleanly, (4) grouping pipeline status shows all groups (active + formerly deferred) have correct status, (5) extraction endpoints respond. Confirm deployment-ready.", "production-validator")
```

**Decision Point**: All three must report clean for the task to be considered complete.

**Expected Duration**: 5-10 minutes (all parallel).

---

## Summary: Total Agent Count for Grouping Expansion

| Phase           | Teams             | Unique Agent Types                                             | Total Agent Instances        |
| --------------- | ----------------- | -------------------------------------------------------------- | ---------------------------- |
| A: Analysis     | 39, 40            | 3 (Explore, researcher, coder)                                 | 4                            |
| B: Mapping      | 41, 42            | 3 (backend-architect, researcher, coder, tester)               | 4                            |
| C: Extraction   | 43                | 2 (coder, tester)                                              | 2                            |
| D: Validation   | 44, 45            | 3 (backend-architect, coder, frontend-developer, react-expert) | 4                            |
| E: Hardening    | 46                | 2 (test-engineer, tester)                                      | 2                            |
| F: Final Gate   | 47                | 3 (reviewer, tester, production-validator)                     | 3                            |
| **Total** | **9 teams** | **9 unique types**                                       | **19 agent instances** |

**Optimal execution with full parallelism**: ~70-140 minutes + review time between phases.

---

## Troubleshooting Guide

### Common Issues and Resolution

| Issue                                          | Symptom                                           | Team That Catches It | Resolution                                                                                                           |
| ---------------------------------------------- | ------------------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Deferred group has no usable fingerprint       | Empty sheets list in `groups.json`              | Team 39              | Re-run fingerprinting for that group's files:`POST /extraction/grouping/fingerprint` with explicit file_paths      |
| Auto-mapper returns 0 Tier 1 matches           | Group template has entirely different sheet names | Team 41              | Skip auto-mapping; all fields need manual cell location from representative file                                     |
| Excluded file won't open                       | pyxlsb/openpyxl raises exception                  | Team 40              | Confirm file isn't corrupted by OneDrive sync. Try re-downloading from SharePoint                                    |
| Property name collision                        | Same property in deferred + active group          | Team 44              | Use `reconcile_property_names()` to determine if same property or different. If same, merge. If different, rename. |
| Dry-run shows very low value count             | Many fields unmapped for this template            | Team 42              | Check auto-mapper output — likely need more supplemental mappings for this family                                   |
| Frontend shows "N/A" for fields that have data | Zod schema not parsing the field                  | Team 45              | Check if field name in API response matches Zod schema key. May need to add new field to Zod schema.                 |
| Template family has only 1-2 files             | Low ROI for creating dedicated mapping            | Team 39              | Deprioritize — focus on families with 5+ files first                                                                |

### If a Deferred Group Can't Be Mapped

Some deferred groups may use templates so different that creating mappings is impractical. In this case:

1. Document why the group can't be mapped (e.g., "template uses calculated cell references instead of fixed addresses")
2. Move the group from "deferred" to "excluded" with a documented reason
3. Consider if the data could be manually entered instead of automatically extracted

---

---

# Dashboard Integrity & Regression Prevention — Full-Stack Review with Financial Validation

A dedicated set of agent teams designed to systematically audit, fix, and regression-proof every dashboard page across the full stack: frontend rendering → API response → backend logic → PostgreSQL database. These teams include a **Financial Analyst agent** with domain expertise in multifamily real estate underwriting — capable of spotting values that are technically valid but contextually wrong (e.g., a 45% cap rate, a negative MOIC, or a stabilized NOI lower than T-12 actuals).

**Task Summary**: Conduct a page-by-page, component-by-component review of the entire dashboard. For each page: verify data flows correctly from database → API → frontend, confirm financial metrics are contextually accurate, fix any rendering or data bugs found, and write regression tests that permanently prevent fixed issues from returning.

**Why This Needs Dedicated Teams**: The recurring problem is that fixes applied in isolation don't stick. A value gets corrected in the backend, but the Zod schema silently coerces it. A component gets fixed, but a shared hook re-introduces the bug on re-render. A database query gets optimized, but a different endpoint uses the old query pattern. This pipeline treats the dashboard as a single integrated system — database to pixel — and locks every fix with a regression test before moving on.

**Root Cause Analysis Framework**: Before fixing any issue, agents must classify the regression mechanism:

| Regression Type | Example | Prevention |
| --- | --- | --- |
| **Schema Drift** | Backend adds nullable field, Zod schema defaults to `0` instead of `undefined` | Contract test asserting Pydantic ↔ Zod field parity |
| **Query Divergence** | Two endpoints query same data with different JOINs, producing different values | Shared query function with single source of truth |
| **Component State Leak** | Zustand store retains stale data across page navigations | Store reset on unmount + test asserting clean state |
| **Silent Coercion** | `Number(null)` → `0`, displayed as "0.0%" instead of "N/A" | Zod `.nullable().optional()` + `?? undefined` pattern |
| **Enrichment Gap** | `_enrich_deals_with_extraction()` skips a field, API returns `null`, frontend shows stale cached value | Enrichment coverage test + API response assertion |
| **Migration Side Effect** | Alembic migration changes column type, existing rows not backfilled | Migration test with seed data asserting backfill |

---

## Dashboard Review Teams

### 48. Full-Stack Data Flow Tracer

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Explorer | `Explore` | **No** | All except Edit/Write | For every dashboard page, trace the complete data path: which React component renders it → which hook/store fetches data → which API endpoint is called → which CRUD function queries the DB → which SQLAlchemy model/query produces the result. Produce a **Data Flow Map** per page. |
| Backend Architect | `backend-development:backend-architect` | Yes | All tools | Cross-reference each data flow path for consistency: does the Pydantic response schema match the actual query result? Does `_enrich_deals_with_extraction()` populate every field the frontend expects? Are there endpoints returning the same entity with different field sets? |

**Flow**: Explorer maps every page's data flow from component → API → DB → produces a comprehensive Data Flow Map → Backend Architect audits each path for schema/query inconsistencies → team produces a **Data Flow Audit Report** listing every discontinuity where data could be lost, coerced, or silently dropped between layers.

**Dashboard Pages to Map** (all pages in the application):

| Page | Key Components | Primary API Endpoints | Critical Data Fields |
| --- | --- | --- | --- |
| Deals Kanban | `DealsKanbanBoard`, `DealCard` | `GET /deals/` | stage, cap_rate, purchase_price, unit_count |
| Deal Detail | `DealDetailPage`, `KPICard`, `FinancialSummary` | `GET /deals/{id}` | All financial metrics, extraction values, LP returns |
| Deal Comparison | `ComparisonView`, `ComparisonTable` | `GET /deals/compare` | Side-by-side metrics across multiple deals |
| Properties List | `PropertiesTable` | `GET /properties/` | address, vintage, units, market, submarket |
| Property Detail | `PropertyDetailPage` | `GET /properties/{id}` | All property attributes + linked deal data |
| Sales Analysis | `SalesAnalysisDashboard` | `GET /market-data/sales/` | price_per_unit, cap_rate, sale_date, submarket |
| Construction Pipeline | `ConstructionDashboard` | `GET /market-data/construction/` | units_planned, units_under_construction, delivery_date |
| Market Data | `MarketDataDashboard` | `GET /market-data/` | rent_growth, occupancy, absorption, supply |
| Extraction Dashboard | `ExtractionDashboard`, `GroupPipelineTab` | `GET /extraction/`, `GET /extraction/grouping/` | run_status, files_processed, extracted_values |

**Output**: Data Flow Map (per page) + Data Flow Audit Report (all discontinuities).

---

### 49. PostgreSQL Data Integrity Audit

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Postgres Expert | `postgres-expert` | Yes | Bash(psql, pg_dump, pg_restore), Read, Grep, Edit | Deep audit of the PostgreSQL database: check for orphaned records, NULL values in required fields, referential integrity violations, index coverage on frequently-queried columns, and data type mismatches between SQLAlchemy models and actual column types. |
| Explorer | `Explore` | **No** | All except Edit/Write | Map every SQLAlchemy model to its corresponding database table. Find all foreign key relationships. Identify any model fields that don't have a corresponding column (or vice versa). Catalog all indexes. |

**Flow**: Explorer maps SQLAlchemy models → DB tables → identifies model/table mismatches → Postgres Expert runs integrity queries directly against the database → team produces a **Database Integrity Report**.

**Integrity Checks**:

1. **Referential integrity**: Every `deal.property_id` points to a valid Property record. Every `extracted_value.property_id` is backfilled.
2. **NULL audit**: Fields that should never be NULL (property name, deal stage, created_at) — query for violations.
3. **Data type validation**: Numeric fields (cap_rate, purchase_price, unit_count) contain valid numbers, not strings or NaN.
4. **Orphaned records**: ExtractedValues without a parent Property. Deals without a parent Property. Properties with no Deal.
5. **Duplicate detection**: Duplicate property names (exact or fuzzy), duplicate deals for the same property, duplicate extraction values for the same (property, field_name) pair.
6. **Index coverage**: Columns used in WHERE clauses and JOINs across all CRUD functions — do they have indexes?
7. **Stale data**: Records with `updated_at` significantly older than `created_at` of newer records (suggests they weren't updated during re-extraction).

**Output**: Database Integrity Report with pass/fail per check, query results for violations, and recommended fixes.

---

### 50. Backend API Response Audit

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Backend Architect | `backend-development:backend-architect` | Yes | All tools | For every API endpoint that serves dashboard data: (1) read the route handler, (2) trace the CRUD call, (3) read the Pydantic response schema, (4) make a real API call and capture the response, (5) compare the actual response against the Pydantic schema — field by field. Flag: missing fields, extra fields, wrong types, null where non-null expected. |
| Tester | `tester` | Yes | Read, Write, Edit, Bash, Grep, Glob | Write automated contract tests that call each endpoint and assert the response matches the Pydantic schema exactly. These tests become the permanent regression guard for API responses. |

**Flow**: Backend Architect audits each endpoint's actual response vs declared schema → flags all discrepancies → Tester writes contract tests for every endpoint → tests become the regression firewall.

**Critical Endpoints to Audit**:

| Endpoint | Response Schema | Known Risk Areas |
| --- | --- | --- |
| `GET /deals/` | `DealListResponse` | `_enrich_deals_with_extraction()` adds ~26 fields — are all populated? |
| `GET /deals/{id}` | `DealDetailResponse` | LP returns (IRR, MOIC), cap rate, supplemental fields |
| `GET /properties/` | `PropertyListResponse` | Market/submarket assignment, vintage, unit_count |
| `GET /properties/{id}` | `PropertyDetailResponse` | Linked deal data, extraction values |
| `GET /market-data/sales/` | `SalesDataResponse` | Aggregations, date filtering, submarket grouping |
| `GET /market-data/construction/` | `ConstructionResponse` | Classification counts, delivery timeline |
| `GET /deals/compare` | `ComparisonResponse` | Cross-deal metrics alignment |

**Output**: API Response Audit Report + contract test suite (one test per endpoint minimum).

---

### 51. Frontend Rendering & State Management Audit

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| React Expert | `react-expert` | Yes | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Audit every dashboard component for rendering correctness: (1) Zod schema transforms match backend response shape, (2) null/undefined handling — no `?? 0` bugs, (3) conditional rendering guards prevent crashes on missing data, (4) Zustand store state doesn't leak between page navigations, (5) useEffect dependencies are correct (no stale closures), (6) trend/delta calculations handle edge cases (division by zero, null previous period). |
| Frontend Developer | `frontend-developer` | Yes | Write, Read, MultiEdit, Bash, Grep, Glob | Audit visual rendering: (1) KPICards display correct units (%, $, x, units), (2) tables sort correctly on numeric columns (not string sort), (3) charts render with correct axis labels and scales, (4) empty states display "N/A" or appropriate placeholder (not "0", "0.0%", "NaN", or blank), (5) responsive layout doesn't break data display on smaller viewports. |

**Flow**: React Expert audits data flow within components (Zod → store → props → render) → Frontend Developer audits visual output and formatting → both produce a **Component Rendering Report** per page with every bug found and its root cause classification (schema drift, silent coercion, state leak, etc.).

**Known Bug Patterns to Check (from project history)**:

| Pattern | What Goes Wrong | Correct Fix |
| --- | --- | --- |
| `value ?? 0` | Missing value shows as "0.0%" instead of "N/A" | `value ?? undefined` + conditional render |
| `trend && trend > 0` | `trend === 0` is falsy, shows wrong indicator | `trend !== undefined && trend !== null` |
| `Number(null)` → `0` | Null from API becomes zero in component | Check for null before conversion |
| `.toFixed(2)` on undefined | Runtime crash | Optional chaining: `value?.toFixed(2)` |
| Zustand store not reset | Stale deal data shows on different deal's page | `useEffect(() => store.reset(), [dealId])` |
| `useMemo` missing dep | Derived metric doesn't update when source changes | Include all source fields in dependency array |

**Output**: Component Rendering Report per page + fix list with root cause classification.

---

### 52. Financial Accuracy & Contextual Validation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Researcher | `researcher` | Yes | All tools | **Acts as Financial Analyst with multifamily RE domain expertise.** Reviews every financial metric displayed on the dashboard for contextual accuracy. This agent doesn't just check "is it a number?" — it checks "does this number make sense given everything else we know about this deal?" Uses cross-referencing, ratio analysis, and domain heuristics to flag values that are technically valid but contextually wrong. |
| Backend Architect | `backend-development:backend-architect` | Yes | All tools | When the Financial Analyst flags a suspicious value, trace it back through the stack: API response → CRUD query → database record → extraction source. Determine WHERE the value went wrong (extraction error, enrichment bug, query JOIN issue, or genuine bad data in the source file). |

**Flow**: Researcher (as Financial Analyst) reviews all financial metrics across all dashboard pages using domain heuristics → flags contextually suspicious values → Backend Architect traces each flagged value to its source → team produces a **Financial Accuracy Report** with root cause for each anomaly.

**Domain Heuristics for Contextual Validation**:

| Metric | Valid Range | Contextual Cross-Checks |
| --- | --- | --- |
| **Cap Rate** | 3.0% – 8.0% (Phoenix Class B) | Must be lower than trailing cap rate if value-add. If cap rate > 10%, likely extraction error or non-stabilized NOI used. |
| **Purchase Price** | $5M – $100M (100+ units) | Price per unit should be $80K–$250K for Phoenix Class B. If price/unit < $50K or > $400K, flag. |
| **Unit Count** | 100 – 800 | B&R targets 100+ units. If unit count < 50, likely wrong property or extraction error. |
| **LP IRR** | 12% – 25% (target) | If IRR < 8%, deal likely doesn't meet investment criteria — may be a dead deal showing active. If IRR > 40%, likely extraction from wrong cell. |
| **LP MOIC** | 1.5x – 2.5x (typical 5-year hold) | MOIC < 1.0x means loss — should correlate with Dead/Passed stage. MOIC > 4.0x on a 5-year hold implies >30% IRR — cross-check against IRR. |
| **T3 Return on Cost** | 5.0% – 8.0% | Should exceed going-in cap rate (value-add thesis). If RoC < cap rate, the renovation thesis doesn't work — flag. |
| **NOI** | Proportional to units × $8K–$14K/unit/year | If NOI/unit < $5K or > $20K, flag. Stabilized NOI should exceed T-12 NOI (value-add assumption). |
| **Vintage (Year Built)** | 1965 – 2000 (Class B target) | If vintage > 2010, it's likely Class A — verify deal thesis. If vintage < 1960, CapEx risk is elevated — verify renovation budget. |
| **Rent/Unit** | $900 – $1,800/mo (Phoenix Class B) | Should correlate with submarket. Tempe/Scottsdale higher than West Phoenix. If rent > $2,500, likely Class A misclassification. |
| **Basis (Total Cost)** | Purchase + Renovation + Closing | Basis should be 10-30% above purchase price (renovation premium). If basis = purchase price, renovation budget is missing. |
| **DSCR** | 1.20 – 1.50 (lender minimum ~1.25) | DSCR < 1.0 means negative cash flow — deal can't service debt. Flag immediately. DSCR > 2.0 is unusual — may indicate conservative underwriting or error. |

**Cross-Deal Consistency Checks**:

1. Deals in the same submarket should have cap rates within ±150bps of each other (unless different vintage/condition).
2. Active Review deals should generally have better returns than Initial Review deals (survivorship bias — worse deals get killed).
3. Under Contract / Closed deals should have complete financial profiles — any null financial fields are data gaps.
4. Dead/Passed deals with strong returns metrics may have been incorrectly staged (or metrics are from a different revision).

**Output**: Financial Accuracy Report — per-deal, per-metric: value, contextual assessment (plausible/suspicious/likely_error), cross-reference evidence, and source trace if flagged.

---

### 53. Regression Root Cause Analysis

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Explorer | `Explore` | **No** | All except Edit/Write | Search git history for files that have been edited 3+ times for the same type of fix (e.g., the same component fixed for null handling repeatedly). Identify **regression hot spots** — files/functions where bugs keep returning. Cross-reference against test coverage to find unprotected hot spots. |
| Refactoring Expert | `refactoring-expert` | Yes | Read, Grep, Glob, Edit, MultiEdit, Bash | For each regression hot spot: analyze WHY the fix didn't stick. Classify the root cause (schema drift, query divergence, state leak, etc.). Design a **structural fix** that prevents the regression class, not just the symptom. This may involve extracting shared utilities, adding type guards, or restructuring data flow. |

**Flow**: Explorer identifies regression hot spots from git history + test gaps → Refactoring Expert analyzes each hot spot's regression mechanism → designs structural fixes that eliminate the regression class → team produces a **Regression Root Cause Report** with prioritized structural fixes.

**Regression Hot Spot Detection Queries**:

1. Files with 5+ commits touching the same function/component
2. Test files that have been updated to "fix" assertions (changing expected values rather than fixing code)
3. Components where `?? 0` or `?? undefined` has been toggled back and forth
4. Backend endpoints where the response schema has changed 3+ times
5. Zustand stores where reset logic has been added/removed/re-added

**Output**: Regression Root Cause Report — per hot spot: file, function, regression count, root cause class, structural fix recommendation.

---

### 54. Page-by-Page Fix & Lock Cycle

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Coder | `coder` | Yes | All tools | Fix all issues found by Teams 48-53 for a single dashboard page at a time. Apply fixes in dependency order: database → backend query → Pydantic schema → API endpoint → Zod schema → Zustand store → React component. Never fix the frontend without verifying the backend is correct first. |
| Test Engineer | `test-engineer` | Yes | Read, Write, Edit, Bash, Grep, Glob | **Immediately after each fix**, write a regression test that asserts the correct behavior. The test must fail if the fix is reverted. Tests span the full stack: DB query returns correct data, API response has correct fields, Zod parse produces correct shape, component renders correct output. |
| Tester | `tester` | Yes | Read, Write, Edit, Bash, Grep, Glob | After all fixes + regression tests for a page are complete, run the FULL test suite (backend + frontend). Only proceed to the next page if all tests pass. If a fix for page N breaks page M, the Coder must resolve the cross-page dependency before moving on. |

**Flow**: For each dashboard page (in priority order): Coder fixes all issues (bottom-up: DB → API → frontend) → Test Engineer writes regression test for each fix → Tester runs full suite → team only advances to next page when current page is green.

**Page Priority Order** (based on user-facing impact and regression frequency):

| Priority | Page | Reason |
| --- | --- | --- |
| 1 | Deal Detail | Highest data density, most financial metrics, most regression-prone |
| 2 | Deals Kanban | Primary navigation, card data must match detail page |
| 3 | Deal Comparison | Cross-deal data must be consistent |
| 4 | Properties List/Detail | Foundation data for all deal views |
| 5 | Sales Analysis | Market data dashboard, independent data source |
| 6 | Construction Pipeline | Market data dashboard, independent data source |
| 7 | Market Data | Aggregated metrics dashboard |
| 8 | Extraction Dashboard | Admin-facing, lower user impact |

**Fix-and-Lock Protocol** (applied to every single fix):

```
1. IDENTIFY: What's wrong? (from Teams 48-53 reports)
2. TRACE: Where does the wrong value originate? (DB → API → frontend)
3. FIX: Apply fix at the correct layer (not the symptom layer)
4. TEST: Write regression test that FAILS if fix is reverted
5. VERIFY: Run full test suite — green before proceeding
6. LOCK: The regression test is the permanent guard
```

**Output**: Per-page fix report: issues fixed, tests added, test suite status.

---

### 55. Cross-Page Consistency Verification

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| React Expert | `react-expert` | Yes | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Verify that the same entity (deal, property) displays identical values across every page where it appears. A deal's cap rate on the Kanban card MUST match the Deal Detail page MUST match the Comparison view. If any page shows a different value for the same field, trace why (different API endpoint? different query? cached stale data? different Zod transform?). |
| Tester | `tester` | Yes | Read, Write, Edit, Bash, Grep, Glob | Write cross-page consistency tests: fetch the same entity from multiple endpoints, assert all return identical values for shared fields. These tests catch query divergence — the #1 cause of "I fixed it on one page but it's wrong on another." |

**Flow**: React Expert checks every entity across all views where it appears → flags any value inconsistency → traces the root cause (different endpoint, different query, stale cache) → Tester writes cross-page consistency tests → tests prevent future divergence.

**Cross-Page Consistency Matrix**:

| Field | Kanban Card | Deal Detail | Comparison | Properties |
| --- | --- | --- | --- | --- |
| cap_rate | DealCard | KPICard | ComparisonTable | — |
| purchase_price | DealCard | FinancialSummary | ComparisonTable | — |
| unit_count | DealCard | KPICard | ComparisonTable | PropertiesTable |
| lp_irr | DealCard | KPICard | ComparisonTable | — |
| lp_moic | DealCard | KPICard | ComparisonTable | — |
| address | DealCard | Header | ComparisonTable | PropertiesTable |
| stage | Column position | Badge | ComparisonTable | — |

Every cell in this matrix must show the same value for the same deal/property. Any discrepancy is a bug.

**Output**: Cross-Page Consistency Report + consistency test suite.

---

### 56. Dashboard Integrity Final Gate

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Reviewer | `reviewer` | Yes | Read, Edit, Grep, Glob, Bash | Review ALL code changes made during Teams 48-55. Check for: code quality, consistent patterns, no hardcoded values, proper error handling, no shortcuts that will regress. Specifically verify that every fix has a corresponding regression test. |
| Tester | `tester` | Yes | Read, Write, Edit, Bash, Grep, Glob | Run the complete test suite: backend pytest + frontend vitest + any E2E tests. Report total test count before and after (should increase significantly). ALL tests must pass. |
| Production Validator | `production-validator` | Yes | All tools | Verify: `npm run build` succeeds, `npx tsc --noEmit` passes, backend starts cleanly, all dashboard pages load without console errors, all API endpoints respond with valid data. |
| Researcher | `researcher` | Yes | All tools | **Final Financial Sanity Check**: Re-run the contextual validation from Team 52 against the now-fixed data. Confirm that all previously-flagged values have been corrected or documented. Verify no new contextual anomalies were introduced by fixes. |

**Flow**: All four work in parallel → Reviewer checks code quality and test coverage → Tester runs full suite → Production Validator confirms build and runtime → Researcher does final financial sanity check → team produces **Final Dashboard Integrity Report** with go/no-go recommendation.

**Output**: Final Dashboard Integrity Report — test count delta, financial accuracy confirmation, build status, go/no-go.

---

## Quick Reference: Dashboard Integrity Teams

| # | Team Name | Agents | Phase | Parallel? | Purpose |
| --- | --- | --- | --- | --- | --- |
| 48 | Full-Stack Data Flow Tracer | Explorer, Backend Architect | Discovery | Yes | Map data flow per page, find discontinuities |
| 49 | PostgreSQL Data Integrity Audit | Postgres Expert, Explorer | Discovery | Yes | Database-level integrity checks |
| 50 | Backend API Response Audit | Backend Architect, Tester | Discovery | Yes | Verify API responses match schemas |
| 51 | Frontend Rendering Audit | React Expert, Frontend Developer | Discovery | Yes | Component rendering and state bugs |
| 52 | Financial Accuracy Validation | Researcher, Backend Architect | Discovery | Yes | Domain-expert contextual validation |
| 53 | Regression Root Cause Analysis | Explorer, Refactoring Expert | Discovery | Yes | Identify why fixes don't stick |
| 54 | Page-by-Page Fix & Lock | Coder, Test Engineer, Tester | Fix | Sequential | Fix issues + write regression tests per page |
| 55 | Cross-Page Consistency | React Expert, Tester | Verification | Sequential | Same entity shows same values everywhere |
| 56 | Final Gate | Reviewer, Tester, Production Validator, Researcher | Final | Yes | Go/no-go with financial sanity check |

---

## Execution Plan: Step-by-Step Instructions

### Overview

The teams are organized into **4 phases**. Phase 1 runs all discovery teams in parallel. Phase 2 fixes page-by-page with immediate regression locking. Phase 3 verifies cross-page consistency. Phase 4 is the final quality gate.

```
PHASE 1: DISCOVERY (Teams 48-53)        <- What's broken? Where? Why does it regress?
    |
PHASE 2: FIX & LOCK (Team 54)           <- Fix each page bottom-up, lock with tests
    |
PHASE 3: CONSISTENCY (Team 55)          <- Same data shows same values everywhere
    |
PHASE 4: FINAL GATE (Team 56)           <- Full verification + financial sanity check
```

---

### Phase 1: Discovery (Teams 48, 49, 50, 51, 52, 53 — ALL PARALLEL)

**What**: Comprehensive audit across all layers. All 6 teams run simultaneously because they are independent read/audit tasks.

**Launch Command** (single message with 6 Task calls):

```
Task("Data Flow Mapping", "Team 48: For every dashboard page (Deals Kanban, Deal Detail, Deal Comparison, Properties List/Detail, Sales Analysis, Construction Pipeline, Market Data, Extraction Dashboard), trace the complete data path: React component → hook/store → API endpoint → CRUD function → SQLAlchemy query → DB table. Produce a Data Flow Map per page. Then cross-reference: does each Pydantic response schema match the actual query result? Does _enrich_deals_with_extraction() populate every field the frontend expects? Are there endpoints returning the same entity with different field sets? Flag every discontinuity.", "Explore")

Task("Database Integrity Audit", "Team 49: Run integrity checks against the PostgreSQL database. Check: (1) every deal.property_id → valid Property, (2) every extracted_value.property_id is non-null, (3) no NaN/string values in numeric columns (cap_rate, purchase_price, unit_count), (4) no orphaned ExtractedValues without parent Property, (5) no duplicate (property_name, field_name) pairs, (6) index coverage on columns used in WHERE/JOIN clauses across all CRUD functions, (7) stale records not updated during re-extraction. Use psql or SQLAlchemy queries. Report pass/fail per check with query results.", "postgres-expert")

Task("API Response Audit", "Team 50: For every API endpoint serving dashboard data (GET /deals/, GET /deals/{id}, GET /properties/, GET /properties/{id}, GET /market-data/sales/, GET /market-data/construction/, GET /deals/compare): (1) read the route handler and trace the CRUD call, (2) read the Pydantic response schema, (3) make a real API call (auth with matt@bandrcapital.com / Wildcats777!!), (4) compare actual response vs schema field-by-field. Flag: missing fields, wrong types, null where non-null expected, extra undocumented fields. Produce per-endpoint audit.", "backend-development:backend-architect")

Task("Frontend Rendering Audit", "Team 51: Audit every dashboard component for rendering bugs. Check: (1) Zod schema transforms — any ?? 0 that should be ?? undefined?, (2) null/undefined guards — any .toFixed() or .toLocaleString() on potentially null values?, (3) Zustand store state leaks — does navigating between deals show stale data?, (4) useEffect dependencies — any stale closures?, (5) trend/delta calculations — division by zero handled?, (6) table sorting — numeric columns sorting as strings?, (7) empty states — showing 'N/A' not '0' or blank?, (8) KPICard units — %, $, x, units all correct? Review components in src/features/deals/, src/features/properties/, src/features/market-data/, src/features/extraction/.", "react-expert")

Task("Financial Accuracy Review", "Team 52: Review every financial metric displayed on the dashboard using multifamily RE domain expertise. For each deal visible in the system: (1) Is cap rate in 3-8% range for Phoenix Class B? If >10%, flag. (2) Is price/unit $80K-$250K? (3) Is LP IRR 12-25%? If <8% on active deal or >40%, flag. (4) Is LP MOIC 1.5-2.5x? If <1.0x on active deal, flag. (5) Is T3 Return on Cost > going-in cap rate? If not, value-add thesis broken — flag. (6) Does NOI/unit fall in $8K-$14K/year range? (7) Are deals in same submarket within ±150bps cap rate? (8) Do Under Contract/Closed deals have complete financial profiles? Query the database directly to get all deal financial data. Produce a per-deal Financial Accuracy Report.", "researcher")

Task("Regression Hot Spot Analysis", "Team 53: Search git history (git log --all --oneline --follow) for files edited 3+ times with similar commit messages (e.g., multiple 'fix' commits on same component). Identify regression hot spots — files where bugs keep returning. For each hot spot: (1) classify the regression mechanism (schema drift, query divergence, state leak, silent coercion, enrichment gap), (2) check if the hot spot has test coverage, (3) if tested, check if tests are asserting the right thing (or just passing trivially). Cross-reference with test coverage report. Produce a Regression Root Cause Report with structural fix recommendations.", "Explore")
```

**Decision Point**: Review all 6 reports. Prioritize issues by:
1. **Financial accuracy errors** (wrong numbers shown to users) — fix first
2. **Data flow discontinuities** (data lost between layers) — fix second
3. **Rendering bugs** (correct data, wrong display) — fix third
4. **Regression hot spots** (structural fixes to prevent re-occurrence) — fix as part of each page

**Expected Duration**: 10-20 minutes (all parallel).

---

### Phase 2: Fix & Lock (Team 54 — SEQUENTIAL, page by page)

**What**: Fix all issues from Phase 1, one dashboard page at a time, in priority order. Each fix is immediately locked with a regression test.

**Pre-Condition**: Phase 1 reports reviewed and approved.

**Launch Command** (run for each page in priority order — start with Deal Detail):

```
Task("Fix Deal Detail Page", "Team 54: Using the Phase 1 reports, fix ALL issues found for the Deal Detail page. Fix in dependency order: (1) Database — fix any data integrity issues for deals shown on this page, (2) Backend queries — fix CRUD functions if queries return wrong data, (3) Pydantic schema — fix response schema if fields are wrong/missing, (4) API endpoint — fix enrichment if _enrich_deals_with_extraction() misses fields, (5) Zod schema — fix transforms, nullable handling, (6) Zustand store — fix state management, (7) React components — fix rendering bugs. FOR EACH FIX: immediately write a regression test that FAILS if the fix is reverted. After all fixes for this page, run full test suite: conda run -n dashboard-backend pytest backend/tests/ -v AND npm run test. ALL tests must pass before proceeding to the next page. Report: issues fixed, tests added, test results.", "coder")
```

Repeat for each page: Deals Kanban → Deal Comparison → Properties → Sales Analysis → Construction → Market Data → Extraction Dashboard.

**Critical Rule**: Never proceed to the next page until the current page has:
- All issues from Phase 1 fixed
- A regression test for every fix
- Full test suite passing (backend + frontend)

**Expected Duration**: 30-60 minutes (sequential across all pages).

---

### Phase 3: Cross-Page Consistency (Team 55 — SEQUENTIAL)

**What**: Verify that the same entity shows identical values across every page where it appears.

**Pre-Condition**: Phase 2 complete, all tests passing.

**Launch Command**:

```
Task("Cross-Page Consistency Check", "Team 55: For each deal and property in the system, verify that financial metrics (cap_rate, purchase_price, unit_count, lp_irr, lp_moic) display identically across every view: Kanban card vs Deal Detail vs Comparison view vs Properties table. Method: (1) call GET /deals/ and capture values per deal, (2) call GET /deals/{id} for each deal and compare, (3) call GET /deals/compare with multiple deal IDs and compare, (4) call GET /properties/ and compare linked deal data. Flag any value that differs between endpoints for the same entity. For each discrepancy, trace the root cause (different query? different enrichment? stale cache?). Write cross-page consistency tests that call multiple endpoints and assert field equality. Run full test suite after writing tests.", "react-expert")
```

**Expected Duration**: 10-20 minutes.

---

### Phase 4: Final Gate (Team 56 — ALL PARALLEL)

**What**: Final quality gate with financial sanity re-check.

**Pre-Condition**: Phase 3 complete, all tests passing.

**Launch Command** (single message with 4 Task calls):

```
Task("Code Review", "Team 56 - Reviewer: Review ALL code changes from Phases 2-3. Verify: (1) every fix has a corresponding regression test, (2) fixes are at the correct layer (not symptom-level patches), (3) no hardcoded values or magic numbers, (4) consistent error handling, (5) Zod schemas use .nullable().optional() + ?? undefined pattern consistently, (6) no ?? 0 patterns anywhere. Flag any fix that looks like it could regress.", "reviewer")

Task("Full Test Suite", "Team 56 - Tester: Run the complete test suite: (1) conda run -n dashboard-backend pytest backend/tests/ -v (2) npm run test. Report total test count BEFORE this effort and AFTER. Both must be 100% pass. The test count increase represents the regression firewall.", "tester")

Task("Production Readiness", "Team 56 - Validator: Verify: (1) npm run build succeeds with zero errors, (2) npx tsc --noEmit passes, (3) backend starts cleanly with conda run -n dashboard-backend uvicorn backend.app.main:app, (4) all dashboard pages load without console errors, (5) all API endpoints respond with valid data shapes.", "production-validator")

Task("Financial Sanity Re-Check", "Team 56 - Financial Analyst: Re-run the contextual validation from Phase 1 Team 52 against the now-fixed data. Confirm: (1) all previously-flagged anomalies are resolved or documented, (2) no NEW anomalies introduced by fixes, (3) cross-deal consistency is maintained (same submarket deals within ±150bps cap rate), (4) all Under Contract/Closed deals have complete financial profiles. Produce final Financial Accuracy Confirmation.", "researcher")
```

**Decision Point**: All four must report clean for the effort to be considered complete.

**Expected Duration**: 10-15 minutes (all parallel).

---

## Summary: Total Agent Count for Dashboard Integrity

| Phase | Teams | Unique Agent Types | Total Agent Instances |
| --- | --- | --- | --- |
| 1: Discovery | 48, 49, 50, 51, 52, 53 | 7 (Explore, backend-architect, postgres-expert, tester, react-expert, frontend-developer, researcher, refactoring-expert) | 12 |
| 2: Fix & Lock | 54 | 3 (coder, test-engineer, tester) | 3 (per page, ×8 pages) |
| 3: Consistency | 55 | 2 (react-expert, tester) | 2 |
| 4: Final Gate | 56 | 4 (reviewer, tester, production-validator, researcher) | 4 |
| **Total** | **9 teams** | **11 unique types** | **21+ agent instances** |

**Optimal execution with full parallelism**: ~60-120 minutes + review time between phases.

---

## Troubleshooting Guide

### Common Issues and Resolution

| Issue | Symptom | Team That Catches It | Resolution |
| --- | --- | --- | --- |
| Cap rate shows 0.0% | `?? 0` coercion of null extracted value | Team 51, 52 | Fix Zod schema: `.nullable().optional()` + `?? undefined`. Add KPICard null guard. |
| Different cap rate on Kanban vs Detail | Two endpoints use different queries or enrichment | Team 48, 55 | Trace both endpoints to their CRUD functions. Unify query or use shared function. |
| LP IRR shows 45% (implausible) | Extraction read wrong cell (e.g., unlevered instead of levered) | Team 52 | Verify cell mapping in `common.py` supplemental dict. Fix sheet/cell reference. |
| Property shows on wrong stage | Deal.stage not updated after extraction re-run | Team 49, 50 | Check `sync_extracted_to_properties()` stage assignment logic. |
| Fix reverts after next deployment | No regression test was written for the fix | Team 53, 54 | Write test that asserts correct behavior and FAILS if fix is reverted. |
| Same deal appears twice on Kanban | Duplicate Deal records for same property | Team 49 | Query for duplicate `(property_id, stage)` pairs. Merge or delete duplicate. |
| Financial metrics null on Closed deals | `_enrich_deals_with_extraction()` skips closed stage | Team 48, 52 | Check enrichment function's stage filter. Remove stage restriction if present. |
| Table sorts $1,200,000 before $800,000 | String sort instead of numeric sort | Team 51 | Add `sortingFn: 'basic'` or custom numeric comparator to TanStack column def. |
| Chart Y-axis shows wrong scale | Outlier value (e.g., 45% cap rate) stretches axis | Team 51, 52 | Fix the outlier data (Team 52) + add axis domain clamping as defensive measure. |

### If a Fix Breaks Another Page

1. The Phase 2 protocol requires full test suite pass before advancing to the next page
2. If fixing Page A breaks Page B's tests, the cross-dependency must be resolved immediately
3. Common cause: shared component or shared API endpoint changed
4. Resolution: trace both pages' data flow (Team 48 map), find the shared dependency, fix it to satisfy both consumers
5. Write a cross-page test (Team 55 style) to prevent future cross-page regressions

### If Financial Anomalies Can't Be Resolved

Some values may be genuinely unusual (not errors). For these:
1. Verify the source Excel file contains the same value (extraction is correct)
2. Document the anomaly with a note explaining why it's valid (e.g., "Cabana on 99th — below-market purchase, cap rate reflects 2019 pricing")
3. Consider adding a `data_quality_flag` field to the Deal model for values that have been manually verified despite appearing anomalous

---

---

# Comprehensive System Review & Documentation — Full-Stack Architecture Audit with Living Documentation

A dedicated set of agent teams designed to thoroughly review, inventory, and document every layer of the B&R Capital dashboard application: frontend pages, components, hooks, and stores → backend API endpoints, CRUD functions, schemas, and middleware → PostgreSQL database schema, relationships, migrations, and query patterns → infrastructure configuration and cross-cutting architectural concerns. The output is a complete, accurate, living documentation suite that serves as the definitive reference for the system, plus a prioritized findings report of everything that needs fixing or improving.

**Task Summary**: Conduct an exhaustive, **strictly read-only** inventory and documentation pass across every layer of the application. For each layer: catalog every artifact (component, endpoint, table, migration), document its purpose, inputs/outputs, dependencies, and known patterns. Identify all issues, inconsistencies, bugs, gaps, and improvement opportunities. Produce structured documentation files in `docs/` and a comprehensive **Findings & Recommendations Report** prioritized by severity.

**Strict Read-Only Constraint**: This effort makes **ZERO changes** to the project. No code edits, no config changes, no test additions, no `.env` updates, no docstring fixes — nothing. Every agent operates in read-only mode against the codebase and database. The sole output is documentation files written to `docs/`. All identified issues, bugs, and improvement opportunities are captured in the Findings & Recommendations Report for the developer to act on separately.

**Why This Needs Dedicated Teams**: The dashboard has grown significantly through iterative Claude Code sessions — new endpoints, components, extraction pipeline features, and schema changes have been added rapidly. There is no single authoritative reference documenting what exists, how it's wired, or why specific patterns were chosen. Without this, onboarding a second developer (or even context-switching after a break) requires re-reading source code. These teams produce the reference that doesn't yet exist, and surface everything that needs attention.

**Documentation Principles**:

| Principle | Implementation |
| --- | --- |
| **Strictly read-only** | No file edits, no config changes, no test additions — agents only READ source code and WRITE to `docs/` |
| **Source-of-truth accuracy** | Every documented fact is verified by reading actual source code, not inferred from memory or comments |
| **Structured for lookup** | Documents use consistent heading hierarchy, tables, and cross-references — designed for searching, not sequential reading |
| **Dependency-aware** | Every component, endpoint, and table documents what it depends on and what depends on it |
| **Pattern-explicit** | Recurring patterns (Zod nullable handling, enrichment flow, auth guards) are named and documented once, then referenced |
| **Findings-driven** | Every issue, inconsistency, bug, gap, and improvement opportunity is captured in the Findings & Recommendations Report |
| **Maintenance-ready** | Documentation includes "last verified" markers and instructions for keeping docs current |

---

## System Review & Documentation Teams

### 57. Frontend Architecture Inventory

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Explorer | `Explore` | **No** | All except Edit/Write | Systematically catalog every frontend artifact: pages (route → component mapping), shared components, feature-specific components, custom hooks, Zustand stores, Zod schemas, TypeScript types/interfaces, utility functions, and constants. For each artifact: file path, export name, props/params, dependencies (imports), and dependents (what imports it). |
| React Expert | `react-expert` | Yes | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | Analyze the component architecture: identify the component hierarchy per page, document the state management strategy (which stores serve which pages), map the data fetching pattern (hooks → API calls → Zod parse → store), document the routing structure, and identify shared vs page-specific components. |

**Flow**: Explorer produces raw inventory of every frontend file with its exports and import graph → React Expert analyzes the inventory to produce an architectural overview: component hierarchy, state flow, data fetching patterns, routing → team produces a **Frontend Architecture Inventory** document.

**Inventory Targets**:

| Category | Location | What to Catalog |
| --- | --- | --- |
| Pages / Routes | `src/pages/`, `src/App.tsx` or router config | Route path, page component, auth requirement, lazy loading |
| Feature Components | `src/features/*/components/` | Component name, props interface, parent page(s), child components |
| Shared Components | `src/components/` | Component name, props, usage count (which features import it) |
| Hooks | `src/features/*/hooks/`, `src/hooks/` | Hook name, params, return type, API endpoints called, stores accessed |
| Stores | `src/stores/` | Store name, state shape, actions, which hooks/components consume it |
| Zod Schemas | `src/lib/api/schemas/` | Schema name, fields with types and nullable/optional status, transforms |
| API Client | `src/lib/api/` | Base URL config, interceptors, auth header injection, error handling |
| Types | `src/types/` | Interface/type name, fields, which schemas/components use it |
| Utils | `src/lib/`, `src/utils/` | Function name, purpose, callers |
| Test Files | `src/**/__tests__/` | Test file, what it covers, assertion patterns |

**Output**: `docs/frontend-architecture.md` — complete frontend inventory with component hierarchy, state management map, data fetching patterns, and routing structure.

---

### 58. Backend Architecture Inventory

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Backend Architect | `backend-development:backend-architect` | Yes | All tools | Catalog every backend artifact: API endpoints (route, method, auth guard, request/response schemas), CRUD functions (which model, which queries, joins, filters), Pydantic schemas (request, response, internal), SQLAlchemy models, Alembic migrations, background tasks, middleware, and utility modules. For each: document inputs, outputs, side effects, and error responses. |
| Explorer | `Explore` | **No** | All except Edit/Write | Map the backend dependency graph: which endpoints call which CRUD functions, which CRUD functions use which models, which models have which relationships. Identify shared utilities, middleware chain order, and startup/shutdown lifecycle. |

**Flow**: Explorer maps the full backend file tree and import graph → Backend Architect documents each artifact's purpose, interface, and behavior → team produces a **Backend Architecture Inventory** document.

**Inventory Targets**:

| Category | Location | What to Catalog |
| --- | --- | --- |
| API Endpoints | `backend/app/api/v1/endpoints/` | Route, method, auth guard, request schema, response schema, CRUD function called, query params |
| CRUD Functions | `backend/app/crud/` | Function name, model, query pattern (filter, join, aggregate), return type, side effects |
| Pydantic Schemas | `backend/app/schemas/` | Schema name, fields with types/nullable/optional/default, validators, computed fields |
| SQLAlchemy Models | `backend/app/models/` | Model name, table name, columns with types/constraints, relationships, indexes |
| Background Tasks | `backend/app/tasks/` or inline | Task name, trigger, what it does, error handling, retry policy |
| Middleware | `backend/app/middleware/` or `main.py` | Middleware name, order, what it intercepts, side effects |
| Auth System | `backend/app/auth/` or `dependencies.py` | Auth flow, JWT config, role guards, permission model |
| Extraction Pipeline | `backend/app/extraction/` | Each module's purpose, pipeline phases, data flow between modules |
| Config / Settings | `backend/app/core/config.py` | Every setting, env var source, default value, type |
| Alembic Migrations | `backend/alembic/versions/` | Each migration: what it changes, reversibility, dependencies |
| Test Files | `backend/tests/` | Test file, what it covers, fixtures used |

**Output**: `docs/backend-architecture.md` — complete backend inventory with endpoint catalog, CRUD map, schema reference, and middleware chain.

---

### 59. Database Schema & Data Model Documentation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Postgres Expert | `postgres-expert` | Yes | Bash(psql, pg_dump, pg_restore), Read, Grep, Edit | Connect to the PostgreSQL database and extract the live schema: all tables, columns, types, constraints, indexes, foreign keys, sequences. Compare the live schema against SQLAlchemy model definitions to identify any drift. Document the actual database state as the source of truth. |
| Docs Writer | `docs-writer` | Yes | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Produce a structured database documentation file: entity-relationship descriptions (prose, not just diagrams), table-by-table reference with column descriptions, relationship explanations, index justifications, and migration history narrative. |

**Flow**: Postgres Expert extracts live schema via `pg_dump --schema-only` and introspection queries → compares against SQLAlchemy models → identifies any drift → Docs Writer transforms the raw schema into readable documentation with entity descriptions, relationship explanations, and query pattern guidance → team produces a **Database Schema Reference** document.

**Documentation Sections**:

1. **Entity-Relationship Overview**: Prose description of the data model — what entities exist, how they relate, cardinality
2. **Table Reference**: Per-table: column name, type, nullable, default, constraints, description, indexed?
3. **Relationship Map**: Every FK relationship with cascade behavior, which CRUD functions traverse each relationship
4. **Index Catalog**: Every index with its columns, type (btree, gin, etc.), and which queries benefit from it
5. **Migration History**: Chronological summary of schema evolution — what changed and why
6. **Schema-Model Drift Report**: Any differences between the live DB schema and SQLAlchemy model definitions
7. **Query Patterns**: Common query patterns used by CRUD functions — which indexes they hit, estimated complexity

**Output**: `docs/database-schema.md` — complete database reference with table descriptions, relationships, indexes, migration history, and schema-model drift report.

---

### 60. Infrastructure & Configuration Inventory

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Explorer | `Explore` | **No** | All except Edit/Write | Catalog every configuration artifact: env var references across the codebase, Docker/compose files, CI/CD config, MCP server config, package.json scripts, conda environment specs, Vite config, TypeScript config, ESLint/Ruff config, Alembic config. For each: file path, purpose, and what depends on it. |
| Config Safety Reviewer | `config-safety-reviewer` | Yes | Read, Edit, Grep, Glob, Bash | Audit every configuration for documentation completeness: does every env var have a description? Are defaults documented? Are secrets properly excluded from version control? Is the config layered correctly (dev vs prod)? Document the configuration hierarchy. |

**Flow**: Explorer catalogs all config files and env var references → Config Safety Reviewer audits each for completeness and safety → team produces an **Infrastructure & Configuration Reference** document.

**Inventory Targets**:

| Category | Files | What to Document |
| --- | --- | --- |
| Environment Variables | `.env`, `.env.example`, `.env.prod.example` | Every var: name, purpose, type, default, required?, secret? |
| Docker | `Dockerfile`, `docker-compose.yml`, `docker/` | Services, ports, volumes, build args, health checks |
| Python Environment | `environment.yml`, `pyproject.toml`, `requirements.txt` | Dependencies with version constraints, conda env name |
| Node Environment | `package.json`, `package-lock.json` | Dependencies, scripts, engines |
| Build Config | `vite.config.ts`, `tsconfig.json` | Build targets, paths, aliases, plugins |
| Lint Config | `.eslintrc`, `ruff.toml` / `pyproject.toml [tool.ruff]` | Rules, ignores, line length, custom rules |
| Database Config | `alembic.ini`, `backend/app/core/config.py` | Connection string pattern, pool settings, migration target |
| Auth Config | Various | JWT secret, token expiry, OAuth providers, role definitions |

**Output**: `docs/infrastructure-config.md` — complete infrastructure reference with env var catalog, Docker architecture, build/lint configuration, and dependency manifest.

---

### 61. Frontend Component & Hook Deep Documentation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| React Expert | `react-expert` | Yes | Read, Grep, Glob, Bash, Edit, MultiEdit, Write | For every component identified by Team 57: document its purpose, props interface (with types and defaults), internal state, side effects, event handlers, child components rendered, and known edge cases. For every hook: document params, return value, API calls made, store interactions, and error handling. |
| Docs Writer | `docs-writer` | Yes | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Transform the React Expert's raw analysis into structured, readable documentation. Organize by feature domain (deals, properties, market-data, extraction). Include usage examples and prop tables. |

**Flow**: React Expert performs deep analysis of every component and hook → documents behavior, state, and edge cases → Docs Writer structures the output into clean, navigable documentation organized by feature → team produces a **Frontend Component Reference** document.

**Per-Component Documentation Template**:

```
## ComponentName

**File**: `src/features/deals/components/ComponentName.tsx`
**Page(s)**: Deal Detail, Deal Comparison
**Parent(s)**: ParentComponent
**Children**: ChildA, ChildB

### Props

| Prop | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| dealId | string | Yes | — | The deal UUID to display |

### State & Hooks

- Uses `useDealStore()` for: selectedDeal, isLoading
- Uses `useDealQuery(dealId)` for: API fetch + cache
- Local state: `isExpanded` (boolean, default false)

### Data Flow

1. `dealId` prop → `useDealQuery` → GET /deals/{id} → Zod parse → store update → re-render
2. On mount: fetches deal data, shows skeleton loader
3. On dealId change: re-fetches, clears stale state

### Edge Cases & Known Patterns

- Handles null financial metrics via `?? undefined` (displays "N/A")
- Trend calculation guards against division by zero
```

**Output**: `docs/frontend-components.md` — per-component and per-hook deep reference organized by feature domain.

---

### 62. Backend Endpoint & CRUD Deep Documentation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Backend Architect | `backend-development:backend-architect` | Yes | All tools | For every endpoint identified by Team 58: document the full request/response cycle — HTTP method, path, auth requirement, path/query params, request body schema, response schema (with all fields), CRUD functions called, enrichment steps, error responses (with status codes and conditions). For every CRUD function: document the SQLAlchemy query, joins, filters, and how the result is transformed before return. |
| Docs Writer | `docs-writer` | Yes | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Transform the Backend Architect's analysis into structured API documentation. Organize by domain (deals, properties, extraction, market-data, auth). Include request/response examples and error code tables. |

**Flow**: Backend Architect analyzes every endpoint and CRUD function in depth → documents the full request lifecycle → Docs Writer structures the output into clean API reference documentation → team produces a **Backend API & CRUD Reference** document.

**Per-Endpoint Documentation Template**:

```
## GET /api/v1/deals/{deal_id}

**Auth**: require_analyst (any authenticated user with analyst+ role)
**File**: backend/app/api/v1/endpoints/deals.py

### Path Parameters

| Param | Type | Description |
| --- | --- | --- |
| deal_id | UUID | The deal to retrieve |

### Response Schema: DealResponse

| Field | Type | Nullable | Source |
| --- | --- | --- | --- |
| id | UUID | No | deals.id |
| property_name | str | No | deals.property_name |
| cap_rate | float | Yes | _enrich_deals_with_extraction() → ExtractedValue |

### CRUD Call Chain

1. `get_deal(db, deal_id)` → SQLAlchemy query with joinedload(Deal.property)
2. `_enrich_deals_with_extraction([deal])` → bulk query ExtractedValue for financial fields
3. Return DealResponse.model_validate(enriched_deal)

### Error Responses

| Code | Condition | Body |
| --- | --- | --- |
| 404 | deal_id not found | {"detail": "Deal not found"} |
| 401 | Missing/invalid JWT | {"detail": "Not authenticated"} |
```

**Output**: `docs/backend-api-reference.md` — per-endpoint and per-CRUD deep reference organized by domain.

---

### 63. Data Flow & Integration Documentation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Explorer | `Explore` | **No** | All except Edit/Write | Trace end-to-end data flows for every major user action: page load, deal creation, extraction run, property search, deal comparison, market data refresh. For each flow: document every system boundary crossed (frontend → API → CRUD → DB → back). Identify shared data paths where multiple features read the same underlying data. |
| Researcher | `researcher` | Yes | All tools | Analyze the extraction pipeline data flow in depth: SharePoint/local file discovery → fingerprinting → grouping → cell mapping → Excel parsing → ExtractedValue storage → Property/Deal sync → API enrichment → frontend display. Document the complete pipeline with decision points, error handling, and retry behavior. |

**Flow**: Explorer maps all user-facing data flows across the full stack → Researcher maps the extraction pipeline's internal data flow in detail → team produces a **Data Flow & Integration Reference** document with per-flow diagrams (described in text/tables) and boundary documentation.

**Critical Data Flows to Document**:

| Flow Name | Trigger | Path | Key Decision Points |
| --- | --- | --- | --- |
| Deal List Load | Page mount | DealsKanbanBoard → useDealsList → GET /deals/ → get_deals() → enrich → response | Auth check, pagination, enrichment scope |
| Deal Detail Load | Card click | DealDetailPage → useDeal(id) → GET /deals/{id} → get_deal() → enrich → response | 404 handling, enrichment fields |
| Extraction Run | Admin action | ExtractionDashboard → POST /extraction/start → background_task → extractor → DB sync | File discovery, change detection, error categorization |
| Grouping Pipeline | Admin action | GroupPipelineTab → discover → fingerprint → group → reference-map → extract | Auto-mapping tiers, dry-run gates, approval |
| Deal Comparison | Multi-select | ComparisonView → GET /deals/compare?ids=... → get_deals_for_comparison() → response | ID validation, enrichment, field alignment |
| Market Data Refresh | Page mount / cron | MarketDataDashboard → GET /market-data/ → get_market_data() → CoStar/FRED queries | API rate limits, cache invalidation |

**Output**: `docs/data-flow-reference.md` — end-to-end data flow documentation for every major user action and system process.

---

### 64. Architecture Decision & Pattern Documentation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Researcher | `researcher` | Yes | All tools | Analyze the codebase for recurring architectural patterns and implicit design decisions. Document each pattern: what it is, where it's used, why it was chosen, and what the alternatives were. Review git history for significant architectural changes. Research best-practice context for the patterns used (FastAPI dependency injection, SQLAlchemy 2.0 async, Zustand vs Redux, Zod transforms). |
| Docs Writer | `docs-writer` | Yes | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Produce Architecture Decision Records (ADRs) for each significant design choice. Write a patterns guide that names and explains each recurring pattern so future development stays consistent. |

**Flow**: Researcher identifies all architectural patterns and implicit decisions → documents rationale and tradeoffs → Docs Writer formats as ADRs and a patterns guide → team produces an **Architecture Decisions & Patterns Reference** document.

**Patterns to Document**:

| Pattern | Where Used | Key Details |
| --- | --- | --- |
| Zod `.nullable().optional()` + `?? undefined` | Frontend schemas | Why not `?? 0`? Display semantics for missing data |
| SQLAlchemy async sessions | All CRUD | Session lifecycle, dependency injection via `get_db()` |
| Pydantic response model enrichment | Deal endpoints | `_enrich_deals_with_extraction()` pattern — why post-query enrichment? |
| Zustand store-per-feature | Frontend state | Why Zustand over React Query? Store boundaries |
| Background task extraction | Extraction endpoints | Why not synchronous? Task lifecycle, status polling |
| Auth guard decorators | All endpoints | `require_analyst` vs `require_manager` — when to use which |
| Conda environment isolation | Python deps | Why conda over venv/uv? Environment naming convention |
| Feature-based folder structure | Frontend `src/features/` | Colocation of components, hooks, tests per domain |

**Output**: `docs/architecture-decisions.md` — ADRs for major design choices + a recurring patterns guide.

---

### 65. Test Coverage & Quality Documentation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Explorer | `Explore` | **No** | All except Edit/Write | Map the complete test inventory: every test file, what it tests (endpoint, component, hook, CRUD, model), assertion patterns used, fixtures available, and mock strategy. Cross-reference against the source inventory from Teams 57-58 to identify untested artifacts. |
| Test Engineer | `test-engineer` | Yes | Read, Write, Edit, Bash, Grep, Glob | Analyze test quality beyond coverage numbers: are tests asserting the right things? Are error paths tested? Are auth boundaries tested? Are there tests that always pass (vacuous assertions)? Document the test strategy and produce a gap analysis. Run coverage reports (`pytest --cov`, vitest coverage) and document results. |

**Flow**: Explorer catalogs all test files and maps coverage → Test Engineer analyzes test quality and runs coverage tools → team produces a **Test Coverage & Quality Reference** document with gap analysis and recommendations.

**Documentation Sections**:

1. **Test Inventory**: Every test file, what it covers, test count
2. **Coverage Report**: Backend line/branch coverage per module, frontend coverage per feature
3. **Gap Analysis**: Untested endpoints, components, hooks, CRUD functions — prioritized by risk
4. **Test Patterns Guide**: How to write tests in this project (fixtures, mocks, auth setup, DB setup)
5. **Test Quality Audit**: Tests with weak assertions, missing error paths, untested auth boundaries

**Output**: `docs/test-coverage.md` — test inventory, coverage metrics, gap analysis, and testing patterns guide.

---

### 66. Documentation Review, Cross-Reference Validation & Findings Consolidation

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Reviewer | `reviewer` | Yes | Read, Edit, Grep, Glob, Bash | Review all documentation produced by Teams 57-65 for: accuracy (does the doc match the actual code?), completeness (are there artifacts mentioned in one doc but missing from another?), consistency (are the same entities named identically across docs?), and navigability (can you find what you need quickly?). |
| Docs Writer | `docs-writer` | Yes | Read, Write, Edit, Grep, Glob, Bash, WebFetch | Produce a **Documentation Index** (`docs/README.md`) that serves as the entry point to all documentation. Cross-link between documents. Add "last verified" timestamps. Fix any inconsistencies found by Reviewer. Consolidate ALL issues, bugs, gaps, and improvement opportunities found by every team into a single **Findings & Recommendations Report** (`docs/findings-and-recommendations.md`), prioritized by severity. |

**Flow**: Reviewer audits all documentation files for accuracy and completeness → flags inconsistencies and gaps → Docs Writer fixes doc-level issues, adds cross-references, produces the documentation index, and consolidates ALL findings from every team into a single prioritized report → team produces a **Documentation Index**, **Findings & Recommendations Report**, and **Validation Report**.

**Findings & Recommendations Report Structure**:

The `docs/findings-and-recommendations.md` file consolidates every issue surfaced by Teams 57-65 into a single actionable document:

| Section | Source Teams | Content |
| --- | --- | --- |
| Critical Issues | 57-63 | Bugs, data integrity violations, schema mismatches — things that produce wrong output |
| Schema & Contract Drift | 58, 59, 62 | Pydantic ↔ Zod mismatches, SQLAlchemy ↔ DB drift, undocumented fields |
| Test Gaps | 65 | Untested endpoints, components, error paths — prioritized by risk |
| Configuration Gaps | 60 | Undocumented env vars, missing defaults, secrets exposure risks |
| Architecture Improvements | 64 | Pattern violations, inconsistent conventions, tech debt opportunities |
| Performance Concerns | 58, 59 | Missing indexes, N+1 query patterns, unnecessary queries |
| Dead Code & Cleanup | 57, 58 | Orphaned files, unused exports, unreachable code paths |

Each finding includes: **severity** (critical/high/medium/low), **location** (file path + line), **description**, **recommended fix**, and **suggested Agent Team** from the reference guide to execute the fix (e.g., "Use Teams 48-56 for Dashboard Integrity fixes").

**Validation Checks**:

1. Every endpoint documented in `backend-api-reference.md` appears in `data-flow-reference.md`
2. Every component in `frontend-components.md` appears in `frontend-architecture.md`
3. Every table in `database-schema.md` has a corresponding SQLAlchemy model in `backend-architecture.md`
4. Every env var in `infrastructure-config.md` appears in the actual codebase
5. No stale references — every file path mentioned in docs exists in the project
6. Cross-document links are valid
7. Every finding from every team appears in `findings-and-recommendations.md`

**Output**: `docs/README.md` (documentation index) + `docs/findings-and-recommendations.md` (consolidated findings) + **Validation Report** listing any remaining inaccuracies.

---

### 67. Documentation Final Gate

| Agent Name | subagent_type | Can Edit? | Tools | Role on Team |
| --- | --- | --- | --- | --- |
| Reviewer | `reviewer` | Yes | Read, Edit, Grep, Glob, Bash | Final review of all documentation and the documentation index. **CRITICAL**: Run `git status` and `git diff` to verify ZERO source code changes were made (only new files in `docs/` should appear). Check that all docs follow the same formatting conventions. Verify `docs/findings-and-recommendations.md` is complete — every finding from every team is represented. |
| Tester | `tester` | Yes | Read, Write, Edit, Bash, Grep, Glob | Run the full test suite (backend + frontend) to confirm no regressions were introduced. Report test count and pass rate — must match the pre-documentation baseline exactly (no tests added, removed, or modified). |
| Production Validator | `production-validator` | Yes | All tools | Verify: `npm run build` succeeds, `npx tsc --noEmit` passes, backend starts cleanly. Run `git diff --stat` to confirm the only changed/added files are in `docs/`. Confirm the project is in the **exact same working state** as before the documentation effort — zero functional changes. |

**Flow**: All three work in parallel → Reviewer confirms documentation quality, findings completeness, and zero source code changes → Tester verifies no regressions → Production Validator confirms build integrity and zero-change guarantee → team produces **Documentation Effort Final Report**.

**Output**: Final Report — documentation file count, total word count, findings count by severity, validation status, test suite status, build status, git diff confirmation (docs/ only), go/no-go.

---

## Quick Reference: System Review & Documentation Teams

| # | Team Name | Agents | Phase | Parallel? | Purpose |
| --- | --- | --- | --- | --- | --- |
| 57 | Frontend Architecture Inventory | Explorer, React Expert | Discovery | Yes | Catalog all frontend artifacts and component hierarchy |
| 58 | Backend Architecture Inventory | Backend Architect, Explorer | Discovery | Yes | Catalog all backend artifacts and dependency graph |
| 59 | Database Schema Documentation | Postgres Expert, Docs Writer | Discovery | Yes | Extract live schema, document tables and relationships |
| 60 | Infrastructure & Config Inventory | Explorer, Config Safety Reviewer | Discovery | Yes | Catalog all config, env vars, Docker, build tools |
| 61 | Frontend Component Deep Docs | React Expert, Docs Writer | Documentation | Yes | Per-component and per-hook deep reference |
| 62 | Backend Endpoint Deep Docs | Backend Architect, Docs Writer | Documentation | Yes | Per-endpoint and per-CRUD deep reference |
| 63 | Data Flow & Integration Docs | Explorer, Researcher | Documentation | Yes | End-to-end data flow documentation |
| 64 | Architecture Decisions & Patterns | Researcher, Docs Writer | Documentation | Yes | ADRs and recurring patterns guide |
| 65 | Test Coverage & Quality Docs | Explorer, Test Engineer | Documentation | Yes | Test inventory, coverage, gap analysis |
| 66 | Docs Review, Validation & Findings | Reviewer, Docs Writer | Validation | Sequential | Cross-reference validation, index creation, findings consolidation |
| 67 | Documentation Final Gate | Reviewer, Tester, Production Validator | Final | Yes | Quality gate — no regressions, docs complete |

---

## Execution Plan: Step-by-Step Instructions

### Overview

The teams are organized into **4 phases**. Phase 1 inventories every artifact in the system. Phase 2 produces deep documentation from those inventories. Phase 3 validates cross-references and consistency. Phase 4 is the final quality gate.

```
PHASE 1: DISCOVERY & INVENTORY (Teams 57-60)     ← What exists? Where? How is it connected?
    ↓
PHASE 2: DEEP DOCUMENTATION (Teams 61-65)         ← Document every artifact in detail
    ↓
PHASE 3: VALIDATION & INDEX (Team 66)             ← Cross-reference, fix inconsistencies, build index
    ↓
PHASE 4: FINAL GATE (Team 67)                     ← Confirm no regressions, docs are complete
```

---

### Phase 1: Discovery & Inventory (Teams 57, 58, 59, 60 — ALL PARALLEL)

**What**: Catalog every artifact in the system across all layers. All 4 teams run simultaneously because they are independent read-only inventory tasks.

**Launch Command** (single message with 4 Task calls):

```
Task("Frontend Inventory", "Team 57: Systematically catalog every frontend artifact in the project. Start from src/ and map: (1) ALL pages — find the router config (React Router) and list every route with its component, path, auth requirement, and lazy loading status, (2) ALL components — scan src/features/*/components/ and src/components/, for each: file path, component name, props interface, imports (dependencies), what imports it (dependents), (3) ALL hooks — scan src/features/*/hooks/ and src/hooks/, for each: hook name, params, return type, API endpoints called, stores accessed, (4) ALL Zustand stores — scan src/stores/, for each: store name, state shape (all fields with types), actions, selectors, which hooks/components consume it, (5) ALL Zod schemas — scan src/lib/api/schemas/, for each: schema name, every field with type, nullable, optional, transforms, defaults, (6) ALL TypeScript types — scan src/types/, for each: interface/type name, fields, which schemas/components use it, (7) ALL utility functions — scan src/lib/ and src/utils/, (8) ALL test files — scan src/**/__tests__/. Produce a structured inventory document. Do NOT edit any files.", "react-expert")

Task("Backend Inventory", "Team 58: Systematically catalog every backend artifact in the project. Start from backend/ and map: (1) ALL API endpoints — scan backend/app/api/v1/endpoints/, for each: file path, route path, HTTP method, auth guard (require_analyst/require_manager/none), request schema, response schema, CRUD function called, query parameters, (2) ALL CRUD functions — scan backend/app/crud/, for each: function name, model, query type (select/insert/update/delete), joins, filters, return type, (3) ALL Pydantic schemas — scan backend/app/schemas/, for each: schema name, every field with type, nullable, optional, default, validators, (4) ALL SQLAlchemy models — scan backend/app/models/, for each: model name, table name, columns, relationships, indexes, (5) ALL extraction pipeline modules — scan backend/app/extraction/, for each: module name, purpose, inputs, outputs, dependencies, (6) ALL middleware — in main.py and backend/app/middleware/, (7) ALL background tasks, (8) ALL config/settings — backend/app/core/config.py, every setting with env var source and default, (9) ALL Alembic migrations — backend/alembic/versions/, each migration's purpose, (10) ALL test files — backend/tests/. Produce a structured inventory document. Do NOT edit any files.", "backend-development:backend-architect")

Task("Database Inventory", "Team 59: Document the complete PostgreSQL database schema. (1) Connect to the database using the connection string from .env (port 5433) and run: pg_dump --schema-only to capture the full DDL, (2) For each table: list all columns with data type, nullable, default, constraints, (3) Map all foreign key relationships with cascade behavior, (4) List all indexes with columns and type, (5) List all sequences, (6) Compare the live schema against SQLAlchemy model definitions in backend/app/models/ — flag any drift (column in DB but not in model, or vice versa), (7) Summarize the migration history from backend/alembic/versions/ — what changed in each migration. Produce a structured schema document.", "postgres-expert")

Task("Infrastructure Inventory", "Team 60: Catalog all configuration and infrastructure artifacts. (1) Find EVERY env var reference across the entire codebase — grep for os.environ, os.getenv, process.env, settings., config., import.meta.env, (2) Cross-reference each against .env, .env.example, .env.prod.example — flag undocumented vars, (3) Document Docker files: Dockerfile, docker-compose.yml, any files in docker/, (4) Document build config: vite.config.ts, tsconfig.json, tsconfig.node.json, (5) Document lint config: ESLint config, ruff config in pyproject.toml, (6) Document package managers: package.json scripts, conda environment spec, (7) Document Alembic config: alembic.ini, env.py, (8) List all MCP server references if any, (9) Document any CI/CD config. Produce a structured infrastructure document.", "Explore")
```

**Decision Point**: Review all 4 inventories. They form the factual foundation for Phase 2. Verify counts are reasonable — if the frontend inventory shows 0 hooks, something was missed.

**Expected Duration**: 10-20 minutes (all parallel).

---

### Phase 2: Deep Documentation (Teams 61, 62, 63, 64, 65 — ALL PARALLEL)

**What**: Using the inventories from Phase 1, produce comprehensive documentation for every artifact. All 5 teams run simultaneously because each produces an independent documentation file.

**Pre-Condition**: Phase 1 inventories reviewed and approved.

**CRITICAL READ-ONLY RULE**: Every Phase 2 agent documents what they find — bugs, inconsistencies, gaps, pattern violations — but makes **ZERO code changes**. All issues are captured in the documentation with severity, file:line, and recommended fix. Team 66 will consolidate all findings into `docs/findings-and-recommendations.md`.

**Launch Command** (single message with 5 Task calls):

```
Task("Frontend Component Docs", "Team 61: Using the Phase 1 frontend inventory, produce comprehensive documentation for every frontend component and hook. For EACH component: document its purpose, full props interface (name, type, required, default, description), internal state (useState/useReducer), side effects (useEffect with dependencies), event handlers, child components rendered, Zustand stores accessed, API calls triggered, and known edge cases (null handling, loading states, error states). For EACH hook: document params, return type, API endpoint called, Zod schema used for parse, store mutations, error handling, and re-fetch triggers. Organize by feature domain: deals, properties, market-data, extraction, auth, shared. Write the output to docs/frontend-components.md. Read the actual source code for every component — do not infer from names. IMPORTANT: For every issue found (bugs, missing null guards, ?? 0 patterns, stale state, missing error handling), add a '## Issues Found' section at the end with severity, file:line, description, and recommended fix. Do NOT edit any source files.", "react-expert")

Task("Backend API Docs", "Team 62: Using the Phase 1 backend inventory, produce comprehensive API documentation for every endpoint and CRUD function. For EACH endpoint: document HTTP method, full path, auth requirement, all path/query params with types, request body schema (if POST/PUT/PATCH), complete response schema (every field with type, nullable, description), the CRUD function(s) called, any enrichment steps, and ALL error responses (status code, condition, response body). For EACH CRUD function: document the SQLAlchemy query in detail — model, joins, filters, ordering, pagination, and how the result is transformed before return. Include the enrichment functions (_enrich_deals_with_extraction, etc.) as separate documented functions. Organize by domain: deals, properties, extraction, market-data, auth. Write the output to docs/backend-api-reference.md. Read the actual source code — do not infer. IMPORTANT: For every issue found (schema mismatches, missing error handlers, inconsistent auth, N+1 queries, missing validation), add a '## Issues Found' section at the end with severity, file:line, description, and recommended fix. Do NOT edit any source files.", "backend-development:backend-architect")

Task("Data Flow Docs", "Team 63: Produce end-to-end data flow documentation for every major user action and system process. For EACH flow: trace the complete path from user action → React component → hook → API call → backend endpoint → CRUD function → SQLAlchemy query → database table → response → Zod parse → store update → component re-render. Document EVERY boundary crossing with what data shape changes. Flows to document: (1) deal list page load, (2) deal detail load, (3) deal creation/edit, (4) property list load, (5) property detail load, (6) deal comparison, (7) extraction run (local), (8) grouping pipeline (discover → fingerprint → group → map → extract), (9) market data sales page load, (10) construction pipeline page load, (11) auth login flow, (12) auth token refresh. Also document the extraction pipeline internal flow in detail: file discovery → fingerprinting → grouping → cell mapping → Excel parsing → value storage → property/deal sync. Write the output to docs/data-flow-reference.md. IMPORTANT: For every data flow discontinuity found (data lost between layers, type coercion, schema gaps, stale cache paths), add a '## Issues Found' section at the end with severity, file:line, description, and recommended fix. Do NOT edit any source files.", "researcher")

Task("Architecture & Patterns Docs", "Team 64: Document all architectural decisions and recurring patterns in the codebase. (1) Identify every recurring pattern: Zod nullable handling, auth guard usage, Pydantic response enrichment, SQLAlchemy async session management, Zustand store conventions, background task lifecycle, error response format, test fixture patterns. For each pattern: document what it is, where it's used (with file references), why it was chosen, what the alternatives are, and how to apply it correctly. (2) Write Architecture Decision Records (ADRs) for major design choices: FastAPI over Django/Flask, SQLAlchemy async over sync, Zustand over Redux/React Query, Zod over io-ts/yup, conda over venv, feature-based folder structure, enrichment-on-read pattern for extraction data, background tasks for extraction. For each ADR: context, decision, consequences, alternatives considered. (3) Document the project's coding conventions: naming, file organization, import ordering, error handling standards. Write the output to docs/architecture-decisions.md. IMPORTANT: For every pattern violation, inconsistent convention, or architectural concern found, add a '## Issues Found' section at the end with severity, file:line, description, and recommended fix. Do NOT edit any source files.", "researcher")

Task("Test Coverage Docs", "Team 65: Produce a comprehensive test documentation and coverage analysis. (1) Run coverage: conda run -n dashboard-backend pytest backend/tests/ --cov=backend/app --cov-report=term-missing -v AND npx vitest run --coverage. Capture results. (2) Map every test file to what it tests — endpoint, component, hook, CRUD function, model. (3) Identify the test GAP: every artifact (endpoint, component, hook, CRUD) that has NO test, or has tests that only cover the happy path and miss error/edge cases. (4) Analyze test quality: find tests with weak assertions (assertTrue(True), assertEqual with hardcoded values), tests missing auth boundary checks, tests that don't assert error responses. (5) Document the test strategy: how to set up test DB, how to create fixtures, how to mock auth, how to test components, test naming conventions. (6) Produce a prioritized gap list: critical (untested auth endpoints, untested error paths) → high (untested CRUD functions) → medium (untested components) → low (untested utilities). Write the output to docs/test-coverage.md. IMPORTANT: The gap list IS the findings for this team — every untested artifact is a finding. Do NOT write any new tests or edit any test files.", "test-engineer")
```

**Expected Duration**: 20-40 minutes (all parallel).

---

### Phase 3: Validation & Index (Team 66 — SEQUENTIAL)

**What**: Cross-reference all documentation for consistency, fix gaps, and produce the documentation index.

**Pre-Condition**: All Phase 2 documentation files written.

**Launch Command**:

```
Task("Documentation Validation & Findings Consolidation", "Team 66: Review and cross-reference all documentation produced in Phase 2. (1) Read every doc file in docs/: frontend-architecture.md, frontend-components.md, backend-architecture.md, backend-api-reference.md, database-schema.md, infrastructure-config.md, data-flow-reference.md, architecture-decisions.md, test-coverage.md. (2) Cross-reference: every endpoint in backend-api-reference.md should appear in data-flow-reference.md. Every component in frontend-components.md should appear in frontend-architecture.md. Every table in database-schema.md should have a corresponding model in backend-architecture.md. Every env var in infrastructure-config.md should exist in the codebase. (3) Flag inconsistencies: same entity named differently across docs, stale file paths that don't exist, missing artifacts (mentioned in one doc but absent from another). (4) Fix all doc-level inconsistencies found. (5) Create docs/README.md as the documentation index. (6) CRITICAL: Consolidate ALL issues, bugs, gaps, inconsistencies, and improvement opportunities identified by EVERY team (57-65) into docs/findings-and-recommendations.md. Organize by severity (critical, high, medium, low). For each finding: severity, location (file:line), description, recommended fix, and suggested Agent Team from docs/agent-team-reference.md to execute the fix. (7) Add 'Last verified: [date]' to each doc file. Report total findings count by severity.", "reviewer")
```

**Expected Duration**: 10-20 minutes.

---

### Phase 4: Final Gate (Team 67 — ALL PARALLEL)

**What**: Final quality gate to confirm documentation is complete and no regressions were introduced.

**Pre-Condition**: Phase 3 validation complete.

**Launch Command** (single message with 3 Task calls):

```
Task("Documentation Quality Review", "Team 67 - Reviewer: Final review of all documentation files in docs/. Verify: (1) every doc follows consistent formatting (heading hierarchy, table structure, code block syntax), (2) no placeholder text or TODO markers remain, (3) cross-document links are valid, (4) no code changes were made outside of docs/ (this is documentation-only), (5) README.md index is complete and all links work. Report any remaining issues.", "reviewer")

Task("Regression Check", "Team 67 - Tester: Run the complete test suite to confirm no regressions: (1) conda run -n dashboard-backend pytest backend/tests/ -v (2) npm run test. Report total test count and pass rate. Both must match the pre-documentation baseline (no tests added or removed — this is a docs-only effort).", "tester")

Task("Build Verification", "Team 67 - Validator: Verify project integrity: (1) npm run build succeeds with zero errors, (2) npx tsc --noEmit passes, (3) backend starts cleanly with conda run -n dashboard-backend uvicorn backend.app.main:app, (4) all documentation files are valid markdown (no syntax errors). Confirm the project is in the exact same working state as before the documentation effort.", "production-validator")
```

**Decision Point**: All three must report clean for the documentation effort to be considered complete.

**Expected Duration**: 5-10 minutes (all parallel).

---

## Summary: Total Agent Count for System Review & Documentation

| Phase | Teams | Unique Agent Types | Total Agent Instances |
| --- | --- | --- | --- |
| 1: Discovery & Inventory | 57, 58, 59, 60 | 5 (Explore, react-expert, backend-architect, postgres-expert, config-safety-reviewer) | 8 |
| 2: Deep Documentation | 61, 62, 63, 64, 65 | 5 (react-expert, backend-architect, researcher, docs-writer, test-engineer) | 10 |
| 3: Validation & Index | 66 | 2 (reviewer, docs-writer) | 2 |
| 4: Final Gate | 67 | 3 (reviewer, tester, production-validator) | 3 |
| **Total** | **11 teams** | **9 unique types** | **23 agent instances** |

**Optimal execution with full parallelism**: ~45-90 minutes + review time between phases.

---

## Documentation Output Manifest

| Document | Produced By | Content |
| --- | --- | --- |
| `docs/README.md` | Team 66 | Documentation index — table of contents linking all docs |
| `docs/findings-and-recommendations.md` | Team 66 (consolidated from all teams) | **Primary deliverable** — every issue, bug, gap, and improvement opportunity, prioritized by severity with recommended fixes and suggested Agent Teams |
| `docs/frontend-architecture.md` | Teams 57 | Component hierarchy, routing, state management, data fetching patterns |
| `docs/frontend-components.md` | Team 61 | Per-component and per-hook deep reference by feature domain |
| `docs/backend-architecture.md` | Team 58 | Endpoint catalog, CRUD map, model reference, middleware chain |
| `docs/backend-api-reference.md` | Team 62 | Per-endpoint deep reference with schemas, errors, CRUD chains |
| `docs/database-schema.md` | Team 59 | Table reference, relationships, indexes, migration history, drift report |
| `docs/infrastructure-config.md` | Team 60 | Env var catalog, Docker architecture, build/lint config, dependencies |
| `docs/data-flow-reference.md` | Team 63 | End-to-end data flow documentation for every major action |
| `docs/architecture-decisions.md` | Team 64 | ADRs for design choices + recurring patterns guide |
| `docs/test-coverage.md` | Team 65 | Test inventory, coverage metrics, gap analysis, testing patterns |

---

## Troubleshooting Guide

### Common Issues and Resolution

| Issue | Symptom | Team That Catches It | Resolution |
| --- | --- | --- | --- |
| Inventory misses files in nested dirs | Component/endpoint count lower than expected | Team 57, 58 | Verify glob patterns search recursively. Check for non-standard file locations. |
| Schema drift between DB and models | pg_dump output doesn't match SQLAlchemy column defs | Team 59 | Document the drift. May need an Alembic migration to reconcile — note it but don't fix it (docs-only effort). |
| Env var referenced but not in .env.example | Config doc lists var but example file missing it | Team 60 | Add to .env.example with safe default — this is the one acceptable code change. |
| Component props inferred incorrectly | Documentation says prop is required but it has a default | Team 61 | Re-read the TypeScript interface. Check for `defaultProps` or destructuring defaults. |
| Test coverage tool errors | pytest-cov or vitest coverage config not set up | Team 65 | Install missing coverage plugins. Document the setup for future runs. |
| Cross-doc inconsistency | Endpoint named `/deals/` in API doc but `/api/v1/deals/` in data flow doc | Team 66 | Standardize on the full path including prefix. Fix all references. |

### If Agents Attempt to Edit Code

This is designed as a **strictly read-only** effort. No agent should edit any project file outside of `docs/`.

1. **If an agent tries to fix a bug it found**: STOP. Document the bug in the findings report with file path, line number, description, and recommended fix — but do NOT apply the fix
2. **If an env var is undocumented**: Document the gap in `docs/infrastructure-config.md` and add it to the findings report — do NOT edit `.env.example`
3. **If a docstring is wrong**: Document the error in the findings report — do NOT edit the source file
4. **If a test is missing**: Document the gap in `docs/test-coverage.md` with the recommended test — do NOT write the test
5. **All identified issues go into `docs/findings-and-recommendations.md`** for the developer to act on in a separate effort (e.g., Teams 48-56 for Dashboard Integrity fixes)

---

## Optimal Prompt for Execution

Copy and paste the following prompt into a Claude Code terminal to execute the full documentation pipeline.

### The Prompt

```
I need you to run a comprehensive system review and documentation pipeline on this project. Follow all 4 phases below exactly. Use Claude Code's built-in Task tool to create agent teams. Communicate progress at every phase boundary.

## CRITICAL CONSTRAINT: STRICTLY READ-ONLY — ZERO CHANGES

This effort makes ZERO changes to the project. No code edits. No config changes. No test additions. No .env updates. No docstring fixes. Nothing. Every agent operates in read-only mode against the codebase and database. The ONLY files created are new documentation files written to `docs/`. If an agent finds a bug, schema mismatch, missing test, or any other issue — it documents the finding with severity, file:line, description, and recommended fix. It does NOT apply the fix. All findings are consolidated into `docs/findings-and-recommendations.md` in Phase 3.

At the end of Phase 4, run `git diff --stat` to prove zero source files were modified. Only new files in `docs/` should appear.

## PROJECT CONTEXT
- Backend: FastAPI + SQLAlchemy 2.0 async + Alembic (Python, in `backend/`)
- Frontend: React + TypeScript + Vite (in `src/`)
- Database: PostgreSQL on port 5433, conda environment `dashboard-backend`
- Backend schemas: Pydantic models in `backend/app/schemas/`
- Frontend schemas: Zod schemas in `src/lib/api/schemas/`
- Extraction pipeline: `backend/app/extraction/` (extractor, fingerprinter, grouping, reference_mapper, cell_mapping, group_pipeline)
- Stores: Zustand in `src/stores/`
- Tests: Backend pytest (`backend/tests/`), Frontend vitest (`src/`)
- Config: `.env` in project root, `.env.prod.example`, Docker configs
- Auth: JWT with role-based guards (require_analyst for reads, require_manager for mutations)
- Test commands: `npm run test` (frontend), `conda run -n dashboard-backend pytest backend/tests/` (backend)
- Build command: `npm run build`
- Type check: `npx tsc --noEmit`
- Documentation output directory: `docs/`
- Agent Team Reference: `docs/agent-team-reference.md` (Teams 57-67 cover this effort)

## PHASE 1: DISCOVERY & INVENTORY (Teams 57-60, ALL PARALLEL)

Create tasks for all 4 inventory workstreams below, then spawn agents to work them IN PARALLEL. No file edits — inventory and documentation only. All output goes to `docs/`.

1. **Frontend Architecture Inventory** (Team 57): Spawn a `react-expert` agent. It must:
   - Map every route in the router config: path, component, auth requirement, lazy loading
   - Catalog every component in `src/features/*/components/` and `src/components/`: file path, component name, props interface, imports, dependents
   - Catalog every hook in `src/features/*/hooks/` and `src/hooks/`: name, params, return type, API calls, store access
   - Catalog every Zustand store in `src/stores/`: state shape, actions, consumers
   - Catalog every Zod schema in `src/lib/api/schemas/`: fields with types, nullable, optional, transforms
   - Catalog every type in `src/types/`
   - Map the component hierarchy per page
   - Write the raw inventory to `docs/frontend-architecture.md`
   - Do NOT edit any source files

2. **Backend Architecture Inventory** (Team 58): Spawn a `backend-development:backend-architect` agent. It must:
   - Catalog every API endpoint in `backend/app/api/v1/endpoints/`: route, method, auth guard, request/response schema, CRUD function
   - Catalog every CRUD function in `backend/app/crud/`: function name, model, query pattern, return type
   - Catalog every Pydantic schema in `backend/app/schemas/`: all fields with types, nullable, validators
   - Catalog every SQLAlchemy model in `backend/app/models/`: table, columns, relationships, indexes
   - Catalog every extraction module in `backend/app/extraction/`: purpose, inputs, outputs
   - Document middleware chain, auth system, background tasks, settings
   - Catalog every Alembic migration and every test file
   - Write the raw inventory to `docs/backend-architecture.md`
   - Do NOT edit any source files

3. **Database Schema Inventory** (Team 59): Spawn a `postgres-expert` agent. It must:
   - Run `pg_dump --schema-only` against the live database
   - Document every table: columns, types, nullable, defaults, constraints
   - Map all foreign key relationships with cascade behavior
   - List all indexes with columns and type
   - Compare live schema against SQLAlchemy models — flag drift
   - Summarize migration history
   - Write to `docs/database-schema.md`
   - Do NOT edit any source files or run any migrations

4. **Infrastructure Inventory** (Team 60): Spawn an `Explore` agent. It must:
   - Grep for every env var reference across the entire codebase
   - Cross-reference against .env.example files — flag undocumented vars
   - Document Docker config, Vite config, TypeScript config, lint config, conda env, package.json scripts
   - Write to `docs/infrastructure-config.md`
   - Do NOT edit any config files — only document what exists and flag gaps

After ALL 4 agents complete, present the inventories to me and WAIT for my approval before proceeding to Phase 2.

## PHASE 2: DEEP DOCUMENTATION (Teams 61-65, ALL PARALLEL)

After I approve the Phase 1 inventories, spawn all 5 documentation teams in parallel.

CRITICAL READ-ONLY RULE: Every Phase 2 agent documents what they find — bugs, inconsistencies, gaps, pattern violations — but makes ZERO code changes. All issues are captured in the documentation with severity, file:line, and recommended fix. Team 66 will consolidate all findings into `docs/findings-and-recommendations.md`.

1. **Frontend Component Deep Docs** (Team 61, `react-expert`): For every component and hook from Team 57's inventory: document purpose, full props interface, internal state, side effects, event handlers, children, stores accessed, API calls, edge cases. Organize by feature domain. Write to `docs/frontend-components.md`. For every issue found (bugs, missing null guards, ?? 0 patterns, stale state, missing error handling), add a `## Issues Found` section at the end with severity, file:line, description, and recommended fix. Do NOT edit any source files.

2. **Backend API Deep Docs** (Team 62, `backend-development:backend-architect`): For every endpoint from Team 58's inventory: document full request/response cycle, all params, complete response schema with every field, CRUD chain, enrichment steps, all error responses. For every CRUD function: document the query in detail. Include enrichment functions. Write to `docs/backend-api-reference.md`. For every issue found (schema mismatches, missing error handlers, inconsistent auth, N+1 queries), add a `## Issues Found` section. Do NOT edit any source files.

3. **Data Flow Documentation** (Team 63, `researcher`): Trace end-to-end data flows for every major user action: deal list load, deal detail, deal creation, property list, property detail, deal comparison, extraction run (local), grouping pipeline (all phases), market data pages, auth login, token refresh. Document every boundary crossing. Write to `docs/data-flow-reference.md`. For every data flow discontinuity found (data lost between layers, type coercion, schema gaps), add a `## Issues Found` section. Do NOT edit any source files.

4. **Architecture Decisions & Patterns** (Team 64, `researcher`): Identify every recurring pattern (Zod nullable, async sessions, enrichment, Zustand conventions, auth guards, background tasks). Write ADRs for major design choices (FastAPI, SQLAlchemy async, Zustand, Zod, conda, feature folders, enrichment-on-read). Document coding conventions. Write to `docs/architecture-decisions.md`. For every pattern violation or architectural concern, add a `## Issues Found` section. Do NOT edit any source files.

5. **Test Coverage Documentation** (Team 65, `test-engineer`): Run coverage tools (read-only — capture output only). Map every test file to what it tests. Identify all gaps (untested endpoints, components, CRUD, error paths). Analyze test quality (weak assertions, missing auth tests). Document test strategy (fixtures, mocks, setup). Write to `docs/test-coverage.md`. The gap list IS the findings — every untested artifact is a finding with severity. Do NOT write any new tests or edit any test files.

After ALL 5 agents complete, present the documentation and WAIT for my approval before Phase 3.

## PHASE 3: VALIDATION, INDEX & FINDINGS CONSOLIDATION (Team 66, SEQUENTIAL)

After I approve Phase 2:

Spawn a `reviewer` agent to:
1. Cross-reference all documentation: every endpoint in API docs appears in data flow docs, every component in component docs appears in architecture docs, every table in DB docs has a model in backend docs
2. Flag and fix all doc-level inconsistencies (naming, stale paths, missing artifacts)
3. Create `docs/README.md` as the documentation index
4. **CRITICAL**: Consolidate ALL issues, bugs, gaps, inconsistencies, and improvement opportunities identified by EVERY team (57-65) into `docs/findings-and-recommendations.md`. Organize by severity (critical → high → medium → low). For each finding: severity, location (file:line), description, recommended fix, and suggested Agent Team from `docs/agent-team-reference.md` to execute the fix
5. Add "Last verified: [today's date]" to each doc
6. Report total findings count by severity

## PHASE 4: FINAL GATE (Team 67, ALL PARALLEL)

After Phase 3:
1. Spawn a `reviewer` to verify all docs follow consistent formatting, no TODOs remain, all cross-links work, `docs/findings-and-recommendations.md` is complete with every finding represented. **Run `git status` and `git diff` to verify ZERO source code changes** — only new files in `docs/` should appear.
2. Spawn a `tester` to run full test suite (backend + frontend) — confirm zero regressions. Test count must match pre-documentation baseline exactly (no tests added, removed, or modified).
3. Spawn a `production-validator` to verify: `npm run build`, `npx tsc --noEmit`, backend starts cleanly. Run `git diff --stat` to confirm only `docs/` files changed.

Present the final report including: documentation file count, findings count by severity, test suite status, build status, and git diff confirmation. Do NOT commit or push — I will review and commit.

## COMMUNICATION RULES
- Report progress at every phase boundary
- If any agent can't read a file or connect to the database, report immediately
- After Phase 1, WAIT for my approval before Phase 2
- After Phase 2, WAIT for my approval before Phase 3
- After Phase 4, present the final summary and STOP
- **ABSOLUTE RULE**: Do NOT edit any source files, config files, test files, or env files. The ONLY files created or modified are in `docs/`. If you find something that needs fixing, document it in the findings — do not fix it.
```

### Expected Duration

| Phase | Agents | Estimated Time |
| --- | --- | --- |
| Phase 1: Discovery | 4 parallel | 10-20 minutes |
| Review break | You | As long as needed |
| Phase 2: Deep Docs | 5 parallel | 20-40 minutes |
| Review break | You | As long as needed |
| Phase 3: Validation | 1 sequential | 10-20 minutes |
| Phase 4: Final Gate | 3 parallel | 5-10 minutes |
| **Total** | | **~45-90 minutes + review time** |

### What Success Looks Like

After a successful run, you should have:

- **ZERO changes** to any project source file (no code, config, test, or env file edits)
- 11 documentation files in `docs/`
- A `docs/README.md` index linking to all docs
- A `docs/findings-and-recommendations.md` with every issue prioritized by severity — the primary actionable deliverable
- Every frontend component, hook, store, and schema documented
- Every backend endpoint, CRUD function, schema, and model documented
- Complete database schema reference with relationship map and drift report
- End-to-end data flow documentation for every major user action
- Architecture Decision Records for all major design choices
- Test coverage report with prioritized gap analysis
- All documentation cross-referenced and validated for consistency
- Zero test regressions (test suite passes, no tests added or removed)
- Build still succeeding
- A clear roadmap of what to fix next, organized by severity and linked to existing Agent Teams (48-56 etc.) for execution
