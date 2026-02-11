"""
B&R Capital Dashboard - SharePoint Client Module

Provides SharePoint integration for:
- Azure AD authentication via MSAL
- Deal folder discovery
- UW model file download
- Configurable file filtering

Uses Microsoft Graph API for SharePoint access.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import msal
import structlog

from app.core.config import settings

if TYPE_CHECKING:
    from .file_filter import FileFilter


@dataclass
class SharePointFile:
    """Represents a file discovered in SharePoint"""

    name: str
    path: str
    download_url: str
    size: int
    modified_date: datetime
    deal_name: str
    deal_stage: str | None = None


@dataclass
class SkippedFile:
    """Represents a file that was skipped during discovery"""

    name: str
    path: str
    size: int
    modified_date: datetime
    skip_reason: str
    deal_name: str


@dataclass
class DiscoveryResult:
    """Result of UW model discovery with filtering applied"""

    files: list[SharePointFile] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)
    total_scanned: int = 0
    folders_scanned: int = 0


class SharePointAuthError(Exception):
    """Authentication failed"""

    pass


class SharePointClient:
    """
    SharePoint client for accessing deal folders and UW models.

    Uses MSAL for Azure AD authentication and Microsoft Graph API
    for SharePoint operations. Supports configurable file filtering.
    """

    # Graph API endpoints
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    # Legacy file patterns (used as fallback if no FileFilter provided)
    UW_MODEL_PATTERNS = [
        r".*UW Model.*\.xlsb$",
        r".*UW Model.*\.xlsx$",
        r".*Underwriting.*\.xlsb$",
    ]

    def __init__(
        self,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        site_url: str | None = None,
        library_name: str | None = None,
        deals_folder: str | None = None,
        file_filter: "FileFilter | None" = None,
    ):
        self.tenant_id = tenant_id or settings.AZURE_TENANT_ID
        self.client_id = client_id or settings.AZURE_CLIENT_ID
        self.client_secret = client_secret or settings.AZURE_CLIENT_SECRET
        self.site_url = site_url or settings.SHAREPOINT_SITE_URL
        self.library_name = library_name or getattr(
            settings, "SHAREPOINT_LIBRARY", "Real Estate"
        )
        self.deals_folder = deals_folder or settings.SHAREPOINT_DEALS_FOLDER

        # File filter for configurable filtering
        self._file_filter = file_filter

        self.logger = structlog.get_logger().bind(component="SharePointClient")

        # MSAL app and token cache
        self._msal_app: msal.ConfidentialClientApplication | None = None
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

        # Site and drive IDs (cached after first lookup)
        self._site_id: str | None = None
        self._drive_id: str | None = None

    @property
    def file_filter(self) -> "FileFilter":
        """Get or create file filter instance."""
        if self._file_filter is None:
            from .file_filter import get_file_filter

            self._file_filter = get_file_filter()
        return self._file_filter

    def set_file_filter(self, file_filter: "FileFilter") -> None:
        """Set custom file filter instance."""
        self._file_filter = file_filter

    def _get_msal_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL confidential client app"""
        if self._msal_app is None:
            authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=authority,
            )
        return self._msal_app

    async def _get_access_token(self) -> str:
        """
        Get valid access token, refreshing if needed.

        Uses client credentials flow for app-only authentication.
        """
        # Check if we have a valid cached token
        if (
            self._access_token
            and self._token_expires
            and datetime.now(UTC) < self._token_expires - timedelta(minutes=5)
        ):
            return self._access_token

        # Acquire new token
        app = self._get_msal_app()
        scopes = ["https://graph.microsoft.com/.default"]

        result = app.acquire_token_for_client(scopes=scopes)

        if "access_token" not in result:
            error = result.get("error_description", "Unknown error")
            self.logger.error("auth_failed", error=error)
            raise SharePointAuthError(f"Failed to acquire token: {error}")

        self._access_token = result["access_token"]
        # Token typically valid for 1 hour
        self._token_expires = datetime.now(UTC) + timedelta(
            seconds=result.get("expires_in", 3600)
        )

        self.logger.info("token_acquired", expires_in=result.get("expires_in"))
        return self._access_token

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> dict[str, Any]:
        """Make authenticated request to Graph API"""
        token = await self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.GRAPH_BASE_URL}{endpoint}"

        async with (
            aiohttp.ClientSession() as session,
            session.request(method, url, headers=headers, **kwargs) as response,
        ):
            if response.status == 401:
                # Token may have expired, clear cache and retry once
                self._access_token = None
                token = await self._get_access_token()
                headers["Authorization"] = f"Bearer {token}"
                async with session.request(
                    method, url, headers=headers, **kwargs
                ) as retry_response:
                    retry_response.raise_for_status()
                    return await retry_response.json()

            response.raise_for_status()
            return await response.json()

    async def _get_site_id(self) -> str:
        """Get SharePoint site ID from site URL"""
        if self._site_id:
            return self._site_id

        # Parse site URL to get hostname and site path
        # e.g., https://company.sharepoint.com/sites/Investments
        from urllib.parse import urlparse

        parsed = urlparse(str(self.site_url))
        hostname = parsed.netloc
        site_path = parsed.path.rstrip("/")

        endpoint = f"/sites/{hostname}:{site_path}"
        result = await self._make_request("GET", endpoint)

        self._site_id = result["id"]
        self.logger.info("site_id_retrieved", site_id=self._site_id)
        return self._site_id

    async def _get_drive_id(self) -> str:
        """Get document library drive ID by name (defaults to 'Real Estate')"""
        if self._drive_id:
            return self._drive_id

        site_id = await self._get_site_id()

        # Get all drives and find the one matching our library name
        endpoint = f"/sites/{site_id}/drives"
        result = await self._make_request("GET", endpoint)

        for drive in result.get("value", []):
            if drive["name"] == self.library_name:
                self._drive_id = drive["id"]
                self.logger.info(
                    "drive_id_retrieved",
                    library=self.library_name,
                    drive_id=self._drive_id,
                )
                return self._drive_id

        # Fallback to default drive if library not found
        self.logger.warning(
            "library_not_found",
            library=self.library_name,
            available=[d["name"] for d in result.get("value", [])],
        )
        endpoint = f"/sites/{site_id}/drive"
        result = await self._make_request("GET", endpoint)
        self._drive_id = result["id"]
        self.logger.info("drive_id_retrieved", drive_id=self._drive_id)
        return self._drive_id

    async def discover_deal_folders(self) -> list[dict[str, Any]]:
        """
        Discover all deal folders in the Deals directory.

        Returns:
            List of folder metadata dicts with name, path, id
        """
        drive_id = await self._get_drive_id()

        # Get children of the deals folder
        folder_path = self.deals_folder.strip("/")
        endpoint = f"/drives/{drive_id}/root:/{folder_path}:/children"

        result = await self._make_request("GET", endpoint)

        folders = []
        for item in result.get("value", []):
            if "folder" in item:  # It's a folder
                folders.append(
                    {
                        "name": item["name"],
                        "id": item["id"],
                        "path": f"{folder_path}/{item['name']}",
                        "child_count": item["folder"].get("childCount", 0),
                        "modified_date": item.get("lastModifiedDateTime"),
                    }
                )

        self.logger.info("deal_folders_discovered", count=len(folders))
        return folders

    async def find_uw_models(
        self,
        deal_folder_path: str | None = None,
        use_filter: bool = True,
    ) -> DiscoveryResult:
        """
        Find UW model files in deal folders with configurable filtering.

        Recursively scans the folder structure:
        - Deals/{Stage}/{Deal Name}/UW Model/*.xlsb

        Args:
            deal_folder_path: Specific folder to search, or None for all deals
            use_filter: Whether to apply FileFilter rules (default True)

        Returns:
            DiscoveryResult containing accepted files, skipped files, and stats
        """
        drive_id = await self._get_drive_id()

        if deal_folder_path:
            # Search specific folder - treat as a deal folder directly
            result = DiscoveryResult()
            result.folders_scanned = 1
            await self._scan_deal_folder(
                drive_id=drive_id,
                deal_path=deal_folder_path,
                deal_name=Path(deal_folder_path).name,
                deal_stage=self._infer_deal_stage(deal_folder_path),
                result=result,
                use_filter=use_filter,
            )
            return result

        # Get stage folders (e.g., "1) Initial UW and Review", "4) Closed Deals")
        stage_folders = await self.discover_deal_folders()

        result = DiscoveryResult()
        result.folders_scanned = len(stage_folders)

        for stage_folder in stage_folders:
            stage_path = stage_folder["path"]
            stage_name = stage_folder["name"]
            deal_stage = self._infer_deal_stage(stage_path)

            self.logger.debug(
                "scanning_stage_folder",
                stage=stage_name,
                path=stage_path,
            )

            try:
                # Get deal folders within this stage
                endpoint = f"/drives/{drive_id}/root:/{stage_path}:/children"
                stage_result = await self._make_request("GET", endpoint)

                for item in stage_result.get("value", []):
                    # Only process folders (deal folders)
                    if "folder" not in item:
                        continue

                    deal_name = item["name"]
                    deal_path = f"{stage_path}/{deal_name}"

                    # Scan the deal folder for UW models
                    await self._scan_deal_folder(
                        drive_id=drive_id,
                        deal_path=deal_path,
                        deal_name=deal_name,
                        deal_stage=deal_stage,
                        result=result,
                        use_filter=use_filter,
                    )

            except Exception as e:
                self.logger.warning(
                    "stage_folder_scan_failed", folder=stage_path, error=str(e)
                )

        self.logger.info(
            "uw_models_discovery_complete",
            accepted=len(result.files),
            skipped=len(result.skipped),
            total_scanned=result.total_scanned,
            folders_scanned=result.folders_scanned,
        )

        return result

    async def _scan_deal_folder(
        self,
        drive_id: str,
        deal_path: str,
        deal_name: str,
        deal_stage: str | None,
        result: DiscoveryResult,
        use_filter: bool,
    ) -> None:
        """
        Scan a single deal folder for UW model files.

        Looks for files in:
        1. Direct children of the deal folder
        2. "UW Model" subfolder within the deal folder
        3. Any subfolder containing "UW" or "Model" in the name
        """
        try:
            # Get children of deal folder
            endpoint = f"/drives/{drive_id}/root:/{deal_path}:/children"
            deal_result = await self._make_request("GET", endpoint)

            uw_model_subfolders = []

            for item in deal_result.get("value", []):
                item_name = item["name"]

                # Check if this is a subfolder that might contain UW models
                if "folder" in item:
                    # Look for "UW Model", "UW", "Model" subfolders
                    name_lower = item_name.lower()
                    if "uw" in name_lower or "model" in name_lower:
                        uw_model_subfolders.append(f"{deal_path}/{item_name}")
                    continue

                # Process file if it's in the deal folder directly
                if "file" in item:
                    self._process_file_item(
                        item=item,
                        folder_path=deal_path,
                        deal_name=deal_name,
                        deal_stage=deal_stage,
                        result=result,
                        use_filter=use_filter,
                    )

            # Scan UW Model subfolders
            for subfolder_path in uw_model_subfolders:
                result.folders_scanned += 1
                try:
                    subfolder_endpoint = (
                        f"/drives/{drive_id}/root:/{subfolder_path}:/children"
                    )
                    subfolder_result = await self._make_request(
                        "GET", subfolder_endpoint
                    )

                    self.logger.debug(
                        "scanning_uw_model_subfolder",
                        path=subfolder_path,
                        items=len(subfolder_result.get("value", [])),
                    )

                    for item in subfolder_result.get("value", []):
                        if "file" in item:
                            self._process_file_item(
                                item=item,
                                folder_path=subfolder_path,
                                deal_name=deal_name,
                                deal_stage=deal_stage,
                                result=result,
                                use_filter=use_filter,
                            )

                except Exception as e:
                    self.logger.warning(
                        "uw_subfolder_scan_failed",
                        subfolder=subfolder_path,
                        error=str(e),
                    )

        except Exception as e:
            self.logger.warning(
                "deal_folder_scan_failed", folder=deal_path, error=str(e)
            )

    def _process_file_item(
        self,
        item: dict[str, Any],
        folder_path: str,
        deal_name: str,
        deal_stage: str | None,
        result: DiscoveryResult,
        use_filter: bool,
    ) -> None:
        """Process a single file item from the Graph API response."""
        filename = item["name"]
        file_size = item.get("size", 0)
        modified_date = datetime.fromisoformat(
            item["lastModifiedDateTime"].replace("Z", "+00:00")
        )

        result.total_scanned += 1

        if use_filter:
            # Apply configurable file filter
            filter_result = self.file_filter.should_process(
                filename=filename,
                size_bytes=file_size,
                modified_date=modified_date,
            )

            if not filter_result.should_process:
                result.skipped.append(
                    SkippedFile(
                        name=filename,
                        path=f"{folder_path}/{filename}",
                        size=file_size,
                        modified_date=modified_date,
                        skip_reason=filter_result.reason_message or "unknown",
                        deal_name=deal_name,
                    )
                )
                self.logger.debug(
                    "file_skipped",
                    filename=filename,
                    deal=deal_name,
                    reason=filter_result.reason_message,
                )
                return
        else:
            # Legacy pattern matching (fallback)
            matched = False
            for pattern in self.UW_MODEL_PATTERNS:
                if re.match(pattern, filename, re.IGNORECASE):
                    matched = True
                    break
            if not matched:
                return

        # File passed filtering - add to results
        result.files.append(
            SharePointFile(
                name=filename,
                path=f"{folder_path}/{filename}",
                download_url=item.get("@microsoft.graph.downloadUrl", ""),
                size=file_size,
                modified_date=modified_date,
                deal_name=deal_name,
                deal_stage=deal_stage,
            )
        )

        self.logger.debug(
            "file_accepted",
            filename=filename,
            deal=deal_name,
            size_mb=round(file_size / 1024 / 1024, 1),
        )

    async def find_uw_models_simple(
        self, deal_folder_path: str | None = None
    ) -> list[SharePointFile]:
        """
        Find UW model files (returns list only for backwards compatibility).

        Args:
            deal_folder_path: Specific folder to search, or None for all deals

        Returns:
            List of SharePointFile objects for discovered UW models
        """
        result = await self.find_uw_models(deal_folder_path, use_filter=True)
        return result.files

    async def download_file(self, file: SharePointFile) -> bytes:
        """
        Download a file from SharePoint.

        Args:
            file: SharePointFile object with download URL

        Returns:
            File content as bytes
        """
        if not file.download_url:
            # Get fresh download URL
            drive_id = await self._get_drive_id()
            file_path = file.path.strip("/")
            endpoint = f"/drives/{drive_id}/root:/{file_path}"
            result = await self._make_request("GET", endpoint)
            file.download_url = result.get("@microsoft.graph.downloadUrl", "")

        if not file.download_url:
            raise ValueError(f"No download URL available for {file.name}")

        # Download using the pre-authenticated URL
        # Download using the pre-authenticated URL
        async with (
            aiohttp.ClientSession() as session,
            session.get(file.download_url) as response,
        ):
            response.raise_for_status()
            content = await response.read()

        self.logger.info("file_downloaded", name=file.name, size=len(content))
        return content

    async def download_all_uw_models(
        self, output_dir: str | None = None
    ) -> tuple[list[tuple[SharePointFile, bytes]], DiscoveryResult]:
        """
        Discover and download all UW models.

        Args:
            output_dir: Optional directory to save files locally

        Returns:
            Tuple of (downloaded files list, discovery result with skip info)
        """
        discovery_result = await self.find_uw_models()
        downloaded = []

        for file in discovery_result.files:
            try:
                content = await self.download_file(file)
                downloaded.append((file, content))

                # Optionally save to disk
                if output_dir:
                    output_path = Path(output_dir) / file.name
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(content)

            except Exception as e:
                self.logger.error("download_failed", file=file.name, error=str(e))

        return downloaded, discovery_result

    def _infer_deal_stage(self, folder_path: str) -> str | None:
        """Infer deal stage from folder path structure.

        Maps SharePoint folder names to normalized stage identifiers:
          0) Dead Deals          -> dead
          1) Initial UW and Review -> initial_review
          2) Active UW and Review  -> active_review
          3) Deals Under Contract  -> under_contract
          4) Closed Deals          -> closed
          5) Realized Deals        -> realized
          Archive                  -> archive
          Deal Pipeline            -> pipeline
        """
        path_lower = folder_path.lower()

        if "dead" in path_lower or "passed" in path_lower:
            return "dead"
        elif "initial uw" in path_lower or "initial review" in path_lower:
            return "initial_review"
        elif "active uw" in path_lower or "active review" in path_lower:
            return "active_review"
        elif "under contract" in path_lower:
            return "under_contract"
        elif "closed" in path_lower or "acquired" in path_lower:
            return "closed"
        elif "realized" in path_lower:
            return "realized"
        elif "archive" in path_lower:
            return "archive"
        elif "pipeline" in path_lower or "active" in path_lower:
            return "pipeline"
        elif "loi" in path_lower:
            return "loi"
        elif "due diligence" in path_lower or "dd" in path_lower:
            return "due_diligence"

        return None


# Convenience function for creating client from settings
def get_sharepoint_client() -> SharePointClient:
    """Create SharePointClient using application settings"""
    return SharePointClient()
