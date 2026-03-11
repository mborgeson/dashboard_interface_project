"""
Proforma Expansion regression tests (Team 46).

Covers the changes made during deferred-group promotion:
1. _extract_single_file validate parameter passthrough
2. run_group_extraction calling with validate=False
3. promote_proforma_groups.py script logic
4. Reference mapping format expected by run_group_extraction
5. Cross-group property collision detection in process_files

Run with: pytest tests/test_extraction/test_proforma_expansion.py -v
"""

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.extraction.common import (
    _extract_single_file,
    process_files,
)
from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
from app.db.base import Base

# ============================================================================
# DB fixtures (SQLite in-memory, StaticPool — matches project convention)
# SQLite limitation (T-DEBT-023): No server_default, no begin_nested().
# See tests/test_integration/ for PG equivalents.
# ============================================================================

SYNC_TEST_DATABASE_URL = "sqlite:///:memory:"

sync_test_engine = create_engine(
    SYNC_TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)

SyncTestSession = sessionmaker(
    bind=sync_test_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
def sync_db_session() -> Generator[Session, None, None]:
    """Create a sync database session for tests."""
    Base.metadata.create_all(bind=sync_test_engine)
    session = SyncTestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_test_engine)


# ============================================================================
# 1. _extract_single_file validate parameter
# ============================================================================


class TestExtractSingleFileValidateParam:
    """Verify the validate kwarg is forwarded to extractor.extract_from_file."""

    def test_validate_defaults_to_true(self):
        """Default call should pass validate=True to the extractor."""
        mock_ext = MagicMock()
        mock_ext.extract_from_file.return_value = {"PROPERTY_NAME": "Test"}

        _extract_single_file(mock_ext, "/tmp/test.xlsb", "Deal A")

        mock_ext.extract_from_file.assert_called_once_with(
            "/tmp/test.xlsb", validate=True
        )

    def test_validate_false_passed_through(self):
        """Explicit validate=False should be forwarded to the extractor."""
        mock_ext = MagicMock()
        mock_ext.extract_from_file.return_value = {"PROPERTY_NAME": "Test"}

        _extract_single_file(mock_ext, "/tmp/test.xlsb", "Deal A", validate=False)

        mock_ext.extract_from_file.assert_called_once_with(
            "/tmp/test.xlsb", validate=False
        )

    def test_extraction_error_returns_none_result(self):
        """When extractor raises, result should be None and error populated."""
        mock_ext = MagicMock()
        mock_ext.extract_from_file.side_effect = RuntimeError("bad file")

        fp, dn, result, err = _extract_single_file(
            mock_ext, "/tmp/bad.xlsb", "Bad Deal", validate=False
        )

        assert result is None
        assert "bad file" in err
        assert fp == "/tmp/bad.xlsb"
        assert dn == "Bad Deal"


# ============================================================================
# 2. run_group_extraction calls with validate=False
# ============================================================================


