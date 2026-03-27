"""
SharePoint file download with retry logic.

Provides resilient download capabilities with:
- Exponential backoff with jitter for transient errors
- Retry-After header parsing (429 rate limiting)
- Automatic URL refresh on 403 (expired pre-auth URLs)
- Configurable max retries and backoff parameters

Uses Microsoft Graph API for URL refresh when pre-authenticated
download URLs expire.
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

import aiohttp
from loguru import logger

from app.core.config import settings

if TYPE_CHECKING:
    from app.extraction.sharepoint import SharePointClient, SharePointFile


class DownloadError(Exception):
    """Base exception for download failures."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DownloadRetriesExhausted(DownloadError):
    """All retry attempts have been exhausted."""

    def __init__(
        self, message: str, attempts: int, last_status: int | None = None
    ) -> None:
        super().__init__(message, status_code=last_status)
        self.attempts = attempts
        self.last_status = last_status


def _is_transient_error(status_code: int) -> bool:
    """Determine whether an HTTP status code represents a transient error.

    Returns True for errors that are worth retrying:
    - 429 (Too Many Requests / rate limit)
    - 5xx (server errors)

    Returns False for client errors (4xx) except 429 and 403:
    - 403 is handled separately (URL refresh)
    - Other 4xx errors indicate permanent failures
    """
    if status_code == 429:
        return True
    return status_code >= 500


def _parse_retry_after(header_value: str | None) -> float | None:
    """Parse a Retry-After header value into seconds to wait.

    Supports two formats per RFC 7231:
    - Integer seconds: "120" -> 120.0
    - HTTP-date: "Wed, 26 Mar 2026 12:00:00 GMT" -> seconds until that time

    Returns None if the header is absent or unparseable.
    """
    if not header_value:
        return None

    # Try integer seconds first
    try:
        seconds = int(header_value)
        return float(max(0, seconds))
    except ValueError:
        pass

    # Try HTTP-date format
    try:
        retry_date = parsedate_to_datetime(header_value)
        # Ensure timezone-aware comparison
        if retry_date.tzinfo is None:
            # Assume UTC if no timezone
            retry_date = retry_date.replace(tzinfo=UTC)
        delta = (retry_date - datetime.now(UTC)).total_seconds()
        return max(0.0, delta)
    except (ValueError, TypeError):
        pass

    return None


def _calculate_backoff(
    attempt: int,
    base_delay: float | None = None,
    retry_after: float | None = None,
) -> float:
    """Calculate delay before next retry attempt.

    If retry_after is provided (from Retry-After header), uses that value.
    Otherwise uses exponential backoff: base_delay * (2 ** attempt) + jitter.

    Args:
        attempt: Zero-based attempt number (0 = first retry).
        base_delay: Base delay in seconds. Defaults to settings value.
        retry_after: Explicit delay from Retry-After header.

    Returns:
        Delay in seconds before the next retry.
    """
    if retry_after is not None:
        return retry_after

    if base_delay is None:
        base_delay = settings.DOWNLOAD_BACKOFF_BASE_SECONDS

    delay = base_delay * (2**attempt)
    # Add jitter: random value between 0 and 50% of delay
    jitter = random.uniform(0, delay * 0.5)  # noqa: S311
    return delay + jitter


async def _refresh_download_url(
    sp_client: SharePointClient,
    file: SharePointFile,
) -> str:
    """Request a fresh download URL from Graph API.

    When a SharePoint pre-authenticated download URL expires (returns 403),
    this function fetches a new one via the Graph API.

    Args:
        sp_client: Authenticated SharePoint client instance.
        file: The file whose URL needs refreshing.

    Returns:
        Fresh download URL string.

    Raises:
        DownloadError: If unable to obtain a fresh URL.
    """
    drive_id = await sp_client._get_drive_id()
    file_path = file.path.strip("/")
    endpoint = f"/drives/{drive_id}/root:/{file_path}"

    try:
        result = await sp_client._make_request("GET", endpoint)
        new_url = result.get("@microsoft.graph.downloadUrl", "")
        if not new_url:
            raise DownloadError(
                f"No download URL returned for {file.name}", status_code=403
            )
        file.download_url = new_url
        logger.info(
            "Download URL refreshed",
            file=file.name,
        )
        return new_url
    except Exception as exc:
        if isinstance(exc, DownloadError):
            raise
        raise DownloadError(
            f"Failed to refresh download URL for {file.name}: {exc}",
            status_code=403,
        ) from exc


