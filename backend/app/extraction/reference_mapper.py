"""
Reference mapping for UW model groups.

4-tier auto-mapping system that maps group file cells to the canonical
field vocabulary from the production reference file:

  Tier 1: Same sheet + same data cell address → direct match (high confidence)
  Tier 2: Same sheet + same label text at different address → shifted match (medium)
  Tier 3: Different sheet + same label text → renamed sheet match (low)
  Tier 4: Same sheet + synonym match via field_synonyms.json → semantic match

Also provides property name reconciliation (exact, normalized, fuzzy, unmatched).
"""

from dataclasses import asdict, dataclass, field
from typing import Any

import structlog

from .cell_mapping import CellMapping
from .fingerprint import FileFingerprint

logger = structlog.get_logger().bind(component="reference_mapper")


@dataclass
class MappingMatch:
    """A single field mapping match from a group to canonical vocabulary."""

    field_name: str
    source_sheet: str
    source_cell: str
    match_tier: int  # 1-4
    confidence: float  # 0.0-1.0
    label_text: str = ""
    category: str = ""
    production_sheet: str = ""
    production_cell: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GroupReferenceMapping:
    """Complete reference mapping for a file group."""

    group_name: str
    mappings: list[MappingMatch] = field(default_factory=list)
    unmapped_fields: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    tier_counts: dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_name": self.group_name,
            "mappings": [m.to_dict() for m in self.mappings],
            "unmapped_fields": self.unmapped_fields,
            "overall_confidence": self.overall_confidence,
            "tier_counts": self.tier_counts,
            "total_mapped": len(self.mappings),
            "total_unmapped": len(self.unmapped_fields),
        }


@dataclass
class PropertyMatch:
    """Result of property name reconciliation."""

    file_property_name: str
    matched_property_name: str | None = None
    match_tier: int = 4  # 1=exact, 2=normalized, 3=fuzzy, 4=unmatched
    edit_distance: int | None = None
    token_overlap: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def auto_map_group(
    group_name: str,
    production_mappings: dict[str, CellMapping],
    representative_fp: FileFingerprint,
    synonyms: dict[str, list[str]] | None = None,
) -> GroupReferenceMapping:
    """
    Auto-map a group's cells to the canonical field vocabulary.

    Uses the representative fingerprint to locate labels in the group's
    file structure, then maps them to production CellMapping entries
    via a 4-tier matching system.

    Args:
        group_name: Name of the group.
        production_mappings: Dict of field_name -> CellMapping from production reference.
        representative_fp: Fingerprint of a representative file from the group.
        synonyms: Optional dict of canonical_name -> [synonym1, synonym2, ...].

    Returns:
        GroupReferenceMapping with all matched and unmatched fields.
    """
    # Build label index from representative fingerprint
    fp_labels = _build_label_index(representative_fp)

    # Build sheet-name mapping from fingerprint
    fp_sheet_names = {s.name for s in representative_fp.sheets}

    mappings: list[MappingMatch] = []
    unmapped: list[str] = []
    tier_counts: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}

    # Build synonym reverse lookup
    synonym_lookup: dict[str, str] = {}
    if synonyms:
        for canonical, syns in synonyms.items():
            for syn in syns:
                synonym_lookup[syn.upper().strip()] = canonical

    for field_name, mapping in production_mappings.items():
        match = _find_best_match(
            field_name=field_name,
            mapping=mapping,
            fp_labels=fp_labels,
            fp_sheet_names=fp_sheet_names,
            synonym_lookup=synonym_lookup,
        )

        if match is not None:
            mappings.append(match)
            tier_counts[match.match_tier] = tier_counts.get(match.match_tier, 0) + 1
        else:
            unmapped.append(field_name)

    # Compute overall confidence
    total = len(mappings) + len(unmapped)
    if total > 0:
        weighted_sum = sum(m.confidence for m in mappings)
        overall_confidence = weighted_sum / total
    else:
        overall_confidence = 0.0

    result = GroupReferenceMapping(
        group_name=group_name,
        mappings=mappings,
        unmapped_fields=unmapped,
        overall_confidence=round(overall_confidence, 3),
        tier_counts=tier_counts,
    )

    logger.info(
        "auto_map_completed",
        group=group_name,
        total_fields=total,
        mapped=len(mappings),
        unmapped=len(unmapped),
        tier_counts=tier_counts,
        overall_confidence=result.overall_confidence,
    )

    return result


