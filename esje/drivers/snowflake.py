"""Snowflake driver implementation for esje using snowflake-sqlalchemy and SQLAlchemy."""

from typing import Any, Dict, Optional, Union
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class SnowflakeDriver(BaseDriver):
    """Snowflake database driver utilizing SQLAlchemy and snowflake-sqlalchemy."""

    def __init__(
        self,
        account: str = "",
        user: str = "",
        password: str = "",
        database: str = "",
        schema: str = "",
        warehouse: str = "",
        role: str = "",
        authenticator: str = "",
        custom_engine: Any = None,
    ) -> None:
        self.account = account
        self.user = user
        self.password = password
        self.database = database
        self.schema = schema
        self.warehouse = warehouse
        self.role = role
        self.authenticator = authenticator

        self._engine = custom_engine

    @property
    def dialect(self) -> str:
        return "snowflake"

    @property
    def host(self) -> str:
        return self.account

    def _build_connection_url(self) -> str:
        encoded_user = quote_plus(self.user)
        encoded_pass = quote_plus(self.password)
        account_str = self.account.strip()

        path = ""
        if self.database:
            path += f"/{quote_plus(self.database)}"
            if self.schema:
                path += f"/{quote_plus(self.schema)}"

        url = f"snowflake://{encoded_user}:{encoded_pass}@{account_str}{path}"

        query_params = []
        if self.warehouse:
            query_params.append(f"warehouse={quote_plus(self.warehouse)}")
        if self.role:
            query_params.append(f"role={quote_plus(self.role)}")
        if self.authenticator:
            query_params.append(f"authenticator={quote_plus(self.authenticator)}")

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
                    f"Snowflake connection engine creation failed: {exc}",
                    hint="Verify driver installation (`pip install snowflake-sqlalchemy`) and connection parameters.",
                ) from (exc if config.verbose_errors else None)

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except OperationalError as exc:
            msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            hint = "Check Snowflake account, user, password, database, warehouse, and role."
            msg_lower = msg.lower()
            if "incorrect username or password" in msg_lower or "authentication failed" in msg_lower:
                hint = "Access denied: verify your Snowflake username and password."
            elif "object does not exist" in msg_lower or "database" in msg_lower:
                hint = f"Verify Snowflake database '{self.database}' and schema '{self.schema}' exist."
            elif "warehouse" in msg_lower:
                hint = f"Verify Snowflake warehouse '{self.warehouse}' exists and is active."

            raise ConnectionError(f"Snowflake connection failed: {msg}", hint=hint) from (
                exc if config.verbose_errors else None
            )
        except Exception as exc:
            if isinstance(exc, ConnectionError):
                raise
            raise ConnectionError(f"Snowflake connection failed: {exc}") from (
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
