"""
CoStar Excel Parser — transforms wide-format CoStar exports to normalized DB rows.

Handles both MSA-level and Submarket-level exports.
Column layout (both files):
  A: Property Class Name  (always "Multi-Family")
  B: Slice               (always "All")
  C: As Of               (e.g. "2026 Q1")
  D: Geography Name      (e.g. "Phoenix - AZ USA" or "Phoenix - AZ USA - Tempe")
  E: Geography Code
  F: Property Type
  G: Forecast Scenario
  H: CBSA Code
  I: Geography Type      ("Metro" or "Submarket")
  J: Concept Name        (63 concepts)
  K+: Quarterly data columns  ("1982 Q1", "1982 Q2", ..., "2031 Q1")

Usage:
  python -m app.services.data_extraction.costar_parser
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import openpyxl
from loguru import logger
from sqlalchemy import create_engine, text

from app.core.config import settings

# Quarter string → date mapping
QUARTER_TO_MONTH = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}


def parse_quarter(quarter_str: str) -> datetime | None:
    """Convert '2025 Q1' → datetime(2025, 1, 1)."""
    match = re.match(r"(\d{4})\s+(Q[1-4])", str(quarter_str).strip())
    if not match:
        return None
    year = int(match.group(1))
    month = QUARTER_TO_MONTH[match.group(2)]
    return datetime(year, month, 1)


def _current_quarter_start() -> datetime:
    """Get the start date of the current quarter."""
    now = datetime.now()
    q = (now.month - 1) // 3
    return datetime(now.year, q * 3 + 1, 1)


def parse_costar_file(filepath: str | Path, engine) -> int:
    """
    Parse a single CoStar Excel file and upsert into costar_timeseries.

    Returns number of records upserted.
    """
    filepath = Path(filepath)
    logger.info(f"Parsing CoStar file: {filepath.name}")

    wb = openpyxl.load_workbook(str(filepath), read_only=True, data_only=True)
    ws = wb["DataExport"]

    # Read header row to get date columns
    header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    date_columns: list[tuple[int, datetime, bool]] = []
    current_q = _current_quarter_start()

    for col_idx, cell_val in enumerate(header_row):
        if col_idx < 10:  # Skip metadata columns A-J
            continue
        dt = parse_quarter(str(cell_val) if cell_val else "")
        if dt:
            is_forecast = dt > current_q
            date_columns.append((col_idx, dt, is_forecast))

    logger.info(f"  Found {len(date_columns)} date columns, {ws.max_row - 1} data rows")

    # Process data rows
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        geo_name = str(row[3]).strip() if row[3] else None
        geo_type = str(row[8]).strip() if row[8] else None
        geo_code = str(row[4]).strip() if row[4] else None
        concept = str(row[9]).strip() if row[9] else None

        if not geo_name or not concept:
            continue

        for col_idx, dt, is_forecast in date_columns:
            val = row[col_idx] if col_idx < len(row) else None
            if val is None:
                continue
            try:
                float_val = float(val)
            except (ValueError, TypeError):
                continue

            records.append({
                "geography_name": geo_name,
                "geography_type": geo_type,
                "geography_code": geo_code,
                "concept": concept,
                "date": dt.date(),
                "value": float_val,
                "is_forecast": is_forecast,
                "source_file": filepath.name,
            })

    wb.close()

    if not records:
        logger.warning(f"  No records extracted from {filepath.name}")
        return 0

    # Batch upsert
    upserted = _batch_upsert(engine, records)
    logger.info(f"  Upserted {upserted} records from {filepath.name}")
    return upserted


def _batch_upsert(engine, records: list[dict], batch_size: int = 5000) -> int:
    """Upsert records into costar_timeseries in batches."""
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        with engine.begin() as conn:
            for rec in batch:
                conn.execute(
                    text("""
                        INSERT INTO costar_timeseries
                            (geography_name, geography_type, geography_code, concept, date, value, is_forecast, source_file)
                        VALUES
                            (:geography_name, :geography_type, :geography_code, :concept, :date, :value, :is_forecast, :source_file)
                        ON CONFLICT (geography_name, concept, date)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            is_forecast = EXCLUDED.is_forecast,
                            source_file = EXCLUDED.source_file,
                            imported_at = NOW()
                    """),
                    rec,
                )
            total += len(batch)
    return total


def run_costar_extraction(engine=None) -> dict:
    """
    Parse all CoStar Excel files in the configured directory.

    Returns extraction summary dict.
    """
    if engine is None:
        db_url = settings.MARKET_ANALYSIS_DB_URL
        if not db_url:
            logger.error("MARKET_ANALYSIS_DB_URL not configured")
            return {"status": "error", "message": "No DB URL configured"}
        engine = create_engine(db_url)

    data_dir = Path(settings.COSTAR_DATA_DIR)
    if not data_dir.exists():
        logger.error(f"CoStar data directory not found: {data_dir}")
        return {"status": "error", "message": f"Directory not found: {data_dir}"}

    # Log extraction start
    with engine.begin() as conn:
        result = conn.execute(
            text("INSERT INTO extraction_log (source, status) VALUES ('costar', 'running') RETURNING id"),
        )
        log_id = result.scalar()

    total_records = 0
    files_processed = 0
    errors = []

    # Process MSA and Submarket files
    xlsx_files = sorted(data_dir.glob("*.xlsx"))
    # Filter out Zone.Identifier files (small metadata files from Windows)
    xlsx_files = [f for f in xlsx_files if f.stat().st_size > 1000]

    for filepath in xlsx_files:
        if "Submarket List" in filepath.name:
            continue  # Skip the summary list file
        try:
            count = parse_costar_file(filepath, engine)
            total_records += count
            files_processed += 1
        except Exception as e:
            logger.error(f"Error parsing {filepath.name}: {e}")
            errors.append(f"{filepath.name}: {e}")

    # Refresh materialized view
    try:
        with engine.begin() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY costar_latest"))
    except Exception as e:
        logger.warning(f"Could not refresh costar_latest view (may not exist yet): {e}")
        try:
            with engine.begin() as conn:
                conn.execute(text("REFRESH MATERIALIZED VIEW costar_latest"))
        except Exception:
            pass

    # Update extraction log
    status = "success" if not errors else "error"
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE extraction_log
                SET finished_at = NOW(), status = :status, records_upserted = :records,
                    error_message = :errors, details = :details
                WHERE id = :log_id
            """),
            {
                "status": status,
                "records": total_records,
                "errors": "; ".join(errors) if errors else None,
                "details": f'{{"files_processed": {files_processed}}}',
                "log_id": log_id,
            },
        )

    summary = {
        "status": status,
        "files_processed": files_processed,
        "records_upserted": total_records,
        "errors": errors,
    }
    logger.info(f"CoStar extraction complete: {summary}")
    return summary


if __name__ == "__main__":
    result = run_costar_extraction()
    print(result)
    sys.exit(0 if result["status"] == "success" else 1)
