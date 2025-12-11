# Testing Sprint: Parallel Agent Tasks

## Overview
Run E2E tests and backend service tests in parallel using specialized agents.

---

## Agent 1: E2E Test Validator

**Role**: Run and validate existing E2E tests (read-only)

### Prerequisites
- Start frontend: `npm run dev` (port 5173)
- Start backend: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload` (port 8000)

### Instructions
1. Wait for both dev servers to be ready
2. Run: `npm run test:e2e`
3. Capture full output
4. Report any failures with:
   - Test name
   - File:line reference
   - Error message
5. **DO NOT modify any files** - only validate and report

### Success Criteria
- All 9 E2E spec files run
- Report summary of passed/failed tests

---

## Agent 2: Backend Service Tester

**Role**: Write tests for untested backend services

### Target Files (in order)
1. `backend/app/services/export_service.py` → `backend/tests/test_services/test_export_service.py`
2. `backend/app/services/pdf_service.py` → `backend/tests/test_services/test_pdf_service.py`
3. `backend/app/services/redis_service.py` → `backend/tests/test_services/test_redis_service.py`
4. `backend/app/services/websocket_service.py` → `backend/tests/test_services/test_websocket_service.py`

### Pattern Reference
Follow existing test patterns from:
- `backend/tests/test_api/test_analytics.py`
- `backend/tests/test_crud/test_crud.py`
- Use fixtures from `backend/tests/conftest.py`

### Instructions
1. Create `backend/tests/test_services/` directory
2. For each service:
   - Read the service file to understand its methods
   - Write comprehensive unit tests
   - Use mocking for external dependencies (Redis, file I/O)
3. Run tests after each file: `PYTHONPATH=. pytest tests/test_services/ -v`

### Success Criteria
- All new test files pass
- Coverage increase reported

---

## Synchronization
- Agent 1 and Agent 2 work in separate directories
- No file conflicts expected
- Merge results when both complete
