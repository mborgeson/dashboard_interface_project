"""
ARQ task definitions for report generation.

Thin wrapper around the existing ``ReportWorker._process_one()`` logic
in ``app.services.report_worker``.
"""

from __future__ import annotations

from typing import Any

from loguru import logger


async def generate_report_task(
    ctx: dict[str, Any],
    report_id: int,
) -> dict[str, Any]:
    """ARQ task: Generate a queued report.

    Picks up a QueuedReport by ID and runs the generation pipeline
    (PDF or Excel). This reuses the existing ReportWorker's
    ``_process_one`` logic but is triggered by ARQ rather than polling.

    Args:
        ctx: ARQ job context (contains job_id, etc.).
        report_id: Primary key of the QueuedReport to process.

    Returns:
        Dictionary with generation result (status, file_size, download_url).
    """
    job_id = ctx.get("job_id", "unknown")
    logger.info(f"[task:{job_id}] Starting report generation for report_id={report_id}")

    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.report_template import QueuedReport
    from app.services.report_worker import ReportWorker

    worker = ReportWorker()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(QueuedReport).where(QueuedReport.id == report_id)
        )
        report = result.scalar_one_or_none()

        if report is None:
            logger.error(f"[task:{job_id}] Report {report_id} not found")
            return {"report_id": report_id, "status": "not_found"}

        await worker._process_one(db, report)

    logger.info(f"[task:{job_id}] Report generation complete for report_id={report_id}")
    return {
        "report_id": report_id,
        "status": "completed",
    }
