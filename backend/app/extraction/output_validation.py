"""
B&R Capital Dashboard - Extraction Output Validation

Validates extracted values against expected ranges for multifamily
real estate financial data. Designed to run after extraction pipeline
completes, flagging values that are out of range or suspicious.

Each field type has defined bounds:
- Error: Value is outside any reasonable range (likely extraction error)
- Warning: Value is unusual but possible (needs human review)
- Valid: Value is within expected range

Ranges are calibrated for Phoenix MSA Class B multifamily properties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np
from loguru import logger as _base_logger

logger = _base_logger.bind(component="output_validation")


class ValidationStatus(StrEnum):
    """Status levels for validated values."""

    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of validating a single extracted value."""

    field_name: str
    value: Any
    status: ValidationStatus
    message: str
    rule_name: str = ""


@dataclass
class ValidationSummary:
    """Aggregated results from validating all extracted values."""

    total: int = 0
    valid: int = 0
    warnings: int = 0
    errors: int = 0
    skipped: int = 0
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return self.errors > 0

    @property
    def has_warnings(self) -> bool:
        return self.warnings > 0


@dataclass
class ValidationRule:
    """Definition of a validation rule for a field pattern."""

    name: str
    field_patterns: list[str]
    min_value: float | None = None
    max_value: float | None = None
    warning_min: float | None = None
    warning_max: float | None = None
    is_percentage: bool = False
    description: str = ""

    def matches_field(self, field_name: str) -> bool:
        """Check if this rule applies to a given field name."""
        normalized = field_name.lower().replace(" ", "_").replace("-", "_")
        return any(pattern in normalized for pattern in self.field_patterns)


# --- Validation Rules ---
# Ranges calibrated for Phoenix MSA multifamily (Class B, 100+ units)

VALIDATION_RULES: list[ValidationRule] = [
    ValidationRule(
        name="cap_rate",
        field_patterns=["cap_rate", "caprate", "cap_rt"],
        min_value=0.0,
        max_value=20.0,
        warning_min=2.0,
        warning_max=15.0,
        is_percentage=True,
        description="Cap rate as percentage (0-20%, warn outside 2-15%)",
    ),
    ValidationRule(
        name="purchase_price",
        field_patterns=["purchase_price", "acquisition_price", "sale_price"],
        min_value=100_000,
        max_value=500_000_000,
        warning_min=1_000_000,
        warning_max=200_000_000,
        description="Purchase price in dollars ($100K-$500M)",
    ),
    ValidationRule(
        name="unit_count",
        field_patterns=["unit_count", "total_units", "num_units", "number_of_units"],
        min_value=1,
        max_value=5000,
        warning_min=10,
        warning_max=2000,
        description="Number of units (1-5000, warn outside 10-2000)",
    ),
    ValidationRule(
        name="year_built",
        field_patterns=["year_built", "yr_built", "vintage"],
        min_value=1900,
        max_value=2026,
        warning_min=1950,
        warning_max=2026,
        description="Year built (1900-2026, warn pre-1950)",
    ),
    ValidationRule(
        name="noi",
        field_patterns=["noi", "net_operating_income"],
        min_value=-10_000_000,
        max_value=100_000_000,
        warning_min=0,
        warning_max=50_000_000,
        description="NOI in dollars (-$10M to $100M, warn if negative or >$50M)",
    ),
    ValidationRule(
        name="rent_per_unit",
        field_patterns=[
            "rent_per_unit",
            "avg_rent",
            "average_rent",
            "rent_unit",
            "monthly_rent",
        ],
        min_value=0,
        max_value=10_000,
        warning_min=400,
        warning_max=5_000,
        description="Monthly rent per unit ($0-$10K, warn outside $400-$5K)",
    ),
    ValidationRule(
        name="price_per_unit",
        field_patterns=["price_per_unit", "cost_per_unit", "ppu"],
        min_value=10_000,
        max_value=1_000_000,
        warning_min=30_000,
        warning_max=500_000,
        description="Price per unit ($10K-$1M, warn outside $30K-$500K)",
    ),
    ValidationRule(
        name="occupancy",
        field_patterns=["occupancy", "occ_rate", "physical_occupancy", "economic_occ"],
        min_value=0,
        max_value=100,
        warning_min=50,
        warning_max=100,
        is_percentage=True,
        description="Occupancy as percentage (0-100%, warn below 50%)",
    ),
    ValidationRule(
        name="square_footage",
        field_patterns=[
            "square_footage",
            "sqft",
            "sq_ft",
            "total_sf",
            "rentable_sf",
            "gross_sf",
        ],
        min_value=100,
        max_value=10_000_000,
        warning_min=5_000,
        warning_max=5_000_000,
        description="Square footage (100-10M, warn outside 5K-5M)",
    ),
]


