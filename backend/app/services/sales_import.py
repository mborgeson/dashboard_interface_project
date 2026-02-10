"""
Sales data import service for CoStar Excel files.

Handles importing, upserting, and verifying CoStar multifamily sales data
from Excel exports into the sales_data table.
"""

import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.sales_data import SalesData

# Exact mapping from CoStar Excel headers to database column names
COSTAR_COLUMN_MAP = {
    "Property Name": "property_name",
    "PropertyID": "property_id",
    "Comp ID": "comp_id",
    "Property Address": "property_address",
    "Property City": "property_city",
    "Property State": "property_state",
    "Property Zip Code": "property_zip_code",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Property County": "property_county",
    "Submarket Cluster": "submarket_cluster",
    "Submarket Name": "submarket_name",
    "Parcel Number 1 (Min)": "parcel_number_1_min",
    "Parcel Number 2 (Max)": "parcel_number_2_max",
    "Land Area AC": "land_area_ac",
    "Land Area SF": "land_area_sf",
    "Location Type": "location_type",
    "Star Rating": "star_rating",
    "Market": "market_column",
    "Submarket Code": "submarket_code",
    "Building Class": "building_class",
    "Affordable Type": "affordable_type",
    "Buyer (True) Company": "buyer_true_company",
    "Buyer (True) Contact": "buyer_true_contact",
    "Acquisition Fund Name": "acquisition_fund_name",
    "Buyer Contact": "buyer_contact",
    "Seller (True) Company": "seller_true_company",
    "Disposition Fund Name": "disposition_fund_name",
    "Listing Broker Company": "listing_broker_company",
    "Listing Broker Agent First Name": "listing_broker_agent_first_name",
    "Listing Broker Agent Last Name": "listing_broker_agent_last_name",
    "Buyers Broker Company": "buyers_broker_company",
    "Buyers Broker Agent First Name": "buyers_broker_agent_first_name",
    "Buyers Broker Agent Last Name": "buyers_broker_agent_last_name",
    "Construction Begin": "construction_begin",
    "Year Built": "year_built",
    "Year Renovated": "year_renovated",
    "Age": "age",
    "Property Type": "property_type",
    "Building SF": "building_sf",
    "Building Materials": "building_materials",
    "Building Condition": "building_condition",
    "Construction Material": "construction_material",
    "Roof Type": "roof_type",
    "Ceiling Height": "ceiling_height",
    "Secondary Type": "secondary_type",
    "Number Of Floors": "number_of_floors",
    "Number Of Units": "number_of_units",
    "Number Of Parking Spaces": "number_of_parking_spaces",
    "Number Of Tenants": "number_of_tenants",
    "Land SF Gross": "land_sf_gross",
    "Land SF Net": "land_sf_net",
    "Flood Risk": "flood_risk",
    "Flood Zone": "flood_zone",
    "Avg Unit SF": "avg_unit_sf",
    "Sale Date": "sale_date",
    "Sale Price": "sale_price",
    "Price Per Unit": "price_per_unit",
    "Price Per SF (Net)": "price_per_sf_net",
    "Price Per SF": "price_per_sf",
    "Hold Period": "hold_period",
    "Document Number": "document_number",
    "Down Payment": "down_payment",
    "Sale Type": "sale_type",
    "Sale Condition": "sale_condition",
    "Sale Price Comment": "sale_price_comment",
    "Sale Status": "sale_status",
    "Sale Category": "sale_category",
    "Actual Cap Rate": "actual_cap_rate",
    "Units Per Acre": "units_per_acre",
    "Zoning": "zoning",
    "Number Of Beds": "number_of_beds",
    "Gross Income": "gross_income",
    "GRM": "grm",
    "GIM": "gim",
    "Building Operating Expenses": "building_operating_expenses",
    "Total Expense Amount": "total_expense_amount",
    "Vacancy": "vacancy",
    "Assessed Improved": "assessed_improved",
    "Assessed Land": "assessed_land",
    "Assessed Value": "assessed_value",
    "Assessed Year": "assessed_year",
    "Number Of Studios Units": "number_of_studios_units",
    "Number Of 1 Bedrooms Units": "number_of_1_bedrooms_units",
    "Number Of 2 Bedrooms Units": "number_of_2_bedrooms_units",
    "Number Of 3 Bedrooms Units": "number_of_3_bedrooms_units",
    "Number Of Other Bedrooms Units": "number_of_other_bedrooms_units",
    "First Trust Deed Terms": "first_trust_deed_terms",
    "First Trust Deed Balance": "first_trust_deed_balance",
    "First Trust Deed Lender": "first_trust_deed_lender",
    "First Trust Deed Payment": "first_trust_deed_payment",
    "Second Trust Deed Balance": "second_trust_deed_balance",
    "Second Trust Deed Lender": "second_trust_deed_lender",
    "Second Trust Deed Payment": "second_trust_deed_payment",
    "Second Trust Deed Terms": "second_trust_deed_terms",
    "Title Company": "title_company",
    "Amenities": "amenities",
    "Sewer": "sewer",
    "Transaction Notes": "transaction_notes",
    "Description Text": "description_text",
    "Research Status": "research_status",
}

