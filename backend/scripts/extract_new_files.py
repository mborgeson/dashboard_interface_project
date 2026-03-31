"""
Extract data from 28 newly-assigned UW model files across 7 groups.

This script targets ONLY the newly-added files — it does not re-extract
files that were already processed in prior extraction runs.

Approach:
  1. Reads groups.json and identifies the 28 target files by deal name
  2. For each affected group, temporarily patches groups.json on disk so
     it contains ONLY the new files for that group
  3. Calls GroupExtractionPipeline.run_group_extraction() per group
  4. Restores the original groups.json after each group (in a try/finally)
  5. Prints per-group and per-file extraction results

Usage:
    cd backend/
    python scripts/extract_new_files.py --dry-run     # preview (default)
    python scripts/extract_new_files.py               # live extraction
    python scripts/extract_new_files.py --group group_26  # single group only
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

# Ensure `app` is importable when running from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.session import SessionLocal
from app.extraction.group_pipeline import GroupExtractionPipeline

# ── Target files: deal_name → group assignment ──────────────────────────────
# These are the 28 newly-assigned files that need extraction.
NEW_FILES_BY_GROUP: dict[str, list[str]] = {
    "group_26": [
        "Sunrise Chandler",
        "Clarendon Park",
        "Brio on Ray",
        "Copper Palms",
        "Escondido",
        "Lemon & Pear Tree",
        "Mountainside Apartments",
        "Pine Forest",
        "Ravinia",
        "Seneca Terrace",
        "Tides on West Indian School",
    ],
    "group_37": [
        "Canyon Greens",
        "Duo",
        "Gateway Village",
        "Oasis Palms",
        "Point at Cypress Woods",
        "Riverpark Apartments",
        "Sandal Ridge",
        "West Station",
    ],
    "group_40": [
        "Artisan Downtown Chandler",
        "Arts District",
        "Coral Point",
        "Sanctuary on Broadway",
    ],
    "group_33": [
        "Kingsview Apartments",
        "Cranbrook Forest",
    ],
    "group_10": [
        "Tides at Old Town",
    ],
    "group_35": [
        "Plaza 550",
    ],
    "group_39": [
        "Riverton Terrace Apartments",
    ],
}


def _file_matches_deal(file_entry: dict, deal_name: str) -> bool:
    """Check if a groups.json file entry matches a target deal name.

    Matching logic: the deal name appears (case-insensitive) in the file_name
    field, e.g. 'Sunrise Chandler' matches 'Sunrise Chandler UW Model vCurrent.xlsb'.
    """
    file_name = file_entry.get("file_name", "")
    return deal_name.lower() in file_name.lower()


def _filter_group_files(
    group_data: dict, target_deals: list[str]
) -> tuple[list[dict], list[str]]:
    """Filter a group's files to only those matching target deal names.

    Returns:
        Tuple of (matched_file_entries, unmatched_deal_names).
    """
    matched: list[dict] = []
    remaining_deals = set(target_deals)

    for f in group_data.get("files", []):
        for deal in list(remaining_deals):
            if _file_matches_deal(f, deal):
                matched.append(f)
                remaining_deals.discard(deal)
                break

    return matched, sorted(remaining_deals)


def run_extraction(
    dry_run: bool = True,
    target_group: str | None = None,
) -> dict:
    """Run extraction for the 28 newly-assigned files.

    Args:
        dry_run: If True, produces report without DB writes.
        target_group: If set, only extract this single group.

    Returns:
        Summary dict with per-group results.
    """
    data_dir = Path(settings.GROUP_EXTRACTION_DATA_DIR)
    groups_path = data_dir / "groups.json"

    if not groups_path.exists():
        logger.error("groups.json not found at {}", groups_path)
        sys.exit(1)

    # Load original groups.json
    original_content = groups_path.read_text()
    original_data = json.loads(original_content)

    # Determine which groups to process
    groups_to_process = (
        {target_group: NEW_FILES_BY_GROUP[target_group]}
        if target_group
        else NEW_FILES_BY_GROUP
    )

    pipeline = GroupExtractionPipeline()
    summary = {
        "dry_run": dry_run,
        "started_at": datetime.now(UTC).isoformat(),
        "groups_processed": 0,
        "total_files_targeted": sum(len(v) for v in groups_to_process.values()),
        "total_files_processed": 0,
        "total_files_failed": 0,
        "total_values_extracted": 0,
        "per_group": {},
    }

    print(f"\n{'=' * 60}")
    print(f"  Extract New Files — {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"  Groups: {len(groups_to_process)}  |  Files: {summary['total_files_targeted']}")
    print(f"{'=' * 60}\n")

    for group_name, deal_names in groups_to_process.items():
        print(f"\n--- {group_name} ({len(deal_names)} files) ---")

        # Find this group in the original data
        group_entry = None
        for g in original_data.get("groups", []):
            if g["group_name"] == group_name:
                group_entry = g
                break

        if group_entry is None:
            msg = f"Group '{group_name}' not found in groups.json"
            logger.warning(msg)
            summary["per_group"][group_name] = {"error": msg}
            continue

        # Filter to only the new files
        matched_files, unmatched = _filter_group_files(group_entry, deal_names)

        if unmatched:
            logger.warning(
                "unmatched_deals_in_group",
                group=group_name,
                unmatched=unmatched,
            )
            print(f"  WARNING: {len(unmatched)} deal(s) not found: {unmatched}")

        if not matched_files:
            msg = "No matching files found in group"
            logger.warning(msg, group=group_name)
            summary["per_group"][group_name] = {"error": msg}
            continue

        print(f"  Matched {len(matched_files)} file(s):")
        for f in matched_files:
            print(f"    - {f['file_name']}")

        # Build a patched copy of groups.json with only our target files
        patched_data = json.loads(original_content)  # deep copy via re-parse
        for g in patched_data.get("groups", []):
            if g["group_name"] == group_name:
                g["files"] = matched_files
                break

        # Write patched groups.json, run extraction, restore original
        try:
            groups_path.write_text(json.dumps(patched_data, indent=2))
            logger.info(
                "patched_groups_json",
                group=group_name,
                file_count=len(matched_files),
            )

            db = SessionLocal()
            try:
                report = pipeline.run_group_extraction(
                    db=db,
                    group_name=group_name,
                    dry_run=dry_run,
                )

                summary["groups_processed"] += 1
                summary["total_files_processed"] += report.get("files_processed", 0)
                summary["total_files_failed"] += report.get("files_failed", 0)
                summary["total_values_extracted"] += report.get("total_values", 0)
                summary["per_group"][group_name] = {
                    "files_targeted": len(matched_files),
                    "files_processed": report.get("files_processed", 0),
                    "files_failed": report.get("files_failed", 0),
                    "total_values": report.get("total_values", 0),
                    "per_file": report.get("per_file", {}),
                }

                # Print per-file results
                for fp, info in report.get("per_file", {}).items():
                    status = info.get("status", "unknown")
                    name = info.get("property_name", Path(fp).stem)
                    values = info.get("values_extracted", 0)
                    if status == "completed":
                        print(f"    OK  {name}: {values} values")
                    elif status == "skipped":
                        print(f"    SKIP  {Path(fp).name}: {info.get('reason', '')}")
                    else:
                        print(f"    FAIL  {Path(fp).name}: {info.get('error', '')}")

                if not dry_run:
                    db.commit()
            except Exception:
                if not dry_run:
                    db.rollback()
                raise
            finally:
                db.close()

        except Exception as e:
            logger.exception("group_extraction_error", group=group_name)
            summary["per_group"][group_name] = {"error": str(e)}
            print(f"  ERROR: {e}")
        finally:
            # ALWAYS restore the original groups.json
            groups_path.write_text(original_content)
            logger.info("restored_groups_json", group=group_name)

    summary["completed_at"] = datetime.now(UTC).isoformat()

    # Print summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Mode:            {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"  Groups processed: {summary['groups_processed']}/{len(groups_to_process)}")
    print(f"  Files processed:  {summary['total_files_processed']}/{summary['total_files_targeted']}")
    print(f"  Files failed:     {summary['total_files_failed']}")
    print(f"  Values extracted: {summary['total_values_extracted']}")
    print(f"{'=' * 60}\n")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract data from 28 newly-assigned UW model files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview extraction without writing to DB (default: live).",
    )
    parser.add_argument(
        "--group",
        type=str,
        default=None,
        choices=list(NEW_FILES_BY_GROUP.keys()),
        help="Extract only a single group.",
    )
    args = parser.parse_args()

    # Validate --group argument
    if args.group and args.group not in NEW_FILES_BY_GROUP:
        print(f"ERROR: Unknown group '{args.group}'.")
        print(f"Valid groups: {', '.join(NEW_FILES_BY_GROUP.keys())}")
        sys.exit(1)

    result = run_extraction(dry_run=args.dry_run, target_group=args.group)

    # Write summary to a report file
    report_path = Path(settings.GROUP_EXTRACTION_DATA_DIR) / "new_files_extraction_report.json"
    report_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
