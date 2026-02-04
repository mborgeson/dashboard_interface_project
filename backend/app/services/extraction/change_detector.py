"""
Per-Deal Change Detection for Extraction Pipeline

Compares freshly extracted data against the most recent database values
for each deal. Uses SHA-256 hashing of sorted field→value pairs to
determine if a deal's data has changed since the last extraction.

Logic per user requirements:
- Extract data for each deal from Excel
- Compare extracted values hash vs. latest DB values hash
- If identical → skip this deal (no insertion)
- If different → proceed with full bulk_insert of ALL values for this deal
"""

import hashlib
import json
from typing import Any

import numpy as np
import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


def _normalize_value(value: Any) -> str:
    """
    Normalize a value to a stable string representation for hashing.

    Handles NaN, None, floats (rounded to avoid floating-point drift),
    and other types consistently.
    """
    if value is None:
        return "NULL"
    if isinstance(value, float):
        if np.isnan(value):
            return "NaN"
        # Round to 4 decimals to match DB precision (Numeric(20,4))
        return f"{value:.4f}"
    if isinstance(value, int):
        return str(value)
    return str(value)


def compute_extraction_hash(extracted_data: dict[str, Any]) -> str:
    """
    Compute a SHA-256 hash of extracted data for change detection.

    Args:
        extracted_data: Dict of field_name → value from extraction.

    Returns:
        Hex digest of the SHA-256 hash.
    """
    # Sort by field name for deterministic ordering
    # Skip metadata fields (starting with _)
    pairs = sorted(
        (k, _normalize_value(v))
        for k, v in extracted_data.items()
        if not k.startswith("_")
    )
    payload = json.dumps(pairs, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_db_values_hash(db: Session, property_name: str) -> str | None:
    """
    Compute a SHA-256 hash of the latest extracted values in the DB for a property.

    Queries the most recent extraction run's values for this property and
    hashes them in the same way as compute_extraction_hash().

    Args:
        db: Database session.
        property_name: Property/deal name to look up.

    Returns:
        Hex digest if data exists, None if no prior extraction data found.
    """
    # Get the latest extraction run ID that has values for this property
    latest_run_stmt = text("""
        SELECT ev.extraction_run_id
        FROM extracted_values ev
        JOIN extraction_runs er ON ev.extraction_run_id = er.id
        WHERE ev.property_name = :prop_name
          AND er.status = 'completed'
        ORDER BY er.completed_at DESC NULLS LAST, er.created_at DESC
        LIMIT 1
    """)
    result = db.execute(latest_run_stmt, {"prop_name": property_name}).fetchone()

    if not result:
        return None

    run_id = result[0]

    # Get all values for this property from that run
    values_stmt = text("""
        SELECT field_name, value_text
        FROM extracted_values
        WHERE extraction_run_id = :run_id
          AND property_name = :prop_name
          AND field_name NOT LIKE '\\_%'
        ORDER BY field_name
    """)
    rows = db.execute(
        values_stmt, {"run_id": run_id, "prop_name": property_name}
    ).fetchall()

    if not rows:
        return None

    # Build pairs matching the format used by compute_extraction_hash
    pairs = sorted((row[0], row[1] if row[1] is not None else "NULL") for row in rows)
    payload = json.dumps(pairs, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def should_extract_deal(
    db: Session,
    property_name: str,
    extracted_data: dict[str, Any],
) -> tuple[bool, str]:
    """
    Determine whether a deal needs extraction by comparing hashes.

    Args:
        db: Database session.
        property_name: The deal/property name.
        extracted_data: Freshly extracted data dict from Excel.

    Returns:
        Tuple of (should_extract: bool, reason: str).
        - (True, "new_deal") if no prior data exists
        - (True, "data_changed") if data differs from DB
        - (False, "unchanged") if data is identical to DB
    """
    new_hash = compute_extraction_hash(extracted_data)
    db_hash = get_db_values_hash(db, property_name)

    if db_hash is None:
        logger.info(
            "change_detection_new_deal",
            property=property_name,
            hash=new_hash[:12],
        )
        return True, "new_deal"

    if new_hash != db_hash:
        logger.info(
            "change_detection_data_changed",
            property=property_name,
            old_hash=db_hash[:12],
            new_hash=new_hash[:12],
        )
        return True, "data_changed"

    logger.info(
        "change_detection_unchanged",
        property=property_name,
        hash=new_hash[:12],
    )
    return False, "unchanged"