class TestGroupExtractionValidateFalse:
    """Verify run_group_extraction bypasses FileFilter via validate=False."""

    def test_group_extraction_passes_validate_false(self, sync_db_session, tmp_path):
        """run_group_extraction should call _extract_single_file with validate=False."""
        from app.extraction.group_pipeline import GroupExtractionPipeline

        # Set up minimal data directory with groups.json and reference_mapping
        data_dir = tmp_path / "extraction_groups"
        data_dir.mkdir()
        group_name = "Proforma-Base"
        group_dir = data_dir / group_name
        group_dir.mkdir()

        groups_data = {
            "groups": [
                {
                    "group_name": group_name,
                    "files": [
                        {"path": "/tmp/bolero.xlsb", "name": "bolero.xlsb"},
                    ],
                }
            ]
        }
        (data_dir / "groups.json").write_text(json.dumps(groups_data))

        mapping = {
            "group_name": group_name,
            "mappings": [
                {
                    "field_name": "PROPERTY_NAME",
                    "source_sheet": "Property",
                    "source_cell": "B1",
                    "match_tier": 1,
                    "confidence": 0.95,
                    "label_text": "Property Name",
                    "category": "General",
                    "production_sheet": "Property",
                    "production_cell": "B1",
                }
            ],
            "overall_confidence": 0.95,
            "tier_counts": {"1": 1},
            "total_mapped": 1,
            "total_unmapped": 0,
        }
        (group_dir / "reference_mapping.json").write_text(json.dumps(mapping))

        # Config file
        (data_dir / "config.json").write_text(
            json.dumps({"created_at": "", "updated_at": "", "total_extracted": 0})
        )

        pipeline = GroupExtractionPipeline(data_dir=str(data_dir))

        # Patch _extract_single_file to capture arguments
        captured_calls = []

        def fake_extract(extractor, fp, dn, validate=True):
            captured_calls.append({"validate": validate})
            return (fp, dn, {"PROPERTY_NAME": "Bolero"}, None)

        with patch(
            "app.api.v1.endpoints.extraction.common._extract_single_file",
            side_effect=fake_extract,
        ):
            report = pipeline.run_group_extraction(
                db=sync_db_session,
                group_name=group_name,
                dry_run=True,
            )

        assert len(captured_calls) == 1
        assert captured_calls[0]["validate"] is False
        assert report["files_processed"] == 1


# ============================================================================
# 3. promote_proforma_groups.py script logic
# ============================================================================


class TestPromoteProformaGroups:
    """Test build_reference_mapping and promote_groups from the promote script."""

    def test_build_reference_mapping_has_45_mappings(self):
        """build_reference_mapping should produce exactly 45 cell mappings."""
        from scripts.promote_proforma_groups import build_reference_mapping

        result = build_reference_mapping("Proforma-Base")
        assert result["group_name"] == "Proforma-Base"
        assert len(result["mappings"]) == 45
        assert result["total_mapped"] == 45
        assert result["total_unmapped"] == 0
        assert result["overall_confidence"] == 0.95

    def test_promote_groups_dry_run_no_modification(self, tmp_path):
        """dry_run=True should report what would happen without modifying files."""
        from scripts.promote_proforma_groups import promote_groups

        # Create a minimal groups.json in a temp location
        groups_data = {
            "groups": [],
            "deferred_groups": [
                {"group_name": "Proforma-Test", "file_count": 3, "files": []},
            ],
            "summary": {"active_groups": 0, "deferred_groups": 1, "active_files": 0},
        }
        groups_file = tmp_path / "groups.json"
        groups_file.write_text(json.dumps(groups_data))

        with patch(
            "scripts.promote_proforma_groups.GROUPS_FILE", groups_file
        ), patch("scripts.promote_proforma_groups.DATA_DIR", tmp_path):
            result = promote_groups(dry_run=True)

        assert result["promoted"] == 0
        assert result["would_promote"] == 1

        # Verify groups.json was NOT modified
        after = json.loads(groups_file.read_text())
        assert len(after["deferred_groups"]) == 1
        assert len(after["groups"]) == 0

    def test_promote_groups_execute_moves_to_active(self, tmp_path):
        """dry_run=False should move deferred groups to active and create mappings."""
        from scripts.promote_proforma_groups import promote_groups

        groups_data = {
            "groups": [{"group_name": "Existing", "file_count": 2}],
            "deferred_groups": [
                {
                    "group_name": "Proforma-A",
                    "file_count": 5,
                    "files": [],
                    "defer_reason": "unsupported template",
                },
            ],
            "summary": {"active_groups": 1, "deferred_groups": 1, "active_files": 2},
        }
        groups_file = tmp_path / "groups.json"
        groups_file.write_text(json.dumps(groups_data))

        with patch(
            "scripts.promote_proforma_groups.GROUPS_FILE", groups_file
        ), patch("scripts.promote_proforma_groups.DATA_DIR", tmp_path):
            result = promote_groups(dry_run=False)

        assert result["promoted"] == 1
        assert "Proforma-A" in result["groups"]
        assert result["mappings_per_group"] == 45

        # Verify groups.json was updated
        after = json.loads(groups_file.read_text())
        assert len(after["deferred_groups"]) == 0
        assert len(after["groups"]) == 2  # Existing + Proforma-A

        promoted = [g for g in after["groups"] if g["group_name"] == "Proforma-A"][0]
        assert promoted["status"] == "active"
        assert promoted["promoted_from"] == "deferred"
        assert "original_defer_reason" in promoted
        assert "defer_reason" not in promoted

        # Verify reference_mapping.json was created
        mapping_path = tmp_path / "Proforma-A" / "reference_mapping.json"
        assert mapping_path.exists()
        mapping_data = json.loads(mapping_path.read_text())
        assert len(mapping_data["mappings"]) == 45


