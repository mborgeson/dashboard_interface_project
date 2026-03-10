# ADR-009: Cursor-based pagination for large datasets

## Status
Accepted

## Context
The original offset-based pagination (`LIMIT/OFFSET`) degrades on large tables because the database must scan and discard all rows before the offset. As the properties and extracted_values tables grew (300+ properties, 12,000+ extracted values), list endpoints became noticeably slower at higher page numbers.

## Decision
We added cursor-based pagination to `CRUDBase` (`backend/app/crud/base.py`) alongside the existing offset pagination. Cursor pagination uses an indexed column (typically `id` or `created_at`) as a seek key, returning results after/before the cursor value.

Key implementation details:
- `get_multi_cursor()` accepts `cursor`, `limit`, and `direction` (forward/backward) parameters.
- The response includes `next_cursor` and `has_more` fields for client-side iteration.
- Offset-based `get_multi()` remains available for endpoints where total count and random page access are needed (e.g., admin tables).
- API endpoints opt in to cursor pagination via query parameters; the default remains offset-based for backward compatibility.

## Consequences
- Large-dataset endpoints maintain consistent response times regardless of position in the result set.
- Cursor pagination does not support jumping to arbitrary pages, so it is best suited for infinite-scroll and feed-style UIs.
- Both pagination styles coexist in `CRUDBase`, adding some method surface area, but each serves a clear use case.
- Clients must store the cursor token between requests rather than a simple page number.
