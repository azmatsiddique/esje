"""Oracle Database driver implementation for esje using oracledb and SQLAlchemy."""

from typing import Any, Dict, Optional, Union
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError


class OracleDriver(BaseDriver):
    """Oracle Database driver utilizing SQLAlchemy with python-oracledb."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1521,
        user: str = "",
        password: str = "",
        service_name: Optional[str] = None,
        sid: Optional[str] = None,
        database: Optional[str] = None,
        thick_mode: bool = False,
        custom_engine: Any = None,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.service_name = service_name
        self.sid = sid
        self.database = database
        self.thick_mode = thick_mode

        self._engine = custom_engine

    @property
    def dialect(self) -> str:
        return "oracle"

    def _build_connection_url(self) -> str:
        encoded_user = quote_plus(self.user) if self.user else ""
        encoded_pass = quote_plus(self.password) if self.password else ""

        # Precedence for target identifier: explicit service_name -> explicit sid -> database
        target_service = self.service_name
        target_sid = self.sid
        if not target_service and not target_sid and self.database:
            target_service = self.database

        auth_part = f"{encoded_user}:{encoded_pass}@" if encoded_user or encoded_pass else ""
        url = f"oracle+oracledb://{auth_part}{self.host}:{self.port}"

        if target_service:
            url += f"/?service_name={quote_plus(target_service)}"
        elif target_sid:
            url += f"/?sid={quote_plus(target_sid)}"

        return url

    def connect(self) -> None:
        if self._engine is None:
            if self.thick_mode:
                try:
                    import oracledb
                    oracledb.init_oracle_client()
                except Exception as exc:
                    raise ConnectionError(
                        f"Failed to initialize Oracle thick mode client: {exc}",
                        hint="Ensure Oracle Client libraries (Instant Client) are installed and configured.",
                    ) from (exc if config.verbose_errors else None)

            url = self._build_connection_url()
            try:
                self._engine = create_engine(url, pool_pre_ping=True)
            except Exception as exc:
                raise ConnectionError(
                    f"Oracle connection engine creation failed: {exc}",
                    hint="Verify driver installation (`pip install oracledb`) and connection parameters.",
                ) from (exc if config.verbose_errors else None)

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
        except OperationalError as exc:
            msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
            hint = "Check hostname, port, username, password, and database service name / SID."
            msg_lower = msg.lower()
            if "ora-01017" in msg_lower or "invalid username/password" in msg_lower:
                hint = "Access denied: verify your Oracle username and password."
            elif "ora-12541" in msg_lower or "tns:no listener" in msg_lower or "connection refused" in msg_lower:
                hint = f"Failed to connect to Oracle server at {self.host}:{self.port}. Ensure TNS listener is running."
            elif "ora-12514" in msg_lower or "listener does not currently know of service" in msg_lower:
                target = self.service_name or self.sid or self.database
                hint = f"Oracle service name / SID '{target}' was not recognized by the listener."
            elif "ora-12154" in msg_lower or "could not resolve the connect identifier" in msg_lower:
                hint = "Could not resolve Oracle connect identifier. Check connection parameters."

            raise ConnectionError(f"Oracle connection failed: {msg}", hint=hint) from (
                exc if config.verbose_errors else None
            )
        except Exception as exc:
            if isinstance(exc, ConnectionError):
                raise
            raise ConnectionError(f"Oracle connection failed: {exc}") from (
                exc if config.verbose_errors else None
            )

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        if self._engine is None:
            raise ConnectionError("Not connected to database.")

        clean_query = query.strip().rstrip(";")
        is_select = clean_query.lower().startswith(
            ("select", "show", "describe", "desc", "explain", "with")
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
