"""
Tests for SharePoint download retry logic.

Covers:
- Transient error classification (429, 5xx vs 4xx)
- Exponential backoff timing with jitter
- Retry-After header parsing (integer and HTTP-date)
- URL refresh on 403 (expired pre-auth URL)
- Max retries exhaustion
- Non-transient error immediate failure
- Network error handling
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from app.extraction.sharepoint import SharePointClient, SharePointFile
from app.services.sharepoint_download import (
    DownloadError,
    DownloadRetriesExhausted,
    _calculate_backoff,
    _is_transient_error,
    _parse_retry_after,
    _refresh_download_url,
    download_file_with_retry,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sp_file() -> SharePointFile:
    """Create a test SharePointFile."""
    return SharePointFile(
        name="Test UW Model.xlsb",
        path="Deals/Test Deal/UW Model/Test UW Model.xlsb",
        download_url="https://test.sharepoint.com/download/pre-auth-token-123",
        size=5_000_000,
        modified_date=datetime(2024, 8, 1, tzinfo=UTC),
        deal_name="Test Deal",
    )


@pytest.fixture
def mock_sp_client() -> SharePointClient:
    """Create a mock SharePoint client."""
    client = MagicMock(spec=SharePointClient)
    client._get_drive_id = AsyncMock(return_value="test-drive-id")
    client._make_request = AsyncMock(
        return_value={
            "@microsoft.graph.downloadUrl": "https://test.sharepoint.com/download/fresh-url",
        }
    )
    return client


def _make_mock_response(
    status: int,
    content: bytes = b"",
    headers: dict[str, str] | None = None,
    text: str = "",
) -> AsyncMock:
    """Create a mock aiohttp response as an async context manager."""
    response = AsyncMock()
    response.status = status
    response.read = AsyncMock(return_value=content)
    response.text = AsyncMock(return_value=text)
    response.headers = headers or {}
    return response


def _make_mock_session(responses: list[AsyncMock]) -> AsyncMock:
    """Create a mock aiohttp session that returns responses in order."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.closed = False

    call_count = 0

    def get_side_effect(url: str, **kwargs: Any) -> AsyncMock:
        nonlocal call_count
        idx = min(call_count, len(responses) - 1)
        resp = responses[idx]
        call_count += 1
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=resp)
        ctx.__aexit__ = AsyncMock(return_value=None)
        return ctx

    session.get = MagicMock(side_effect=get_side_effect)
    session.close = AsyncMock()
    return session


# =============================================================================
# _is_transient_error Tests
# =============================================================================


class TestIsTransientError:
    """Tests for transient error classification."""

    def test_429_is_transient(self) -> None:
        """429 Too Many Requests should be transient."""
        assert _is_transient_error(429) is True

    def test_500_is_transient(self) -> None:
        """500 Internal Server Error should be transient."""
        assert _is_transient_error(500) is True

    def test_502_is_transient(self) -> None:
        """502 Bad Gateway should be transient."""
        assert _is_transient_error(502) is True

    def test_503_is_transient(self) -> None:
        """503 Service Unavailable should be transient."""
        assert _is_transient_error(503) is True

    def test_504_is_transient(self) -> None:
        """504 Gateway Timeout should be transient."""
        assert _is_transient_error(504) is True

    def test_404_not_transient(self) -> None:
        """404 Not Found should NOT be transient."""
        assert _is_transient_error(404) is False

    def test_400_not_transient(self) -> None:
        """400 Bad Request should NOT be transient."""
        assert _is_transient_error(400) is False

    def test_401_not_transient(self) -> None:
        """401 Unauthorized should NOT be transient."""
        assert _is_transient_error(401) is False

    def test_403_not_transient(self) -> None:
        """403 Forbidden should NOT be transient (handled separately for URL refresh)."""
        assert _is_transient_error(403) is False

    def test_200_not_transient(self) -> None:
        """200 OK should NOT be transient."""
        assert _is_transient_error(200) is False

    def test_408_not_transient(self) -> None:
        """408 Request Timeout is a client error, not transient."""
        assert _is_transient_error(408) is False


# =============================================================================
# _parse_retry_after Tests
# =============================================================================


