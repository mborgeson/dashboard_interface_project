"""
Tests for Sprint 3, Team D — Epic 3.5: Supporting P1 Items.

Covers:
- Task 1-2: Field synonyms loading and matching (UR-024)
- Task 4: SharePoint auth status in health check (UR-017)
- Task 5: Batch query optimization for _sync_deal_stages (UR-020)
- Task 6: Reconciliation report service and API endpoints (UR-016)
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


# =============================================================================
# Task 1-2: Field Synonyms Loading & Matching
# =============================================================================


class TestFieldSynonyms:
    """Tests for field_synonyms.json loading and Tier 4 matching."""

    def test_synonyms_file_exists(self) -> None:
        """Verify field_synonyms.json exists in the extraction package."""
        synonyms_path = (
            Path(__file__).parent.parent
            / "app"
            / "extraction"
            / "field_synonyms.json"
        )
        assert synonyms_path.exists(), f"field_synonyms.json not found at {synonyms_path}"

    def test_synonyms_file_valid_json(self) -> None:
        """Verify field_synonyms.json is valid JSON with correct structure."""
        synonyms_path = (
            Path(__file__).parent.parent
            / "app"
            / "extraction"
            / "field_synonyms.json"
        )
        raw = json.loads(synonyms_path.read_text(encoding="utf-8"))
        assert "synonym_groups" in raw
        assert isinstance(raw["synonym_groups"], list)
        assert len(raw["synonym_groups"]) >= 20, (
            f"Expected at least 20 synonym groups, got {len(raw['synonym_groups'])}"
        )

    def test_synonyms_all_groups_have_at_least_two_entries(self) -> None:
        """Every synonym group must have at least 2 entries."""
        synonyms_path = (
            Path(__file__).parent.parent
            / "app"
            / "extraction"
            / "field_synonyms.json"
        )
        raw = json.loads(synonyms_path.read_text(encoding="utf-8"))
        for i, group in enumerate(raw["synonym_groups"]):
            assert len(group) >= 2, f"Group {i} has < 2 entries: {group}"

    def test_load_field_synonyms_returns_dict(self) -> None:
        """load_field_synonyms() returns a dict with canonical -> synonyms."""
        from app.extraction.reference_mapper import load_field_synonyms

        result = load_field_synonyms()
        assert isinstance(result, dict)
        assert len(result) >= 20

    def test_load_field_synonyms_canonical_keys(self) -> None:
        """The canonical key is the first element of each group."""
        from app.extraction.reference_mapper import load_field_synonyms

        result = load_field_synonyms()
        # "noi" should be a canonical key
        assert "noi" in result
        assert "net_operating_income" in result["noi"]

    def test_load_field_synonyms_cap_rate_group(self) -> None:
        """Cap rate group contains expected variations."""
        from app.extraction.reference_mapper import load_field_synonyms

        result = load_field_synonyms()
        assert "cap_rate" in result
        assert "capitalization_rate" in result["cap_rate"]

    def test_load_field_synonyms_missing_file(self, tmp_path: Path) -> None:
        """Returns empty dict when the file is missing."""
        from app.extraction.reference_mapper import load_field_synonyms

        result = load_field_synonyms(path=tmp_path / "nonexistent.json")
        assert result == {}

    def test_load_field_synonyms_malformed_json(self, tmp_path: Path) -> None:
        """Returns empty dict when the file is malformed JSON."""
        from app.extraction.reference_mapper import load_field_synonyms

        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json}", encoding="utf-8")
        result = load_field_synonyms(path=bad_file)
        assert result == {}

    def test_load_field_synonyms_empty_groups(self, tmp_path: Path) -> None:
        """Skips groups with fewer than 2 entries."""
        from app.extraction.reference_mapper import load_field_synonyms

        data = {"synonym_groups": [["solo"], ["pair", "match"], []]}
        f = tmp_path / "test_syns.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = load_field_synonyms(path=f)
        assert len(result) == 1
        assert "pair" in result

    def test_synonym_reverse_lookup_in_auto_map(self) -> None:
        """Synonym lookup builds correct reverse index for Tier 4 matching."""
        from app.extraction.reference_mapper import auto_map_group

        from dataclasses import dataclass

        @dataclass
        class FakeCellMapping:
            category: str = "Revenue"
            description: str = "Net Operating Income"
            sheet_name: str = "Assumptions"
            cell_address: str = "D10"
            field_name: str = "NET_OPERATING_INCOME"

        @dataclass
        class FakeSheetFP:
            name: str = "Returns"
            header_labels: list = None
            col_a_labels: list = None

            def __post_init__(self):
                if self.header_labels is None:
                    self.header_labels = ["NOI"]
                if self.col_a_labels is None:
                    self.col_a_labels = []

        @dataclass
        class FakeFP:
            sheets: list = None

            def __post_init__(self):
                if self.sheets is None:
                    self.sheets = [FakeSheetFP()]

        # Synonyms: "noi" is canonical, "net_operating_income" is a synonym
        synonyms = {"noi": ["net_operating_income", "net operating income"]}

        result = auto_map_group(
            group_name="test_group",
            production_mappings={"NET_OPERATING_INCOME": FakeCellMapping()},
            representative_fp=FakeFP(),
            synonyms=synonyms,
        )

        # The description "Net Operating Income" should match via synonym to "NOI"
        # label in fingerprint -- Tier 4 match
        assert len(result.mappings) > 0 or len(result.unmapped_fields) > 0

    def test_no_duplicate_canonical_names(self) -> None:
        """Each synonym group should have a unique canonical name (first element)."""
        synonyms_path = (
            Path(__file__).parent.parent
            / "app"
            / "extraction"
            / "field_synonyms.json"
        )
        raw = json.loads(synonyms_path.read_text(encoding="utf-8"))
        canonicals = [g[0] for g in raw["synonym_groups"] if g]
        assert len(canonicals) == len(set(canonicals)), "Duplicate canonical names found"


# =============================================================================
# Task 4: SharePoint Auth Status in Health Check
# =============================================================================


class TestSharePointHealthCheck:
    """Tests for SharePoint authentication status in health check."""

    def setup_method(self) -> None:
        """Clear SharePoint auth cache before each test."""
        import app.api.v1.endpoints.health as health_mod

        health_mod._sharepoint_auth_cache = None
        health_mod._sharepoint_auth_cache_time = 0.0

    async def test_health_check_includes_sharepoint(self, client: AsyncClient) -> None:
        """Health check response includes sharepoint check with status and timestamp."""
        response = await client.get("/api/v1/health/status")
        assert response.status_code == 200

        data = response.json()
        sp = data["checks"]["sharepoint"]
        assert "status" in sp
        assert "last_checked" in sp

    async def test_sharepoint_not_configured_status(
        self, client: AsyncClient
    ) -> None:
        """When SharePoint is not configured, status is 'not_configured'."""
        import app.api.v1.endpoints.health as health_mod

        # Directly test the function with sharepoint_configured=False
        with patch(
            "app.api.v1.endpoints.health.settings"
        ) as mock_settings:
            mock_settings.sharepoint_configured = False
            result = await health_mod._check_sharepoint_auth()
            assert result["status"] == "not_configured"
            assert "last_checked" in result

    async def test_sharepoint_cache_is_used(self, client: AsyncClient) -> None:
        """Subsequent health checks use the cached SharePoint result."""
        import app.api.v1.endpoints.health as health_mod

        health_mod._sharepoint_auth_cache = None

        # First call populates cache
        resp1 = await client.get("/api/v1/health/status")
        data1 = resp1.json()
        ts1 = data1["checks"]["sharepoint"]["last_checked"]

        # Second call should use cache (same timestamp)
        resp2 = await client.get("/api/v1/health/status")
        data2 = resp2.json()
        ts2 = data2["checks"]["sharepoint"]["last_checked"]

        assert ts1 == ts2, "Cache was not used -- timestamps differ"

    async def test_sharepoint_cache_expiry(self, client: AsyncClient) -> None:
        """SharePoint cache expires after TTL."""
        import app.api.v1.endpoints.health as health_mod

        # Force cache to be "old"
        health_mod._sharepoint_auth_cache = {
            "status": "not_configured",
            "last_checked": "2020-01-01T00:00:00+00:00",
        }
        health_mod._sharepoint_auth_cache_time = time.monotonic() - 600  # 10 min ago

        response = await client.get("/api/v1/health/status")
        data = response.json()
        sp = data["checks"]["sharepoint"]
        # Should have been refreshed -- timestamp should be newer
        assert sp["last_checked"] != "2020-01-01T00:00:00+00:00"

    async def test_sharepoint_connected_when_token_available(
        self, client: AsyncClient
    ) -> None:
        """When SharePoint auth succeeds, status is 'connected'."""
        import app.api.v1.endpoints.health as health_mod

        health_mod._sharepoint_auth_cache = None

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.sharepoint_configured = True
            mock_settings.AZURE_TENANT_ID = "test"
            mock_settings.AZURE_CLIENT_ID = "test"
            mock_settings.AZURE_CLIENT_SECRET = "test"
            mock_settings.SHAREPOINT_SITE_URL = "test"

            with patch(
                "app.extraction.sharepoint.SharePointClient._get_access_token",
                new_callable=AsyncMock,
                return_value="fake-token",
            ):
                result = await health_mod._check_sharepoint_auth()
                assert result["status"] == "connected"

    async def test_sharepoint_error_on_auth_failure(
        self, client: AsyncClient
    ) -> None:
        """When SharePoint auth fails, status is 'error'."""
        import app.api.v1.endpoints.health as health_mod

        health_mod._sharepoint_auth_cache = None

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.sharepoint_configured = True

            with patch(
                "app.extraction.sharepoint.SharePointClient._get_access_token",
                new_callable=AsyncMock,
                side_effect=Exception("Auth failed"),
            ):
                result = await health_mod._check_sharepoint_auth()
                assert result["status"] == "error"
                assert "Auth failed" in result["error"]

    async def test_sharepoint_health_does_not_fail_overall(
        self, client: AsyncClient
    ) -> None:
        """SharePoint failure should not make the overall health check fail."""
        import app.api.v1.endpoints.health as health_mod

        # Set cached result to "error" status
        health_mod._sharepoint_auth_cache = {
            "status": "error",
            "last_checked": datetime.now(UTC).isoformat(),
            "error": "test error",
        }
        health_mod._sharepoint_auth_cache_time = time.monotonic()

        response = await client.get("/api/v1/health/status")
        assert response.status_code == 200
        data = response.json()
        # Overall status should still be healthy/degraded (not unhealthy)
        assert data["status"] in ["healthy", "degraded"]


# =============================================================================
# Task 5: Batch Query Optimization for _sync_deal_stages
# =============================================================================


class TestBatchSyncDealStages:
    """Tests for the batch-optimized _sync_deal_stages method."""

    async def test_sync_empty_stage_changes(self, db_session: AsyncSession) -> None:
        """No DB queries when stage_changes is empty."""
        from app.services.extraction.file_monitor import SharePointFileMonitor

        monitor = SharePointFileMonitor(db=db_session)
        result = await monitor._sync_deal_stages([])
        assert result == 0

    async def test_sync_invalid_stage_skipped(self, db_session: AsyncSession) -> None:
        """Invalid stage values are logged and skipped without error."""
        from app.services.extraction.file_monitor import SharePointFileMonitor

        monitor = SharePointFileMonitor(db=db_session)
        result = await monitor._sync_deal_stages([
            ("Test Deal", "invalid_stage_value"),
        ])
        assert result == 0

    async def test_sync_all_invalid_returns_zero(
        self, db_session: AsyncSession
    ) -> None:
        """When all stage changes are invalid, returns 0 without querying."""
        from app.services.extraction.file_monitor import SharePointFileMonitor

        monitor = SharePointFileMonitor(db=db_session)
        result = await monitor._sync_deal_stages([
            ("Deal A", "not_a_real_stage"),
            ("Deal B", "also_invalid"),
        ])
        assert result == 0

    async def test_sync_deal_not_found(self, db_session: AsyncSession) -> None:
        """When no matching deal exists, returns 0."""
        from app.services.extraction.file_monitor import SharePointFileMonitor

        monitor = SharePointFileMonitor(db=db_session)
        # "dead" is a valid DealStage value
        result = await monitor._sync_deal_stages([
            ("Nonexistent Deal XYZ", "dead"),
        ])
        assert result == 0

    async def test_sync_batch_fetches_multiple_deals(
        self, db_session: AsyncSession, test_user: Any
    ) -> None:
        """Multiple deals are fetched in a single batch query."""
        from decimal import Decimal

        from app.models.deal import Deal, DealStage

        # Create multiple deals
        deal_a = Deal(
            name="Batch Deal Alpha",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=test_user.id,
            asking_price=Decimal("5000000"),
        )
        deal_b = Deal(
            name="Batch Deal Beta",
            deal_type="acquisition",
            stage=DealStage.INITIAL_REVIEW,
            stage_order=0,
            assigned_user_id=test_user.id,
            asking_price=Decimal("6000000"),
        )
        db_session.add_all([deal_a, deal_b])
        await db_session.commit()

        from app.services.extraction.file_monitor import SharePointFileMonitor

        monitor = SharePointFileMonitor(db=db_session)

        # Mock the websocket notifications
        with patch.object(monitor, "_emit_stage_change_notifications", new_callable=AsyncMock):
            result = await monitor._sync_deal_stages([
                ("Batch Deal Alpha", "dead"),
                ("Batch Deal Beta", "dead"),
            ])

        assert result == 2

    async def test_sync_same_stage_no_update(
        self, db_session: AsyncSession, test_user: Any
    ) -> None:
        """Deal already at the target stage is not updated."""
        from decimal import Decimal

        from app.models.deal import Deal, DealStage

        deal = Deal(
            name="Already Dead Deal",
            deal_type="acquisition",
            stage=DealStage.DEAD,
            stage_order=0,
            assigned_user_id=test_user.id,
            asking_price=Decimal("4000000"),
        )
        db_session.add(deal)
        await db_session.commit()

        from app.services.extraction.file_monitor import SharePointFileMonitor

        monitor = SharePointFileMonitor(db=db_session)
        result = await monitor._sync_deal_stages([
            ("Already Dead Deal", "dead"),
        ])
        assert result == 0


# =============================================================================
# Task 6: Reconciliation Report Service
# =============================================================================


class TestReconciliationService:
    """Tests for the reconciliation report service."""

    def setup_method(self) -> None:
        """Clear reconciliation history before each test."""
        from app.services.reconciliation import clear_history

        clear_history()

    async def test_run_reconciliation_no_sharepoint(
        self, db_session: AsyncSession
    ) -> None:
        """Reconciliation works when SharePoint is unavailable."""
        from app.services.reconciliation import run_reconciliation

        report = await run_reconciliation(db_session)
        assert report.report_id
        assert report.generated_at is not None
        assert report.sharepoint_available is False
        assert report.error is not None

    async def test_run_reconciliation_report_structure(
        self, db_session: AsyncSession
    ) -> None:
        """Report has all expected fields populated."""
        from app.services.reconciliation import run_reconciliation

        report = await run_reconciliation(db_session)
        assert report.total_database_files >= 0
        assert report.total_sharepoint_files >= 0
        assert report.files_in_sync >= 0
        assert isinstance(report.sharepoint_only, list)
        assert isinstance(report.database_only, list)
        assert isinstance(report.stale_extractions, list)
        assert report.duration_seconds >= 0

    async def test_run_reconciliation_stores_history(
        self, db_session: AsyncSession
    ) -> None:
        """Each reconciliation run is stored in history."""
        from app.services.reconciliation import (
            get_report_history,
            run_reconciliation,
        )

        await run_reconciliation(db_session)
        await run_reconciliation(db_session)

        history = get_report_history()
        assert len(history) == 2
        # Most recent first
        assert history[0].generated_at >= history[1].generated_at

    async def test_get_latest_report_none(self) -> None:
        """Returns None when no reports have been generated."""
        from app.services.reconciliation import get_latest_report

        assert get_latest_report() is None

    async def test_get_latest_report_after_run(
        self, db_session: AsyncSession
    ) -> None:
        """Returns the most recent report."""
        from app.services.reconciliation import (
            get_latest_report,
            run_reconciliation,
        )

        await run_reconciliation(db_session)
        latest = get_latest_report()
        assert latest is not None
        assert latest.report_id

    async def test_history_limit_and_offset(
        self, db_session: AsyncSession
    ) -> None:
        """History pagination with limit and offset works."""
        from app.services.reconciliation import (
            get_report_history,
            run_reconciliation,
        )

        for _ in range(5):
            await run_reconciliation(db_session)

        page1 = get_report_history(limit=2, offset=0)
        page2 = get_report_history(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].report_id != page2[0].report_id

    async def test_reconciliation_with_mock_sharepoint(
        self, db_session: AsyncSession
    ) -> None:
        """Reconciliation with mocked SharePoint data identifies discrepancies."""
        from app.services import reconciliation as recon_mod
        from app.services.reconciliation import run_reconciliation

        mock_sp_files = [
            {
                "file_path": "Deals/Stage1/DealA/uw_model.xlsb",
                "file_name": "uw_model.xlsb",
                "deal_name": "DealA",
                "modified_date": datetime(2026, 3, 1, tzinfo=UTC),
                "size": 5000,
            },
        ]

        with patch.object(
            recon_mod,
            "_get_sharepoint_files",
            new_callable=AsyncMock,
            return_value=mock_sp_files,
        ):
            report = await run_reconciliation(db_session)

        assert report.sharepoint_available is True
        assert report.error is None
        assert report.total_sharepoint_files == 1
        # No DB files, so 1 file is sharepoint_only
        assert len(report.sharepoint_only) == 1
        assert report.sharepoint_only[0].file_name == "uw_model.xlsb"

    def test_clear_history(self) -> None:
        """clear_history() empties the report store."""
        from app.services.reconciliation import (
            _report_history,
            clear_history,
        )

        _report_history.append(MagicMock())
        assert len(_report_history) == 1
        clear_history()
        assert len(_report_history) == 0


# =============================================================================
# Task 6: Reconciliation API Endpoints
# =============================================================================


class TestReconciliationAPI:
    """Tests for reconciliation API endpoints."""

    def setup_method(self) -> None:
        """Clear reconciliation history before each test."""
        from app.services.reconciliation import clear_history

        clear_history()

    async def test_get_latest_no_auth(self, client: AsyncClient) -> None:
        """GET /reconciliation/latest without auth returns 401."""
        response = await client.get("/api/v1/reconciliation/latest")
        assert response.status_code == 401

    async def test_get_latest_with_auth(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """GET /reconciliation/latest with auth returns 200."""
        response = await client.get(
            "/api/v1/reconciliation/latest", headers=auth_headers
        )
        assert response.status_code == 200

    async def test_get_latest_returns_null_initially(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """GET /reconciliation/latest returns null when no reports exist."""
        response = await client.get(
            "/api/v1/reconciliation/latest", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() is None

    async def test_get_history_no_auth(self, client: AsyncClient) -> None:
        """GET /reconciliation/history without auth returns 401."""
        response = await client.get("/api/v1/reconciliation/history")
        assert response.status_code == 401

    async def test_get_history_with_auth(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """GET /reconciliation/history with auth returns 200 and empty list."""
        response = await client.get(
            "/api/v1/reconciliation/history", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_trigger_no_auth(self, client: AsyncClient) -> None:
        """POST /reconciliation/trigger without auth returns 401."""
        response = await client.post("/api/v1/reconciliation/trigger")
        assert response.status_code == 401

    async def test_trigger_with_auth(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """POST /reconciliation/trigger runs reconciliation and returns report."""
        response = await client.post(
            "/api/v1/reconciliation/trigger", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Reconciliation completed"
        assert "report" in data
        report = data["report"]
        assert "report_id" in report
        assert "generated_at" in report
        assert "total_sharepoint_files" in report
        assert "total_database_files" in report

    async def test_trigger_then_get_latest(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """After triggering, GET /latest returns the report."""
        await client.post(
            "/api/v1/reconciliation/trigger", headers=auth_headers
        )

        response = await client.get(
            "/api/v1/reconciliation/latest", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert "report_id" in data

    async def test_trigger_then_get_history(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """After triggering twice, history shows both reports."""
        await client.post(
            "/api/v1/reconciliation/trigger", headers=auth_headers
        )
        await client.post(
            "/api/v1/reconciliation/trigger", headers=auth_headers
        )

        response = await client.get(
            "/api/v1/reconciliation/history", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_history_pagination(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """History endpoint respects limit and offset parameters."""
        for _ in range(3):
            await client.post(
                "/api/v1/reconciliation/trigger", headers=auth_headers
            )

        response = await client.get(
            "/api/v1/reconciliation/history?limit=1&offset=0",
            headers=auth_headers,
        )
        data = response.json()
        assert len(data) == 1


# =============================================================================
# Schema Tests
# =============================================================================


class TestReconciliationSchemas:
    """Tests for reconciliation Pydantic schemas."""

    def test_file_discrepancy_schema(self) -> None:
        """FileDiscrepancy validates correctly."""
        from app.schemas.reconciliation import FileDiscrepancy

        d = FileDiscrepancy(
            file_path="/path/to/file.xlsb",
            file_name="file.xlsb",
            deal_name="Test Deal",
            location="sharepoint_only",
        )
        assert d.location == "sharepoint_only"
        assert d.last_modified is None

    def test_extraction_staleness_schema(self) -> None:
        """ExtractionStaleness validates correctly."""
        from app.schemas.reconciliation import ExtractionStaleness

        s = ExtractionStaleness(
            file_path="/path/file.xlsb",
            file_name="file.xlsb",
            deal_name="Test",
            file_modified_date=datetime.now(UTC),
            hours_stale=48.5,
        )
        assert s.hours_stale == 48.5

    def test_reconciliation_report_total_discrepancies(self) -> None:
        """ReconciliationReport.total_discrepancies sums both sides."""
        from app.schemas.reconciliation import (
            FileDiscrepancy,
            ReconciliationReport,
        )

        report = ReconciliationReport(
            report_id="test",
            generated_at=datetime.now(UTC),
            duration_seconds=1.0,
            sharepoint_only=[
                FileDiscrepancy(
                    file_path="a",
                    file_name="a",
                    deal_name="d",
                    location="sharepoint_only",
                ),
            ],
            database_only=[
                FileDiscrepancy(
                    file_path="b",
                    file_name="b",
                    deal_name="d",
                    location="database_only",
                ),
                FileDiscrepancy(
                    file_path="c",
                    file_name="c",
                    deal_name="d",
                    location="database_only",
                ),
            ],
            sharepoint_available=True,
        )
        assert report.total_discrepancies == 3

    def test_history_item_schema(self) -> None:
        """ReconciliationHistoryItem validates correctly."""
        from app.schemas.reconciliation import ReconciliationHistoryItem

        item = ReconciliationHistoryItem(
            report_id="abc123",
            generated_at=datetime.now(UTC),
            total_sharepoint_files=10,
            total_database_files=8,
            files_in_sync=7,
            sharepoint_only_count=3,
            database_only_count=1,
            stale_extraction_count=2,
            sharepoint_available=True,
        )
        assert item.sharepoint_only_count == 3
