"""
Common utilities and shared dependencies for extraction endpoints.

This module contains:
- Logger setup
- Shared constants
- SharePoint helper functions
- Background task utilities
"""

import asyncio
import tempfile
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.extraction.sharepoint import (
    SharePointAuthError,
    SharePointClient,
    SharePointFile,
)

logger = structlog.get_logger().bind(component="extraction_api")

# Path to reference file (project root / filename)
REFERENCE_FILE = Path(__file__).parent.parent.parent.parent.parent.parent.parent / (
    "Underwriting_Dashboard_Cell_References.xlsx"
)


async def discover_sharepoint_files() -> list[SharePointFile]:
    """
    Discover UW model files from SharePoint.

    Returns:
        List of SharePointFile objects for discovered UW models.

    Raises:
        SharePointAuthError: If authentication fails.
        ValueError: If SharePoint is not configured.
    """
    if not settings.sharepoint_configured:
        missing = settings.get_sharepoint_config_errors()
        raise ValueError(f"SharePoint not configured. Missing: {', '.join(missing)}")

    client = SharePointClient()
    logger.info("sharepoint_discovery_started", site_url=settings.SHAREPOINT_SITE_URL)

    result = await client.find_uw_models()
    logger.info("sharepoint_files_discovered", count=len(result.files))

    return result.files


async def download_sharepoint_file(
    client: SharePointClient, file: SharePointFile, temp_dir: str
) -> str:
    """
    Download a SharePoint file to a temporary directory.

    Args:
        client: SharePointClient instance.
        file: SharePointFile to download.
        temp_dir: Temporary directory path.

    Returns:
        Path to the downloaded file.
    """
    content = await client.download_file(file)
    local_path = Path(temp_dir) / file.name
    local_path.write_bytes(content)
    logger.info(
        "sharepoint_file_downloaded",
        name=file.name,
        size=len(content),
        deal_name=file.deal_name,
    )
    return str(local_path)


def process_files(
    db: Session,
    run_id: UUID,
    files_to_process: list[dict],
    mappings: dict,
    ExtractionRunCRUD,
    ExtractedValueCRUD,
):
    """
    Process a list of files and extract data.

    Args:
        db: Database session.
        run_id: Extraction run ID.
        files_to_process: List of file info dicts with file_path and deal_name.
        mappings: Cell mappings for extraction.
        ExtractionRunCRUD: CRUD class for extraction runs.
        ExtractedValueCRUD: CRUD class for extracted values.
    """
    from app.extraction import ExcelDataExtractor

    # Update run with file count
    ExtractionRunCRUD.update_progress(db, run_id, files_processed=0, files_failed=0)

    # Create extractor
    extractor = ExcelDataExtractor(mappings)

    processed = 0
    failed = 0
    file_errors: list[dict] = []

    for file_info in files_to_process:
        file_path = file_info["file_path"]
        deal_name = file_info.get("deal_name", "")

        try:
            # Extract data
            result = extractor.extract_from_file(file_path)

            # Get property name from extracted data or use deal name
            property_name = (
                result.get("PROPERTY_NAME", deal_name) or Path(file_path).stem
            )

            # Include SharePoint metadata if available
            source_file = file_info.get("sharepoint_path", file_path)

            # Insert into database
            ExtractedValueCRUD.bulk_insert(
                db,
                extraction_run_id=run_id,
                extracted_data=result,
                mappings=mappings,
                property_name=str(property_name),
                source_file=source_file,
            )

            processed += 1
            logger.info(
                "file_processed",
                file=Path(file_path).name,
                property=property_name,
                fields_extracted=len(result),
            )

        except Exception as e:
            failed += 1
            file_name = Path(file_path).name
            error_msg = str(e)
            file_errors.append({"file": file_name, "error": error_msg})
            logger.error(
                "file_processing_failed",
                file=file_name,
                error=error_msg,
                exc_info=True,
            )

        # Update progress after each file
        try:
            ExtractionRunCRUD.update_progress(
                db, run_id, files_processed=processed, files_failed=failed
            )
        except Exception as progress_error:
            logger.warning(
                "progress_update_failed",
                run_id=str(run_id),
                error=str(progress_error),
            )

    # Prepare error summary if there were failures
    error_summary = None
    if file_errors:
        error_summary = {
            "failed_files": file_errors[:10],
            "total_failures": len(file_errors),
        }

    # Mark complete with error summary
    ExtractionRunCRUD.complete(
        db,
        run_id,
        files_processed=processed,
        files_failed=failed,
        error_summary=error_summary,
    )
    logger.info(
        "extraction_completed",
        run_id=str(run_id),
        processed=processed,
        failed=failed,
    )


