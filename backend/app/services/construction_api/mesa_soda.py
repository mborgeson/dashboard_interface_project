"""
Mesa, AZ Building Permits — Socrata Open Data API (SODA) client.

Fetches multifamily building permit data from the City of Mesa's
open data portal via the Socrata SODA API.

API endpoint: https://data.mesaaz.gov/resource/{dataset_id}.json
Filter: permits for residential with 5+ units
"""

from datetime import UTC, date, datetime

import httpx
import structlog

from app.models.construction import ConstructionPermitData, ConstructionSourceLog

logger = structlog.get_logger(__name__)

# Default Mesa SODA dataset ID for building permits
DEFAULT_MESA_DATASET_ID = "h2sj-gt3d"

# Mesa SODA API base URL
MESA_SODA_BASE_URL = "https://data.mesaaz.gov/resource"


async def fetch_mesa_permits(
    dataset_id: str | None = None,
    app_token: str | None = None,
    limit: int = 5000,
    months_back: int = 36,
) -> dict:
    """Fetch building permit data from Mesa's SODA API.

    Args:
        dataset_id: Socrata dataset identifier. Defaults to building permits.
        app_token: Optional Socrata app token (increases rate limit).
        limit: Maximum records to fetch per request.
        months_back: How far back to fetch.

    Returns:
        Dict with 'records' (list of dicts) and 'errors'.
    """
    if dataset_id is None:
        dataset_id = DEFAULT_MESA_DATASET_ID

    url = f"{MESA_SODA_BASE_URL}/{dataset_id}.json"

    cutoff = datetime.now(UTC).replace(
        year=datetime.now(UTC).year - (months_back // 12),
        month=max(1, datetime.now(UTC).month - (months_back % 12)),
    )
    cutoff_str = cutoff.strftime("%Y-%m-%dT00:00:00")

    params: dict[str, str | int] = {
        "$limit": limit,
        "$where": (
            f"permit_issue_date > '{cutoff_str}' "
            "AND permit_type = 'BUILDING' "
            "AND work_class LIKE '%MULTI%'"
        ),
        "$order": "permit_issue_date DESC",
    }

    if app_token:
        params["$$app_token"] = app_token

    records: list[dict] = []
    errors: list[str] = []
    status_code = None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            status_code = resp.status_code
            resp.raise_for_status()
            data = resp.json()

        for row in data:
            permit_date_str = row.get("permit_issue_date", "")
            if not permit_date_str:
                continue

            try:
                period_date = date.fromisoformat(permit_date_str[:10])
            except (ValueError, IndexError):
                continue

            address = row.get("address", row.get("site_address", ""))
            permit_number = row.get("permit_number", "")
            description = row.get("description", row.get("work_description", ""))

            records.append(
                {
                    "source": "mesa_soda",
                    "series_id": f"MESA-{permit_number}"
                    if permit_number
                    else "MESA-UNKNOWN",
                    "geography": "Mesa, AZ",
                    "period_date": period_date,
                    "period_type": "permit",
                    "value": 1.0,  # Each record = 1 permit
                    "unit": "permits",
                    "structure_type": "multifamily",
                    "raw_json": row,
                    "address": address,
                    "description": description,
                }
            )

    except httpx.HTTPStatusError as e:
        errors.append(f"Mesa SODA API HTTP error: {e.response.status_code}")
        return {
            "records": [],
            "errors": errors,
            "api_response_code": e.response.status_code,
        }
    except httpx.RequestError as e:
        errors.append(f"Mesa SODA API request error: {e}")
        return {"records": [], "errors": errors, "api_response_code": None}

    logger.info(
        "mesa_soda_fetch_complete",
        records_count=len(records),
        errors_count=len(errors),
    )

    return {
        "records": records,
        "errors": errors,
        "api_response_code": status_code,
    }


def save_mesa_records(
    db_session,
    records: list[dict],
    api_response_code: int | None = None,
    errors: list[str] | None = None,
) -> tuple[int, int]:
    """Save fetched Mesa permit records to the database.

    Uses upsert on (source, series_id, period_date).

    Returns:
        Tuple of (inserted_count, updated_count).
    """
    now = datetime.now(UTC)
    inserted = 0
    updated = 0

    for rec in records:
        existing = (
            db_session.query(ConstructionPermitData)
            .filter(
                ConstructionPermitData.source == rec["source"],
                ConstructionPermitData.series_id == rec["series_id"],
                ConstructionPermitData.period_date == rec["period_date"],
            )
            .first()
        )

        if existing:
            existing.value = rec["value"]
            existing.raw_json = rec.get("raw_json")
            existing.updated_at = now
            updated += 1
        else:
            permit = ConstructionPermitData(
                source=rec["source"],
                series_id=rec["series_id"],
                geography=rec.get("geography"),
                period_date=rec["period_date"],
                period_type=rec["period_type"],
                value=rec["value"],
                unit=rec.get("unit"),
                structure_type=rec.get("structure_type"),
                raw_json=rec.get("raw_json"),
                created_at=now,
                updated_at=now,
            )
            db_session.add(permit)
            inserted += 1

    # Create source log
    source_log = ConstructionSourceLog(
        source_name="mesa_soda",
        fetch_type="api_fetch",
        fetched_at=now,
        records_fetched=len(records),
        records_inserted=inserted,
        records_updated=updated,
        success=not errors,
        error_message="; ".join(errors) if errors else None,
        api_response_code=api_response_code,
        created_at=now,
    )
    db_session.add(source_log)
    db_session.commit()

    return inserted, updated