def _build_label_index(fp: FileFingerprint) -> dict[str, list[dict[str, str]]]:
    """
    Build a lookup of normalized label text → list of {sheet, label_type}.

    This allows quick matching of production labels to fingerprint labels.
    """
    index: dict[str, list[dict[str, str]]] = {}

    for sheet in fp.sheets:
        for label in sheet.header_labels:
            key = label.strip().upper()
            index.setdefault(key, []).append(
                {
                    "sheet": sheet.name,
                    "type": "header",
                }
            )
        for label in sheet.col_a_labels:
            key = label.strip().upper()
            index.setdefault(key, []).append(
                {
                    "sheet": sheet.name,
                    "type": "col_a",
                }
            )

    return index


def _find_best_match(
    field_name: str,
    mapping: CellMapping,
    fp_labels: dict[str, list[dict[str, str]]],
    fp_sheet_names: set[str],
    synonym_lookup: dict[str, str],
) -> MappingMatch | None:
    """
    Find the best tier match for a production field in the fingerprint.

    Tier 1: Same sheet exists in fingerprint (direct structure match)
    Tier 2: Same sheet + label text found at different position
    Tier 3: Label text found in different sheet
    Tier 4: Synonym match
    """
    prod_sheet = mapping.sheet_name
    prod_cell = mapping.cell_address
    prod_desc = mapping.description.strip().upper()

    # Tier 1: Same sheet exists in fingerprint → direct match
    if prod_sheet in fp_sheet_names:
        # Sheet exists — check if description label exists in that sheet
        label_entries = fp_labels.get(prod_desc, [])
        same_sheet_entries = [e for e in label_entries if e["sheet"] == prod_sheet]

        if same_sheet_entries:
            # Label found in same sheet — Tier 1 (highest confidence)
            return MappingMatch(
                field_name=field_name,
                source_sheet=prod_sheet,
                source_cell=prod_cell,
                match_tier=1,
                confidence=0.95,
                label_text=mapping.description,
                category=mapping.category,
                production_sheet=prod_sheet,
                production_cell=prod_cell,
            )
        else:
            # Sheet exists but label not found — still Tier 1 (structural match)
            return MappingMatch(
                field_name=field_name,
                source_sheet=prod_sheet,
                source_cell=prod_cell,
                match_tier=1,
                confidence=0.85,
                label_text=mapping.description,
                category=mapping.category,
                production_sheet=prod_sheet,
                production_cell=prod_cell,
            )

    # Tier 2: Label found in fingerprint (same label, any sheet)
    label_entries = fp_labels.get(prod_desc, [])
    if label_entries:
        # Pick best match (prefer header over col_a)
        best = sorted(label_entries, key=lambda e: 0 if e["type"] == "header" else 1)[0]
        return MappingMatch(
            field_name=field_name,
            source_sheet=best["sheet"],
            source_cell=prod_cell,
            match_tier=2,
            confidence=0.70,
            label_text=mapping.description,
            category=mapping.category,
            production_sheet=prod_sheet,
            production_cell=prod_cell,
        )

    # Tier 3: Partial label match (first 3+ words match)
    words = prod_desc.split()
    if len(words) >= 3:
        prefix = " ".join(words[:3])
        for label_key, entries in fp_labels.items():
            if label_key.startswith(prefix):
                best = entries[0]
                return MappingMatch(
                    field_name=field_name,
                    source_sheet=best["sheet"],
                    source_cell=prod_cell,
                    match_tier=3,
                    confidence=0.50,
                    label_text=mapping.description,
                    category=mapping.category,
                    production_sheet=prod_sheet,
                    production_cell=prod_cell,
                )

    # Tier 4: Synonym match
    canonical = synonym_lookup.get(prod_desc)
    if canonical:
        canonical_entries = fp_labels.get(canonical.upper(), [])
        if canonical_entries:
            best = canonical_entries[0]
            return MappingMatch(
                field_name=field_name,
                source_sheet=best["sheet"],
                source_cell=prod_cell,
                match_tier=4,
                confidence=0.40,
                label_text=mapping.description,
                category=mapping.category,
                production_sheet=prod_sheet,
                production_cell=prod_cell,
            )

    # No match found
    return None


