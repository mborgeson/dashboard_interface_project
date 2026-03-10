# ADR-010: Redis caching with rate limiting and ETag support

## Status
Accepted

## Context
Several dashboard pages aggregate data across multiple tables (market analytics, portfolio summary, deal comparisons). These queries are expensive but the underlying data changes infrequently. Without caching, repeated page loads and polling cycles unnecessarily load the database. Additionally, the API needed rate limiting to protect against accidental or abusive request floods.

## Decision
We introduced Redis as an application-level cache and rate-limiting backend:

- **Tiered caching**: Frequently accessed, slow-to-compute endpoints (market data, portfolio KPIs) cache responses in Redis with configurable TTLs. Cache keys include query parameters and user context where results are user-specific.
- **ETag support**: Cached responses include ETag headers derived from content hashes. Clients send `If-None-Match` and receive `304 Not Modified` when data has not changed, reducing payload transfer.
- **Sorted-set sliding window rate limiting**: Each API key/user gets a Redis sorted set tracking request timestamps. The middleware enforces configurable per-endpoint rate limits using a sliding window algorithm, avoiding the burst issues of fixed-window counters.
- **Cache invalidation**: Write operations (create, update, delete) invalidate related cache keys using a tag-based pattern. Models declare their cache tags, and the CRUD layer clears them on mutation.

## Consequences
- Dashboard page loads are significantly faster for repeated visits when underlying data has not changed.
- Redis becomes a runtime dependency; the application falls back to uncached behavior if Redis is unavailable.
- Cache invalidation logic must be maintained alongside CRUD operations to prevent stale data.
- Rate limiting protects the API from excessive load without requiring an external gateway.