# Columns that should be stored as strings even if pandas reads as numeric
STRING_COLUMNS = {
    "property_id",
    "comp_id",
    "property_zip_code",
    "document_number",
    "parcel_number_1_min",
    "parcel_number_2_max",
}

# Columns that should be nullable integers (pandas reads as float due to NaN)
NULLABLE_INT_COLUMNS = {
    "year_built",
    "year_renovated",
    "age",
    "number_of_floors",
    "number_of_units",
    "number_of_parking_spaces",
    "number_of_tenants",
    "number_of_beds",
    "assessed_year",
    "land_area_sf",
    "number_of_studios_units",
    "number_of_1_bedrooms_units",
    "number_of_2_bedrooms_units",
    "number_of_3_bedrooms_units",
    "number_of_other_bedrooms_units",
}


@dataclass
class FileImportResult:
    """Result of importing a single Excel file."""

    filename: str
    rows_imported: int = 0
    rows_updated: int = 0
    rows_with_null_comp_id: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class FullImportResult:
    """Aggregate result of importing all files."""

    files_processed: int = 0
    files_skipped: int = 0
    total_rows_imported: int = 0
    total_rows_updated: int = 0
    total_null_comp_ids: int = 0
    file_results: list[FileImportResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class VerificationReport:
    """Verification query results after import."""

    total_rows: int = 0
    rows_per_file: dict[str, int] = field(default_factory=dict)
    null_comp_id_count: int = 0
    earliest_sale_date: str | None = None
    latest_sale_date: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    median_price: float | None = None
    duplicate_comp_ids: int = 0


def scan_sales_files(data_dir: str) -> list[str]:
    """Recursively scan for .xlsx files in data_dir and subfolders."""
    files = []
    for root, _, filenames in os.walk(data_dir):
        for f in filenames:
            if f.endswith(".xlsx") and not f.startswith("~$"):
                files.append(os.path.join(root, f))
    return sorted(files)


def get_unimported_files(db: Session, data_dir: str) -> list[str]:
    """Compare scanned files vs source_file column in DB."""
    all_files = scan_sales_files(data_dir)
    imported = {r[0] for r in db.query(SalesData.source_file).distinct().all() if r[0]}
    return [f for f in all_files if os.path.basename(f) not in imported]


def _clean_currency(val):
    """Strip currency formatting from a value."""
    if isinstance(val, str):
        cleaned = re.sub(r"[$,]", "", val.strip())
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    return val


def _safe_str(val) -> str | None:
    """Convert value to trimmed string or None."""
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _safe_float(val) -> float | None:
    """Convert value to float or None."""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, str):
        val = _clean_currency(val)
    try:
        f = float(val)
        return f if np.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    """Convert value to int or None."""
    f = _safe_float(val)
    if f is None:
        return None
    return int(f)


