# WS3: Deal Stage Sync -- Gap Analysis

**Date:** 2026-03-25
**Scope:** Identified gaps, risks, and missing capabilities in the deal stage synchronization system

---

## Gap Summary

| # | Gap | Severity | Category |
|---|-----|----------|----------|
| G-01 | No audit trail for stage changes | P0 | Data Integrity |
| G-02 | Dual mapping systems can diverge | P0 | Architecture |
| G-03 | stage_updated_at inconsistently set | P1 | Data Integrity |
| G-04 | No WebSocket notifications for sync-originated stage changes | P1 | Real-time |
| G-05 | No conflict resolution for dashboard vs SharePoint stage changes | P1 | Data Integrity |
| G-06 | _infer_deal_stage() uses fragile string matching | P1 | Robustness |
| G-07 | Deletion handling undefined | P1 | Policy |
| G-08 | Bulk folder moves not explicitly handled | P2 | Performance |
| G-09 | Frontend folder name discrepancies | P2 | Consistency |
| G-10 | 30-minute polling delay | P2 | Latency |
| G-11 | Non-canonical stages silently dropped | P2 | Completeness |

---

## G-01: No Audit Trail for Stage Changes

**Severity:** P0 -- Critical

### Problem

When a deal's stage changes (whether from SharePoint folder sync or dashboard Kanban drag-drop), the change is logged only via structlog/loguru to stdout. There is no persisted database record of:
- What the previous stage was
- What the new stage is
- When the change occurred
- What triggered the change (user action vs folder sync)
- Who made the change (for dashboard-initiated changes)

### Evidence

- `_sync_deal_stages()` at `backend/app/services/extraction/file_monitor.py` line 454: logs via `self.logger.info("deal_stage_synced_from_folder", ...)` but does not persist.
- `_batch_update_deal_stages()` at `backend/app/crud/extraction.py` line 632-634: sets `deal.stage = target_stage` with no logging at all.
- `CRUDDeal.update_stage()` at `backend/app/crud/crud_deal.py` line 307: sets stage directly, no audit record.

### Impact

- Cannot answer "When did this deal move from Active Review to Under Contract?"
- Cannot identify whether a stage change was user-initiated or system-initiated
- No way to detect or investigate erroneous stage transitions
- Analytics endpoint (`backend/app/api/v1/endpoints/analytics.py` lines 252-254) queries `stage_updated_at` for "recent stage movements" but this only tells you the last change, not the full history

### Existing Partial Coverage

The `Deal.activity_log` JSON column could theoretically store stage changes, but neither `_sync_deal_stages()` nor `CRUDDeal.update_stage()` writes to it. The `Deal.add_activity()` method exists (line 192-199) but is not called for stage transitions.

---

## G-02: Dual Mapping Systems Can Diverge

**Severity:** P0 -- Critical

### Problem

Two independent code paths map folder names to stage values:

1. `STAGE_FOLDER_MAP` in `backend/app/api/v1/endpoints/extraction/common.py` (lines 32-39) -- explicit dict, exact match
2. `_infer_deal_stage()` in `backend/app/extraction/sharepoint.py` (lines 662-698) -- substring matching, 10 patterns

These serve different contexts (local vs SharePoint) but return the same stage values. If one is updated without the other, the same deal could get different stages depending on whether it was discovered via local scan or SharePoint API.

### Divergence Risks

- Adding a new folder name variant to `_infer_deal_stage()` without updating `STAGE_FOLDER_MAP`
- `_infer_deal_stage()` matches patterns that `STAGE_FOLDER_MAP` would not (e.g., "Passed Deals" -> "dead", "Acquired Deals" -> "closed")
- The frontend has a **third** independent mapping in two locations (`src/features/deals/utils/sharepoint.ts` and `src/components/quick-actions/QuickActionButton.tsx`) with different folder names for 4 of 6 stages

### Impact

- Same deal files could be assigned different stages depending on the discovery path
- Difficult to maintain: changes must be replicated across 4 locations in 2 languages

---

## G-03: stage_updated_at Inconsistently Set

**Severity:** P1 -- High

### Problem

The `stage_updated_at` column is set by some code paths but not others:

| Code Path | Sets stage_updated_at? |
|-----------|----------------------|
| `_sync_deal_stages()` (file_monitor.py line 452) | Yes |
| `Deal.update_stage()` model method (deal.py line 190) | Yes |
| `CRUDDeal.update_stage()` (crud_deal.py line 307) | **No** |
| `_batch_update_deal_stages()` (extraction.py line 632-634) | **No** |

### Impact

- The analytics dashboard (`analytics.py` lines 252-254) queries `stage_updated_at` to show "recent stage movements." Deals whose stage was changed via Kanban drag-drop or extraction sync will have `stage_updated_at = NULL` and will be invisible to this query.
- Cannot reliably determine when a deal's stage was last changed.

---

## G-04: No WebSocket Notifications for Sync-Originated Stage Changes

**Severity:** P1 -- High

### Problem

When a user moves a deal via Kanban drag-drop, the pipeline endpoint emits a WebSocket notification (`backend/app/api/v1/endpoints/deals/pipeline.py` lines 146-157). However, when `_sync_deal_stages()` or `_batch_update_deal_stages()` updates stages from SharePoint folder moves, **no notification is emitted**.

### Impact

- Dashboard users will not see real-time stage changes when SharePoint folders are reorganized
- Kanban board may show stale positions until the next full page refresh or API poll
- Users who are watching a deal will not be alerted to stage transitions