# ============================================================================
# 4. Reference mapping format validation
# ============================================================================


class TestReferenceMappingFormat:
    """Verify reference_mapping.json has all fields expected by run_group_extraction."""

    REQUIRED_KEYS = {
        "field_name",
        "source_sheet",
        "source_cell",
        "match_tier",
        "confidence",
        "label_text",
        "category",
        "production_sheet",
        "production_cell",
    }

    def test_every_mapping_has_required_keys(self):
        """Each mapping entry must have all 9 required keys."""
        from scripts.promote_proforma_groups import build_reference_mapping

        result = build_reference_mapping("TestGroup")
        for i, m in enumerate(result["mappings"]):
            missing = self.REQUIRED_KEYS - set(m.keys())
            assert not missing, f"Mapping {i} ({m.get('field_name')}) missing: {missing}"

    def test_mappings_cover_key_fields(self):
        """Mappings should include the critical financial fields."""
        from scripts.promote_proforma_groups import build_reference_mapping

        result = build_reference_mapping("TestGroup")
        field_names = {m["field_name"] for m in result["mappings"]}

        expected_fields = {
            "PROPERTY_NAME",
            "PURCHASE_PRICE",
            "TOTAL_UNITS",
            "GOING_IN_CAP_RATE",
            "T3_RETURN_ON_COST",
            "LEVERED_RETURNS_IRR",
            "LEVERED_RETURNS_MOIC",
            "LOAN_AMOUNT",
            "INTEREST_RATE",
        }
        missing = expected_fields - field_names
        assert not missing, f"Missing critical fields: {missing}"


# ============================================================================
# 5. Cross-group property collision detection
# ============================================================================


class TestPropertyCollisionDetection:
    """Test that process_files warns when two files produce the same property_name."""

    def test_collision_logged_when_same_property_from_two_files(
        self, sync_db_session: Session
    ):
        """Two files with same PROPERTY_NAME should trigger a collision warning."""
        run = ExtractionRunCRUD.create(sync_db_session, trigger_type="manual")

        mock_extractor = MagicMock()
        # Both files extract the same PROPERTY_NAME
        mock_extractor.extract_from_file.side_effect = lambda path, **kw: {
            "PROPERTY_NAME": "Shared Property",
            "PURCHASE_PRICE": 1_000_000,
        }

        files = [
            {"file_path": "/tmp/uw_model_a.xlsb", "deal_name": "Deal A"},
            {"file_path": "/tmp/proforma_a.xlsb", "deal_name": "Deal A Pro"},
        ]

        with (
            patch("app.extraction.ExcelDataExtractor", return_value=mock_extractor),
            patch(
                "app.services.extraction.change_detector.should_extract_deal",
                return_value=(True, "new_deal"),
            ),
            patch(
                "app.crud.extraction.sync_extracted_to_properties",
                return_value={"created": 0, "updated": 0},
            ),
            patch(
                "app.api.v1.endpoints.extraction.common.logger"
            ) as mock_logger,
        ):
            process_files(
                sync_db_session,
                run.id,
                files,
                {"PROPERTY_NAME": MagicMock(), "PURCHASE_PRICE": MagicMock()},
                ExtractionRunCRUD,
                ExtractedValueCRUD,
                max_workers=1,
            )

        # Verify the collision warning was emitted
        collision_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c[0][0] == "property_name_collision"
        ]
        assert len(collision_calls) == 1, (
            f"Expected 1 collision warning, got {len(collision_calls)}"
        )
