# ADR-001: FastAPI + SQLAlchemy async for backend

## Status
Accepted

## Context
The dashboard backend needs to serve a React SPA with REST endpoints for deal management, property analytics, extraction pipelines, and real-time WebSocket updates. Multiple background schedulers (extraction, file monitoring, market data, interest rates) run concurrently during the application lifecycle. The team needed a framework that supports async I/O natively, has strong typing/validation, and auto-generates OpenAPI docs for frontend integration.

## Decision
We chose FastAPI with SQLAlchemy 2.0 async sessions and Pydantic schemas. The database layer (`backend/app/db/session.py`) provides both async (`AsyncSession`) and sync (`Session`) factories -- async for API endpoints, sync for background tasks and CRUD operations. Alembic manages schema migrations. PostgreSQL is the production database, with SQLite for test isolation.

Key structural conventions:
- `backend/app/api/v1/` -- versioned route modules
- `backend/app/models/` -- SQLAlchemy 2.0 mapped models (`Mapped[type]`, `mapped_column()`)
- `backend/app/schemas/` -- Pydantic request/response DTOs
- `backend/app/crud/` -- generic `CRUDBase` with soft-delete awareness
- `backend/app/services/` -- business logic and background schedulers

## Consequences
- Async endpoints and schedulers coexist naturally within a single process via `asynccontextmanager` lifespan.
- Auto-generated OpenAPI docs (`/api/docs`) accelerate frontend development.
- Dual session factories add complexity but allow sync CRUD code (simpler to test) alongside async endpoints.
- SQLAlchemy 2.0 style requires the team to learn `Mapped`/`mapped_column` patterns, but provides better type-checker support.
