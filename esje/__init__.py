"""esje: SQL Magic for Jupyter Notebooks."""

from typing import Any, Dict, List, Optional

import pandas as pd

from esje.config import config
from esje.connection import Connection, manager
from esje.drivers.bigquery import BigQueryDriver
from esje.drivers.cockroachdb import CockroachDBDriver
from esje.drivers.duckdb import DuckDBDriver
from esje.drivers.mysql import MySQLDriver
from esje.drivers.oracle import OracleDriver
from esje.drivers.postgres import PostgresDriver
from esje.drivers.sqlite import SQLiteDriver
from esje.errors import ConnectionError, EsjeError, QueryError
from esje.extension import load_ipython_extension, unload_ipython_extension
from esje.prompts import (
    resolve_bigquery_credentials,
    resolve_cockroachdb_credentials,
    resolve_duckdb_credentials,
    resolve_mysql_credentials,
    resolve_oracle_credentials,
    resolve_postgres_credentials,
    resolve_sqlite_credentials,
)

from esje.live import live_manager

__version__ = "0.7.0"



def pause_live(widget_id: Optional[str] = None) -> None:
    """Pause live auto-refresh dashboard widget(s)."""
    live_manager.pause(widget_id)


def resume_live(widget_id: Optional[str] = None) -> None:
    """Resume live auto-refresh dashboard widget(s)."""
    live_manager.resume(widget_id)


def stop_live(widget_id: Optional[str] = None) -> None:
    """Stop live auto-refresh dashboard widget(s)."""
    live_manager.stop(widget_id)


def stop_all_live() -> None:
    """Stop all active live dashboard widgets."""
    live_manager.stop()


def connect_mysql(
    name: str = "default",
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    interactive_prompt: Optional[bool] = None,
    custom_engine: Any = None,
) -> Connection:
    """Connect to a MySQL database and store in connection registry."""
    creds = resolve_mysql_credentials(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        interactive_prompt=interactive_prompt,
    )

    driver = MySQLDriver(
        host=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
        custom_engine=custom_engine,
    )
    driver.connect()

    conn = Connection(name=name, driver=driver)
    manager.add(conn)
    print(f"Connected to MySQL on {creds['host']}:{creds['port']} as connection '{name}'.")
    return conn


def connect_postgres(
    name: str = "postgres",
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    sslmode: Optional[str] = None,
    interactive_prompt: Optional[bool] = None,
    custom_engine: Any = None,
) -> Connection:
    """Connect to a PostgreSQL database and store in connection registry."""
    creds = resolve_postgres_credentials(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        sslmode=sslmode,
        interactive_prompt=interactive_prompt,
    )

    driver = PostgresDriver(
        host=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
        sslmode=creds["sslmode"],
        custom_engine=custom_engine,
    )
    driver.connect()

    conn = Connection(name=name, driver=driver)
    manager.add(conn)
    print(f"Connected to PostgreSQL on {creds['host']}:{creds['port']} as connection '{name}'.")
    return conn


connect_postgresql = connect_postgres


def connect_cockroachdb(
    name: str = "cockroachdb",
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    sslmode: Optional[str] = None,
    interactive_prompt: Optional[bool] = None,
    custom_engine: Any = None,
) -> Connection:
    """Connect to a CockroachDB database and store in connection registry."""
    creds = resolve_cockroachdb_credentials(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        sslmode=sslmode,
        interactive_prompt=interactive_prompt,
    )

    driver = CockroachDBDriver(
        host=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        database=creds["database"],
        sslmode=creds["sslmode"],
        custom_engine=custom_engine,
    )
    driver.connect()

    conn = Connection(name=name, driver=driver)
    manager.add(conn)
    print(f"Connected to CockroachDB on {creds['host']}:{creds['port']} as connection '{name}'.")
    return conn


connect_cockroach = connect_cockroachdb
connect_crdb = connect_cockroachdb


def connect_duckdb(
    name: str = "duckdb",
    database: Optional[str] = None,
    read_only: Optional[bool] = None,
    interactive_prompt: Optional[bool] = None,
    custom_connection: Any = None,
) -> Connection:
    """Connect to a DuckDB database (in-memory or file) and store in connection registry."""
    creds = resolve_duckdb_credentials(
        database=database,
        read_only=read_only,
        interactive_prompt=interactive_prompt,
    )

    driver = DuckDBDriver(
        database=creds["database"],
        read_only=creds["read_only"],
        custom_connection=custom_connection,
    )
    driver.connect()

    conn = Connection(name=name, driver=driver)
    manager.add(conn)
    print(f"Connected to DuckDB ('{creds['database']}') as connection '{name}'.")
    return conn


