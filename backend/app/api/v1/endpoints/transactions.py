"""
Transaction endpoints for financial transaction management.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_transaction import transaction as transaction_crud
from app.db.session import get_db
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionSummaryResponse,
    TransactionUpdate,
)

router = APIRouter()


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = None,
    property_id: int | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str | None = "date",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    """
    List all transactions with filtering and pagination.

    Supports filtering by:
    - type: acquisition, disposition, capital_improvement, refinance, distribution
    - property_id: Filter to specific property
    - category: Transaction category
    - date_from/date_to: Date range filter
    """
    skip = (page - 1) * page_size
    order_desc = sort_order.lower() == "desc"

    # Get filtered transactions from database
    items = await transaction_crud.get_filtered(
        db,
        skip=skip,
        limit=page_size,
        transaction_type=type,
        property_id=property_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
        order_by=sort_by or "date",
        order_desc=order_desc,
    )

    # Get total count for pagination
    total = await transaction_crud.count_filtered(
        db,
        transaction_type=type,
        property_id=property_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
    )

    return TransactionListResponse(
        items=items,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=TransactionSummaryResponse)
async def get_transaction_summary(
    property_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get transaction summary statistics.

    Returns counts and totals grouped by type.
    """
    summary = await transaction_crud.get_summary(
        db,
        property_id=property_id,
        date_from=date_from,
        date_to=date_to,
    )

    return TransactionSummaryResponse(
        total_acquisitions=summary["total_acquisitions"],
        total_dispositions=summary["total_dispositions"],
        total_capital_improvements=summary["total_capital_improvements"],
        total_refinances=summary["total_refinances"],
        total_distributions=summary["total_distributions"],
        transaction_count=summary["transaction_count"],
        transactions_by_type=summary["transactions_by_type"],
    )


@router.get("/by-property/{property_id}", response_model=list[TransactionResponse])
async def get_transactions_by_property(
    property_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all transactions for a specific property.
    """
    transactions = await transaction_crud.get_by_property(
        db,
        property_id=property_id,
        skip=skip,
        limit=limit,
    )
    return transactions


@router.get("/by-type/{transaction_type}", response_model=list[TransactionResponse])
async def get_transactions_by_type(
    transaction_type: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all transactions of a specific type.

    Valid types: acquisition, disposition, capital_improvement, refinance, distribution
    """
    valid_types = {
        "acquisition",
        "disposition",
        "capital_improvement",
        "refinance",
        "distribution",
    }
    if transaction_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transaction type: {transaction_type}. Valid types: {', '.join(valid_types)}",
        )

    transactions = await transaction_crud.get_by_type(
        db,
        transaction_type=transaction_type,
        skip=skip,
        limit=limit,
    )
    return transactions


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific transaction by ID.
    """
    transaction = await transaction_crud.get(db, transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    return transaction


@router.post(
    "/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    transaction_data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new transaction.
    """
    new_transaction = await transaction_crud.create(db, obj_in=transaction_data)

    logger.info(
        f"Created transaction: {new_transaction.type} - ${new_transaction.amount:,.2f} "
        f"for {new_transaction.property_name} (ID: {new_transaction.id})"
    )

    return new_transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing transaction.
    """
    existing = await transaction_crud.get(db, transaction_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    updated_transaction = await transaction_crud.update(
        db, db_obj=existing, obj_in=transaction_data
    )

    logger.info(f"Updated transaction: {transaction_id}")

    return updated_transaction


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def patch_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Partially update an existing transaction.
    """
    existing = await transaction_crud.get(db, transaction_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    updated_transaction = await transaction_crud.update(
        db, db_obj=existing, obj_in=transaction_data
    )

    logger.info(f"Patched transaction: {transaction_id}")

    return updated_transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a transaction (soft delete).
    """
    existing = await transaction_crud.get(db, transaction_id)

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    # Perform soft delete
    existing.soft_delete()
    db.add(existing)
    await db.commit()

    logger.info(f"Deleted transaction: {transaction_id}")
    return None
