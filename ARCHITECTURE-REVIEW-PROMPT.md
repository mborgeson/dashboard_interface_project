# B&R Capital Dashboard — Architecture Review & Improvement Plan

## Instructions for Claude Code

### Pre-Execution: Skills Loading
Before starting any work, read and internalize these skill files. Apply their patterns, checklists, and frameworks throughout the review:

```
/mnt/skills/user/senior-architect/SKILL.md
/mnt/skills/user/senior-data-engineer/SKILL.md
/mnt/skills/user/senior-backend/SKILL.md
/mnt/skills/user/code-reviewer/SKILL.md
/mnt/skills/user/senior-fullstack/SKILL.md
```

### Behavioral Rules
- Treat me as a senior developer. Direct answers, no preamble or basic explanations.
- Show multiple approaches with tradeoffs; lead with the production-ready solution.
- No hedging. No unnecessary caveats.
- Use BMAD methodology for breaking down deliverables into epics → stories.
- Use functional programming style where applicable.
- Prefer dynamic verification over hard-coded values.
- When providing code: break into logical sections with approach comments, then provide comprehensive implementation combining all components.
- When making changes to documents: regenerate the full updated version, not partial diffs.
- Use file-based state management (TASKS.md, PROGRESS.md) for session continuity.

### Interaction Protocol — CRITICAL
**Before executing any work**, complete these steps in order:

1. **Read the entire codebase** relevant to this pipeline (extraction, DB, dashboard layers).
2. **Generate a Phased Execution Plan** as a markdown document (`/docs/architecture-review/PLAN.md`) outlining:
   - What you will do in each phase
   - What agents will handle which workstreams
   - Estimated scope/complexity per phase
   - Dependencies between phases
   - Risks or assumptions you're making
3. **Ask me any questions** you have before proceeding. This includes:
   - Ambiguities about the SharePoint file structure or naming conventions
   - Unclear deal stage mappings or folder hierarchy
   - Which Excel templates are in active use vs. legacy
   - Whether certain integrations (Graph API, Azure Functions, etc.) are already partially set up
   - Authentication method currently used for SharePoint access
   - Any files or directories you can't locate but expect to exist
   - Priorities or constraints I haven't stated
4. **Wait for my answers** before moving to execution.
5. **Only after I confirm the plan**, begin executing phase by phase.

---

## Project Context

**System:** B&R Capital Dashboard — real estate underwriting data extraction and analytics platform.

**Pipeline:** SharePoint Excel files → Python extraction/monitoring service → PostgreSQL → Dash/FastAPI dashboard (with React/TypeScript/Vite frontend in progress).

**Stack:**
- Python 3.12, conda environment
- PostgreSQL on port 5433 (Windows-side, accessed from WSL2 via dynamic host resolution)
- SQLAlchemy 2.0 async
- FastAPI backend
- Dash frontend (migrating to React/TypeScript/Vite)
- WSL2 Ubuntu development environment

**Key Projects/Repos:**
- `dashboard_interface_project` — primary dashboard
- `mf_market_ranking` — market ranking model (separate but related)

**Data Sources:** SharePoint-hosted Excel workbooks containing deal underwriting data, property financials, and portfolio metrics. Files are organized by deal stage folders.

---

## Phase 1: Discovery & Audit (Single Agent — Coordinator)

Read the following in order, building a complete mental model. At each step, write findings to `/docs/architecture-review/discovery/`.

### 1.1 Project Structure
- Read CLAUDE.md, README, and any configuration files
- Map the directory structure and module boundaries
- Identify entry points, scripts, and scheduled jobs
- Document: `01-project-structure.md`

### 1.2 SharePoint Extraction Layer
- Identify the extraction/monitoring service (entry point, scheduling, file detection logic)
- Map how SharePoint files are accessed (API, SDK, direct path, credentials)
- Document file detection: polling vs. event-driven, frequency, filtering
- Document: `02-extraction-layer.md`

### 1.3 Database Schema & Models
- Read all migration files, SQLAlchemy models, and raw SQL
- Map every table, relationship, constraint, index
- Identify: orphaned tables, missing indexes, denormalization patterns
- Document: `03-database-schema.md`

### 1.4 ETL / Mapping Layer
- Trace how Excel columns map to database columns
- Identify all transformation logic (type casting, normalization, calculated fields)
- Find: hardcoded mappings, magic strings, implicit assumptions
- Document: `04-etl-mapping.md`

