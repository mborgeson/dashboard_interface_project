# CLAUDE.md — Dashboard Interface Project

## Stack
- **Backend:** FastAPI + SQLAlchemy async (Python 3.12)
- **Frontend:** React + TypeScript + Vite
- **Database:** PostgreSQL. Alembic for migrations (`backend/alembic/`).
- **Conda env:** `dashboard-backend`

## Directory Structure

### Backend
- `backend/app/api/` — FastAPI routes
- `backend/app/models/` — SQLAlchemy models (2.0 style: `Mapped[type]`, `mapped_column()`, async sessions)
- `backend/app/schemas/` — Pydantic request/response schemas
- `backend/app/crud/` — Database operations
- `backend/app/services/` — Business logic (subdirs: `batch/`, `construction_api/`, `data_extraction/`, `extraction/`, `ml/`, `monitoring/`, `workflow/`; plus 19 top-level service modules)
- `backend/app/extraction/` — Proforma parsing (see Extraction Stack below)
- `backend/app/core/` — Config, security, logging, permissions
- `backend/app/db/` — Database abstraction (base.py, session.py, query_logger.py)
- `backend/app/database/` — Data seeding and schema utilities
- `backend/app/middleware/` — HTTP middleware (error_handler, etag, rate_limiter, request_id)
- `backend/app/events/` — Event handlers
- `backend/app/tasks/` — Background tasks
- `backend/app/templates/` — Email templates

### Frontend
- `src/features/` — Feature modules
- `src/lib/api/` — API clients + Zod schemas
- `src/lib/calculations/` — Financial calculation utilities
- `src/lib/constants/` — App constants
- `src/lib/utils/` — Shared utility functions
- `src/components/` — Shared UI (shadcn/ui)
- `src/hooks/` — React hooks
- `src/stores/` — Feature stores (auth, notification, search via Zustand)
- `src/store/` — App-level Zustand store (`useAppStore.ts`)
- `src/app/` — App shell, router, routes
- `src/assets/` — Static assets
- `src/contexts/` — React Context providers (Loading, QuickActions, Toast)
- `src/services/` — Frontend services (error tracking)
- `src/types/` — Centralized TypeScript type definitions (api, deal, property, extraction, etc.)

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
- **API client:** `src/lib/api/client.ts` (fetch-based). Exported via `src/lib/api/index.ts` with `get`/`post`/`put`/`patch`/`del` convenience wrappers.
- React conventions: no setState in useEffect, no ref.current in render paths.
- `src/store/useAppStore.ts` (app-level Zustand store) is separate from `src/stores/` (feature stores).
- Known chunk warnings (deferred): exceljs 937KB, vendor-charts 455KB.

## Testing

### Backend (pytest)
- Tests in `backend/tests/`. SQLite in-memory for DB tests (need explicit `created_at`/`updated_at`, no `server_default`).
- Run: `cd backend && python -m pytest` (in `dashboard-backend` conda env)
- Parallel: `python -m pytest -n auto` (pytest-xdist, uses all available cores)
- Coverage: `python -m pytest --cov=app --cov-report=term-missing` (not in default addopts — pass explicitly)
- CI uses `-n auto` with coverage flags; see `backend-ci.yml` for the full invocation.

### Frontend (vitest)
- Tests colocated with features or in `src/test/`.
- Run: `npm run test:run`
- Coverage: `@vitest/coverage-v8`
- E2E: `npm run test:e2e` (Playwright, `e2e/` directory, `playwright.config.ts` at root)

### When to write tests
- Always for extraction logic and financial calculations (cap rates, NOI, IRR/MOIC).
- Always for API endpoint changes and Zod schema changes.
- Use judgment for UI glue code — test the logic, not the framework.

## CI/CD

- `.github/workflows/backend-ci.yml` — Ruff lint, mypy type check, pytest (Python 3.12)
- `.github/workflows/frontend-ci.yml` — ESLint, TypeScript check, Vite build
- `.github/workflows/e2e.yml` — Playwright end-to-end tests

## Infrastructure

- `docker-compose.yml` — Development compose
- `docker-compose.prod.yml` — Production compose
- `Dockerfile.frontend` — Frontend container
- `nginx/` — Nginx production config
- `scripts/` — Deployment and automation scripts
- `.env.example` / `.env.prod.example` — Environment variable templates

## Extraction Stack

`backend/app/extraction/` — openpyxl for .xlsx/.xlsm parsing, pandas for cell mapping/transforms.

**Pipeline:** `file_filter.py` (classify files) → `fingerprint.py` (identify UW model type) → `extractor.py` (pull cell values via `reference_mapper.py`) → `ExtractedValue` table. `group_pipeline.py` orchestrates batch runs. `validation.py` checks extracted values. `domain_validators.py` (domain-specific value validation), `schema_drift.py` (detects schema changes across runs), `reconciliation_checks.py` (cross-checks extracted values), `output_validation.py` (validates output quality), `field_synonyms.json` (maps alternate field names). Supporting: `sharepoint.py` (SharePoint download integration), `error_handler.py` (extraction error handling), `grouping.py` (file grouping utilities).

Fragile module — cell references are template-specific.

## Data Sources

- CoStar submarket data (15 clusters)
- Proforma Excel files from SharePoint/OneDrive (`/mnt/c/Users/MattBorgeson/B&R Capital/...`)
- Construction pipeline
- Sales comps

## Do Not Touch (without explicit instruction)

- **Alembic migration history** — never edit existing files in `backend/alembic/versions/`. Only create new migrations.
- **Auth middleware** — `backend/app/core/security.py`, `permissions.py`, `token_blacklist.py`. Changes affect all protected endpoints.
- **Linter configs** — root ESLint config. Changing rules cascades across entire codebase. (`backend/ruff.toml` target-version may be updated to match runtime; rule changes still require caution.)
- **Extraction cell mappings** — `backend/app/extraction/cell_mapping.py`, `reference_mapper.py`. These map to specific Excel cell addresses in UW model templates. Wrong values = wrong financial data.
- **HTTP middleware** — `backend/app/middleware/`. Changes affect all HTTP request processing.

## Key Versions

**Frontend:** React 19.2, TypeScript 5.9, Vite 7.2, Zod 4.1, Zustand 5.0, TanStack Query 5.90, React Router 6.30, Recharts 2.15, Playwright 1.57
**Backend:** FastAPI >=0.109, SQLAlchemy >=2.0.25, Pydantic >=2.5, Alembic >=1.13, Redis >=5.0, Loguru >=0.7, Pandas >=2.2
