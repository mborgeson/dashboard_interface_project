# ADR-007: Soft-delete pattern for deals and transactions

## Status
Accepted

## Context
Deals and transactions represent financial records that must be auditable. Hard-deleting records would lose historical data needed for reporting, compliance, and undo functionality. However, users still need the ability to "delete" records from their active views.

## Decision
We implemented a `SoftDeleteMixin` (`backend/app/models/base.py`) that adds `is_deleted` (boolean, indexed) and `deleted_at` (nullable timestamp) columns to any model. The mixin provides `soft_delete()` and `restore()` methods.

Applied to: `Deal`, `Transaction` (both inherit `SoftDeleteMixin`).

The `CRUDBase` class (`backend/app/crud/base.py`) is soft-delete-aware:
- `get()` and `get_multi()` exclude soft-deleted records by default.
- An `include_deleted` parameter allows queries to include them when needed (admin views, audits).
- `remove()` calls `soft_delete()` on models that support it; hard-deletes otherwise.
- `restore()` reverses a soft-delete.

Dedicated tests in `backend/tests/test_models/test_soft_delete.py` verify the mixin behavior.

## Consequences
- Financial records are never permanently lost through normal application operations.
- All list queries must filter on `is_deleted`, which the `CRUDBase._apply_soft_delete_filter` method handles automatically.
- Database size grows over time since records are never truly removed; periodic archival may be needed for very old soft-deleted records.
- The `is_deleted` index ensures filtering performance does not degrade as the table grows.
