"""
Construction pipeline import service for CoStar Excel files.

Handles importing, upserting, and verifying CoStar multifamily construction
pipeline data from Excel exports into the construction_projects table.
Applies 50-unit minimum filter and infers property classification.
"""

import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.construction import (
    ConstructionProject,
    ConstructionSourceLog,
    PipelineStatus,
    ProjectClassification,
)

# ── Column Mapping ──────────────────────────────────────────────────────────
# Maps CoStar Excel headers (171 columns) to DB column names (~100 mapped).
# Unmapped CoStar columns (detailed per-bedroom rent breakdowns, FEMA panel IDs,
# property manager contact info, etc.) are intentionally excluded.

COSTAR_CONSTRUCTION_COLUMN_MAP = {
    # Core identifiers
    "PropertyID": "costar_property_id",
    "Property Name": "project_name",
    "Property Address": "project_address",
    "Property Type": "property_type",
    # Location
    "City": "city",
    "State": "state",
    "Zip": "zip_code",
    "County Name": "county",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Market Name": "market_name",
    "Submarket Name": "submarket_name",
    "Submarket Cluster": "submarket_cluster",
    # Status
    "Building Status": "building_status_raw",
    "Constr Status": "constr_status_raw",
    # Building info
    "Number Of Units": "number_of_units",
    "RBA": "building_sf",
    "Number Of Stories": "number_of_stories",
    "Total Buildings": "total_buildings",
    "Star Rating": "star_rating",
    "Building Class": "building_class",
    "Style": "style",
    "Secondary Type": "secondary_type",
    "Construction Material": "construction_material",
    "Condo": "is_condo",
    "Number Of Elevators": "number_of_elevators",
    "Ceiling Ht": "ceiling_height",
    "Sprinklers": "sprinklers",
    # Unit mix percentages
    "% Studios": "pct_studio",
    "% 1-Bed": "pct_1bed",
    "% 2-Bed": "pct_2bed",
    "% 3-Bed": "pct_3bed",
    "% 4-Bed": "pct_4bed",
    # Unit mix counts
    "Number Of Studios Units": "num_studios",
    "Number Of 1 Bedrooms Units": "num_1bed",
    "Number Of 2 Bedrooms Units": "num_2bed",
    "Number Of 3 Bedrooms Units": "num_3bed",
    "Number Of 4 Bedrooms Units": "num_4bed",
    "Number of Beds": "num_beds_total",
    "Avg Unit SF": "avg_unit_sf",
    # Rent info
    "Rent Type": "rent_type",
    "Affordable Type": "affordable_type",
    "Market Segment": "market_segment",
    "Avg Asking/Unit": "avg_asking_per_unit",
    "Avg Asking/SF": "avg_asking_per_sf",
    "Avg Effective/Unit": "avg_effective_per_unit",
    "Avg Effective/SF": "avg_effective_per_sf",
    "Avg Concessions %": "avg_concessions_pct",
    "Vacancy %": "vacancy_pct",
    "Percent Leased": "pct_leased",
    "Pre-Leasing": "pre_leasing",
    # Timeline
    "Construction Begin": "construction_begin",
    "Year Built": "year_built",
    "Month Built": "month_built",
    "Year Renovated": "year_renovated",
    "Month Renovated": "month_renovated",
    # Developer / Owner / Architect
    "Developer Name": "developer_name",
    "Owner Name": "owner_name",
    "Owner Contact": "owner_contact",
    "Architect Name": "architect_name",
    "Property Manager Name": "property_manager_name",
    # Sale / For-Sale info
    "For Sale Price": "for_sale_price",
    "For Sale Status": "for_sale_status",
    "For Sale Price Per Unit": "for_sale_price_per_unit",
    "For Sale Price Per SF": "for_sale_price_per_sf",
    "Cap Rate": "cap_rate",
    "Last Sale Date": "last_sale_date",
    "Last Sale Price": "last_sale_price",
    "Days On Market": "days_on_market",
    # Land / Parking / Zoning
    "Land Area (AC)": "land_area_ac",
    "Land Area (SF)": "land_area_sf",
    "Zoning": "zoning",
    "Number Of Parking Spaces": "parking_spaces",
    "Parking Spaces/Unit": "parking_spaces_per_unit",
    "Parking Ratio": "parking_ratio",
    # Flood / FEMA
    "Fema Flood Zone": "fema_flood_zone",
    "Flood Risk Area": "flood_risk_area",
    "In SFHA": "in_sfha",
    # Financing
    "Origination Amount": "origination_amount",
    "Origination Date": "origination_date",
    "Originator": "originator",
    "Interest Rate": "interest_rate",
    "Interest Rate Type": "interest_rate_type",
    "Loan Type": "loan_type",
    "Maturity Date": "maturity_date",
    # Tax
    "Tax Year": "tax_year",
    "Taxes Per SF": "taxes_per_sf",
    "Taxes Total": "taxes_total",
    # Amenities / Misc
    "Amenities": "amenities",
    "Features": "features",
    "Closest Transit Stop": "closest_transit_stop",
    "Closest Transit Stop Dist (mi)": "closest_transit_dist_mi",
    "University": "university",
    "Energy Star": "energy_star",
    "LEED Certified": "leed_certified",
}

