"""
Micro-benchmarks for critical hot paths using pytest-benchmark.

Tests measure serialization, validation, hashing, and lookup performance
for components that sit on every request's critical path.

Usage:
    cd backend && python -m pytest tests/performance/test_benchmarks.py -v
    cd backend && python -m pytest tests/performance/test_benchmarks.py -v --benchmark-only

These tests are excluded from CI via the `benchmark` marker.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

# ---------------------------------------------------------------------------
# Mark the entire module so `pytest -m "not benchmark"` skips it
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.benchmark


# ============================================================================
# 1. Pydantic schema validation speed
# ============================================================================


class TestPydanticValidation:
    """Benchmark Pydantic schema instantiation for API-critical models."""

    def test_property_response_validation(self, benchmark) -> None:
        """Measure PropertyResponse schema validation throughput."""
        from app.schemas.property import PropertyResponse

        payload = {
            "id": 1,
            "name": "Test Property",
            "property_type": "multifamily",
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001",
            "county": "Maricopa",
            "market": "Phoenix Metro",
            "submarket": "Central Phoenix",
            "year_built": 1985,
            "year_renovated": 2020,
            "total_units": 200,
            "total_sf": 150000,
            "lot_size_acres": Decimal("3.5"),
            "stories": 3,
            "parking_spaces": 250,
            "purchase_price": Decimal("25000000.00"),
            "current_value": Decimal("28000000.00"),
            "acquisition_date": "2023-01-15",
            "occupancy_rate": Decimal("94.50"),
            "avg_rent_per_unit": Decimal("1250.00"),
            "avg_rent_per_sf": Decimal("1.65"),
            "noi": Decimal("1500000.00"),
            "cap_rate": Decimal("0.0600"),
            "description": "A well-maintained Class B multifamily asset",
            "amenities": {"pool": True, "gym": True, "laundry": True},
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        def validate():
            return PropertyResponse.model_validate(payload)

        result = benchmark(validate)
        assert result.id == 1

    def test_deal_response_validation(self, benchmark) -> None:
        """Measure DealResponse schema validation throughput."""
        from app.schemas.deal import DealResponse

        payload = {
            "id": 1,
            "name": "Test Deal #0001",
            "deal_type": "acquisition",
            "stage": "active_review",
            "stage_order": 1,
            "assigned_user_id": 1,
            "property_id": None,
            "asking_price": Decimal("15000000.00"),
            "offer_price": Decimal("14000000.00"),
            "projected_irr": Decimal("18.500"),
            "projected_coc": Decimal("8.000"),
            "projected_equity_multiple": Decimal("2.10"),
            "hold_period_years": 5,
            "initial_contact_date": "2025-01-15",
            "target_close_date": "2025-06-30",
            "actual_close_date": None,
            "source": "CBRE",
            "priority": "high",
            "competition_level": "medium",
            "notes": "Strong basis play in desirable submarket",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        def validate():
            return DealResponse.model_validate(payload)

        result = benchmark(validate)
        assert result.id == 1

    def test_property_create_validation(self, benchmark) -> None:
        """Measure PropertyCreate input validation (includes field constraints)."""
        from app.schemas.property import PropertyCreate

        payload = {
            "name": "New Acquisition Target",
            "property_type": "multifamily",
            "address": "456 Investment Blvd",
            "city": "Scottsdale",
            "state": "AZ",
            "zip_code": "85251",
            "market": "Phoenix Metro",
            "total_units": 150,
            "year_built": 1992,
            "purchase_price": Decimal("20000000.00"),
            "occupancy_rate": Decimal("92.00"),
            "cap_rate": Decimal("0.055"),
        }

        def validate():
            return PropertyCreate.model_validate(payload)

        result = benchmark(validate)
        assert result.name == "New Acquisition Target"


# ============================================================================
# 2. ETag hash computation
# ============================================================================


class TestETagHashing:
    """Benchmark ETag computation — on every GET response's critical path."""

    @pytest.fixture
    def sample_payloads(self) -> list[bytes]:
        """Generate realistic JSON response bodies of varying sizes."""
        small = json.dumps({"status": "healthy", "version": "2.0.0"}).encode()
        medium = json.dumps(
            {
                "items": [
                    {
                        "id": i,
                        "name": f"Property {i}",
                        "city": "Phoenix",
                        "units": 100 + i,
                        "noi": 1000000 + i * 50000,
                        "cap_rate": 0.055 + i * 0.001,
                    }
                    for i in range(50)
                ],
                "total": 50,
                "page": 1,
            }
        ).encode()
        large = json.dumps(
            {
                "items": [
                    {
                        "id": i,
                        "name": f"Deal {i}",
                        "asking_price": 10000000 + i * 500000,
                        "projected_irr": 15.0 + i * 0.1,
                        "notes": f"Detailed notes for deal {i} " * 10,
                    }
                    for i in range(200)
                ],
                "total": 200,
            }
        ).encode()
        return [small, medium, large]

    def test_sha256_small_payload(self, benchmark, sample_payloads) -> None:
        """SHA-256 hash of a small health-check response (~50 bytes)."""
        body = sample_payloads[0]

        def compute():
            return f'"{hashlib.sha256(body).hexdigest()}"'

        result = benchmark(compute)
        assert result.startswith('"') and result.endswith('"')

    def test_sha256_medium_payload(self, benchmark, sample_payloads) -> None:
        """SHA-256 hash of a 50-item property list response (~5 KB)."""
        body = sample_payloads[1]

        def compute():
            return f'"{hashlib.sha256(body).hexdigest()}"'

        result = benchmark(compute)
        assert len(result) == 66  # 64 hex chars + 2 quotes

    def test_sha256_large_payload(self, benchmark, sample_payloads) -> None:
        """SHA-256 hash of a 200-item deal list response (~50 KB)."""
        body = sample_payloads[2]

        def compute():
            return f'"{hashlib.sha256(body).hexdigest()}"'

        result = benchmark(compute)
        assert len(result) == 66

    def test_builtin_hash_for_cache_key(self, benchmark, sample_payloads) -> None:
        """Python built-in hash used as LRU cache key (should be much faster)."""
        body = sample_payloads[1]

        def compute():
            return hash(body)

        result = benchmark(compute)
        assert isinstance(result, int)