def connect_bigquery(
    name: str = "bigquery",
    project: Optional[str] = None,
    dataset: Optional[str] = None,
    credentials_path: Optional[str] = None,
    location: Optional[str] = None,
    auth_method: Optional[str] = None,
    interactive_prompt: Optional[bool] = None,
    custom_client: Any = None,
    custom_engine: Any = None,
) -> Connection:
    """Connect to Google BigQuery and store in connection registry.

    Auth methods:
    - ``auth_method='browser'`` — opens a Google login in your browser (default when interactive).
    - ``auth_method='adc'`` — uses Application Default Credentials.
    - ``auth_method='service_account'`` — uses a service account JSON key file.
    """
    creds = resolve_bigquery_credentials(
        project=project,
        dataset=dataset,
        credentials_path=credentials_path,
        location=location,
        auth_method=auth_method,
        interactive_prompt=interactive_prompt,
    )

    driver = BigQueryDriver(
        project=creds["project"],
        dataset=creds["dataset"],
        credentials_path=creds["credentials_path"],
        location=creds["location"],
        auth_method=creds["auth_method"],
        custom_client=custom_client,
        custom_engine=custom_engine,
    )
    driver.connect()

    conn = Connection(name=name, driver=driver)
    manager.add(conn)
    proj_info = driver.project or creds['project'] or 'auto-detected'
    auth_info = creds['auth_method']
    print(f"✅ Connected to BigQuery project '{proj_info}' via {auth_info} as connection '{name}'.")
    return conn


def connect_oracle(
    name: str = "oracle",
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    service_name: Optional[str] = None,
    sid: Optional[str] = None,
    database: Optional[str] = None,
    thick_mode: Optional[bool] = None,
    interactive_prompt: Optional[bool] = None,
    custom_engine: Any = None,
) -> Connection:
    """Connect to an Oracle Database and store in connection registry."""
    creds = resolve_oracle_credentials(
        host=host,
        port=port,
        user=user,
        password=password,
        service_name=service_name,
        sid=sid,
        database=database,
        thick_mode=thick_mode,
        interactive_prompt=interactive_prompt,
    )

    driver = OracleDriver(
        host=creds["host"],
        port=creds["port"],
        user=creds["user"],
        password=creds["password"],
        service_name=creds["service_name"],
        sid=creds["sid"],
        database=creds["database"],
        thick_mode=creds["thick_mode"],
        custom_engine=custom_engine,
    )
    driver.connect()

    conn = Connection(name=name, driver=driver)
    manager.add(conn)
    target = creds["service_name"] or creds["sid"] or creds["database"] or ""
    target_info = f" ({target})" if target else ""
    print(f"Connected to Oracle Database{target_info} on {creds['host']}:{creds['port']} as connection '{name}'.")
    return conn


connect_ora = connect_oracle


def connect_sqlite(
    name: str = "sqlite",
    database: Optional[str] = None,
    read_only: Optional[bool] = None,
    interactive_prompt: Optional[bool] = None,
    custom_engine: Any = None,
) -> Connection:
    """Connect to a SQLite database (in-memory or file) and store in connection registry."""
    creds = resolve_sqlite_credentials(
        database=database,
        read_only=read_only,
        interactive_prompt=interactive_prompt,
    )

    driver = SQLiteDriver(
        database=creds["database"],
        read_only=creds["read_only"],
        custom_engine=custom_engine,
    )
    driver.connect()

    conn = Connection(name=name, driver=driver)
    manager.add(conn)
    print(f"Connected to SQLite ('{creds['database']}') as connection '{name}'.")
    return conn


connect_sqlite3 = connect_sqlite


def connect(dialect: str = "mysql", **kwargs: Any) -> Connection:
    """Generic connection helper dispatching to dialect-specific connector."""
    d = dialect.lower()
    if d in ("mysql", "mariadb"):
        return connect_mysql(**kwargs)
    elif d in ("postgres", "postgresql", "pg", "psql"):
        return connect_postgres(**kwargs)
    elif d in ("cockroachdb", "cockroach", "crdb", "cockroach-db"):
        return connect_cockroachdb(**kwargs)
    elif d in ("duckdb", "duck"):
        return connect_duckdb(**kwargs)
    elif d in ("bigquery", "bq"):
        return connect_bigquery(**kwargs)
    elif d in ("oracle", "ora", "oracledb"):
        return connect_oracle(**kwargs)
    elif d in ("sqlite", "sqlite3", "sqldb"):
        return connect_sqlite(**kwargs)
    else:
        raise ConnectionError(
            f"Unsupported dialect '{dialect}'. Supported dialects: 'mysql', 'postgres', 'cockroachdb', 'duckdb', 'bigquery', 'oracle', 'sqlite'.",
            hint="Use connect_sqlite(), connect_oracle(), connect_cockroachdb(), connect_duckdb(), connect_postgres(), connect_mysql(), or connect_bigquery().",
        )


def use(name: str) -> str:
    """Set the active connection name for %sql commands."""
    return manager.use(name)


def connections() -> pd.DataFrame:
    """Return DataFrame listing all open connections."""
    conns = manager.list_connections()
    if not conns:
        return pd.DataFrame(columns=["name", "active", "dialect", "host", "port", "user", "database"])
    return pd.DataFrame(conns)


def close(name: str) -> str:
    """Close connection by name."""
    return manager.close(name)


def close_all() -> None:
    """Close all open connections."""
    live_manager.stop()
    manager.close_all()


__all__ = [
    "connect_mysql",
    "connect_postgres",
    "connect_postgresql",
    "connect_cockroachdb",
    "connect_cockroach",
    "connect_crdb",
    "connect_duckdb",
    "connect_bigquery",
    "connect_oracle",
    "connect_ora",
    "connect_sqlite",
    "connect_sqlite3",
    "connect",
    "use",
    "connections",
    "close",
    "close_all",
    "pause_live",
    "resume_live",
    "stop_live",
    "stop_all_live",
    "config",
    "load_ipython_extension",
    "unload_ipython_extension",
    "EsjeError",
    "ConnectionError",
    "QueryError",
]





