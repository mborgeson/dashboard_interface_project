# Discovery Document 02: SharePoint Extraction Layer

## Overview

The extraction layer is the data ingestion backbone of the dashboard. It connects to B&R Capital's SharePoint/OneDrive deal folders, discovers underwriting model files, classifies and fingerprints them, extracts cell-level financial data, and persists the results for dashboard consumption. The layer spans authentication, file discovery, change detection, extraction orchestration, and cell-mapping logic.

---

## 1. SharePoint Client

**File:** `backend/app/extraction/sharepoint.py` (~705 lines)

### Authentication

| Component | Detail |
|-----------|--------|
| Library | MSAL (`ConfidentialClientApplication`) |
| Flow | Client credentials (client_secret) |
| Scope | `https://graph.microsoft.com/.default` |
| Token caching | In-memory; refreshed 5 minutes before expiry |
| Error class | `SharePointAuthError` |

The client authenticates using Azure AD application credentials. Tokens are cached and proactively refreshed when they are within 5 minutes of expiry, avoiding mid-request 401 failures.

### HTTP Session Management

- Uses `aiohttp.ClientSession` for async HTTP calls to Microsoft Graph API.
- Supports both context-manager usage and per-request session creation.
- Site ID and drive ID are resolved once and cached for the lifetime of the client instance.

### Graph API Endpoints

| Purpose | Endpoint Pattern |
|---------|-----------------|
| Site lookup | `/sites/{hostname}:{path}` |
| Drive children | `/drives/{id}/root:/{path}:/children` |
| File download | Pre-authenticated `@microsoft.graph.downloadUrl` |

### Data Structures

| Dataclass | Purpose |
|-----------|---------|
| `SharePointFile` | Represents a discovered file with metadata (name, path, size, modified date, download URL) |
| `SkippedFile` | Tracks files excluded during discovery with reason |
| `DiscoveryResult` | Aggregates accepted files, skipped files, and discovery metadata |

### File Discovery

The `SharePointClient` performs recursive scanning through the deal folder hierarchy:

```
SharePoint Deals Folder/
  0) Dead Deals/
  1) Initial UW and Review/
  2) Active UW and Review/
  3) Deals Under Contract/
  4) Closed Deals/
  5) Realized Deals/
    <Deal Name>/
      UW Model Subfolder/
        *.xlsx, *.xlsm, *.xlsb
```

Discovery walks stage folders, then deal folders within each stage, then UW model subfolders. Each file is wrapped in a `SharePointFile` dataclass with its inferred deal stage.

### Deal Stage Inference

The `_infer_deal_stage()` method maps folder names to stage enum values:

| Folder Name | Stage Value |
|-------------|-------------|
| `0) Dead Deals` | `dead` |
| `1) Initial UW and Review` | `initial_review` |
| `2) Active UW and Review` | `active_review` |
| `3) Deals Under Contract` | `under_contract` |
| `4) Closed Deals` | `closed` |
| `5) Realized Deals` | `realized` |

Additional mappings exist for variant folder names: `archive`, `pipeline`, `loi`, `due_diligence`.

The canonical stage folder map is also defined in `backend/app/api/v1/endpoints/extraction/common.py` as `STAGE_FOLDER_MAP`.

### Error Handling

- `SharePointAuthError` raised for authentication failures.
- 401 responses trigger a single retry: the cached token is cleared, a fresh token is acquired, and the request is retried once.
- Legacy fallback: when `FileFilter` is not available, regex patterns (`UW_MODEL_PATTERNS`) are used to identify underwriting model files.

---

## 2. File Monitor

**File:** `backend/app/services/extraction/file_monitor.py`

### Architecture

| Component | Detail |
|-----------|--------|
| Class | `SharePointFileMonitor` |
| Detection method | Polling-based (compare current SharePoint state vs. stored database state) |
| State storage | `MonitoredFile` database model |
| Logging | structlog with component binding |

### Change Detection Categories

| Change Type | Condition |
|-------------|-----------|
| **Added** | File exists in SharePoint but not in the database |
| **Modified** | File exists in both, but modified date or file size differs |
| **Deleted** | File exists in the database but not in SharePoint |

### Data Structures

| Dataclass | Purpose |
|-----------|---------|
| `FileChange` | Represents a single detected change (type, file metadata, previous state) |
| `MonitorCheckResult` | Aggregates all changes from a single monitoring pass |

### Datetime Handling