class TestParseRetryAfter:
    """Tests for Retry-After header parsing."""

    def test_integer_seconds(self) -> None:
        """Parse integer seconds format."""
        assert _parse_retry_after("120") == 120.0

    def test_zero_seconds(self) -> None:
        """Parse zero seconds."""
        assert _parse_retry_after("0") == 0.0

    def test_negative_seconds_clamps_to_zero(self) -> None:
        """Negative seconds should clamp to 0."""
        assert _parse_retry_after("-5") == 0.0

    def test_http_date_format(self) -> None:
        """Parse HTTP-date format (future date)."""
        future = datetime.now(UTC) + timedelta(seconds=60)
        http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
        result = _parse_retry_after(http_date)
        assert result is not None
        # Should be roughly 60 seconds, allow tolerance
        assert 50 <= result <= 70

    def test_http_date_in_past(self) -> None:
        """HTTP-date in the past should return 0."""
        past = datetime.now(UTC) - timedelta(hours=1)
        http_date = past.strftime("%a, %d %b %Y %H:%M:%S GMT")
        result = _parse_retry_after(http_date)
        assert result == 0.0

    def test_none_returns_none(self) -> None:
        """None header value returns None."""
        assert _parse_retry_after(None) is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        assert _parse_retry_after("") is None

    def test_garbage_returns_none(self) -> None:
        """Unparseable string returns None."""
        assert _parse_retry_after("not-a-number-or-date") is None


# =============================================================================
# _calculate_backoff Tests
# =============================================================================


class TestCalculateBackoff:
    """Tests for exponential backoff calculation."""

    def test_first_attempt_uses_base_delay(self) -> None:
        """Attempt 0 should use approximately base_delay."""
        delay = _calculate_backoff(0, base_delay=1.0)
        # base_delay * 2^0 = 1.0, plus jitter (0 to 0.5)
        assert 1.0 <= delay <= 1.5

    def test_exponential_increase(self) -> None:
        """Delay should double with each attempt (ignoring jitter)."""
        # Seed random for reproducibility in structure tests
        delays = []
        for attempt in range(4):
            # Use many samples to check the base is doubling
            delay = _calculate_backoff(attempt, base_delay=1.0)
            delays.append(delay)

        # Each attempt's minimum should be >= 2x previous base
        # attempt 0: base=1.0, attempt 1: base=2.0, attempt 2: base=4.0
        assert delays[1] >= 2.0  # 2^1 = 2.0
        assert delays[2] >= 4.0  # 2^2 = 4.0
        assert delays[3] >= 8.0  # 2^3 = 8.0

    def test_retry_after_overrides_backoff(self) -> None:
        """Explicit retry_after should override exponential backoff."""
        delay = _calculate_backoff(5, base_delay=1.0, retry_after=30.0)
        assert delay == 30.0

    def test_retry_after_zero(self) -> None:
        """retry_after of 0 should return 0 (immediate retry)."""
        delay = _calculate_backoff(5, base_delay=1.0, retry_after=0.0)
        assert delay == 0.0

    def test_jitter_adds_randomness(self) -> None:
        """Multiple calls should produce different values (jitter)."""
        delays = {_calculate_backoff(2, base_delay=1.0) for _ in range(20)}
        # With jitter, we should get multiple distinct values
        assert len(delays) > 1


# =============================================================================
# _refresh_download_url Tests
# =============================================================================


