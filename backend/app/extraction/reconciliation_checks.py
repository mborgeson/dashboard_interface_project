"""
Batch-level reconciliation checks for extracted financial data.

Verifies internal consistency of extracted values, e.g.,
  NOI = Revenue - Operating Expenses

These checks run *after* extraction and log warnings but never block
the extraction pipeline.  Results can be surfaced in dashboards for
manual review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger as _base_logger

logger = _base_logger.bind(component="reconciliation_checks")

# Default tolerance: 5 % relative difference
DEFAULT_TOLERANCE = 0.05


@dataclass
class ReconciliationResult:
    """Outcome of a single reconciliation check."""

    property_name: str
    check_name: str
    expected_value: float
    actual_value: float
    difference: float
    tolerance: float
    passed: bool


def check_noi_reconciliation(
    extracted_data: dict[str, Any],
    property_name: str = "",
    tolerance: float = DEFAULT_TOLERANCE,
) -> ReconciliationResult | None:
    """Verify NOI = Revenue - Operating Expenses for a single property.

    Looks for the following fields in *extracted_data* (keys are the
    canonical field names from the cell-mapping vocabulary):

    * Revenue: ``TOTAL_REVENUE`` or ``EFFECTIVE_GROSS_INCOME``
    * Expenses: ``TOTAL_EXPENSES``
    * NOI: ``NOI`` or ``NOI_YEAR_1``

    Args:
        extracted_data: Dict of field_name -> value from extraction.
        property_name: Human-readable property name for reporting.
        tolerance: Maximum relative difference (default 5 %).

    Returns:
        A ``ReconciliationResult`` if all three components are present,
        or ``None`` if insufficient data for the check.
    """
    # Resolve revenue
    revenue = _safe_float(
        extracted_data.get("TOTAL_REVENUE")
        or extracted_data.get("EFFECTIVE_GROSS_INCOME")
    )
    expenses = _safe_float(extracted_data.get("TOTAL_EXPENSES"))
    noi = _safe_float(extracted_data.get("NOI") or extracted_data.get("NOI_YEAR_1"))

    if revenue is None or expenses is None or noi is None:
        return None

    expected_noi = revenue - expenses
    difference = abs(expected_noi - noi)

    # Relative tolerance: use the larger absolute value as denominator
    denominator = max(abs(expected_noi), abs(noi), 1.0)
    relative_diff = difference / denominator
    passed = relative_diff <= tolerance

    result = ReconciliationResult(
        property_name=property_name,
        check_name="noi_equals_revenue_minus_expenses",
        expected_value=expected_noi,
        actual_value=noi,
        difference=round(difference, 2),
        tolerance=tolerance,
        passed=passed,
    )

    if not passed:
        logger.warning(
            "reconciliation_failed",
            property=property_name,
            check="NOI = Revenue - OpEx",
            expected=expected_noi,
            actual=noi,
            difference=round(difference, 2),
            relative_diff=round(relative_diff, 4),
        )
    else:
        logger.debug(
            "reconciliation_passed",
            property=property_name,
            check="NOI = Revenue - OpEx",
        )

    return result


def run_reconciliation_checks(
    extracted_data: dict[str, Any],
    property_name: str,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[ReconciliationResult]:
    """Run all reconciliation checks for a property's extracted data.

    Currently implements:
    * NOI = Revenue - Operating Expenses

    The list is designed to be extended with additional checks
    (e.g., DSCR consistency, cap-rate cross-check) without breaking
    existing callers.

    Args:
        extracted_data: Dict of field_name -> value from extraction.
        property_name: Human-readable property name for reporting.
        tolerance: Maximum relative difference for checks.

    Returns:
        List of ``ReconciliationResult`` (may be empty if data is
        insufficient for any check).
    """
    results: list[ReconciliationResult] = []

    noi_result = check_noi_reconciliation(extracted_data, property_name, tolerance)
    if noi_result is not None:
        results.append(noi_result)

    if results:
        passed = sum(1 for r in results if r.passed)
        logger.info(
            "reconciliation_summary",
            property=property_name,
            total_checks=len(results),
            passed=passed,
            failed=len(results) - passed,
        )

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        f = float(value)
        import math

        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None