### 1.5 Dashboard & API Layer
- Map all Dash callbacks, FastAPI endpoints, and data queries
- Identify: N+1 queries, unoptimized joins, missing pagination
- Document: `05-dashboard-api.md`

### 1.6 Testing & Error Handling
- Inventory all existing tests (unit, integration, e2e)
- Map error handling: try/except coverage, logging, alerting, failure modes
- Identify: silent failures, bare excepts, unhandled edge cases
- Document: `06-testing-errors.md`

### 1.7 Discovery Summary
Produce a single summary document that includes:
- Architecture diagram (mermaid) of current state
- Data flow diagram (mermaid) from SharePoint → DB → Dashboard
- Critical findings and risk areas
- Document: `07-discovery-summary.md`

---

## Phase 2: Agent Team Execution (Parallel Workstreams)

### Agent Team Configuration

Use Claude Agent Teams (via `claude-flow` or tmux-based orchestration) with the following team structure:

```yaml
team:
  coordinator:
    role: "Architecture Review Coordinator"
    responsibilities:
      - Merge outputs from all workstream agents
      - Resolve cross-cutting concerns and conflicts
      - Maintain TASKS.md and PROGRESS.md at project root
      - Produce final unified deliverables
      - Ensure consistency across workstream recommendations
    context:
      - All Phase 1 discovery documents
      - This prompt file
      - Project CLAUDE.md

  agents:
    - name: "architect-agent"
      role: "Senior Architect — General Improvements (WS1)"
      skills:
        - /mnt/skills/user/senior-architect/SKILL.md
        - /mnt/skills/user/code-reviewer/SKILL.md
      focus: "Architecture quality, code health, performance, observability"
      output_dir: "/docs/architecture-review/ws1-improvements/"

    - name: "data-engineer-agent"
      role: "Senior Data Engineer — Extraction Automation & Data Integrity (WS2 + WS4)"
      skills:
        - /mnt/skills/user/senior-data-engineer/SKILL.md
        - /mnt/skills/user/senior-backend/SKILL.md
      focus: "Event-driven extraction pipeline, data validation, mapping integrity"
      output_dir: "/docs/architecture-review/ws2-extraction-automation/"
      output_dir_secondary: "/docs/architecture-review/ws4-data-integrity/"

    - name: "backend-agent"
      role: "Senior Backend Engineer — Deal Stage Sync (WS3)"
      skills:
        - /mnt/skills/user/senior-backend/SKILL.md
        - /mnt/skills/user/senior-data-engineer/SKILL.md
      focus: "SharePoint folder sync, deal stage propagation, state management"
      output_dir: "/docs/architecture-review/ws3-deal-stage-sync/"
```

**Coordination Protocol:**
- Coordinator distributes Phase 1 discovery docs to all agents as shared context.
- Each agent works independently within their workstream scope.
- Agents write findings and recommendations to their designated output directories.
- If an agent identifies a cross-cutting concern (e.g., a schema change that affects multiple workstreams), it logs it to `/docs/architecture-review/cross-cutting-concerns.md` for the coordinator to resolve.
- Coordinator merges all outputs into a unified plan after agents complete.

---

### WS1: General Improvements (architect-agent)

#### Scope
Review and recommend improvements across the entire pipeline.

#### Architecture
- Evaluate separation of concerns between extraction, ETL, API, and presentation layers
- Assess async patterns: connection pooling, session management, task queuing
- Review dependency injection and service boundaries
- Check for circular imports, god modules, tight coupling

#### Code Quality
- Run code-reviewer skill analysis across the codebase
- Audit: type hints coverage, docstrings, dead code, unused imports
- Check error handling: bare excepts, swallowed errors, missing context in logs
- Evaluate: naming conventions, module organization, DRY violations

#### Performance
- Identify slow queries (missing indexes, full table scans, N+1 patterns)
- Evaluate caching strategy (or lack thereof)
- Check connection pool configuration and resource cleanup
- Review pagination in API and dashboard

#### Observability
- Recommend structured logging (JSON, correlation IDs)
- Design health check endpoints for each service layer
- Propose alerting rules: extraction failures, stale data, schema drift
- Recommend monitoring stack (lightweight — not over-engineered)