---

## G-05: No Conflict Resolution for Dashboard vs SharePoint Stage Changes

**Severity:** P1 -- High

### Problem

A user can change a deal's stage via the Kanban board (dashboard). Independently, someone can move the deal's folder in SharePoint. When the next polling cycle runs, the SharePoint folder location will overwrite whatever the dashboard user set.

Scenario:
1. User drags deal from "Dead" to "Active Review" on Kanban board (15:00)
2. Someone moves the folder to "0) Dead Deals" in SharePoint (15:10)
3. File monitor polls at 15:30, detects stage = "dead", overwrites the user's "active_review" change

There is no conflict detection, no "last-write-wins" awareness, and no user notification that their manual change was overridden.

### Impact

- User-initiated stage changes can be silently reverted
- No mechanism to "pin" a dashboard-set stage
- No indication to users that their change was overwritten by a sync

---

## G-06: _infer_deal_stage() Uses Fragile String Matching

**Severity:** P1 -- High

### Problem

`_infer_deal_stage()` (`sharepoint.py` lines 662-698) uses `in` substring matching on the full folder path, which creates several risks:

1. **Deal name collision:** A deal named "Dead Creek Apartments" in an Active Review folder would match `"dead"` before `"active uw"` because `"dead"` is checked first.
2. **Order dependency:** The `elif` chain is order-sensitive. Rearranging conditions changes behavior.
3. **Overly broad matches:** `"dd"` matches any path containing "dd" (e.g., "Haddock Properties", "Paddington Arms").
4. **"active" ambiguity:** `"active"` in the pipeline branch (line 691) could match active_review paths if the elif order changes.

### Evidence

Test file `backend/tests/test_extraction/test_sharepoint_integration.py` (lines 573-601) covers basic cases but does not test the deal-name-collision scenario.

### Impact

- Incorrect stage assignment for deals with stage-related words in their names
- Subtle bugs that only manifest with specific deal naming patterns

---

## G-07: Deletion Handling Undefined

**Severity:** P1 -- High

### Problem

When a file is detected as deleted from SharePoint (present in DB but missing from current scan), the file monitor:
- Marks the `MonitoredFile.is_active = False` (file_monitor.py line 396-397)
- Creates a `FileChangeLog` with `change_type="deleted"` (line 276-294)
- Does **not** change the Deal's stage

There is no defined policy for what should happen to the Deal when all its files are removed from SharePoint. Should it:
- Remain in its current stage?
- Be moved to DEAD?
- Be soft-deleted?

### Impact

- Orphaned deals that no longer have files in SharePoint remain in their last-known stage
- No way to distinguish "intentionally removed" from "accidentally deleted"

---

## G-08: Bulk Folder Moves Not Explicitly Handled

**Severity:** P2 -- Medium

### Problem

If someone moves an entire stage folder's contents (e.g., moves all 30 deals from "Active UW and Review" to "Dead Deals"), the file monitor will detect each as an individual change and call `_sync_deal_stages()` with all 30 deal names. While this works functionally, there are concerns:

1. **N+1 queries:** `_sync_deal_stages()` executes one `SELECT` per deal name (file_monitor.py line 438-446), not a batch query.
2. **Single commit:** All 30 updates are committed in one `db.commit()` (good), but the logging is per-deal (N log entries).
3. **No batch notification:** No aggregate WebSocket event like "30 deals moved to Dead."

### Impact

- Performance degradation for bulk moves (30+ individual queries)
- Log noise for large reorganizations
- No aggregate awareness at the UI level

---

## G-09: Frontend Folder Name Discrepancies

**Severity:** P2 -- Medium

### Problem

The frontend STAGE_FOLDER_MAP uses different folder names than the backend for 4 of 6 stages:

| Stage | Backend | Frontend |
|---|---|---|
| active_review | `2) Active UW and Review` | `2) Active Review` |
| under_contract | `3) Deals Under Contract` | `3) Under Contract` |
| closed | `4) Closed Deals` | `4) Closed - Active Assets` |
| realized | `5) Realized Deals` | `5) Realized` |

### Impact

- SharePoint folder links generated by the frontend may point to incorrect folder paths
- Users clicking "Open in SharePoint" from the dashboard may get 404 or wrong folder

---

## G-10: 30-Minute Polling Delay

**Severity:** P2 -- Medium

### Problem

File monitor polls every 30 minutes by default (`FILE_MONITOR_INTERVAL_MINUTES`). A folder move in SharePoint will not be reflected in the dashboard for up to 30 minutes.

### Impact

- Stale stage information on the Kanban board
- Users may not trust the dashboard's stage accuracy
- Not a functional bug but a user experience concern

---

## G-11: Non-Canonical Stages Silently Dropped

**Severity:** P2 -- Medium

### Problem

`_infer_deal_stage()` returns 4 non-canonical stage values (`"archive"`, `"pipeline"`, `"loi"`, `"due_diligence"`) that have no corresponding `DealStage` enum member. When these reach `_sync_deal_stages()`, the `DealStage(new_stage_str)` conversion raises `ValueError`, which is caught and the change is silently skipped (file_monitor.py lines 428-435).

On the next polling cycle, the same "change" is detected again (since the stored `MonitoredFile.deal_stage` was updated but the Deal.stage was not), leading to repeated warning logs every 30 minutes.

### Impact

- Repeated log noise for deals in non-standard folders
- Deals in "LOI" or "Due Diligence" folders cannot have their stage tracked
- No user visibility into why certain deals are not syncing
