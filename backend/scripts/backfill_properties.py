"""
Backfill properties/deals tables from existing group extraction runs.

Runs sync_extracted_to_properties for all group_extraction runs that have
unlinked extracted_values (property_id IS NULL).

Run: python -m scripts.backfill_properties [--dry-run]
"""

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.crud.extraction import sync_extracted_to_properties

engine = create_engine(str(settings.DATABASE_URL).replace("+asyncpg", ""))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def run(dry_run: bool = True) -> dict:
    results = {
        "runs_processed": 0,
        "total_properties_created": 0,
        "total_deals_created": 0,
        "total_properties_linked": 0,
        "errors": [],
    }

    with engine.connect() as conn:
        # Find group extraction runs with unlinked values
        runs = conn.execute(
            text("""
                SELECT DISTINCT er.id, er.trigger_type, er.created_at
                FROM extraction_runs er
                JOIN extracted_values ev ON ev.extraction_run_id = er.id
                WHERE ev.property_id IS NULL
                ORDER BY er.created_at
            """)
        ).fetchall()

    print(f"Found {len(runs)} extraction runs with unlinked values")

    if dry_run:
        # In dry-run mode, just count what would be synced
        with engine.connect() as conn:
            unlinked = conn.execute(
                text("""
                    SELECT COUNT(DISTINCT property_name)
                    FROM extracted_values
                    WHERE property_id IS NULL
                """)
            ).scalar()
            print(f"  {unlinked} distinct property names would be synced")
        return results

    for run_row in runs:
        run_id = run_row[0]
        trigger = run_row[1]
        created = run_row[2]
        print(f"\nSyncing run {str(run_id)[:8]}... ({trigger}, {created})")

        db = SessionLocal()
        try:
            result = sync_extracted_to_properties(db, run_id)
            results["runs_processed"] += 1
            results["total_properties_created"] += result.get("properties_created", 0)
            results["total_deals_created"] += result.get("deals_created", 0)
            results["total_properties_linked"] += result.get("properties_linked", 0)
            print(f"  Created: {result.get('properties_created', 0)} properties, "
                  f"{result.get('deals_created', 0)} deals | "
                  f"Linked: {result.get('properties_linked', 0)}")
        except Exception as e:
            results["errors"].append({"run_id": str(run_id), "error": str(e)})
            print(f"  ERROR: {e}")
        finally:
            db.close()

    return results


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    mode = "DRY RUN" if dry_run else "EXECUTE"
    print(f"=== Backfill Properties ({mode}) ===\n")

    results = run(dry_run=dry_run)

    print(f"\n=== Summary ===")
    print(f"Runs processed: {results['runs_processed']}")
    print(f"Properties created: {results['total_properties_created']}")
    print(f"Deals created: {results['total_deals_created']}")
    print(f"Properties linked: {results['total_properties_linked']}")
    if results["errors"]:
        print(f"Errors: {len(results['errors'])}")
        for e in results["errors"]:
            print(f"  Run {e['run_id'][:8]}: {e['error']}")

    if dry_run:
        print("\nRe-run without --dry-run to apply changes.")
