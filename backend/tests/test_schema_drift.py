"""
Tests for Schema Drift Detection (Epic 4.1, UR-023).

Covers:
- DriftResult creation and severity classification
- check_drift() with identical, minor, moderate, and major changes
- Baseline save/load round-trip
- Alert CRUD (create, get with filters, resolve)
- API endpoint tests (GET list, POST resolve)
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.fingerprint import FileFingerprint, SheetFingerprint
from app.extraction.schema_drift import (
    THRESHOLD_INFO,
    THRESHOLD_OK,
    THRESHOLD_WARNING,
    DriftResult,
    SchemaDriftDetector,
    _classify_severity,
    _dimension_similarity,
    _header_similarity,
    _jaccard_similarity,
    load_baseline_fingerprint,
    save_baseline_fingerprint,
)

# ===========================================================================
# Fixtures — fingerprints
# ===========================================================================


def _make_sheet(
    name: str = "Summary",
    rows: int = 100,
    cols: int = 20,
    headers: list[str] | None = None,
    col_a: list[str] | None = None,
) -> SheetFingerprint:
    """Helper to build a SheetFingerprint quickly."""
    return SheetFingerprint(
        name=name,
        row_count=rows,
        col_count=cols,
        header_labels=headers or ["A", "B", "C"],
        col_a_labels=col_a or ["Row1", "Row2"],
        populated_cell_count=rows * cols,
    )


def _make_fingerprint(
    sheets: list[SheetFingerprint] | None = None,
    file_path: str = "/test/file.xlsx",
) -> FileFingerprint:
    """Helper to build a FileFingerprint quickly."""
    if sheets is None:
        sheets = [
            _make_sheet("Summary"),
            _make_sheet("Cash Flow", rows=200, cols=30),
            _make_sheet("Assumptions", rows=50, cols=10),
        ]
    return FileFingerprint(
        file_path=file_path,
        file_name=Path(file_path).name,
        file_size=10000,
        content_hash="abc123",
        sheet_count=len(sheets),
        sheet_signatures=[s.signature for s in sheets],
        sheets=sheets,
        total_populated_cells=sum(s.populated_cell_count for s in sheets),
        population_status="populated",
    )


# ===========================================================================
# Unit Tests — Severity Classification (Story 3)
# ===========================================================================


class TestSeverityClassification:
    """Test threshold-based severity classification."""

    def test_score_1_0_is_ok(self) -> None:
        assert _classify_severity(1.0) == "ok"

    def test_score_0_95_is_ok(self) -> None:
        assert _classify_severity(0.95) == "ok"

    def test_score_0_94_is_info(self) -> None:
        assert _classify_severity(0.94) == "info"

    def test_score_0_90_is_info(self) -> None:
        assert _classify_severity(0.90) == "info"

    def test_score_0_89_is_warning(self) -> None:
        assert _classify_severity(0.89) == "warning"

    def test_score_0_80_is_warning(self) -> None:
        assert _classify_severity(0.80) == "warning"

    def test_score_0_79_is_error(self) -> None:
        assert _classify_severity(0.79) == "error"

    def test_score_0_0_is_error(self) -> None:
        assert _classify_severity(0.0) == "error"


# ===========================================================================
# Unit Tests — Similarity Helpers
# ===========================================================================


class TestJaccardSimilarity:
    """Test Jaccard index computation."""

    def test_identical_sets(self) -> None:
        assert _jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self) -> None:
        assert _jaccard_similarity({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self) -> None:
        assert _jaccard_similarity({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)

    def test_both_empty(self) -> None:
        assert _jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self) -> None:
        assert _jaccard_similarity({"a"}, set()) == 0.0


class TestDimensionSimilarity:
    """Test dimension comparison across sheets."""

    def test_identical_dimensions(self) -> None:
        sheets = [_make_sheet("S1", rows=100, cols=20)]
        assert _dimension_similarity(sheets, sheets) == pytest.approx(1.0)

    def test_different_dimensions(self) -> None:
        base = [_make_sheet("S1", rows=100, cols=20)]
        changed = [_make_sheet("S1", rows=200, cols=20)]
        score = _dimension_similarity(base, changed)
        assert 0.0 < score < 1.0

    def test_missing_sheet_lowers_score(self) -> None:
        base = [_make_sheet("S1"), _make_sheet("S2")]
        new = [_make_sheet("S1")]
        score = _dimension_similarity(base, new)
        # S2 is absent; only S1 contributes, averaged over 2 total names
        assert score < 1.0

    def test_both_empty(self) -> None:
        assert _dimension_similarity([], []) == 1.0


class TestHeaderSimilarity:
    """Test header label comparison across sheets."""

    def test_identical_headers(self) -> None:
        sheets = [_make_sheet("S1", headers=["A", "B"])]
        assert _header_similarity(sheets, sheets) == pytest.approx(1.0)

    def test_different_headers(self) -> None:
        base = [_make_sheet("S1", headers=["A", "B"])]
        changed = [_make_sheet("S1", headers=["C", "D"])]
        assert _header_similarity(base, changed) == 0.0

    def test_partial_header_overlap(self) -> None:
        base = [_make_sheet("S1", headers=["A", "B"])]
        changed = [_make_sheet("S1", headers=["B", "C"])]
        score = _header_similarity(base, changed)
        assert 0.0 < score < 1.0


# ===========================================================================
# Unit Tests — DriftResult (Story 2)
# ===========================================================================


class TestDriftResult:
    """Test DriftResult dataclass."""

    def test_creation(self) -> None:
        result = DriftResult(
            group_name="group_1",
            file_path="/test/file.xlsx",
            similarity_score=0.92,
            severity="info",
            changed_sheets=["Summary"],
            missing_sheets=[],
            new_sheets=["NewSheet"],
        )
        assert result.group_name == "group_1"
        assert result.similarity_score == 0.92
        assert result.severity == "info"

    def test_to_dict(self) -> None:
        result = DriftResult(
            group_name="g1",
            file_path="/f.xlsx",
            similarity_score=1.0,
            severity="ok",
        )
        d = result.to_dict()
        assert d["group_name"] == "g1"
        assert d["similarity_score"] == 1.0
        assert isinstance(d["details"], dict)


# ===========================================================================
# Unit Tests — Baseline Save/Load (Story 1)
# ===========================================================================


class TestBaselinePersistence:
    """Test save/load round-trip for baseline fingerprints."""

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        fp = _make_fingerprint()
        save_baseline_fingerprint(tmp_path, "test_group", fp)

        loaded = load_baseline_fingerprint(tmp_path, "test_group")
        assert loaded is not None
        assert loaded.file_path == fp.file_path
        assert loaded.sheet_count == fp.sheet_count
        assert len(loaded.sheets) == len(fp.sheets)

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        result = load_baseline_fingerprint(tmp_path, "nonexistent")
        assert result is None

    def test_save_creates_baselines_directory(self, tmp_path: Path) -> None:
        fp = _make_fingerprint()
        save_baseline_fingerprint(tmp_path, "g1", fp)
        assert (tmp_path / "baselines" / "g1_baseline.json").exists()

    def test_load_corrupted_returns_none(self, tmp_path: Path) -> None:
        baselines_dir = tmp_path / "baselines"
        baselines_dir.mkdir(parents=True)
        (baselines_dir / "bad_baseline.json").write_text("not valid json")
        result = load_baseline_fingerprint(tmp_path, "bad")
        assert result is None

    def test_round_trip_preserves_sheet_details(self, tmp_path: Path) -> None:
        sheets = [
            _make_sheet("Summary", rows=150, cols=25, headers=["NOI", "Cap Rate"]),
            _make_sheet("Returns", rows=30, cols=5, headers=["IRR", "MOIC"]),
        ]
        fp = _make_fingerprint(sheets=sheets)
        save_baseline_fingerprint(tmp_path, "detailed", fp)

        loaded = load_baseline_fingerprint(tmp_path, "detailed")
        assert loaded is not None
        assert loaded.sheets[0].name == "Summary"
        assert loaded.sheets[0].row_count == 150
        assert "NOI" in loaded.sheets[0].header_labels


# ===========================================================================
# Unit Tests — SchemaDriftDetector.check_drift() (Story 2 & 3)
# ===========================================================================


class TestSchemaDriftDetector:
    """Test the main drift detection logic."""

    def test_identical_fingerprints_score_1(self, tmp_path: Path) -> None:
        """Identical file vs baseline => 1.0 / ok."""
        fp = _make_fingerprint()
        save_baseline_fingerprint(tmp_path, "group_a", fp)

        detector = SchemaDriftDetector(tmp_path)
        result = detector.check_drift("group_a", fp)

        assert result.similarity_score == 1.0
        assert result.severity == "ok"
        assert result.missing_sheets == []
        assert result.new_sheets == []
        assert result.changed_sheets == []

    def test_no_baseline_returns_ok(self, tmp_path: Path) -> None:
        """No baseline saved => defaults to 1.0 / ok."""
        fp = _make_fingerprint()
        detector = SchemaDriftDetector(tmp_path)
        result = detector.check_drift("missing_group", fp)

        assert result.similarity_score == 1.0
        assert result.severity == "ok"
        assert result.details.get("reason") == "no_baseline_available"

    def test_minor_change_info_severity(self, tmp_path: Path) -> None:
        """Minor structural change => info severity."""
        baseline = _make_fingerprint(
            sheets=[
                _make_sheet("Summary", rows=100, cols=20, headers=["A", "B", "C"]),
                _make_sheet("Cash Flow", rows=200, cols=30, headers=["D", "E", "F"]),
                _make_sheet("Assumptions", rows=50, cols=10, headers=["G", "H", "I"]),
            ]
        )
        save_baseline_fingerprint(tmp_path, "grp", baseline)

        # Slightly different dimensions and one header change
        modified = _make_fingerprint(
            sheets=[
                _make_sheet("Summary", rows=105, cols=20, headers=["A", "B", "C"]),
                _make_sheet("Cash Flow", rows=200, cols=30, headers=["D", "E", "F"]),
                _make_sheet("Assumptions", rows=50, cols=10, headers=["G", "H", "X"]),
            ]
        )

        detector = SchemaDriftDetector(tmp_path)
        result = detector.check_drift("grp", modified)

        # Expect high similarity but not 1.0
        assert result.similarity_score >= THRESHOLD_INFO
        assert result.severity in ("ok", "info")

    def test_moderate_change_warning_severity(self, tmp_path: Path) -> None:
        """Missing a sheet + header changes => warning severity."""
        baseline = _make_fingerprint(
            sheets=[
                _make_sheet("Summary", headers=["A", "B", "C", "D"]),
                _make_sheet("Cash Flow", headers=["E", "F", "G", "H"]),
                _make_sheet("Assumptions", headers=["I", "J", "K", "L"]),
                _make_sheet("Returns", headers=["M", "N", "O", "P"]),
            ]
        )
        save_baseline_fingerprint(tmp_path, "grp", baseline)

        # Remove one sheet, change headers on remaining
        modified = _make_fingerprint(
            sheets=[
                _make_sheet("Summary", headers=["A", "X", "Y", "Z"]),
                _make_sheet("Cash Flow", headers=["E", "Q", "R", "S"]),
                _make_sheet("Assumptions", headers=["I", "J", "K", "L"]),
            ]
        )

        detector = SchemaDriftDetector(tmp_path)
        result = detector.check_drift("grp", modified)

        # Should be in warning range (0.80-0.89) or lower
        assert result.similarity_score < THRESHOLD_INFO
        assert result.severity in ("warning", "error")
        assert "Returns" in result.missing_sheets

    def test_major_change_error_severity(self, tmp_path: Path) -> None:
        """Completely different sheets => error severity."""
        baseline = _make_fingerprint(
            sheets=[
                _make_sheet("Summary", headers=["A", "B"]),
                _make_sheet("Cash Flow", headers=["C", "D"]),
                _make_sheet("Assumptions", headers=["E", "F"]),
            ]
        )
        save_baseline_fingerprint(tmp_path, "grp", baseline)

        # Completely different sheet names
        modified = _make_fingerprint(
            sheets=[
                _make_sheet("Revenue", headers=["X", "Y"]),
                _make_sheet("Expenses", headers=["Z", "W"]),
            ]
        )

        detector = SchemaDriftDetector(tmp_path)
        result = detector.check_drift("grp", modified)

        assert result.similarity_score < THRESHOLD_WARNING
        assert result.severity == "error"
        assert len(result.missing_sheets) > 0
        assert len(result.new_sheets) > 0

    def test_changed_sheets_detected(self, tmp_path: Path) -> None:
        """Sheets with same name but different structure are flagged."""
        baseline = _make_fingerprint(
            sheets=[_make_sheet("Summary", rows=100, cols=20, headers=["A"])]
        )
        save_baseline_fingerprint(tmp_path, "grp", baseline)

        modified = _make_fingerprint(
            sheets=[_make_sheet("Summary", rows=999, cols=99, headers=["Z"])]
        )

        detector = SchemaDriftDetector(tmp_path)
        result = detector.check_drift("grp", modified)

        assert "Summary" in result.changed_sheets

    def test_details_contain_component_scores(self, tmp_path: Path) -> None:
        """DriftResult.details should have per-component similarity scores."""
        fp = _make_fingerprint()
        save_baseline_fingerprint(tmp_path, "grp", fp)

        detector = SchemaDriftDetector(tmp_path)
        result = detector.check_drift("grp", fp)

        assert "sheet_name_similarity" in result.details
        assert "dimension_similarity" in result.details
        assert "header_similarity" in result.details
        assert result.details["sheet_name_similarity"] == 1.0


# ===========================================================================
# Database Tests — Alert CRUD (Story 5)
# ===========================================================================


class TestSchemaDriftAlertCRUD:
    """Test CRUD operations for SchemaDriftAlert model."""

    @pytest.mark.asyncio
    async def test_create_alert(self, db_session: AsyncSession) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        alert = await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="group_1",
            file_path="/test/file.xlsx",
            similarity_score=0.85,
            severity="warning",
            changed_sheets=["Summary"],
            missing_sheets=["Returns"],
            new_sheets=[],
            details={"sheet_name_similarity": 0.9},
        )
        await db_session.commit()

        assert alert.id is not None
        assert alert.group_name == "group_1"
        assert float(alert.similarity_score) == pytest.approx(0.85, abs=0.001)
        assert alert.severity == "warning"
        assert alert.resolved is False
        assert alert.resolved_at is None

    @pytest.mark.asyncio
    async def test_get_alerts_no_filter(self, db_session: AsyncSession) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.85,
            severity="warning",
        )
        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g2",
            file_path="/b.xlsx",
            similarity_score=0.70,
            severity="error",
        )
        await db_session.commit()

        alerts = await SchemaDriftAlertCRUD.get_alerts(db_session)
        assert len(alerts) == 2

    @pytest.mark.asyncio
    async def test_get_alerts_filter_by_group(self, db_session: AsyncSession) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.85,
            severity="warning",
        )
        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g2",
            file_path="/b.xlsx",
            similarity_score=0.70,
            severity="error",
        )
        await db_session.commit()

        alerts = await SchemaDriftAlertCRUD.get_alerts(db_session, group_name="g1")
        assert len(alerts) == 1
        assert alerts[0].group_name == "g1"

    @pytest.mark.asyncio
    async def test_get_alerts_filter_by_severity(
        self, db_session: AsyncSession
    ) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.85,
            severity="warning",
        )
        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g2",
            file_path="/b.xlsx",
            similarity_score=0.70,
            severity="error",
        )
        await db_session.commit()

        alerts = await SchemaDriftAlertCRUD.get_alerts(db_session, severity="error")
        assert len(alerts) == 1
        assert alerts[0].severity == "error"

    @pytest.mark.asyncio
    async def test_get_alerts_filter_by_resolved(
        self, db_session: AsyncSession
    ) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        alert1 = await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.85,
            severity="warning",
        )
        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g2",
            file_path="/b.xlsx",
            similarity_score=0.70,
            severity="error",
        )
        await db_session.commit()

        # Resolve the first one
        await SchemaDriftAlertCRUD.resolve_alert(db_session, alert1.id)
        await db_session.commit()

        unresolved = await SchemaDriftAlertCRUD.get_alerts(db_session, resolved=False)
        assert len(unresolved) == 1
        assert unresolved[0].group_name == "g2"

        resolved = await SchemaDriftAlertCRUD.get_alerts(db_session, resolved=True)
        assert len(resolved) == 1
        assert resolved[0].group_name == "g1"

    @pytest.mark.asyncio
    async def test_resolve_alert(self, db_session: AsyncSession) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        alert = await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.85,
            severity="warning",
        )
        await db_session.commit()

        resolved = await SchemaDriftAlertCRUD.resolve_alert(db_session, alert.id)
        await db_session.commit()

        assert resolved is not None
        assert resolved.resolved is True
        assert resolved.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        result = await SchemaDriftAlertCRUD.resolve_alert(db_session, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_alerts_with_limit(self, db_session: AsyncSession) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        for i in range(5):
            await SchemaDriftAlertCRUD.create_alert(
                db_session,
                group_name=f"g{i}",
                file_path=f"/f{i}.xlsx",
                similarity_score=0.85,
                severity="warning",
            )
        await db_session.commit()

        alerts = await SchemaDriftAlertCRUD.get_alerts(db_session, limit=3)
        assert len(alerts) == 3


# ===========================================================================
# API Endpoint Tests (Story 5)
# ===========================================================================


class TestSchemaDriftAPI:
    """Test the drift alert API endpoints."""

    @pytest.mark.asyncio
    async def test_list_alerts_empty(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        response = await client.get(
            "/api/v1/extraction/drift-alerts",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["alerts"] == []

    @pytest.mark.asyncio
    async def test_list_alerts_with_data(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="test_group",
            file_path="/test.xlsx",
            similarity_score=0.88,
            severity="warning",
            changed_sheets=["Summary"],
        )
        await db_session.commit()

        response = await client.get(
            "/api/v1/extraction/drift-alerts",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        alert = data["alerts"][0]
        assert alert["group_name"] == "test_group"
        assert alert["severity"] == "warning"
        assert alert["resolved"] is False

    @pytest.mark.asyncio
    async def test_list_alerts_filter_by_severity(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.88,
            severity="warning",
        )
        await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g2",
            file_path="/b.xlsx",
            similarity_score=0.70,
            severity="error",
        )
        await db_session.commit()

        response = await client.get(
            "/api/v1/extraction/drift-alerts?severity=error",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["alerts"][0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_resolve_alert(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        db_session: AsyncSession,
    ) -> None:
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        alert = await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.85,
            severity="warning",
        )
        await db_session.commit()

        response = await client.post(
            f"/api/v1/extraction/drift-alerts/{alert.id}/resolve",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resolved"] is True
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert_404(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
    ) -> None:
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/extraction/drift-alerts/{fake_id}/resolve",
            headers=admin_auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_alerts_no_auth_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/extraction/drift-alerts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_resolve_alert_analyst_forbidden(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ) -> None:
        """Analyst (not manager) should get 403 when trying to resolve."""
        from app.crud.schema_drift import SchemaDriftAlertCRUD

        alert = await SchemaDriftAlertCRUD.create_alert(
            db_session,
            group_name="g1",
            file_path="/a.xlsx",
            similarity_score=0.85,
            severity="warning",
        )
        await db_session.commit()

        response = await client.post(
            f"/api/v1/extraction/drift-alerts/{alert.id}/resolve",
            headers=auth_headers,  # analyst, not manager
        )
        assert response.status_code == 403
