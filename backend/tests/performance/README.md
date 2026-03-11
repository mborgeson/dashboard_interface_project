# Performance Testing Framework

Performance and load testing for the B&R Capital Dashboard API.

## Components

### 1. Locust Load Tests (`locustfile.py`)
HTTP load testing with realistic user behavior patterns.

```bash
# Start locust with web UI (default: http://localhost:8089)
locust -f backend/tests/performance/locustfile.py --host=http://localhost:8000

# Headless mode (CI-friendly)
locust -f backend/tests/performance/locustfile.py --host=http://localhost:8000 \
    --users 50 --spawn-rate 5 --run-time 60s --headless
```

**User profiles:**
- **DashboardUser** (80%): Property dashboard, portfolio summary, paginated lists
- **DealBrowserUser** (15%): Deal pipeline browsing, individual deal details
- **AdminUser** (5%): Health checks, audit log monitoring

### 2. pytest-benchmark Micro-Benchmarks (`test_benchmarks.py`)
Measures critical hot-path performance: schema validation, ETag hashing, token blacklist lookups.

```bash
cd backend && python -m pytest tests/performance/test_benchmarks.py -v

# With detailed benchmark stats
cd backend && python -m pytest tests/performance/test_benchmarks.py -v --benchmark-only

# Compare against saved baseline
cd backend && python -m pytest tests/performance/test_benchmarks.py --benchmark-compare
```

### 3. Response Time Assertion Tests (`test_response_times.py`)
Functional tests that also validate response time thresholds.

```bash
cd backend && python -m pytest tests/performance/test_response_times.py -v
```

**Thresholds:**
| Endpoint | Threshold |
|---|---|
| `GET /api/v1/health` | < 100ms |
| `GET /api/v1/properties/dashboard` | < 500ms |
| `GET /api/v1/deals` | < 500ms |
| `POST /api/v1/auth/login` | < 750ms (bcrypt-dominated) |

## Running All Performance Tests

```bash
cd backend && python -m pytest tests/performance/ -v -m "performance or benchmark"
```

## Excluding from CI

Performance tests are marked with `@pytest.mark.performance` and `@pytest.mark.benchmark`.
The default pytest configuration excludes them via `-m "not slow and not pg"`.
To also explicitly exclude them:

```bash
python -m pytest -m "not benchmark and not performance"
```

## Dependencies

```bash
pip install locust pytest-benchmark
```
