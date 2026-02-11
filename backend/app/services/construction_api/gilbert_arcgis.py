"""
Gilbert, AZ Building Permits — ArcGIS REST API client.

Fetches multifamily building permit data from the Town of Gilbert's
ArcGIS-based open data portal.

API endpoint: ArcGIS REST MapServer/FeatureServer query endpoint
"""

from datetime import UTC, date, datetime

import httpx
import structlog

from app.models.construction import ConstructionPermitData, ConstructionSourceLog

logger = structlog.get_logger(__name__)

# Default Gilbert ArcGIS layer URL for building permits
DEFAULT_GILBERT_LAYER_URL = (
    "https://services1.arcgis.com/Gilbert/arcgis/rest/services/"
    "Building_Permits/FeatureServer/0/query"
)


async def fetch_gilbert_permits(
    layer_url: str | None = None,
    months_back: int = 36,
    result_record_count: int = 2000,
) -> dict:
    """Fetch building permit data from Gilbert's ArcGIS REST endpoint.

    Args:
        layer_url: ArcGIS feature layer query URL.
        months_back: How far back to fetch.
        result_record_count: Maximum records per request.

    Returns:
        Dict with 'records' (list of dicts) and 'errors'.
    """
    if layer_url is None:
        layer_url = DEFAULT_GILBERT_LAYER_URL

    cutoff = datetime.now(UTC).replace(
        year=datetime.now(UTC).year - (months_back // 12),
        month=max(1, datetime.now(UTC).month - (months_back % 12)),
    )
    epoch_ms = int(cutoff.timestamp() * 1000)

    params: dict[str, str | int] = {
        "where": (
            f"IssueDate > {epoch_ms} "
            "AND PermitType LIKE '%BUILD%' "
            "AND Description LIKE '%MULTI%'"
        ),
        "outFields": (
            "PermitNum,IssueDate,Address,Description,PermitType,Status,Valuation"
        ),
        "returnGeometry": "false",
        "resultRecordCount": result_record_count,
        "orderByFields": "IssueDate DESC",
        "f": "json",
    }

    records: list[dict] = []
    errors: list[str] = []
    status_code = None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(layer_url, params=params)
            status_code = resp.status_code
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            errors.append(
                f"Gilbert ArcGIS error: {data['error'].get('message', 'Unknown')}"
            )
            return {
                "records": [],
                "errors": errors,
                "api_response_code": status_code,
            }

        features = data.get("features", [])

        for feature in features:
            attrs = feature.get("attributes", {})

            # IssueDate is in epoch milliseconds
            issued_ms = attrs.get("IssueDate")
            if not issued_ms:
                continue

            try:
                period_date = date.fromtimestamp(issued_ms / 1000)
            except (ValueError, OSError):
                continue

            permit_number = attrs.get("PermitNum", "")
            address = attrs.get("Address", "")
            description = attrs.get("Description", "")

            records.append(
                {
                    "source": "gilbert_arcgis",
                    "series_id": (
                        f"GILBERT-{permit_number}"
                        if permit_number
                        else "GILBERT-UNKNOWN"
                    ),
                    "geography": "Gilbert, AZ",
                    "period_date": period_date,
                    "period_type": "permit",
                    "value": 1.0,
                    "unit": "permits",
                    "structure_type": "multifamily",
                    "raw_json": attrs,
                    "address": address,
                    "description": description,
                }
            )

    except httpx.HTTPStatusError as e:
        errors.append(f"Gilbert ArcGIS HTTP error: {e.response.status_code}")
        return {
            "records": [],
            "errors": errors,
            "api_response_code": e.response.status_code,
        }
    except httpx.RequestError as e:
        errors.append(f"Gilbert ArcGIS request error: {e}")
        return {"records": [], "errors": errors, "api_response_code": None}

    logger.info(
        "gilbert_arcgis_fetch_complete",
        records_count=len(records),
        errors_count=len(errors),
    )

    return {
        "records": records,
        "errors": errors,
        "api_response_code": status_code,
    }


def save_gilbert_records(
    db_session,
    records: list[dict],
    api_response_code: int | None = None,
    errors: list[str] | None = None,
) -> tuple[int, int]:
    """Save fetched Gilbert permit records to the database.

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
        source_name="gilbert_arcgis",
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