# Columns stored as strings even if pandas reads as numeric
STRING_COLUMNS = {
    "costar_property_id",
    "zip_code",
}

# Columns that should be nullable integers (pandas reads as float due to NaN)
NULLABLE_INT_COLUMNS = {
    "number_of_units",
    "number_of_stories",
    "total_buildings",
    "num_studios",
    "num_1bed",
    "num_2bed",
    "num_3bed",
    "num_4bed",
    "num_beds_total",
    "number_of_elevators",
    "year_built",
    "month_built",
    "year_renovated",
    "month_renovated",
    "parking_spaces",
    "days_on_market",
    "tax_year",
}

# Columns that are float
FLOAT_COLUMNS = {
    "latitude",
    "longitude",
    "building_sf",
    "avg_unit_sf",
    "pct_studio",
    "pct_1bed",
    "pct_2bed",
    "pct_3bed",
    "pct_4bed",
    "avg_asking_per_unit",
    "avg_asking_per_sf",
    "avg_effective_per_unit",
    "avg_effective_per_sf",
    "avg_concessions_pct",
    "vacancy_pct",
    "pct_leased",
    "for_sale_price",
    "for_sale_price_per_unit",
    "for_sale_price_per_sf",
    "cap_rate",
    "last_sale_price",
    "land_area_ac",
    "land_area_sf",
    "parking_spaces_per_unit",
    "parking_ratio",
    "origination_amount",
    "interest_rate",
    "taxes_per_sf",
    "taxes_total",
    "closest_transit_dist_mi",
}

# Minimum unit threshold for import
MIN_UNITS = 50


# ── Result dataclasses ──────────────────────────────────────────────────────


