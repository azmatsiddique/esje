"""DuckDB driver implementation for esje using python-duckdb."""

from typing import Any, Dict, Optional, Union

import pandas as pd

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class DuckDBDriver(BaseDriver):
    """DuckDB driver utilizing python-duckdb native client."""

    def __init__(
        self,
        database: str = ":memory:",
        read_only: bool = False,
        custom_connection: Any = None,
    ) -> None:
        self.database = database
        self.read_only = read_only

        self.host = database
        self.port = 0
        self.user = "duckdb"

        self._conn = custom_connection

    @property
    def dialect(self) -> str:
        return "duckdb"

    def connect(self) -> None:
        if self._conn is None:
            try:
                import duckdb  # type: ignore
            except ImportError:
                raise ConnectionError(
                    "duckdb package is not installed.",
                    hint="Install DuckDB support via: pip install 'esje[duckdb]' or pip install duckdb",
                )

            try:
                self._conn = duckdb.connect(database=self.database, read_only=self.read_only)
            except Exception as exc:
                raise ConnectionError(
                    f"DuckDB connection failed for database '{self.database}': {exc}",
                    hint="Verify database file path, permissions, or read-only settings.",
                ) from (exc if config.verbose_errors else None)

        try:
            res = self._conn.execute("SELECT 1")
            if hasattr(res, "fetchall"):
                res.fetchall()
        except Exception as exc:
            raise ConnectionError(
                f"DuckDB ping check failed: {exc}",
                hint="Verify DuckDB database state and query capabilities.",
            ) from (exc if config.verbose_errors else None)

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        if self._conn is None:
            raise ConnectionError("Not connected to DuckDB.")

        clean_query = query.strip().rstrip(";")
        is_select = clean_query.lower().startswith(
            ("select", "show", "describe", "desc", "explain", "with", "summarize", "pivot", "from")
        )

        try:
            res = self._conn.execute(query)
            if is_select:
                if config.use_pyarrow and hasattr(res, "arrow"):
                    try:
                        return res.arrow().to_pandas(types_mapper=pd.ArrowDtype)
                    except Exception:
                        pass
                if hasattr(res, "df"):
                    return res.df()
                elif hasattr(res, "fetchdf"):
                    return res.fetchdf()
                elif hasattr(res, "fetchall"):
                    cols = [desc[0] for desc in res.description] if hasattr(res, "description") and res.description else []
                    rows = res.fetchall()
                    return pd.DataFrame(rows, columns=cols)
                else:
                    return pd.DataFrame()
            else:
                rowcount = getattr(res, "rowcount", -1)
                return {
                    "status": "Query executed successfully",
                    "rowcount": rowcount if rowcount >= 0 else 0,
                }
        except Exception as exc:
            raise QueryError(f"DuckDB Query Error: {exc}") from (
                exc if config.verbose_errors else None
            )

    def close(self) -> None:
        if self._conn is not None:
            try:
                if hasattr(self._conn, "close"):
                    self._conn.close()
            except Exception:
                pass
            self._conn = None
