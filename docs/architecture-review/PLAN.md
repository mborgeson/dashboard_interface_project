# Architecture Review — Phased Execution Plan

**Date**: 2026-03-24
**Branch**: `main` at `5bfc8d4`
**Baseline**: ~4,230+ tests passing, zero TS build errors
**Prior Reviews**: findings-and-recommendations.md (69 open, 2026-03-10), remediation-plan-2026-03-11.md (73 findings, 5 waves)

---

## Current State Summary

The codebase has been through two rounds of review (Architecture Review v2: 71 findings, Dashboard Review: 73 findings) and a tech debt remediation (62/76 items resolved). Key infrastructure already in place:

- **SharePoint integration**: Graph API via MSAL (`extraction/sharepoint.py`), aiohttp-based
- **File monitoring**: Polling-based (APScheduler, 30-min interval), database-backed state store
- **Deal stage sync**: Already implemented (commit `0d09ae7`) — folder moves → stage updates
- **Extraction pipeline**: file_filter → fingerprint → extractor → reference_mapper → bulk upsert
- **Middleware chain**: RequestID, Origin, Error, Security, ETag, RateLimit, Metrics, CORS
- **Auth**: JWT with refresh token rotation (backend), but frontend doesn't use refresh (F-005)
- **Caching**: Redis preferred with in-memory fallback (Redis init commented out)
- **11 ADRs** documented

### Known Open Critical/High Issues (from prior reviews)

| ID | Issue | Status |
|----|-------|--------|
| F-001 | Users endpoints use in-memory demo data | OPEN |
| F-002 | Health probes guarded by require_admin | OPEN |
| F-003 | Report generation has no background worker | OPEN |
| F-004 | WebSocket token doesn't check blacklist | OPEN |
| F-005 | Frontend doesn't use refresh token | OPEN |
| F-006 | Financial calc libraries have no tests | OPEN |
| F-007 | Transaction DELETE/Restore only require_viewer | OPEN |
| S-01 | Demo credentials in config defaults | From remediation plan |
| D-11 | Sync sessions in async extraction endpoints | From remediation plan |

---

## Phase 1: Discovery & Audit (Coordinator — Single Agent)

**Estimated effort**: 2-4 hours
**Approach**: Read every layer of the codebase, synthesize with prior reviews, produce 7 discovery documents.

### What's Different From Prior Reviews

Prior reviews (v2 + remediation) produced excellent findings but were organized by team/severity. This review reorganizes by architectural layer for actionability and adds the WS2/WS3/WS4 workstreams that were never covered.

| Step | Output | Scope | Notes |
|------|--------|-------|-------|
| 1.1 | `01-project-structure.md` | Directory map, entry points, scheduled jobs | Incorporates 15+ commits since last review |
| 1.2 | `02-extraction-layer.md` | SharePoint client, file monitor, scheduler, file filter, extractor | Focus on what exists vs. what WS2 proposes |
| 1.3 | `03-database-schema.md` | All models, migrations, relationships, indexes | Delta from `database-schema.md` (2026-03-10), 4+ new migrations since |
| 1.4 | `04-etl-mapping.md` | cell_mapping.py, reference_mapper.py, transforms | Baseline for WS4 mapping audit |
| 1.5 | `05-dashboard-api.md` | FastAPI routes, Dash remnants, frontend data flows | Check which F-xxx findings were actually fixed |
| 1.6 | `06-testing-errors.md` | Test inventory, error handling audit | ~4,230+ tests — verify claimed fixes landed |
| 1.7 | `07-discovery-summary.md` | Mermaid diagrams, critical findings, risk map | Unified view |

**Dependencies**: None. This is the foundation for all subsequent work.

---

## Phase 2: Agent Team Execution (Parallel Workstreams)

### Agent Assignment

| Agent | Workstream | Focus |
|-------|-----------|-------|
| **architect-agent** | WS1: General Improvements | Code health, performance, observability |
| **data-engineer-agent** | WS2: Extraction Automation | Event-driven pipeline, Graph API webhooks/delta |
| **data-engineer-agent** | WS4: Data Integrity | Mapping manifest, validation framework |
| **backend-agent** | WS3: Deal Stage Sync | Folder sync enhancement, bidirectional sync evaluation |

### WS1: General Improvements (architect-agent)

**Scope adjustment**: Since two prior reviews already exist, this workstream focuses on:
1. **Verification**: Which of the 69+73 findings were actually fixed in code (not just planned)?
2. **New findings**: Anything introduced in the 15 commits since last review
3. **Cross-cutting patterns**: Recurring issues across modules (e.g., mixed sync/async, hardcoded values)
4. **Observability gap**: Structured logging partially implemented (loguru), but no correlation IDs in practice

**Deliverables**: `ws1-current-state.md`, `ws1-gap-analysis.md`, `ws1-recommendations.md`, `ws1-implementation-plan.md`

**Estimated effort**: 4-6 hours

### WS2: Extraction Automation (data-engineer-agent)

**Current state**: Polling-based (APScheduler, 30-min). SharePointClient already uses Graph API + MSAL.

**Key evaluation**:

