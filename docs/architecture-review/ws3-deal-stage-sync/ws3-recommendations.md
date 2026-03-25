# WS3: Deal Stage Sync -- Prioritized Recommendations

**Date:** 2026-03-25
**Scope:** Prioritized action items for improving deal stage synchronization

---

## Priority Definitions

| Priority | Meaning | Timeline |
|----------|---------|----------|
| **P0** | Must fix before production | Sprint 1 (this cycle) |
| **P1** | Should fix before production | Sprint 2 (next cycle) |
| **P2** | Technical debt / nice-to-have | Backlog |

---

## P0: Must Fix Before Production

### R-01: Audit Trail for Stage Changes (StageChangeLog Model + Migration)

**Gaps addressed:** G-01

**What:** Create a `StageChangeLog` model that records every deal stage transition with full context: old stage, new stage, source (sharepoint_sync, user_kanban, extraction_sync, manual_override), user ID (if applicable), timestamp, and optional reason/metadata.

**Why:** Without this, there is no way to answer "When did this deal change stage?" or "Was this change user-initiated or automated?" This is a compliance and operational visibility requirement.

**Implementation:**
1. Create `backend/app/models/stage_change_log.py` with the `StageChangeLog` model and `StageChangeSource` enum.
2. Create Alembic migration to add the `stage_change_logs` table.
3. Register model in `backend/app/db/base.py` and `backend/app/models/__init__.py`.
4. Create a central `change_deal_stage()` function that all stage-changing code paths call.
5. Retrofit existing callers:
   - `_sync_deal_stages()` in `file_monitor.py`
   - `CRUDDeal.update_stage()` in `crud_deal.py`
   - `_batch_update_deal_stages()` in `extraction.py`
6. Write tests covering all sources.

**Effort:** M (Medium) -- new model, migration, function, retrofit 3 callers

**Risk if deferred:** Stage changes in production are untraceable; cannot investigate incorrect stage assignments.

---

### R-02: Unify Folder Mapping to Single Source of Truth

**Gaps addressed:** G-02, G-06, G-09

**What:** Create `backend/app/services/extraction/stage_mapping.py` as the single canonical mapping. Replace `_infer_deal_stage()` substring matching with path-component-based lookup against the canonical dict. Replace `STAGE_FOLDER_MAP` in `common.py` with a derived import.

**Why:** Two independent mapping systems with different logic are a maintenance liability and a correctness risk. The substring matching in `_infer_deal_stage()` has known fragility (deal name collisions, order-dependent behavior).

**Implementation:**
1. Create `stage_mapping.py` with `FOLDER_TO_STAGE`, `STAGE_TO_FOLDER`, `FOLDER_ALIASES`, and `resolve_stage()`.
2. Refactor `_infer_deal_stage()` in `sharepoint.py` to extract path components and call `resolve_stage()`.
3. Replace `STAGE_FOLDER_MAP` in `common.py` with an import from `stage_mapping.py`.
4. Fix frontend folder names in `src/features/deals/utils/sharepoint.ts` and `src/components/quick-actions/QuickActionButton.tsx` to match the actual SharePoint folder names.
5. Add tests for the new `resolve_stage()` function including edge cases (deal name collision, unknown folders, alias matching).

**Effort:** S (Small) -- new module, refactor 2 files, update 2 frontend files

**Risk if deferred:** Same deal gets different stages depending on local vs SharePoint discovery path; deal name collisions cause wrong stage assignment.

---

## P1: Should Fix Before Production

### R-03: Stage Change WebSocket Notifications

**Gaps addressed:** G-04

**What:** Emit WebSocket notifications when `_sync_deal_stages()` or `_batch_update_deal_stages()` updates deal stages. Use the existing `ws_manager.notify_deal_update()` infrastructure.

**Why:** Dashboard users currently do not see real-time updates for SharePoint-originated stage changes. The Kanban board shows stale data until the next page refresh.

**Implementation:**
1. Import `get_websocket_manager` in `file_monitor.py`.
2. After committing stage changes in `_sync_deal_stages()`, iterate changed deals and call `ws_manager.notify_deal_update()`.
3. For bulk moves (>5 deals), emit a single `deals_bulk_stage_change` event instead.
4. Add the same notification to `_batch_update_deal_stages()` in `extraction.py` (or convert it to use the central `change_deal_stage()` function).

**Effort:** S (Small) -- add notification calls to 2 existing functions

**Dependencies:** None (WebSocket infrastructure already exists in `backend/app/services/websocket_manager.py`)

---

### R-04: Deletion Handling Policy (Mark DEAD, Not Delete)

**Gaps addressed:** G-07

**What:** When the file monitor detects that all files for a deal have been removed from SharePoint, automatically move the deal to DEAD (unless it is CLOSED or REALIZED).

**Why:** Orphaned deals that lost their files remain in their last stage indefinitely. Without a policy, the Kanban board accumulates stale deals.

**Implementation:**
1. After `_update_stored_state()` marks files as inactive, query for deals that have zero active `MonitoredFile` records.
2. For each orphaned deal not in CLOSED or REALIZED, call `change_deal_stage()` with source `SHAREPOINT_SYNC` and reason `"All files removed from SharePoint"`.
3. Make the policy configurable via `STAGE_SYNC_DELETE_POLICY` setting (options: `mark_dead`, `ignore`).
4. Protect CLOSED and REALIZED deals via `STAGE_SYNC_PROTECT_CLOSED` setting.

