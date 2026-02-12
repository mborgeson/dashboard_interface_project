"""
API endpoints for UW Model File Grouping & Data Extraction pipeline.

Each endpoint corresponds to a pipeline phase. Phases must be run in order:
  Phase 1: POST /discover → discovery manifest
  Phase 2: POST /fingerprint → fingerprints + POST /group (via /fingerprint)
  Phase 3: POST /reference-map → auto-mapping
  Phase 4: POST /conflict-check → conflicts, POST /extract/{name} → extraction
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_sync_db
from app.extraction.group_pipeline import GroupExtractionPipeline
from app.schemas.grouping import (
    BatchExtractionRequest,
    BatchExtractionResponse,
    ConflictCheckResponse,
    DiscoveryResponse,
    FingerprintResponse,
    GroupApprovalResponse,
    GroupDetailResponse,
    GroupExtractionRequest,
    GroupExtractionResponse,
    GroupListResponse,
    GroupSummary,
    PipelineStatusResponse,
    ReferenceMappingResponse,
)

logger = structlog.get_logger().bind(component="grouping_api")

router = APIRouter(prefix="/grouping", tags=["extraction-grouping"])


def _get_pipeline() -> GroupExtractionPipeline:
    """Create pipeline instance."""
    return GroupExtractionPipeline()


# ------------------------------------------------------------------
# Pipeline Status
# ------------------------------------------------------------------


@router.get("/status", response_model=PipelineStatusResponse)
def get_pipeline_status(pipeline: GroupExtractionPipeline = Depends(_get_pipeline)):
    """Get current pipeline status including phase completion and stats."""
    status = pipeline.get_status()
    return PipelineStatusResponse(**status)


# ------------------------------------------------------------------
# Phase 1: Discovery
# ------------------------------------------------------------------


@router.post("/discover", response_model=DiscoveryResponse)
def run_discovery(
    files: list[dict[str, Any]] | None = None,
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """
    Phase 1: Discover candidate UW model files.

    Pass a list of file info dicts, or call with empty body to trigger
    discovery from configured sources.
    """
    if files is None:
        files = []

    try:
        manifest = pipeline.run_discovery(files)
    except Exception as e:
        logger.error("discovery_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Discovery failed: {e}") from e

    return DiscoveryResponse(
        total_scanned=manifest["total_scanned"],
        candidates_accepted=manifest["candidates_accepted"],
        candidates_skipped=manifest["candidates_skipped"],
        duplicates_removed=manifest["duplicates_removed"],
        batch_info=manifest.get("batch_info"),
    )


@router.get("/manifest")
def get_manifest(pipeline: GroupExtractionPipeline = Depends(_get_pipeline)):
    """View the discovery manifest."""
    import json

    manifest_path = pipeline.data_dir / "discovery_manifest.json"

    if not manifest_path.exists():
        raise HTTPException(
            status_code=404, detail="Discovery manifest not found. Run discovery first."
        )

    return json.loads(manifest_path.read_text())


# ------------------------------------------------------------------
# Phase 2: Fingerprinting & Grouping
# ------------------------------------------------------------------


@router.post("/fingerprint", response_model=FingerprintResponse)
def run_fingerprint(
    file_paths: list[str] | None = None,
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """
    Phase 2: Fingerprint candidate files and auto-group them.

    Optionally provide explicit file paths. Otherwise reads from
    discovery manifest.
    """
    # Check prerequisite
    cfg = pipeline.config
    if not cfg.discovery_completed_at and not file_paths:
        raise HTTPException(
            status_code=400,
            detail="Discovery has not been run. Run POST /discover first or provide file_paths.",
        )

    if file_paths is None:
        import json

        manifest_path = pipeline.data_dir / "discovery_manifest.json"
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="Discovery manifest not found.")
        manifest = json.loads(manifest_path.read_text())
        file_paths = [
            f.get("path", f.get("file_path", "")) for f in manifest.get("files", [])
        ]

    try:
        fp_dicts = pipeline.run_fingerprinting(file_paths)
    except Exception as e:
        logger.error("fingerprinting_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Fingerprinting failed: {e}"
        ) from e

    populated = sum(1 for fp in fp_dicts if fp.get("population_status") == "populated")
    sparse = sum(1 for fp in fp_dicts if fp.get("population_status") == "sparse")
    empty = sum(1 for fp in fp_dicts if fp.get("population_status") == "empty")

    # Auto-run grouping after fingerprinting
    try:
        pipeline.run_grouping()
    except Exception as e:
        logger.warning("auto_grouping_failed", error=str(e))

    return FingerprintResponse(
        total_fingerprinted=len(fp_dicts),
        populated=populated,
        sparse=sparse,
        empty_templates=empty,
    )


# ------------------------------------------------------------------
# Groups
# ------------------------------------------------------------------


@router.get("/groups", response_model=GroupListResponse)
def list_groups(pipeline: GroupExtractionPipeline = Depends(_get_pipeline)):
    """List all file groups."""
    import json

    groups_path = pipeline.data_dir / "groups.json"

    if not groups_path.exists():
        raise HTTPException(
            status_code=404, detail="Groups not found. Run fingerprinting first."
        )

    data = json.loads(groups_path.read_text())
    groups = [
        GroupSummary(
            group_name=g["group_name"],
            file_count=g.get("file_count", len(g.get("files", []))),
            structural_overlap=g.get("structural_overlap", 1.0),
            era=g.get("era", ""),
            sub_variant_count=len(g.get("sub_variants", [])),
        )
        for g in data.get("groups", [])
    ]

    return GroupListResponse(
        groups=groups,
        total_groups=data.get("summary", {}).get("total_groups", len(groups)),
        total_ungrouped=data.get("summary", {}).get("total_ungrouped", 0),
        total_empty_templates=data.get("summary", {}).get("total_empty_templates", 0),
    )


@router.get("/groups/{name}", response_model=GroupDetailResponse)
def get_group_detail(
    name: str,
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """Get detailed info for a specific group."""
    import json

    groups_path = pipeline.data_dir / "groups.json"

    if not groups_path.exists():
        raise HTTPException(status_code=404, detail="Groups not found.")

    data = json.loads(groups_path.read_text())
    for g in data.get("groups", []):
        if g["group_name"] == name:
            return GroupDetailResponse(
                group_name=g["group_name"],
                files=g.get("files", []),
                structural_overlap=g.get("structural_overlap", 1.0),
                era=g.get("era", ""),
                sub_variants=g.get("sub_variants", []),
                variances=g.get("variances", {}),
            )

    raise HTTPException(status_code=404, detail=f"Group '{name}' not found.")


# ------------------------------------------------------------------
# Phase 3: Reference Mapping & Reconciliation
# ------------------------------------------------------------------


@router.post("/reference-map", response_model=ReferenceMappingResponse)
def run_reference_map(
    reference_file_path: str | None = None,
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """Phase 3.1-3.3: Auto-map groups to canonical field vocabulary."""
    cfg = pipeline.config
    if not cfg.grouping_completed_at:
        raise HTTPException(
            status_code=400,
            detail="Grouping has not been run. Run POST /fingerprint first.",
        )

    try:
        results = pipeline.run_reference_mapping(
            reference_file_path=reference_file_path
        )
    except Exception as e:
        logger.error("reference_mapping_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Reference mapping failed: {e}"
        ) from e

    total_mapped = sum(r.get("total_mapped", 0) for r in results.values())
    total_unmapped = sum(r.get("total_unmapped", 0) for r in results.values())

    return ReferenceMappingResponse(
        groups_mapped=len(results),
        total_fields_mapped=total_mapped,
        total_fields_unmapped=total_unmapped,
        per_group=results,
    )


@router.post("/reconcile")
def run_reconciliation(
    known_properties: list[str],
    max_edit_distance: int = 3,
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """Phase 3.4: Reconcile property names to known DB properties."""
    try:
        results = pipeline.run_property_reconciliation(
            known_properties=known_properties,
            max_edit_distance=max_edit_distance,
        )
    except Exception as e:
        logger.error("reconciliation_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Reconciliation failed: {e}"
        ) from e

    return results


# ------------------------------------------------------------------
# Phase 4: Extraction
# ------------------------------------------------------------------


@router.post("/conflict-check", response_model=ConflictCheckResponse)
def run_conflict_check(
    db: Session = Depends(get_sync_db),
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """Phase 4.1: Check for conflicts with existing extraction data."""
    cfg = pipeline.config
    if not cfg.reference_map_completed_at:
        raise HTTPException(
            status_code=400,
            detail="Reference mapping has not been run. Run POST /reference-map first.",
        )

    try:
        conflicts = pipeline.run_conflict_check(db)
    except Exception as e:
        logger.error("conflict_check_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Conflict check failed: {e}"
        ) from e

    total_conflicts = sum(len(c) for c in conflicts.values())
    return ConflictCheckResponse(
        groups_with_conflicts=len(conflicts),
        total_conflicts=total_conflicts,
        conflicts=conflicts,
    )


@router.post("/extract/{name}", response_model=GroupExtractionResponse)
def run_extraction(
    name: str,
    request: GroupExtractionRequest = GroupExtractionRequest(),
    db: Session = Depends(get_sync_db),
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """Phase 4.2: Extract data from a group (dry-run by default)."""
    try:
        report = pipeline.run_group_extraction(
            db=db,
            group_name=name,
            dry_run=request.dry_run,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("extraction_failed", group=name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}") from e

    return GroupExtractionResponse(
        group_name=report["group_name"],
        dry_run=report["dry_run"],
        files_processed=report["files_processed"],
        files_failed=report["files_failed"],
        total_values=report["total_values"],
        started_at=report.get("started_at", ""),
        completed_at=report.get("completed_at", ""),
    )


@router.post("/approve/{name}", response_model=GroupApprovalResponse)
def approve_group(
    name: str,
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """
    Mark a group as approved for live extraction.

    Updates config.json groups[group_name].approved = true.
    Only approved groups can be extracted with dry_run=False in batch mode.
    """
    try:
        approved = pipeline.approve_group(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("approval_failed", group=name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Approval failed: {e}") from e

    return GroupApprovalResponse(
        group_name=name,
        approved=approved,
        message=f"Group '{name}' approved for live extraction.",
    )


@router.post("/extract-batch", response_model=BatchExtractionResponse)
def run_batch_extraction(
    request: BatchExtractionRequest,
    db: Session = Depends(get_sync_db),
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """
    Extract data from multiple groups.

    If group_names is None, extracts all approved groups.
    Use dry_run=True (default) to preview extraction without DB writes.
    """
    try:
        report = pipeline.run_batch_extraction(
            db=db,
            group_names=request.group_names,
            dry_run=request.dry_run,
            stop_on_error=request.stop_on_error,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("batch_extraction_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Batch extraction failed: {e}"
        ) from e

    # Convert per_group dict values to GroupExtractionResponse
    per_group_responses: dict[str, GroupExtractionResponse] = {}
    for group_name, group_report in report.get("per_group", {}).items():
        per_group_responses[group_name] = GroupExtractionResponse(
            group_name=group_report.get("group_name", group_name),
            dry_run=group_report.get("dry_run", request.dry_run),
            files_processed=group_report.get("files_processed", 0),
            files_failed=group_report.get("files_failed", 0),
            total_values=group_report.get("total_values", 0),
            started_at=group_report.get("started_at", ""),
            completed_at=group_report.get("completed_at", ""),
        )

    return BatchExtractionResponse(
        groups_processed=report["groups_processed"],
        groups_failed=report["groups_failed"],
        total_files=report["total_files"],
        total_values=report["total_values"],
        per_group=per_group_responses,
    )


@router.post("/validate")
def run_validation(
    db: Session = Depends(get_sync_db),
    pipeline: GroupExtractionPipeline = Depends(_get_pipeline),
):
    """Phase 4.3: Cross-group validation."""
    try:
        report = pipeline.run_cross_group_validation(db)
    except Exception as e:
        logger.error("validation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Validation failed: {e}") from e

    return report