def run_extraction_task(run_id: UUID, source: str, file_paths: list | None = None):
    """
    Background task to run extraction.

    This is executed in a separate thread by FastAPI BackgroundTasks.
    Supports both local files and SharePoint sources.

    Note: Creates its own database session since the request session
    will be closed by the time this background task executes.
    """
    from app.crud.extraction import ExtractedValueCRUD, ExtractionRunCRUD
    from app.extraction import CellMappingParser

    db = SessionLocal()

    try:
        parser = CellMappingParser(str(REFERENCE_FILE))
        mappings = parser.load_mappings()

        if source == "local" and file_paths:
            files_to_process = [
                {
                    "file_path": p,
                    "deal_name": Path(p).stem.replace(" UW Model vCurrent", ""),
                }
                for p in file_paths
            ]
            logger.info("local_extraction_started", file_count=len(files_to_process))

        elif source == "sharepoint":
            logger.info("sharepoint_extraction_started")

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    sharepoint_files = loop.run_until_complete(
                        discover_sharepoint_files()
                    )

                    if not sharepoint_files:
                        logger.warning("no_sharepoint_files_found")
                        ExtractionRunCRUD.complete(
                            db, run_id, files_processed=0, files_failed=0
                        )
                        return

                    client = SharePointClient()
                    files_to_process = []

                    with tempfile.TemporaryDirectory(prefix="uw_models_") as temp_dir:
                        for sp_file in sharepoint_files:
                            try:
                                local_path = loop.run_until_complete(
                                    download_sharepoint_file(client, sp_file, temp_dir)
                                )
                                files_to_process.append(
                                    {
                                        "file_path": local_path,
                                        "deal_name": sp_file.deal_name,
                                        "deal_stage": sp_file.deal_stage,
                                        "sharepoint_path": sp_file.path,
                                    }
                                )
                            except Exception as e:
                                logger.error(
                                    "sharepoint_download_failed",
                                    file=sp_file.name,
                                    error=str(e),
                                )

                        process_files(
                            db,
                            run_id,
                            files_to_process,
                            mappings,
                            ExtractionRunCRUD,
                            ExtractedValueCRUD,
                        )
                        return
                finally:
                    loop.close()

            except SharePointAuthError as e:
                logger.error("sharepoint_auth_failed", error=str(e))
                ExtractionRunCRUD.fail(
                    db,
                    run_id,
                    {
                        "error": "SharePoint authentication failed",
                        "details": str(e),
                    },
                )
                return

            except ValueError as e:
                logger.error("sharepoint_config_error", error=str(e))
                ExtractionRunCRUD.fail(
                    db,
                    run_id,
                    {
                        "error": "SharePoint configuration error",
                        "details": str(e),
                    },
                )
                return

        else:
            logger.info("fixture_extraction_started", source=source)
            fixtures_dir = (
                Path(__file__).parent.parent.parent.parent.parent.parent
                / "tests"
                / "fixtures"
                / "uw_models"
            )
            files_to_process = [
                {
                    "file_path": str(f),
                    "deal_name": f.stem.replace(" UW Model vCurrent", ""),
                }
                for f in fixtures_dir.glob("*.xlsb")
            ]

        process_files(
            db,
            run_id,
            files_to_process,
            mappings,
            ExtractionRunCRUD,
            ExtractedValueCRUD,
        )

    except Exception as e:
        logger.exception("extraction_task_failed", error=str(e))
        try:
            from app.crud.extraction import ExtractionRunCRUD

            ExtractionRunCRUD.fail(db, run_id, {"error": str(e)})
        except Exception as db_error:
            logger.error(
                "failed_to_update_run_status",
                run_id=str(run_id),
                original_error=str(e),
                db_error=str(db_error),
            )
    finally:
        db.close()
