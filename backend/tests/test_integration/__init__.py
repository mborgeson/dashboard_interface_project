"""PostgreSQL integration tests (T-DEBT-015, T-DEBT-023).

These tests validate behavior that differs between SQLite and PostgreSQL,
including server_default, real transactions with savepoints, and PG-specific
query features like ILIKE.

T-DEBT-023 cleanup: SQLite workarounds throughout the unit test suite
(manual datetime.now(UTC) in fixtures, .replace(tzinfo=None) comparisons,
str(uuid4()) conversions, ON CONFLICT fallback) are documented in-place
with ``SQLite limitation (T-DEBT-023)`` comments that cross-reference
these PG integration tests as the authoritative validation.

All tests are marked with ``@pytest.mark.pg`` and are skipped automatically
when the ``TEST_DATABASE_URL`` environment variable is not set (i.e., when
no PostgreSQL instance is available).
"""
