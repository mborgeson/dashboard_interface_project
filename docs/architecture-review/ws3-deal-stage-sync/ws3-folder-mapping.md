# WS3: Deal Stage Sync -- Folder Mapping Documentation

**Date:** 2026-03-25
**Scope:** Complete mapping between SharePoint folder names, DealStage enum values, and database stage values

---

## 1. Primary Folder Mappings (6 Canonical Stages)

### SharePoint Folder Structure

```
Deals/
  0) Dead Deals/
  1) Initial UW and Review/
  2) Active UW and Review/
  3) Deals Under Contract/
  4) Closed Deals/
  5) Realized Deals/
```

### Complete Mapping Table

| SharePoint Folder Name | DealStage Enum Member | DB `stage` Column Value | Kanban Board Column |
|---|---|---|---|
| `0) Dead Deals` | `DealStage.DEAD` | `dead` | Dead Deals |
| `1) Initial UW and Review` | `DealStage.INITIAL_REVIEW` | `initial_review` | Initial Review |
| `2) Active UW and Review` | `DealStage.ACTIVE_REVIEW` | `active_review` | Active Review |
| `3) Deals Under Contract` | `DealStage.UNDER_CONTRACT` | `under_contract` | Under Contract |
| `4) Closed Deals` | `DealStage.CLOSED` | `closed` | Closed |
| `5) Realized Deals` | `DealStage.REALIZED` | `realized` | Realized |

---

## 2. Dual Mapping Systems

There are **two independent implementations** that map folder names to stage values. They serve different contexts but can diverge.

### 2.1 STAGE_FOLDER_MAP (Explicit Dict)

**File:** `backend/app/api/v1/endpoints/extraction/common.py` (lines 32-39)

```python
STAGE_FOLDER_MAP: dict[str, str] = {
    "0) Dead Deals": "dead",
    "1) Initial UW and Review": "initial_review",
    "2) Active UW and Review": "active_review",
    "3) Deals Under Contract": "under_contract",
    "4) Closed Deals": "closed",
    "5) Realized Deals": "realized",
}
```

**Used by:** `discover_local_deal_files()` in `common.py` for local OneDrive file scanning. Iterates stage folders by exact name match against the filesystem.

**Characteristics:**
- Exact folder name match (no fuzzy/substring matching)
- Only covers the 6 canonical stage folders
- Direction: folder name -> stage value
- Cannot handle variant folder names (e.g., renamed folders, typos)

### 2.2 _infer_deal_stage() (String Matching Fallback)

**File:** `backend/app/extraction/sharepoint.py` (lines 662-698)

```python
def _infer_deal_stage(self, folder_path: str) -> str | None:
    path_lower = folder_path.lower()

    if "dead" in path_lower or "passed" in path_lower:
        return "dead"
    elif "initial uw" in path_lower or "initial review" in path_lower:
        return "initial_review"
    elif "active uw" in path_lower or "active review" in path_lower:
        return "active_review"
    elif "under contract" in path_lower:
        return "under_contract"
    elif "closed" in path_lower or "acquired" in path_lower:
        return "closed"
    elif "realized" in path_lower:
        return "realized"
    elif "archive" in path_lower:
        return "archive"
    elif "pipeline" in path_lower or "active" in path_lower:
        return "pipeline"
    elif "loi" in path_lower:
        return "loi"
    elif "due diligence" in path_lower or "dd" in path_lower:
        return "due_diligence"
    return None
```

**Used by:** `SharePointClient.find_uw_models()` during SharePoint API-based discovery (lines 359, 374).

**Characteristics:**
- Substring matching against the full folder path (case-insensitive)
- Covers 10 stage identifiers (6 canonical + 4 additional)
- Direction: folder path substring -> stage value
- Returns `None` for unrecognized paths
- Fragile: `"active"` in the `"pipeline"` branch (line 691) can match `"active review"` paths if the order of `elif` branches ever changes

---

## 3. Additional Inferred Stages (Non-Canonical)

`_infer_deal_stage()` maps 4 additional folder patterns that do **not** correspond to any `DealStage` enum member:

| Folder Pattern | Inferred Stage | Has DealStage Enum? | What Happens |
|---|---|---|---|
| `archive` | `"archive"` | No | `DealStage("archive")` raises `ValueError` -- stage change is skipped |
| `pipeline` or `active` | `"pipeline"` | No | Same -- skipped by `_sync_deal_stages()` |
| `loi` | `"loi"` | No | Same -- skipped |
| `due diligence` or `dd` | `"due_diligence"` | No | Same -- skipped |

When `_sync_deal_stages()` receives one of these non-canonical stage strings, the `try/except ValueError` block (file_monitor.py lines 428-435) catches the enum conversion failure and skips the update with a warning log.

This is **safe but silent** -- the deal's stage will not be updated, and the file monitor will re-detect the same "change" on the next polling cycle.

---

## 4. Frontend Folder Mappings

The frontend maintains its own stage-to-folder mappings for generating SharePoint URLs. These are the **reverse direction** (stage value -> folder name).

### 4.1 src/features/deals/utils/sharepoint.ts (lines 3-10)

```typescript
const STAGE_FOLDER_MAP: Record<string, string> = {
  dead: '0) Dead Deals',
  initial_review: '1) Initial UW and Review',
  active_review: '2) Active Review',           // <-- DIFFERS from backend
  under_contract: '3) Under Contract',          // <-- DIFFERS from backend
  closed: '4) Closed - Active Assets',          // <-- DIFFERS from backend
  realized: '5) Realized',                      // <-- DIFFERS from backend
};
```

