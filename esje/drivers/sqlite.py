"""SQLite driver implementation for esje using Python's built-in sqlite3 and SQLAlchemy."""

import os
from typing import Any, Dict, Optional, Union

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class SQLiteDriver(BaseDriver):
    """SQLite database driver utilizing SQLAlchemy and sqlite3."""

    def __init__(
        self,
        database: str = ":memory:",
        read_only: bool = False,
        custom_engine: Any = None,
    ) -> None:
        self.database = database
        self.read_only = read_only

        self._engine = custom_engine

    @property
    def dialect(self) -> str:
        return "sqlite"

    def _build_connection_url(self) -> str:
        db = self.database.strip() if self.database else ":memory:"
        if db == ":memory:":
            url = "sqlite:///:memory:"
        else:
            abs_path = os.path.abspath(db)
            if self.read_only:
                url = f"sqlite:///file:{abs_path}?mode=ro&uri=true"
            else:
                url = f"sqlite:///{abs_path}"

        return url

    def connect(self) -> None:
        if self._engine is None:
            url = self._build_connection_url()
            try:
                self._engine = create_engine(url, pool_pre_ping=True)
            except Exception as exc:
                raise ConnectionError(
                    f"SQLite connection engine creation failed: {exc}",
                    hint="Check database path syntax and permissions.",
                ) from (exc if config.verbose_errors else None)

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except OperationalError as exc:
            msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            hint = "Check file path, read/write permissions, and disk space."
            msg_lower = msg.lower()
            if "unable to open database file" in msg_lower or "cannot open" in msg_lower:
                hint = f"Unable to open SQLite database at '{self.database}'. Verify path exists and permissions are granted."
            elif "permission denied" in msg_lower:
                hint = f"Permission denied accessing SQLite database file at '{self.database}'."
            elif "file is not a database" in msg_lower or "database disk image is malformed" in msg_lower:
                hint = f"The file at '{self.database}' is corrupted or not a valid SQLite database."

            raise ConnectionError(f"SQLite connection failed: {msg}", hint=hint) from (
                exc if config.verbose_errors else None
            )
        except Exception as exc:
            if isinstance(exc, ConnectionError):
                raise
            raise ConnectionError(f"SQLite connection failed: {exc}") from (
                exc if config.verbose_errors else None
            )

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        if self._engine is None:
            raise ConnectionError("Not connected to database.")

        clean_query = query.strip().rstrip(";")
        is_select = clean_query.lower().startswith(
            ("select", "show", "describe", "desc", "explain", "pragma", "with")
        )

        try:
            with self._engine.connect() as conn:
                if is_select:
                    if config.use_pyarrow:
                        try:
                            df = pd.read_sql(text(clean_query), con=conn, dtype_backend="pyarrow")
                        except Exception:
                            df = pd.read_sql(text(clean_query), con=conn)
                    else:
                        df = pd.read_sql(text(clean_query), con=conn)
                    return df

                else:
                    trans = conn.begin() if config.auto_commit else None
                    result = conn.execute(text(clean_query))
                    if trans:
                        trans.commit()
                    rowcount = result.rowcount if hasattr(result, "rowcount") else 0
                    return {"status": "Query executed successfully", "rowcount": rowcount}
        except SQLAlchemyError as exc:
            msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            raise QueryError(f"SQL Execution Error: {msg}") from (
                exc if config.verbose_errors else None
            )
        except Exception as exc:
            raise QueryError(f"Query Error: {exc}") from (
                exc if config.verbose_errors else None
            )

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
