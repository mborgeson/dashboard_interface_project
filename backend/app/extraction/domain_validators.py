"""
Domain validation rules for extracted financial data.

Checks extracted values against plausible ranges for multifamily real estate
metrics.  Flags implausible values with warnings — never rejects them.

Usage:
    from app.extraction.domain_validators import validate_domain_range

    warning = validate_domain_range("GOING_IN_CAP_RATE", 5.0)
    # -> ValidationWarning (5.0 >> 0.15 max)

    warning = validate_domain_range("GOING_IN_CAP_RATE", 0.055)
    # -> None (within range)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger as _base_logger

logger = _base_logger.bind(component="domain_validation")


@dataclass
class DomainRule:
    """Validation rule for a financial field."""

    field_pattern: str  # regex or exact match for field_name
    min_value: float | None = None
    max_value: float | None = None
    expected_type: str = "numeric"  # numeric, percentage, currency, count, year
    description: str = ""

    # Compiled regex cached lazily
    _compiled: re.Pattern[str] | None = field(default=None, repr=False, compare=False)

    def matches(self, field_name: str) -> bool:
        """Check whether *field_name* matches this rule's pattern (case-insensitive)."""
        if self._compiled is None:
            self._compiled = re.compile(self.field_pattern, re.IGNORECASE)
        return self._compiled.search(field_name) is not None


@dataclass
class ValidationWarning:
    """Warning produced when a value is outside domain range."""

    field_name: str
    value: Any
    rule: DomainRule
    reason: str
    severity: str = "warning"  # "warning" or "info"


# ── Domain rules for multifamily real estate financial data ──────────────
# NOTE: More specific patterns MUST come before broader patterns because
# _find_matching_rule() returns the first match.
DOMAIN_RULES: list[DomainRule] = [
    # Cap rates / yields  (specific before generic)
    DomainRule(".*GOING_IN_CAP.*", 0.03, 0.15, "percentage", "Going-in cap rate 3-15%"),
    DomainRule(".*CAP_RATE.*", 0.01, 0.20, "percentage", "Cap rate typically 1-20%"),
    # Returns
    DomainRule(".*IRR.*", -0.30, 0.60, "percentage", "IRR typically -30% to 60%"),
    DomainRule(".*MOIC.*", 0.3, 6.0, "numeric", "MOIC typically 0.3x to 6x"),
    DomainRule(
        ".*RETURN_ON_COST.*", -0.15, 0.40, "percentage", "Return on cost -15% to 40%"
    ),
    # Income / expenses
    DomainRule(".*NOI.*", 50_000, 100_000_000, "currency", "NOI $50K to $100M"),
    DomainRule(
        ".*REVENUE.*", 100_000, 200_000_000, "currency", "Revenue $100K to $200M"
    ),
    DomainRule(
        ".*EXPENSE.*", 10_000, 100_000_000, "currency", "Expenses $10K to $100M"
    ),
    # Property metrics
    DomainRule(
        ".*PURCHASE_PRICE.*",
        500_000,
        1_000_000_000,
        "currency",
        "Purchase price $500K to $1B",
    ),
    DomainRule(".*UNIT_COUNT.*", 1, 5000, "count", "Unit count 1 to 5000"),
    DomainRule(
        ".*PRICE_PER_UNIT.*", 20_000, 800_000, "currency", "Price/unit $20K to $800K"
    ),
    DomainRule(
        ".*RENT.*UNIT.*", 300, 8000, "currency", "Rent/unit $300 to $8000/month"
    ),
    DomainRule(".*OCCUPANCY.*", 0.0, 1.0, "percentage", "Occupancy 0-100%"),
    DomainRule(".*YEAR_BUILT.*", 1900, 2030, "year", "Year built 1900 to 2030"),
    DomainRule(
        r".*SQ.*FT.*|.*SQUARE.*FOOT.*", 100, 10_000_000, "count", "Sq ft 100 to 10M"
    ),
]


def _find_matching_rule(field_name: str) -> DomainRule | None:
    """Return the first DOMAIN_RULE whose pattern matches *field_name*.

    More specific patterns (e.g. GOING_IN_CAP) are listed before broader
    ones (e.g. CAP_RATE) so the first match wins.
    """
    for rule in DOMAIN_RULES:
        if rule.matches(field_name):
            return rule
    return None


def validate_domain_range(field_name: str, value: Any) -> ValidationWarning | None:
    """Check if a value falls within expected domain range for its field type.

    Returns a ``ValidationWarning`` if the value is outside the rule's range,
    ``None`` if the value is acceptable or no rule applies.
    """
    # Coerce to float; bail if not numeric
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    rule = _find_matching_rule(field_name)
    if rule is None:
        return None

    # Check boundaries
    if rule.min_value is not None and numeric_value < rule.min_value:
        reason = (
            f"{field_name}={numeric_value} is below minimum "
            f"{rule.min_value} ({rule.description})"
        )
        return ValidationWarning(
            field_name=field_name,
            value=numeric_value,
            rule=rule,
            reason=reason,
            severity="warning",
        )

    if rule.max_value is not None and numeric_value > rule.max_value:
        reason = (
            f"{field_name}={numeric_value} is above maximum "
            f"{rule.max_value} ({rule.description})"
        )
        return ValidationWarning(
            field_name=field_name,
            value=numeric_value,
            rule=rule,
            reason=reason,
            severity="warning",
        )

    return None


def validate_extracted_values(
    extracted_data: dict[str, Any],
) -> list[ValidationWarning]:
    """Validate all extracted values against domain rules.

    Returns a list of warnings (empty if all values are within range or
    no rules apply).
    """
    warnings: list[ValidationWarning] = []
    for field_name, value in extracted_data.items():
        warning = validate_domain_range(field_name, value)
        if warning is not None:
            warnings.append(warning)
    return warnings
