Generated: 2026-03-10

# Infrastructure Configuration Audit
## B&R Capital Dashboard Interface Project

Complete audit of infrastructure, configuration, dependencies, and deployment settings across backend, frontend, and DevOps.

---

## 1. Environment Variables

### Development Environment (backend/.env.example)

**Database**
- `DATABASE_URL`: PostgreSQL or SQLite connection string (dev default: `sqlite:///./test.db`)
- `DATABASE_POOL_SIZE`: Connection pool size (default: 10)
- `DATABASE_MAX_OVERFLOW`: Max overflow connections (default: 20)
- `DATABASE_POOL_TIMEOUT`: Pool timeout in seconds (default: 30)

**Redis**
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379/0`)
- `REDIS_CACHE_TTL`: Cache time-to-live in seconds (default: 3600 = 1 hour)
- `REDIS_MAX_CONNECTIONS`: Max Redis connections (default: 50)
- `REDIS_SOCKET_CONNECT_TIMEOUT`: Socket timeout in seconds (default: 5)

**Security**
- `SECRET_KEY`: JWT signing key (required in production, auto-generated in dev)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiry (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiry (default: 7)
- `API_KEYS`: Comma-separated list of valid API keys for service-to-service calls
- `API_KEY_HEADER`: Header name for API key authentication (default: X-API-Key)

**CORS**
- `CORS_ORIGINS`: Comma-separated or JSON array of allowed origins (dev defaults: localhost:5173, localhost:3000, 127.0.0.1:5173, 127.0.0.1:3000; prod: dashboard.bandrcapital.com, app.bandrcapital.com, bandrcapital.com)

**Email (SMTP)**
- `SMTP_HOST`: SMTP server (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP port (default: 465)
- `SMTP_USER`: SMTP username (required, set via env var)
- `SMTP_PASSWORD`: SMTP password (never hardcoded, set via env var)
- `EMAIL_FROM_NAME`: Display name for emails (default: Dashboard Interface (B&R Capital))
- `EMAIL_FROM_ADDRESS`: From address (required, set via env var)
- `EMAIL_RATE_LIMIT`: Max emails per minute (default: 60)
- `EMAIL_MAX_RETRIES`: Retry attempts (default: 3)
- `EMAIL_RETRY_DELAY`: Retry delay in seconds (default: 300)
- `EMAIL_BATCH_SIZE`: Batch send size (default: 10)
- `EMAIL_DEV_MODE`: Log emails instead of sending (default: false)

**Azure AD / SharePoint**
- `AZURE_CLIENT_ID`: Microsoft Entra application ID
- `AZURE_CLIENT_SECRET`: Microsoft Entra application secret
- `AZURE_TENANT_ID`: Azure tenant ID
- `SHAREPOINT_SITE_URL`: SharePoint site URL
- `SHAREPOINT_SITE`: SharePoint site name (default: BRCapital-Internal)
- `SHAREPOINT_LIBRARY`: Document library name (default: Real Estate)
- `SHAREPOINT_DEALS_FOLDER`: Folder within library (default: Deals)
- `LOCAL_DEALS_ROOT`: Local OneDrive path to deals folder

**File Processing**
- `FILE_PATTERN`: Regex pattern for UW model filenames (default: `.*UW\s*Model.*vCurrent.*`)
- `EXCLUDE_PATTERNS`: Comma-separated substrings to exclude (default: ~$,.tmp,backup,old,archive,Speedboat,vOld)
- `FILE_EXTENSIONS`: Valid file extensions (default: .xlsb,.xlsm,.xlsx)
- `CUTOFF_DATE`: Skip files older than date YYYY-MM-DD (default: 2024-07-15)
- `MAX_FILE_SIZE_MB`: Max file size in MB (default: 100)

**External APIs**
- `FRED_API_KEY`: Federal Reserve FRED API key (optional)
- `CENSUS_API_KEY`: US Census API key (optional)
- `BLS_API_KEY`: Bureau of Labor Statistics API key (optional, increases rate limit)
- `MESA_SODA_APP_TOKEN`: Socrata API token for Mesa AZ data (optional)

**Construction Pipeline**
- `CONSTRUCTION_API_ENABLED`: Enable construction pipeline (default: false)
- `CONSTRUCTION_DATA_DIR`: Data directory (default: data/construction)
- `CONSTRUCTION_CENSUS_CRON`: Census sync schedule (default: 0 4 15 * * = monthly 15th 4 AM)
- `CONSTRUCTION_FRED_CRON`: FRED sync schedule (default: 0 4 15 * *)
- `CONSTRUCTION_BLS_CRON`: BLS sync schedule (default: 0 5 15 * *)
- `CONSTRUCTION_MUNICIPAL_CRON`: Municipal data sync (default: 0 6 16 * *)
- `MESA_SODA_DATASET_ID`: Mesa dataset ID (default: h2sj-gt3d)
- `TEMPE_BLDS_LAYER_URL`: Tempe ArcGIS feature layer URL (optional)
- `GILBERT_ARCGIS_LAYER_URL`: Gilbert ArcGIS layer URL (optional)

**Market Data**
- `MARKET_ANALYSIS_DB_URL`: Separate PostgreSQL database for CoStar + FRED data (optional, e.g., postgresql://user:pass@localhost:5432/market_analysis)
- `COSTAR_DATA_DIR`: CoStar data directory (default: data/costar)
- `MARKET_DATA_EXTRACTION_ENABLED`: Enable market data extraction (default: false)
- `MARKET_FRED_SCHEDULE_CRON`: FRED schedule (default: 0 10 * * * = daily 10 AM)
- `MARKET_COSTAR_SCHEDULE_CRON`: CoStar schedule (default: 0 10 15 * * = monthly 15th 10 AM)
- `MARKET_CENSUS_SCHEDULE_CRON`: Census schedule (default: 0 10 15 1 * = annual Jan 15th 10 AM)

**Interest Rates**
- `INTEREST_RATE_SCHEDULE_ENABLED`: Enable interest rate scheduler (default: false)
- `INTEREST_RATE_SCHEDULE_CRON_AM`: Morning fetch schedule (default: 0 8 * * * = daily 8 AM)
- `INTEREST_RATE_SCHEDULE_CRON_PM`: Afternoon fetch schedule (default: 0 15 * * * = daily 3 PM)
- `INTEREST_RATE_CACHE_TTL`: In-memory cache TTL in seconds (default: 300)
- `INTEREST_RATE_DB_POOL_SIZE`: Market data DB pool size (default: 2)
- `INTEREST_RATE_DB_MAX_OVERFLOW`: Market data DB max overflow (default: 1)

**Extraction & Grouping**
- `EXTRACTION_BATCH_SIZE`: Files per batch (default: 10)
- `EXTRACTION_MAX_WORKERS`: Thread pool workers (default: 4)
- `EXTRACTION_SCHEDULE_ENABLED`: Enable extraction scheduler (default: true)
- `EXTRACTION_SCHEDULE_CRON`: Extraction schedule (default: 0 17 * * * = daily 5 PM)
- `EXTRACTION_SCHEDULE_TIMEZONE`: Scheduler timezone (default: America/Phoenix)
- `GROUP_EXTRACTION_DATA_DIR`: Extraction groups data directory (default: data/extraction_groups)
- `GROUP_FINGERPRINT_WORKERS`: Fingerprint thread workers (default: 4)
- `GROUP_IDENTITY_THRESHOLD`: Identity matching threshold (default: 0.95)
- `GROUP_VARIANT_THRESHOLD`: Variant matching threshold (default: 0.80)
- `GROUP_EMPTY_TEMPLATE_THRESHOLD`: Empty template threshold (default: 20)
- `GROUP_MAX_BATCH_SIZE`: Max batch size for grouping (default: 500)

**File Monitoring**
- `FILE_MONITOR_ENABLED`: Enable file monitoring (default: false)
- `FILE_MONITOR_INTERVAL_MINUTES`: Monitor check interval (default: 30)
- `AUTO_EXTRACT_ON_CHANGE`: Auto-extract when files change (default: true)
- `MONITOR_CHECK_CRON`: Monitor check schedule (default: */30 * * * * = every 30 minutes)

**Rate Limiting**
- `RATE_LIMIT_ENABLED`: Enable rate limiting (default: true)
- `RATE_LIMIT_BACKEND`: Limiting backend (default: auto = memory/redis auto-select)
- `RATE_LIMIT_REQUESTS`: Default requests per window (default: 100)
- `RATE_LIMIT_WINDOW`: Window in seconds (default: 60)
- `RATE_LIMIT_AUTH_REQUESTS`: Auth endpoint limit (default: 5)
- `RATE_LIMIT_AUTH_WINDOW`: Auth window in seconds (default: 60)
- `RATE_LIMIT_REFRESH_REQUESTS`: Token refresh limit (default: 10)
- `RATE_LIMIT_CLEANUP_WINDOW`: Max cleanup window in seconds (default: 3600)

**Performance & Caching**
- `CACHE_SHORT_TTL`: Short cache TTL in seconds (default: 300 = 5 minutes for frequently-changing data)
- `CACHE_LONG_TTL`: Long cache TTL in seconds (default: 7200 = 2 hours for rarely-changing aggregates)
- `HTTP_TIMEOUT`: Default HTTP request timeout in seconds (default: 10.0)
- `HTTP_TIMEOUT_LONG`: Longer timeout for slow APIs (default: 15.0)

**Slow Query Detection**
- `SLOW_QUERY_THRESHOLD_MS`: Log threshold in milliseconds (default: 500)
- `SLOW_QUERY_LOG_PARAMS`: Include sanitized params in logs (default: false)

**Upload Limits**
- `UPLOAD_MAX_EXCEL_MB`: Max Excel size in MB (default: 50)
- `UPLOAD_MAX_PDF_MB`: Max PDF size in MB (default: 25)
- `UPLOAD_MAX_CSV_MB`: Max CSV size in MB (default: 10)
- `UPLOAD_MAX_DOCX_MB`: Max DOCX size in MB (default: 25)

**Miscellaneous**
- `APP_NAME`: Application name (default: B&R Capital Dashboard API)
- `APP_VERSION`: Version (default: 2.0.0)
- `DEBUG`: Debug mode (default: false)
- `ENVIRONMENT`: Environment (default: development)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `WORKERS`: Uvicorn workers (default: 4)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FORMAT`: Log format string (default: %(asctime)s - %(name)s - %(levelname)s - %(message)s)
- `LOG_RETENTION_DAYS`: App log retention (default: 30)
- `LOG_ERROR_RETENTION_DAYS`: Error log retention (default: 90)
- `WS_HEARTBEAT_INTERVAL`: WebSocket heartbeat in seconds (default: 30)
- `WS_MAX_CONNECTIONS`: Max WebSocket connections (default: 1000)
- `ML_MODEL_PATH`: ML models directory (default: ./models)
- `ML_BATCH_SIZE`: ML batch size (default: 32)
- `ML_PREDICTION_CACHE_TTL`: ML prediction cache TTL in seconds (default: 300)
- `GEOCODING_RATE_LIMIT_DELAY`: Nominatim rate limit delay in seconds (default: 1.1)
- `CONSTRUCTION_MIN_UNITS`: Minimum units for pipeline import (default: 50)
- `PDF_MAX_PROPERTIES`: Max properties in PDF summary (default: 10)
- `PDF_MAX_DEALS`: Max deals in PDF pipeline table (default: 10)
- `WORKFLOW_HTTP_TIMEOUT`: Workflow HTTP step timeout in seconds (default: 30)

