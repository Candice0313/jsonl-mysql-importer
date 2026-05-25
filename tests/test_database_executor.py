"""Tests for DatabaseExecutor (tasks 5.1 / 5.2 / 5.3).

Real DB connections are not required; mysql.connector is mocked throughout.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call

import pytest

from src.database_executor import DatabaseExecutor
from mysql.connector import Error as MySQLError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_executor(**kwargs):
    defaults = dict(
        host="localhost",
        port=3306,
        database="testdb",
        username="root",
        password="secret",
    )
    defaults.update(kwargs)
    return DatabaseExecutor(**defaults)


def make_mysql_error(errno: int, msg: str = "error") -> MySQLError:
    """Create a MySQLError with a specific errno."""
    err = MySQLError(msg)
    err.errno = errno
    return err


# ---------------------------------------------------------------------------
# Task 5.1 — __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_init_stores_params(self):
        ex = DatabaseExecutor(
            host="db.example.com",
            port=3307,
            database="mydb",
            username="admin",
            password="p@ssw0rd",
        )
        assert ex.host == "db.example.com"
        assert ex.port == 3307
        assert ex.database == "mydb"
        assert ex.username == "admin"
        assert ex.password == "p@ssw0rd"
        assert ex.connection is None
        assert ex.error_log_path == Path("import_errors.log")


# ---------------------------------------------------------------------------
# Task 5.1 — connect() with retry logic
# ---------------------------------------------------------------------------

class TestConnect:
    @patch("src.database_executor.time.sleep")
    @patch("src.database_executor.mysql.connector.connect")
    def test_connect_success(self, mock_connect, mock_sleep):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        ex = make_executor()
        result = ex.connect()

        assert result is True
        assert ex.connection is mock_conn
        mock_sleep.assert_not_called()

    @patch("src.database_executor.time.sleep")
    @patch("src.database_executor.mysql.connector.connect")
    def test_connect_failure_returns_false(self, mock_connect, mock_sleep, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.database_executor.DatabaseExecutor.error_log_path",
            tmp_path / "import_errors.log",
            raising=False,
        )
        err = make_mysql_error(2003, "Connection refused")
        mock_connect.side_effect = err

        ex = make_executor()
        ex.error_log_path = tmp_path / "import_errors.log"
        result = ex.connect()

        assert result is False
        assert ex.connection is None

    @patch("src.database_executor.time.sleep")
    @patch("src.database_executor.mysql.connector.connect")
    def test_connect_retries_3_times(self, mock_connect, mock_sleep, tmp_path):
        err = make_mysql_error(2003, "Connection refused")
        mock_connect.side_effect = err

        ex = make_executor()
        ex.error_log_path = tmp_path / "import_errors.log"
        ex.connect()

        assert mock_connect.call_count == 3

    @patch("src.database_executor.time.sleep")
    @patch("src.database_executor.mysql.connector.connect")
    def test_connect_logs_error_on_failure(self, mock_connect, mock_sleep, tmp_path):
        err = make_mysql_error(2003, "Connection refused")
        mock_connect.side_effect = err

        ex = make_executor()
        ex.error_log_path = tmp_path / "import_errors.log"
        ex.connect()

        assert ex.error_log_path.exists(), "Error log should be written on connection failure"
        log_content = ex.error_log_path.read_text()
        assert len(log_content) > 0, "Error log should not be empty"

    @patch("src.database_executor.time.sleep")
    @patch("src.database_executor.mysql.connector.connect")
    def test_connect_sleeps_between_retries(self, mock_connect, mock_sleep, tmp_path):
        """Sleep is called between retry attempts (MAX_RETRIES-1 times)."""
        err = make_mysql_error(2003, "Connection refused")
        mock_connect.side_effect = err

        ex = make_executor()
        ex.error_log_path = tmp_path / "import_errors.log"
        ex.connect()

        # 3 attempts → sleep called between attempt 1→2 and 2→3 = 2 times
        assert mock_sleep.call_count == DatabaseExecutor.MAX_RETRIES - 1
        mock_sleep.assert_called_with(DatabaseExecutor.RETRY_DELAY)

    @patch("src.database_executor.time.sleep")
    @patch("src.database_executor.mysql.connector.connect")
    def test_connect_auth_failure_no_password_in_error(self, mock_connect, mock_sleep, tmp_path):
        """Authentication error message must NOT contain the password."""
        err = make_mysql_error(1045, "Access denied for user 'root'@'localhost'")
        mock_connect.side_effect = err

        ex = make_executor(password="supersecret")
        ex.error_log_path = tmp_path / "import_errors.log"
        ex.connect()

        log_content = ex.error_log_path.read_text()
        assert "supersecret" not in log_content

    @patch("src.database_executor.time.sleep")
    @patch("src.database_executor.mysql.connector.connect")
    def test_connect_host_unreachable_message(self, mock_connect, mock_sleep, tmp_path):
        """Host-unreachable error should include host and port in log."""
        err = make_mysql_error(2003, "Can't connect to host")
        mock_connect.side_effect = err

        ex = make_executor(host="db.example.com", port=3307)
        ex.error_log_path = tmp_path / "import_errors.log"
        ex.connect()

        log_content = ex.error_log_path.read_text()
        assert "db.example.com" in log_content
        assert "3307" in log_content


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_closes_connection(self):
        ex = make_executor()
        mock_conn = MagicMock()
        ex.connection = mock_conn

        ex.close()

        mock_conn.close.assert_called_once()

    def test_close_sets_connection_to_none(self):
        ex = make_executor()
        mock_conn = MagicMock()
        ex.connection = mock_conn

        ex.close()

        assert ex.connection is None

    def test_close_noop_when_not_connected(self):
        """close() must not raise when connection is already None."""
        ex = make_executor()
        assert ex.connection is None
        ex.close()  # should not raise


# ---------------------------------------------------------------------------
# Task 5.3 — execute_script()
# ---------------------------------------------------------------------------

class TestExecuteScript:
    def _make_executor_with_mock_conn(self):
        ex = make_executor()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        ex.connection = mock_conn
        return ex, mock_conn, mock_cursor

    def test_execute_script_commits_after_success(self, tmp_path):
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()

        script = tmp_path / "test.sql"
        script.write_text("INSERT INTO t VALUES (1);\nINSERT INTO t VALUES (2);\n")

        result = ex.execute_script(script)

        assert result is True
        mock_conn.commit.assert_called_once()

    def test_execute_script_continues_on_sql_error(self, tmp_path):
        """If the first statement raises MySQLError, the second must still execute."""
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()

        sql_err = make_mysql_error(1064, "Syntax error")
        # First call raises, second call succeeds
        mock_cursor.execute.side_effect = [sql_err, None]

        script = tmp_path / "test.sql"
        script.write_text("BAD SQL;\nINSERT INTO t VALUES (2);\n")
        ex.error_log_path = tmp_path / "import_errors.log"

        result = ex.execute_script(script)

        assert result is True
        # Both statements should have been attempted
        assert mock_cursor.execute.call_count == 2

    def test_execute_script_returns_false_without_connection(self, tmp_path):
        ex = make_executor()
        ex.error_log_path = tmp_path / "import_errors.log"

        script = tmp_path / "test.sql"
        script.write_text("SELECT 1;\n")

        result = ex.execute_script(script)

        assert result is False

    def test_execute_script_skips_empty_statements(self, tmp_path):
        """Empty fragments after split (e.g. trailing semicolons) are not executed."""
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()

        script = tmp_path / "test.sql"
        # Two real statements + trailing newline produces an empty fragment
        script.write_text("INSERT INTO t VALUES (1);\nINSERT INTO t VALUES (2);\n")

        ex.execute_script(script)

        # Only 2 real statements, not 3
        assert mock_cursor.execute.call_count == 2

    def test_execute_script_logs_sql_errors(self, tmp_path):
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()
        ex.error_log_path = tmp_path / "import_errors.log"

        sql_err = make_mysql_error(1064, "Syntax error")
        mock_cursor.execute.side_effect = [sql_err, None]

        script = tmp_path / "test.sql"
        script.write_text("BAD SQL;\nINSERT INTO t VALUES (2);\n")

        ex.execute_script(script)

        assert ex.error_log_path.exists()
        log_content = ex.error_log_path.read_text()
        assert "SQL error" in log_content or "Syntax error" in log_content


# ---------------------------------------------------------------------------
# Task 5.3 — execute_schema()
# ---------------------------------------------------------------------------

class TestExecuteSchema:
    def _make_executor_with_mock_conn(self):
        ex = make_executor()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        ex.connection = mock_conn
        return ex, mock_conn, mock_cursor

    def test_execute_schema_success(self):
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()
        mock_cursor.execute.return_value = None  # no error

        result = ex.execute_schema("CREATE TABLE t (id INT)", "t")

        assert result is True
        mock_conn.commit.assert_called_once()

    def test_execute_schema_skip_existing_table(self):
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()
        err = make_mysql_error(1050, "Table 't' already exists")
        mock_cursor.execute.side_effect = err

        with patch("builtins.input", return_value="s"):
            result = ex.execute_schema("CREATE TABLE t (id INT)", "t")

        assert result is True

    def test_execute_schema_abort_existing_table(self):
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()
        err = make_mysql_error(1050, "Table 't' already exists")
        mock_cursor.execute.side_effect = err

        with patch("builtins.input", return_value="a"):
            result = ex.execute_schema("CREATE TABLE t (id INT)", "t")

        assert result is False

    def test_execute_schema_drop_recreate(self):
        ex, mock_conn, mock_cursor = self._make_executor_with_mock_conn()
        err = make_mysql_error(1050, "Table 't' already exists")
        # First call raises (table exists), subsequent calls succeed
        mock_cursor.execute.side_effect = [err, None, None]

        with patch("builtins.input", return_value="d"):
            result = ex.execute_schema("CREATE TABLE t (id INT)", "t")

        assert result is True
        mock_conn.commit.assert_called_once()

    def test_execute_schema_returns_false_without_connection(self, tmp_path):
        ex = make_executor()
        ex.error_log_path = tmp_path / "import_errors.log"

        result = ex.execute_schema("CREATE TABLE t (id INT)", "t")

        assert result is False