def _safe_date(val):
    """Convert value to date or None."""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, pd.Timestamp):
        return val.date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
            try:
                return datetime.strptime(val.strip(), fmt).date()
            except ValueError:
                continue
    return None


def import_sales_file(
    db: Session,
    filepath: str,
    market: str,
) -> FileImportResult:
    """Import a single CoStar Excel file into the database."""
    filename = os.path.basename(filepath)
    result = FileImportResult(filename=filename)
    now = datetime.now(UTC)

    # Read Excel file
    try:
        df = pd.read_excel(filepath, engine="openpyxl")
    except UnicodeDecodeError:
        try:
            df = pd.read_excel(filepath, engine="openpyxl")
        except Exception as e:
            result.errors.append(f"Failed to read file: {e}")
            return result

    # Verify expected columns exist
    missing = set(COSTAR_COLUMN_MAP.keys()) - set(df.columns)
    if missing:
        result.warnings.append(f"Missing columns: {', '.join(sorted(missing))}")
        if len(missing) > 10:
            result.errors.append(
                f"Too many missing columns ({len(missing)}), skipping file"
            )
            return result

    # Rename columns to snake_case
    rename_map = {k: v for k, v in COSTAR_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Track comp_ids seen in this file to handle within-file duplicates
    comp_id_counts: dict[str, int] = {}

    for row_idx, row in df.iterrows():
        row_dict: dict = {}

        for _excel_col, db_col in COSTAR_COLUMN_MAP.items():
            if db_col not in df.columns:
                row_dict[db_col] = None
                continue

            val = row.get(db_col)

            if db_col in STRING_COLUMNS:
                row_dict[db_col] = _safe_str(val)
            elif db_col in NULLABLE_INT_COLUMNS:
                row_dict[db_col] = _safe_int(val)
            elif db_col == "sale_date":
                row_dict[db_col] = _safe_date(val)
            elif db_col in (
                "sale_price",
                "price_per_unit",
                "price_per_sf",
                "price_per_sf_net",
                "down_payment",
                "actual_cap_rate",
                "gross_income",
                "grm",
                "gim",
                "total_expense_amount",
                "vacancy",
                "assessed_improved",
                "assessed_land",
                "assessed_value",
                "latitude",
                "longitude",
                "land_area_ac",
                "avg_unit_sf",
                "units_per_acre",
                "building_sf",
                "land_sf_gross",
                "land_sf_net",
                "ceiling_height",
                "first_trust_deed_balance",
                "first_trust_deed_payment",
                "second_trust_deed_balance",
                "second_trust_deed_payment",
            ):
                row_dict[db_col] = _safe_float(val)
            elif db_col in (
                "building_operating_expenses",
                "hold_period",
                "construction_begin",
                "amenities",
                "transaction_notes",
                "description_text",
                "sale_price_comment",
            ):
                row_dict[db_col] = _safe_str(val)
            else:
                row_dict[db_col] = _safe_str(val)

        # Handle null/blank Comp ID
        comp_id = row_dict.get("comp_id")
        if not comp_id:
            row_num = row_idx + 2  # Excel row (1-indexed + header)
            row_dict["comp_id"] = f"UNKNOWN-{filename}-{row_num}"
            result.rows_with_null_comp_id += 1

        # Handle within-file duplicate comp_ids by appending suffix
        comp_id = row_dict["comp_id"]
        comp_id_counts[comp_id] = comp_id_counts.get(comp_id, 0) + 1
        if comp_id_counts[comp_id] > 1:
            row_dict["comp_id"] = f"{comp_id}-dup{comp_id_counts[comp_id]}"

        # Add metadata
        row_dict["source_file"] = filename
        row_dict["imported_at"] = now
        row_dict["market"] = market

        # Upsert: check if comp_id + source_file already exists
        existing = (
            db.query(SalesData)
            .filter(
                SalesData.comp_id == row_dict["comp_id"],
                SalesData.source_file == filename,
            )
            .first()
        )

        if existing:
            for key, val in row_dict.items():
                if key != "id":
                    setattr(existing, key, val)
            existing.updated_at = now
            result.rows_updated += 1
        else:
            record = SalesData(
                **row_dict,
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            db.flush()  # Flush each row so subsequent queries see it
            result.rows_imported += 1

    db.commit()

    # Log warnings for zero/negative prices
    zero_prices = (
        df[
            (df.get("sale_price", pd.Series(dtype=float)).notna())
            & (df.get("sale_price", pd.Series(dtype=float)) <= 0)
        ]
        if "sale_price" in df.columns
        else pd.DataFrame()
    )

    if len(zero_prices) > 0:
        result.warnings.append(
            f"{len(zero_prices)} rows with zero or negative sale price"
        )

    return result


def import_all_files(
    db: Session,
    data_dir: str,
    market: str = "Phoenix",
) -> FullImportResult:
    """Import all Excel files from the sales data directory.

    Args:
        db: SQLAlchemy sync session.
        data_dir: Path to directory containing .xlsx files (e.g. data/sales/Phoenix/).
        market: Market name tag applied to all imported rows.
    """
    result = FullImportResult()
    files = scan_sales_files(data_dir)

    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"  Importing: {filename}...")
        file_result = import_sales_file(db, filepath, market)
        result.file_results.append(file_result)
        result.files_processed += 1
        result.total_rows_imported += file_result.rows_imported
        result.total_rows_updated += file_result.rows_updated
        result.total_null_comp_ids += file_result.rows_with_null_comp_id

        if file_result.errors:
            result.errors.extend(file_result.errors)
            result.files_skipped += 1

        print(
            f"    -> {file_result.rows_imported} new, "
            f"{file_result.rows_updated} updated, "
            f"{file_result.rows_with_null_comp_id} null comp IDs"
        )

    return result


def run_verification_queries(db: Session) -> VerificationReport:
    """Execute post-import verification queries."""
    report = VerificationReport()

    # Total rows
    report.total_rows = db.query(func.count(SalesData.id)).scalar() or 0

    # Rows per source file
    file_counts = (
        db.query(SalesData.source_file, func.count(SalesData.id))
        .group_by(SalesData.source_file)
        .order_by(SalesData.source_file)
        .all()
    )
    report.rows_per_file = dict(file_counts)  # type: ignore[arg-type]

    # Null/placeholder comp IDs
    report.null_comp_id_count = (
        db.query(func.count(SalesData.id))
        .filter(SalesData.comp_id.like("UNKNOWN-%"))
        .scalar()
        or 0
    )

    # Date range
    date_range = db.query(
        func.min(SalesData.sale_date),
        func.max(SalesData.sale_date),
    ).first()
    if date_range:
        report.earliest_sale_date = str(date_range[0]) if date_range[0] else None
        report.latest_sale_date = str(date_range[1]) if date_range[1] else None

    # Price stats (where price > 0)
    price_stats = (
        db.query(
            func.min(SalesData.sale_price),
            func.max(SalesData.sale_price),
        )
        .filter(SalesData.sale_price > 0)
        .first()
    )
    if price_stats:
        report.min_price = price_stats[0]
        report.max_price = price_stats[1]

    # Median price
    median_result = db.execute(
        text(
            "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY sale_price) "
            "FROM sales_data WHERE sale_price > 0"
        )
    ).scalar()
    report.median_price = float(median_result) if median_result else None

    # Duplicate comp_id check (same comp_id in multiple source files)
    dup_result = db.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "  SELECT comp_id FROM sales_data "
            "  WHERE comp_id NOT LIKE 'UNKNOWN-%' "
            "  GROUP BY comp_id HAVING COUNT(DISTINCT source_file) > 1"
            ") sub"
        )
    ).scalar()
    report.duplicate_comp_ids = dup_result or 0

    return report