def reconcile_property_names(
    file_property_names: list[str],
    known_properties: list[str],
    max_edit_distance: int = 3,
) -> list[PropertyMatch]:
    """
    Reconcile file-derived property names to known DB property names.

    Tier 1: Exact match (case-insensitive)
    Tier 2: Normalized match (strip common suffixes)
    Tier 3: Fuzzy match (Levenshtein <= max_edit_distance OR >= 90% token overlap)
    Tier 4: Unmatched

    Args:
        file_property_names: Property names derived from files.
        known_properties: Known property names from the database.
        max_edit_distance: Maximum Levenshtein distance for fuzzy matching.

    Returns:
        List of PropertyMatch results.
    """
    known_lower = {p.lower(): p for p in known_properties}
    known_normalized = {_normalize_property_name(p): p for p in known_properties}

    results: list[PropertyMatch] = []

    for name in file_property_names:
        # Tier 1: Exact (case-insensitive)
        if name.lower() in known_lower:
            results.append(
                PropertyMatch(
                    file_property_name=name,
                    matched_property_name=known_lower[name.lower()],
                    match_tier=1,
                )
            )
            continue

        # Tier 2: Normalized
        norm = _normalize_property_name(name)
        if norm in known_normalized:
            results.append(
                PropertyMatch(
                    file_property_name=name,
                    matched_property_name=known_normalized[norm],
                    match_tier=2,
                )
            )
            continue

        # Tier 3: Fuzzy
        best_match = _fuzzy_match(name, known_properties, max_edit_distance)
        if best_match is not None:
            results.append(best_match)
            continue

        # Tier 4: Unmatched
        results.append(
            PropertyMatch(
                file_property_name=name,
                match_tier=4,
            )
        )

    return results


def _normalize_property_name(name: str) -> str:
    """
    Normalize a property name by stripping common suffixes.

    Removes: "Apartments", "LLC", "LP", "Inc", city names like "- Phoenix",
    and common real estate suffixes.
    """
    import re

    normalized = name.strip()

    # Remove common suffixes
    suffixes = [
        r"\s*-\s*Phoenix$",
        r"\s*-\s*Tempe$",
        r"\s*-\s*Mesa$",
        r"\s*-\s*Scottsdale$",
        r"\s*-\s*Gilbert$",
        r"\s*-\s*Chandler$",
        r"\s+Apartments?$",
        r"\s+LLC$",
        r"\s+LP$",
        r"\s+Inc\.?$",
        r"\s+Phase\s+\w+$",
    ]

    for suffix in suffixes:
        normalized = re.sub(suffix, "", normalized, flags=re.IGNORECASE)

    return normalized.strip().lower()


def _fuzzy_match(
    name: str,
    candidates: list[str],
    max_edit_distance: int,
) -> PropertyMatch | None:
    """
    Find the best fuzzy match using Levenshtein distance and token overlap.
    """
    best: PropertyMatch | None = None
    best_score = float("inf")

    name_tokens = set(name.lower().split())

    for candidate in candidates:
        # Levenshtein distance
        dist = _levenshtein(name.lower(), candidate.lower())
        if dist <= max_edit_distance and dist < best_score:
            best_score = dist
            best = PropertyMatch(
                file_property_name=name,
                matched_property_name=candidate,
                match_tier=3,
                edit_distance=dist,
            )

        # Token overlap
        cand_tokens = set(candidate.lower().split())
        if name_tokens and cand_tokens:
            overlap = len(name_tokens & cand_tokens) / max(
                len(name_tokens), len(cand_tokens)
            )
            if overlap >= 0.9:
                effective_score = 1  # Better than most edit distances
                if best is None or effective_score < best_score:
                    best_score = effective_score
                    best = PropertyMatch(
                        file_property_name=name,
                        matched_property_name=candidate,
                        match_tier=3,
                        token_overlap=round(overlap, 3),
                    )

    return best


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]