@dataclass
class FileImportResult:
    """Result of importing a single Excel file."""

    filename: str
    rows_imported: int = 0
    rows_updated: int = 0
    rows_skipped_under_min: int = 0
    rows_skipped_no_units: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class FullImportResult:
    """Aggregate result of importing all files."""

    files_processed: int = 0
    files_skipped: int = 0
    total_rows_imported: int = 0
    total_rows_updated: int = 0
    total_rows_skipped: int = 0
    file_results: list[FileImportResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ── Type conversion helpers ─────────────────────────────────────────────────


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


def _safe_bool(val) -> bool:
    """Convert value to bool (default False)."""
    if pd.isna(val) or val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("yes", "true", "1", "y")


# ── Classification inference ─────────────────────────────────────────────────


def infer_classification(row_dict: dict) -> str:
    """Infer property classification from CoStar fields.

    Priority order:
      1. is_condo=True → CONV_CONDO
      2. affordable_type contains "Rent Restricted" OR rent_type == "Affordable" → LIHTC
      3. rent_type == "Market/Affordable" → WORKFORCE
      4. Default → CONV_MR

    BTR, AGE_55, MIXED_USE, CONVERSION require manual tagging (CoStar doesn't
    reliably distinguish these from conventional multifamily).
    """
    if row_dict.get("is_condo"):
        return ProjectClassification.CONV_CONDO

    affordable_type = (row_dict.get("affordable_type") or "").lower()
    rent_type = (row_dict.get("rent_type") or "").lower()

    if "rent restricted" in affordable_type or rent_type == "affordable":
        return ProjectClassification.LIHTC

    if rent_type == "market/affordable":
        return ProjectClassification.WORKFORCE

    return ProjectClassification.CONV_MR


# ── Pipeline status mapping ─────────────────────────────────────────────────


def map_pipeline_status(building_status: str | None, constr_status: str | None) -> str:
    """Map CoStar Building Status / Constr Status to PipelineStatus enum.

    CoStar values observed in the data:
      - "Proposed" → proposed
      - "Final Planning" → final_planning
      - "Under Construction" → under_construction
      - (not in current export but possible:)
      - "Permitted" → permitted
      - "Existing" / "Built" → delivered
    """
    raw = (constr_status or building_status or "").strip().lower()

    status_map = {
        "proposed": PipelineStatus.PROPOSED,
        "final planning": PipelineStatus.FINAL_PLANNING,
        "permitted": PipelineStatus.PERMITTED,
        "under construction": PipelineStatus.UNDER_CONSTRUCTION,
        "existing": PipelineStatus.DELIVERED,
        "built": PipelineStatus.DELIVERED,
        "delivered": PipelineStatus.DELIVERED,
    }

    return status_map.get(raw, PipelineStatus.PROPOSED)


# ── File scanning ────────────────────────────────────────────────────────────


def scan_construction_files(data_dir: str) -> list[str]:
    """Recursively scan for .xlsx files in data_dir and subfolders."""
    files = []
    for root, _, filenames in os.walk(data_dir):
        for f in filenames:
            if f.endswith((".xlsx", ".xlsb", ".xlsm")) and not f.startswith("~$"):
                files.append(os.path.join(root, f))
    return sorted(files)


def get_unimported_files(db: Session, data_dir: str) -> list[str]:
    """Compare scanned files vs source_file column in DB."""
    all_files = scan_construction_files(data_dir)
    imported = {
        r[0] for r in db.query(ConstructionProject.source_file).distinct().all() if r[0]
    }
    return [f for f in all_files if os.path.basename(f) not in imported]


# ── Single file import ───────────────────────────────────────────────────────


def import_construction_file(
    db: Session,
    filepath: str,
) -> FileImportResult:
    """Import a single CoStar construction Excel file into the database.

    Applies 50-unit minimum filter and infers classification from CoStar fields.
    Upserts on (costar_property_id, source_file).
    """
    filename = os.path.basename(filepath)
    result = FileImportResult(filename=filename)
    now = datetime.now(UTC)

    # Read Excel file
    try:
        df = pd.read_excel(filepath, engine="openpyxl")
    except Exception as e:
        result.errors.append(f"Failed to read file: {e}")
        return result

    # Verify expected columns exist
    missing = set(COSTAR_CONSTRUCTION_COLUMN_MAP.keys()) - set(df.columns)
    if missing:
        result.warnings.append(f"Missing columns: {', '.join(sorted(missing))}")
        if len(missing) > 20:
            result.errors.append(
                f"Too many missing columns ({len(missing)}), skipping file"
            )
            return result

    # Rename columns to snake_case DB names
    rename_map = {
        k: v for k, v in COSTAR_CONSTRUCTION_COLUMN_MAP.items() if k in df.columns
    }
    df = df.rename(columns=rename_map)

    for row_idx, row in df.iterrows():
        row_dict: dict = {}

        for _excel_col, db_col in COSTAR_CONSTRUCTION_COLUMN_MAP.items():
            if db_col not in df.columns:
                row_dict[db_col] = None
                continue

            val = row.get(db_col)

            if db_col == "is_condo":
                row_dict[db_col] = _safe_bool(val)
            elif db_col in STRING_COLUMNS:
                row_dict[db_col] = _safe_str(val)
            elif db_col in NULLABLE_INT_COLUMNS:
                row_dict[db_col] = _safe_int(val)
            elif db_col in FLOAT_COLUMNS:
                row_dict[db_col] = _safe_float(val)
            elif db_col in ("last_sale_date",):
                row_dict[db_col] = _safe_date(val)
            else:
                row_dict[db_col] = _safe_str(val)

        # ── 50-unit filter ────────────────────────────────────────────
        units = row_dict.get("number_of_units")
        if units is None:
            result.rows_skipped_no_units += 1
            continue
        if units < MIN_UNITS:
            result.rows_skipped_under_min += 1
            continue

        # ── Infer classification and pipeline status ──────────────────
        row_dict["primary_classification"] = infer_classification(row_dict)
        row_dict["pipeline_status"] = map_pipeline_status(
            row_dict.get("building_status_raw"),
            row_dict.get("constr_status_raw"),
        )

        # ── Metadata ──────────────────────────────────────────────────
        row_dict["source_type"] = "costar"
        row_dict["source_file"] = filename
        row_dict["imported_at"] = now

        # ── Handle missing costar_property_id ─────────────────────────
        prop_id = row_dict.get("costar_property_id")
        if not prop_id:
            row_num = row_idx + 2  # Excel row (1-indexed + header)
            row_dict["costar_property_id"] = f"UNKNOWN-{filename}-{row_num}"

        # ── Upsert on (costar_property_id, source_file) ──────────────
        existing = (
            db.query(ConstructionProject)
            .filter(
                ConstructionProject.costar_property_id
                == row_dict["costar_property_id"],
                ConstructionProject.source_file == filename,
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
            record = ConstructionProject(
                **row_dict,
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            db.flush()
            result.rows_imported += 1

    db.commit()

    # Create source log entry
    source_log = ConstructionSourceLog(
        source_name="costar_construction",
        fetch_type="excel_import",
        fetched_at=now,
        records_fetched=len(df),
        records_inserted=result.rows_imported,
        records_updated=result.rows_updated,
        success=len(result.errors) == 0,
        error_message="; ".join(result.errors) if result.errors else None,
        created_at=now,
    )
    db.add(source_log)
    db.commit()

    return result


# ── Bulk import ──────────────────────────────────────────────────────────────


def import_all_construction_files(
    db: Session,
    data_dir: str,
) -> FullImportResult:
    """Import all Excel files from the construction data directory.

    Args:
        db: SQLAlchemy sync session.
        data_dir: Path to directory containing .xlsx files
                  (e.g. data/construction/Phoenix/).
    """
    result = FullImportResult()
    files = scan_construction_files(data_dir)

    for filepath in files:
        file_result = import_construction_file(db, filepath)
        result.file_results.append(file_result)
        result.files_processed += 1
        result.total_rows_imported += file_result.rows_imported
        result.total_rows_updated += file_result.rows_updated
        result.total_rows_skipped += (
            file_result.rows_skipped_under_min + file_result.rows_skipped_no_units
        )

        if file_result.errors:
            result.errors.extend(file_result.errors)
            result.files_skipped += 1

    return result


# ── Verification ─────────────────────────────────────────────────────────────


@dataclass
class VerificationReport:
    """Post-import verification results."""

    total_rows: int = 0
    rows_per_status: dict[str, int] = field(default_factory=dict)
    rows_per_classification: dict[str, int] = field(default_factory=dict)
    rows_per_file: dict[str, int] = field(default_factory=dict)
    unit_range: tuple[int | None, int | None] = (None, None)
    cities: list[str] = field(default_factory=list)
    submarkets: list[str] = field(default_factory=list)


def run_verification_queries(db: Session) -> VerificationReport:
    """Execute post-import verification queries."""
    report = VerificationReport()

    report.total_rows = db.query(func.count(ConstructionProject.id)).scalar() or 0

    # Rows per pipeline_status
    status_counts = (
        db.query(
            ConstructionProject.pipeline_status,
            func.count(ConstructionProject.id),
        )
        .group_by(ConstructionProject.pipeline_status)
        .all()
    )
    report.rows_per_status = {str(k): v for k, v in status_counts}

    # Rows per classification
    class_counts = (
        db.query(
            ConstructionProject.primary_classification,
            func.count(ConstructionProject.id),
        )
        .group_by(ConstructionProject.primary_classification)
        .all()
    )
    report.rows_per_classification = {str(k): v for k, v in class_counts}

    # Rows per source file
    file_counts = (
        db.query(
            ConstructionProject.source_file,
            func.count(ConstructionProject.id),
        )
        .group_by(ConstructionProject.source_file)
        .all()
    )
    report.rows_per_file = {str(k): v for k, v in file_counts}

    # Unit range
    unit_range = db.query(
        func.min(ConstructionProject.number_of_units),
        func.max(ConstructionProject.number_of_units),
    ).first()
    if unit_range:
        report.unit_range = (unit_range[0], unit_range[1])

    # Distinct cities
    cities = (
        db.query(ConstructionProject.city)
        .filter(ConstructionProject.city.isnot(None))
        .distinct()
        .order_by(ConstructionProject.city)
        .all()
    )
    report.cities = [c[0] for c in cities]

    # Distinct submarkets
    submarkets = (
        db.query(ConstructionProject.submarket_cluster)
        .filter(ConstructionProject.submarket_cluster.isnot(None))
        .distinct()
        .order_by(ConstructionProject.submarket_cluster)
        .all()
    )
    report.submarkets = [s[0] for s in submarkets]

    return report
