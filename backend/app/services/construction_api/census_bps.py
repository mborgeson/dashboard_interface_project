"""
Census Building Permits Survey (BPS) API client.

Fetches 5+ unit multifamily permit data for Phoenix MSA (CBSA 38060)
from the Census Bureau's time-series API.

API endpoint: https://api.census.gov/data/timeseries/bps
Series: BLDG5O_UNITS (5+ unit buildings, unit count),
        BLDG_UNITS (total units), BLDG5O_BLDGS (5+ unit buildings, building count)
"""

from datetime import UTC, date, datetime

import httpx
import structlog

from app.models.construction import ConstructionPermitData, ConstructionSourceLog

logger = structlog.get_logger(__name__)

# Census BPS series we're interested in for 5+ unit multifamily
CENSUS_BPS_SERIES = ["BLDG5O_UNITS", "BLDG_UNITS", "BLDG5O_BLDGS"]

# Phoenix-Mesa-Chandler MSA CBSA code
PHOENIX_MSA_CBSA = "38060"

# Census BPS API base URL
CENSUS_BPS_API_URL = "https://api.census.gov/data/timeseries/bps"


async def fetch_census_bps(
    api_key: str,
    months_back: int = 24,
) -> dict:
    """Fetch Census Building Permits Survey data for Phoenix MSA.

    Args:
        api_key: Census API key.
        months_back: Number of months of history to request.

    Returns:
        Dict with 'records' (list of dicts) and 'source_log' metadata.
    """
    records: list[dict] = []
    errors: list[str] = []

    series_str = ",".join(CENSUS_BPS_SERIES)
    params = {
        "get": series_str,
        "for": f"metropolitan statistical area/micropolitan statistical area:{PHOENIX_MSA_CBSA}",
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(CENSUS_BPS_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        if not data or len(data) < 2:
            errors.append("Census BPS API returned empty data")
            return {
                "records": [],
                "errors": errors,
                "api_response_code": resp.status_code,
            }

        # data[0] = header row, data[1:] = data rows
        headers = data[0]
        for row in data[1:]:
            row_dict = dict(zip(headers, row, strict=False))

            # Extract time period — Census BPS returns 'time' as YYYY-MM
            time_str = row_dict.get("time", "")
            if not time_str or len(time_str) < 7:
                continue

            try:
                year = int(time_str[:4])
                month = int(time_str[5:7])
                period_date = date(year, month, 1)
            except (ValueError, IndexError):
                continue

            for series_id in CENSUS_BPS_SERIES:
                val_str = row_dict.get(series_id)
                if val_str is None or val_str == "":
                    continue
                try:
                    value = float(val_str)
                except (ValueError, TypeError):
                    continue

                records.append(
                    {
                        "source": "census_bps",
                        "series_id": series_id,
                        "geography": f"MSA:{PHOENIX_MSA_CBSA}",
                        "period_date": period_date,
                        "period_type": "monthly",
                        "value": value,
                        "unit": "units" if "UNITS" in series_id else "buildings",
                        "structure_type": "5+ units",
                    }
                )

    except httpx.HTTPStatusError as e:
        errors.append(f"Census BPS API HTTP error: {e.response.status_code}")
        return {
            "records": [],
            "errors": errors,
            "api_response_code": e.response.status_code,
        }
    except httpx.RequestError as e:
        errors.append(f"Census BPS API request error: {e}")
        return {"records": [], "errors": errors, "api_response_code": None}

    logger.info(
        "census_bps_fetch_complete",
        records_count=len(records),
        errors_count=len(errors),
    )

    return {
        "records": records,
        "errors": errors,
        "api_response_code": resp.status_code,
    }


def save_census_bps_records(
    db_session,
    records: list[dict],
    api_response_code: int | None = None,
    errors: list[str] | None = None,
) -> tuple[int, int]:
    """Save fetched Census BPS records to the database.

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
        source_name="census_bps",
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
