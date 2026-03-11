"""Tests for ETag middleware LRU cache (A-TD-019).

Covers:
- LRU cache basic operations (get, put, eviction)
- Cache capacity enforcement at 500 entries
- Cache integration with ETag computation
"""

import pytest

from app.middleware.etag import ETAG_CACHE_CAPACITY, _LRUETagCache


class TestLRUETagCache:
    """Unit tests for the _LRUETagCache class."""

    def test_default_capacity(self):
        """Default capacity should be 500."""
        assert ETAG_CACHE_CAPACITY == 500
        cache = _LRUETagCache()
        assert cache._capacity == 500

    def test_custom_capacity(self):
        """Cache should accept a custom capacity."""
        cache = _LRUETagCache(capacity=10)
        assert cache._capacity == 10

    def test_get_miss(self):
        """Getting a non-existent key should return None."""
        cache = _LRUETagCache(capacity=10)
        assert cache.get(12345) is None

    def test_put_and_get(self):
        """Stored values should be retrievable."""
        cache = _LRUETagCache(capacity=10)
        cache.put(42, '"abc123"')
        assert cache.get(42) == '"abc123"'

    def test_put_overwrites(self):
        """Putting the same key should overwrite the value."""
        cache = _LRUETagCache(capacity=10)
        cache.put(42, '"old"')
        cache.put(42, '"new"')
        assert cache.get(42) == '"new"'
        assert len(cache) == 1

    def test_len(self):
        """len() should return the number of cached entries."""
        cache = _LRUETagCache(capacity=10)
        assert len(cache) == 0
        cache.put(1, '"a"')
        cache.put(2, '"b"')
        assert len(cache) == 2

    def test_eviction_at_capacity(self):
        """When at capacity, the LRU entry should be evicted on put."""
        cache = _LRUETagCache(capacity=3)
        cache.put(1, '"a"')
        cache.put(2, '"b"')
        cache.put(3, '"c"')

        # At capacity, adding a 4th should evict key=1 (LRU)
        cache.put(4, '"d"')
        assert len(cache) == 3
        assert cache.get(1) is None  # Evicted
        assert cache.get(2) == '"b"'
        assert cache.get(3) == '"c"'
        assert cache.get(4) == '"d"'

    def test_get_promotes_to_mru(self):
        """Accessing an entry should promote it to most-recently-used."""
        cache = _LRUETagCache(capacity=3)
        cache.put(1, '"a"')
        cache.put(2, '"b"')
        cache.put(3, '"c"')

        # Access key=1, promoting it to MRU
        cache.get(1)

        # Now adding key=4 should evict key=2 (LRU), not key=1
        cache.put(4, '"d"')
        assert cache.get(1) == '"a"'  # Still present (was promoted)
        assert cache.get(2) is None  # Evicted (was LRU)

    def test_put_existing_promotes_to_mru(self):
        """Updating an existing entry should promote it to MRU."""
        cache = _LRUETagCache(capacity=3)
        cache.put(1, '"a"')
        cache.put(2, '"b"')
        cache.put(3, '"c"')

        # Update key=1 (promotes to MRU)
        cache.put(1, '"a-updated"')

        # Adding key=4 should evict key=2 (now LRU), not key=1
        cache.put(4, '"d"')
        assert cache.get(1) == '"a-updated"'
        assert cache.get(2) is None

    def test_large_capacity_enforcement(self):
        """Cache should never exceed capacity even with many insertions."""
        capacity = 50
        cache = _LRUETagCache(capacity=capacity)

        for i in range(200):
            cache.put(i, f'"etag-{i}"')

        assert len(cache) == capacity

        # Only the most recent entries should be present
        for i in range(200 - capacity, 200):
            assert cache.get(i) == f'"etag-{i}"'

    def test_eviction_order_is_lru(self):
        """Entries should be evicted in least-recently-used order."""
        cache = _LRUETagCache(capacity=5)

        # Insert 1-5
        for i in range(1, 6):
            cache.put(i, f'"etag-{i}"')

        # Access in specific order: 3, 1, 5 (these become most-recently-used)
        cache.get(3)
        cache.get(1)
        cache.get(5)

        # Insert 3 more -- should evict 2, 4, 3 in that order
        cache.put(6, '"etag-6"')
        assert cache.get(2) is None  # LRU, evicted first

        cache.put(7, '"etag-7"')
        assert cache.get(4) is None  # Next LRU, evicted second

        cache.put(8, '"etag-8"')
        assert cache.get(3) is None  # Next LRU, evicted third

        # 1, 5, 6, 7, 8 should remain
        assert cache.get(1) is not None
        assert cache.get(5) is not None
        assert cache.get(6) is not None
        assert cache.get(7) is not None
        assert cache.get(8) is not None
