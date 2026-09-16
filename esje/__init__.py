"""esje: SQL Magic for Jupyter Notebooks."""

from typing import Any, Dict, List, Optional

import pandas as pd

from esje.config import config
from esje.connection import Connection, manager
from esje.drivers.bigquery import BigQueryDriver
from esje.drivers.mysql import MySQLDriver
from esje.errors import ConnectionError, EsjeError, QueryError
from esje.extension import load_ipython_extension, unload_ipython_extension
from esje.prompts import resolve_bigquery_credentials, resolve_mysql_credentials

from esje.live import live_manager

__version__ = "0.3.1"


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


def connect(dialect: str = "mysql", **kwargs: Any) -> Connection:
    """Generic connection helper dispatching to dialect-specific connector."""
    d = dialect.lower()
    if d == "mysql":
        return connect_mysql(**kwargs)
    elif d in ("bigquery", "bq"):
        return connect_bigquery(**kwargs)
    else:
        raise ConnectionError(
            f"Unsupported dialect '{dialect}'. Supported dialects: 'mysql', 'bigquery'.",
            hint="Use connect_mysql() or connect_bigquery().",
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
    "connect_bigquery",
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


