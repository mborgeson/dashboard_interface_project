# Architecture Review — Discovery Summary

**Date:** 2026-03-25
**Branch:** `main` at `5bfc8d4`
**Baseline:** ~3,130 backend + ~1,274 frontend = **4,400+ tests**
**Prior Reviews:** Architecture Review v2 (69 findings), Dashboard Review (73 findings), Tech Debt (62/76 resolved)

---

## Architecture Diagram — Current State

```mermaid
graph TB
    subgraph "Data Sources"
        SP[SharePoint Online<br/>Graph API + MSAL]
        LOCAL[Local OneDrive<br/>WSL2 C:/...]
        COSTAR[CoStar Data<br/>Market Analytics]
        FRED[FRED API<br/>Interest Rates]
    end

    subgraph "Extraction Layer"
        FILTER[FileFilter<br/>classify files]
        FP[Fingerprint<br/>identify template]
        MAPPER[ReferenceMapper<br/>4-tier auto-map]
        EXTRACTOR[Extractor<br/>openpyxl cell read]
        VALID[Validation<br/>type/range checks]
        MONITOR[FileMonitor<br/>polling 30-min]
        SCHED[APScheduler<br/>cron + interval]
    end

    subgraph "Backend (FastAPI)"
        API[API Router<br/>20 endpoints]
        AUTH[JWT Auth<br/>+ token blacklist]
        MW[Middleware Chain<br/>8 layers]
        CACHE[CacheService<br/>Redis + memory fallback]
        WORKER[Report Worker<br/>background generation]
        WS[WebSocket<br/>real-time updates]
    end

    subgraph "Database (PostgreSQL)"
        PROPS[properties]
        DEALS[deals<br/>6-stage pipeline]
        EV[extracted_values<br/>EAV pattern]
        ER[extraction_runs]
        MF[monitored_files]
        MARKET[market_data<br/>253K records]
        UW[underwriting models<br/>11 tables]
    end

    subgraph "Frontend (React + Vite)"
        DASH[Dashboard<br/>portfolio summary]
        KANBAN[Deals Kanban<br/>6-stage board]
        ANALYTICS[Analytics<br/>charts + KPIs]
        EXTRACT_UI[Extraction UI<br/>pipeline stepper]
        MAP[Property Map<br/>aerial views]
        MARKET_UI[Market Analysis<br/>15 CoStar clusters]
        CONSTRUCT[Construction<br/>pipeline tracker]
    end

    SP --> MONITOR
    SP --> FILTER
    LOCAL --> FILTER
    COSTAR --> MARKET
    FRED --> API

    MONITOR --> FILTER
    SCHED --> MONITOR
    FILTER --> FP --> MAPPER --> EXTRACTOR --> VALID --> EV
    EXTRACTOR --> ER

    API --> AUTH --> MW
    API --> PROPS
    API --> DEALS
    API --> EV
    API --> MARKET
    API --> UW
    CACHE --> API
    WORKER --> API
    WS --> API

    DASH --> API
    KANBAN --> API
    ANALYTICS --> API
    EXTRACT_UI --> API
    MAP --> API
    MARKET_UI --> API
    CONSTRUCT --> API
```

## Data Flow — SharePoint → Dashboard

```mermaid
sequenceDiagram
    participant SP as SharePoint
    participant MON as FileMonitor
    participant FIL as FileFilter
    participant FP as Fingerprint
    participant MAP as ReferenceMapper
    participant EXT as Extractor
    participant DB as PostgreSQL
    participant API as FastAPI
    participant UI as React Frontend

    MON->>SP: Poll every 30 min (Graph API)
    SP-->>MON: File listing + metadata
    MON->>DB: Compare against stored state
    Note over MON: Detect added/modified/deleted

    MON->>FIL: Classify changed files
    FIL->>FP: Identify UW model template
    FP->>MAP: 4-tier auto-map cells
    MAP->>EXT: Extract cell values (openpyxl)
    EXT->>DB: Upsert to extracted_values (EAV)

    Note over MON: Also detect folder moves
    MON->>DB: Update deal.stage from folder

    UI->>API: Fetch dashboard data
    API->>DB: Query properties + extracted_values
    API-->>UI: JSON response (Zod validated)
```

## Critical Findings & Risk Map