#### Deliverables
1. `ws1-current-state.md` — What exists now
2. `ws1-gap-analysis.md` — What's missing or broken
3. `ws1-recommendations.md` — Prioritized P0/P1/P2 improvements
4. `ws1-implementation-plan.md` — BMAD epics → stories

---

### WS2: Automated Extraction on SharePoint File Changes (data-engineer-agent)

#### Scope
Design and plan an event-driven extraction pipeline that triggers when SharePoint files are created, modified, or deleted.

#### Evaluation
Compare these approaches with explicit tradeoffs:

| Approach | Mechanism | Pros | Cons |
|----------|-----------|------|------|
| **A: Graph API Webhooks** | Microsoft Graph subscriptions with change notifications | Real-time, push-based, no polling overhead | Requires public endpoint or relay, subscription renewal, webhook validation |
| **B: Graph API Delta Queries** | Polling delta endpoint for incremental changes | Simpler auth, no public endpoint needed, works behind NAT | Polling latency, must manage delta tokens, heavier on API quota |
| **C: Hybrid** | Webhooks for real-time + delta polling as fallback/reconciliation | Best of both, self-healing | More complex, two code paths |

#### Pipeline Design
- File change detection → event queue → extraction worker → validation → DB upsert
- Handle: file locking (Excel files open in browser), partial uploads, concurrent edits
- Retry logic with exponential backoff and dead-letter queue
- Idempotent upserts (no duplicate records from re-processing)
- Consider worker implementation: Celery, asyncio task queue, or lightweight event loop

#### Authentication
- Evaluate: Azure AD app registration, certificate-based auth, managed identity
- Credential storage: environment variables, Azure Key Vault, or secrets manager
- Token refresh handling

#### Deliverables
1. `ws2-current-state.md` — How extraction works today
2. `ws2-gap-analysis.md` — What breaks, what's manual, what's fragile
3. `ws2-architecture-proposal.md` — Proposed pipeline with mermaid diagrams
4. `ws2-recommendations.md` — Prioritized P0/P1/P2
5. `ws2-implementation-plan.md` — BMAD epics → stories

---

### WS3: Deal Stage Folder Sync (backend-agent)

#### Scope
When a deal moves to a different stage folder in SharePoint, detect that change and propagate it to the database (and optionally vice versa).

#### Folder Structure Mapping
- Map the current SharePoint folder hierarchy to deal stages in the DB
- Document the expected folder names and their corresponding `deal_stage` values
- Handle: non-standard folder names, nested structures, legacy folders

#### Change Detection
- Detect file moves between folders (Graph API: driveItem moves change `parentReference`)
- Detect folder renames (stage name changes)
- Handle bulk operations (multiple files moved simultaneously)
- Handle deletions (deal removed from SharePoint — archive vs. delete in DB?)

#### Sync Direction
Evaluate with explicit tradeoffs:

| Direction | Description | Pros | Cons |
|-----------|-------------|------|------|
| **SharePoint → DB** (unidirectional) | SP is source of truth; DB reflects SP state | Simple, single source of truth, no conflict resolution | Dashboard can't drive stage changes |
| **DB → SharePoint** (reverse) | Dashboard drives stage changes, reflected back to SP | Power users can manage via dashboard | Requires Graph API write permissions, conflict risk |
| **Bidirectional** | Either side can initiate changes | Maximum flexibility | Complex conflict resolution, race conditions, audit trail critical |

#### State Management
- Track sync state: last known folder per deal, sync timestamps
- Conflict resolution strategy (last-write-wins, manual review queue, etc.)
- Audit trail: log every stage change with timestamp, source, previous value

#### Deliverables
1. `ws3-current-state.md` — How deal stages are managed today
2. `ws3-folder-mapping.md` — SharePoint folder → DB stage mapping table
3. `ws3-gap-analysis.md` — What's missing, what breaks
4. `ws3-architecture-proposal.md` — Proposed sync design with mermaid diagrams
5. `ws3-recommendations.md` — Prioritized P0/P1/P2
6. `ws3-implementation-plan.md` — BMAD epics → stories

---

### WS4: Data Completeness & Mapping Integrity (data-engineer-agent)

#### Scope
Ensure every field in the source Excel templates is correctly extracted, transformed, and stored in the database — with no silent drops, truncation, or type coercion errors.

