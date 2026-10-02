"""Databricks driver implementation for esje using databricks-sql-connector and SQLAlchemy."""

from typing import Any, Dict, Optional, Union
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class DatabricksDriver(BaseDriver):
    """Databricks SQL driver utilizing SQLAlchemy and databricks-sql-connector."""

    def __init__(
        self,
        host: str = "",
        token: str = "",
        http_path: str = "",
        catalog: str = "",
        schema: str = "",
        port: int = 443,
        custom_engine: Any = None,
    ) -> None:
        self.host_val = host
        self.token = token
        self.http_path = http_path
        self.catalog = catalog
        self.schema = schema
        self.port_val = port or 443

        self._engine = custom_engine

    @property
    def dialect(self) -> str:
        return "databricks"

    @property
    def host(self) -> str:
        return self.host_val

    @property
    def port(self) -> int:
        return self.port_val

    @property
    def user(self) -> str:
        return "token"

    @property
    def database(self) -> str:
        return self.catalog or self.schema

    def _build_connection_url(self) -> str:
        encoded_token = quote_plus(self.token)
        host_str = self.host_val.strip()
        port_str = f":{self.port_val}" if self.port_val else ""

        url = f"databricks://token:{encoded_token}@{host_str}{port_str}"

        query_params = []
        if self.http_path:
            query_params.append(f"http_path={quote_plus(self.http_path)}")
        if self.catalog:
            query_params.append(f"catalog={quote_plus(self.catalog)}")
        if self.schema:
            query_params.append(f"schema={quote_plus(self.schema)}")

        if query_params:
            url += "?" + "&".join(query_params)

        return url

    def connect(self) -> None:
        if self._engine is None:
            url = self._build_connection_url()
            try:
                self._engine = create_engine(url, pool_pre_ping=True)
            except Exception as exc:
                raise ConnectionError(
                    f"Databricks connection engine creation failed: {exc}",
                    hint="Verify driver installation (`pip install databricks-sql-connector databricks-sqlalchemy`) and connection parameters.",
                ) from (exc if config.verbose_errors else None)

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except OperationalError as exc:
            msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            hint = "Check Databricks server hostname, HTTP path, token, catalog, and schema."
            msg_lower = msg.lower()
            if "invalid token" in msg_lower or "authentication failed" in msg_lower or "401" in msg_lower:
                hint = "Access denied: verify your Databricks Personal Access Token."
            elif "http path" in msg_lower or "404" in msg_lower:
                hint = f"Verify Databricks HTTP path '{self.http_path}' exists and is reachable."
            elif "catalog" in msg_lower or "schema" in msg_lower:
                hint = f"Verify Databricks catalog '{self.catalog}' and schema '{self.schema}' exist."

            raise ConnectionError(f"Databricks connection failed: {msg}", hint=hint) from (
                exc if config.verbose_errors else None
            )
        except Exception as exc:
            if isinstance(exc, ConnectionError):
                raise
            raise ConnectionError(f"Databricks connection failed: {exc}") from (
                exc if config.verbose_errors else None
            )

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        if self._engine is None:
            raise ConnectionError("Not connected to database.")

        clean_query = query.strip().rstrip(";")
        is_select = clean_query.lower().startswith(
            ("select", "show", "describe", "desc", "explain", "with", "call")
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
