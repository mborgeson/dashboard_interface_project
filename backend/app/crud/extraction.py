"""
CRUD operations for extraction runs and extracted values.

Provides database operations for:
- Creating and updating extraction runs
- Bulk inserting extracted values
- Querying extraction history and results
"""

import contextlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import numpy as np
from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealStage
from app.models.extraction import ExtractedValue, ExtractionRun
from app.models.property import Property

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
    unlinked: list[str] = list(
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

    if not unlinked:
        # Still need to handle stage updates even if nothing is unlinked
        stages_updated = _batch_update_deal_stages(db, stages)
        db.commit()
        return {
            "properties_created": 0,
            "deals_created": 0,
            "properties_linked": 0,
            "stages_updated": stages_updated,
        }

    # ── Pre-fetch all existing properties in bulk ──
    # Build OR conditions for all unlinked names
    name_conditions = []
    for prop_name in unlinked:
        name_conditions.append(func.lower(Property.name) == func.lower(prop_name))
        name_conditions.append(
            func.lower(Property.name).like(func.lower(prop_name) + " (%")
        )

    existing_props_rows = db.execute(
        select(Property.id, Property.name).where(or_(*name_conditions))
    ).all()

    # Build a lookup: lowercase-name -> property_id (for exact and prefix match)
    existing_lookup: dict[str, int] = {}
    for pid, pname in existing_props_rows:
        existing_lookup[pname.lower()] = pid

    # ── Pre-fetch all extracted field values for unlinked properties in bulk ──
    _SYNC_FIELDS = [
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

    bulk_field_rows = db.execute(
        select(
            ExtractedValue.property_name,
            ExtractedValue.field_name,
            ExtractedValue.value_text,
            ExtractedValue.value_numeric,
        ).where(
            and_(
                ExtractedValue.extraction_run_id == extraction_run_id,
                ExtractedValue.property_name.in_(unlinked),
                ExtractedValue.field_name.in_(_SYNC_FIELDS),
            )
        )
    ).all()

    # Group field values by property name
    fields_by_prop: dict[str, dict[str, Any]] = defaultdict(dict)
    for pname, fname, vtext, vnumeric in bulk_field_rows:
        fields_by_prop[pname][fname] = vnumeric if vnumeric is not None else vtext

    created_properties = 0
    created_deals = 0
    linked = 0

    for prop_name in unlinked:
        # Try to find existing property via the pre-fetched lookup
        prop_id: int | None = None
        prop_name_lower = prop_name.lower()
        for existing_name_lower, existing_pid in existing_lookup.items():
            if existing_name_lower == prop_name_lower or existing_name_lower.startswith(
                f"{prop_name_lower} ("
            ):
                prop_id = existing_pid
                break

        if prop_id is None:
            # Create new Property + Deal using pre-fetched fields
            fields = fields_by_prop.get(prop_name, {})

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

            # Determine deal stage from folder structure or default to dead
            # (new imports without an explicit stage are unreviewed — default dead,
            # not initial_review, to avoid polluting the kanban board)
            deal_stage = DealStage.DEAD
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
    stages_updated = _batch_update_deal_stages(db, stages)

    db.commit()

    return {
        "properties_created": created_properties,
        "deals_created": created_deals,
        "properties_linked": linked,
        "stages_updated": stages_updated,
    }


def _batch_update_deal_stages(db: Session, stages: dict[str, str]) -> int:
    """Batch-update deal stages from a property_name -> stage_str mapping.

    Pre-fetches all matching deals in a single query instead of one query
    per property name.

    Returns the number of deals whose stage was changed.
    """
    if not stages:
        return 0

    # Validate stage values and filter to valid ones
    valid_stages: dict[str, DealStage] = {}
    for prop_name, stage_str in stages.items():
        try:
            valid_stages[prop_name] = DealStage(stage_str)
        except ValueError:
            continue

    if not valid_stages:
        return 0

    # Build OR conditions for all property names at once
    name_conditions = []
    for prop_name in valid_stages:
        name_conditions.append(func.lower(Deal.name) == func.lower(prop_name))
        name_conditions.append(
            func.lower(Deal.name).like(func.lower(prop_name) + " (%")
        )

    all_deals = list(
        db.execute(select(Deal).where(or_(*name_conditions))).scalars().all()
    )

    stages_updated = 0
    for deal in all_deals:
        deal_name_lower = deal.name.lower() if deal.name else ""
        for prop_name, target_stage in valid_stages.items():
            prop_lower = prop_name.lower()
            if deal_name_lower == prop_lower or deal_name_lower.startswith(
                f"{prop_lower} ("
            ):
                if deal.stage != target_stage:
                    deal.stage = target_stage
                    stages_updated += 1
                break

    return stages_updated


# ── Field-name → property column mapping ────────────────────────────────────

_EXTRACTED_FIELD_MAP: dict[str, str] = {
    "PURCHASE_PRICE": "purchase_price",
    "TOTAL_UNITS": "total_units",
    "YEAR_BUILT": "year_built",
    "TOTAL_SF": "total_sf",
    "GOING_IN_CAP_RATE": "cap_rate",
    "PROPERTY_ADDRESS": "address",
}

# Fields that go into financial_data JSON
_FINANCIAL_DATA_FIELDS: set[str] = {
    "PURCHASE_PRICE",
    "PRICE_PER_UNIT",
    "TOTAL_UNITS",
    "YEAR_BUILT",
    "TOTAL_SF",
    "GOING_IN_CAP_RATE",
    "T3_RETURN_ON_COST",
    "INTEREST_RATE",
    "LOAN_AMOUNT",
    "LOAN_TO_VALUE",
    "EQUITY",
    "LOAN_TERM",
    "AMORTIZATION",
    "IO_PERIOD",
    "DEBT_SERVICE_ANNUAL",
    "LEVERED_RETURNS_IRR",
    "LEVERED_RETURNS_MOIC",
    "UNLEVERED_RETURNS_IRR",
    "UNLEVERED_RETURNS_MOIC",
    "NOI",
    "NOI_PER_UNIT",
    "EFFECTIVE_GROSS_INCOME",
    "NET_RENTAL_INCOME",
    "TOTAL_REVENUE",
    "TOTAL_EXPENSES",
    "VACANCY_RATE",
    "AVG_RENT_PER_UNIT",
    "AVG_RENT_PER_SF",
    "OCCUPANCY_PERCENT",
}


def _safe_float(val: Any) -> float | None:
    """Safely convert to float, returning None on failure."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _dec(val: Any, places: int = 2) -> Decimal | None:
    """Convert to Decimal for SQLAlchemy Numeric columns."""
    f = _safe_float(val)
    return Decimal(str(round(f, places))) if f is not None else None


def _apply_hydration(
    prop: Property, field_values: dict[str, float | str | None]
) -> bool:
    """Apply extracted field values to a Property, updating columns and
    financial_data JSON. Returns True if any field was changed."""
    changed = False

    # Update direct columns
    pp = _safe_float(field_values.get("PURCHASE_PRICE"))
    if pp is not None and not prop.purchase_price:
        prop.purchase_price = _dec(pp, 2)
        changed = True

    units_f = _safe_float(field_values.get("TOTAL_UNITS"))
    if units_f is not None and units_f > 0 and not prop.total_units:
        prop.total_units = int(units_f)
        changed = True

    # Fallback: derive units from financial_data purchasePrice / pricePerUnit
    if not prop.total_units:
        fd_acq = (prop.financial_data or {}).get("acquisition", {})
        fd_pp = fd_acq.get("purchasePrice") or 0
        fd_ppu = fd_acq.get("pricePerUnit") or 0
        if fd_pp > 0 and fd_ppu > 0:
            prop.total_units = round(fd_pp / fd_ppu)
            changed = True

    yb = _safe_float(field_values.get("YEAR_BUILT"))
    if yb is not None and not prop.year_built:
        prop.year_built = int(yb)
        changed = True

    sf = _safe_float(field_values.get("TOTAL_SF"))
    if sf is not None and not prop.total_sf:
        prop.total_sf = int(sf)
        changed = True

    cap = _safe_float(field_values.get("GOING_IN_CAP_RATE"))
    if cap is not None and not prop.cap_rate:
        prop.cap_rate = _dec(cap, 6)
        changed = True

    addr = field_values.get("PROPERTY_ADDRESS")
    if addr and (not prop.address or prop.address == "TBD"):
        prop.address = str(addr)
        changed = True

    # Compute and set NOI per unit
    noi_total = _safe_float(field_values.get("NOI"))
    noi_per_unit = _safe_float(field_values.get("NOI_PER_UNIT"))
    if noi_per_unit and not prop.noi:
        prop.noi = _dec(noi_per_unit, 2)
        changed = True
    elif noi_total and prop.total_units and not prop.noi:
        prop.noi = _dec(noi_total / prop.total_units, 2)
        changed = True

    occ = _safe_float(field_values.get("OCCUPANCY_PERCENT"))
    if occ and not prop.occupancy_rate:
        prop.occupancy_rate = _dec(occ, 4)
        changed = True

    avg_rent = _safe_float(field_values.get("AVG_RENT_PER_UNIT"))
    if avg_rent and not prop.avg_rent_per_unit:
        prop.avg_rent_per_unit = _dec(avg_rent, 2)
        changed = True

    avg_rent_sf = _safe_float(field_values.get("AVG_RENT_PER_SF"))
    if avg_rent_sf and not prop.avg_rent_per_sf:
        prop.avg_rent_per_sf = _dec(avg_rent_sf, 4)
        changed = True

    # Set current_value to purchase_price if missing
    if not prop.current_value and prop.purchase_price:
        prop.current_value = prop.purchase_price
        changed = True

    # Build financial_data JSON
    fd = dict(prop.financial_data) if prop.financial_data else {}
    acq = fd.get("acquisition", {})
    fin = fd.get("financing", {})
    ret = fd.get("returns", {})
    ops = fd.get("operations", {})

    # Acquisition
    if pp is not None and not acq.get("purchasePrice"):
        acq["purchasePrice"] = round(pp, 2)
    ppu = _safe_float(field_values.get("PRICE_PER_UNIT"))
    if ppu is not None and not acq.get("pricePerUnit"):
        acq["pricePerUnit"] = round(ppu, 2)
    eq = _safe_float(field_values.get("EQUITY"))
    if eq is not None:
        acq["totalAcquisitionBudget"] = acq.get("totalAcquisitionBudget") or round(
            pp or 0, 2
        )

    # Financing
    la = _safe_float(field_values.get("LOAN_AMOUNT"))
    if la is not None and not fin.get("loanAmount"):
        fin["loanAmount"] = round(la, 2)
    ltv = _safe_float(field_values.get("LOAN_TO_VALUE"))
    if ltv is not None and not fin.get("ltv"):
        fin["ltv"] = round(ltv, 4)
    ir = _safe_float(field_values.get("INTEREST_RATE"))
    if ir is not None and not fin.get("interestRate"):
        fin["interestRate"] = round(ir, 6)
    lt = _safe_float(field_values.get("LOAN_TERM"))
    if lt is not None and not fin.get("loanTermMonths"):
        fin["loanTermMonths"] = int(lt * 12) if lt < 40 else int(lt)
    amort = _safe_float(field_values.get("AMORTIZATION"))
    if amort is not None and not fin.get("amortizationMonths"):
        fin["amortizationMonths"] = int(amort * 12) if amort < 50 else int(amort)
    ds = _safe_float(field_values.get("DEBT_SERVICE_ANNUAL"))
    if ds is not None and not fin.get("annualDebtService"):
        fin["annualDebtService"] = round(ds, 2)

    # Returns
    lirr = _safe_float(field_values.get("LEVERED_RETURNS_IRR"))
    if lirr is not None and not ret.get("leveredIrr"):
        ret["leveredIrr"] = round(lirr, 6)
        ret["lpIrr"] = round(lirr, 6)
    lmoic = _safe_float(field_values.get("LEVERED_RETURNS_MOIC"))
    if lmoic is not None and not ret.get("leveredMoic"):
        ret["leveredMoic"] = round(lmoic, 4)
        ret["lpMoic"] = round(lmoic, 4)
    uirr = _safe_float(field_values.get("UNLEVERED_RETURNS_IRR"))
    if uirr is not None and not ret.get("unleveredIrr"):
        ret["unleveredIrr"] = round(uirr, 6)
    umoic = _safe_float(field_values.get("UNLEVERED_RETURNS_MOIC"))
    if umoic is not None and not ret.get("unleveredMoic"):
        ret["unleveredMoic"] = round(umoic, 4)

    # Operations
    egi = _safe_float(field_values.get("EFFECTIVE_GROSS_INCOME"))
    if egi is not None and not ops.get("totalRevenueYear1"):
        ops["totalRevenueYear1"] = round(egi, 2)
    nri = _safe_float(field_values.get("NET_RENTAL_INCOME"))
    if nri is not None and not ops.get("netRentalIncomeYear1"):
        ops["netRentalIncomeYear1"] = round(nri, 2)
    noi_val = _safe_float(field_values.get("NOI"))
    if noi_val is not None and not ops.get("noiYear1"):
        ops["noiYear1"] = round(noi_val, 2)
    tex = _safe_float(field_values.get("TOTAL_EXPENSES"))
    if tex is not None and not ops.get("totalExpensesYear1"):
        ops["totalExpensesYear1"] = round(tex, 2)
    if occ is not None and not ops.get("occupancy"):
        ops["occupancy"] = round(occ, 4)
    if avg_rent is not None and not ops.get("avgRentPerUnit"):
        ops["avgRentPerUnit"] = round(avg_rent, 2)
    if avg_rent_sf is not None and not ops.get("avgRentPerSf"):
        ops["avgRentPerSf"] = round(avg_rent_sf, 4)

    new_fd: dict[str, Any] = {}
    if acq:
        new_fd["acquisition"] = acq
    if fin:
        new_fd["financing"] = fin
    if ret:
        new_fd["returns"] = ret
    if ops:
        new_fd["operations"] = ops

    if new_fd and new_fd != (prop.financial_data or {}):
        prop.financial_data = new_fd
        changed = True

    return changed


def hydrate_properties_from_extracted(db: Session) -> dict[str, Any]:
    """
    Populate properties table columns and financial_data JSON from
    the latest extracted_values for each property.

    For each property, finds the most recent non-null extracted value
    per field_name and uses it to fill in missing data.

    Uses bulk queries to avoid N+1: fetches all relevant extracted values
    in a single query, then groups them by property_name in Python.

    Returns summary of updated records.
    """
    # Get all properties
    all_props: list[Property] = list(db.execute(select(Property)).scalars().all())
    if not all_props:
        return {"total_properties": 0, "properties_updated": 0}

    # Build name variants for all properties
    # Map: variant (lowercase) -> list of Property objects
    variant_to_props: dict[str, list[Property]] = defaultdict(list)
    all_target_fields = list(_FINANCIAL_DATA_FIELDS) + list(_EXTRACTED_FIELD_MAP.keys())

    for prop in all_props:
        if not prop.name:
            continue
        full_lower = prop.name.lower()
        variant_to_props[full_lower].append(prop)
        short_name = prop.name.split("(")[0].strip()
        if short_name and short_name != prop.name:
            variant_to_props[short_name.lower()].append(prop)

    # ── Single bulk query for ALL extracted values across all properties ──
    # Build OR conditions for all name variants
    name_conditions = []
    all_variant_names = list(variant_to_props.keys())
    for variant in all_variant_names:
        name_conditions.append(func.lower(ExtractedValue.property_name) == variant)
        name_conditions.append(
            func.lower(ExtractedValue.property_name).like(variant + " (%")
        )

    if not name_conditions:
        return {"total_properties": len(all_props), "properties_updated": 0}

    bulk_rows = db.execute(
        select(
            ExtractedValue.property_name,
            ExtractedValue.field_name,
            ExtractedValue.value_numeric,
            ExtractedValue.value_text,
        )
        .where(
            and_(
                or_(*name_conditions),
                ExtractedValue.is_error.is_(False),
                ExtractedValue.field_name.in_(all_target_fields),
            )
        )
        .order_by(
            ExtractedValue.property_name,
            ExtractedValue.field_name,
            ExtractedValue.created_at.desc(),
        )
    ).all()

    # Group extracted values by property_name (lowercase)
    # Keep first occurrence per (property_name, field_name) since ordered by
    # created_at DESC
    values_by_ev_name: dict[str, dict[str, float | str | None]] = defaultdict(dict)
    for ev_pname, ev_fname, ev_vnumeric, ev_vtext in bulk_rows:
        ev_key = ev_pname.lower()
        if ev_fname not in values_by_ev_name[ev_key]:
            values_by_ev_name[ev_key] = values_by_ev_name.get(ev_key, {})
            if ev_fname not in values_by_ev_name[ev_key]:
                values_by_ev_name[ev_key][ev_fname] = (
                    ev_vnumeric if ev_vnumeric is not None else ev_vtext
                )

    # Match extracted values back to properties
    updated = 0
    for prop in all_props:
        if not prop.name:
            continue

        # Try full name first, then short name
        full_lower = prop.name.lower()
        short_name = prop.name.split("(")[0].strip().lower()

        field_values: dict[str, float | str | None] = {}

        # Check direct match on full name
        if full_lower in values_by_ev_name:
            field_values = values_by_ev_name[full_lower]
        elif short_name and short_name != full_lower:
            # Check short name match
            if short_name in values_by_ev_name:
                field_values = values_by_ev_name[short_name]
            else:
                # Check prefix matches: any ev_name that starts with short_name + " ("
                for ev_name, ev_fields in values_by_ev_name.items():
                    if ev_name.startswith(f"{short_name} ("):
                        field_values = ev_fields
                        break
        else:
            # Check prefix matches for full name
            for ev_name, ev_fields in values_by_ev_name.items():
                if ev_name.startswith(f"{full_lower} ("):
                    field_values = ev_fields
                    break

        if not field_values:
            continue

        if _apply_hydration(prop, field_values):
            updated += 1

    db.commit()
    logger.info(
        f"hydrate_properties_complete: updated={updated}, total={len(all_props)}"
    )

    return {
        "total_properties": len(all_props),
        "properties_updated": updated,
    }
