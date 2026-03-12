"""
Promote deferred Proforma groups to active status and create
reference_mapping.json files with Proforma-specific cell addresses.

Cell addresses were mapped from representative files:
  - Bolero Proforma vCurrent.xlsb (Proforma-Base, 13 sheets)
  - Liv Crossroads Proforma vCurrent.xlsb (Proforma-Extended, 15 sheets)

Both template families share identical cell layouts for financial fields.

Usage:
    python -m backend.scripts.promote_proforma_groups [--dry-run]
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "extraction_groups"
GROUPS_FILE = DATA_DIR / "groups.json"

# ── Proforma cell mappings (identical for Base and Extended families) ─────────
# Derived from Bolero (Base) and Liv Crossroads (Extended) probes.
# Format: (field_name, source_sheet, source_cell, label_text, category)
PROFORMA_MAPPINGS: list[tuple[str, str, str, str, str]] = [
    # ── Property sheet: identification ──
    ("PROPERTY_NAME", "Property", "B1", "Property Name", "General"),
    ("PROPERTY_ADDRESS", "Property", "B2", "Property Address", "General"),
    ("YEAR_BUILT", "Property", "F7", "Year Constructed", "General"),
    # ── Property sheet: pricing & capital stack ──
    ("PURCHASE_PRICE", "Property", "D9", "Offering Price Total", "Pricing"),
    ("PRICE_PER_UNIT", "Property", "E9", "Offering Price Per Unit", "Pricing"),
    ("EQUITY", "Property", "E17", "Equity", "Capital Stack"),
    ("LOAN_AMOUNT", "Property", "E18", "Loan Amount", "Capital Stack"),
    ("LOAN_TO_VALUE", "Property", "E19", "Loan to PP", "Capital Stack"),
    ("LOAN_TERM", "Property", "E21", "Loan Term", "Capital Stack"),
    ("AMORTIZATION", "Property", "E22", "Amortization", "Capital Stack"),
    ("INTEREST_RATE", "Property", "E23", "Interest Rate", "Capital Stack"),
    ("IO_PERIOD", "Property", "E25", "Interest Only", "Capital Stack"),
    ("DEBT_SERVICE_ANNUAL", "Property", "E28", "Debt service /year", "Capital Stack"),
    # ── Property sheet: cap rate analysis ──
    ("GOING_IN_CAP_RATE", "Property", "F11", "Cap Rate T3", "Returns"),
    ("CAP_RATE_ADJ_TAXES", "Property", "F12", "Cap Rate adj for taxes", "Returns"),
    ("YR1_PF_CAP_RATE", "Property", "F13", "Yr 1 PF Cap Rate", "Returns"),
    ("YR3_PF_CAP_RATE", "Property", "F14", "Yr 3 PF Cap Rate", "Returns"),
    # ── Property sheet: debt metrics ──
    ("DEBT_YIELD_IN_PLACE", "Property", "E26", "Debt Yield on In Place", "Returns"),
    ("DSCR_T3", "Property", "E27", "DSC T3", "Returns"),
    # ── Property sheet: unit info ──
    ("TOTAL_UNITS", "Property", "K31", "Total Units", "General"),
    ("TOTAL_SF", "Property", "J31", "Total SF", "General"),
    # ── Property sheet: investment analysis (by exit year) ──
    ("NOI_PER_UNIT_YR2", "Property", "B41", "NOI/Unit Year 2", "Investment Analysis"),
    ("NOI_PER_UNIT_YR3", "Property", "C41", "NOI/Unit Year 3", "Investment Analysis"),
    ("NOI_PER_UNIT_YR5", "Property", "E41", "NOI/Unit Year 5", "Investment Analysis"),
    ("NOI_PER_UNIT_YR7", "Property", "F41", "NOI/Unit Year 7", "Investment Analysis"),
    ("LEVERED_RETURNS_IRR", "Property", "E44", "IRR Year 5", "Returns"),
    ("IRR_YR2", "Property", "B44", "IRR Year 2", "Investment Analysis"),
    ("IRR_YR3", "Property", "C44", "IRR Year 3", "Investment Analysis"),
    ("IRR_YR7", "Property", "F44", "IRR Year 7", "Investment Analysis"),
    ("LEVERED_RETURNS_MOIC", "Property", "E45", "Multiplier Year 5", "Returns"),
    ("MOIC_YR2", "Property", "B45", "Multiplier Year 2", "Investment Analysis"),
    ("MOIC_YR3", "Property", "C45", "Multiplier Year 3", "Investment Analysis"),
    ("MOIC_YR7", "Property", "F45", "Multiplier Year 7", "Investment Analysis"),
    ("COC_YR5", "Property", "E46", "COC Year 5", "Investment Analysis"),
    ("DSCR_YR5", "Property", "E47", "DSC Year 5", "Investment Analysis"),
    # ── Proforma sheet: annual metrics ──
    ("PROFORMA_NOI_YR1", "Proforma", "I15", "NOI/Unit Year 1", "Proforma"),
    ("PROFORMA_NOI_YR3", "Proforma", "K15", "NOI/Unit Year 3", "Proforma"),
    ("PROFORMA_NOI_YR5", "Proforma", "M15", "NOI/Unit Year 5", "Proforma"),
    ("T3_RETURN_ON_COST", "Proforma", "I18", "Cap Rate of ALL In Costs Yr1", "Returns"),
    (
        "CAP_RATE_ALL_IN_YR3",
        "Proforma",
        "K18",
        "Cap Rate of ALL In Costs Yr3",
        "Returns",
    ),
    (
        "CAP_RATE_ALL_IN_YR5",
        "Proforma",
        "M18",
        "Cap Rate of ALL In Costs Yr5",
        "Returns",
    ),
    ("PROFORMA_DEBT_YIELD_YR1", "Proforma", "I19", "Debt Yield Year 1", "Proforma"),
    ("PROFORMA_DSCR_YR1", "Proforma", "I20", "DSCR Year 1", "Proforma"),
    ("PROFORMA_DSCR_YR3", "Proforma", "K20", "DSCR Year 3", "Proforma"),
    ("PROFORMA_DSCR_YR5", "Proforma", "M20", "DSCR Year 5", "Proforma"),
]


def build_reference_mapping(group_name: str) -> dict:
    """Build a reference_mapping.json dict for a Proforma group."""
    mappings = []
    for field_name, sheet, cell, label, category in PROFORMA_MAPPINGS:
        mappings.append(
            {
                "field_name": field_name,
                "source_sheet": sheet,
                "source_cell": cell,
                "match_tier": 1,
                "confidence": 0.95,
                "label_text": label,
                "category": category,
                "production_sheet": sheet,
                "production_cell": cell,
            }
        )

    return {
        "group_name": group_name,
        "mappings": mappings,
        "unmapped_fields": [],
        "overall_confidence": 0.95,
        "tier_counts": {"1": len(mappings)},
        "total_mapped": len(mappings),
        "total_unmapped": 0,
        "template_type": "proforma",
    }


def promote_groups(dry_run: bool = True) -> dict:
    """Promote deferred Proforma groups to active and create reference mappings."""
    if not GROUPS_FILE.exists():
        print(f"ERROR: {GROUPS_FILE} not found")
        sys.exit(1)

    data = json.loads(GROUPS_FILE.read_text())
    deferred = data.get("deferred_groups", [])
    active = data.get("groups", [])

    if not deferred:
        print("No deferred groups found.")
        return {"promoted": 0}

    print(f"Found {len(deferred)} deferred groups to promote:")
    promoted_names = []

    for group in deferred:
        gname = group["group_name"]
        fcount = group.get("file_count", len(group.get("files", [])))
        print(f"  {gname}: {fcount} files")
        promoted_names.append(gname)

    if dry_run:
        print(
            f"\n[DRY RUN] Would promote {len(deferred)} groups and create reference mappings."
        )
        print("Run with --execute to apply changes.")
        return {"promoted": 0, "would_promote": len(deferred)}

    # 1. Move deferred groups to active
    for group in deferred:
        group["status"] = "active"
        group["promoted_from"] = "deferred"
        group["promoted_at"] = datetime.now(UTC).isoformat()
        if "defer_reason" in group:
            group["original_defer_reason"] = group.pop("defer_reason")
        active.append(group)

    data["groups"] = active
    data["deferred_groups"] = []

    # Update summary
    if "summary" in data:
        data["summary"]["active_groups"] = len(active)
        data["summary"]["deferred_groups"] = 0
        data["summary"]["active_files"] = sum(
            g.get("file_count", len(g.get("files", []))) for g in active
        )

    # 2. Create reference_mapping.json for each promoted group
    for gname in promoted_names:
        group_dir = DATA_DIR / gname
        group_dir.mkdir(parents=True, exist_ok=True)

        mapping = build_reference_mapping(gname)
        mapping_path = group_dir / "reference_mapping.json"
        mapping_path.write_text(json.dumps(mapping, indent=2))
        print(f"  Created {mapping_path.relative_to(DATA_DIR)}")

    # 3. Save updated groups.json
    GROUPS_FILE.write_text(json.dumps(data, indent=2))
    print(f"\nPromoted {len(promoted_names)} groups. Updated {GROUPS_FILE.name}.")

    return {
        "promoted": len(promoted_names),
        "groups": promoted_names,
        "mappings_per_group": len(PROFORMA_MAPPINGS),
    }


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    result = promote_groups(dry_run=not execute)
    print(f"\nResult: {json.dumps(result, indent=2)}")
