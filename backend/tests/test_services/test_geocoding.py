"""Tests for geocoding service (F-060)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.geocoding import geocode_address, geocode_with_fallback

# ---------------------------------------------------------------------------
# geocode_address — successful lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_address_success():
    """Successful geocoding returns (lat, lon) tuple."""
    mock_response = httpx.Response(
        200,
        json=[{"lat": "33.4484", "lon": "-112.0740"}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ", "85001")

    assert result is not None
    lat, lon = result
    assert lat == pytest.approx(33.4484)
    assert lon == pytest.approx(-112.0740)

    # Verify the request was made with correct params
    call_kwargs = mock_client.get.call_args
    assert call_kwargs[1]["params"]["q"] == "123 Main St, Phoenix, AZ, 85001"
    assert call_kwargs[1]["params"]["format"] == "json"
    assert call_kwargs[1]["params"]["countrycodes"] == "us"
    assert call_kwargs[1]["params"]["limit"] == 1


@pytest.mark.asyncio
async def test_geocode_address_success_without_zip():
    """Geocoding works without zip code."""
    mock_response = httpx.Response(
        200,
        json=[{"lat": "33.4484", "lon": "-112.0740"}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ")

    assert result is not None
    call_kwargs = mock_client.get.call_args
    assert call_kwargs[1]["params"]["q"] == "123 Main St, Phoenix, AZ"


# ---------------------------------------------------------------------------
# geocode_address — no results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_address_no_results():
    """Empty results array returns None."""
    mock_response = httpx.Response(
        200,
        json=[],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("Nonexistent St", "Nowhere", "XX")

    assert result is None


# ---------------------------------------------------------------------------
# geocode_address — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_address_network_error():
    """Network errors return None instead of raising."""
    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ")

    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_timeout_error():
    """Timeout errors return None."""
    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ")

    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_http_error():
    """HTTP 500 error returns None."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ")

    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_invalid_json_response():
    """Malformed JSON in lat/lon fields returns None."""
    mock_response = httpx.Response(
        200,
        json=[{"lat": "not_a_number", "lon": "-112.0740"}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ")

    # float("not_a_number") raises ValueError, caught by except block
    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_missing_keys():
    """Response missing lat/lon keys returns None."""
    mock_response = httpx.Response(
        200,
        json=[{"display_name": "Phoenix, AZ"}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ")

    assert result is None


# ---------------------------------------------------------------------------
# geocode_address — input sanitization / normalization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_address_empty_inputs():
    """All empty/whitespace inputs returns None without making HTTP call."""
    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        result = await geocode_address("", "", "", "")

    # Should not create a client at all
    mock_client_cls.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_whitespace_only():
    """Whitespace-only inputs returns None without HTTP call."""
    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        result = await geocode_address("  ", "  ", "  ")

    mock_client_cls.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_geocode_address_strips_blank_parts():
    """Blank parts are excluded from the query string."""
    mock_response = httpx.Response(
        200,
        json=[{"lat": "33.4484", "lon": "-112.0740"}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # Empty street, should only use city + state
        result = await geocode_address("", "Phoenix", "AZ")

    call_kwargs = mock_client.get.call_args
    assert call_kwargs[1]["params"]["q"] == "Phoenix, AZ"


@pytest.mark.asyncio
async def test_geocode_address_none_zip():
    """None zip_code is filtered out of query."""
    mock_response = httpx.Response(
        200,
        json=[{"lat": "33.4484", "lon": "-112.0740"}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await geocode_address("123 Main St", "Phoenix", "AZ", None)

    call_kwargs = mock_client.get.call_args
    assert call_kwargs[1]["params"]["q"] == "123 Main St, Phoenix, AZ"


# ---------------------------------------------------------------------------
# geocode_address — user agent header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_address_sends_user_agent():
    """Nominatim requires a User-Agent header; verify it is sent."""
    mock_response = httpx.Response(
        200,
        json=[{"lat": "33.0", "lon": "-112.0"}],
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )

    with patch("app.services.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await geocode_address("123 Main St", "Phoenix", "AZ")

    call_kwargs = mock_client.get.call_args
    assert "User-Agent" in call_kwargs[1]["headers"]
    assert "BRCapital" in call_kwargs[1]["headers"]["User-Agent"]


# ---------------------------------------------------------------------------
# geocode_with_fallback — full address succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_with_fallback_full_address_success():
    """When full address succeeds, returns immediately without fallback."""
    with patch(
        "app.services.geocoding.geocode_address", new_callable=AsyncMock
    ) as mock_geocode:
        mock_geocode.return_value = (33.4484, -112.0740)

        result = await geocode_with_fallback(
            "Test Property", "123 Main St", "Phoenix", "AZ", "85001"
        )

    assert result == (33.4484, -112.0740)
    # Should only be called once (full address succeeded)
    mock_geocode.assert_called_once_with("123 Main St", "Phoenix", "AZ", "85001")


# ---------------------------------------------------------------------------
# geocode_with_fallback — fallback to city+state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_with_fallback_falls_back_to_city_state():
    """When full address fails, falls back to city+state after rate limit delay."""
    call_count = 0

    async def mock_geocode(street, city, state, zip_code=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None  # Full address fails
        return (33.4484, -112.0740)  # City+state succeeds

    with (
        patch(
            "app.services.geocoding.geocode_address", side_effect=mock_geocode
        ),
        patch("app.services.geocoding.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        result = await geocode_with_fallback(
            "Test Property", "123 Main St", "Phoenix", "AZ"
        )

    assert result == (33.4484, -112.0740)
    assert call_count == 2
    # Rate limit delay should have been called
    mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# geocode_with_fallback — rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_with_fallback_rate_limit_delay():
    """Rate limit delay uses settings.GEOCODING_RATE_LIMIT_DELAY between retries."""
    async def mock_geocode(street, city, state, zip_code=None):
        return None

    with (
        patch("app.services.geocoding.geocode_address", side_effect=mock_geocode),
        patch("app.services.geocoding.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("app.services.geocoding.settings") as mock_settings,
    ):
        mock_settings.GEOCODING_RATE_LIMIT_DELAY = 1.1
        mock_settings.HTTP_TIMEOUT = 10.0

        await geocode_with_fallback(
            "Test Property", "123 Main St", "Phoenix", "AZ"
        )

    mock_sleep.assert_called_once_with(1.1)


# ---------------------------------------------------------------------------
# geocode_with_fallback — no street skips to fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_with_fallback_no_street():
    """When street is None, goes directly to city+state fallback (no rate limit pause)."""
    with (
        patch(
            "app.services.geocoding.geocode_address", new_callable=AsyncMock
        ) as mock_geocode,
        patch("app.services.geocoding.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_geocode.return_value = (33.4484, -112.0740)

        result = await geocode_with_fallback(
            "Test Property", None, "Phoenix", "AZ"
        )

    assert result == (33.4484, -112.0740)
    # Only one call (city+state), no rate limit pause
    mock_geocode.assert_called_once_with("", "Phoenix", "AZ", None)
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_geocode_with_fallback_empty_street():
    """When street is empty string, goes directly to city+state fallback."""
    with (
        patch(
            "app.services.geocoding.geocode_address", new_callable=AsyncMock
        ) as mock_geocode,
        patch("app.services.geocoding.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_geocode.return_value = (33.4484, -112.0740)

        result = await geocode_with_fallback(
            "Test Property", "   ", "Phoenix", "AZ"
        )

    assert result == (33.4484, -112.0740)
    mock_geocode.assert_called_once_with("", "Phoenix", "AZ", None)
    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# geocode_with_fallback — both attempts fail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_geocode_with_fallback_both_fail():
    """When both full address and city+state fail, returns None."""
    with (
        patch(
            "app.services.geocoding.geocode_address", new_callable=AsyncMock
        ) as mock_geocode,
        patch("app.services.geocoding.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_geocode.return_value = None

        result = await geocode_with_fallback(
            "Test Property", "123 Main St", "Phoenix", "AZ"
        )

    assert result is None
    assert mock_geocode.call_count == 2
