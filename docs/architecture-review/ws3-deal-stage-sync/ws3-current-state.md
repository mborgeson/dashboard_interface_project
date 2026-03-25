# WS3: Deal Stage Sync -- Current State

**Date:** 2026-03-25
**Scope:** How deal stage synchronization from SharePoint folder structure works today

---

## 1. Overview

Deal stage sync is a **unidirectional** process: SharePoint folder structure drives the deal stage in the database. When the file monitor detects that a deal's files have moved from one stage folder to another (e.g., from `1) Initial UW and Review` to `0) Dead Deals`), it updates the `deals.stage` column accordingly.

There is **no bidirectional sync** -- the dashboard cannot move files between SharePoint folders. Users who want to change a deal's stage in SharePoint must do so manually; the dashboard will pick up the change on the next polling cycle.

---

## 2. DealStage Enum

**File:** `backend/app/models/deal.py` (lines 28-36)

```python
class DealStage(StrEnum):
    DEAD = "dead"
    INITIAL_REVIEW = "initial_review"
    ACTIVE_REVIEW = "active_review"
    UNDER_CONTRACT = "under_contract"
    CLOSED = "closed"
    REALIZED = "realized"
```

- 6 canonical stages, stored as lowercase strings via `values_callable`.
- The `stage` column on the `Deal` model uses `Enum(DealStage, values_callable=...)` (line 80-85).
- A composite index `ix_deals_stage_stage_order` supports Kanban board queries.

---

## 3. How Folder Moves Are Detected

### 3.1 Polling Cycle

The `SharePointFileMonitor` (file: `backend/app/services/extraction/file_monitor.py`) uses polling-based detection:

1. `check_for_changes()` (line 119) calls `self.client.find_uw_models()` to get the current file listing from SharePoint.
2. It retrieves stored state from the `monitored_files` table via `_get_stored_state()` (line 222).
3. `_detect_changes()` (line 235) compares current vs stored files to identify added/modified/deleted files.
4. `_update_stored_state()` (line 330) reconciles the database with the current SharePoint state.

### 3.2 Stage Change Detection Within _update_stored_state()

Lines 349-404 in `file_monitor.py`:

```python
# Track stage changes for deal sync
stage_changes: list[tuple[str, str]] = []  # (deal_name, new_stage)

for file in files:
    if file.path in stored_files:
        existing = stored_files[file.path]
        # Detect folder move (deal_stage changed)
        if file.deal_stage and existing.deal_stage != file.deal_stage:
            stage_changes.append((file.deal_name, file.deal_stage))
        existing.deal_stage = file.deal_stage
        ...
    else:
        # New file -- deal_stage set from folder inference
        new_file = MonitoredFile(..., deal_stage=file.deal_stage)
        ...

# Sync deal stages when files move between stage folders
if stage_changes:
    await self._sync_deal_stages(stage_changes)
```

The key mechanism: each `SharePointFile` carries a `deal_stage` field (set during discovery via `_infer_deal_stage()`). When the stored `MonitoredFile.deal_stage` differs from the incoming `SharePointFile.deal_stage`, a stage change is recorded.

---

## 4. _sync_deal_stages() Method

**File:** `backend/app/services/extraction/file_monitor.py` (lines 406-466)

This method receives a list of `(deal_name, new_stage_str)` tuples and updates matching `Deal` records:

1. **Validate stage string:** Converts `new_stage_str` to a `DealStage` enum. Invalid values are logged and skipped (line 428-435).
2. **Match deal by name:** Uses a case-insensitive query with two match strategies (line 438-446):
   - Exact match: `func.lower(Deal.name) == func.lower(deal_name)`
   - Prefix match: `func.lower(Deal.name).like(func.lower(deal_name) + " (%")` -- handles the `"Name (City, ST)"` naming convention.
   - Filters out soft-deleted deals: `Deal.is_deleted.is_(False)`.
3. **Update if changed:** For each matched deal where `deal.stage != target_stage`, sets (line 449-453):
   - `deal.stage = target_stage`
   - `deal.stage_updated_at = datetime.now(UTC)`
4. **Commit:** A single `db.commit()` after all updates (line 463).

### Return Value

Returns the count of deals actually updated (where stage changed). Zero if all deals were already in the target stage or no matches found.

---

## 5. Deal.update_stage() Method

**File:** `backend/app/models/deal.py` (lines 185-190)

```python
def update_stage(self, new_stage: DealStage) -> None:
    """Update the deal stage with timestamp."""
    self.stage = new_stage
    self.stage_updated_at = datetime.now(UTC)
```

This is a convenience method on the model. However, `_sync_deal_stages()` does **not** call this method -- it sets `deal.stage` and `deal.stage_updated_at` directly (lines 451-452). The CRUD layer's `update_stage()` method (`backend/app/crud/crud_deal.py`, line 294-314) also sets stage directly without calling `Deal.update_stage()` or setting `stage_updated_at`.

### Inconsistency: stage_updated_at Not Always Set