# ============================================================================
# 3. Token blacklist lookup at scale
# ============================================================================


class TestTokenBlacklistPerformance:
    """Benchmark in-memory token blacklist operations at scale."""

    def test_blacklist_lookup_at_1000_entries(self, benchmark) -> None:
        """Measure lookup time with 1000 entries in the memory blacklist."""
        from app.core.token_blacklist import _memory_blacklist

        # Pre-populate with 1000 entries
        now = time.time()
        for i in range(1000):
            _memory_blacklist[f"jti_{i:04d}"] = now + 3600  # expire in 1 hour

        # Lookup a token that IS blacklisted (worst case — must check value)
        target = "jti_0500"

        def lookup():
            exp = _memory_blacklist.get(target, 0)
            return exp > time.time()

        result = benchmark(lookup)
        assert result is True

        # Cleanup
        _memory_blacklist.clear()

    def test_blacklist_lookup_miss_at_1000_entries(self, benchmark) -> None:
        """Measure lookup time for a token NOT in the blacklist (1000 entries)."""
        from app.core.token_blacklist import _memory_blacklist

        now = time.time()
        for i in range(1000):
            _memory_blacklist[f"jti_{i:04d}"] = now + 3600

        missing = "jti_not_blacklisted"

        def lookup():
            exp = _memory_blacklist.get(missing, 0)
            return exp > time.time()

        result = benchmark(lookup)
        assert result is False

        _memory_blacklist.clear()

    def test_blacklist_add_performance(self, benchmark) -> None:
        """Measure time to add a token to the blacklist."""
        from app.core.token_blacklist import _memory_blacklist

        counter = [0]

        def add_token():
            jti = f"bench_jti_{counter[0]}"
            counter[0] += 1
            _memory_blacklist[jti] = time.time() + 1800

        benchmark(add_token)
        _memory_blacklist.clear()

    def test_blacklist_cleanup_at_1000_entries(self, benchmark) -> None:
        """Measure cleanup sweep time with 1000 expired entries."""
        from app.core.token_blacklist import _memory_blacklist, token_blacklist

        def setup_and_cleanup():
            # Fill with expired entries
            past = time.time() - 100
            for i in range(1000):
                _memory_blacklist[f"expired_{i:04d}"] = past
            # Run cleanup
            removed = token_blacklist.cleanup_memory()
            return removed

        result = benchmark(setup_and_cleanup)
        assert result == 1000


# ============================================================================
# 4. JSON serialization throughput
# ============================================================================


class TestJSONSerialization:
    """Benchmark JSON serialization — bottleneck for large API responses."""

    def test_serialize_property_list(self, benchmark) -> None:
        """Serialize a list of 100 property dicts to JSON."""
        properties = [
            {
                "id": i,
                "name": f"Property {i}",
                "property_type": "multifamily",
                "address": f"{i} Main St",
                "city": "Phoenix",
                "state": "AZ",
                "zip_code": "85001",
                "total_units": 100 + i,
                "year_built": 1980 + (i % 40),
                "purchase_price": str(10_000_000 + i * 500_000),
                "cap_rate": str(round(0.04 + i * 0.001, 4)),
                "occupancy_rate": str(round(90.0 + i * 0.05, 2)),
                "noi": str(500_000 + i * 25_000),
            }
            for i in range(100)
        ]
        payload = {"items": properties, "total": 100, "page": 1, "page_size": 100}

        def serialize():
            return json.dumps(payload)

        result = benchmark(serialize)
        assert len(result) > 1000

    def test_deserialize_property_list(self, benchmark) -> None:
        """Deserialize a JSON string of 100 properties."""
        properties = [
            {
                "id": i,
                "name": f"Property {i}",
                "city": "Phoenix",
                "total_units": 100 + i,
                "cap_rate": str(round(0.04 + i * 0.001, 4)),
            }
            for i in range(100)
        ]
        json_str = json.dumps({"items": properties, "total": 100})

        def deserialize():
            return json.loads(json_str)

        result = benchmark(deserialize)
        assert len(result["items"]) == 100


# ============================================================================
# 5. UUID generation (used in request IDs, JTIs)
# ============================================================================


class TestUUIDGeneration:
    """Benchmark UUID generation used in request IDs and JWT identifiers."""

    def test_uuid4_generation(self, benchmark) -> None:
        """Measure uuid4() generation time."""
        result = benchmark(uuid.uuid4)
        assert isinstance(result, uuid.UUID)

    def test_uuid4_to_string(self, benchmark) -> None:
        """Measure uuid4 generation + string conversion."""

        def generate():
            return str(uuid.uuid4())

        result = benchmark(generate)
        assert len(result) == 36  # standard UUID string length
