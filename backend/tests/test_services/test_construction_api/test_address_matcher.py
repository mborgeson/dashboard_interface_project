"""Tests for the address normalization and fuzzy matching module."""

import pytest

from app.services.construction_api.address_matcher import (
    find_matching_project,
    normalize_address,
    normalize_city,
    normalize_zip,
)


class TestNormalizeAddress:
    def test_basic_normalization(self):
        assert normalize_address("123 Main St") == "123 MAIN ST"

    def test_strips_unit_suffix(self):
        assert normalize_address("456 Oak Ave Suite 200") == "456 OAK AVE"
        assert normalize_address("456 Oak Ave Apt B") == "456 OAK AVE"
        assert normalize_address("456 Oak Ave Unit 3A") == "456 OAK AVE"
        assert normalize_address("456 Oak Ave #12") == "456 OAK AVE"

    def test_standardizes_street_suffixes(self):
        assert normalize_address("100 Elm Street") == "100 ELM ST"
        assert normalize_address("200 Pine Avenue") == "200 PINE AVE"
        assert normalize_address("300 Oak Boulevard") == "300 OAK BLVD"
        assert normalize_address("400 Maple Drive") == "400 MAPLE DR"
        assert normalize_address("500 Cedar Lane") == "500 CEDAR LN"
        assert normalize_address("600 Birch Road") == "600 BIRCH RD"

    def test_standardizes_directionals(self):
        assert normalize_address("100 North Main St") == "100 N MAIN ST"
        assert normalize_address("200 South Central Ave") == "200 S CENTRAL AVE"
        assert normalize_address("300 East Broadway Blvd") == "300 E BROADWAY BLVD"
        assert normalize_address("400 West Baseline Rd") == "400 W BASELINE RD"

    def test_removes_punctuation(self):
        assert normalize_address("123 N. Main St.") == "123 N MAIN ST"

    def test_none_returns_empty(self):
        assert normalize_address(None) == ""

    def test_empty_returns_empty(self):
        assert normalize_address("") == ""

    def test_collapses_whitespace(self):
        assert normalize_address("  123   Main   St  ") == "123 MAIN ST"


class TestNormalizeCity:
    def test_basic(self):
        assert normalize_city("Mesa") == "MESA"
        assert normalize_city("  tempe  ") == "TEMPE"

    def test_none(self):
        assert normalize_city(None) == ""


class TestNormalizeZip:
    def test_five_digit(self):
        assert normalize_zip("85201") == "85201"

    def test_zip_plus_four(self):
        assert normalize_zip("85201-1234") == "85201"

    def test_none(self):
        assert normalize_zip(None) == ""

    def test_empty(self):
        assert normalize_zip("") == ""


class TestFindMatchingProject:
    """Test the entity resolution logic."""

    SAMPLE_PROJECTS = [
        {
            "id": 1,
            "normalized_address": "1234 E MAIN ST",
            "normalized_city": "MESA",
            "normalized_zip": "85201",
        },
        {
            "id": 2,
            "normalized_address": "5678 N SCOTTSDALE RD",
            "normalized_city": "SCOTTSDALE",
            "normalized_zip": "85251",
        },
        {
            "id": 3,
            "normalized_address": "900 S MILL AVE",
            "normalized_city": "TEMPE",
            "normalized_zip": "85281",
        },
    ]

    def test_exact_match_with_zip(self):
        match = find_matching_project(
            "1234 E MAIN ST", "MESA", "85201", self.SAMPLE_PROJECTS
        )
        assert match is not None
        assert match["id"] == 1

    def test_exact_match_without_zip(self):
        match = find_matching_project(
            "900 S MILL AVE", "TEMPE", "", self.SAMPLE_PROJECTS
        )
        assert match is not None
        assert match["id"] == 3

    def test_no_match(self):
        match = find_matching_project(
            "999 W UNKNOWN BLVD", "MESA", "85201", self.SAMPLE_PROJECTS
        )
        assert match is None

    def test_city_mismatch_no_match(self):
        """Same address, wrong city — should not match."""
        match = find_matching_project(
            "1234 E MAIN ST", "PHOENIX", "85201", self.SAMPLE_PROJECTS
        )
        assert match is None

    def test_fuzzy_match_high_overlap(self):
        """Address with slight variation should fuzzy-match."""
        projects = [
            {
                "id": 10,
                "normalized_address": "1234 E MAIN ST",
                "normalized_city": "MESA",
                "normalized_zip": "85201",
            },
        ]
        # "1234 E MAIN" is close to "1234 E MAIN ST" (3/4 tokens overlap)
        match = find_matching_project(
            "1234 E MAIN", "MESA", "85201", projects, fuzzy_threshold=0.6
        )
        assert match is not None
        assert match["id"] == 10

    def test_fuzzy_match_below_threshold(self):
        """Address with too little overlap should not match."""
        projects = [
            {
                "id": 10,
                "normalized_address": "1234 E MAIN ST",
                "normalized_city": "MESA",
                "normalized_zip": "85201",
            },
        ]
        # Only "MESA" overlap at the city level, address has low overlap
        match = find_matching_project(
            "9999 W BROADWAY BLVD", "MESA", "85201", projects, fuzzy_threshold=0.7
        )
        assert match is None

    def test_empty_address_no_match(self):
        match = find_matching_project(
            "", "MESA", "85201", self.SAMPLE_PROJECTS
        )
        assert match is None

    def test_empty_projects_no_match(self):
        match = find_matching_project(
            "1234 E MAIN ST", "MESA", "85201", []
        )
        assert match is None
