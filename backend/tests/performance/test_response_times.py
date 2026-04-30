"""
Response time assertion tests for key API endpoints.

Validates that endpoints respond within acceptable thresholds using
the existing async test client (SQLite in-memory, no network overhead).

These are functional tests that also validate performance characteristics,
not load tests. They catch regressions where a code change accidentally
introduces slow queries or unnecessary computation.

Usage:
    cd backend && python -m pytest tests/performance/test_response_times.py -v
"""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

# ---------------------------------------------------------------------------
# Mark the entire module for selective inclusion/exclusion
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.performance


# ============================================================================
# Threshold constants (seconds)
# ============================================================================
# These are generous for the in-process test client (no network latency).
# Real-world thresholds against a live server would be tighter.

HEALTH_THRESHOLD_S = 0.100  # 100 ms
DASHBOARD_THRESHOLD_S = 0.500  # 500 ms
DEALS_THRESHOLD_S = 0.500  # 500 ms
# Login threshold is higher because bcrypt password hashing is intentionally
# slow (~200-400ms per verify) as a brute-force defense mechanism.
# First call also incurs bcrypt backend initialization overhead.
LOGIN_THRESHOLD_S = 0.750  # 750 ms (bcrypt-dominated)
PROPERTIES_LIST_THRESHOLD_S = 0.500  # 500 ms
ANALYTICS_THRESHOLD_S = 0.500  # 500 ms


# ============================================================================
# Helper
# ============================================================================


def _measure_request(coro):
    """Not used directly — timing is done inline for clarity."""
    pass


# ============================================================================
# Health endpoints (no auth required)
# ============================================================================


class TestHealthResponseTimes:
    """Response time assertions for health check endpoints."""

    async def test_legacy_health_under_threshold(self, client) -> None:
        """GET /api/v1/health should respond within 100ms."""
        start = time.perf_counter()
        response = await client.get("/api/v1/health")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < HEALTH_THRESHOLD_S, (
            f"GET /api/v1/health took {elapsed:.3f}s, "
            f"threshold is {HEALTH_THRESHOLD_S}s"
        )

    async def test_health_status_under_threshold(self, client) -> None:
        """GET /api/v1/health/status (detailed) should respond within 100ms."""
        start = time.perf_counter()
        response = await client.get("/api/v1/health/status")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < HEALTH_THRESHOLD_S, (
            f"GET /api/v1/health/status took {elapsed:.3f}s, "
            f"threshold is {HEALTH_THRESHOLD_S}s"
        )


# ============================================================================
# Auth endpoint
# ============================================================================


class TestAuthResponseTimes:
    """Response time assertions for authentication endpoints."""

    async def test_login_under_threshold(self, client, test_user) -> None:
        """POST /api/v1/auth/login should respond within 200ms."""
        start = time.perf_counter()
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "testpassword123",
            },
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < LOGIN_THRESHOLD_S, (
            f"POST /api/v1/auth/login took {elapsed:.3f}s, "
            f"threshold is {LOGIN_THRESHOLD_S}s"
        )

    async def test_login_invalid_credentials_under_threshold(self, client) -> None:
        """POST /api/v1/auth/login with bad credentials should still be fast."""
        start = time.perf_counter()
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 401
        assert elapsed < LOGIN_THRESHOLD_S, (
            f"POST /api/v1/auth/login (invalid) took {elapsed:.3f}s, "
            f"threshold is {LOGIN_THRESHOLD_S}s"
        )


# ============================================================================
# Property endpoints
# ============================================================================


