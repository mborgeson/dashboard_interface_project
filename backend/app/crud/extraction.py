"""
CRUD operations for extraction runs and extracted values.

Provides database operations for:
- Creating and updating extraction runs
- Bulk inserting extracted values
- Querying extraction history and results
"""

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import numpy as np
import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealStage
from app.models.extraction import ExtractedValue, ExtractionRun
from app.models.property import Property

logger = structlog.get_logger(__name__)

# Extraction runs older than this are considered stale/crashed
STALE_RUN_TIMEOUT_MINUTES = 30


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
    def get_latest_completed(db: Session) -> ExtractionRun | None:
        """Get most recent completed extraction run."""
        stmt = (
            select(ExtractionRun)
            .where(ExtractionRun.status == "completed")
            .order_by(
                ExtractionRun.completed_at.desc().nullslast(),
                ExtractionRun.started_at.desc(),
            )
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_running(db: Session) -> ExtractionRun | None:
        """Get currently running extraction, auto-failing stale runs.

        If a run has been in "running" status for longer than
        STALE_RUN_TIMEOUT_MINUTES, it is assumed to have crashed
        and is automatically marked as failed.
        """
        stmt = (
            select(ExtractionRun)
            .where(ExtractionRun.status == "running")
            .order_by(ExtractionRun.started_at.desc())
            .limit(1)
        )
        running = db.execute(stmt).scalar_one_or_none()

        if running is not None:
            elapsed = datetime.now(UTC) - running.started_at.replace(tzinfo=UTC)
            if elapsed > timedelta(minutes=STALE_RUN_TIMEOUT_MINUTES):
                running.status = "failed"
                running.completed_at = datetime.now(UTC)
                running.error_summary = {
                    "reason": "Stale extraction run (timed out)",
                    "started_at": running.started_at.isoformat(),
                    "elapsed_minutes": round(elapsed.total_seconds() / 60, 1),
                }
                db.commit()
                db.refresh(running)
                logger.warning(
                    "stale_run_marked_failed",
                    run_id=str(running.id),
                    elapsed_minutes=round(elapsed.total_seconds() / 60, 1),
                )
                return None

        return running

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
        per_file_status: dict | None = None,
        file_metadata: dict | None = None,
    ) -> ExtractionRun | None:
        """Mark extraction run as completed."""
        run = db.get(ExtractionRun, run_id)
        if run:
            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            run.files_processed = files_processed
            run.files_failed = files_failed
            run.error_summary = error_summary
            if per_file_status is not None:
                run.per_file_status = per_file_status
            if file_metadata is not None:
                run.file_metadata = file_metadata
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
        error_categories: dict[str, str] | None = None,
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
            error_categories: Optional dict of field_name -> error category string

        Returns:
            Number of values inserted
        """
        # Resolve property_id from the Property table (if match exists)
        # Try exact match first, then prefix match for "Name (City, ST)" pattern
        prop_row = db.execute(
            select(Property.id)
            .where(
                or_(
                    func.lower(Property.name) == func.lower(property_name),
                    func.lower(Property.name).like(func.lower(property_name) + " (%"),
                )
            )
            .limit(1)
        ).scalar_one_or_none()
        property_id: int | None = prop_row if prop_row is not None else None

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

            # Resolve error_category from the error_categories dict if present
            error_cat = (
                error_categories.get(field_name)
                if error_categories and is_error
                else None
            )

            values_to_insert.append(
                {
                    "extraction_run_id": extraction_run_id,
                    "property_id": property_id,
                    "property_name": property_name,
                    "field_name": field_name,
                    "field_category": mapping.category if mapping else None,
                    "sheet_name": mapping.sheet_name if mapping else None,
                    "cell_address": mapping.cell_address if mapping else None,
                    "value_text": value_text,
                    "value_numeric": value_numeric,
                    "value_date": value_date,
                    "is_error": is_error,
                    "error_category": error_cat,
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
                    "property_id": stmt.excluded.property_id,
                    "value_text": stmt.excluded.value_text,
                    "value_numeric": stmt.excluded.value_numeric,
                    "value_date": stmt.excluded.value_date,
                    "is_error": stmt.excluded.is_error,
                    "error_category": stmt.excluded.error_category,
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


def sync_extracted_to_properties(
    db: Session,
    extraction_run_id: UUID,
    property_stages: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create Property and Deal records for extracted properties that don't
    already exist in the main tables, backfill property_id links, and
    update deal stages based on folder structure.

    Called after extraction completes. For each extracted property_name:
      1. Try to match an existing Property (exact or prefix match).
      2. If no match, create a new Property + Deal using extracted fields.
      3. Update extracted_values.property_id for unlinked rows.
      4. If property_stages provided, update deal stages to match folder.

    Args:
        db: Database session
        extraction_run_id: ID of the extraction run
        property_stages: Optional mapping of property_name -> deal stage value
            from folder structure (e.g., {"Hayden Park": "initial_review"})

    Returns summary of created/linked/updated records.
    """
    stages = property_stages or {}

    # Get distinct property names from this run that have NULL property_id
    unlinked = (
        db.execute(
            select(func.distinct(ExtractedValue.property_name)).where(
                and_(
                    ExtractedValue.extraction_run_id == extraction_run_id,
                    ExtractedValue.property_id.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )

    created_properties = 0
    created_deals = 0
    linked = 0

    for prop_name in unlinked:
        # Try prefix match against existing properties
        existing = db.execute(
            select(Property.id)
            .where(
                or_(
                    func.lower(Property.name) == func.lower(prop_name),
                    func.lower(Property.name).like(func.lower(prop_name) + " (%"),
                )
            )
            .limit(1)
        ).scalar_one_or_none()

        if existing:
            prop_id = existing
        else:
            # Gather field values from this extraction run
            fields = {}
            rows = db.execute(
                select(
                    ExtractedValue.field_name,
                    ExtractedValue.value_text,
                    ExtractedValue.value_numeric,
                ).where(
                    and_(
                        ExtractedValue.extraction_run_id == extraction_run_id,
                        ExtractedValue.property_name == prop_name,
                        ExtractedValue.field_name.in_(
                            [
                                "PROPERTY_NAME",
                                "PROPERTY_CITY",
                                "PROPERTY_STATE",
                                "PROPERTY_ZIP",
                                "TOTAL_UNITS",
                                "UNITS",
                                "PURCHASE_PRICE",
                                "YEAR_BUILT",
                                "MARKET",
                                "SUBMARKET",
                                "TOTAL_SF",
                                "PROPERTY_TYPE",
                            ]
                        ),
                    )
                )
            ).all()
            for fname, vtext, vnumeric in rows:
                fields[fname] = vnumeric if vnumeric is not None else vtext

            city = str(fields.get("PROPERTY_CITY", "")) or "Unknown"
            state = str(fields.get("PROPERTY_STATE", "")) or "AZ"
            display_name = f"{prop_name} ({city}, {state})"
            zip_code = str(fields.get("PROPERTY_ZIP", "")) or "00000"
            # Clean up numeric zip like "85306.0"
            if "." in zip_code:
                zip_code = zip_code.split(".")[0]

            total_units = None
            raw_units = fields.get("TOTAL_UNITS") or fields.get("UNITS")
            if raw_units is not None:
                with contextlib.suppress(ValueError, TypeError):
                    total_units = int(float(raw_units))

            purchase_price = None
            raw_price = fields.get("PURCHASE_PRICE")
            if raw_price is not None:
                with contextlib.suppress(ValueError, TypeError):
                    purchase_price = round(float(raw_price), 2)

            year_built = None
            raw_year = fields.get("YEAR_BUILT")
            if raw_year is not None:
                with contextlib.suppress(ValueError, TypeError):
                    year_built = int(float(raw_year))

            # Determine deal stage from folder structure or default
            deal_stage = DealStage.INITIAL_REVIEW
            if prop_name in stages:
                with contextlib.suppress(ValueError):
                    deal_stage = DealStage(stages[prop_name])

            new_prop = Property(
                name=display_name,
                property_type=str(fields.get("PROPERTY_TYPE", "multifamily")).lower(),
                address="TBD",
                city=city,
                state=state,
                zip_code=zip_code,
                market=str(fields.get("MARKET", "")) or None,
                submarket=str(fields.get("SUBMARKET", "")) or None,
                total_units=total_units,
                purchase_price=purchase_price,
                year_built=year_built,
                data_source="extraction",
            )
            db.add(new_prop)
            db.flush()  # Get the ID
            prop_id = new_prop.id
            created_properties += 1

            new_deal = Deal(
                name=display_name,
                deal_type="acquisition",
                stage=deal_stage,
                property_id=prop_id,
                asking_price=purchase_price,
                priority="medium",
            )
            db.add(new_deal)
            created_deals += 1

        # Backfill property_id on all extracted_values for this property
        db.execute(
            ExtractedValue.__table__.update()  # type: ignore[attr-defined]
            .where(
                and_(
                    ExtractedValue.extraction_run_id == extraction_run_id,
                    ExtractedValue.property_name == prop_name,
                    ExtractedValue.property_id.is_(None),
                )
            )
            .values(property_id=prop_id)
        )
        linked += 1

    # Update deal stages for ALL properties with known stages (not just unlinked)
    stages_updated = 0
    if stages:
        for prop_name, stage_str in stages.items():
            try:
                target_stage = DealStage(stage_str)
            except ValueError:
                continue

            # Find deals matching this property name (exact or prefix)
            matched_deals = (
                db.execute(
                    select(Deal).where(
                        or_(
                            func.lower(Deal.name) == func.lower(prop_name),
                            func.lower(Deal.name).like(func.lower(prop_name) + " (%"),
                        )
                    )
                )
                .scalars()
                .all()
            )

            for deal in matched_deals:
                if deal.stage != target_stage:
                    deal.stage = target_stage
                    stages_updated += 1

    db.commit()

    return {
        "properties_created": created_properties,
        "deals_created": created_deals,
        "properties_linked": linked,
        "stages_updated": stages_updated,
    }
