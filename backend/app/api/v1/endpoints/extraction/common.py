"""
Common utilities and shared dependencies for extraction endpoints.

This module contains:
- Logger setup
- Shared constants
- SharePoint helper functions
- Background task utilities
"""

import asyncio
import hashlib
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from app.services.extraction.metrics import FileMetrics, RunMetrics

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
) -> tuple[str, str]:
    """
    Download a SharePoint file to a temporary directory.

    Args:
        client: SharePointClient instance.
        file: SharePointFile to download.
        temp_dir: Temporary directory path.

    Returns:
        Tuple of (local file path, SHA-256 content hash).
    """
    content = await client.download_file(file)
    content_hash = hashlib.sha256(content).hexdigest()
    local_path = Path(temp_dir) / file.name
    local_path.write_bytes(content)
    logger.info(
        "sharepoint_file_downloaded",
        name=file.name,
        size=len(content),
        content_hash=content_hash[:12],
        deal_name=file.deal_name,
    )
    return str(local_path), content_hash


def _extract_single_file(
    extractor, file_path: str, deal_name: str
) -> tuple[str, str, dict | None, str | None]:
    """Extract data from a single Excel file (CPU-bound, thread-safe).

    Returns:
        Tuple of (file_path, deal_name, extracted_data_or_None, error_message_or_None).
    """
    try:
        result = extractor.extract_from_file(file_path)
        return (file_path, deal_name, result, None)
    except Exception as e:
        return (file_path, deal_name, None, str(e))