#### Mapping Audit
- Inventory every column in every active Excel template
- Map each column to its corresponding DB column (or document that it's unmapped)
- Produce a **mapping manifest**: `Excel Column → Transform → DB Column → Dashboard Field`
- Flag: columns that exist in Excel but not DB, columns in DB with no Excel source

#### Data Quality Checks
- Type validation: ensure Excel types (dates, currencies, percentages) map correctly to PG types
- Null handling: identify which fields allow nulls, which have defaults, which silently drop
- Truncation: check varchar lengths vs. actual data lengths
- Precision: verify decimal/float precision for financial calculations
- Encoding: check for Unicode issues, special characters in property names/addresses

#### Validation Layer Design
- Row-level validation: checksums, field-count assertions, required-field checks
- Batch-level validation: before/after record counts, sum-of-amounts reconciliation
- Schema drift detection: alert when Excel template structure changes
- Propose a validation framework (pydantic models, pandera, great_expectations, or custom)

#### Reconciliation
- Design a reconciliation report: what was extracted vs. what's in the DB
- Dashboard widget or standalone report showing data freshness and completeness
- Alerting: email/Slack notification when records fail validation or counts drift

#### Deliverables
1. `ws4-current-state.md` — Current mapping and validation coverage
2. `ws4-mapping-manifest.md` — Complete Excel → DB → Dashboard field map
3. `ws4-gap-analysis.md` — Missing fields, broken mappings, silent failures
4. `ws4-validation-framework.md` — Proposed validation architecture
5. `ws4-recommendations.md` — Prioritized P0/P1/P2
6. `ws4-implementation-plan.md` — BMAD epics → stories

---

## Phase 3: Coordinator — Unified Deliverables

After all agents complete, the coordinator produces:

### Final Documents (in `/docs/architecture-review/`)

1. **`EXECUTIVE-SUMMARY.md`**
   - 1-page overview of findings, risks, and top recommendations
   - Current state vs. proposed state (before/after mermaid diagrams)

2. **`ARCHITECTURE-CURRENT.mermaid`**
   - Complete data flow diagram of current system

3. **`ARCHITECTURE-PROPOSED.mermaid`**
   - Complete data flow diagram of proposed system with all improvements

4. **`UNIFIED-RECOMMENDATIONS.md`**
   - All recommendations across workstreams, merged and deduplicated
   - Prioritized: P0 (critical/breaking) → P1 (important) → P2 (nice-to-have)
   - Dependency map between recommendations

5. **`IMPLEMENTATION-ROADMAP.md`**
   - BMAD-style breakdown: Epics → Stories → Tasks
   - Sequenced by dependency and priority
   - Estimated effort (T-shirt sizing: S/M/L/XL)
   - Suggested sprint allocation (assuming 2-week sprints)

6. **`TASKS.md`** (project root)
   - Flat checklist of all actionable items
   - Grouped by workstream and priority
   - Checkbox format for tracking execution
   - Session-drop safe: any future Claude Code session can pick this up

7. **`SECURITY-FINDINGS.md`** (if applicable)
   - Credentials in code, SQL injection vectors, auth gaps → all flagged as P0

---

## MCP Servers Available
The following MCP servers are connected and available for use during this review:

- **Filesystem** — Direct access to project files on the local machine
- **Linear** — Create issues/stories directly from recommendations (ask before creating)
- **Slack** — Post summaries or alerts (ask before sending)
- **Google Drive** — Access any related documentation stored in Drive
- **Figma** — Generate architecture diagrams if mermaid is insufficient
- **Supabase** — If any DB inspection is needed beyond direct PG access

Use these tools proactively where they add value. If you need to create Linear issues or send Slack messages, ask me first.

---

## Constraints & Preferences

- **Stack:** Python 3.12, PostgreSQL (port 5433), SQLAlchemy 2.0 async, FastAPI, Dash
- **Style:** Ruff @ 88 chars, functional preferred, SOLID/DRY/KISS/YAGNI
- **Session management:** TASKS.md + PROGRESS.md for continuity across session drops
- **No hardcoded values:** Prefer dynamic verification commands and environment-based config
- **Auth:** Do not store or log credentials. Reference env vars or secrets manager.
- **Code output:** When recommending code changes, provide complete implementations grouped by logical section with summary comments, not partial snippets.
