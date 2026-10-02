"""Amazon Redshift driver implementation for esje using sqlalchemy-redshift and psycopg2."""

from typing import Any, Dict, Optional, Union
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class RedshiftDriver(BaseDriver):
    """Amazon Redshift database driver utilizing SQLAlchemy and redshift+psycopg2."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        user: str = "awsuser",
        password: str = "",
        database: str = "dev",
        sslmode: Optional[str] = None,
        custom_engine: Any = None,
    ) -> None:
        self.host_val = host
        self.port_val = port or 5439
        self.user_val = user
        self.password = password
        self.database_val = database
        self.sslmode = sslmode

        self._engine = custom_engine

    @property
    def dialect(self) -> str:
        return "redshift"

    @property
    def host(self) -> str:
        return self.host_val

    @property
    def port(self) -> int:
        return self.port_val

    @property
    def user(self) -> str:
        return self.user_val

    @property
    def database(self) -> str:
        return self.database_val

    def _build_connection_url(self, driver_prefix: str = "redshift+psycopg2") -> str:
        encoded_user = quote_plus(self.user_val)
        encoded_pass = quote_plus(self.password)
        db_str = f"/{quote_plus(self.database_val)}" if self.database_val else ""

        url = f"{driver_prefix}://{encoded_user}:{encoded_pass}@{self.host_val}:{self.port_val}{db_str}"
        if self.sslmode:
            url += f"?sslmode={quote_plus(self.sslmode)}"

        return url

    def connect(self) -> None:
        if self._engine is None:
            try:
                url = self._build_connection_url(driver_prefix="redshift+psycopg2")
                self._engine = create_engine(url, pool_pre_ping=True)
            except Exception:
                # Fall back to postgresql dialect if redshift+psycopg2 is not registered
                url = self._build_connection_url(driver_prefix="postgresql")
                try:
                    self._engine = create_engine(url, pool_pre_ping=True)
                except Exception as exc:
                    raise ConnectionError(
                        f"Redshift connection engine creation failed: {exc}",
                        hint="Verify driver installation (`pip install sqlalchemy-redshift psycopg2-binary`) and connection parameters.",
                    ) from (exc if config.verbose_errors else None)

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except OperationalError as exc:
            msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            hint = "Check Redshift host, port (default 5439), database, username, and password."
            msg_lower = msg.lower()
            if "password authentication failed" in msg_lower or "access denied" in msg_lower:
                hint = "Access denied: verify your Redshift username and password."
            elif "database" in msg_lower and "does not exist" in msg_lower:
                hint = f"Verify Redshift database '{self.database_val}' exists."
            elif "could not connect to server" in msg_lower or "connection refused" in msg_lower:
                hint = f"Could not reach Redshift host '{self.host_val}:{self.port_val}'. Check security groups/firewall rules."

            raise ConnectionError(f"Redshift connection failed: {msg}", hint=hint) from (
                exc if config.verbose_errors else None
            )
        except Exception as exc:
            if isinstance(exc, ConnectionError):
                raise
            raise ConnectionError(f"Redshift connection failed: {exc}") from (
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
