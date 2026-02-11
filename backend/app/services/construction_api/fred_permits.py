"""
FRED API client for Phoenix MSA building permit series.

Fetches time-series observations from FRED for:
  - PHOE004BPPRIVSA: Total private building permits, Phoenix MSA (SA)
  - PHOE004BP1FHSA: Single-family permits, Phoenix MSA (SA)
  - BPPRIV004013: Private building permits, Maricopa County

API endpoint: https://api.stlouisfed.org/fred/series/observations
"""

from datetime import UTC, date, datetime

import httpx
import structlog

from app.models.construction import ConstructionPermitData, ConstructionSourceLog

logger = structlog.get_logger(__name__)

# FRED series IDs for Phoenix MSA building permits
FRED_PERMIT_SERIES = [
    "PHOE004BPPRIVSA",  # Total private permits, Phoenix MSA (SA)
    "PHOE004BP1FHSA",  # Single-family permits, Phoenix MSA (SA)
    "BPPRIV004013",  # Private permits, Maricopa County
]

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"


async def fetch_fred_permits(
    api_key: str,
    series_ids: list[str] | None = None,
    observation_start: str | None = None,
) -> dict:
    """Fetch FRED building permit observations.

    Args:
        api_key: FRED API key.
        series_ids: List of FRED series IDs. Defaults to FRED_PERMIT_SERIES.
        observation_start: Earliest observation date (YYYY-MM-DD).
            Defaults to 24 months ago.

    Returns:
        Dict with 'records' (list of dicts) and 'errors'.
    """
    if series_ids is None:
        series_ids = FRED_PERMIT_SERIES

    if observation_start is None:
        two_years_ago = datetime.now(UTC).replace(year=datetime.now(UTC).year - 2)
        observation_start = two_years_ago.strftime("%Y-%m-%d")

    records: list[dict] = []
    errors: list[str] = []
    last_status_code = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        for series_id in series_ids:
            params = {
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": observation_start,
            }

            try:
                resp = await client.get(FRED_API_URL, params=params)
                last_status_code = resp.status_code
                resp.raise_for_status()
                data = resp.json()

                observations = data.get("observations", [])
                for obs in observations:
                    date_str = obs.get("date", "")
                    value_str = obs.get("value", "")

                    if not date_str or value_str == ".":
                        continue

                    try:
                        period_date = date.fromisoformat(date_str)
                        value = float(value_str)
                    except (ValueError, TypeError):
                        continue

                    records.append(
                        {
                            "source": "fred",
                            "series_id": series_id,
                            "geography": "Phoenix MSA",
                            "period_date": period_date,
                            "period_type": "monthly",
                            "value": value,
                            "unit": "permits",
                            "structure_type": None,
                        }
                    )

            except httpx.HTTPStatusError as e:
                errors.append(
                    f"FRED API error for {series_id}: {e.response.status_code}"
                )
            except httpx.RequestError as e:
                errors.append(f"FRED API request error for {series_id}: {e}")

    logger.info(
        "fred_permits_fetch_complete",
        records_count=len(records),
        series_count=len(series_ids),
        errors_count=len(errors),
    )

    return {
        "records": records,
        "errors": errors,
        "api_response_code": last_status_code,
    }


def save_fred_records(
    db_session,
    records: list[dict],
    api_response_code: int | None = None,
    errors: list[str] | None = None,
) -> tuple[int, int]:
    """Save fetched FRED records to the database.

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
                created_at=now,
                updated_at=now,
            )
            db_session.add(permit)
            inserted += 1

    # Create source log
    source_log = ConstructionSourceLog(
        source_name="fred_permits",
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
