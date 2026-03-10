# ADR-005: Optimistic locking with version column for deal edits

## Status
Accepted

## Context
Multiple users (analysts, managers) may view and edit the same deal concurrently via the Kanban board or deal detail page. Without concurrency control, the last write silently overwrites earlier changes. Pessimistic locking (database row locks) would degrade UX by blocking concurrent readers.

## Decision
We added a `version` integer column to the `Deal` model (`backend/app/models/deal.py`, line 69) that is incremented on each update. The update endpoint requires the client to send the current version; if it does not match the database value, the request is rejected with a conflict error (HTTP 409). This is tested in `backend/tests/test_api/test_deal_optimistic_locking.py`.

Flow:
1. Client fetches deal, receives `version: N`.
2. Client sends `PUT /deals/{id}` with `version: N` in the payload.
3. Backend checks `deal.version == N`. If true, updates and sets `version = N + 1`. If false, returns 409 Conflict.
4. Client shows a conflict notification and re-fetches the latest state.

## Consequences
- No database-level locks are held during editing, so read performance is unaffected.
- Conflict resolution is pushed to the UI layer -- the client must handle 409 responses gracefully.
- Only the `Deal` model uses this pattern currently; other models (properties, transactions) do not have concurrent edit concerns.
- The version column adds minimal storage overhead (single integer per row).