### Production Environment (.env.example)

The production environment uses the same variables as above plus adds:
- Docker Compose service names: `db`, `redis`, `backend`, `frontend`, `celery-worker`, `celery-beat`, `nginx`
- `POSTGRES_USER`: PostgreSQL username (required)
- `POSTGRES_PASSWORD`: PostgreSQL password (required)
- `REDIS_PASSWORD`: Redis password (required)

### Production Build (.env.prod.example)

Frontend build variables:
- `VITE_API_URL`: API base URL for frontend
- `VITE_ENABLE_AI_INSIGHTS`: Feature flag for AI insights
- `VITE_ENABLE_REAL_TIME_UPDATES`: Feature flag for real-time updates
- `VITE_ENABLE_EXPORT_FEATURES`: Feature flag for export features

---

## 2. Docker Configuration

### Backend Services (docker-compose.yml)

**backend** (development)
- Image: Dockerfile (development target)
- Port: 8000
- Environment: Inherits from .env
- Volumes: Logs mounted to logs/
- Health check: curl http://localhost:8000/health every 30s
- Dependencies: PostgreSQL, Redis (service_healthy condition)

**PostgreSQL (db)**
- Image: postgres:15-alpine
- Port: 5432
- Environment: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- Volumes: postgres-data (persistent)
- Health check: pg_isready every 10s

