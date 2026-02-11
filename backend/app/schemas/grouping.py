"""
Pydantic schemas for UW Model File Grouping & Data Extraction API.
"""

from typing import Any

from pydantic import BaseModel, Field


class GroupSummary(BaseModel):
    """Summary of a single file group."""

    group_name: str
    file_count: int = 0
    structural_overlap: float = 1.0
    era: str = ""
    sub_variant_count: int = 0


class DiscoveryResponse(BaseModel):
    """Response from Phase 1 discovery."""

    total_scanned: int
    candidates_accepted: int
    candidates_skipped: int
    duplicates_removed: int
    batch_info: dict[str, Any] | None = None


class FingerprintResponse(BaseModel):
    """Response from Phase 2.1 fingerprinting."""

    total_fingerprinted: int
    populated: int
    sparse: int
    empty_templates: int


class GroupListResponse(BaseModel):
    """Response listing all groups."""

    groups: list[GroupSummary]
    total_groups: int
    total_ungrouped: int
    total_empty_templates: int


class GroupDetailResponse(BaseModel):
    """Detailed response for a single group."""

    group_name: str
    files: list[dict[str, Any]] = Field(default_factory=list)
    structural_overlap: float = 1.0
    era: str = ""
    sub_variants: list[str] = Field(default_factory=list)
    variances: dict[str, Any] = Field(default_factory=dict)


class ReferenceMappingResponse(BaseModel):
    """Response from Phase 3 reference mapping."""

    groups_mapped: int
    total_fields_mapped: int
    total_fields_unmapped: int
    per_group: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ConflictCheckResponse(BaseModel):
    """Response from Phase 4.1 conflict check."""

    groups_with_conflicts: int
    total_conflicts: int
    conflicts: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class GroupExtractionRequest(BaseModel):
    """Request to extract data from a group."""

    dry_run: bool = Field(
        default=True, description="If True, produces report without DB writes"
    )


class GroupExtractionResponse(BaseModel):
    """Response from Phase 4.2 group extraction."""

    group_name: str
    dry_run: bool
    files_processed: int
    files_failed: int
    total_values: int
    started_at: str = ""
    completed_at: str = ""


class PipelineStatusResponse(BaseModel):
    """Full pipeline status response."""

    data_dir: str
    phases: dict[str, str]
    stats: dict[str, int]
    created_at: str = ""
    updated_at: str = ""