### 4.2 src/components/quick-actions/QuickActionButton.tsx (lines 76-83)

```typescript
const UW_STAGE_FOLDER_MAP: Record<string, string> = {
  dead: '0) Dead Deals',
  initial_review: '1) Initial UW and Review',
  active_review: '2) Active Review',            // <-- DIFFERS
  under_contract: '3) Under Contract',           // <-- DIFFERS
  closed: '4) Closed - Active Assets',           // <-- DIFFERS
  realized: '5) Realized',                       // <-- DIFFERS
};
```

---

## 5. Mapping Discrepancies

### 5.1 Backend vs Frontend Folder Names

| Stage | Backend (STAGE_FOLDER_MAP) | Frontend | Match? |
|---|---|---|---|
| dead | `0) Dead Deals` | `0) Dead Deals` | Yes |
| initial_review | `1) Initial UW and Review` | `1) Initial UW and Review` | Yes |
| active_review | `2) Active UW and Review` | `2) Active Review` | **No** |
| under_contract | `3) Deals Under Contract` | `3) Under Contract` | **No** |
| closed | `4) Closed Deals` | `4) Closed - Active Assets` | **No** |
| realized | `5) Realized Deals` | `5) Realized` | **No** |

The frontend uses **shortened or alternate** folder names for 4 of the 6 stages. Since the frontend only uses these for constructing SharePoint URLs (not for ingestion), the actual folder names in SharePoint determine which is correct. If the actual SharePoint folders use the backend's naming convention, the frontend URLs will point to wrong locations.

### 5.2 Backend STAGE_FOLDER_MAP vs _infer_deal_stage()

| Pattern | STAGE_FOLDER_MAP | _infer_deal_stage() | Risk |
|---|---|---|---|
| `0) Dead Deals` | `"dead"` | `"dead"` (matches `"dead"` substring) | None |
| `1) Initial UW and Review` | `"initial_review"` | `"initial_review"` (matches `"initial uw"`) | None |
| `2) Active UW and Review` | `"active_review"` | `"active_review"` (matches `"active uw"`) | None |
| `3) Deals Under Contract` | `"under_contract"` | `"under_contract"` (matches `"under contract"`) | None |
| `4) Closed Deals` | `"closed"` | `"closed"` (matches `"closed"`) | None |
| `5) Realized Deals` | `"realized"` | `"realized"` (matches `"realized"`) | None |
| Variant: `Passed Deals` | Not handled | `"dead"` (matches `"passed"`) | STAGE_FOLDER_MAP would miss this |
| Variant: `Acquired Deals` | Not handled | `"closed"` (matches `"acquired"`) | STAGE_FOLDER_MAP would miss this |
| Variant: `Active Deals` | Not handled | `"pipeline"` (matches `"active"`) | Ambiguous -- could also be active_review |

### 5.3 Order-Dependent Ambiguity in _infer_deal_stage()

The `elif` chain in `_infer_deal_stage()` creates order-dependent behavior:

```
elif "pipeline" in path_lower or "active" in path_lower:
    return "pipeline"
```

The `"active"` check (line 691) would match any path containing `"active"`, including `"Active UW and Review"`. However, because the `"active uw"` / `"active review"` checks appear earlier in the chain (line 679), the canonical `active_review` stage is matched first. If someone rearranges the conditions, `"active_review"` folders could be misidentified as `"pipeline"`.

Similarly, `"dd"` (line 696) could match substrings in deal names that happen to contain "dd" (e.g., a deal path containing "Haddock" or "Paddington").

---

## 6. Edge Cases

### 6.1 Non-Standard Folder Names

If a SharePoint admin renames or creates non-standard folders:
- `STAGE_FOLDER_MAP`: Will not find the folder at all (local discovery skips it)
- `_infer_deal_stage()`: May match via substring, potentially incorrectly

### 6.2 Nested Folder Structures

Deal folder structure is: `Stage Folder / Deal Name / [UW Model Subfolder] / files`

`_infer_deal_stage()` receives the **full folder path** (e.g., `Deals/1) Initial UW and Review/The Clubhouse`). The substring matching operates on the entire path, so a deal named "Dead Creek Apartments" in `2) Active UW and Review` would match the `"dead"` substring before reaching the `"active uw"` check.

### 6.3 Files Without a Stage Folder

If a file is placed directly under the Deals root (not inside a numbered stage folder):
- `STAGE_FOLDER_MAP`: File not discovered (only iterates known stage folders)
- `_infer_deal_stage()`: Returns `None`
- `MonitoredFile.deal_stage`: Set to `None`
- No stage sync occurs (stage_changes list skips `None` values via the `if file.deal_stage` check at file_monitor.py line 358)

### 6.4 Multiple Files for Same Deal in Different Folders

If the same deal name has files in two different stage folders (e.g., old copy in Dead Deals, new copy in Active UW), the stage_changes list will contain entries for both. The last-write-wins behavior of `_sync_deal_stages()` means the final stage depends on the order of iteration.

---

## 7. Mapping Architecture Summary

```
                            SharePoint
                               |
              +----------------+----------------+
              |                                 |
      Local OneDrive Sync              SharePoint API (Graph)
              |                                 |
     STAGE_FOLDER_MAP                  _infer_deal_stage()
     (exact folder name)               (substring match)
              |                                 |
     discover_local_deal_files()       find_uw_models()
              |                                 |
              +---------> deal_stage <----------+
                               |
                    _sync_deal_stages()
                               |
                       Deal.stage (DB)
```