**Redis**
- Image: redis:7-alpine
- Port: 6379
- Volumes: redis-data (persistent)
- Command: redis-server --appendonly yes (persistence)
- Health check: redis-cli ping every 10s

**Celery Worker**
- Image: Dockerfile (development target)
- Command: celery -A app.tasks worker --loglevel=info --concurrency=2
- Environment: Inherits from .env
- Dependencies: PostgreSQL, Redis, backend
- Health check: PS check for celery process

**Celery Beat**
- Image: Dockerfile (development target)
- Command: celery -A app.tasks beat --loglevel=info --scheduler=redbeat.RedBeatScheduler
- Environment: Inherits from .env
- Dependencies: PostgreSQL, Redis, backend
- Health check: PS check for celery beat process

**Optional Dev Tools (profile: dev-tools)**

pgAdmin:
- Image: dpage/pgadmin4:latest
- Port: 5050
- Volumes: pgadmin-data (persistent)
- Environment: PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD

redis-commander:
- Image: rediscommander/redis-commander:latest
- Port: 8081
- Environment: REDIS_HOSTS (connects to redis service)

### Production Services (docker-compose.prod.yml)

**backend** (production)
- Image: Dockerfile (production target)
- Replicas: 2
- Resources: 2 CPU limit, 512M reserved
- Logging: json-file, max-size 10m, max-file 5
- Port: 8000 (internal only, exposed via nginx)
- Environment: WORKERS=4, LOG_LEVEL=WARNING
- Dependencies: PostgreSQL (service_healthy), Redis (service_healthy)

**PostgreSQL** (postgres:15-alpine)
- Port: 5432
- Tuning:
  - max_connections: 200
  - shared_buffers: 1GB
  - effective_cache_size: 3GB
  - maintenance_work_mem: 256MB
  - checkpoint_completion_target: 0.9
  - wal_buffers: 16MB
  - default_statistics_target: 100
  - random_page_cost: 1.1
  - effective_io_concurrency: 200
  - work_mem: 5MB
  - min_wal_size: 1GB
  - max_wal_size: 4GB
- Volumes: postgres-data (persistent)
- Logging: json-file, max-size 10m, max-file 3

**Redis** (redis:7-alpine)
- Port: 6379
- Configuration:
  - maxmemory: 384MB
  - maxmemory-policy: allkeys-lru
  - appendonly: yes
  - appendfsync: everysec
  - save: 900 1, 300 10, 60 10000
- Volumes: redis-data (persistent)
- Logging: json-file, max-size 10m, max-file 3

**Celery Worker**
- Concurrency: 4
- Loglevel: WARNING
- Resources: 1 CPU limit, 512M reserved

**Nginx** (nginx:1.25-alpine)
- Port: 80
- Volumes: nginx.conf (configuration), dist/ (static frontend)
- Logging: json-file, max-size 10m, max-file 5
- Health check: wget http://localhost/health every 30s

