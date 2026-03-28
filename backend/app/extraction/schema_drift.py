"""
Schema Drift Detection for UW Model File Groups.

Detects structural changes in new Excel files compared to a group's
baseline fingerprint. Used as a pre-extraction gate in Phase 4 of the
group extraction pipeline.

Stories: UR-023 Stories 1-4
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger as _base_logger

from app.extraction.fingerprint import FileFingerprint, SheetFingerprint

logger = _base_logger.bind(component="schema_drift")

# ---------------------------------------------------------------------------
# Thresholds (Story 3)
# ---------------------------------------------------------------------------
THRESHOLD_OK = 0.95
THRESHOLD_INFO = 0.90
THRESHOLD_WARNING = 0.80


def _classify_severity(score: float) -> str:
    """Classify similarity score into severity level.

    >= 0.95  -> "ok"
    0.90-0.94 -> "info"
    0.80-0.89 -> "warning"
    < 0.80   -> "error"
    """
    if score >= THRESHOLD_OK:
        return "ok"
    if score >= THRESHOLD_INFO:
        return "info"
    if score >= THRESHOLD_WARNING:
        return "warning"
    return "error"


# ---------------------------------------------------------------------------
# DriftResult dataclass (Story 2)
# ---------------------------------------------------------------------------


@dataclass
class DriftResult:
    """Result of comparing a file fingerprint against a group baseline."""

    group_name: str
    file_path: str
    similarity_score: float  # 0.0 to 1.0
    severity: str  # "ok", "info", "warning", "error"
    changed_sheets: list[str] = field(default_factory=list)
    missing_sheets: list[str] = field(default_factory=list)
    new_sheets: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Baseline persistence (Story 1)
# ---------------------------------------------------------------------------


def save_baseline_fingerprint(
    data_dir: Path,
    group_name: str,
    fingerprint: FileFingerprint,
) -> Path:
    """Save a canonical baseline fingerprint JSON for a group.

    Args:
        data_dir: Root data directory for the pipeline.
        group_name: Name of the file group.
        fingerprint: The representative FileFingerprint to store.

    Returns:
        Path to the saved baseline file.
    """
    baselines_dir = data_dir / "baselines"
    baselines_dir.mkdir(parents=True, exist_ok=True)

    baseline_path = baselines_dir / f"{group_name}_baseline.json"
    baseline_path.write_text(json.dumps(fingerprint.to_dict(), indent=2, default=str))

    logger.info(
        "baseline_saved",
        group_name=group_name,
        path=str(baseline_path),
        sheet_count=fingerprint.sheet_count,
    )
    return baseline_path


def load_baseline_fingerprint(
    data_dir: Path,
    group_name: str,
) -> FileFingerprint | None:
    """Load a baseline fingerprint for a group.

    Args:
        data_dir: Root data directory for the pipeline.
        group_name: Name of the file group.

    Returns:
        FileFingerprint if baseline exists, None otherwise.
    """
    baseline_path = data_dir / "baselines" / f"{group_name}_baseline.json"
    if not baseline_path.exists():
        logger.debug("no_baseline_found", group_name=group_name)
        return None

    try:
        data = json.loads(baseline_path.read_text())
        fp = FileFingerprint.from_dict(data)
        logger.debug(
            "baseline_loaded",
            group_name=group_name,
            sheet_count=fp.sheet_count,
        )
        return fp
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(
            "baseline_load_error",
            group_name=group_name,
            error=str(e),
        )
        return None


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------


def _jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard index: |A ∩ B| / |A ∪ B|."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def _dimension_similarity(
    baseline_sheets: list[SheetFingerprint],
    new_sheets: list[SheetFingerprint],
) -> float:
    """Compare sheet dimensions (row_count, col_count) for matching sheets.

    For each sheet present in both fingerprints, compute a per-dimension
    similarity as 1 - |diff| / max(a, b) and average across sheets.
    Sheets missing from either side score 0.
    """
    baseline_by_name = {s.name: s for s in baseline_sheets}
    new_by_name = {s.name: s for s in new_sheets}

    all_names = set(baseline_by_name.keys()) | set(new_by_name.keys())
    if not all_names:
        return 1.0

    total = 0.0
    for name in all_names:
        bs = baseline_by_name.get(name)
        ns = new_by_name.get(name)
        if bs is None or ns is None:
            # Sheet missing on one side — 0 similarity for this sheet
            continue

        row_sim = _ratio_similarity(bs.row_count, ns.row_count)
        col_sim = _ratio_similarity(bs.col_count, ns.col_count)
        total += (row_sim + col_sim) / 2.0

    matched_count = len(set(baseline_by_name.keys()) & set(new_by_name.keys()))
    if matched_count == 0:
        return 0.0
    return total / len(all_names)


def _ratio_similarity(a: int, b: int) -> float:
    """Similarity between two non-negative integers: 1 - |a-b|/max(a,b)."""
    if a == 0 and b == 0:
        return 1.0
    return 1.0 - abs(a - b) / max(a, b)


def _header_similarity(
    baseline_sheets: list[SheetFingerprint],
    new_sheets: list[SheetFingerprint],
) -> float:
    """Compare header labels across matching sheets using Jaccard."""
    baseline_by_name = {s.name: s for s in baseline_sheets}
    new_by_name = {s.name: s for s in new_sheets}

    all_names = set(baseline_by_name.keys()) | set(new_by_name.keys())
    if not all_names:
        return 1.0

    total = 0.0
    for name in all_names:
        bs = baseline_by_name.get(name)
        ns = new_by_name.get(name)
        if bs is None or ns is None:
            continue
        total += _jaccard_similarity(set(bs.header_labels), set(ns.header_labels))

    matched_count = len(set(baseline_by_name.keys()) & set(new_by_name.keys()))
    if matched_count == 0:
        return 0.0
    return total / len(all_names)


# ---------------------------------------------------------------------------
# SchemaDriftDetector (Story 2)
# ---------------------------------------------------------------------------


class SchemaDriftDetector:
    """Detects structural drift between a file and a group baseline.

    Similarity weights:
        - Sheet names (Jaccard):   40%
        - Sheet dimensions:        30%
        - Header label overlap:    30%
    """

    WEIGHT_SHEET_NAMES = 0.40
    WEIGHT_DIMENSIONS = 0.30
    WEIGHT_HEADERS = 0.30

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def check_drift(
        self,
        group_name: str,
        new_fingerprint: FileFingerprint,
    ) -> DriftResult:
        """Compare a new file fingerprint against the group baseline.

        Args:
            group_name: Group identifier.
            new_fingerprint: Fingerprint of the file being checked.

        Returns:
            DriftResult with similarity score, severity, and change details.
        """
        baseline = load_baseline_fingerprint(self.data_dir, group_name)

        if baseline is None:
            logger.info(
                "drift_check_no_baseline",
                group_name=group_name,
                file=new_fingerprint.file_name,
            )
            return DriftResult(
                group_name=group_name,
                file_path=new_fingerprint.file_path,
                similarity_score=1.0,
                severity="ok",
                details={"reason": "no_baseline_available"},
            )

        # Sheet name sets
        baseline_names = {s.name for s in baseline.sheets}
        new_names = {s.name for s in new_fingerprint.sheets}

        missing_sheets = sorted(baseline_names - new_names)
        new_sheets = sorted(new_names - baseline_names)
        changed_sheets = self._detect_changed_sheets(baseline, new_fingerprint)

        # Weighted similarity
        name_sim = _jaccard_similarity(baseline_names, new_names)
        dim_sim = _dimension_similarity(baseline.sheets, new_fingerprint.sheets)
        hdr_sim = _header_similarity(baseline.sheets, new_fingerprint.sheets)

        similarity = (
            self.WEIGHT_SHEET_NAMES * name_sim
            + self.WEIGHT_DIMENSIONS * dim_sim
            + self.WEIGHT_HEADERS * hdr_sim
        )

        # Clamp to [0, 1]
        similarity = max(0.0, min(1.0, similarity))
        severity = _classify_severity(similarity)

        details = {
            "sheet_name_similarity": round(name_sim, 4),
            "dimension_similarity": round(dim_sim, 4),
            "header_similarity": round(hdr_sim, 4),
            "baseline_sheet_count": baseline.sheet_count,
            "new_sheet_count": new_fingerprint.sheet_count,
        }

        logger.info(
            "drift_check_complete",
            group_name=group_name,
            file=new_fingerprint.file_name,
            similarity=round(similarity, 4),
            severity=severity,
            missing_sheets=len(missing_sheets),
            new_sheets=len(new_sheets),
            changed_sheets=len(changed_sheets),
        )

        return DriftResult(
            group_name=group_name,
            file_path=new_fingerprint.file_path,
            similarity_score=round(similarity, 4),
            severity=severity,
            changed_sheets=changed_sheets,
            missing_sheets=missing_sheets,
            new_sheets=new_sheets,
            details=details,
        )

    @staticmethod
    def _detect_changed_sheets(
        baseline: FileFingerprint,
        new_fp: FileFingerprint,
    ) -> list[str]:
        """Identify sheets present in both but with different signatures."""
        baseline_sigs = {s.name: s.signature for s in baseline.sheets}
        new_sigs = {s.name: s.signature for s in new_fp.sheets}

        changed = []
        for name in set(baseline_sigs.keys()) & set(new_sigs.keys()):
            if baseline_sigs[name] != new_sigs[name]:
                changed.append(name)
        return sorted(changed)
