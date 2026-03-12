"""
Locust load test configuration for B&R Capital Dashboard API.

Simulates realistic user behavior patterns against the FastAPI backend:
  - DashboardUser (80%): Property dashboard browsing and portfolio summary
  - DealBrowserUser (15%): Deal pipeline browsing and detail views
  - AdminUser (5%): Health checks and audit log monitoring

Usage:
    locust -f backend/tests/performance/locustfile.py --host=http://localhost:8000
    locust -f backend/tests/performance/locustfile.py --host=http://localhost:8000 \
        --users 50 --spawn-rate 5 --run-time 60s --headless
"""

from __future__ import annotations

import random

from locust import HttpUser, between, events, task


class AuthenticatedUser(HttpUser):
    """Base class providing JWT authentication flow.

    Subclasses inherit automatic login on start, with the JWT token
    attached to all subsequent requests via the Authorization header.
    """

    abstract = True
    # Default credentials — override via environment or locust web UI
    login_email: str = "matt@bandrcapital.com"
    login_password: str = "Wildcats777!!"
    token: str | None = None

    def on_start(self) -> None:
        """Authenticate and store JWT for subsequent requests."""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": self.login_email,
                "password": self.login_password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/api/v1/auth/login",
        )
        if response.status_code == 200:
            body = response.json()
            self.token = body.get("access_token")
        else:
            # Log failure but don't crash — tasks will see 401s which is useful data
            self.token = None

    @property
    def auth_headers(self) -> dict[str, str]:
        """Return Authorization header dict, or empty dict if not authenticated."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}


class DashboardUser(AuthenticatedUser):
    """Simulates an analyst browsing the property dashboard.

    This is the heaviest traffic pattern (~80% of real users):
    property list views, dashboard format, and portfolio summary.
    """

    weight = 80
    wait_time = between(1, 3)

    @task(5)
    def view_dashboard(self) -> None:
        """GET /api/v1/properties/dashboard — main dashboard view."""
        self.client.get(
            "/api/v1/properties/dashboard",
            headers=self.auth_headers,
            name="/api/v1/properties/dashboard",
        )

    @task(3)
    def view_portfolio_summary(self) -> None:
        """GET /api/v1/properties/summary — portfolio KPI summary."""
        self.client.get(
            "/api/v1/properties/summary",
            headers=self.auth_headers,
            name="/api/v1/properties/summary",
        )

    @task(2)
    def view_properties_paginated(self) -> None:
        """GET /api/v1/properties/ — paginated property list."""
        page = random.randint(1, 3)
        self.client.get(
            f"/api/v1/properties/?page={page}&page_size=20",
            headers=self.auth_headers,
            name="/api/v1/properties/?page=[n]",
        )

    @task(1)
    def view_analytics_dashboard(self) -> None:
        """GET /api/v1/analytics/dashboard — analytics overview."""
        self.client.get(
            "/api/v1/analytics/dashboard",
            headers=self.auth_headers,
            name="/api/v1/analytics/dashboard",
        )


class DealBrowserUser(AuthenticatedUser):
    """Simulates a user browsing the deal pipeline.

    Moderately heavy traffic (~15%): deal list views and individual deal details.
    """

    weight = 15
    wait_time = between(1, 3)
    _deal_ids: list[int] = []

    @task(5)
    def browse_deals(self) -> None:
        """GET /api/v1/deals — paginated deal list."""
        response = self.client.get(
            "/api/v1/deals?page_size=100",
            headers=self.auth_headers,
            name="/api/v1/deals?page_size=100",
        )
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            self._deal_ids = [d["id"] for d in items if "id" in d]

    @task(3)
    def view_deal_detail(self) -> None:
        """GET /api/v1/deals/{id} — individual deal detail."""
        if not self._deal_ids:
            return
        deal_id = random.choice(self._deal_ids)
        self.client.get(
            f"/api/v1/deals/{deal_id}",
            headers=self.auth_headers,
            name="/api/v1/deals/[id]",
        )

    @task(1)
    def view_deal_pipeline(self) -> None:
        """GET /api/v1/analytics/deal-pipeline — pipeline analytics."""
        self.client.get(
            "/api/v1/analytics/deal-pipeline",
            headers=self.auth_headers,
            name="/api/v1/analytics/deal-pipeline",
        )


class AdminUser(AuthenticatedUser):
    """Simulates an admin checking system health and audit logs.

    Light traffic (~5%): health checks and audit log browsing.
    """

    weight = 5
    wait_time = between(2, 5)

    @task(3)
    def check_health(self) -> None:
        """GET /api/v1/health — legacy health check (no auth required)."""
        self.client.get(
            "/api/v1/health",
            name="/api/v1/health",
        )

    @task(2)
    def check_health_status(self) -> None:
        """GET /api/v1/health/status — detailed health check (no auth required)."""
        self.client.get(
            "/api/v1/health/status",
            name="/api/v1/health/status",
        )

    @task(1)
    def view_audit_log(self) -> None:
        """GET /api/v1/admin/audit-log — admin audit trail."""
        self.client.get(
            "/api/v1/admin/audit-log",
            headers=self.auth_headers,
            name="/api/v1/admin/audit-log",
        )


# ---------------------------------------------------------------------------
# Event hooks for aggregate reporting
# ---------------------------------------------------------------------------


@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs) -> None:
    """Print a summary when the test completes."""
    stats = environment.runner.stats
    total = stats.total
    if total.num_requests > 0:
        print(
            f"\n{'=' * 60}\n"
            f"Load Test Summary\n"
            f"{'=' * 60}\n"
            f"Total requests:  {total.num_requests}\n"
            f"Failed requests: {total.num_failures}\n"
            f"Avg response:    {total.avg_response_time:.0f} ms\n"
            f"Median response: {total.median_response_time:.0f} ms\n"
            f"95th percentile: {total.get_response_time_percentile(0.95):.0f} ms\n"
            f"99th percentile: {total.get_response_time_percentile(0.99):.0f} ms\n"
            f"Requests/s:      {total.total_rps:.1f}\n"
            f"{'=' * 60}\n"
        )