### Networking

Development: br-capital-network (bridge)
Production: dashboard-network-prod (bridge)

### Volumes (Development)

- postgres-data: PostgreSQL persistence
- redis-data: Redis persistence
- backend-logs: Backend application logs
- pgadmin-data: pgAdmin configuration (dev-tools only)

### Volumes (Production)

- postgres-data: PostgreSQL persistence
- redis-data: Redis persistence

---

## 3. Vite Configuration (vite.config.ts)

**Plugins**
- @vitejs/plugin-react: React JSX support

**Resolve**
- Path alias: @ → ./src

**Dev Server**
- Port: 5173
- Proxies (in order of specificity):
  1. `/api/fred/*` → https://api.stlouisfed.org (FRED API CORS proxy)
  2. `/api/*` → http://localhost:8000 (backend API)
  3. `/ws/*` → ws://localhost:8000 (WebSocket)

**Build Optimization**

Manual chunk splitting (vendor bundles):
- vendor-react: react, react-dom, react-router-dom
- vendor-radix: @radix-ui/* (11 Radix UI components)
- vendor-icons: lucide-react
- vendor-charts: recharts (lazy-loaded on chart route visit)
- vendor-maps: leaflet, react-leaflet, leaflet.markercluster
- vendor-dnd: @dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities
- vendor-data: @tanstack/react-query, @tanstack/react-table, zustand, fuse.js
- vendor-misc: cmdk, date-fns
- vendor-forms: dayjs, react-hook-form, @hookform/resolvers, zod

Dynamic imports (lazy-loaded on demand):
- jspdf (~386KB) - loaded only when user clicks export button
- exceljs (~937KB) - loaded only when user clicks export button
- html2canvas (~201KB) - loaded on demand

Chunk size warning limit: 500KB (only lazy-loaded chunks exceed)

**Dependency Optimization**
- Include: react, react-dom, react-router-dom, zustand, lucide-react

---

## 4. TypeScript Configuration

### tsconfig.app.json (Frontend Application)

**Compiler Options**
- target: ES2022
- useDefineForClassFields: true
- lib: ES2020, DOM, DOM.Iterable
- module: ESNext
- skipLibCheck: true
- strict: true (strict null checks, strict function types, strict property initialization, no implicit any)
- esModuleInterop: true
- skipDefaultLibCheck: true
- moduleResolution: Bundler
- allowSyntheticDefaultImports: true
- resolveJsonModule: true
- isolatedModules: true
- noEmit: true
- jsx: react-jsx

**Path Aliases**
- @/* → ./src/*

**Linting**
- noUnusedLocals: false (disabled)
- noUnusedParameters: false (disabled)
- noFallthroughCasesInSwitch: true

### tsconfig.node.json (Build Tools)

**Compiler Options**
- target: ES2023
- useDefineForClassFields: true
- lib: ES2023, DOM
- module: ESNext
- skipLibCheck: true
- strict: true
- esModuleInterop: true
- skipDefaultLibCheck: true
- moduleResolution: Bundler
- allowSyntheticDefaultImports: true
- resolveJsonModule: true

**Linting**
- noUnusedLocals: true
- noUnusedParameters: true
- noFallthroughCasesInSwitch: true

---

## 5. Lint Configuration

### ESLint (eslint.config.js)

**Format**: Flat config (newer ESLint v9+ format)

**Base Configuration**
- @eslint/js: js.configs.recommended
- typescript-eslint: tseslint.configs.recommended
- Globals: browser environment
- ECMAScript version: 2020

**Plugins**
- react-hooks: eslint-plugin-react-hooks flat.recommended
- react-refresh: eslint-plugin-react-refresh (Vite HMR compatibility)

**Ignored Paths**
- dist/
- coverage/**
- e2e/**

### Ruff (backend/ruff.toml)

**Project Settings**
- Target Python: 3.11
- Line length: 88
- Fix mode: enabled

**Enabled Rules**
- E: pycodestyle errors
- F: Pyflakes
- W: pycodestyle warnings
- I: isort (import sorting)
- UP: pyupgrade (Python version compatibility)
- B: flake8-bugbear (bug detection)
- C4: flake8-comprehensions (comprehension optimization)
- SIM: flake8-simplify (code simplification)

**Ignored Rules**
- E501: Line too long (handled by formatter)
- B008: Function call in default argument (needed for FastAPI Depends)

**Per-File Ignores**
- tests/**/*.py: F841 (unused variable)
- backend/alembic/versions/*.py: F401 (unused import)
- backend/app/db/base.py: F401 (unused import for SQLAlchemy registry)

### MyPy (backend Configuration)

Implicit settings (no separate mypy.ini file, uses default strict checks):
- Type checking: enabled for entire backend/
- Strict mode equivalent: All implicit checks enabled

---

## 6. Python Dependencies (backend/requirements.txt)

**FastAPI & Uvicorn Ecosystem** (79 packages total)
- fastapi>=0.109.0
- uvicorn[standard]>=0.27.0
- python-multipart>=0.0.6

**Database & ORM**
- sqlalchemy>=2.0.25 (async ORM, SQLAlchemy 2.0 style)
- psycopg2-binary>=2.9.9 (PostgreSQL sync driver)
- asyncpg>=0.29.0 (PostgreSQL async driver)
- alembic>=1.13.1 (database migrations)
- sqlalchemy-utils>=0.41.1 (SQLAlchemy utilities)

**Redis & Caching**
- redis>=5.0.1
- aioredis>=2.0.1 (async Redis)

**WebSocket & Real-time**
- websockets>=12.0
- python-socketio>=5.11.0
- aiofiles>=23.2.1

**Email**
- aiosmtplib>=3.0.1 (async SMTP)
- email-validator>=2.1.0
- jinja2>=3.1.3 (email templates)

**Data Processing**
- pydantic>=2.5.3 (data validation)
- pydantic-settings>=2.1.0 (settings management)
- python-dateutil>=2.8.2
- pytz>=2024.1

**Excel/Data File Processing**
- pyxlsb>=1.0.10 (XLSB reader)
- openpyxl>=3.1.0 (XLSX/XLSM parser)
- pandas>=2.2.0 (data manipulation)

**Authentication & Security**
- python-jose[cryptography]>=3.3.0 (JWT)
- passlib[bcrypt]>=1.7.4 (password hashing)
- bcrypt>=4.1.0,<5.0.0 (bcrypt hashing)

**Azure & SharePoint**
- msal>=1.24.0 (Microsoft authentication)

**Logging & Observability**
- structlog>=23.1.0 (structured logging)
- loguru>=0.7.2 (enhanced logging)
- prometheus-client>=0.19.0 (Prometheus metrics)
- psutil>=5.9.8 (system monitoring)

**HTTP Clients**
- aiohttp>=3.8.0 (async HTTP)
- httpx>=0.26.0 (async HTTP with timeouts)
- requests>=2.31.0 (sync HTTP fallback)

**Task Scheduling**
- apscheduler>=3.10.0 (scheduled tasks)
- redbeat>=2.0.0 (Redis-backed scheduler)

**ML/Data Science**
- numpy>=1.26.3
- scikit-learn>=1.4.0
- xgboost>=2.0.3
- lightgbm>=4.3.0
- torch>=2.2.0
- tensorflow>=2.16.1

**Testing**
- pytest>=7.4.4
- pytest-asyncio>=0.23.3 (async test support)
- pytest-cov>=4.1.0 (coverage)
- pytest-timeout>=2.2.0 (test timeouts)
- aiosqlite>=0.19.0 (SQLite async for tests)

**Development Tools**
- ruff>=0.4.0 (linting)
- black>=24.1.1 (formatting)
- isort>=5.13.2 (import sorting)
- mypy>=1.8.0 (type checking)
- flake8>=7.0.0 (linting)
- ipython>=8.21.0 (interactive shell)

---

## 7. Frontend Dependencies (package.json)

**Core React Stack**
- react@^19.2.0
- react-dom@^19.2.0
- react-router-dom@^6.30.1

**State Management**
- zustand@^5.0.8
- @tanstack/react-query@^5.90.8 (server state)
- @tanstack/react-table@^8.21.3 (table management)
- @tanstack/react-virtual@^3.13.21 (virtual scrolling)

**UI Component Libraries**
- @radix-ui/react-accordion@^1.2.12
- @radix-ui/react-alert-dialog@^1.1.15
- @radix-ui/react-checkbox@^1.3.3
- @radix-ui/react-dialog@^1.1.15
- @radix-ui/react-dropdown-menu@^2.1.16
- @radix-ui/react-label@^2.1.8
- @radix-ui/react-select@^2.2.6
- @radix-ui/react-separator@^1.1.8
- @radix-ui/react-slot@^1.2.4
- @radix-ui/react-tabs@^1.1.13
- @radix-ui/react-tooltip@^1.2.8
- class-variance-authority@^0.7.1
- clsx@^2.1.1

**Icons**
- lucide-react@^0.553.0

**Charts & Visualization**
- recharts@^2.15.4

**Maps**
- leaflet@1.9
- react-leaflet@^4.2.1
- leaflet.markercluster@1.5

**Forms & Validation**
- react-hook-form@^7.66.0
- @hookform/resolvers@^5.2.2
- zod@^4.1.12

**Date & Time**
- dayjs@^1.11.19
- date-fns@^4.1.0

**Drag & Drop**
- @dnd-kit/core@^6.3.1
- @dnd-kit/sortable@^10.0.0
- @dnd-kit/utilities@^3.2.2

**Search & Filtering**
- fuse.js@^7.1.0

**Command Palette**
- cmdk@^1.1.1

**Export & PDF Generation**
- exceljs@^4.4.0 (dynamically imported, lazy-loaded)
- jspdf@^4.2.0 (dynamically imported, lazy-loaded)

**CSS & Styling**
- tailwind-merge@^3.4.0

**Miscellaneous**
- @anthropic-ai/sdk@^0.78.0 (Claude API)
- tmux@^1.0.0
- ttyd@^1.0.3

### Frontend Dev Dependencies

**Build Tools**
- @vitejs/plugin-react@^5.1.0
- vite@^7.2.2
- typescript@~5.9.3

**Testing**
- vitest@^4.0.15
- @testing-library/react@^16.3.0
- @testing-library/dom@^10.4.1
- @testing-library/jest-dom@^6.9.1
- @testing-library/user-event@^14.6.1
- @playwright/test@^1.57.0
- @vitest/coverage-v8@^4.0.15
- jsdom@^27.2.0

**Type Definitions**
- @types/node@^24.10.0
- @types/react@^19.2.2
- @types/react-dom@^19.2.2
- @types/leaflet@^1.9.21
- @types/leaflet.markercluster@^1.5.6

**Linting & Code Quality**
- eslint@^9.39.1
- @eslint/js@^9.39.1
- typescript-eslint@^8.46.3
- eslint-plugin-react-hooks@^7.0.1
- eslint-plugin-react-refresh@^0.4.24
- globals@^16.5.0

**CSS Processing**
- tailwindcss@^3.4.18
- postcss@^8.5.6
- autoprefixer@^10.4.22

**Utilities**
- concurrently@^9.2.1
- @tanstack/react-query-devtools@^5.91.2

---

## 8. NPM Scripts (package.json)

**Development**
- `dev`: vite (start dev server on port 5173)
- `dev:all`: concurrently runs uvicorn (backend:8000) + vite (frontend:5173) + browser auto-open

**Build**
- `build`: tsc -b && vite build (type-check and build)
- `preview`: vite preview (preview production build)

**Code Quality**
- `lint`: eslint . (lint TypeScript/React code)

**Testing**
- `test`: vitest (watch mode)
- `test:run`: vitest run (single run with coverage)
- `test:coverage`: vitest run --coverage (coverage report)

**E2E Testing**
- `test:e2e`: playwright test (run E2E tests)
- `test:e2e:ui`: playwright test --ui (interactive E2E UI)

---

## 9. Backend Makefile Targets (backend/Makefile)

**Setup & Environment**
- `install`: Create venv and install requirements.txt
- `shell`: Launch IPython interactive shell

**Development**
- `dev`: Run uvicorn with reload on port 8000

**Testing**
- `test`: Run pytest (excludes slow tests)
- `test-cov`: Run pytest with coverage report (HTML in htmlcov/)
- `test-fast`: Run only non-slow tests (-m "not slow")

**Code Quality**
- `lint`: Run flake8, mypy checks
- `format`: Run black, isort formatters
- `check`: Run lint + format checks

**Database**
- `migrate`: Run latest Alembic migrations
- `migrate-new`: Create new migration (prompts for message)
- `seed`: Populate database with seed data
- `db-reset`: Drop and recreate database, run migrations

**Docker**
- `docker-build`: Build Docker images
- `docker-up`: Start docker-compose services
- `docker-down`: Stop services
- `docker-logs`: Tail logs
- `docker-shell`: Exec into running container
- `docker-prod`: Run docker-compose.prod.yml (production)

**Cleanup**
- `clean`: Remove __pycache__, .pyc, .pytest_cache, htmlcov/
- `clean-all`: clean + remove venv

---

## 10. Database Migration Configuration (backend/alembic.ini)

**Script Directories**
- Script location: alembic directory
- Migration file template: `YYYYMMDD_HHMMSS_{rev}_{slug}.py`

**Logging**
- Root logger: WARNING level
- sqlalchemy logger: WARNING level (suppress verbose SQL logs)
- alembic logger: INFO level

**SQLAlchemy Connection**
- Uses connection from environment SQLALCHEMY_DATABASE_URL

---

## 11. Test Configuration (backend/pytest.ini)

**Execution**
- Asyncio mode: auto (auto event loop scope for async tests)
- Test paths: tests/ directory
- File patterns: test_*.py (files), Test* (classes), test_* (functions)
- Minimum pytest version: 7.0

**Reporting**
- Verbosity: -v (verbose output)
- Traceback: --tb=short (short traceback format)
- Coverage: --cov=app (measure app code coverage), --cov-report=term-missing + HTML
- Coverage failure: --cov-fail-under=30 (fail if < 30% coverage)
- Timeout: --timeout=60 (60-second test timeout), --timeout-method=thread

**Test Selection**
- Default: -m "not slow" (exclude slow tests)

**Markers**
- asyncio: Mark async tests
- slow: Mark slow tests (deselect with -m "not slow")
- integration: Mark integration tests
- unit: Mark unit tests

**Warnings**
- Ignore DeprecationWarning, PendingDeprecationWarning

---

## 12. CSS & Styling Configuration

### Tailwind CSS (tailwind.config.js)

**Dark Mode**: class-based (requires class on parent element)

**Content Paths**: ./index.html, ./src/**/*.{js,ts,jsx,tsx}

