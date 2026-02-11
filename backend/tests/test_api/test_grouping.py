"""
Tests for grouping API endpoints.

Tests cover:
- GET /extraction/grouping/status
- POST /extraction/grouping/discover
- Phase dependency enforcement (fingerprint requires discovery, etc.)
- GET /extraction/grouping/groups
- GET /extraction/grouping/groups/{name}

Run with: pytest tests/test_api/test_grouping.py -v
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.extraction.grouping import _get_pipeline, router


@pytest.fixture
def groups_dir(tmp_path):
    """Shared temp directory for pipeline data."""
    return str(tmp_path / "groups")


@pytest.fixture
def app(groups_dir):
    """Create FastAPI app with grouping router and tmp pipeline."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/extraction")

    # Override pipeline to use temp directory
    _dir = groups_dir

    def _test_pipeline():
        from app.extraction.group_pipeline import GroupExtractionPipeline
        return GroupExtractionPipeline(data_dir=_dir)

    test_app.dependency_overrides[_get_pipeline] = _test_pipeline

    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def pipeline(groups_dir):
    """Direct pipeline instance sharing the same directory as app."""
    from app.extraction.group_pipeline import GroupExtractionPipeline
    return GroupExtractionPipeline(data_dir=groups_dir)


class TestPipelineStatus:
    """Tests for GET /extraction/grouping/status."""

    def test_status_initial(self, client):
        """Initial status should show all phases pending."""
        response = client.get("/extraction/grouping/status")
        assert response.status_code == 200
        data = response.json()
        assert "phases" in data
        assert data["phases"]["discovery"] == "pending"

    def test_status_after_discovery(self, client, pipeline):
        """Status should reflect completed discovery."""
        cfg = pipeline.config
        cfg.discovery_completed_at = "2025-01-01T00:00:00"
        cfg.total_candidates = 5
        pipeline.save_config(cfg)

        response = client.get("/extraction/grouping/status")
        assert response.status_code == 200
        data = response.json()
        assert data["phases"]["discovery"] == "completed"
        assert data["stats"]["total_candidates"] == 5


class TestDiscoveryEndpoint:
    """Tests for POST /extraction/grouping/discover."""

    def test_discover_empty(self, client):
        """Discovery with no files should succeed."""
        response = client.post("/extraction/grouping/discover", json=[])
        assert response.status_code == 200
        data = response.json()
        assert data["total_scanned"] == 0
        assert data["candidates_accepted"] == 0

    def test_discover_with_files(self, client):
        """Discovery with valid files should accept candidates."""
        files = [{
            "name": "Deal UW Model v2.xlsb",
            "path": "/test/model.xlsb",
            "size": 5000000,
            "modified_date": "2023-01-15T00:00:00",
            "deal_name": "Deal",
            "deal_stage": "Active",
        }]
        response = client.post("/extraction/grouping/discover", json=files)
        assert response.status_code == 200
        data = response.json()
        assert data["candidates_accepted"] == 1


class TestManifestEndpoint:
    """Tests for GET /extraction/grouping/manifest."""

    def test_manifest_before_discovery(self, client):
        """Manifest should return 404 before discovery."""
        response = client.get("/extraction/grouping/manifest")
        assert response.status_code == 404

    def test_manifest_after_discovery(self, client):
        """Manifest should return data after discovery."""
        # Run discovery first
        client.post("/extraction/grouping/discover", json=[])
        response = client.get("/extraction/grouping/manifest")
        assert response.status_code == 200


class TestFingerprintEndpoint:
    """Tests for POST /extraction/grouping/fingerprint."""

    def test_fingerprint_requires_discovery_or_paths(self, client):
        """Fingerprint should require discovery or explicit paths."""
        response = client.post("/extraction/grouping/fingerprint")
        assert response.status_code == 400
        assert "Discovery has not been run" in response.json()["detail"]


class TestGroupsEndpoint:
    """Tests for GET /extraction/grouping/groups."""

    def test_groups_before_fingerprinting(self, client):
        """Groups should return 404 before fingerprinting."""
        response = client.get("/extraction/grouping/groups")
        assert response.status_code == 404

    def test_groups_after_setup(self, client, pipeline):
        """Groups should return data after setup."""
        pipeline.data_dir.mkdir(parents=True, exist_ok=True)
        (pipeline.data_dir / "groups.json").write_text(json.dumps({
            "groups": [{
                "group_name": "test_group",
                "files": [{"name": "f1.xlsb"}, {"name": "f2.xlsb"}],
                "structural_overlap": 0.95,
                "era": "2020-2023",
                "sub_variants": [],
            }],
            "ungrouped": [],
            "empty_templates": [],
            "summary": {"total_groups": 1, "total_ungrouped": 0, "total_empty_templates": 0},
        }))

        response = client.get("/extraction/grouping/groups")
        assert response.status_code == 200
        data = response.json()
        assert data["total_groups"] == 1
        assert data["groups"][0]["group_name"] == "test_group"


class TestGroupDetailEndpoint:
    """Tests for GET /extraction/grouping/groups/{name}."""

    def test_group_not_found(self, client, pipeline):
        """Non-existent group should return 404."""
        pipeline.data_dir.mkdir(parents=True, exist_ok=True)
        (pipeline.data_dir / "groups.json").write_text(json.dumps({
            "groups": [],
            "summary": {},
        }))

        response = client.get("/extraction/grouping/groups/nonexistent")
        assert response.status_code == 404

    def test_group_found(self, client, pipeline):
        """Existing group should return detail."""
        pipeline.data_dir.mkdir(parents=True, exist_ok=True)
        (pipeline.data_dir / "groups.json").write_text(json.dumps({
            "groups": [{
                "group_name": "test_group",
                "files": [{"name": "f1.xlsb"}],
                "structural_overlap": 0.99,
                "era": "2024+",
                "sub_variants": [],
                "variances": {"uniform": True},
            }],
            "summary": {},
        }))

        response = client.get("/extraction/grouping/groups/test_group")
        assert response.status_code == 200
        data = response.json()
        assert data["group_name"] == "test_group"
        assert data["structural_overlap"] == 0.99


class TestReferenceMappingEndpoint:
    """Tests for POST /extraction/grouping/reference-map."""

    def test_reference_map_requires_grouping(self, client):
        """Reference mapping should require grouping to be completed."""
        response = client.post("/extraction/grouping/reference-map")
        assert response.status_code == 400
        assert "Grouping has not been run" in response.json()["detail"]