class TestRefreshDownloadUrl:
    """Tests for download URL refresh via Graph API."""

    @pytest.mark.asyncio
    async def test_successful_refresh(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """URL refresh should update the file's download_url."""
        old_url = sp_file.download_url
        new_url = await _refresh_download_url(mock_sp_client, sp_file)

        assert new_url == "https://test.sharepoint.com/download/fresh-url"
        assert sp_file.download_url == new_url
        assert sp_file.download_url != old_url

    @pytest.mark.asyncio
    async def test_refresh_no_url_returned(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Raise DownloadError if Graph API returns no download URL."""
        mock_sp_client._make_request = AsyncMock(return_value={})

        with pytest.raises(DownloadError) as exc_info:
            await _refresh_download_url(mock_sp_client, sp_file)

        assert "No download URL returned" in str(exc_info.value)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_refresh_api_error(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Raise DownloadError on Graph API failure."""
        mock_sp_client._make_request = AsyncMock(
            side_effect=Exception("Graph API unavailable")
        )

        with pytest.raises(DownloadError) as exc_info:
            await _refresh_download_url(mock_sp_client, sp_file)

        assert "Failed to refresh download URL" in str(exc_info.value)


# =============================================================================
# download_file_with_retry Tests
# =============================================================================


class TestDownloadFileWithRetry:
    """Tests for the main download-with-retry function."""

    @pytest.mark.asyncio
    async def test_successful_download_no_retry(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Successful download on first attempt."""
        content = b"excel file content here"
        session = _make_mock_session([_make_mock_response(200, content=content)])

        result = await download_file_with_retry(
            mock_sp_client, sp_file, session=session, max_retries=3
        )

        assert result == content
        assert session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_503(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should retry on 503 Service Unavailable."""
        content = b"file content"
        session = _make_mock_session(
            [
                _make_mock_response(503),
                _make_mock_response(200, content=content),
            ]
        )

        with patch(
            "app.services.sharepoint_download.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=0.01,
            )

        assert result == content
        assert session.get.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_404(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should fail immediately on 404 Not Found."""
        session = _make_mock_session(
            [
                _make_mock_response(404, text="Not Found"),
            ]
        )

        with pytest.raises(DownloadError) as exc_info:
            await download_file_with_retry(
                mock_sp_client, sp_file, session=session, max_retries=3
            )

        assert exc_info.value.status_code == 404
        assert session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_400(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should fail immediately on 400 Bad Request."""
        session = _make_mock_session(
            [
                _make_mock_response(400, text="Bad Request"),
            ]
        )

        with pytest.raises(DownloadError) as exc_info:
            await download_file_with_retry(
                mock_sp_client, sp_file, session=session, max_retries=3
            )

        assert exc_info.value.status_code == 400
        assert session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_url_refresh_on_403(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should refresh URL on 403 and retry with fresh URL."""
        content = b"refreshed content"
        session = _make_mock_session(
            [
                _make_mock_response(403),
                _make_mock_response(200, content=content),
            ]
        )

        result = await download_file_with_retry(
            mock_sp_client, sp_file, session=session, max_retries=3
        )

        assert result == content
        # Verify URL was refreshed
        mock_sp_client._make_request.assert_called_once()
        assert sp_file.download_url == "https://test.sharepoint.com/download/fresh-url"

    @pytest.mark.asyncio
    async def test_retry_after_header_429(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should use Retry-After header value on 429."""
        content = b"rate limited then success"
        session = _make_mock_session(
            [
                _make_mock_response(429, headers={"Retry-After": "5"}),
                _make_mock_response(200, content=content),
            ]
        )

        sleep_mock = AsyncMock()
        with patch("app.services.sharepoint_download.asyncio.sleep", sleep_mock):
            result = await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=1.0,
            )

        assert result == content
        # Should have used Retry-After value of 5 seconds
        sleep_mock.assert_called_once()
        actual_delay = sleep_mock.call_args[0][0]
        assert actual_delay == 5.0

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should raise DownloadRetriesExhausted after max retries."""
        session = _make_mock_session(
            [
                _make_mock_response(503),
                _make_mock_response(503),
                _make_mock_response(503),
                _make_mock_response(503),  # 4th attempt = 3 retries + initial
            ]
        )

        with (
            patch(
                "app.services.sharepoint_download.asyncio.sleep", new_callable=AsyncMock
            ),
            pytest.raises(DownloadRetriesExhausted) as exc_info,
        ):
            await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=0.01,
            )

        assert exc_info.value.attempts == 4
        assert exc_info.value.last_status == 503

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Verify exponential backoff delays increase between retries."""
        session = _make_mock_session(
            [
                _make_mock_response(500),
                _make_mock_response(500),
                _make_mock_response(500),
                _make_mock_response(200, content=b"ok"),
            ]
        )

        sleep_mock = AsyncMock()
        with patch("app.services.sharepoint_download.asyncio.sleep", sleep_mock):
            await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=1.0,
            )

        # Should have slept 3 times (before attempts 1, 2, 3)
        assert sleep_mock.call_count == 3
        delays = [call.args[0] for call in sleep_mock.call_args_list]

        # Each delay should be >= the base for that attempt (exponential)
        assert delays[0] >= 1.0  # 1.0 * 2^0
        assert delays[1] >= 2.0  # 1.0 * 2^1
        assert delays[2] >= 4.0  # 1.0 * 2^2

    @pytest.mark.asyncio
    async def test_no_download_url_raises_value_error(
        self, mock_sp_client: SharePointClient
    ) -> None:
        """Should raise ValueError if file has no download URL."""
        file_no_url = SharePointFile(
            name="No URL.xlsb",
            path="path/to/file.xlsb",
            download_url="",
            size=1000,
            modified_date=datetime(2024, 1, 1, tzinfo=UTC),
            deal_name="Test",
        )

        with pytest.raises(ValueError, match="No download URL"):
            await download_file_with_retry(mock_sp_client, file_no_url)

    @pytest.mark.asyncio
    async def test_network_error_retries(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should retry on network-level errors (DNS, connection reset)."""
        content = b"success after network error"
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        session.close = AsyncMock()

        call_count = 0

        def get_side_effect(url: str, **kwargs: Any) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call raises network error
                ctx = AsyncMock()
                ctx.__aenter__ = AsyncMock(
                    side_effect=aiohttp.ClientConnectionError("Connection reset")
                )
                ctx.__aexit__ = AsyncMock(return_value=None)
                return ctx
            # Second call succeeds
            resp = _make_mock_response(200, content=content)
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=resp)
            ctx.__aexit__ = AsyncMock(return_value=None)
            return ctx

        session.get = MagicMock(side_effect=get_side_effect)

        with patch(
            "app.services.sharepoint_download.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=0.01,
            )

        assert result == content

    @pytest.mark.asyncio
    async def test_creates_own_session_when_none_provided(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should create and close its own session when none provided."""
        content = b"content with own session"

        mock_resp = _make_mock_response(200, content=content)
        mock_session = _make_mock_session([mock_resp])

        with patch(
            "app.services.sharepoint_download.aiohttp.ClientSession",
            return_value=mock_session,
        ):
            result = await download_file_with_retry(
                mock_sp_client, sp_file, max_retries=1, backoff_base=0.01
            )

        assert result == content
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_403_exhausted_retries(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """403s should exhaust retries if URL keeps expiring."""
        session = _make_mock_session(
            [
                _make_mock_response(403),
                _make_mock_response(403),
            ]
        )

        with pytest.raises(DownloadRetriesExhausted) as exc_info:
            await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=1,
                backoff_base=0.01,
            )

        assert exc_info.value.last_status == 403

    @pytest.mark.asyncio
    async def test_mixed_errors_then_success(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should handle different error types across retries."""
        content = b"finally success"
        session = _make_mock_session(
            [
                _make_mock_response(503),  # Attempt 0: server error
                _make_mock_response(
                    429, headers={"Retry-After": "1"}
                ),  # Attempt 1: rate limit
                _make_mock_response(200, content=content),  # Attempt 2: success
            ]
        )

        with patch(
            "app.services.sharepoint_download.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=0.01,
            )

        assert result == content

    @pytest.mark.asyncio
    async def test_retry_after_http_date_format(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """Should parse Retry-After in HTTP-date format."""
        content = b"success"
        future = datetime.now(UTC) + timedelta(seconds=2)
        http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")

        session = _make_mock_session(
            [
                _make_mock_response(429, headers={"Retry-After": http_date}),
                _make_mock_response(200, content=content),
            ]
        )

        sleep_mock = AsyncMock()
        with patch("app.services.sharepoint_download.asyncio.sleep", sleep_mock):
            result = await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=1.0,
            )

        assert result == content
        sleep_mock.assert_called_once()
        # Delay should be roughly 2 seconds (allow tolerance)
        actual_delay = sleep_mock.call_args[0][0]
        assert 0 <= actual_delay <= 5

    @pytest.mark.asyncio
    async def test_429_without_retry_after_uses_backoff(
        self, mock_sp_client: SharePointClient, sp_file: SharePointFile
    ) -> None:
        """429 without Retry-After header should use exponential backoff."""
        content = b"success"
        session = _make_mock_session(
            [
                _make_mock_response(429),  # No Retry-After header
                _make_mock_response(200, content=content),
            ]
        )

        sleep_mock = AsyncMock()
        with patch("app.services.sharepoint_download.asyncio.sleep", sleep_mock):
            result = await download_file_with_retry(
                mock_sp_client,
                sp_file,
                session=session,
                max_retries=3,
                backoff_base=2.0,
            )

        assert result == content
        sleep_mock.assert_called_once()
        # Should use backoff: 2.0 * 2^0 + jitter = 2.0 to 3.0
        actual_delay = sleep_mock.call_args[0][0]
        assert 2.0 <= actual_delay <= 3.0


# =============================================================================
# DownloadError / DownloadRetriesExhausted Tests
# =============================================================================


class TestDownloadExceptions:
    """Tests for download exception classes."""

    def test_download_error_with_status(self) -> None:
        """DownloadError should carry status code."""
        err = DownloadError("Not found", status_code=404)
        assert str(err) == "Not found"
        assert err.status_code == 404

    def test_download_error_without_status(self) -> None:
        """DownloadError should work without status code."""
        err = DownloadError("Network failure")
        assert str(err) == "Network failure"
        assert err.status_code is None

    def test_retries_exhausted_attributes(self) -> None:
        """DownloadRetriesExhausted should carry attempts and last_status."""
        err = DownloadRetriesExhausted(
            "Failed after 4 attempts", attempts=4, last_status=503
        )
        assert err.attempts == 4
        assert err.last_status == 503
        assert err.status_code == 503

    def test_retries_exhausted_is_download_error(self) -> None:
        """DownloadRetriesExhausted should be a subclass of DownloadError."""
        err = DownloadRetriesExhausted("msg", attempts=1)
        assert isinstance(err, DownloadError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
