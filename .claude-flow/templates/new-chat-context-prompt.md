# B&R Capital Dashboard - New Chat Context Prompt

Use this prompt when starting a new Claude Code chat session to bring it fully up to speed with the project.

---

## Copy Everything Below This Line

---

# B&R Capital Dashboard - Project Context & Continuation

## Project Location
/home/mattb/projects/dashboard_interface_project

## Restore Context First
Run this command to restore the project checkpoint:
```
mcp__memory-keeper__context_restore_checkpoint --name "backend-testing-cicd-final"
```

## Technology Stack

### Frontend
- React 19.2.0, TypeScript 5.9.3, Vite 7.2.2
- TailwindCSS 3.4.x, Radix UI (shadcn/ui components)
- Zustand 5.x (client state), TanStack Query 5.x (server state)
- React Hook Form 7.x + Zod 4.x (forms/validation)
- Recharts 2.x (charts), Leaflet 1.9.x (maps)
- Fuse.js (fuzzy search)

### Backend
- FastAPI (Python 3.12+)
- SQLAlchemy 2.x async, Pydantic 2.x
- Alembic (migrations)
- JWT authentication

### Testing
- Vitest + Testing Library (frontend unit/integration)
- Playwright (E2E)
- Pytest + pytest-cov (backend)

## Current Implementation Status

### Frontend (Phase 1 Complete - All Tiers)
| Tier | Features |
|------|----------|
| Phase 1 | Dashboard, Investments, Analytics, Mapping pages |
| Tier 1 | PropertyDetailPage, TransactionsPage, UnderwritingModal |
| Tier 2 | DealsPage, DocumentsPage, MarketPage |
| Tier 3 | GlobalSearch, SavedFilters, Toast System, Skeletons |
| Tier 4 | Full integration across all pages |
| Tier 5 | Performance (code splitting, lazy loading) |
| Tier 6 | Testing (43 tests passing), accessibility, responsive |

### Backend (Testing Infrastructure Complete)
- **Tests**: 33 total (31 passed, 2 skipped expected)
- **Coverage**: 31%
- **Git Commit**: 7d36cad on main

#### CRUD Layer (`backend/app/crud/`)
- `base.py` - Generic CRUD base class
- `crud_user.py` - User CRUD with password hashing & authenticate()
- `crud_deal.py` - Deal CRUD operations

#### Test Suite (`backend/tests/`)
- `conftest.py` - SQLite in-memory with StaticPool pattern
- `test_models/` - User (6), Deal (8), Property (7) tests
- `test_api/` - Health (2), Auth (5), Deals (5) tests

#### CI/CD (`.github/workflows/`)
- `backend-ci.yml` - lint → test (PostgreSQL) → security → build
- `frontend-ci.yml` - lint → build → test

## Key Architectural Patterns

### Password Hashing (CRUDUser)
```python
def create(self, db, *, obj_in):
    obj_in_data = obj_in.dict()
    if 'password' in obj_in_data:
        obj_in_data['hashed_password'] = get_password_hash(obj_in_data.pop('password'))
    # ... create user
```

### Test Database Fixture
```python
SQLALCHEMY_DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
engine = create_async_engine(url, poolclass=StaticPool, connect_args={'check_same_thread': False})
app.dependency_overrides[get_db] = override_get_db
```

## Directory Structure
```
dashboard_interface_project/
├── src/                    # Frontend source
│   ├── components/         # Shared UI components
│   ├── features/           # Feature modules (deals, properties, reporting)
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utilities
│   ├── services/           # API services
│   └── stores/             # Zustand stores
├── backend/                # Python backend
│   ├── app/
│   │   ├── api/v1/endpoints/  # API routes
│   │   ├── crud/              # CRUD operations
│   │   ├── models/            # SQLAlchemy models
│   │   └── schemas/           # Pydantic schemas
│   └── tests/                 # Backend tests
├── e2e/                    # Playwright E2E tests
├── .github/workflows/      # CI/CD pipelines
├── .claude-flow/           # Agent documentation
├── .swarm/                 # Runtime state (gitignored)
├── claude-flow.config.json # Swarm configuration
└── .mcp.json               # Project MCP servers
```

## Remaining Tasks (Priority Order)

### High Priority
1. Add test coverage for remaining API endpoints (properties, analytics, users)
2. Set up PostgreSQL test database for integration tests
3. Add E2E tests for critical user flows (Playwright)
4. Implement proper auth flow testing

### Medium Priority
5. Increase backend test coverage (currently 31%)
6. Add API endpoint tests for underwriting models
7. Implement test data factories (factory_boy)
8. Review and optimize bundle size

### Lower Priority
9. Add performance/load testing
10. API documentation tests (OpenAPI validation)
11. Document remaining technical debt for Phase 2

## Claude-Flow Configuration
Project uses local swarm configuration:
- `claude-flow.config.json` - Agent settings, memory paths
- `.swarm/memory.db` - SQLite reasoning bank
- `.claude-flow/docs/project-context.md` - Agent context

## Commands
```bash
# Frontend
npm run dev          # Start dev server
npm run test         # Run Vitest
npm run test:e2e     # Run Playwright

# Backend
cd backend
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v --tb=short
```

## Your Task
[INSERT YOUR SPECIFIC TASK HERE]

Please read the key files and restore the checkpoint context before proceeding.

---

## End of Prompt

---

## Usage Instructions

1. Copy everything between "Copy Everything Below This Line" and "End of Prompt"
2. Paste into a new Claude Code chat
3. Replace `[INSERT YOUR SPECIFIC TASK HERE]` with your actual task
4. The new chat will have full project context

## Alternative: Quick Start Prompt

For simpler tasks, use this shorter version:

```
Project: /home/mattb/projects/dashboard_interface_project
Stack: React 19 + TypeScript + Vite | FastAPI + SQLAlchemy
Status: Phase 1 complete, backend testing infrastructure done (33 tests, 31% coverage)
Checkpoint: mcp__memory-keeper__context_restore_checkpoint --name "backend-testing-cicd-final"

Task: [YOUR TASK]
```
