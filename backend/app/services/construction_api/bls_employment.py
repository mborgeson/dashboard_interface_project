"""
BLS API client for Phoenix MSA construction employment data.

Fetches time-series employment data from the Bureau of Labor Statistics:
  - SMU04380602000000001: Total construction employment, Phoenix MSA
  - CES2000000001: National construction employment (for comparison)

API endpoint: https://api.bls.gov/publicAPI/v2/timeseries/data/
Note: No API key required (25 queries/day limit for v2 without key).
"""

from datetime import UTC, date, datetime

import httpx
import structlog

from app.models.construction import (
    ConstructionEmploymentData,
    ConstructionSourceLog,
)

logger = structlog.get_logger(__name__)

# BLS series IDs for construction employment
BLS_EMPLOYMENT_SERIES = [
    "SMU04380602000000001",  # Construction employment, Phoenix MSA
    "CES2000000001",  # National construction employment
]

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


async def fetch_bls_employment(
    series_ids: list[str] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    api_key: str | None = None,
) -> dict:
    """Fetch BLS construction employment data.

    Args:
        series_ids: List of BLS series IDs. Defaults to BLS_EMPLOYMENT_SERIES.
        start_year: Start year for data. Defaults to 2 years ago.
        end_year: End year. Defaults to current year.
        api_key: Optional BLS API key (increases rate limit from 25 to 500/day).

    Returns:
        Dict with 'records' (list of dicts) and 'errors'.
    """
    if series_ids is None:
        series_ids = BLS_EMPLOYMENT_SERIES

    current_year = datetime.now(UTC).year
    if start_year is None:
        start_year = current_year - 2
    if end_year is None:
        end_year = current_year

    records: list[dict] = []
    errors: list[str] = []
    status_code = None

    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if api_key:
        payload["registrationkey"] = api_key

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(BLS_API_URL, json=payload)
            status_code = resp.status_code
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "REQUEST_SUCCEEDED":
            errors.append(f"BLS API error: {data.get('message', ['Unknown error'])}")
            return {
                "records": [],
                "errors": errors,
                "api_response_code": status_code,
            }

        # BLS month mapping
        month_map = {
            "M01": 1,
            "M02": 2,
            "M03": 3,
            "M04": 4,
            "M05": 5,
            "M06": 6,
            "M07": 7,
            "M08": 8,
            "M09": 9,
            "M10": 10,
            "M11": 11,
            "M12": 12,
        }

        for series in data.get("Results", {}).get("series", []):
            series_id = series.get("seriesID", "")
            for obs in series.get("data", []):
                year = int(obs.get("year", 0))
                period = obs.get("period", "")
                month = month_map.get(period)
                if not month or not year:
                    continue

                try:
                    value = float(obs.get("value", "0"))
                    period_date = date(year, month, 1)
                except (ValueError, TypeError):
                    continue

                records.append(
                    {
                        "series_id": series_id,
                        "series_title": _get_series_title(series_id),
                        "period_date": period_date,
                        "value": value,
                        "period_type": "monthly",
                    }
                )

    except httpx.HTTPStatusError as e:
        errors.append(f"BLS API HTTP error: {e.response.status_code}")
        return {
            "records": [],
            "errors": errors,
            "api_response_code": e.response.status_code,
        }
    except httpx.RequestError as e:
        errors.append(f"BLS API request error: {e}")
        return {"records": [], "errors": errors, "api_response_code": None}

    logger.info(
        "bls_employment_fetch_complete",
        records_count=len(records),
        errors_count=len(errors),
    )

    return {
        "records": records,
        "errors": errors,
        "api_response_code": status_code,
    }


def _get_series_title(series_id: str) -> str:
    """Map BLS series ID to a human-readable title."""
    titles = {
        "SMU04380602000000001": "Construction Employment, Phoenix MSA",
        "CES2000000001": "Construction Employment, National",
    }
    return titles.get(series_id, series_id)


def save_bls_records(
    db_session,
    records: list[dict],
    api_response_code: int | None = None,
    errors: list[str] | None = None,
) -> tuple[int, int]:
    """Save fetched BLS employment records to the database.

    Uses upsert on (series_id, period_date).

    Returns:
        Tuple of (inserted_count, updated_count).
    """
    now = datetime.now(UTC)
    inserted = 0
    updated = 0

    for rec in records:
        existing = (
            db_session.query(ConstructionEmploymentData)
            .filter(
                ConstructionEmploymentData.series_id == rec["series_id"],
                ConstructionEmploymentData.period_date == rec["period_date"],
            )
            .first()
        )

        if existing:
            existing.value = rec["value"]
            existing.updated_at = now
            updated += 1
        else:
            emp = ConstructionEmploymentData(
                series_id=rec["series_id"],
                series_title=rec.get("series_title"),
                period_date=rec["period_date"],
                value=rec["value"],
                period_type=rec["period_type"],
                created_at=now,
                updated_at=now,
            )
            db_session.add(emp)
            inserted += 1

    # Create source log
    source_log = ConstructionSourceLog(
        source_name="bls_employment",
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
