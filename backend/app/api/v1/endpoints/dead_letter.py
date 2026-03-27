"""
Dead-letter (quarantine) API endpoints.

Provides endpoints for managing quarantined files that have failed
extraction multiple times:
- GET /dead-letter — list quarantined files
- POST /dead-letter/{id}/retry — retry a quarantined file
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_analyst, require_manager
from app.db.session import get_db
from app.schemas.dead_letter import (
    DeadLetterFileResponse,
    DeadLetterListResponse,
    DeadLetterRetryResponse,
)
from app.services.extraction.dead_letter import (
    get_quarantined_files,
    retry_quarantined_file,
)

router = APIRouter()


@router.get(
    "/dead-letter",
    response_model=DeadLetterListResponse,
    summary="List quarantined files",
)
async def list_dead_letter_files(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_analyst),
) -> DeadLetterListResponse:
    """List all quarantined files that have failed extraction repeatedly.

    These files have exceeded the consecutive failure threshold and are
    excluded from automatic extraction. Use the retry endpoint to
    re-attempt extraction.
    """
    files, total = await get_quarantined_files(db, skip=skip, limit=limit)

    items = [
        DeadLetterFileResponse(
            id=f.id,
            file_path=f.file_path,
            file_name=f.file_name,
            deal_name=f.deal_name,
            consecutive_failures=f.consecutive_failures,
            last_failure_at=f.last_failure_at,
            last_failure_reason=f.last_failure_reason,
            quarantined_at=f.quarantined_at,
            is_active=f.is_active,
            deal_stage=f.deal_stage,
        )
        for f in files
    ]

    return DeadLetterListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + limit < total,
    )


@router.post(
    "/dead-letter/{file_id}/retry",
    response_model=DeadLetterRetryResponse,
    summary="Retry a quarantined file",
)
async def retry_dead_letter_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_manager),
) -> DeadLetterRetryResponse:
    """Reset quarantine status and mark file for re-extraction.

    Clears the consecutive failure count and quarantine flag, then
    marks the file as pending extraction so the next extraction cycle
    picks it up.

    Requires manager-level permissions.
    """
    file = await retry_quarantined_file(db, file_id)
    if file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Monitored file {file_id} not found",
        )

    await db.commit()

    logger.info(
        "dead_letter_retry_requested",
        file_id=str(file_id),
        file_name=file.file_name,
        user=current_user.email,
    )

    return DeadLetterRetryResponse(
        id=file.id,
        file_name=file.file_name,
        deal_name=file.deal_name,
        message="File quarantine reset. Marked for re-extraction.",
        extraction_pending=file.extraction_pending,
    )