| Approach | Feasibility | Notes |
|----------|------------|-------|
| A: Graph API Webhooks | Requires public endpoint or Azure relay | WSL2 dev environment has no public URL; needs ngrok or Azure deployment |
| B: Graph API Delta Queries | Most practical for current setup | `SharePointClient` already has Graph API auth; delta endpoint is additive |
| C: Hybrid | Best for production | Webhook for real-time + delta for reconciliation |

**Assumption**: Current deployment target is single-server (Oracle Free Tier or Hetzner CX22), not Azure. This affects webhook feasibility.

**Deliverables**: `ws2-current-state.md`, `ws2-gap-analysis.md`, `ws2-architecture-proposal.md`, `ws2-recommendations.md`, `ws2-implementation-plan.md`

**Estimated effort**: 4-6 hours

### WS3: Deal Stage Sync (backend-agent)

**Current state**: Basic sync already implemented in `file_monitor.py:_sync_deal_stages()`. Detects folder moves during polling, updates Deal.stage. Unidirectional (SharePoint → DB).

**Remaining gaps**:
1. No audit trail for stage changes (just loguru logs, not persisted)
2. No conflict resolution (what if someone changes stage in dashboard AND moves folder?)
3. Bulk moves not explicitly handled
4. No folder→stage mapping documentation (implicit in DealStage enum + folder naming convention)
5. Deletion handling undefined (archive? keep as dead?)

**Key decision**: Should bidirectional sync be evaluated, or is SharePoint → DB sufficient?

**Deliverables**: `ws3-current-state.md`, `ws3-folder-mapping.md`, `ws3-gap-analysis.md`, `ws3-architecture-proposal.md`, `ws3-recommendations.md`, `ws3-implementation-plan.md`

**Estimated effort**: 3-4 hours

### WS4: Data Completeness & Mapping Integrity (data-engineer-agent)

**Current state**:
- `cell_mapping.py` + `reference_mapper.py` define ~1,179 cell mappings
- 66/66 files processed in deferred groups expansion (2026-03-06)
- 28 ungrouped files remaining (next priority per MEMORY.md)
- `extracted_values` table stores per-field results
- Change detection via SHA-256 hash comparison
- `error_category` column exists but never populated

**Deliverables**: `ws4-current-state.md`, `ws4-mapping-manifest.md`, `ws4-gap-analysis.md`, `ws4-validation-framework.md`, `ws4-recommendations.md`, `ws4-implementation-plan.md`

**Estimated effort**: 4-6 hours

---

## Phase 3: Coordinator — Unified Deliverables

**Input**: All Phase 2 outputs from 3 agents across 4 workstreams
**Estimated effort**: 2-3 hours

### Final Documents

1. `EXECUTIVE-SUMMARY.md` — 1-page overview with before/after mermaid diagrams
2. `ARCHITECTURE-CURRENT.mermaid` — Current data flow
3. `ARCHITECTURE-PROPOSED.mermaid` — Proposed with all improvements
4. `UNIFIED-RECOMMENDATIONS.md` — Merged, deduplicated, prioritized P0/P1/P2
5. `IMPLEMENTATION-ROADMAP.md` — BMAD epics → stories → tasks with T-shirt sizing
6. `TASKS.md` (project root) — Flat checklist for execution tracking
7. `SECURITY-FINDINGS.md` — If any new security issues found

### Deduplication Strategy

Prior reviews produced overlapping findings (F-005 and F-029 are the same issue from different perspectives; S-01 and F-001 overlap). The coordinator will:
1. Cross-reference all three finding sets (v2 findings, remediation plan, this review)
2. Mark truly-resolved items with commit evidence
3. Merge duplicates into canonical entries
4. Assign final priority based on production deployment criticality

---

## Risks & Assumptions

| Risk | Mitigation |
|------|-----------|
| Prior review findings may have been fixed but not verified | WS1 explicitly verifies fixes in code |
| Graph API webhook requires public endpoint (not available in WSL2 dev) | WS2 will recommend delta queries as primary, webhooks deferred to production deploy |
| `tech-debt/remediation-phase1` branch not yet merged to main | Review runs against `main`; findings may already be fixed on that branch |
| Cell mapping fragility — changes break financial data | WS4 treats mapping audit as read-only; no changes to cell_mapping.py without explicit instruction |
| Session size — deep codebase read may hit context limits | Phase 1 uses parallel agents with scoped reads; Phase 2 agents get only their workstream context |

---

## Dependencies Between Phases

```
Phase 1 (Discovery)
    ├── WS1 depends on: Phase 1 discovery docs
    ├── WS2 depends on: 02-extraction-layer.md specifically
    ├── WS3 depends on: 02-extraction-layer.md + 03-database-schema.md
    └── WS4 depends on: 04-etl-mapping.md + 03-database-schema.md

Phase 2 (all WS run in parallel)
    └── Phase 3 depends on: ALL Phase 2 deliverables
```

---

## Execution Timeline

| Phase | Duration | Parallelism |
|-------|----------|-------------|
| Phase 1: Discovery | 2-4h | Single coordinator agent, 7 sequential docs |
| Phase 2: WS1+WS2+WS3+WS4 | 4-6h | 3 agents in parallel (data-engineer handles WS2+WS4 sequentially) |
| Phase 3: Unification | 2-3h | Single coordinator |
| **Total** | **8-13h** | |
