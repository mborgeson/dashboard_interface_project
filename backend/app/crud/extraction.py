"""
CRUD operations for extraction runs and extracted values.

Provides database operations for:
- Creating and updating extraction runs
- Bulk inserting extracted values
- Querying extraction history and results
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.extraction import ExtractedValue, ExtractionRun


class ExtractionRunCRUD:
    """CRUD operations for ExtractionRun model."""

    @staticmethod
    def create(
        db: Session, trigger_type: str = "manual", files_discovered: int = 0
    ) -> ExtractionRun:
        """Create a new extraction run."""
        run = ExtractionRun(
            trigger_type=trigger_type,
            files_discovered=files_discovered,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def get(db: Session, run_id: UUID) -> ExtractionRun | None:
        """Get extraction run by ID."""
        return db.get(ExtractionRun, run_id)

    @staticmethod
    def get_latest(db: Session) -> ExtractionRun | None:
        """Get most recent extraction run."""
        stmt = select(ExtractionRun).order_by(ExtractionRun.started_at.desc()).limit(1)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_running(db: Session) -> ExtractionRun | None:
        """Get currently running extraction (if any)."""
        stmt = (
            select(ExtractionRun)
            .where(ExtractionRun.status == "running")
            .order_by(ExtractionRun.started_at.desc())
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_recent(
        db: Session, limit: int = 10, offset: int = 0
    ) -> list[ExtractionRun]:
        """List recent extraction runs."""
        stmt = (
            select(ExtractionRun)
            .order_by(ExtractionRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_progress(
        db: Session, run_id: UUID, files_processed: int = 0, files_failed: int = 0
    ) -> ExtractionRun | None:
        """Update extraction run progress."""
        run = db.get(ExtractionRun, run_id)
        if run:
            run.files_processed = files_processed
            run.files_failed = files_failed
            db.commit()
            db.refresh(run)
        return run

    @staticmethod
    def complete(
        db: Session,
        run_id: UUID,
        files_processed: int,
        files_failed: int,
        error_summary: dict | None = None,
    ) -> ExtractionRun | None:
        """Mark extraction run as completed."""
        run = db.get(ExtractionRun, run_id)
        if run:
            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            run.files_processed = files_processed
            run.files_failed = files_failed
            run.error_summary = error_summary
            db.commit()
            db.refresh(run)
        return run

    @staticmethod
    def fail(
        db: Session, run_id: UUID, error_summary: dict | None = None
    ) -> ExtractionRun | None:
        """Mark extraction run as failed."""
        run = db.get(ExtractionRun, run_id)
        if run:
            run.status = "failed"
            run.completed_at = datetime.now(UTC)
            run.error_summary = error_summary
            db.commit()
            db.refresh(run)
        return run

    @staticmethod
    def cancel(db: Session, run_id: UUID) -> ExtractionRun | None:
        """Cancel a running extraction."""
        run = db.get(ExtractionRun, run_id)
        if run and run.status == "running":
            run.status = "cancelled"
            run.completed_at = datetime.now(UTC)
            db.commit()
            db.refresh(run)
        return run


class ExtractedValueCRUD:
    """CRUD operations for ExtractedValue model."""

    @staticmethod
    def bulk_insert(
        db: Session,
        extraction_run_id: UUID,
        extracted_data: dict[str, Any],
        mappings: dict[str, Any],
        property_name: str,
        source_file: str | None = None,
    ) -> int:
        """
        Bulk insert extracted values from a single file extraction.

        Args:
            db: Database session
            extraction_run_id: ID of the extraction run
            extracted_data: Dict of field_name -> value from extraction
            mappings: Dict of field_name -> CellMapping objects
            property_name: Name of the property extracted
            source_file: Path to source file

        Returns:
            Number of values inserted
        """
        values_to_insert = []

        for field_name, value in extracted_data.items():
            # Skip metadata fields
            if field_name.startswith("_"):
                continue

            # Get mapping info if available
            mapping = mappings.get(field_name)

            # Determine value types
            value_text = None
            value_numeric = None
            value_date = None
            is_error = False

            # Handle NaN values
            if value is None or (isinstance(value, float) and np.isnan(value)):
                is_error = True
                value_text = None
            elif isinstance(value, int | float):
                value_numeric = float(value)
                value_text = str(value)
            elif isinstance(value, datetime):
                value_date = value
                value_text = value.isoformat()
            else:
                value_text = str(value)

            values_to_insert.append(
                {
                    "extraction_run_id": extraction_run_id,
                    "property_name": property_name,
                    "field_name": field_name,
                    "field_category": mapping.category if mapping else None,
                    "sheet_name": mapping.sheet_name if mapping else None,
                    "cell_address": mapping.cell_address if mapping else None,
                    "value_text": value_text,
                    "value_numeric": value_numeric,
                    "value_date": value_date,
                    "is_error": is_error,
                    "source_file": source_file,
                }
            )

        # Bulk insert with conflict handling
        if values_to_insert:
            stmt = insert(ExtractedValue).values(values_to_insert)
            # On conflict, update the values (upsert behavior)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_extracted_value",
                set_={
                    "value_text": stmt.excluded.value_text,
                    "value_numeric": stmt.excluded.value_numeric,
                    "value_date": stmt.excluded.value_date,
                    "is_error": stmt.excluded.is_error,
                    "updated_at": datetime.now(UTC),
                },
            )
            db.execute(stmt)
            db.commit()

        return len(values_to_insert)

    @staticmethod
    def get_by_property(
        db: Session, property_name: str, extraction_run_id: UUID | None = None
    ) -> list[ExtractedValue]:
        """Get all extracted values for a property."""
        stmt = select(ExtractedValue).where(
            ExtractedValue.property_name == property_name
        )
        if extraction_run_id:
            stmt = stmt.where(ExtractedValue.extraction_run_id == extraction_run_id)
        stmt = stmt.order_by(ExtractedValue.field_name)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_property_summary(
        db: Session, property_name: str, extraction_run_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get summary of extracted data for a property as dict."""
        values = ExtractedValueCRUD.get_by_property(
            db, property_name, extraction_run_id
        )
        return {v.field_name: v.value for v in values}

    @staticmethod
    def get_extraction_stats(db: Session, extraction_run_id: UUID) -> dict[str, Any]:
        """Get statistics for an extraction run."""
        # Total values
        total_stmt = select(func.count(ExtractedValue.id)).where(
            ExtractedValue.extraction_run_id == extraction_run_id
        )
        total = db.execute(total_stmt).scalar_one()

        # Error count
        error_stmt = select(func.count(ExtractedValue.id)).where(
            and_(
                ExtractedValue.extraction_run_id == extraction_run_id,
                ExtractedValue.is_error.is_(True),
            )
        )
        errors = db.execute(error_stmt).scalar_one()

        # Unique properties
        props_stmt = select(
            func.count(func.distinct(ExtractedValue.property_name))
        ).where(ExtractedValue.extraction_run_id == extraction_run_id)
        properties = db.execute(props_stmt).scalar_one()

        return {
            "total_values": total,
            "error_count": errors,
            "success_count": total - errors,
            "success_rate": (
                round((total - errors) / total * 100, 1) if total > 0 else 0
            ),
            "unique_properties": properties,
        }

    @staticmethod
    def list_properties(
        db: Session, extraction_run_id: UUID | None = None
    ) -> list[str]:
        """List all property names with extracted values."""
        stmt = select(func.distinct(ExtractedValue.property_name))
        if extraction_run_id:
            stmt = stmt.where(ExtractedValue.extraction_run_id == extraction_run_id)
        stmt = stmt.order_by(ExtractedValue.property_name)
        return list(db.execute(stmt).scalars().all())