async def download_file_with_retry(
    sp_client: SharePointClient,
    file: SharePointFile,
    *,
    max_retries: int | None = None,
    backoff_base: float | None = None,
    session: aiohttp.ClientSession | None = None,
) -> bytes:
    """Download a file from SharePoint with retry logic.

    Implements resilient download with:
    - Exponential backoff with jitter for 5xx / network errors
    - Retry-After header support for 429 responses
    - Automatic URL refresh on 403 (expired pre-auth URL)
    - Immediate failure on non-transient 4xx errors (400, 404, etc.)

    Args:
        sp_client: Authenticated SharePoint client for URL refresh.
        file: SharePoint file to download.
        max_retries: Maximum retry attempts. Defaults to settings value.
        backoff_base: Base delay for exponential backoff. Defaults to settings.
        session: Optional aiohttp session to reuse. Creates one if not provided.

    Returns:
        Downloaded file content as bytes.

    Raises:
        DownloadRetriesExhausted: All retry attempts failed.
        DownloadError: Non-transient error (e.g., 404).
        ValueError: No download URL available.
    """
    if max_retries is None:
        max_retries = settings.DOWNLOAD_MAX_RETRIES
    if backoff_base is None:
        backoff_base = settings.DOWNLOAD_BACKOFF_BASE_SECONDS

    if not file.download_url:
        raise ValueError(f"No download URL available for {file.name}")

    owns_session = session is None
    if owns_session:
        session = aiohttp.ClientSession()
    assert session is not None  # guaranteed by the block above

    last_status: int | None = None
    last_error: str = ""

    try:
        for attempt in range(max_retries + 1):
            try:
                async with session.get(file.download_url) as response:
                    last_status = response.status

                    if response.status == 200:
                        content = await response.read()
                        if attempt > 0:
                            logger.info(
                                "Download succeeded after retry",
                                file=file.name,
                                attempt=attempt,
                            )
                        return content

                    # 403: Expired pre-auth URL -- refresh and retry
                    if response.status == 403:
                        if attempt < max_retries:
                            logger.warning(
                                "Download URL expired (403), refreshing",
                                file=file.name,
                                attempt=attempt,
                            )
                            await _refresh_download_url(sp_client, file)
                            # No backoff needed for URL refresh
                            continue
                        last_error = "Download URL expired and max retries exhausted"

                    # 429: Rate limited -- use Retry-After if available
                    elif response.status == 429:
                        if attempt < max_retries:
                            retry_after = _parse_retry_after(
                                response.headers.get("Retry-After")
                            )
                            delay = _calculate_backoff(
                                attempt,
                                base_delay=backoff_base,
                                retry_after=retry_after,
                            )
                            logger.warning(
                                "Rate limited (429), backing off",
                                file=file.name,
                                attempt=attempt,
                                delay_seconds=round(delay, 2),
                                retry_after_header=response.headers.get("Retry-After"),
                            )
                            await asyncio.sleep(delay)
                            continue
                        last_error = "Rate limited and max retries exhausted"

                    # 5xx: Transient server error -- exponential backoff
                    elif _is_transient_error(response.status):
                        if attempt < max_retries:
                            delay = _calculate_backoff(attempt, base_delay=backoff_base)
                            logger.warning(
                                "Transient error, retrying",
                                file=file.name,
                                status=response.status,
                                attempt=attempt,
                                delay_seconds=round(delay, 2),
                            )
                            await asyncio.sleep(delay)
                            continue
                        last_error = f"Server error {response.status} after max retries"

                    # 4xx (except 403/429): Non-transient -- fail immediately
                    else:
                        body_text = await response.text()
                        raise DownloadError(
                            f"Non-transient HTTP {response.status} downloading "
                            f"{file.name}: {body_text[:200]}",
                            status_code=response.status,
                        )

            except aiohttp.ClientError as exc:
                # Network-level errors (DNS, connection reset, etc.)
                last_status = None
                last_error = str(exc)
                if attempt < max_retries:
                    delay = _calculate_backoff(attempt, base_delay=backoff_base)
                    logger.warning(
                        "Network error, retrying",
                        file=file.name,
                        error=str(exc),
                        attempt=attempt,
                        delay_seconds=round(delay, 2),
                    )
                    await asyncio.sleep(delay)
                    continue

            except DownloadError:
                raise  # Re-raise non-transient errors immediately

        # All retries exhausted
        raise DownloadRetriesExhausted(
            f"Download failed for {file.name} after {max_retries + 1} attempts: {last_error}",
            attempts=max_retries + 1,
            last_status=last_status,
        )

    finally:
        if owns_session:
            await session.close()