The `_ensure_aware()` helper normalizes datetimes for SQLite/PostgreSQL compatibility. SQLite stores datetimes as naive strings, while PostgreSQL uses timezone-aware timestamps. This helper ensures consistent comparison regardless of the database backend.

### Auto-Extraction

When changes are detected and the `AUTO_EXTRACT_ON_CHANGE` setting is enabled, the monitor automatically triggers the extraction pipeline for affected files. This is configurable and can be disabled for manual extraction workflows.

---

## 3. Extraction Pipeline (5 Phases)

The pipeline processes files through five sequential phases:

```
Discovery → Filter → Fingerprint → Extract → Persist
```

### Phase 1: File Filter (`file_filter.py`)

Configurable file classification. Accepts or rejects files based on extension, name patterns, and size thresholds. Outputs a list of candidate files for fingerprinting.

### Phase 2: Fingerprint (`fingerprint.py`)

Identifies the UW model type (template family) for each accepted file. The fingerprint determines which cell mappings apply. Template families share a common layout, so files within the same family can use the same extraction configuration.

### Phase 3: Group Pipeline (`group_pipeline.py`)

Batch extraction orchestration for grouped files. Files sharing the same fingerprint are processed as a group, allowing reference mappings from one file to inform extraction of others in the same template family.

### Phase 4: Extractor (`extractor.py`)

Core cell value extraction using openpyxl. Opens each Excel file, navigates to the mapped sheet and cell addresses, reads values, and returns structured `ExtractedValue` records. Handles `.xlsx` and `.xlsm` natively; `.xlsb` files require special handling and may trigger `BadZipFile` errors for corrupt files (see Error Categories below).

### Phase 5: Reference Mapper (`reference_mapper.py`)

The 4-tier auto-mapping system (detailed in Section 4). Maps field names to cell addresses across template variants.

---

## 4. Four-Tier Auto-Mapping System

**File:** `backend/app/extraction/reference_mapper.py`

The reference mapper bridges the gap between the canonical cell mappings (defined for a reference template) and the actual cell locations in variant templates. It uses a tiered confidence system:

| Tier | Confidence | Strategy | Description |
|------|-----------|----------|-------------|
| 1 | 0.95 | Direct match | Same sheet name + same cell address. The field is exactly where expected. |
| 2 | 0.85 | Shifted match | Same sheet name + same label text, but at a different cell address. Rows or columns shifted. |
| 3 | 0.70 | Renamed sheet | Different sheet name + same label text. The sheet was renamed but the layout is preserved. |
| 4 | 0.40-0.50 | Semantic match | Same sheet + synonym match via `field_synonyms.json`. Different label text but equivalent meaning. |

### Data Structures

| Dataclass | Purpose |
|-----------|---------|
| `MappingMatch` | A single field-to-cell mapping with confidence score |
| `GroupReferenceMapping` | Complete mapping set for a template group |
| `PropertyMatch` | Associates a property name with its matched mapping |

### Key Method: `auto_map_group()`

Accepts a group name, production (canonical) mappings, a representative fingerprint from the target group, and optional synonym definitions. Returns a `GroupReferenceMapping` with per-field confidence scores.

### Property Name Reconciliation

Property names are matched across files using a four-level cascade:

1. **Exact match** -- property name matches verbatim
2. **Normalized match** -- case-insensitive, whitespace-trimmed comparison
3. **Fuzzy match** -- string similarity scoring for minor variations
4. **Unmatched** -- no match found; flagged for manual review

---

## 5. Cell Mapping

**File:** `backend/app/extraction/cell_mapping.py`

### Architecture

| Component | Detail |
|-----------|--------|
| Class | `CellMappingParser` |
| Source file | `Underwriting_Dashboard_Cell_References.xlsx` |
| Source sheet | `UW Model - Cell Reference Table` |
| Total mappings | ~1,179 |

### Source Columns

| Column | Content |
|--------|---------|
| B | Category (e.g., "Revenue", "Expenses", "Returns") |
| C | Description (human-readable field label) |
| D | Sheet Name (target worksheet in the UW model) |
| G | Cell Address (e.g., "C12", "H45") |

### Field Name Generation

Field names are auto-generated from the description column. When duplicate field names occur (same description appearing on different sheets or rows), unique suffixes are appended using the pattern `{field_name}_{sheet}_{row_index}`.

### Dataclass: `CellMapping`

| Field | Type | Description |
|-------|------|-------------|
| `category` | `str` | Grouping category from column B |
| `description` | `str` | Human-readable label from column C |
| `sheet_name` | `str` | Target Excel sheet from column D |
| `cell_address` | `str` | Cell reference from column G |
| `field_name` | `str` | Auto-generated unique identifier |

