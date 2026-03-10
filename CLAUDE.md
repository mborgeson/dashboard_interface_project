# CLAUDE.md — Dashboard Interface Project

## Stack
- **Backend:** FastAPI + SQLAlchemy async (Python 3.11)
- **Frontend:** React + TypeScript + Vite
- **Database:** PostgreSQL. Alembic for migrations (`backend/alembic/`).
- **Conda env:** `dashboard-backend`

## Directory Structure

### Backend
- `backend/app/api/` — FastAPI routes
- `backend/app/models/` — SQLAlchemy models (2.0 style: `Mapped[type]`, `mapped_column()`, async sessions)
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/crud/` — Database operations
- `backend/app/services/` — Business logic
- `backend/app/extraction/` — Proforma parsing (see Extraction Stack below)
- `backend/app/core/` — Config, security, logging, permissions

### Frontend
- `src/features/` — Feature modules
- `src/lib/api/` — API clients + Zod schemas
- `src/components/` — Shared UI (shadcn/ui)
- `src/hooks/` — React hooks
- `src/stores/` — State management

## Dev Environment

- **Dev command:** `npm run dev:all` (concurrently runs uvicorn + vite)
- **Backend:** `http://localhost:8000` (uvicorn, docs at `/docs`)
- **Frontend:** `http://localhost:5173` (vite)
- **Auth:** JWT via authStore. Backend guards in `app/core/permissions.py`: `require_analyst`, `require_manager`. Login: `POST /api/v1/auth/login`. No dev bypass — authenticate to get token.

## Code Conventions

### Python (Backend)
- SQLAlchemy 2.0 style. Async sessions.
- Pydantic for API schemas. Dataclasses for internal DTOs when needed.
- Loguru for logging (already used throughout).
- `StrEnum` for enums. SQLAlchemy enum columns need `values_callable` for lowercase storage.
- `known-first-party = ["app"]` in ruff isort config.
- Ruff: line-length 88, E/F/W/I/UP/B/C4/SIM rules.

### TypeScript/React (Frontend)
- Zod schemas validate and transform API responses: snake_case backend → camelCase frontend (`src/lib/api/schemas/`).
- Zod pattern: `.nullable().optional()` with `?? undefined` (NOT `?? 0`).
- **Two API clients:** `src/lib/api.ts` (axios, legacy — don't extend) and `src/lib/api/client.ts` (fetch, use for new work).
- ESLint react-compiler rules: no setState in useEffect, no ref.current in render.
- Known chunk warnings (deferred): exceljs 937KB, vendor-charts 455KB.

## Testing

### Backend (pytest)
- Tests in `backend/tests/`. SQLite in-memory for DB tests (need explicit `created_at`/`updated_at`, no `server_default`).
- Run: `cd backend && python -m pytest` (in `dashboard-backend` conda env)

### Frontend (vitest)
- Tests colocated with features or in `src/test/`.
- Run: `npm run test:run`
- E2E: `npm run test:e2e` (Playwright)

### When to write tests
- Always for extraction logic and financial calculations (cap rates, NOI, IRR/MOIC).
- Always for API endpoint changes and Zod schema changes.
- Use judgment for UI glue code — test the logic, not the framework.

## Extraction Stack

`backend/app/extraction/` — openpyxl for .xlsx/.xlsm parsing, pandas for cell mapping/transforms.

**Pipeline:** `file_filter.py` (classify files) → `fingerprint.py` (identify UW model type) → `extractor.py` (pull cell values via `reference_mapper.py`) → `ExtractedValue` table. `group_pipeline.py` orchestrates batch runs. `validation.py` checks extracted values.

Fragile module — cell references are template-specific.

## Data Sources

- CoStar submarket data (15 clusters)
- Proforma Excel files from SharePoint/OneDrive (`/mnt/c/Users/MattBorgeson/B&R Capital/...`)
- Construction pipeline
- Sales comps

## Do Not Touch (without explicit instruction)

- **Alembic migration history** — never edit existing files in `backend/alembic/versions/`. Only create new migrations.
- **Auth middleware** — `backend/app/core/security.py`, `permissions.py`, `token_blacklist.py`. Changes affect all protected endpoints.
- **Linter configs** — `backend/ruff.toml`, root ESLint config. Changing rules cascades across entire codebase.
- **Extraction cell mappings** — `backend/app/extraction/cell_mapping.py`, `reference_mapper.py`. These map to specific Excel cell addresses in UW model templates. Wrong values = wrong financial data.
