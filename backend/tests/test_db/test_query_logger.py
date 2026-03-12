"""Tests for the slow query detection and parameter sanitization in query_logger.

Covers:
- Slow query detection (above threshold)
- Fast queries not logged
- Parameter sanitization (passwords, tokens redacted)
- Query truncation and statement type extraction
- Event listener attachment for sync and async engines
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers: _truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    """Tests for the _truncate helper."""

    def test_short_text_unchanged(self) -> None:
        from app.db.query_logger import _truncate

        assert _truncate("SELECT 1", max_len=100) == "SELECT 1"

    def test_long_text_truncated_with_ellipsis(self) -> None:
        from app.db.query_logger import _truncate

        result = _truncate("A" * 2000, max_len=1024)
        assert len(result) == 1027  # 1024 + len("...")
        assert result.endswith("...")

    def test_exact_length_not_truncated(self) -> None:
        from app.db.query_logger import _truncate

        text = "X" * 1024
        assert _truncate(text, max_len=1024) == text


# ---------------------------------------------------------------------------
# Helpers: _sanitize_params
# ---------------------------------------------------------------------------


class TestSanitizeParams:
    """Tests for parameter sanitization."""

    def test_none_returns_none(self) -> None:
        from app.db.query_logger import _sanitize_params

        assert _sanitize_params(None) is None

    def test_list_params_hidden(self) -> None:
        from app.db.query_logger import _sanitize_params

        assert _sanitize_params([1, 2, 3]) == "[positional params hidden]"

    def test_tuple_params_hidden(self) -> None:
        from app.db.query_logger import _sanitize_params

        assert _sanitize_params((1, 2)) == "[positional params hidden]"

    def test_dict_non_sensitive_preserved(self) -> None:
        from app.db.query_logger import _sanitize_params

        result = _sanitize_params({"name": "Alice", "age": 30})
        assert result == {"name": "Alice", "age": 30}

    def test_password_key_redacted(self) -> None:
        from app.db.query_logger import _sanitize_params

        result = _sanitize_params({"username": "alice", "password": "s3cret"})
        assert result["username"] == "alice"
        assert result["password"] == "***"

    def test_token_key_redacted(self) -> None:
        from app.db.query_logger import _sanitize_params

        result = _sanitize_params({"access_token": "abc123", "user_id": 1})
        assert result["access_token"] == "***"
        assert result["user_id"] == 1

    def test_secret_key_redacted(self) -> None:
        from app.db.query_logger import _sanitize_params

        result = _sanitize_params({"api_secret": "xyz", "data": "ok"})
        assert result["api_secret"] == "***"
        assert result["data"] == "ok"

    def test_authorization_key_redacted(self) -> None:
        from app.db.query_logger import _sanitize_params

        result = _sanitize_params({"authorization": "Bearer tok"})
        assert result["authorization"] == "***"

    def test_credential_key_redacted(self) -> None:
        from app.db.query_logger import _sanitize_params

        result = _sanitize_params({"credential": "abc"})
        assert result["credential"] == "***"

    def test_case_insensitive_matching(self) -> None:
        from app.db.query_logger import _sanitize_params

        result = _sanitize_params({"PASSWORD": "x", "Token": "y"})
        assert result["PASSWORD"] == "***"
        assert result["Token"] == "***"

    def test_non_dict_non_list_returns_type_name(self) -> None:
        from app.db.query_logger import _sanitize_params

        assert _sanitize_params(42) == "int"


# ---------------------------------------------------------------------------
# Helpers: _extract_statement_type
# ---------------------------------------------------------------------------


class TestExtractStatementType:
    """Tests for SQL statement type extraction."""

    @pytest.mark.parametrize(
        "sql,expected",
        [
            ("SELECT * FROM users", "SELECT"),
            ("  select id from deals", "SELECT"),
            ("INSERT INTO users VALUES (1)", "INSERT"),
            ("UPDATE deals SET name='x'", "UPDATE"),
            ("DELETE FROM users WHERE id=1", "DELETE"),
            ("CREATE TABLE foo (id INT)", "CREATE"),
            ("ALTER TABLE foo ADD col TEXT", "ALTER"),
            ("DROP TABLE foo", "DROP"),
            ("WITH cte AS (SELECT 1) SELECT * FROM cte", "WITH"),
            ("VACUUM ANALYZE", "OTHER"),
        ],
    )
    def test_statement_types(self, sql: str, expected: str) -> None:
        from app.db.query_logger import _extract_statement_type

        assert _extract_statement_type(sql) == expected


# ---------------------------------------------------------------------------
# Event listeners: slow vs fast query detection
# ---------------------------------------------------------------------------


class TestSlowQueryDetection:
    """Tests for before/after cursor execute event listeners."""

    def _make_conn_info(self) -> dict[str, Any]:
        """Create a mock connection.info dict."""
        return {}

    def _make_mock_conn(self) -> MagicMock:
        conn = MagicMock()
        conn.info = self._make_conn_info()
        return conn

    def test_before_execute_stores_start_time(self) -> None:
        from app.db.query_logger import _CONTEXT_KEY, _before_cursor_execute

        conn = self._make_mock_conn()
        _before_cursor_execute(conn, None, "SELECT 1", None, None, False)
        assert _CONTEXT_KEY in conn.info
        assert isinstance(conn.info[_CONTEXT_KEY], float)

    @patch("app.db.query_logger.DB_QUERY_LATENCY")
    @patch("app.core.config.settings")
    def test_fast_query_not_logged_as_slow(
        self, mock_settings: MagicMock, mock_latency: MagicMock
    ) -> None:
        """A fast query should feed the generic histogram but NOT trigger slow-query logging."""
        from app.db.query_logger import (
            _CONTEXT_KEY,
            _after_cursor_execute,
        )

        mock_settings.SLOW_QUERY_THRESHOLD_MS = 500

        conn = self._make_mock_conn()
        # Simulate a query that took ~1ms
        conn.info[_CONTEXT_KEY] = time.perf_counter()

        with patch("app.db.query_logger.logger") as mock_logger:
            _after_cursor_execute(conn, None, "SELECT 1", None, None, False)
            mock_logger.warning.assert_not_called()

        # Generic histogram should still be observed
        mock_latency.labels.return_value.observe.assert_called_once()

    @patch("app.db.query_logger.SLOW_QUERY_COUNT")
    @patch("app.db.query_logger.SLOW_QUERY_HISTOGRAM")
    @patch("app.db.query_logger.DB_QUERY_LATENCY")
    @patch("app.core.config.settings")
    def test_slow_query_logged(
        self,
        mock_settings: MagicMock,
        mock_latency: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
    ) -> None:
        """A query exceeding the threshold triggers a warning log and Prometheus metrics."""
        from app.db.query_logger import (
            _CONTEXT_KEY,
            _after_cursor_execute,
        )

        mock_settings.SLOW_QUERY_THRESHOLD_MS = 100
        mock_settings.SLOW_QUERY_LOG_PARAMS = False

        conn = self._make_mock_conn()
        # Simulate a query that started 0.5 seconds ago (500ms > 100ms threshold)
        conn.info[_CONTEXT_KEY] = time.perf_counter() - 0.5

        with patch("app.db.query_logger.logger") as mock_logger:
            _after_cursor_execute(conn, None, "SELECT * FROM deals", None, None, False)
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args
            # First positional arg is the message
            assert "slow query" in call_kwargs[0][0].lower()

        # Prometheus slow-query histogram observed
        mock_histogram.labels.return_value.observe.assert_called_once()
        mock_counter.labels.return_value.inc.assert_called_once()

    @patch("app.db.query_logger.SLOW_QUERY_COUNT")
    @patch("app.db.query_logger.SLOW_QUERY_HISTOGRAM")
    @patch("app.db.query_logger.DB_QUERY_LATENCY")
    @patch("app.core.config.settings")
    def test_slow_query_includes_sanitized_params_when_enabled(
        self,
        mock_settings: MagicMock,
        mock_latency: MagicMock,
        mock_histogram: MagicMock,
        mock_counter: MagicMock,
    ) -> None:
        """When SLOW_QUERY_LOG_PARAMS is True, params should be included but sanitized."""
        from app.db.query_logger import (
            _CONTEXT_KEY,
            _after_cursor_execute,
        )

        mock_settings.SLOW_QUERY_THRESHOLD_MS = 10
        mock_settings.SLOW_QUERY_LOG_PARAMS = True

        conn = self._make_mock_conn()
        conn.info[_CONTEXT_KEY] = time.perf_counter() - 0.5

        params = {"username": "alice", "password": "s3cret"}

        with patch("app.db.query_logger.logger") as mock_logger:
            _after_cursor_execute(
                conn,
                None,
                "SELECT * FROM users WHERE username=:username",
                params,
                None,
                False,
            )
            call_kwargs = mock_logger.warning.call_args[1]
            # Params should be sanitized
            assert call_kwargs["params"]["password"] == "***"
            assert call_kwargs["params"]["username"] == "alice"

    @patch("app.db.query_logger.DB_QUERY_LATENCY")
    @patch("app.core.config.settings")
    def test_missing_start_time_returns_early(
        self, mock_settings: MagicMock, mock_latency: MagicMock
    ) -> None:
        """If no start time in conn.info, _after_cursor_execute should return early."""
        from app.db.query_logger import _after_cursor_execute

        conn = self._make_mock_conn()
        # No start time set

        with patch("app.db.query_logger.logger") as mock_logger:
            _after_cursor_execute(conn, None, "SELECT 1", None, None, False)
            mock_logger.warning.assert_not_called()

        # Generic histogram should NOT be observed since we returned early
        mock_latency.labels.assert_not_called()

    @patch("app.db.query_logger.SLOW_QUERY_COUNT", None)
    @patch("app.db.query_logger.SLOW_QUERY_HISTOGRAM", None)
    @patch("app.db.query_logger.DB_QUERY_LATENCY")
    @patch("app.core.config.settings")
    def test_slow_query_works_without_prometheus(
        self,
        mock_settings: MagicMock,
        mock_latency: MagicMock,
    ) -> None:
        """Slow query logging degrades gracefully when Prometheus is unavailable."""
        from app.db.query_logger import (
            _CONTEXT_KEY,
            _after_cursor_execute,
        )

        mock_settings.SLOW_QUERY_THRESHOLD_MS = 10
        mock_settings.SLOW_QUERY_LOG_PARAMS = False

        conn = self._make_mock_conn()
        conn.info[_CONTEXT_KEY] = time.perf_counter() - 0.5

        with patch("app.db.query_logger.logger") as mock_logger:
            # Should not raise even though SLOW_QUERY_HISTOGRAM/COUNT are None
            _after_cursor_execute(conn, None, "SELECT 1", None, None, False)
            mock_logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# attach_query_logger
# ---------------------------------------------------------------------------


class TestAttachQueryLogger:
    """Tests for the attach_query_logger public API."""

    def test_attach_to_sync_engine(self) -> None:
        from sqlalchemy import create_engine, event

        from app.db.query_logger import (
            _after_cursor_execute,
            _before_cursor_execute,
            attach_query_logger,
        )

        engine = MagicMock()
        engine.__class__ = type("SyncEngine", (), {})  # Not an AsyncEngine

        with patch("sqlalchemy.event.listen") as mock_listen:
            attach_query_logger(engine)

        assert mock_listen.call_count == 2
        calls = mock_listen.call_args_list
        assert calls[0][0][0] is engine
        assert calls[0][0][1] == "before_cursor_execute"
        assert calls[1][0][0] is engine
        assert calls[1][0][1] == "after_cursor_execute"

    def test_attach_to_async_engine_uses_sync_engine(self) -> None:
        from sqlalchemy.ext.asyncio import AsyncEngine

        from app.db.query_logger import attach_query_logger

        mock_sync_engine = MagicMock()
        mock_async = MagicMock(spec=AsyncEngine)
        mock_async.sync_engine = mock_sync_engine

        with patch("sqlalchemy.event.listen") as mock_listen:
            attach_query_logger(mock_async)

        calls = mock_listen.call_args_list
        assert calls[0][0][0] is mock_sync_engine
        assert calls[1][0][0] is mock_sync_engine