| Caller | Sets stage_updated_at? |
|--------|----------------------|
| `_sync_deal_stages()` (file_monitor) | Yes (line 452) |
| `CRUDDeal.update_stage()` (Kanban drag-drop) | **No** |
| `_batch_update_deal_stages()` (extraction sync) | **No** |
| `Deal.update_stage()` model method | Yes (line 190), but rarely called |

---

## 6. New Deal Default Stage

**File:** `backend/app/crud/extraction.py` (lines 525-528)

When the extraction pipeline discovers a new property and creates a corresponding Deal, it defaults to `DealStage.DEAD`:

```python
# Determine deal stage from folder structure or default to dead
# (new imports without an explicit stage are unreviewed -- default dead,
# not initial_review, to avoid polluting the kanban board)
deal_stage = DealStage.DEAD
if prop_name in stages:
    with contextlib.suppress(ValueError):
        deal_stage = DealStage(stages[prop_name])
```

This was a deliberate decision -- defaulting to DEAD prevents unreviewed imports from appearing on the active Kanban board. If the extraction pipeline has folder-based stage information, it overrides the default.

The Deal model's column definition defaults to `DealStage.INITIAL_REVIEW` (line 82), but the extraction sync code overrides this at insertion time.

---

## 7. Additional Stage Sync Path: _batch_update_deal_stages()

**File:** `backend/app/crud/extraction.py` (lines 590-637)

A separate batch sync runs during `sync_extracted_to_properties()`, updating deal stages based on the `property_stages` dict built during extraction. This uses the same name-matching logic (exact + prefix) but:

- Does **not** set `stage_updated_at`
- Does **not** emit WebSocket notifications
- Does **not** log individual stage changes (only returns a count)

---

## 8. WebSocket Notifications for Stage Changes

**File:** `backend/app/api/v1/endpoints/deals/pipeline.py` (lines 145-157)

When a user changes a deal's stage via the Kanban board (dashboard UI), the pipeline endpoint emits a WebSocket notification:

```python
ws_manager = get_websocket_manager()
await ws_manager.notify_deal_update(
    deal_id=deal_id,
    action="stage_changed",
    data={...},
)
```

However, when `_sync_deal_stages()` or `_batch_update_deal_stages()` updates stages from SharePoint folder moves, **no WebSocket notification is emitted**. Connected dashboard clients will not see real-time updates for SharePoint-originated stage changes.

---

## 9. stage_updated_at Column

**File:** `backend/app/models/deal.py` (lines 172-176)

```python
stage_updated_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
)
```

Used by:
- Analytics endpoints to show recent stage movements (`backend/app/api/v1/endpoints/analytics.py`, lines 245, 252-254)
- Migration `152c800e6789` that fixed deal stages also set `stage_updated_at` for affected deals

---

## 10. Polling Frequency

- Default: 30-minute intervals (`FILE_MONITOR_INTERVAL_MINUTES`, see `backend/app/core/config.py`)
- Configurable via settings
- This means a folder move in SharePoint can take up to 30 minutes to be reflected in the dashboard

---

## 11. Test Coverage

**File:** `backend/tests/test_services/test_file_monitor.py` (lines 1057-1155)

The `TestSyncDealStages` class covers:
- `test_sync_updates_deal_stage` -- folder move updates Deal.stage and sets stage_updated_at
- `test_sync_no_change_when_same_stage` -- no update when already in target stage
- `test_sync_invalid_stage_skipped` -- invalid stage strings are silently skipped
- `test_sync_multiple_stage_changes` -- multiple deals updated in one call

---

## 12. Key File Reference

| File | Lines | Role |
|------|-------|------|
| `backend/app/services/extraction/file_monitor.py` | 406-466 | `_sync_deal_stages()` -- core sync logic |
| `backend/app/services/extraction/file_monitor.py` | 330-404 | `_update_stored_state()` -- stage change detection |
| `backend/app/models/deal.py` | 28-36 | `DealStage` enum definition |
| `backend/app/models/deal.py` | 80-85 | `stage` column with enum + index |
| `backend/app/models/deal.py` | 172-176 | `stage_updated_at` column |
| `backend/app/models/deal.py` | 185-190 | `update_stage()` model method |
| `backend/app/crud/crud_deal.py` | 294-314 | `CRUDDeal.update_stage()` for Kanban |
| `backend/app/crud/extraction.py` | 525-528 | New deal default stage (DEAD) |
| `backend/app/crud/extraction.py` | 590-637 | `_batch_update_deal_stages()` batch sync |
| `backend/app/api/v1/endpoints/extraction/common.py` | 32-39 | `STAGE_FOLDER_MAP` dict |
| `backend/app/extraction/sharepoint.py` | 662-698 | `_infer_deal_stage()` string matching |
| `backend/app/models/file_monitor.py` | 88 | `MonitoredFile.deal_stage` column |
| `backend/app/api/v1/endpoints/deals/pipeline.py` | 125-157 | Kanban stage update + WebSocket notify |