def process_files(
    db: Session,
    run_id: UUID,
    files_to_process: list[dict],
    mappings: dict,
    ExtractionRunCRUD,
    ExtractedValueCRUD,
    max_workers: int = 4,
    resume_run_id: UUID | None = None,
):
    """
    Process a list of files and extract data with per-deal change detection.

    Excel extraction is parallelized across threads (CPU-bound). DB
    operations (change detection + bulk_insert) remain sequential to
    avoid session conflicts.

    Args:
        db: Database session.
        run_id: Extraction run ID.
        files_to_process: List of file info dicts with file_path and deal_name.
        mappings: Cell mappings for extraction.
        ExtractionRunCRUD: CRUD class for extraction runs.
        ExtractedValueCRUD: CRUD class for extracted values.
        max_workers: Maximum parallel extraction threads (default 4).
        resume_run_id: If provided, skip files already completed in that run.
    """
    from app.extraction import ExcelDataExtractor
    from app.services.extraction.change_detector import should_extract_deal

    # Update run with file count
    ExtractionRunCRUD.update_progress(db, run_id, files_processed=0, files_failed=0)

    # Create extractor
    extractor = ExcelDataExtractor(mappings)

    processed = 0
    skipped = 0
    failed = 0
    file_errors: list[dict] = []
    per_file_status: dict[str, dict] = {}
    run_metrics = RunMetrics(files_total=len(files_to_process))

    # Resume support: skip files already completed in a previous run
    completed_files: set[str] = set()
    if resume_run_id:
        prev_run = ExtractionRunCRUD.get(db, resume_run_id)
        if prev_run and prev_run.per_file_status:
            completed_files = {
                fp
                for fp, info in prev_run.per_file_status.items()
                if info.get("status") == "completed"
            }
            logger.info(
                "resume_skipping_completed",
                resume_run_id=str(resume_run_id),
                files_skipped=len(completed_files),
            )

    # Filter out already-completed files for resume
    if completed_files:
        files_to_process = [
            fi for fi in files_to_process if fi["file_path"] not in completed_files
        ]

    # Build a file_path → file_info lookup for source_file resolution
    file_info_map = {fi["file_path"]: fi for fi in files_to_process}

    # Phase 1: Parallel extraction (CPU-bound Excel parsing)
    extraction_results: list[tuple[str, str, dict | None, str | None]] = []

    if len(files_to_process) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _extract_single_file,
                    extractor,
                    fi["file_path"],
                    fi.get("deal_name", ""),
                ): fi["file_path"]
                for fi in files_to_process
            }
            for future in as_completed(futures):
                extraction_results.append(future.result())
    else:
        # Single file — no threading overhead needed
        for fi in files_to_process:
            extraction_results.append(
                _extract_single_file(
                    extractor, fi["file_path"], fi.get("deal_name", "")
                )
            )

    # Phase 2: Sequential DB operations (change detection + insert)
    # Track property → source_file for collision detection (Issue 4.2)
    processed_properties: dict[str, str] = {}

    for file_path, deal_name, result, error_msg in extraction_results:
        file_info = file_info_map[file_path]

        if error_msg is not None:
            # Extraction failed
            failed += 1
            file_name = Path(file_path).name
            file_errors.append({"file": file_name, "error": error_msg})
            per_file_status[file_path] = {"status": "failed", "error": error_msg}
            run_metrics.record_file(
                FileMetrics(
                    file_path=file_path,
                    deal_name=deal_name,
                    status="failed",
                )
            )
            logger.error(
                "file_processing_failed",
                file=file_name,
                error=error_msg,
            )
        else:
            try:
                assert result is not None  # guaranteed when error_msg is None
                # Get property name from extracted data or use deal name
                property_name = (
                    result.get("PROPERTY_NAME", deal_name) or Path(file_path).stem
                )

                # Collision detection: warn if another file already wrote
                # to the same property_name (last-file-wins via upsert)
                prop_key = str(property_name)
                if prop_key in processed_properties:
                    logger.warning(
                        "property_name_collision",
                        property=prop_key,
                        previous_file=processed_properties[prop_key],
                        current_file=Path(file_path).name,
                        run_id=str(run_id),
                    )
                processed_properties[prop_key] = Path(file_path).name

                # Per-deal change detection: compare extracted vs DB
                needs_update, reason = should_extract_deal(
                    db, str(property_name), result
                )

                if not needs_update:
                    skipped += 1
                    per_file_status[file_path] = {"status": "skipped"}
                    run_metrics.record_file(
                        FileMetrics(
                            file_path=file_path,
                            deal_name=deal_name,
                            status="skipped",
                        )
                    )
                    logger.info(
                        "file_skipped_unchanged",
                        file=Path(file_path).name,
                        property=property_name,
                    )
                    processed += 1
                else:
                    # Data changed or new deal — insert ALL values
                    source_file = file_info.get("sharepoint_path", file_path)

                    ExtractedValueCRUD.bulk_insert(
                        db,
                        extraction_run_id=run_id,
                        extracted_data=result,
                        mappings=mappings,
                        property_name=str(property_name),
                        source_file=source_file,
                    )

                    processed += 1
                    per_file_status[file_path] = {"status": "completed"}
                    run_metrics.record_file(
                        FileMetrics(
                            file_path=file_path,
                            deal_name=deal_name,
                            status="completed",
                            values_count=len(result),
                        )
                    )
                    logger.info(
                        "file_processed",
                        file=Path(file_path).name,
                        property=property_name,
                        fields_extracted=len(result),
                        change_reason=reason,
                    )

            except Exception as e:
                failed += 1
                file_name = Path(file_path).name
                file_errors.append({"file": file_name, "error": str(e)})
                per_file_status[file_path] = {"status": "failed", "error": str(e)}
                run_metrics.record_file(
                    FileMetrics(
                        file_path=file_path,
                        deal_name=deal_name,
                        status="failed",
                    )
                )
                logger.error(
                    "file_processing_failed",
                    file=file_name,
                    error=str(e),
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

    # Emit structured metrics and build metadata
    run_metrics.emit_run_metrics(str(run_id))
    file_metadata = run_metrics.to_metadata()

    # Mark complete with error summary including skip stats
    ExtractionRunCRUD.complete(
        db,
        run_id,
        files_processed=processed,
        files_failed=failed,
        error_summary=error_summary,
        per_file_status=per_file_status if per_file_status else None,
        file_metadata=file_metadata,
    )
    logger.info(
        "extraction_completed",
        run_id=str(run_id),
        processed=processed,
        skipped=skipped,
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
                        # Concurrent downloads with semaphore limit
                        sem = asyncio.Semaphore(5)

                        async def _download_one(sp_file):
                            async with sem:
                                return sp_file, await download_sharepoint_file(
                                    client, sp_file, temp_dir
                                )

                        async def _download_all():
                            async with client:
                                return await asyncio.gather(
                                    *[_download_one(f) for f in sharepoint_files],
                                    return_exceptions=True,
                                )

                        results = loop.run_until_complete(_download_all())

                        for result in results:
                            if isinstance(result, Exception):
                                logger.error(
                                    "sharepoint_download_failed",
                                    error=str(result),
                                )
                                continue
                            sp_file, (local_path, content_hash) = result
                            files_to_process.append(
                                {
                                    "file_path": local_path,
                                    "deal_name": sp_file.deal_name,
                                    "deal_stage": sp_file.deal_stage,
                                    "sharepoint_path": sp_file.path,
                                    "content_hash": content_hash,
                                }
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
