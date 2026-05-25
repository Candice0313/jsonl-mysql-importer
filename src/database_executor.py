"""DatabaseExecutor module for connecting to MySQL and executing SQL scripts."""

import logging
import time
from pathlib import Path
from typing import Optional

import mysql.connector
from mysql.connector import Error as MySQLError

logger = logging.getLogger(__name__)


class DatabaseExecutor:
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds

    def __init__(self, host: str, port: int, database: str, username: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None
        self.error_log_path = Path("import_errors.log")

    def _log_error(self, message: str) -> None:
        """Append an error message to the error log file."""
        logger.error(message)
        with self.error_log_path.open("a", encoding="utf-8") as fh:
            fh.write(message + "\n")

    def connect(self) -> bool:
        """Connect to MySQL with up to MAX_RETRIES attempts, RETRY_DELAY seconds between attempts.

        Returns True on success, False on failure.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                conn_kwargs = {
                    "host": self.host,
                    "port": self.port,
                    "user": self.username,
                    "password": self.password,
                }
                if self.database:
                    conn_kwargs["database"] = self.database

                connection = mysql.connector.connect(**conn_kwargs)
                self.connection = connection
                logger.info(
                    "Connected to MySQL at %s:%s (database=%s)",
                    self.host,
                    self.port,
                    self.database or "<none>",
                )
                return True

            except MySQLError as exc:
                last_error = exc
                errno = exc.errno if hasattr(exc, "errno") else None

                # Classify and surface the error without leaking the password
                if errno in (2003, 2002, 2005, 2013):
                    # CR_CONN_HOST_ERROR / CR_SOCKET_CREATE_ERROR / CR_UNKNOWN_HOST /
                    # CR_SERVER_LOST
                    msg = (
                        f"Cannot connect to MySQL server at {self.host}:{self.port}"
                    )
                elif errno == 1045:
                    # ER_ACCESS_DENIED_ERROR
                    msg = f"Authentication failed for user '{self.username}'"
                elif errno == 1049:
                    # ER_BAD_DB_ERROR — database doesn't exist
                    answer = input(
                        f"Database '{self.database}' does not exist. Create it? [y/n]: "
                    ).strip().lower()
                    if answer == "y":
                        # Reconnect without specifying a database, then create it
                        try:
                            bare_conn = mysql.connector.connect(
                                host=self.host,
                                port=self.port,
                                user=self.username,
                                password=self.password,
                            )
                            cursor = bare_conn.cursor()
                            cursor.execute(
                                f"CREATE DATABASE `{self.database}`"
                            )
                            cursor.close()
                            bare_conn.close()
                            # Retry the full connection (will pick up the new DB)
                            continue
                        except MySQLError as create_exc:
                            msg = (
                                f"Failed to create database '{self.database}': "
                                f"{create_exc}"
                            )
                            self._log_error(msg)
                            return False
                    else:
                        self._log_error(f"User declined to create database '{self.database}'")
                        return False
                else:
                    msg = f"MySQL connection error (attempt {attempt}/{self.MAX_RETRIES}): {exc}"

                self._log_error(msg)

                if attempt < self.MAX_RETRIES:
                    logger.info(
                        "Retrying in %s seconds (attempt %s/%s)…",
                        self.RETRY_DELAY,
                        attempt,
                        self.MAX_RETRIES,
                    )
                    time.sleep(self.RETRY_DELAY)

        if last_error is not None:
            logger.error(
                "Failed to connect after %s attempts. Last error: %s",
                self.MAX_RETRIES,
                last_error,
            )
        return False

    def execute_schema(self, schema_sql: str, table_name: str) -> bool:
        """Execute CREATE TABLE statement.

        Prompts the user if the table already exists:
          [s] Skip creation
          [d] Drop and recreate
          [a] Abort

        Returns False if aborted, True otherwise.
        """
        if self.connection is None:
            self._log_error("execute_schema called but no active connection.")
            return False

        cursor = self.connection.cursor()
        try:
            cursor.execute(schema_sql)
            self.connection.commit()
            logger.info("Table '%s' created successfully.", table_name)
            return True
        except MySQLError as exc:
            # errno 1050: ER_TABLE_EXISTS_ERROR
            if exc.errno == 1050:
                print(
                    f"Table '{table_name}' already exists. Choose:\n"
                    f"  [s] Skip creation\n"
                    f"  [d] Drop and recreate\n"
                    f"  [a] Abort"
                )
                choice = input("> ").strip().lower()
                if choice == "s":
                    logger.info("Skipping creation of existing table '%s'.", table_name)
                    return True
                elif choice == "d":
                    try:
                        cursor.execute(f"DROP TABLE `{table_name}`")
                        cursor.execute(schema_sql)
                        self.connection.commit()
                        logger.info(
                            "Table '%s' dropped and recreated.", table_name
                        )
                        return True
                    except MySQLError as drop_exc:
                        msg = f"Error recreating table '{table_name}': {drop_exc}"
                        self._log_error(msg)
                        return False
                else:
                    logger.info("Aborting at user request.")
                    return False
            else:
                msg = f"Error executing schema for table '{table_name}': {exc}"
                self._log_error(msg)
                return False
        finally:
            cursor.close()

    def execute_script(self, script_path: Path) -> bool:
        """Execute a SQL script file.

        - Reads file with UTF-8 encoding.
        - Splits on ';\\n' to obtain individual statements.
        - Executes each non-empty statement.
        - On MySQLError: logs to import_errors.log and continues.
        - Commits after all statements complete.
        - Returns True if completed (even with errors), False if connection lost.
        """
        if self.connection is None:
            self._log_error("execute_script called but no active connection.")
            return False

        sql_text = script_path.read_text(encoding="utf-8")
        statements = sql_text.split(";\n")

        cursor = self.connection.cursor()
        try:
            for raw_stmt in statements:
                stmt = raw_stmt.strip()
                if not stmt:
                    continue
                try:
                    cursor.execute(stmt)
                except MySQLError as exc:
                    msg = f"SQL error while executing statement: {exc}\nStatement: {stmt[:200]}"
                    self._log_error(msg)
                    # Continue with the remaining statements

            try:
                self.connection.commit()
            except MySQLError as exc:
                msg = f"Error committing transaction: {exc}"
                self._log_error(msg)
                return False

            return True

        except Exception as exc:
            # Unexpected error — treat as connection loss
            msg = f"Unexpected error executing script '{script_path}': {exc}"
            self._log_error(msg)
            return False
        finally:
            cursor.close()

    def close(self) -> None:
        """Close the database connection."""
        if self.connection is not None:
            try:
                self.connection.close()
                logger.info("Database connection closed.")
            except MySQLError as exc:
                logger.warning("Error closing connection: %s", exc)
            finally:
                self.connection = None
