"""
B&R Capital Dashboard - SharePoint Client Module

Provides SharePoint integration for:
- Azure AD authentication via MSAL
- Deal folder discovery
- UW model file download

Uses Microsoft Graph API for SharePoint access.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp
import msal
import structlog

from app.core.config import settings


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


class SharePointAuthError(Exception):
    """Authentication failed"""

    pass


class SharePointClient:
    """
    SharePoint client for accessing deal folders and UW models.

    Uses MSAL for Azure AD authentication and Microsoft Graph API
    for SharePoint operations.
    """

    # Graph API endpoints
    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    # File patterns to look for
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
    ):
        self.tenant_id = tenant_id or settings.AZURE_TENANT_ID
        self.client_id = client_id or settings.AZURE_CLIENT_ID
        self.client_secret = client_secret or settings.AZURE_CLIENT_SECRET
        self.site_url = site_url or settings.SHAREPOINT_SITE_URL
        self.library_name = library_name or getattr(
            settings, "SHAREPOINT_LIBRARY", "Real Estate"
        )
        self.deals_folder = deals_folder or settings.SHAREPOINT_DEALS_FOLDER

        self.logger = structlog.get_logger().bind(component="SharePointClient")

        # MSAL app and token cache
        self._msal_app: msal.ConfidentialClientApplication | None = None
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

        # Site and drive IDs (cached after first lookup)
        self._site_id: str | None = None
        self._drive_id: str | None = None

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
            and datetime.utcnow() < self._token_expires - timedelta(minutes=5)
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
        self._token_expires = datetime.utcnow() + timedelta(
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

        async with aiohttp.ClientSession() as session, session.request(
            method, url, headers=headers, **kwargs
        ) as response:
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

        parsed = urlparse(self.site_url)
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
        self, deal_folder_path: str | None = None
    ) -> list[SharePointFile]:
        """
        Find UW model files in deal folders.

        Args:
            deal_folder_path: Specific folder to search, or None for all deals

        Returns:
            List of SharePointFile objects for discovered UW models
        """
        drive_id = await self._get_drive_id()

        if deal_folder_path:
            # Search specific folder
            folders = [{"path": deal_folder_path, "name": Path(deal_folder_path).name}]
        else:
            # Search all deal folders
            folders = await self.discover_deal_folders()

        uw_models = []

        for folder in folders:
            folder_path = folder["path"]
            deal_name = folder["name"]

            try:
                # Get all files in this folder (recursive)
                endpoint = f"/drives/{drive_id}/root:/{folder_path}:/children"
                result = await self._make_request("GET", endpoint)

                for item in result.get("value", []):
                    if "file" in item:
                        filename = item["name"]

                        # Check if it matches UW model patterns
                        for pattern in self.UW_MODEL_PATTERNS:
                            if re.match(pattern, filename, re.IGNORECASE):
                                uw_models.append(
                                    SharePointFile(
                                        name=filename,
                                        path=f"{folder_path}/{filename}",
                                        download_url=item.get(
                                            "@microsoft.graph.downloadUrl", ""
                                        ),
                                        size=item.get("size", 0),
                                        modified_date=datetime.fromisoformat(
                                            item["lastModifiedDateTime"].replace(
                                                "Z", "+00:00"
                                            )
                                        ),
                                        deal_name=deal_name,
                                        deal_stage=self._infer_deal_stage(folder_path),
                                    )
                                )
                                break

            except Exception as e:
                self.logger.warning(
                    "folder_scan_failed", folder=folder_path, error=str(e)
                )

        self.logger.info("uw_models_found", count=len(uw_models))
        return uw_models

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
        async with aiohttp.ClientSession() as session:
            async with session.get(file.download_url) as response:
                response.raise_for_status()
                content = await response.read()

        self.logger.info("file_downloaded", name=file.name, size=len(content))
        return content

    async def download_all_uw_models(
        self, output_dir: str | None = None
    ) -> list[tuple[SharePointFile, bytes]]:
        """
        Discover and download all UW models.

        Args:
            output_dir: Optional directory to save files locally

        Returns:
            List of (SharePointFile, content) tuples
        """
        files = await self.find_uw_models()
        results = []

        for file in files:
            try:
                content = await self.download_file(file)
                results.append((file, content))

                # Optionally save to disk
                if output_dir:
                    output_path = Path(output_dir) / file.name
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(content)

            except Exception as e:
                self.logger.error("download_failed", file=file.name, error=str(e))

        return results

    def _infer_deal_stage(self, folder_path: str) -> str | None:
        """Infer deal stage from folder path structure"""
        path_lower = folder_path.lower()

        if "closed" in path_lower or "acquired" in path_lower:
            return "closed"
        elif "pipeline" in path_lower or "active" in path_lower:
            return "pipeline"
        elif "dead" in path_lower or "passed" in path_lower:
            return "dead"
        elif "loi" in path_lower:
            return "loi"
        elif "due diligence" in path_lower or "dd" in path_lower:
            return "due_diligence"

        return None


# Convenience function for creating client from settings
def get_sharepoint_client() -> SharePointClient:
    """Create SharePointClient using application settings"""
    return SharePointClient()
