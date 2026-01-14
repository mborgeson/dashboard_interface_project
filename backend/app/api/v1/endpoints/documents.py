"""
Document endpoints for document management.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_document import document as document_crud
from app.db.session import get_db
from app.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentStats,
    DocumentUpdate,
    DocumentUploadResponse,
)

router = APIRouter()


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, alias="type"),
    property_id: str | None = None,
    search: str | None = None,
    date_range: str | None = Query(None, pattern="^(all|7days|30days|90days|1year)$"),
    sort_by: str | None = "uploaded_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    """
    List all documents with filtering and pagination.

    Args:
        page: Page number (1-based)
        page_size: Items per page (max 100)
        type: Filter by document type (lease, financial, legal, due_diligence, photo, other)
        property_id: Filter by property ID
        search: Search term for name/description
        date_range: Filter by upload date (all, 7days, 30days, 90days, 1year)
        sort_by: Field to sort by
        sort_order: Sort direction (asc/desc)
    """
    skip = (page - 1) * page_size
    order_desc = sort_order.lower() == "desc"

    # Get filtered documents from database
    items = await document_crud.get_filtered(
        db,
        skip=skip,
        limit=page_size,
        doc_type=type,
        property_id=property_id,
        search_term=search,
        date_range=date_range,
        order_by=sort_by or "uploaded_at",
        order_desc=order_desc,
    )

    # Get total count for pagination
    total = await document_crud.count_filtered(
        db,
        doc_type=type,
        property_id=property_id,
        search_term=search,
        date_range=date_range,
    )

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=DocumentStats)
async def get_document_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get document statistics.

    Returns aggregate statistics about documents including:
    - Total document count
    - Total storage size
    - Breakdown by document type
    - Recent uploads count (last 30 days)
    """
    stats = await document_crud.get_stats(db)

    return DocumentStats(
        total_documents=stats["total_documents"],
        total_size=stats["total_size"],
        by_type=stats["by_type"],
        recent_uploads=stats["recent_uploads"],
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific document by ID.
    """
    doc = await document_crud.get(db, document_id)

    if not doc or doc.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return doc


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new document metadata entry.

    This endpoint creates document metadata without file upload.
    Use POST /upload for file upload with metadata.
    """
    # Create document in database
    new_doc = await document_crud.create(db, obj_in=document_data)

    logger.info(f"Created document: {new_doc.name} (ID: {new_doc.id})")

    return new_doc


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile,
    property_id: str | None = None,
    property_name: str | None = None,
    type: str = Query(
        "other", pattern="^(lease|financial|legal|due_diligence|photo|other)$"
    ),
    description: str | None = None,
    tags: str | None = None,  # Comma-separated tags
    uploaded_by: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document file with metadata.

    Note: File storage is not yet implemented. This endpoint currently
    saves metadata only. File content will be stored when storage
    backend is configured.
    """
    # Parse tags from comma-separated string
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    # Get file size
    file_content = await file.read()
    file_size = len(file_content)

    # Create document data
    document_data = DocumentCreate(
        name=file.filename or "untitled",
        type=type,
        property_id=property_id,
        property_name=property_name,
        size=file_size,
        mime_type=file.content_type,
        uploaded_by=uploaded_by,
        description=description,
        tags=tag_list,
        # Note: url and file_path will be set when storage is implemented
    )

    # Create document in database
    new_doc = await document_crud.create(db, obj_in=document_data)

    logger.info(
        f"Uploaded document: {new_doc.name} (ID: {new_doc.id}, size: {file_size})"
    )

    return DocumentUploadResponse(
        document=new_doc,
        message=f"Document '{file.filename}' uploaded successfully. Note: File storage not yet implemented.",
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Download a document file.

    Note: File storage is not yet implemented. Returns 501 Not Implemented.
    """
    doc = await document_crud.get(db, document_id)

    if not doc or doc.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # File storage not yet implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="File download not yet implemented. Storage backend required.",
    )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update document metadata.
    """
    existing = await document_crud.get(db, document_id)

    if not existing or existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Update document in database
    updated_doc = await document_crud.update(db, db_obj=existing, obj_in=document_data)

    logger.info(f"Updated document: {document_id}")

    return updated_doc


@router.patch("/{document_id}", response_model=DocumentResponse)
async def patch_document(
    document_id: int,
    document_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update document metadata.
    """
    existing = await document_crud.get(db, document_id)

    if not existing or existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Update document in database
    updated_doc = await document_crud.update(db, db_obj=existing, obj_in=document_data)

    logger.info(f"Patched document: {document_id}")

    return updated_doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete a document.

    The document is marked as deleted but not permanently removed.
    """
    existing = await document_crud.get(db, document_id)

    if not existing or existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    await document_crud.soft_delete(db, id=document_id)

    logger.info(f"Deleted document: {document_id}")
    return None


@router.get("/property/{property_id}", response_model=DocumentListResponse)
async def get_documents_by_property(
    property_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all documents for a specific property.
    """
    skip = (page - 1) * page_size

    items = await document_crud.get_by_property(
        db,
        property_id=property_id,
        skip=skip,
        limit=page_size,
    )

    total = await document_crud.count_filtered(
        db,
        property_id=property_id,
    )

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
