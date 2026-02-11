"""
UW Model file grouping by structural similarity.

Groups FileFingerprints into clusters based on sheet structure overlap:
- >=95% overlap → same group (identity threshold)
- 80-95% overlap → sub-variant (flagged)
- <80% overlap → separate group

Each group shares the same cell mapping layout and can be extracted
using the same reference file.
"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from .fingerprint import FileFingerprint

logger = structlog.get_logger().bind(component="grouping")


@dataclass
class FileGroup:
    """A group of structurally similar UW model files."""

    group_name: str
    files: list[FileFingerprint] = field(default_factory=list)
    sheet_signature: str = ""
    structural_overlap: float = 1.0
    era: str = ""  # e.g. "2020-2023", "2024+"
    sub_variants: list[str] = field(default_factory=list)
    variances: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["files"] = [
            f.to_dict() if isinstance(f, FileFingerprint) else f for f in self.files
        ]
        d["file_count"] = len(self.files)
        return d


@dataclass
class GroupingResult:
    """Result of the grouping algorithm."""

    groups: list[FileGroup] = field(default_factory=list)
    ungrouped: list[FileFingerprint] = field(default_factory=list)
    empty_templates: list[FileFingerprint] = field(default_factory=list)
    duplicates: list[FileFingerprint] = field(default_factory=list)
    methodology: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "groups": [g.to_dict() for g in self.groups],
            "ungrouped": [f.to_dict() for f in self.ungrouped],
            "empty_templates": [f.to_dict() for f in self.empty_templates],
            "duplicates": [f.to_dict() for f in self.duplicates],
            "methodology": self.methodology,
            "summary": {
                "total_groups": len(self.groups),
                "total_ungrouped": len(self.ungrouped),
                "total_empty_templates": len(self.empty_templates),
                "total_duplicates": len(self.duplicates),
            },
        }


def compute_structural_overlap(fp1: FileFingerprint, fp2: FileFingerprint) -> float:
    """
    Compute Jaccard-like structural overlap between two file fingerprints.

    Compares the union of all header_labels and col_a_labels across sheets.

    Returns:
        Float 0.0-1.0 where 1.0 = identical structure.
    """
    labels1 = _collect_labels(fp1)
    labels2 = _collect_labels(fp2)

    if not labels1 and not labels2:
        # Both empty — compare sheet names
        sheets1 = {s.name for s in fp1.sheets}
        sheets2 = {s.name for s in fp2.sheets}
        if not sheets1 and not sheets2:
            return 1.0
        union = sheets1 | sheets2
        intersection = sheets1 & sheets2
        return len(intersection) / len(union) if union else 1.0

    union = labels1 | labels2
    intersection = labels1 & labels2

    return len(intersection) / len(union) if union else 0.0


def _collect_labels(fp: FileFingerprint) -> set[str]:
    """Collect all normalized labels from a fingerprint."""
    labels: set[str] = set()
    for sheet in fp.sheets:
        for label in sheet.header_labels:
            labels.add(f"{sheet.name}:H:{label.strip().upper()}")
        for label in sheet.col_a_labels:
            labels.add(f"{sheet.name}:A:{label.strip().upper()}")
    return labels


def group_fingerprints(
    fingerprints: list[FileFingerprint],
    identity_threshold: float = 0.95,
    variant_threshold: float = 0.80,
) -> GroupingResult:
    """
    Group file fingerprints by structural similarity.

    Algorithm:
    1. Filter out empty templates
    2. Cluster by identical combined sheet signatures
    3. Within each cluster, compute pairwise structural label overlap
    4. >=identity_threshold → same group
    5. variant_threshold <= overlap < identity_threshold → sub-variant (flagged)
    6. <variant_threshold → separate group

    Args:
        fingerprints: List of FileFingerprints to group.
        identity_threshold: Minimum overlap for same group (default 0.95).
        variant_threshold: Minimum overlap for sub-variant (default 0.80).

    Returns:
        GroupingResult with groups, ungrouped, and empty templates.
    """
    empty_templates: list[FileFingerprint] = []
    populated: list[FileFingerprint] = []

    for fp in fingerprints:
        if fp.population_status == "empty":
            empty_templates.append(fp)
        elif fp.population_status == "error":
            # Skip errored files
            continue
        else:
            populated.append(fp)

    if not populated:
        return GroupingResult(
            empty_templates=empty_templates,
            methodology=_generate_methodology(identity_threshold, variant_threshold),
        )

    # Step 1: Cluster by sorted sheet names (structural signal).
    # Using sheet_name_key instead of combined_signature because the full
    # signature includes deal-specific labels (property names, addresses)
    # which make every file unique even when they share the same template.
    sig_clusters: dict[str, list[FileFingerprint]] = {}
    for fp in populated:
        sig = fp.sheet_name_key
        sig_clusters.setdefault(sig, []).append(fp)

    groups: list[FileGroup] = []
    ungrouped: list[FileFingerprint] = []
    group_counter = 0

    for sig, cluster in sig_clusters.items():
        if len(cluster) == 1:
            # Single file with unique signature — try merging with existing groups
            fp = cluster[0]
            merged = False

            for group in groups:
                if not group.files:
                    continue
                overlap = compute_structural_overlap(fp, group.files[0])
                if overlap >= identity_threshold:
                    group.files.append(fp)
                    group.structural_overlap = min(group.structural_overlap, overlap)
                    merged = True
                    break
                elif overlap >= variant_threshold:
                    group.files.append(fp)
                    group.sub_variants.append(fp.file_name)
                    group.structural_overlap = min(group.structural_overlap, overlap)
                    merged = True
                    break

            if not merged:
                ungrouped.append(fp)
        else:
            # Multiple files with same signature — form a group
            group_counter += 1

            # Compute pairwise overlaps within cluster
            min_overlap = 1.0
            sub_variants: list[str] = []

            if len(cluster) > 1:
                for i in range(len(cluster)):
                    for j in range(i + 1, len(cluster)):
                        overlap = compute_structural_overlap(cluster[i], cluster[j])
                        min_overlap = min(min_overlap, overlap)
                        if overlap < identity_threshold:
                            sub_variants.append(cluster[j].file_name)

            # Determine era from file dates
            era = _compute_era(cluster)

            group_name = _generate_group_name(cluster, group_counter)

            groups.append(
                FileGroup(
                    group_name=group_name,
                    files=cluster,
                    sheet_signature=sig,
                    structural_overlap=min_overlap,
                    era=era,
                    sub_variants=list(set(sub_variants)),
                )
            )

    # Try to merge ungrouped into existing groups
    still_ungrouped: list[FileFingerprint] = []
    for fp in ungrouped:
        merged = False
        for group in groups:
            if not group.files:
                continue
            overlap = compute_structural_overlap(fp, group.files[0])
            if overlap >= variant_threshold:
                group.files.append(fp)
                if overlap < identity_threshold:
                    group.sub_variants.append(fp.file_name)
                group.structural_overlap = min(group.structural_overlap, overlap)
                merged = True
                break
        if not merged:
            still_ungrouped.append(fp)

    # Split low-overlap groups into tighter sub-groups
    groups = _split_low_overlap_groups(
        groups, still_ungrouped, group_counter, variant_threshold
    )

    # Compute variances for each group
    for group in groups:
        group.variances = compute_intra_group_variances(group)

    methodology = _generate_methodology(identity_threshold, variant_threshold)

    result = GroupingResult(
        groups=groups,
        ungrouped=still_ungrouped,
        empty_templates=empty_templates,
        methodology=methodology,
    )

    logger.info(
        "grouping_completed",
        total_files=len(fingerprints),
        groups=len(groups),
        ungrouped=len(still_ungrouped),
        empty_templates=len(empty_templates),
    )

    return result


def _split_low_overlap_groups(
    groups: list[FileGroup],
    ungrouped: list[FileFingerprint],
    start_counter: int,
    min_overlap: float,
) -> list[FileGroup]:
    """
    Split groups with low structural overlap into tighter sub-groups.

    Uses greedy clustering: for each file in a low-overlap group, assign it
    to the first sub-group where it has >= min_overlap with the representative
    (first file). If no match, start a new sub-group. Files that don't fit
    any sub-group are moved to ungrouped.

    Args:
        groups: Current groups (modified in place for splits).
        ungrouped: List to append truly ungrouped files to.
        start_counter: Counter for generating new group names.
        min_overlap: Minimum overlap for sub-group membership.

    Returns:
        Updated list of groups (tight groups unchanged, loose groups split).
    """
    result: list[FileGroup] = []
    counter = start_counter

    for group in groups:
        if group.structural_overlap >= min_overlap or len(group.files) <= 2:
            result.append(group)
            continue

        logger.info(
            "splitting_low_overlap_group",
            group=group.group_name,
            files=len(group.files),
            overlap=f"{group.structural_overlap:.0%}",
        )

        # Greedy clustering within this group
        sub_groups: list[list[FileFingerprint]] = []

        for fp in group.files:
            placed = False
            for sg in sub_groups:
                # Check overlap with representative (first file in sub-group)
                overlap = compute_structural_overlap(fp, sg[0])
                if overlap >= min_overlap:
                    sg.append(fp)
                    placed = True
                    break
            if not placed:
                sub_groups.append([fp])

        # Convert sub-groups back to FileGroup objects
        for sg in sub_groups:
            if len(sg) == 1:
                ungrouped.append(sg[0])
                continue

            counter += 1

            # Compute minimum pairwise overlap
            sg_min_overlap = 1.0
            sg_sub_variants: list[str] = []
            for i in range(len(sg)):
                for j in range(i + 1, len(sg)):
                    ov = compute_structural_overlap(sg[i], sg[j])
                    sg_min_overlap = min(sg_min_overlap, ov)
                    if ov < 0.95:
                        sg_sub_variants.append(sg[j].file_name)

            era = _compute_era(sg)
            name = _generate_group_name(sg, counter)

            result.append(
                FileGroup(
                    group_name=name,
                    files=sg,
                    sheet_signature=sg[0].sheet_name_key,
                    structural_overlap=sg_min_overlap,
                    era=era,
                    sub_variants=list(set(sg_sub_variants)),
                )
            )

        logger.info(
            "split_complete",
            original_group=group.group_name,
            sub_groups=len([sg for sg in sub_groups if len(sg) > 1]),
            singletons=len([sg for sg in sub_groups if len(sg) == 1]),
        )

    return result


def compute_intra_group_variances(group: FileGroup) -> dict[str, Any]:
    """
    Compute structural variance within a group.

    Identifies sheets/labels that are NOT present in all files within the group.

    Returns:
        Dict with variance details.
    """
    if len(group.files) <= 1:
        return {"uniform": True, "varying_labels": [], "varying_sheets": []}

    # Collect labels from each file
    all_file_labels = [_collect_labels(fp) for fp in group.files]

    # Find labels present in ALL files vs some files
    universal = set.intersection(*all_file_labels) if all_file_labels else set()
    any_labels = set.union(*all_file_labels) if all_file_labels else set()
    varying = any_labels - universal

    # Collect sheet names from each file
    all_sheets = [{s.name for s in fp.sheets} for fp in group.files]
    universal_sheets = set.intersection(*all_sheets) if all_sheets else set()
    any_sheets = set.union(*all_sheets) if all_sheets else set()
    varying_sheets = any_sheets - universal_sheets

    return {
        "uniform": len(varying) == 0 and len(varying_sheets) == 0,
        "universal_label_count": len(universal),
        "varying_label_count": len(varying),
        "varying_labels": sorted(varying)[:20],  # Limit for storage
        "universal_sheet_count": len(universal_sheets),
        "varying_sheet_count": len(varying_sheets),
        "varying_sheets": sorted(varying_sheets),
    }


def _compute_era(files: list[FileFingerprint]) -> str:
    """Determine era string from file collection."""
    # Extract years from file names or metadata
    # Simple heuristic: use file name patterns
    years: set[int] = set()
    for fp in files:
        # Try to extract year from filename
        import re

        matches = re.findall(r"20\d{2}", fp.file_name)
        for m in matches:
            years.add(int(m))

    if not years:
        return "unknown"

    min_year = min(years)
    max_year = max(years)

    if min_year == max_year:
        return str(min_year)
    return f"{min_year}-{max_year}"


def _generate_group_name(files: list[FileFingerprint], index: int) -> str:
    """Generate a descriptive group name from files."""
    # Try to find common name pattern
    names = [Path(fp.file_name).stem for fp in files]

    if len(names) == 1:
        return names[0].replace(" ", "_")

    # Find longest common prefix
    prefix = names[0]
    for name in names[1:]:
        while not name.startswith(prefix) and prefix:
            prefix = prefix[:-1]

    if len(prefix) > 5:
        clean = prefix.strip().rstrip("_- ")
        return clean.replace(" ", "_")

    return f"group_{index}"


def _generate_methodology(identity_threshold: float, variant_threshold: float) -> str:
    """Generate methodology documentation."""
    return f"""# UW Model Grouping Methodology

## Algorithm

1. **Population classification**: Files with <20 populated data-region cells
   are classified as empty templates and excluded from grouping.

2. **Sheet name clustering**: Files are first clustered by identical
   sorted sheet names (ignoring deal-specific labels and dimensions).

3. **Structural overlap analysis**: Within clusters, pairwise Jaccard-like
   overlap is computed using normalized header and column-A labels.

4. **Group formation**:
   - Overlap >= {identity_threshold:.0%} → Same group (identity match)
   - {variant_threshold:.0%} <= Overlap < {identity_threshold:.0%} → Sub-variant (flagged)
   - Overlap < {variant_threshold:.0%} → Separate group

5. **Variance analysis**: Each group is analyzed for structural differences
   between files (varying labels, varying sheets).

## Thresholds

| Threshold | Value | Meaning |
|-----------|-------|---------|
| Identity  | {identity_threshold:.0%} | Files considered structurally identical |
| Variant   | {variant_threshold:.0%} | Files considered structural variants |

## Date

Generated: {datetime.now(UTC).isoformat()}
"""