def _is_empty(value: Any) -> bool:
    """Check if a value is None, NaN, NullValue, or empty string."""
    from app.extraction.error_handler import NullValue

    if isinstance(value, NullValue):
        return True
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return bool(isinstance(value, float) and np.isnan(value))


def _to_numeric(value: Any) -> float | None:
    """Attempt to convert a value to float. Returns None if not possible."""
    from app.extraction.error_handler import NullValue

    if isinstance(value, NullValue):
        return None
    if _is_empty(value):
        return None
    if isinstance(value, int | float):
        if isinstance(value, float) and np.isnan(value):
            return None
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("$", "").replace("%", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _validate_field(
    field_name: str,
    value: Any,
    rule: ValidationRule,
) -> ValidationResult:
    """Validate a single field value against a rule."""
    numeric = _to_numeric(value)

    if numeric is None:
        return ValidationResult(
            field_name=field_name,
            value=value,
            status=ValidationStatus.SKIPPED,
            message=f"Non-numeric or missing value for {rule.name}",
            rule_name=rule.name,
        )

    # Check hard bounds (error)
    if rule.min_value is not None and numeric < rule.min_value:
        return ValidationResult(
            field_name=field_name,
            value=numeric,
            status=ValidationStatus.ERROR,
            message=(f"{rule.name}: {numeric} is below minimum {rule.min_value}"),
            rule_name=rule.name,
        )

    if rule.max_value is not None and numeric > rule.max_value:
        return ValidationResult(
            field_name=field_name,
            value=numeric,
            status=ValidationStatus.ERROR,
            message=(f"{rule.name}: {numeric} is above maximum {rule.max_value}"),
            rule_name=rule.name,
        )

    # Check warning bounds
    if rule.warning_min is not None and numeric < rule.warning_min:
        return ValidationResult(
            field_name=field_name,
            value=numeric,
            status=ValidationStatus.WARNING,
            message=(
                f"{rule.name}: {numeric} is below typical minimum {rule.warning_min}"
            ),
            rule_name=rule.name,
        )

    if rule.warning_max is not None and numeric > rule.warning_max:
        return ValidationResult(
            field_name=field_name,
            value=numeric,
            status=ValidationStatus.WARNING,
            message=(
                f"{rule.name}: {numeric} is above typical maximum {rule.warning_max}"
            ),
            rule_name=rule.name,
        )

    return ValidationResult(
        field_name=field_name,
        value=numeric,
        status=ValidationStatus.VALID,
        message=f"{rule.name}: value {numeric} is within expected range",
        rule_name=rule.name,
    )


def validate_extraction_output(
    extracted: dict[str, Any],
    rules: list[ValidationRule] | None = None,
) -> ValidationSummary:
    """
    Validate a dictionary of extracted values against defined rules.

    Iterates over all fields in the extraction output, matches each
    field against applicable validation rules, and collects results.
    Fields that don't match any rule or are internal metadata (prefixed
    with '_') are skipped.

    Args:
        extracted: Dictionary of field_name -> value from extraction.
        rules: Optional custom rules. Defaults to VALIDATION_RULES.

    Returns:
        ValidationSummary with per-field results and aggregate counts.
    """
    if rules is None:
        rules = VALIDATION_RULES

    summary = ValidationSummary()

    for field_name, value in extracted.items():
        # Skip internal metadata fields
        if field_name.startswith("_"):
            continue

        # Find matching rules for this field
        matched_rules = [r for r in rules if r.matches_field(field_name)]

        if not matched_rules:
            continue

        for rule in matched_rules:
            result = _validate_field(field_name, value, rule)
            summary.results.append(result)
            summary.total += 1

            if result.status == ValidationStatus.VALID:
                summary.valid += 1
            elif result.status == ValidationStatus.WARNING:
                summary.warnings += 1
            elif result.status == ValidationStatus.ERROR:
                summary.errors += 1
            elif result.status == ValidationStatus.SKIPPED:
                summary.skipped += 1

    logger.info(
        "extraction_output_validated",
        total=summary.total,
        valid=summary.valid,
        warnings=summary.warnings,
        errors=summary.errors,
        skipped=summary.skipped,
    )

    return summary