---

## 6. Schedulers

Schedulers are initialized at application startup in `main.py` using APScheduler.

| Scheduler | Purpose | Configuration |
|-----------|---------|---------------|
| Extraction scheduler | Periodic full extraction runs | Cron expression via `EXTRACTION_SCHEDULE_CRON` |
| File monitor scheduler | Polling for SharePoint changes | Interval via `FILE_MONITOR_INTERVAL_MINUTES` (default: 30 min) |
| Market data scheduler | Periodic market data ingestion | Internal schedule |
| Interest rate scheduler | Periodic interest rate updates | Internal schedule |

---

## 7. Error Categories

| Error Type | Source | Handling |
|------------|--------|----------|
| `SharePointAuthError` | `sharepoint.py` | Raised on authentication failure; triggers token refresh and retry |
| 401 HTTP response | `_make_request()` | Clears cached token, retries once with fresh token |
| `BadZipFile` | openpyxl opening corrupt `.xlsb`/`.xlsx` | Caught as `FileAccessError`; pipeline skips file and continues |
| Per-file errors | `ExtractionRun.per_file_status` | JSON column tracking success/failure per file in each run |
| `error_category` | `ExtractedValue` model | Column exists on the model but is currently underutilized |

---

## 8. Configuration

**File:** `backend/app/core/config.py`

### Azure / SharePoint Settings

| Setting | Purpose |
|---------|---------|
| `AZURE_CLIENT_ID` | Azure AD application (client) ID |
| `AZURE_CLIENT_SECRET` | Azure AD client secret |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `SHAREPOINT_SITE_URL` | SharePoint site URL for Graph API |
| `SHAREPOINT_DEALS_FOLDER` | Root folder path within the SharePoint document library |

### Local Development Fallback

| Setting | Purpose |
|---------|---------|
| `LOCAL_DEALS_ROOT` | Local OneDrive sync path (e.g., `C:/Users/MattBorgeson/B&R Capital/...`); used when SharePoint API is unavailable during local development |

### File Monitor Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `FILE_MONITOR_ENABLED` | -- | Enable/disable the file monitoring service |
| `FILE_MONITOR_INTERVAL_MINUTES` | 30 | Polling interval for change detection |
| `AUTO_EXTRACT_ON_CHANGE` | -- | Automatically trigger extraction when changes are detected |

### Extraction Scheduler Settings

| Setting | Purpose |
|---------|---------|
| `EXTRACTION_SCHEDULE_ENABLED` | Enable/disable scheduled extraction runs |
| `EXTRACTION_SCHEDULE_CRON` | Cron expression for extraction timing |
| `EXTRACTION_SCHEDULE_TIMEZONE` | Timezone for cron schedule interpretation |

---

## 9. Key File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/extraction/sharepoint.py` | ~705 | SharePoint Graph API client, file discovery, authentication |
| `backend/app/services/extraction/file_monitor.py` | -- | Polling-based change detection and auto-extraction trigger |
| `backend/app/extraction/file_filter.py` | -- | File classification (accept/reject) |
| `backend/app/extraction/fingerprint.py` | -- | UW model type identification |
| `backend/app/extraction/group_pipeline.py` | -- | Batch extraction orchestration |
| `backend/app/extraction/extractor.py` | -- | Core cell value extraction via openpyxl |
| `backend/app/extraction/reference_mapper.py` | -- | 4-tier auto-mapping system |
| `backend/app/extraction/cell_mapping.py` | -- | Cell reference parser from Excel reference table |
| `backend/app/api/v1/endpoints/extraction/common.py` | -- | `STAGE_FOLDER_MAP` and shared extraction utilities |
| `backend/app/core/config.py` | -- | All extraction-related configuration settings |

---

## 10. Data Flow Diagram

```
SharePoint (Graph API)
        |
        v
  SharePointClient
  (auth, discover, download)
        |
        v
  SharePointFileMonitor ──────> FileChange detection
  (polling, DB state diff)      (added / modified / deleted)
        |
        v
  FileFilter ──────────────────> Accept or reject
        |
        v
  Fingerprint ─────────────────> Template family ID
        |
        v
  GroupPipeline ───────────────> Batch orchestration
        |
        v
  Extractor ───────────────────> Cell value reads (openpyxl)
        |                        via ReferenceMapper (4-tier)
        v
  ExtractedValue ──────────────> Database (per-field, per-file)
        |
        v
  Dashboard API ───────────────> Frontend display
```