**Color Palette**
- Primary: Dark blue (#2A3F54), with 50-900 shades
- Secondary: CSS variable-based (hsl)
- Accent: Red (#E74C3C), with multiple shades
- Neutral: Gray scale (50-900)
- Shadcn colors: background, foreground, card, popover, muted, destructive, border, input, ring (all CSS variables)

**Typography**
- Font: Inter (system-ui, sans-serif)
- Custom sizes:
  - hero-stat: 2.5rem, 700 weight, -0.02em letter spacing
  - page-title: 1.875rem, 600 weight, 2.25rem line-height
  - section-title: 1.5rem, 600 weight, 2rem line-height
  - card-title: 1.125rem, 600 weight, 1.75rem line-height

**Effects**
- Border radius: lg, md (calc(var(--radius) - 2px)), sm (calc(var(--radius) - 4px))
- Shadows:
  - card: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)
  - card-hover: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)
- Animations: fade-in (0.3s), slide-in (0.3s), accordion-down/up (0.2s)

### PostCSS (postcss.config.js)

**Plugins**
- tailwindcss: Tailwind CSS processing
- autoprefixer: Cross-browser vendor prefixes (e.g., -webkit, -moz)

---

## 13. Reverse Proxy Configuration (nginx.conf)

**Server Settings**
- Listen: port 80
- Root: /usr/share/nginx/html (static frontend files)

