"""
Fix placeholder and duplicate property names in extracted_values.

Resolves:
1. Placeholder names ([Deal Name], nan, Property, Property Name) → actual deal names from filenames
2. Duplicate variants (Palm  Trails → Palm Trails, Soltra SanTan Village → Soltra at SanTan Village)

Run: python -m scripts.fix_property_names [--dry-run]
"""

import sys

from sqlalchemy import create_engine, text

from app.core.config import settings

# Placeholder resolutions: (old_name, source_file_substring, new_name)
PLACEHOLDER_FIXES = [
    ("[Deal Name]", "Capri on Camelback Proforma", "Capri on Camelback"),
    ("[Deal Name]", "Liv Crossroads Proforma", "Liv Crossroads"),
    ("[Deal Name]", "Nightingale on 25th Proforma", "Nightingale on 25th"),
    ("[Deal Name]", "Ponderosa Ranch Proforma", "Ponderosa Ranch"),
    ("[Deal Name]", "The Scottsdale Grand Proforma", "The Scottsdale Grand"),
    ("nan", "Heather Brook Apartments UW Model", "Heather Brook Apartments"),
    ("nan", "Revival on 7th UW Model", "Revival on 7th"),
    ("Property", "Apex on Central Model", "Apex on Central"),
    ("Property Name", "Papago View Apartments UW Model", "Papago View Apartments"),
]

# Duplicate consolidations: (old_name, new_name)
DUPLICATE_FIXES = [
    ("Palm  Trails", "Palm Trails"),
    ("Soltra SanTan Village", "Soltra at SanTan Village"),
]


def run(dry_run: bool = True) -> dict:
    engine = create_engine(str(settings.DATABASE_URL).replace("+asyncpg", ""))
    results = {"placeholder_fixes": [], "duplicate_fixes": [], "total_rows_updated": 0}

    with engine.begin() as conn:
        # Fix placeholders (scoped by source_file to avoid collisions)
        for old_name, file_substr, new_name in PLACEHOLDER_FIXES:
            row = conn.execute(
                text(
                    "SELECT COUNT(*) FROM extracted_values "
                    "WHERE property_name = :old AND source_file LIKE :pattern"
                ),
                {"old": old_name, "pattern": f"%{file_substr}%"},
            ).scalar()

            if row and row > 0:
                if not dry_run:
                    conn.execute(
                        text(
                            "UPDATE extracted_values SET property_name = :new "
                            "WHERE property_name = :old AND source_file LIKE :pattern"
                        ),
                        {"new": new_name, "old": old_name, "pattern": f"%{file_substr}%"},
                    )
                results["placeholder_fixes"].append(
                    {"old": old_name, "new": new_name, "file": file_substr, "rows": row}
                )
                results["total_rows_updated"] += row

        # Fix duplicates (rename all rows with old_name)
        for old_name, new_name in DUPLICATE_FIXES:
            row = conn.execute(
                text("SELECT COUNT(*) FROM extracted_values WHERE property_name = :old"),
                {"old": old_name},
            ).scalar()

            if row and row > 0:
                if not dry_run:
                    conn.execute(
                        text(
                            "UPDATE extracted_values SET property_name = :new "
                            "WHERE property_name = :old"
                        ),
                        {"new": new_name, "old": old_name},
                    )
                results["duplicate_fixes"].append(
                    {"old": old_name, "new": new_name, "rows": row}
                )
                results["total_rows_updated"] += row

        if dry_run:
            # Rollback — this is inside engine.begin() so we need to explicitly rollback
            conn.rollback()

    return results


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"=== Fix Property Names ({mode}) ===\n")

    results = run(dry_run=dry_run)

    if results["placeholder_fixes"]:
        print("Placeholder fixes:")
        for fix in results["placeholder_fixes"]:
            print(f'  "{fix["old"]}" → "{fix["new"]}" ({fix["rows"]} rows) [{fix["file"]}]')

    if results["duplicate_fixes"]:
        print("\nDuplicate fixes:")
        for fix in results["duplicate_fixes"]:
            print(f'  "{fix["old"]}" → "{fix["new"]}" ({fix["rows"]} rows)')

    print(f"\nTotal rows {'would be' if dry_run else ''} updated: {results['total_rows_updated']}")

    if dry_run:
        print("\nRe-run without --dry-run to apply changes.")
