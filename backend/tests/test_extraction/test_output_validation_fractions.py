"""Tests for aligned validation rules (fraction scale, not percentage scale).

Verifies that cap_rate, occupancy, and vacancy_rate use 0.0-1.0 scale
to match domain_validators.py and the actual values stored by the
extraction pipeline.
"""

from app.extraction.output_validation import validate_extraction_output


def test_cap_rate_as_fraction_passes():
    """Cap rate 0.055 (5.5%) should pass validation."""
    data = {"T12_RETURN_ON_PP": 0.055}
    result = validate_extraction_output(data)
    cap_result = next((r for r in result.results if r.field_name == "T12_RETURN_ON_PP"), None)
    assert cap_result is None or cap_result.status == "valid"


def test_cap_rate_as_percentage_fails():
    """Cap rate 5.5 (interpreted as 550%) should fail validation."""
    data = {"T12_RETURN_ON_PP": 5.5}
    result = validate_extraction_output(data)
    cap_result = next((r for r in result.results if r.field_name == "T12_RETURN_ON_PP"), None)
    assert cap_result is not None
    assert cap_result.status in ("error", "warning")


def test_occupancy_as_fraction_passes():
    """Occupancy 0.95 (95%) should pass validation."""
    data = {"OCCUPANCY": 0.95}
    result = validate_extraction_output(data)
    occ_result = next((r for r in result.results if r.field_name == "OCCUPANCY"), None)
    assert occ_result is None or occ_result.status == "valid"


def test_vacancy_75_percent_flags_warning():
    """Vacancy rate 0.75 (75%) should flag a warning -- implausibly high."""
    data = {"VACANCY_LOSS_YEAR_1_RATE": 0.75}
    result = validate_extraction_output(data)
    vac_result = next((r for r in result.results if r.field_name == "VACANCY_LOSS_YEAR_1_RATE"), None)
    assert vac_result is not None
    assert vac_result.status == "warning"