**Compression**
- gzip: on
- Compression level: 6 (balanced)
- Compressed types: text/*, application/json, application/javascript, fonts

**Security Headers**
- X-Frame-Options: SAMEORIGIN (prevent clickjacking)
- X-Content-Type-Options: nosniff (prevent MIME-sniffing)
- X-XSS-Protection: 1; mode=block (XSS filter)
- Referrer-Policy: no-referrer-when-downgrade
- Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=() (restrict browser features)

**API Proxy** (/api/*)
- Target: http://backend:8000/api/
- Timeouts: 60s connect, 60s send, 60s read
- Buffering: disabled
- Headers: X-Forwarded-For, X-Forwarded-Proto, X-Forwarded-Host

**WebSocket Proxy** (/ws/*)
- Target: http://backend:8000/ws/
- Timeout: 7 days (604800s)
- Buffering: disabled
- WebSocket upgrade headers

**Health Endpoint** (/health)
- Returns 200 OK (for Docker health checks)

**Static Assets** (1-year cache, immutable)
- JavaScript (.js): Cache-Control: public, max-age=31536000, immutable
- CSS (.css): Cache-Control: public, max-age=31536000, immutable
- Images (.jpg, .jpeg, .png, .gif, .svg, .webp): Cache-Control: public, max-age=31536000, immutable
- Fonts (.woff, .woff2, .ttf, .eot): Cache-Control: public, max-age=31536000, immutable

**SPA Routing** (/)
- try_files $uri /index.html (client-side routing fallback)

**index.html** (no-cache)
- Cache-Control: no-cache, no-store, must-revalidate
- Pragma: no-cache
- Expires: 0
- ETag handling

---

## 14. Backend Application Configuration (backend/app/core/config.py)

**Settings Management**: Pydantic BaseSettings with environment variable parsing

**Configuration Parsing**
- CORS_ORIGINS: Supports comma-separated (CORS_ORIGINS="url1,url2") and JSON array (CORS_ORIGINS='["url1","url2"]')
- API_KEYS: Comma-separated list of service-to-service API keys
- Environment file: .env (loaded automatically via SettingsConfigDict)
- Case-insensitive: False (env vars case-sensitive)

**Validation Rules**
- Production environment:
  - SECRET_KEY required and ≥32 characters
  - DATABASE_URL must use PostgreSQL (SQLite not allowed)
- Development/testing:
  - SECRET_KEY auto-generated if not provided (secrets.token_urlsafe(64))

**New Configuration Parameters (50+)**

Rate Limiting:
- RATE_LIMIT_ENABLED (bool)
- RATE_LIMIT_BACKEND (auto/memory/redis)
- RATE_LIMIT_REQUESTS (100)
- RATE_LIMIT_WINDOW (60)
- RATE_LIMIT_AUTH_REQUESTS (5)
- RATE_LIMIT_AUTH_WINDOW (60)
- RATE_LIMIT_REFRESH_REQUESTS (10)
- RATE_LIMIT_CLEANUP_WINDOW (3600)

Request ID Tracking:
- Correlation IDs in middleware (via security.py)

API Key Authentication:
- API_KEYS (list of valid keys)
- API_KEY_HEADER (X-API-Key)

Structlog Logging:
- LOG_LEVEL, LOG_FORMAT, LOG_RETENTION_DAYS, LOG_ERROR_RETENTION_DAYS

Redis Caching:
- REDIS_URL, REDIS_CACHE_TTL, REDIS_MAX_CONNECTIONS
- REDIS_SOCKET_CONNECT_TIMEOUT

WebSocket Support:
- WS_HEARTBEAT_INTERVAL (30s)
- WS_MAX_CONNECTIONS (1000)

Connection Pool Monitoring:
- DATABASE_POOL_SIZE (10)
- DATABASE_MAX_OVERFLOW (20)
- DATABASE_POOL_TIMEOUT (30)
- REDIS_MAX_CONNECTIONS (50)

Slow Query Logging:
- SLOW_QUERY_THRESHOLD_MS (500)
- SLOW_QUERY_LOG_PARAMS (false)

ETags:
- Automatic ETag generation in response middleware (via security.py)

Extraction Validation:
- EXTRACTION_BATCH_SIZE (10)
- EXTRACTION_MAX_WORKERS (4)
- GROUP_EXTRACTION_DATA_DIR (data/extraction_groups)
- GROUP_FINGERPRINT_WORKERS (4)
- GROUP_IDENTITY_THRESHOLD (0.95)
- GROUP_VARIANT_THRESHOLD (0.80)
- GROUP_EMPTY_TEMPLATE_THRESHOLD (20)
- GROUP_MAX_BATCH_SIZE (500)
- EXTRACTION_SCHEDULE_ENABLED (true)
- EXTRACTION_SCHEDULE_CRON (0 17 * * *)
- EXTRACTION_SCHEDULE_TIMEZONE (America/Phoenix)

Cache Settings:
- CACHE_SHORT_TTL (300s)
- CACHE_LONG_TTL (7200s)

Performance:
- HTTP_TIMEOUT (10.0s)
- HTTP_TIMEOUT_LONG (15.0s)

Email Configuration:
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
- EMAIL_FROM_NAME, EMAIL_FROM_ADDRESS
- EMAIL_RATE_LIMIT, EMAIL_MAX_RETRIES, EMAIL_RETRY_DELAY, EMAIL_BATCH_SIZE, EMAIL_DEV_MODE

SharePoint Integration:
- AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
- SHAREPOINT_SITE_URL, SHAREPOINT_SITE, SHAREPOINT_LIBRARY, SHAREPOINT_DEALS_FOLDER
- LOCAL_DEALS_ROOT

File Processing:
- FILE_PATTERN, EXCLUDE_PATTERNS, FILE_EXTENSIONS, CUTOFF_DATE, MAX_FILE_SIZE_MB

External APIs:
- FRED_API_KEY, CENSUS_API_KEY, BLS_API_KEY, MESA_SODA_APP_TOKEN

Market Data:
- MARKET_ANALYSIS_DB_URL, COSTAR_DATA_DIR, MARKET_DATA_EXTRACTION_ENABLED

Interest Rates:
- INTEREST_RATE_SCHEDULE_ENABLED, INTEREST_RATE_SCHEDULE_CRON_AM, INTEREST_RATE_SCHEDULE_CRON_PM
- INTEREST_RATE_CACHE_TTL, INTEREST_RATE_DB_POOL_SIZE, INTEREST_RATE_DB_MAX_OVERFLOW

PDF Reports:
- PDF_MAX_PROPERTIES (10), PDF_MAX_DEALS (10)

---

## 15. Docker Build Configuration

### Backend (backend/Dockerfile)

**Stage 1 - Builder** (python:3.11-slim)
- Installs build tools (gcc, g++, python3-dev)
- Creates Python virtual environment
- Installs requirements.txt

**Stage 2 - Production** (python:3.11-slim)
- Installs runtime dependencies only (libpq5 for PostgreSQL, curl for health checks)
- Copies venv from builder
- Creates non-root user: appuser (UID 1000)
- Health check: curl http://localhost:PORT/health every 30s, timeout 10s, retries 3
- CMD: uvicorn app.main:app --host $HOST --port $PORT --workers $WORKERS --log-level $LOG_LEVEL

**Stage 3 - Development** (extends production)
- Adds development packages (git, vim, build-essential)
- Adds dev dependencies (pytest, black, flake8, isort, mypy, ipython)
- Enables interactive development with entrypoint override

### Frontend (Dockerfile.frontend)

**Stage 1 - Builder** (node:20-alpine)
- Install dependencies: npm ci --include=dev
- Build args: VITE_API_URL, VITE_ENABLE_AI_INSIGHTS, VITE_ENABLE_REAL_TIME_UPDATES, VITE_ENABLE_EXPORT_FEATURES
- Build command: npm run build
- Output: dist/ directory

**Stage 2 - Production** (nginx:1.25-alpine)
- Copies nginx.conf
- Copies dist/ from builder
- Runs as non-root nginx user
- Health check: wget http://localhost/health every 30s, timeout 10s, retries 3
- Expose: port 80 (or FRONTEND_PORT env var)

---

## Summary

### Architecture Highlights

**Full-Stack Development**
- Backend: FastAPI async + PostgreSQL + Redis + Celery task queue
- Frontend: React 19 + TypeScript + Vite (7.2) + Tailwind CSS + shadcn/ui
- DevOps: Docker multi-stage builds, docker-compose orchestration, nginx reverse proxy
- Testing: pytest (backend), vitest (frontend), Playwright (E2E)

**Performance Optimizations**
- Vite chunk splitting: 11 vendor bundles + lazy-loaded exporters (exceljs, jspdf)
- Redis caching: short-TTL (5m) and long-TTL (2h) strategies
- Connection pooling: PostgreSQL (10-30), Redis (50)
- Slow query detection: logged at 500ms threshold
- Compression: gzip level 6 on nginx, static assets with 1-year cache

**Security & Authentication**
- JWT tokens (HS256, 30-minute expiry, 7-day refresh)
- API key authentication for service-to-service calls
- CORS origin validation (dev/prod specific)
- Rate limiting (100 req/60s default, 5 req/60s for auth)
- Secure headers: SAMEORIGIN, nosniff, XSS protection, Permissions-Policy

**Data Processing**
- Excel extraction: pyxlsb (XLSB), openpyxl (XLSX/XLSM)
- Azure AD + SharePoint integration
- FRED, Census, CoStar, BLS external API integrations
- Construction pipeline + market data extraction
- Extraction grouping: fingerprinting + identity/variant thresholds

**Production Deployment**
- PostgreSQL (15-alpine): tuned for 200 connections, 3GB effective cache
- Redis (7-alpine): 384MB max memory, LRU eviction, RDB + AOF persistence
- Celery: task queue with 4 workers + beat scheduler
- Nginx: reverse proxy with SPA routing, WebSocket support, security headers
- Resource constraints: 2 CPU/512M memory per service
- Health checks: all services with 30s interval, 3 retries

