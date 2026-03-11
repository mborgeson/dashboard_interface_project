"""
ARQ task definitions for proforma extraction.

Thin wrapper around the existing extraction pipeline in
``app.api.v1.endpoints.extraction.common``.
"""

from __future__ import annotations

from typing import Any

from loguru import logger


async def run_extraction_task(
    ctx: dict[str, Any],
    run_id: str,
    source: str = "local",
    file_paths: list[str] | None = None,
) -> dict[str, Any]:
    """ARQ task: Run proforma extraction for a batch of files.

    Wraps ``common.run_extraction_task`` from the extraction endpoints.
    This is the same function that BackgroundTasks currently calls,
    now dispatchable via ARQ.

    Args:
        ctx: ARQ job context (contains job_id, etc.).
        run_id: UUID of the ExtractionRun record (as string).
        source: Extraction source ("local", "sharepoint").
        file_paths: Optional list of specific file paths to process.

    Returns:
        Dictionary with extraction result summary.
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(
        f"[task:{job_id}] Starting extraction run_id={run_id} "
        f"source={source} files={len(file_paths) if file_paths else 'auto'}"
    )

    from uuid import UUID

    from app.api.v1.endpoints.extraction.common import (
        run_extraction_task as _run_extraction,
    )

    # The existing function handles its own DB session management
    await _run_extraction(UUID(run_id), source, file_paths)

    logger.info(f"[task:{job_id}] Extraction run {run_id} complete")
    return {
        "run_id": run_id,
        "source": source,
        "status": "completed",
    }
