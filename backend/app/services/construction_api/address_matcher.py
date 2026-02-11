"""
Address normalization and fuzzy matching for entity resolution.

Used to match municipal building permit records to existing CoStar
projects in the construction_projects table.

Strategy:
  1. Normalize addresses (uppercase, strip Suite/Apt/Unit, standardize
     street suffixes and directionals).
  2. Exact match on (normalized_address, city, zip_code).
  3. Fallback fuzzy match on (normalized_address, city) using token overlap.
"""

import re

import structlog

logger = structlog.get_logger(__name__)

# Street suffix normalization (USPS standard abbreviations)
_SUFFIX_MAP: dict[str, str] = {
    "STREET": "ST",
    "AVENUE": "AVE",
    "BOULEVARD": "BLVD",
    "DRIVE": "DR",
    "LANE": "LN",
    "ROAD": "RD",
    "COURT": "CT",
    "PLACE": "PL",
    "CIRCLE": "CIR",
    "WAY": "WAY",
    "TRAIL": "TRL",
    "PARKWAY": "PKWY",
    "HIGHWAY": "HWY",
    "TERRACE": "TER",
    "LOOP": "LOOP",
}

# Directional abbreviations
_DIRECTIONAL_MAP: dict[str, str] = {
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
    "NORTHEAST": "NE",
    "NORTHWEST": "NW",
    "SOUTHEAST": "SE",
    "SOUTHWEST": "SW",
}

# Pattern to strip unit/suite/apt identifiers
_UNIT_PATTERN = re.compile(
    r"(?:\b(?:STE|SUITE|APT|APARTMENT|UNIT|BLDG|BUILDING)|#)\s*[\w\-]*$",
    re.IGNORECASE,
)


def normalize_address(raw: str | None) -> str:
    """Normalize an address for matching.

    - Uppercase
    - Strip suite/apt/unit suffixes
    - Standardize street suffixes and directionals
    - Collapse whitespace
    """
    if not raw:
        return ""

    addr = raw.upper().strip()

    # Remove unit/suite identifiers
    addr = _UNIT_PATTERN.sub("", addr).strip()

    # Remove common punctuation
    addr = addr.replace(".", "").replace(",", "").replace("#", "")

    # Split into tokens for suffix/directional replacement
    tokens = addr.split()
    normalized_tokens: list[str] = []

    for token in tokens:
        if token in _DIRECTIONAL_MAP:
            normalized_tokens.append(_DIRECTIONAL_MAP[token])
        elif token in _SUFFIX_MAP:
            normalized_tokens.append(_SUFFIX_MAP[token])
        else:
            normalized_tokens.append(token)

    return " ".join(normalized_tokens)


def normalize_city(raw: str | None) -> str:
    """Normalize city name for matching."""
    if not raw:
        return ""
    return raw.upper().strip()


def normalize_zip(raw: str | None) -> str:
    """Normalize ZIP code (keep first 5 digits)."""
    if not raw:
        return ""
    cleaned = re.sub(r"[^0-9]", "", raw)
    return cleaned[:5]


def _token_overlap_score(a: str, b: str) -> float:
    """Calculate token overlap ratio between two normalized addresses.

    Returns a score from 0.0 to 1.0 where 1.0 means all tokens match.
    """
    tokens_a = set(a.split())
    tokens_b = set(b.split())

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    # Jaccard-like: intersection / union
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def find_matching_project(
    normalized_address: str,
    normalized_city: str,
    normalized_zip: str,
    projects: list[dict],
    fuzzy_threshold: float = 0.7,
) -> dict | None:
    """Find a matching project from a list of candidates.

    Args:
        normalized_address: Normalized permit address.
        normalized_city: Normalized permit city.
        normalized_zip: Normalized permit ZIP code.
        projects: List of dicts with keys: id, normalized_address,
            normalized_city, normalized_zip.
        fuzzy_threshold: Minimum token overlap score for fuzzy match.

    Returns:
        Best matching project dict, or None.
    """
    if not normalized_address:
        return None

    # Phase 1: Exact match on (address, city, zip)
    for proj in projects:
        if (
            proj["normalized_address"] == normalized_address
            and proj["normalized_city"] == normalized_city
            and normalized_zip
            and proj["normalized_zip"] == normalized_zip
        ):
            return proj

    # Phase 2: Exact match on (address, city) ignoring zip
    for proj in projects:
        if (
            proj["normalized_address"] == normalized_address
            and proj["normalized_city"] == normalized_city
        ):
            return proj

    # Phase 3: Fuzzy match on (address, city)
    best_match = None
    best_score = 0.0

    for proj in projects:
        if proj["normalized_city"] != normalized_city:
            continue

        score = _token_overlap_score(normalized_address, proj["normalized_address"])
        if score >= fuzzy_threshold and score > best_score:
            best_score = score
            best_match = proj

    if best_match:
        logger.debug(
            "fuzzy_address_match",
            permit_address=normalized_address,
            matched_address=best_match["normalized_address"],
            score=round(best_score, 3),
        )

    return best_match
