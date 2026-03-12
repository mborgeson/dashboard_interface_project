"""Tests for report template CRUD, report generation, and queue endpoints."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.models.report_template import ReportTemplate

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def seed_template(db_session) -> int:
    """Seed a single report template and return its ID."""
    now = datetime.now(UTC).isoformat()
    await db_session.execute(
        text(
            "INSERT INTO report_templates "
            "(id, name, description, category, sections, export_formats, "
            "is_default, created_by, config, is_deleted, created_at, updated_at) "
            "VALUES (1, 'Monthly Portfolio Report', 'Monthly overview', 'executive', "
            '\'["summary","financials"]\', \'["pdf","excel"]\', '
            f"0, 'System', NULL, 0, '{now}', '{now}')"
        )
    )
    await db_session.commit()
    return 1


@pytest.fixture
async def seed_multiple_templates(db_session) -> list[int]:
    """Seed multiple report templates and return their IDs."""
    now = datetime.now(UTC).isoformat()
    templates = [
        (1, "Monthly Portfolio Report", "executive", 1),
        (2, "Market Analysis", "market", 0),
        (3, "Financial Deep Dive", "financial", 0),
    ]
    for tid, name, category, is_default in templates:
        await db_session.execute(
            text(
                "INSERT INTO report_templates "
                "(id, name, description, category, sections, export_formats, "
                "is_default, created_by, config, is_deleted, created_at, updated_at) "
                "VALUES (:id, :name, :name, :category, '[]', '[\"pdf\"]', "
                f":is_default, 'System', NULL, 0, '{now}', '{now}')"
            ),
            {"id": tid, "name": name, "category": category, "is_default": is_default},
        )
    await db_session.commit()
    return [1, 2, 3]


# =============================================================================
# 1. List report templates — GET /api/v1/reporting/templates
# =============================================================================

# Auth-required tests first (no auto_auth)


@pytest.mark.asyncio
async def test_list_templates_returns_empty(client, db_session, auto_auth):
    """GET /templates returns empty list when no templates exist."""
    response = await client.get("/api/v1/reporting/templates")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_templates_returns_seeded(
    client, db_session, seed_multiple_templates, auto_auth
):
    """GET /templates returns all seeded templates."""
    response = await client.get("/api/v1/reporting/templates")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_list_templates_filter_by_category(
    client, db_session, seed_multiple_templates, auto_auth
):
    """GET /templates?category=market filters correctly."""
    response = await client.get("/api/v1/reporting/templates?category=market")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "market"


@pytest.mark.asyncio
async def test_list_templates_filter_by_is_default(
    client, db_session, seed_multiple_templates, auto_auth
):
    """GET /templates?is_default=true returns only default templates."""
    response = await client.get("/api/v1/reporting/templates?is_default=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["is_default"] is True


@pytest.mark.asyncio
async def test_list_templates_pagination(
    client, db_session, seed_multiple_templates, auto_auth
):
    """GET /templates?page=1&page_size=2 paginates correctly."""
    response = await client.get("/api/v1/reporting/templates?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2


# =============================================================================
# 2. Get single template — GET /api/v1/reporting/templates/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_get_template_by_id(client, db_session, seed_template, auto_auth):
    """GET /templates/{id} returns the specific template."""
    response = await client.get("/api/v1/reporting/templates/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Monthly Portfolio Report"
    assert data["category"] == "executive"
    assert data["created_by"] == "System"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_template_not_found(client, db_session, auto_auth):
    """GET /templates/{id} returns 404 for nonexistent template."""
    response = await client.get("/api/v1/reporting/templates/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_template_soft_deleted_returns_404(
    client, db_session, seed_template, auto_auth
):
    """GET /templates/{id} returns 404 for a soft-deleted template."""
    # Soft-delete the template
    now = datetime.now(UTC).isoformat()
    await db_session.execute(
        text(
            f"UPDATE report_templates SET is_deleted = 1, deleted_at = '{now}' WHERE id = 1"
        )
    )
    await db_session.commit()

    response = await client.get("/api/v1/reporting/templates/1")
    assert response.status_code == 404


# =============================================================================
# 3. Create template — POST /api/v1/reporting/templates (auth enforcement)
# =============================================================================


@pytest.mark.asyncio
async def test_create_template(client, db_session, auto_auth):
    """POST /templates creates a new template and returns 201."""
    payload = {
        "name": "Custom Report",
        "description": "A custom report template",
        "category": "custom",
        "sections": ["overview", "details"],
        "export_formats": ["pdf", "excel"],
        "is_default": False,
        "created_by": "test_user",
    }
    response = await client.post("/api/v1/reporting/templates", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Custom Report"
    assert data["description"] == "A custom report template"
    assert data["category"] == "custom"
    assert data["sections"] == ["overview", "details"]
    assert data["export_formats"] == ["pdf", "excel"]
    assert data["is_default"] is False
    assert data["created_by"] == "test_user"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_template_minimal(client, db_session, auto_auth):
    """POST /templates with minimal fields uses defaults."""
    payload = {"name": "Bare Template"}
    response = await client.post("/api/v1/reporting/templates", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Bare Template"
    assert data["category"] == "custom"
    assert data["is_default"] is False


@pytest.mark.asyncio
async def test_create_template_invalid_category(client, db_session, auto_auth):
    """POST /templates with invalid category returns 422."""
    payload = {"name": "Bad Category", "category": "nonexistent"}
    response = await client.post("/api/v1/reporting/templates", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_template_missing_name(client, db_session, auto_auth):
    """POST /templates without name returns 422."""
    payload = {"description": "No name provided"}
    response = await client.post("/api/v1/reporting/templates", json=payload)
    assert response.status_code == 422


# =============================================================================
# 4. Update template — PUT /api/v1/reporting/templates/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_update_template(client, db_session, seed_template, auto_auth):
    """PUT /templates/{id} updates the template fields."""
    payload = {
        "name": "Updated Report",
        "description": "Updated description",
        "category": "financial",
    }
    response = await client.put("/api/v1/reporting/templates/1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Report"
    assert data["description"] == "Updated description"
    assert data["category"] == "financial"


@pytest.mark.asyncio
async def test_update_template_not_found(client, db_session, auto_auth):
    """PUT /templates/{id} returns 404 for nonexistent template."""
    payload = {"name": "Ghost"}
    response = await client.put("/api/v1/reporting/templates/999", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_template_partial(client, db_session, seed_template, auto_auth):
    """PUT /templates/{id} with partial data only updates provided fields."""
    payload = {"description": "New description only"}
    response = await client.put("/api/v1/reporting/templates/1", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "New description only"
    # Name should remain unchanged
    assert data["name"] == "Monthly Portfolio Report"


# =============================================================================
# 5. Delete template — DELETE /api/v1/reporting/templates/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_delete_template(client, db_session, seed_template, auto_auth):
    """DELETE /templates/{id} returns 204 and soft-deletes the template."""
    response = await client.delete("/api/v1/reporting/templates/1")
    assert response.status_code == 204

    # Confirm it's now 404
    response = await client.get("/api/v1/reporting/templates/1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_not_found(client, db_session, auto_auth):
    """DELETE /templates/{id} returns 404 for nonexistent template."""
    response = await client.delete("/api/v1/reporting/templates/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_already_deleted(
    client, db_session, seed_template, auto_auth
):
    """DELETE /templates/{id} returns 404 for an already-deleted template."""
    # Delete once
    response = await client.delete("/api/v1/reporting/templates/1")
    assert response.status_code == 204

    # Delete again
    response = await client.delete("/api/v1/reporting/templates/1")
    assert response.status_code == 404


# =============================================================================
# 6. Generate report — POST /api/v1/reporting/generate (auth enforcement)
# =============================================================================


@pytest.mark.asyncio
async def test_generate_report(client, db_session, seed_template, auto_auth):
    """POST /generate queues a report and returns queued_report_id."""
    payload = {
        "template_id": 1,
        "name": "Q4 2025 Portfolio Report",
        "format": "pdf",
    }
    response = await client.post("/api/v1/reporting/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "queued_report_id" in data
    assert data["status"] == "pending"
    assert "Q4 2025 Portfolio Report" in data["message"]


@pytest.mark.asyncio
async def test_generate_report_with_excel(client, db_session, seed_template, auto_auth):
    """POST /generate supports excel format."""
    payload = {
        "template_id": 1,
        "name": "Excel Report",
        "format": "excel",
    }
    response = await client.post("/api/v1/reporting/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_generate_report_template_not_found(client, db_session, auto_auth):
    """POST /generate returns 404 when template does not exist."""
    payload = {
        "template_id": 999,
        "name": "Ghost Report",
        "format": "pdf",
    }
    response = await client.post("/api/v1/reporting/generate", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_report_missing_fields(client, db_session, auto_auth):
    """POST /generate without required fields returns 422."""
    payload = {"format": "pdf"}
    response = await client.post("/api/v1/reporting/generate", json=payload)
    assert response.status_code == 422


# =============================================================================
# 7. List queued reports — GET /api/v1/reporting/queue
# =============================================================================


@pytest.mark.asyncio
async def test_list_queued_reports_empty(client, db_session, auto_auth):
    """GET /queue returns empty list when no reports are queued."""
    response = await client.get("/api/v1/reporting/queue")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_queued_reports_after_generate(
    client, db_session, seed_template, auto_auth
):
    """GET /queue returns queued reports after generation."""
    # Generate a report first
    payload = {
        "template_id": 1,
        "name": "Test Queue Report",
        "format": "pdf",
    }
    gen_response = await client.post("/api/v1/reporting/generate", json=payload)
    assert gen_response.status_code == 200

    # List queue
    response = await client.get("/api/v1/reporting/queue")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["name"] == "Test Queue Report"
    assert item["status"] == "pending"
    assert item["template_name"] == "Monthly Portfolio Report"


@pytest.mark.asyncio
async def test_get_queued_report_by_id(client, db_session, seed_template, auto_auth):
    """GET /queue/{id} returns a specific queued report."""
    # Generate a report
    payload = {
        "template_id": 1,
        "name": "Specific Report",
        "format": "pdf",
    }
    gen_response = await client.post("/api/v1/reporting/generate", json=payload)
    queued_id = gen_response.json()["queued_report_id"]

    response = await client.get(f"/api/v1/reporting/queue/{queued_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == queued_id
    assert data["name"] == "Specific Report"
    assert data["template_name"] == "Monthly Portfolio Report"


@pytest.mark.asyncio
async def test_get_queued_report_not_found(client, db_session, auto_auth):
    """GET /queue/{id} returns 404 for nonexistent report."""
    response = await client.get("/api/v1/reporting/queue/999")
    assert response.status_code == 404


# =============================================================================
# 8. Auth enforcement — 401 without auth token
# =============================================================================


@pytest.mark.asyncio
async def test_list_templates_requires_auth(client, db_session):
    """GET /templates returns 401 without auth token."""
    response = await client.get("/api/v1/reporting/templates")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_template_requires_auth(client, db_session):
    """GET /templates/{id} returns 401 without auth token."""
    response = await client.get("/api/v1/reporting/templates/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_template_requires_auth(client, db_session):
    """POST /templates returns 401 without auth token."""
    payload = {"name": "Unauthorized Template"}
    response = await client.post("/api/v1/reporting/templates", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_template_requires_auth(client, db_session):
    """PUT /templates/{id} returns 401 without auth token."""
    payload = {"name": "Nope"}
    response = await client.put("/api/v1/reporting/templates/1", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_template_requires_auth(client, db_session):
    """DELETE /templates/{id} returns 401 without auth token."""
    response = await client.delete("/api/v1/reporting/templates/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generate_report_requires_auth(client, db_session):
    """POST /generate returns 401 without auth token."""
    payload = {"template_id": 1, "name": "No Auth", "format": "pdf"}
    response = await client.post("/api/v1/reporting/generate", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_queue_requires_auth(client, db_session):
    """GET /queue returns 401 without auth token."""
    response = await client.get("/api/v1/reporting/queue")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_queued_report_requires_auth(client, db_session):
    """GET /queue/{id} returns 401 without auth token."""
    response = await client.get("/api/v1/reporting/queue/1")
    assert response.status_code == 401
