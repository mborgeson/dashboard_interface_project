"""Register conftest_pg fixtures for PG integration tests.

Uses a wildcard import instead of ``pytest_plugins`` to avoid the pytest
restriction on defining ``pytest_plugins`` in non-top-level conftest files.
"""

from tests.conftest_pg import *  # noqa: F401, F403
