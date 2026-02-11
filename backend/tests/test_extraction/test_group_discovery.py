"""
Tests for Phase 1 discovery and the GroupExtractionPipeline orchestrator.

Tests cover:
- Pipeline initialization and config persistence
- Discovery with CandidateFileFilter
- Deduplication (size+date, content hash)
- File count gate / batching
- Manifest generation and persistence
- Pipeline status tracking

Run with: pytest tests/test_extraction/test_group_discovery.py -v
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.extraction.group_pipeline import GroupExtractionPipeline, PipelineConfig


@pytest.fixture
def pipeline(tmp_path):
    """Create a pipeline with a temporary data directory."""
    return GroupExtractionPipeline(data_dir=str(tmp_path / "extraction_groups"))


class TestPipelineConfig:
    """Tests for PipelineConfig and state management."""

    def test_config_created_on_init(self, pipeline):
        """Config file should be created on first access."""
        cfg = pipeline.config
        assert cfg.created_at != ""
        assert pipeline.config_path.exists()

    def test_config_persists(self, pipeline):
        """Config should persist between load/save cycles."""
        cfg = pipeline.config
        cfg.total_candidates = 42
        pipeline.save_config(cfg)

        # Reload
        pipeline._config = None
        cfg2 = pipeline.load_config()
        assert cfg2.total_candidates == 42

    def test_phase_status_all_pending(self, pipeline):
        """All phases should be pending initially."""
        status = pipeline.config.phase_status()
        assert all(v == "pending" for v in status.values())

    def test_phase_status_after_discovery(self, pipeline):
        """Discovery phase should be marked completed after run."""
        cfg = pipeline.config
        cfg.discovery_completed_at = "2025-01-01T00:00:00"
        pipeline.save_config(cfg)

        status = pipeline.config.phase_status()
        assert status["discovery"] == "completed"
        assert status["fingerprinting"] == "pending"

    def test_get_status(self, pipeline):
        """get_status should return full status dict."""
        status = pipeline.get_status()
        assert "data_dir" in status
        assert "phases" in status
        assert "stats" in status


class TestDiscovery:
    """Tests for Phase 1 discovery."""

    def test_discovery_empty_input(self, pipeline):
        """Empty file list should produce empty manifest."""
        manifest = pipeline.run_discovery([])
        assert manifest["total_scanned"] == 0
        assert manifest["candidates_accepted"] == 0

    def test_discovery_accepts_old_uw_model(self, pipeline):
        """Old UW model (before cutoff) should be accepted."""
        files = [{
            "name": "Deal UW Model vCurrent.xlsb",
            "path": "/deals/Deal UW Model vCurrent.xlsb",
            "size": 5_000_000,
            "modified_date": datetime(2023, 1, 15),
            "deal_name": "Deal",
            "deal_stage": "Active",
        }]
        manifest = pipeline.run_discovery(files)
        assert manifest["candidates_accepted"] == 1

    def test_discovery_rejects_non_uw(self, pipeline):
        """Non-UW model files should be skipped."""
        files = [{
            "name": "Random Report.xlsb",
            "path": "/random.xlsb",
            "size": 1000,
            "modified_date": datetime(2023, 1, 15),
            "deal_name": "Report",
            "deal_stage": "Active",
        }]
        manifest = pipeline.run_discovery(files)
        assert manifest["candidates_accepted"] == 0
        assert manifest["candidates_skipped"] == 1

    def test_discovery_deduplicates_by_size_and_date(self, pipeline):
        """Files with same size and date should be deduplicated."""
        files = [
            {
                "name": "Deal A UW Model vCurrent.xlsb",
                "path": "/path1/Deal A UW Model vCurrent.xlsb",
                "size": 5_000_000,
                "modified_date": datetime(2023, 1, 15),
                "deal_name": "Deal A",
                "content_hash": "abc123",
            },
            {
                "name": "Deal B UW Model vCurrent.xlsb",
                "path": "/path2/Deal B UW Model vCurrent.xlsb",
                "size": 5_000_000,
                "modified_date": datetime(2023, 1, 15),
                "deal_name": "Deal B",
                "content_hash": "abc123",
            },
        ]
        manifest = pipeline.run_discovery(files)
        assert manifest["duplicates_removed"] == 1

    def test_discovery_keeps_different_hashes(self, pipeline):
        """Files with same size+date but different hash should be kept."""
        files = [
            {
                "name": "Deal A UW Model vCurrent.xlsb",
                "path": "/path1/a.xlsb",
                "size": 5_000_000,
                "modified_date": datetime(2023, 1, 15),
                "deal_name": "Deal A",
                "content_hash": "hash_a",
            },
            {
                "name": "Deal B UW Model vCurrent.xlsb",
                "path": "/path2/b.xlsb",
                "size": 5_000_000,
                "modified_date": datetime(2023, 1, 15),
                "deal_name": "Deal B",
                "content_hash": "hash_b",
            },
        ]
        manifest = pipeline.run_discovery(files)
        assert manifest["duplicates_removed"] == 0
        assert manifest["candidates_accepted"] == 2

    def test_discovery_manifest_persisted(self, pipeline):
        """Manifest should be written to disk."""
        files = [{
            "name": "Deal UW Model vCurrent.xlsb",
            "path": "/deals/model.xlsb",
            "size": 5_000_000,
            "modified_date": datetime(2023, 1, 15),
            "deal_name": "Deal",
        }]
        pipeline.run_discovery(files)

        manifest_path = pipeline.data_dir / "discovery_manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["candidates_accepted"] == 1

    def test_discovery_updates_config(self, pipeline):
        """Config should be updated after discovery."""
        files = [{
            "name": "Deal UW Model vCurrent.xlsb",
            "path": "/deals/model.xlsb",
            "size": 5_000_000,
            "modified_date": datetime(2023, 1, 15),
            "deal_name": "Deal",
        }]
        pipeline.run_discovery(files)

        cfg = pipeline.load_config()
        assert cfg.total_candidates == 1
        assert cfg.discovery_completed_at is not None

    def test_discovery_batching_gate(self, pipeline):
        """Files exceeding batch size should trigger batching info."""
        files = [
            {
                "name": f"Deal {i} UW Model vCurrent.xlsb",
                "path": f"/deals/{i}.xlsb",
                "size": 5_000_000 + i,  # Different sizes to avoid dedup
                "modified_date": datetime(2023, 1, i + 1),
                "deal_name": f"Deal {i}",
            }
            for i in range(5)
        ]
        with patch("app.extraction.group_pipeline.settings") as mock_settings:
            mock_settings.GROUP_MAX_BATCH_SIZE = 2
            manifest = pipeline.run_discovery(files)
        assert manifest["batch_info"] is not None
        assert manifest["batch_info"]["batch_count"] > 1

    def test_discovery_multiple_runs_overwrite(self, pipeline):
        """Running discovery again should overwrite manifest."""
        files1 = [{
            "name": "Deal A UW Model vCurrent.xlsb",
            "path": "/a.xlsb",
            "size": 5_000_000,
            "modified_date": datetime(2023, 1, 15),
            "deal_name": "Deal A",
        }]
        pipeline.run_discovery(files1)

        files2 = [
            {
                "name": f"Deal {c} UW Model vCurrent.xlsb",
                "path": f"/{c}.xlsb",
                "size": 5_000_000 + i,
                "modified_date": datetime(2023, 2, i + 1),
                "deal_name": f"Deal {c}",
            }
            for i, c in enumerate(["X", "Y"])
        ]
        manifest = pipeline.run_discovery(files2)
        assert manifest["candidates_accepted"] == 2

    def test_discovery_production_file_rejected(self, pipeline):
        """Current vCurrent file with recent date should be rejected (handled by production)."""
        files = [{
            "name": "Deal UW Model vCurrent.xlsb",
            "path": "/deals/vCurrent.xlsb",
            "size": 5_000_000,
            "modified_date": datetime(2025, 1, 15),
            "deal_name": "Deal",
        }]
        manifest = pipeline.run_discovery(files)
        assert manifest["candidates_accepted"] == 0


class TestDeduplication:
    """Tests for the _deduplicate method."""

    def test_no_duplicates(self, pipeline):
        """Unique files should all be kept."""
        files = [
            {"name": "a.xlsb", "size": 100, "modified_date": "2023-01-01"},
            {"name": "b.xlsb", "size": 200, "modified_date": "2023-01-02"},
        ]
        unique, dupes = pipeline._deduplicate(files)
        assert len(unique) == 2
        assert len(dupes) == 0

    def test_exact_duplicates(self, pipeline):
        """Files with same size+date+hash should be deduplicated."""
        files = [
            {"name": "a.xlsb", "size": 100, "modified_date": "2023-01-01", "content_hash": "h1"},
            {"name": "b.xlsb", "size": 100, "modified_date": "2023-01-01", "content_hash": "h1"},
        ]
        unique, dupes = pipeline._deduplicate(files)
        assert len(unique) == 1
        assert len(dupes) == 1

    def test_same_size_date_different_hash(self, pipeline):
        """Same size+date but different hash should both be kept."""
        files = [
            {"name": "a.xlsb", "size": 100, "modified_date": "2023-01-01", "content_hash": "h1"},
            {"name": "b.xlsb", "size": 100, "modified_date": "2023-01-01", "content_hash": "h2"},
        ]
        unique, dupes = pipeline._deduplicate(files)
        assert len(unique) == 2
        assert len(dupes) == 0

    def test_no_hash_keeps_first(self, pipeline):
        """Without hash, first file with same size+date should be kept."""
        files = [
            {"name": "a.xlsb", "size": 100, "modified_date": "2023-01-01"},
            {"name": "b.xlsb", "size": 100, "modified_date": "2023-01-01"},
        ]
        unique, dupes = pipeline._deduplicate(files)
        # Both kept (no hash to compare)
        assert len(unique) == 2
