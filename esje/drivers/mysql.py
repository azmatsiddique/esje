"""MySQL driver implementation for esje using pymysql and SQLAlchemy."""

from typing import Any, Dict, Union
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class MySQLDriver(BaseDriver):
    """MySQL driver utilizing pymysql and SQLAlchemy."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "",
        custom_engine=None,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self._engine = custom_engine

    @property
    def dialect(self) -> str:
        return "mysql"

    def _build_connection_url(self) -> str:
        encoded_user = quote_plus(self.user)
        encoded_pass = quote_plus(self.password)
        encoded_db = quote_plus(self.database) if self.database else ""

        url = f"mysql+pymysql://{encoded_user}:{encoded_pass}@{self.host}:{self.port}"
        if encoded_db:
            url += f"/{encoded_db}"
        return url

    def connect(self) -> None:
        if self._engine is None:
            url = self._build_connection_url()
            self._engine = create_engine(url, pool_pre_ping=True)

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except OperationalError as exc:
            msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            hint = "Check hostname, port, username, password, and database permissions."
            if "Access denied" in msg:
                hint = "Access denied: verify your username and password."
            elif "Can't connect to MySQL server" in msg or "Connection refused" in msg:
                hint = f"Failed to connect to MySQL server at {self.host}:{self.port}. Ensure the server is running."
            elif "Unknown database" in msg:
                hint = f"Database '{self.database}' does not exist on target host."
            raise ConnectionError(f"MySQL connection failed: {msg}", hint=hint) from (
                exc if config.verbose_errors else None
            )
        except Exception as exc:
            raise ConnectionError(f"MySQL connection failed: {exc}") from (
                exc if config.verbose_errors else None
            )

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        if self._engine is None:
            raise ConnectionError("Not connected to database.")

        clean_query = query.strip().rstrip(";")
        is_select = (
            clean_query.lower().startswith(
                ("select", "show", "describe", "desc", "explain", "with")
            )
        )

        try:
            with self._engine.connect() as conn:
                if is_select:
                    if config.use_pyarrow:
                        try:
                            df = pd.read_sql(text(query), con=conn, dtype_backend="pyarrow")
                        except Exception:
                            df = pd.read_sql(text(query), con=conn)
                    else:
                        df = pd.read_sql(text(query), con=conn)
                    return df

                else:
                    trans = conn.begin() if config.auto_commit else None
                    result = conn.execute(text(query))
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
