"""PostgreSQL integration tests (T-DEBT-015, T-DEBT-023).

These tests validate behavior that differs between SQLite and PostgreSQL,
including server_default, real transactions with savepoints, and PG-specific
query features like ILIKE.

All tests are marked with ``@pytest.mark.pg`` and are skipped automatically
when the ``TEST_DATABASE_URL`` environment variable is not set (i.e., when
no PostgreSQL instance is available).
"""