class TestPropertyResponseTimes:
    """Response time assertions for property endpoints."""

    async def test_properties_dashboard_under_threshold(
        self, client, db_session, auth_headers
    ) -> None:
        """GET /api/v1/properties/dashboard should respond within 500ms."""
        start = time.perf_counter()
        response = await client.get(
            "/api/v1/properties/dashboard",
            headers=auth_headers,
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < DASHBOARD_THRESHOLD_S, (
            f"GET /api/v1/properties/dashboard took {elapsed:.3f}s, "
            f"threshold is {DASHBOARD_THRESHOLD_S}s"
        )

    async def test_properties_summary_under_threshold(
        self, client, db_session, auth_headers
    ) -> None:
        """GET /api/v1/properties/summary should respond within 500ms."""
        start = time.perf_counter()
        response = await client.get(
            "/api/v1/properties/summary",
            headers=auth_headers,
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < DASHBOARD_THRESHOLD_S, (
            f"GET /api/v1/properties/summary took {elapsed:.3f}s, "
            f"threshold is {DASHBOARD_THRESHOLD_S}s"
        )

    async def test_properties_list_under_threshold(
        self, client, db_session, auth_headers
    ) -> None:
        """GET /api/v1/properties/ should respond within 500ms."""
        start = time.perf_counter()
        response = await client.get(
            "/api/v1/properties/",
            headers=auth_headers,
            follow_redirects=True,
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < PROPERTIES_LIST_THRESHOLD_S, (
            f"GET /api/v1/properties/ took {elapsed:.3f}s, "
            f"threshold is {PROPERTIES_LIST_THRESHOLD_S}s"
        )


# ============================================================================
# Deal endpoints
# ============================================================================


class TestDealResponseTimes:
    """Response time assertions for deal endpoints."""

    async def test_deals_list_under_threshold(
        self, client, db_session, auth_headers
    ) -> None:
        """GET /api/v1/deals should respond within 500ms."""
        start = time.perf_counter()
        response = await client.get(
            "/api/v1/deals",
            headers=auth_headers,
            follow_redirects=True,
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < DEALS_THRESHOLD_S, (
            f"GET /api/v1/deals took {elapsed:.3f}s, threshold is {DEALS_THRESHOLD_S}s"
        )

    async def test_deals_list_large_page_under_threshold(
        self, client, db_session, auth_headers
    ) -> None:
        """GET /api/v1/deals?page_size=100 should respond within 500ms."""
        start = time.perf_counter()
        response = await client.get(
            "/api/v1/deals?page_size=100",
            headers=auth_headers,
            follow_redirects=True,
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < DEALS_THRESHOLD_S, (
            f"GET /api/v1/deals?page_size=100 took {elapsed:.3f}s, "
            f"threshold is {DEALS_THRESHOLD_S}s"
        )

    async def test_deal_detail_under_threshold(
        self, client, test_deal, auth_headers
    ) -> None:
        """GET /api/v1/deals/{id} should respond within 500ms."""
        start = time.perf_counter()
        response = await client.get(
            f"/api/v1/deals/{test_deal.id}",
            headers=auth_headers,
        )
        elapsed = time.perf_counter() - start

        assert response.status_code == 200
        assert elapsed < DEALS_THRESHOLD_S, (
            f"GET /api/v1/deals/{test_deal.id} took {elapsed:.3f}s, "
            f"threshold is {DEALS_THRESHOLD_S}s"
        )


# ============================================================================
# Multiple sequential requests (simulates real usage patterns)
# ============================================================================


class TestSequentialRequestTimes:
    """Test that sequential requests don't degrade (catches connection leaks)."""

    async def test_ten_sequential_health_checks(self, client) -> None:
        """10 sequential health checks should each be under threshold."""
        times: list[float] = []
        for _ in range(10):
            start = time.perf_counter()
            response = await client.get("/api/v1/health")
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            times.append(elapsed)

        avg = sum(times) / len(times)
        max_time = max(times)

        # Average should be well under threshold
        assert avg < HEALTH_THRESHOLD_S, (
            f"Average of 10 health checks: {avg:.3f}s, "
            f"threshold is {HEALTH_THRESHOLD_S}s"
        )
        # No single request should be an outlier (2x threshold)
        assert max_time < HEALTH_THRESHOLD_S * 2, (
            f"Worst health check: {max_time:.3f}s, "
            f"threshold is {HEALTH_THRESHOLD_S * 2}s"
        )

    async def test_five_sequential_dashboard_requests(
        self, client, db_session, auth_headers
    ) -> None:
        """5 sequential dashboard requests should not degrade."""
        times: list[float] = []
        for _ in range(5):
            start = time.perf_counter()
            response = await client.get(
                "/api/v1/properties/dashboard",
                headers=auth_headers,
            )
            elapsed = time.perf_counter() - start
            assert response.status_code == 200
            times.append(elapsed)

        avg = sum(times) / len(times)
        # Average should be under threshold
        assert avg < DASHBOARD_THRESHOLD_S, (
            f"Average of 5 dashboard requests: {avg:.3f}s, "
            f"threshold is {DASHBOARD_THRESHOLD_S}s"
        )
        # Last request should not be significantly slower than first
        # (would indicate connection pool exhaustion or memory leak)
        if times[0] > 0.001:  # avoid division by near-zero
            degradation = times[-1] / times[0]
            assert degradation < 3.0, (
                f"Last request was {degradation:.1f}x slower than first "
                f"({times[-1]:.3f}s vs {times[0]:.3f}s) — possible resource leak"
            )