**Effort:** S (Small) -- query + conditional stage change after existing code

---

### R-05: Fix stage_updated_at Inconsistency

**Gaps addressed:** G-03

**What:** Ensure `stage_updated_at` is always set when a deal's stage changes, regardless of the code path.

**Why:** The analytics dashboard relies on `stage_updated_at` to show recent stage movements. Deals changed via Kanban or extraction sync have `stage_updated_at = NULL` and are invisible to analytics.

**Implementation:**
1. If implementing R-01 (central `change_deal_stage()` function), this is automatic -- the function always sets `stage_updated_at`.
2. As a quick fix without R-01: add `deal.stage_updated_at = datetime.now(UTC)` to:
   - `CRUDDeal.update_stage()` (`crud_deal.py` line 307)
   - `_batch_update_deal_stages()` (`extraction.py` line 632-634)

**Effort:** XS (Extra Small) -- add one line to 2 functions

**Note:** This is resolved for free if R-01 is implemented first, since all paths would go through `change_deal_stage()`.

---

### R-06: Bulk Move Batch Processing

**Gaps addressed:** G-08

**What:** Replace the N-query-per-deal pattern in `_sync_deal_stages()` with a single batch SELECT, then match deals in-memory.

**Why:** Performance optimization for bulk folder reorganizations. Currently executes one DB query per deal name.

**Implementation:**
1. Collect all deal names from `stage_changes` list.
2. Build a single `SELECT Deal WHERE name IN (...)` query with OR conditions.
3. Match deals to their target stages in Python.
4. Commit all updates in one transaction.

**Effort:** S (Small) -- refactor the inner loop of `_sync_deal_stages()`

**Note:** `_batch_update_deal_stages()` in `extraction.py` already uses the batch pattern (lines 612-621). Align `_sync_deal_stages()` to match.

---

## P2: Technical Debt / Nice-to-Have

### R-07: Stage Change Dashboard Widget (History Timeline)

**Gaps addressed:** Visibility improvement

**What:** Add a "Stage History" section to the Deal Detail Modal showing a timeline of all stage transitions.

**Implementation:**
1. Create API endpoint: `GET /api/v1/deals/{deal_id}/stage-history`
2. Create frontend component: `StageHistoryTimeline` showing chronological entries with source icons (user, system, SharePoint).
3. Add to Deal Detail Modal as a collapsible section (same pattern as Proforma Returns).

**Effort:** M (Medium) -- new endpoint, new component, modal integration

**Dependencies:** R-01 (StageChangeLog model must exist)

---

### R-08: Manual Stage Override with Reason

**Gaps addressed:** G-05 (partial -- conflict awareness)

**What:** When a user changes a deal's stage via the Kanban board, allow them to optionally provide a reason. If the stage was recently changed by SharePoint sync, show a warning.

**Implementation:**
1. Add optional `reason` field to the stage update API request.
2. In the pipeline endpoint, check `StageChangeLog` for recent sync-originated changes. If the last change was from SharePoint sync within 24 hours, return a warning in the response.
3. Frontend: show a confirmation dialog if the deal's stage was recently auto-synced.

**Effort:** S (Small) -- API field addition, conditional check, UI dialog

**Dependencies:** R-01 (StageChangeLog must exist for conflict detection)

---

### R-09: Stage Mapping API Endpoint

**Gaps addressed:** G-09 (frontend alignment)

**What:** Expose the canonical folder mapping via `GET /api/v1/extraction/stage-mapping` so the frontend can fetch the correct folder names dynamically instead of hardcoding them.

**Implementation:**
1. Add endpoint in extraction router.
2. Return `FOLDER_TO_STAGE` and `STAGE_TO_FOLDER` as JSON.
3. Frontend: fetch on app init, cache in a store.

**Effort:** XS (Extra Small) -- one endpoint, one frontend hook

**Dependencies:** R-02 (canonical mapping module must exist)

---

### R-10: Handle Non-Canonical Stages Explicitly

**Gaps addressed:** G-11

**What:** For folders that `_infer_deal_stage()` maps to non-DealStage values (archive, pipeline, loi, due_diligence), define explicit behavior instead of silent drop.

**Options:**
- **Option A:** Expand `DealStage` enum to include these stages. Requires migration + frontend Kanban columns.
- **Option B:** Map them to the closest canonical stage (e.g., pipeline -> initial_review, loi -> under_contract, archive -> dead, due_diligence -> under_contract).
- **Option C (recommended):** Add `FOLDER_ALIASES` in the canonical mapping that maps these to existing stages, and log the alias resolution.

**Effort:** XS-S depending on option chosen

---

## Implementation Order

```
R-02 (Unified Mapping) ─────> R-01 (Audit Trail) ─────> R-05 (stage_updated_at)
                                       |                          |
                                       v                          v
                               R-03 (WebSocket)           R-06 (Batch Queries)
                                       |
                                       v
                               R-04 (Deletion Policy)
                                       |
                                       v
                               R-07 (History UI) ─────> R-08 (Manual Override)
                                       |
                                       v
                               R-09 (Mapping API) ─────> R-10 (Non-Canonical)
```

**Recommended sprint plan:**
- **Sprint 1:** R-02, R-01, R-05 (foundation: canonical mapping + audit trail)
- **Sprint 2:** R-03, R-04, R-06 (real-time: notifications, policies, performance)
- **Backlog:** R-07, R-08, R-09, R-10 (UI enhancements)
