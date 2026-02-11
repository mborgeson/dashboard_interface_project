"""
Tests for SharePoint client with mocked responses.

These tests verify SharePoint file discovery, filtering, authentication
error handling, and file download functionality.

Run with: pytest tests/test_extraction/test_sharepoint_integration.py -v
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.extraction.file_filter import FileFilter, FilterResult, SkipReason
from app.extraction.sharepoint import (
    DiscoveryResult,
    SharePointAuthError,
    SharePointClient,
    SharePointFile,
    SkippedFile,
)


class MockSettings:
    """Mock settings for testing."""

    AZURE_TENANT_ID = "test-tenant-id"
    AZURE_CLIENT_ID = "test-client-id"
    AZURE_CLIENT_SECRET = "test-client-secret"
    SHAREPOINT_SITE_URL = "https://test.sharepoint.com/sites/Test"
    SHAREPOINT_DEALS_FOLDER = "Deals"
    FILE_PATTERN = ".*UW Model.*"
    EXCLUDE_PATTERNS = "old,backup,archive"
    FILE_EXTENSIONS = ".xlsb,.xlsx"
    CUTOFF_DATE = "2023-01-01"
    MAX_FILE_SIZE_MB = 100


def create_mock_file_filter() -> FileFilter:
    """Create a FileFilter with mock settings."""
    return FileFilter(MockSettings())


class TestSharePointAuthentication:
    """Test SharePoint authentication handling."""

    @pytest.fixture
    def client(self) -> SharePointClient:
        """Create SharePoint client with mock settings."""
        with patch("app.extraction.sharepoint.settings", MockSettings()):
            return SharePointClient(
                tenant_id=MockSettings.AZURE_TENANT_ID,
                client_id=MockSettings.AZURE_CLIENT_ID,
                client_secret=MockSettings.AZURE_CLIENT_SECRET,
                site_url=MockSettings.SHAREPOINT_SITE_URL,
            )

    @pytest.mark.asyncio
    async def test_authentication_error_handling(
        self, client: SharePointClient
    ) -> None:
        """Verify SharePointAuthError is raised on auth failure."""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials",
        }

        with patch.object(client, "_get_msal_app", return_value=mock_app):
            with pytest.raises(SharePointAuthError) as exc_info:
                await client._get_access_token()

            assert "Invalid client credentials" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_successful_authentication(self, client: SharePointClient) -> None:
        """Verify successful authentication returns token."""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test-token-12345",
            "expires_in": 3600,
        }

        with patch.object(client, "_get_msal_app", return_value=mock_app):
            token = await client._get_access_token()

            assert token == "test-token-12345"
            assert client._access_token == "test-token-12345"
            assert client._token_expires is not None

    @pytest.mark.asyncio
    async def test_token_caching(self, client: SharePointClient) -> None:
        """Verify token is cached and reused."""
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "cached-token",
            "expires_in": 3600,
        }

        with patch.object(client, "_get_msal_app", return_value=mock_app):
            # First call - acquires token
            token1 = await client._get_access_token()

            # Second call - should use cached token
            token2 = await client._get_access_token()

            assert token1 == token2
            # Should only call acquire once
            assert mock_app.acquire_token_for_client.call_count == 1


class TestSharePointFileDiscovery:
    """Test SharePoint file discovery functionality."""

    @pytest.fixture
    def client(self) -> SharePointClient:
        """Create SharePoint client with mock settings."""
        with patch("app.extraction.sharepoint.settings", MockSettings()):
            return SharePointClient(
                tenant_id=MockSettings.AZURE_TENANT_ID,
                client_id=MockSettings.AZURE_CLIENT_ID,
                client_secret=MockSettings.AZURE_CLIENT_SECRET,
                site_url=MockSettings.SHAREPOINT_SITE_URL,
            )

    @pytest.fixture
    def mock_file_filter(self) -> FileFilter:
        """Create mock file filter."""
        return create_mock_file_filter()

    @pytest.mark.asyncio
    async def test_file_discovery_returns_expected_files(
        self, client: SharePointClient
    ) -> None:
        """Verify file discovery finds UW model files."""
        # Mock files with dates after the cutoff
        mock_uw_files = [
            {
                "name": "Property A UW Model vCurrent.xlsb",
                "file": {},
                "size": 5000000,
                "lastModifiedDateTime": "2024-08-01T12:00:00Z",
                "@microsoft.graph.downloadUrl": "https://test.com/download/1",
            },
            {
                "name": "Property B UW Model vCurrent.xlsb",
                "file": {},
                "size": 6000000,
                "lastModifiedDateTime": "2024-09-01T12:00:00Z",
                "@microsoft.graph.downloadUrl": "https://test.com/download/2",
            },
        ]

        # Mock folder structure: Stage -> Deal -> UW Model subfolder
        mock_stage_folders = [{"path": "Deals/1) Initial UW", "name": "1) Initial UW"}]
        mock_deal_folders = {"value": [{"name": "Property A", "folder": {}}]}
        mock_deal_children = {"value": [{"name": "UW Model", "folder": {}}]}
        mock_uw_model_files = {"value": mock_uw_files}

        def mock_request(method: str, endpoint: str) -> dict:
            if "1) Initial UW:/children" in endpoint:
                return mock_deal_folders
            elif "Property A:/children" in endpoint:
                return mock_deal_children
            elif "UW Model:/children" in endpoint:
                return mock_uw_model_files
            return {"value": []}

        with (
            patch.object(client, "_get_drive_id", return_value="test-drive-id"),
            patch.object(
                client, "discover_deal_folders", return_value=mock_stage_folders
            ),
            patch.object(client, "_make_request", side_effect=mock_request),
        ):
            result = await client.find_uw_models(use_filter=False)

            assert isinstance(result, DiscoveryResult)
            assert len(result.files) == 2
            assert result.files[0].name == "Property A UW Model vCurrent.xlsb"

    @pytest.mark.asyncio
    async def test_file_filtering_applied(
        self, client: SharePointClient, mock_file_filter: FileFilter
    ) -> None:
        """Verify exclude patterns filter out unwanted files."""
        client.set_file_filter(mock_file_filter)

        mock_files = [
            {
                "name": "Property A UW Model vCurrent.xlsb",
                "file": {},
                "size": 5000000,
                "lastModifiedDateTime": "2024-06-01T12:00:00Z",
            },
            {
                "name": "old_Property B UW Model.xlsb",  # Should be excluded
                "file": {},
                "size": 5000000,
                "lastModifiedDateTime": "2024-06-01T12:00:00Z",
            },
            {
                "name": "Property C UW Model backup.xlsb",  # Should be excluded
                "file": {},
                "size": 5000000,
                "lastModifiedDateTime": "2024-06-01T12:00:00Z",
            },
        ]

        # Mock folder structure: Stage -> Deal -> UW Model subfolder
        mock_stage_folders = [{"path": "Deals/Test", "name": "Test"}]
        mock_deal_folders = {"value": [{"name": "Test Deal", "folder": {}}]}
        mock_deal_children = {"value": [{"name": "UW Model", "folder": {}}]}
        mock_uw_model_files = {"value": mock_files}

        def mock_request(method: str, endpoint: str) -> dict:
            if "Deals/Test:/children" in endpoint:
                return mock_deal_folders
            elif "Test Deal:/children" in endpoint:
                return mock_deal_children
            elif "UW Model:/children" in endpoint:
                return mock_uw_model_files
            return {"value": []}

        with (
            patch.object(client, "_get_drive_id", return_value="test-drive-id"),
            patch.object(
                client, "discover_deal_folders", return_value=mock_stage_folders
            ),
            patch.object(client, "_make_request", side_effect=mock_request),
        ):
            result = await client.find_uw_models(use_filter=True)

            # Only non-excluded files should be in result
            assert len(result.files) == 1
            assert result.files[0].name == "Property A UW Model vCurrent.xlsb"

            # Excluded files should be in skipped
            assert len(result.skipped) >= 2

    @pytest.mark.asyncio
    async def test_cutoff_date_filtering(
        self, client: SharePointClient, mock_file_filter: FileFilter
    ) -> None:
        """Verify old files are skipped based on cutoff."""
        client.set_file_filter(mock_file_filter)

        mock_files = [
            {
                "name": "New Property UW Model.xlsb",
                "file": {},
                "size": 5000000,
                "lastModifiedDateTime": "2024-06-01T12:00:00Z",  # After cutoff
            },
            {
                "name": "Old Property UW Model.xlsb",
                "file": {},
                "size": 5000000,
                "lastModifiedDateTime": "2022-01-01T12:00:00Z",  # Before cutoff
            },
        ]

        # Mock folder structure: Stage -> Deal -> UW Model subfolder
        mock_stage_folders = [{"path": "Deals/Test", "name": "Test"}]
        mock_deal_folders = {"value": [{"name": "Test Deal", "folder": {}}]}
        mock_deal_children = {"value": [{"name": "UW Model", "folder": {}}]}
        mock_uw_model_files = {"value": mock_files}

        def mock_request(method: str, endpoint: str) -> dict:
            if "Deals/Test:/children" in endpoint:
                return mock_deal_folders
            elif "Test Deal:/children" in endpoint:
                return mock_deal_children
            elif "UW Model:/children" in endpoint:
                return mock_uw_model_files
            return {"value": []}

        with (
            patch.object(client, "_get_drive_id", return_value="test-drive-id"),
            patch.object(
                client, "discover_deal_folders", return_value=mock_stage_folders
            ),
            patch.object(client, "_make_request", side_effect=mock_request),
        ):
            result = await client.find_uw_models(use_filter=True)

            # Only new file should be accepted
            assert len(result.files) == 1
            assert result.files[0].name == "New Property UW Model.xlsb"

    @pytest.mark.asyncio
    async def test_max_file_size_filtering(
        self, client: SharePointClient, mock_file_filter: FileFilter
    ) -> None:
        """Verify oversized files are skipped."""
        client.set_file_filter(mock_file_filter)

        mock_files = [
            {
                "name": "Normal Property UW Model.xlsb",
                "file": {},
                "size": 50 * 1024 * 1024,  # 50MB - under limit
                "lastModifiedDateTime": "2024-06-01T12:00:00Z",
            },
            {
                "name": "Huge Property UW Model.xlsb",
                "file": {},
                "size": 150 * 1024 * 1024,  # 150MB - over limit
                "lastModifiedDateTime": "2024-06-01T12:00:00Z",
            },
        ]

        # Mock folder structure: Stage -> Deal -> UW Model subfolder
        mock_stage_folders = [{"path": "Deals/Test", "name": "Test"}]
        mock_deal_folders = {"value": [{"name": "Test Deal", "folder": {}}]}
        mock_deal_children = {"value": [{"name": "UW Model", "folder": {}}]}
        mock_uw_model_files = {"value": mock_files}

        def mock_request(method: str, endpoint: str) -> dict:
            if "Deals/Test:/children" in endpoint:
                return mock_deal_folders
            elif "Test Deal:/children" in endpoint:
                return mock_deal_children
            elif "UW Model:/children" in endpoint:
                return mock_uw_model_files
            return {"value": []}

        with (
            patch.object(client, "_get_drive_id", return_value="test-drive-id"),
            patch.object(
                client, "discover_deal_folders", return_value=mock_stage_folders
            ),
            patch.object(client, "_make_request", side_effect=mock_request),
        ):
            result = await client.find_uw_models(use_filter=True)

            # Only normal-sized file should be accepted
            assert len(result.files) == 1
            assert result.files[0].name == "Normal Property UW Model.xlsb"


class TestFileFilter:
    """Test FileFilter functionality."""

    @pytest.fixture
    def file_filter(self) -> FileFilter:
        """Create file filter with mock settings."""
        return create_mock_file_filter()

    def test_valid_file_accepted(self, file_filter: FileFilter) -> None:
        """Verify valid files are accepted."""
        result = file_filter.should_process(
            filename="Property UW Model vCurrent.xlsb",
            size_bytes=10 * 1024 * 1024,
            modified_date=datetime(2024, 6, 1),
        )

        assert result.should_process is True
        assert result.skip_reason is None

    def test_pattern_mismatch_rejected(self, file_filter: FileFilter) -> None:
        """Verify files not matching pattern are rejected."""
        result = file_filter.should_process(
            filename="random_spreadsheet.xlsb",
            size_bytes=10 * 1024 * 1024,
            modified_date=datetime(2024, 6, 1),
        )

        assert result.should_process is False
        assert result.skip_reason == SkipReason.PATTERN_MISMATCH

    def test_excluded_pattern_rejected(self, file_filter: FileFilter) -> None:
        """Verify files matching exclude patterns are rejected."""
        result = file_filter.should_process(
            filename="old_Property UW Model.xlsb",
            size_bytes=10 * 1024 * 1024,
            modified_date=datetime(2024, 6, 1),
        )

        assert result.should_process is False
        assert result.skip_reason == SkipReason.EXCLUDED_PATTERN

    def test_old_file_rejected(self, file_filter: FileFilter) -> None:
        """Verify files before cutoff date are rejected."""
        result = file_filter.should_process(
            filename="Property UW Model.xlsb",
            size_bytes=10 * 1024 * 1024,
            modified_date=datetime(2022, 1, 1),  # Before 2023-01-01 cutoff
        )

        assert result.should_process is False
        assert result.skip_reason == SkipReason.TOO_OLD

    def test_large_file_rejected(self, file_filter: FileFilter) -> None:
        """Verify files exceeding max size are rejected."""
        result = file_filter.should_process(
            filename="Property UW Model.xlsb",
            size_bytes=150 * 1024 * 1024,  # 150MB > 100MB limit
            modified_date=datetime(2024, 6, 1),
        )

        assert result.should_process is False
        assert result.skip_reason == SkipReason.TOO_LARGE

    def test_invalid_extension_rejected(self, file_filter: FileFilter) -> None:
        """Verify files with invalid extensions are rejected."""
        result = file_filter.should_process(
            filename="Property UW Model.docx",  # Wrong extension
            size_bytes=10 * 1024 * 1024,
            modified_date=datetime(2024, 6, 1),
        )

        assert result.should_process is False
        assert result.skip_reason == SkipReason.INVALID_EXTENSION

    def test_filter_config_retrieval(self, file_filter: FileFilter) -> None:
        """Verify filter config can be retrieved."""
        config = file_filter.get_config()

        assert "file_pattern" in config
        assert "exclude_patterns" in config
        assert "valid_extensions" in config
        assert "cutoff_date" in config
        assert "max_file_size_mb" in config


class TestSharePointFileDownload:
    """Test SharePoint file download functionality."""

    @pytest.fixture
    def client(self) -> SharePointClient:
        """Create SharePoint client with mock settings."""
        with patch("app.extraction.sharepoint.settings", MockSettings()):
            return SharePointClient(
                tenant_id=MockSettings.AZURE_TENANT_ID,
                client_id=MockSettings.AZURE_CLIENT_ID,
                client_secret=MockSettings.AZURE_CLIENT_SECRET,
                site_url=MockSettings.SHAREPOINT_SITE_URL,
            )

    @pytest.mark.asyncio
    async def test_file_download_success(self, client: SharePointClient) -> None:
        """Verify successful file download."""
        test_file = SharePointFile(
            name="Test UW Model.xlsb",
            path="Deals/Test/Test UW Model.xlsb",
            download_url="https://test.com/download/123",
            size=1000000,
            modified_date=datetime(2024, 6, 1),
            deal_name="Test Deal",
        )

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=b"test file content")

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(return_value=None),
            )
        )
        mock_session.closed = False

        with patch(
            "aiohttp.ClientSession",
            return_value=mock_session,
        ):
            content = await client.download_file(test_file)

            assert content == b"test file content"

    @pytest.mark.asyncio
    async def test_file_download_without_url(self, client: SharePointClient) -> None:
        """Verify download URL is fetched if not provided."""
        test_file = SharePointFile(
            name="Test UW Model.xlsb",
            path="Deals/Test/Test UW Model.xlsb",
            download_url="",  # No URL provided
            size=1000000,
            modified_date=datetime(2024, 6, 1),
            deal_name="Test Deal",
        )

        with (
            patch.object(client, "_get_drive_id", return_value="test-drive-id"),
            patch.object(
                client,
                "_make_request",
                return_value={
                    "@microsoft.graph.downloadUrl": "https://new-url.com/download",
                },
            ),
        ):
            # This should fetch the download URL first
            # Then fail because we haven't mocked the actual download
            with pytest.raises(Exception):  # noqa: B017
                await client.download_file(test_file)

            # URL should have been updated
            assert test_file.download_url == "https://new-url.com/download"


class TestDiscoveryResult:
    """Test DiscoveryResult dataclass."""

    def test_empty_discovery_result(self) -> None:
        """Verify empty DiscoveryResult initialization."""
        result = DiscoveryResult()

        assert result.files == []
        assert result.skipped == []
        assert result.total_scanned == 0
        assert result.folders_scanned == 0

    def test_discovery_result_with_data(self) -> None:
        """Verify DiscoveryResult with data."""
        files = [
            SharePointFile(
                name="Test.xlsb",
                path="/path/Test.xlsb",
                download_url="https://test.com",
                size=1000,
                modified_date=datetime.now(),
                deal_name="Test",
            )
        ]
        skipped = [
            SkippedFile(
                name="Old.xlsb",
                path="/path/Old.xlsb",
                size=500,
                modified_date=datetime.now() - timedelta(days=365),
                skip_reason="too_old",
                deal_name="Old Deal",
            )
        ]

        result = DiscoveryResult(
            files=files,
            skipped=skipped,
            total_scanned=10,
            folders_scanned=5,
        )

        assert len(result.files) == 1
        assert len(result.skipped) == 1
        assert result.total_scanned == 10
        assert result.folders_scanned == 5


class TestDealStageInference:
    """Test deal stage inference from folder paths."""

    @pytest.fixture
    def client(self) -> SharePointClient:
        """Create SharePoint client."""
        with patch("app.extraction.sharepoint.settings", MockSettings()):
            return SharePointClient(
                tenant_id=MockSettings.AZURE_TENANT_ID,
                client_id=MockSettings.AZURE_CLIENT_ID,
                client_secret=MockSettings.AZURE_CLIENT_SECRET,
                site_url=MockSettings.SHAREPOINT_SITE_URL,
            )

    def test_closed_deal_inference(self, client: SharePointClient) -> None:
        """Verify closed deals are identified."""
        assert client._infer_deal_stage("Deals/Closed/Property A") == "closed"
        assert client._infer_deal_stage("Deals/Acquired/Property B") == "closed"

    def test_pipeline_deal_inference(self, client: SharePointClient) -> None:
        """Verify pipeline deals are identified."""
        assert client._infer_deal_stage("Deals/Pipeline/Property A") == "pipeline"
        assert client._infer_deal_stage("Deals/Active/Property B") == "pipeline"

    def test_dead_deal_inference(self, client: SharePointClient) -> None:
        """Verify dead deals are identified."""
        assert client._infer_deal_stage("Deals/Dead/Property A") == "dead"
        assert client._infer_deal_stage("Deals/Passed/Property B") == "dead"

    def test_loi_deal_inference(self, client: SharePointClient) -> None:
        """Verify LOI deals are identified."""
        assert client._infer_deal_stage("Deals/LOI/Property A") == "loi"

    def test_due_diligence_deal_inference(self, client: SharePointClient) -> None:
        """Verify due diligence deals are identified."""
        assert (
            client._infer_deal_stage("Deals/Due Diligence/Property A")
            == "due_diligence"
        )
        assert client._infer_deal_stage("Deals/DD/Property B") == "due_diligence"

    def test_unknown_stage_inference(self, client: SharePointClient) -> None:
        """Verify unknown stages return None."""
        assert client._infer_deal_stage("Deals/Other/Property A") is None
        assert client._infer_deal_stage("Random/Path") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