### P0 — Critical (Production Blockers)

| # | Finding | Impact | Source |
|---|---------|--------|--------|
| 1 | **F-001: Users endpoints use in-memory demo data** | Auth returns demo users in production | v2 review |
| 2 | **F-004: WebSocket token doesn't check blacklist** | Revoked tokens can still connect to WS | v2 review |
| 3 | **F-005: Frontend ignores refresh tokens** | Users must re-login when access token expires | v2 review |
| 4 | **F-007: Transaction DELETE only requires viewer role** | Any viewer can delete financial records | v2 review |
| 5 | **28 ungrouped files need mapping** | ~25 deals without extracted data | Extraction audit |
| 6 | **error_category column never populated** | No error categorization for debugging extraction failures | Schema audit |

### P1 — High (Should Fix Before Production)

| # | Finding | Impact | Source |
|---|---------|--------|--------|
| 7 | Mixed logging: loguru vs structlog | Inconsistent log format, no unified correlation | Code audit |
| 8 | No schema drift detection | Template changes silently break extraction | ETL audit |
| 9 | Redis code exists but not enabled by default | In-memory cache lost on restart, no pub/sub | Infra audit |
| 10 | Tier 3/4 mappings (confidence < 0.85) need manual review | Wrong cell → wrong financial data | ETL audit |
| 11 | No audit trail for deal stage changes | Only loguru logs, not persisted to DB | WS3 scope |
| 12 | `_infer_deal_stage()` uses string matching (fragile) | Folder rename → wrong stage assignment | Extraction audit |
| 13 | Two API clients in frontend | Maintenance burden, inconsistent patterns | Frontend audit |

### P2 — Medium (Technical Debt)

| # | Finding | Impact | Source |
|---|---------|--------|--------|
| 14 | Duplicate field name handling depends on row index | Reference file reorder breaks field names | ETL audit |
| 15 | No delta query support (full poll every 30 min) | Unnecessary API calls, latency | WS2 scope |
| 16 | deploy.yml workflow disabled (.disabled file remains) | CI/CD not operational | Infra audit |
| 17 | Some CHECK constraints only on new migrations | Older data may violate constraints | Schema audit |

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend test functions | 3,130 |
| Frontend test files | 72 |
| Total tests | ~4,400+ |
| SQLAlchemy models | 30+ (across 17 files) |
| Alembic migrations | 20 |
| API routers | 20 |
| Middleware layers | 8 |
| Cell mappings | ~1,179 |
| Extracted values (last run) | 12,881 (initial) + 2,970 (groups) |
| Extraction groups completed | 9/9 deferred groups |
| Ungrouped files remaining | 28 |
| Market data records | 253K |

## Workstream Dependencies

```mermaid
graph LR
    D[Phase 1: Discovery<br/>✅ Complete] --> WS4[WS4: Data Integrity<br/>mapping manifest, validation]
    D --> WS1[WS1: General Improvements<br/>code health, Redis, logging]
    D --> WS2[WS2: Extraction Automation<br/>delta queries, webhooks]
    D --> WS3[WS3: Deal Stage Sync<br/>audit trail, bulk moves]

    WS4 --> WS1
    WS1 --> WS2
    WS2 --> WS3

    style D fill:#2d6a4f,color:#fff
    style WS4 fill:#264653,color:#fff
    style WS1 fill:#264653,color:#fff
    style WS2 fill:#264653,color:#fff
    style WS3 fill:#264653,color:#fff
```

**Execution order (confirmed):** WS4 → WS1 → WS2 → WS3

## Architecture Strengths

1. **EAV pattern for extracted values** — avoids 1,179-column table, makes new fields trivial
2. **4-tier auto-mapping** — handles template variants with confidence scoring
3. **Comprehensive middleware chain** — security headers, rate limiting, ETag, error handling, CORS, request ID
4. **Async throughout** — SQLAlchemy 2.0 async, aiohttp for SharePoint, FastAPI async endpoints
5. **Strong test coverage** — 4,400+ tests across backend and frontend
6. **CacheService graceful degradation** — Redis preferred, in-memory fallback transparent to callers
7. **Optimistic locking on Deal** — version column prevents concurrent update conflicts
8. **CHECK constraints on financial fields** — database-level data integrity for prices, rates, percentages
