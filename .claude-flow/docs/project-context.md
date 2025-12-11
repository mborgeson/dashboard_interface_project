# Dashboard Interface Project Context

This document provides context for Claude-Flow agents working on this project.

## Project Overview

**Name**: Dashboard Interface Project
**Type**: Full-stack Real Estate Underwriting Dashboard
**Status**: Active Development (Phase 1 Complete)

## Technology Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.x | UI Framework |
| TypeScript | 5.9.x | Type Safety |
| TailwindCSS | 3.4.x | Styling |
| Radix UI | Latest | Accessible Components |
| TanStack Query | 5.x | Server State |
| TanStack Table | 8.x | Data Tables |
| Zustand | 5.x | Client State |
| React Hook Form | 7.x | Form Management |
| Zod | 4.x | Validation |
| Recharts | 2.x | Charts |
| Leaflet | 1.9.x | Maps |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | Latest | API Framework |
| Python | 3.12+ | Runtime |
| SQLAlchemy | 2.x | ORM |
| Pydantic | 2.x | Validation |
| Alembic | Latest | Migrations |

### Testing
| Tool | Purpose |
|------|---------|
| Vitest | Unit/Integration Tests |
| Playwright | E2E Browser Tests |
| Pytest | Backend Tests |
| Testing Library | React Component Tests |

## Directory Structure

```
dashboard_interface_project/
├── src/                    # Frontend source
│   ├── components/         # Shared UI components
│   ├── features/           # Feature modules
│   │   ├── deals/          # Deal management
│   │   ├── properties/     # Property views
│   │   └── reporting/      # Reports
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utilities
│   ├── services/           # API services
│   └── stores/             # Zustand stores
├── backend/                # Python backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── crud/           # Database operations
│   │   ├── models/         # SQLAlchemy models
│   │   └── schemas/        # Pydantic schemas
│   └── tests/              # Backend tests
├── e2e/                    # Playwright E2E tests
└── docs/                   # Documentation
```

## Key Patterns

### Frontend
- **Component Structure**: Feature-based organization
- **State Management**: Zustand for client, TanStack Query for server
- **Forms**: React Hook Form + Zod validation
- **Styling**: TailwindCSS utility classes + CVA for variants

### Backend
- **API Design**: RESTful with FastAPI
- **Database**: SQLAlchemy 2.0 async patterns
- **Validation**: Pydantic v2 models
- **Authentication**: JWT-based

## Agent Guidelines

### When Working on Frontend (`src/`)
- Follow existing component patterns
- Use Radix UI primitives for accessibility
- Apply TailwindCSS classes (no custom CSS)
- Ensure TypeScript strict mode compliance
- Write Vitest tests for new components

### When Working on Backend (`backend/`)
- Follow FastAPI best practices
- Use Pydantic for all request/response models
- Write Pytest tests with fixtures
- Document API endpoints with OpenAPI

### When Writing Tests
- **Unit**: Test isolated logic with mocks
- **Integration**: Test component interactions
- **E2E**: Test critical user flows only
