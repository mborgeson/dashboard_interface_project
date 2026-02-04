"""
Geocoding service using Nominatim (OpenStreetMap).
Free, no API key required. Rate limited to 1 request/sec per Nominatim policy.
"""

import asyncio

import httpx
from loguru import logger


async def geocode_address(
    street: str,
    city: str,
    state: str,
    zip_code: str | None = None,
) -> tuple[float, float] | None:
    """
    Geocode a street address to (latitude, longitude) using Nominatim.
    Returns None if geocoding fails.
    """
    parts = [p for p in [street, city, state, zip_code] if p and p.strip()]
    query = ", ".join(parts)

    if not query.strip():
        return None

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "us",
    }

    headers = {
        "User-Agent": "BRCapital-Dashboard/1.0 (property geocoding)",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

            if results and len(results) > 0:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                logger.info(f"Geocoded '{query}' -> ({lat}, {lon})")
                return (lat, lon)

            logger.warning(f"No results for '{query}'")
            return None
    except Exception as e:
        logger.error(f"Geocoding failed for '{query}': {e}")
        return None


async def geocode_with_fallback(
    property_name: str,
    street: str | None,
    city: str,
    state: str,
    zip_code: str | None = None,
) -> tuple[float, float] | None:
    """
    Try geocoding with full address, then fall back to city+state.
    Respects Nominatim rate limit (1 req/sec).
    """
    # Try full address first
    if street and street.strip():
        result = await geocode_address(street, city, state, zip_code)
        if result:
            return result
        # Rate limit pause before retry
        await asyncio.sleep(1.1)

    # Fallback: city + state
    result = await geocode_address("", city, state, zip_code)
    return result
