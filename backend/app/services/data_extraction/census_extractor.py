"""
Census Bureau Extractor — fetches ACS 5-Year estimates for Phoenix MSA.

Variables:
  B01003_001E — Total Population
  B19013_001E — Median Household Income

Geography: Phoenix-Mesa-Chandler MSA (CBSA 38060)
Range: 2010–2024

Usage:
  python -m app.services.data_extraction.census_extractor
"""

import sys

import httpx
from loguru import logger
from sqlalchemy import create_engine, text

from app.core.config import settings

CENSUS_BASE_URL = "https://api.census.gov/data"
PHOENIX_CBSA = "38060"

VARIABLES = {
    "B01003_001E": "Total Population",
    "B19013_001E": "Median Household Income",
}


def fetch_census_data(
    api_key: str, year: int, variables: list[str]
) -> dict[str, float] | None:
    """Fetch ACS 5-year data for Phoenix MSA for a given year."""
    var_str = ",".join(["NAME"] + variables)
    url = f"{CENSUS_BASE_URL}/{year}/acs/acs5"
    params = {
        "get": var_str,
        "for": f"metropolitan statistical area/micropolitan statistical area:{PHOENIX_CBSA}",
        "key": api_key,
    }

    try:
        response = httpx.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        if len(data) < 2:
            return None

        header = data[0]
        values = data[1]

        result = {}
        for var_code in variables:
            try:
                idx = header.index(var_code)
                val = values[idx]
                if val is not None and str(val) not in ("", "-", "null"):
                    result[var_code] = float(val)
            except (ValueError, IndexError):
                continue

        return result if result else None
    except httpx.HTTPStatusError as e:
        logger.debug(f"Census API {year}: HTTP {e.response.status_code}")
        return None
    except Exception as e:
        logger.debug(f"Census API {year}: {e}")
        return None


def run_census_extraction(engine=None) -> dict:
    """
    Fetch Census Bureau ACS data for Phoenix MSA across all available years.

    Returns extraction summary.
    """
    api_key = settings.CENSUS_API_KEY
    if not api_key:
        logger.error("CENSUS_API_KEY not configured")
        return {"status": "error", "message": "No Census API key"}

    if engine is None:
        db_url = settings.MARKET_ANALYSIS_DB_URL
        if not db_url:
            logger.error("MARKET_ANALYSIS_DB_URL not configured")
            return {"status": "error", "message": "No DB URL configured"}
        engine = create_engine(db_url)

    # Log extraction start
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO extraction_log (source, status) VALUES ('census', 'running') RETURNING id"
            ),
        )
        log_id = result.scalar()

    total_records = 0
    years_processed = 0
    errors = []
    var_codes = list(VARIABLES.keys())

    # ACS 5-year estimates: 2010–2024
    for year in range(2010, 2025):
        try:
            data = fetch_census_data(api_key, year, var_codes)
            if not data:
                continue

            with engine.begin() as conn:
                for var_code, value in data.items():
                    conn.execute(
                        text("""
                            INSERT INTO census_timeseries
                                (variable_code, variable_name, geography, geography_code, year, value, dataset)
                            VALUES
                                (:var_code, :var_name, :geo, :geo_code, :year, :value, 'acs5')
                            ON CONFLICT (variable_code, geography_code, year)
                            DO UPDATE SET value = EXCLUDED.value, imported_at = NOW()
                        """),
                        {
                            "var_code": var_code,
                            "var_name": VARIABLES[var_code],
                            "geo": "Phoenix-Mesa-Chandler, AZ Metro Area",
                            "geo_code": PHOENIX_CBSA,
                            "year": year,
                            "value": value,
                        },
                    )
                    total_records += 1

            years_processed += 1
            logger.info(f"  Census {year}: {len(data)} variables")

        except Exception as e:
            logger.error(f"Error fetching Census {year}: {e}")
            errors.append(f"{year}: {e}")

    # Update extraction log
    status = "success" if not errors else "error"
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE extraction_log
                SET finished_at = NOW(), status = :status, records_upserted = :records,
                    error_message = :errors,
                    details = :details
                WHERE id = :log_id
            """),
            {
                "status": status,
                "records": total_records,
                "errors": "; ".join(errors) if errors else None,
                "details": f'{{"years_processed": {years_processed}}}',
                "log_id": log_id,
            },
        )

    summary = {
        "status": status,
        "years_processed": years_processed,
        "records_upserted": total_records,
        "errors": errors,
    }
    logger.info(f"Census extraction complete: {summary}")
    return summary


if __name__ == "__main__":
    result = run_census_extraction()
    print(result)
    sys.exit(0 if result["status"] == "success" else 1)
