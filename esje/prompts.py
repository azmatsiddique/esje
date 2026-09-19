"""Credential prompting and environment variable resolution for esje."""

import getpass
import os
import sys
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from esje.errors import ConnectionError

# Load environment variables from .env if present
load_dotenv()


def is_interactive() -> bool:
    """Check if execution environment is interactive (TTY or IPython)."""
    if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        return True

    # Check for IPython interactive shell presence
    try:
        from IPython import get_ipython

        ip = get_ipython()
        if ip is not None:
            return True
    except ImportError:
        pass

    return False


def resolve_mysql_credentials(
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    interactive_prompt: Optional[bool] = None,
) -> Dict[str, Any]:
    """Resolve MySQL connection credentials from arguments, env vars, or interactive prompts.

    Args:
        host: Hostname or IP.
        port: Port number.
        user: Username.
        password: Password.
        database: Database name.
        interactive_prompt: Override interactive prompting behavior.

    Returns:
        Dict with keys: host, port, user, password, database.
    """
    env_host = os.getenv("ESJE_MYSQL_HOST") or os.getenv("MYSQL_HOST")
    env_port = os.getenv("ESJE_MYSQL_PORT") or os.getenv("MYSQL_PORT")
    env_user = os.getenv("ESJE_MYSQL_USER") or os.getenv("MYSQL_USER")
    env_password = os.getenv("ESJE_MYSQL_PASSWORD") or os.getenv("MYSQL_PASSWORD")
    env_database = os.getenv("ESJE_MYSQL_DATABASE") or os.getenv("MYSQL_DATABASE")

    # Resolve values with precedence: explicit arg -> env var -> interactive prompt
    resolved_host = host if host is not None else env_host
    resolved_port = port if port is not None else (int(env_port) if env_port else None)
    resolved_user = user if user is not None else env_user
    resolved_password = password if password is not None else env_password
    resolved_database = database if database is not None else env_database

    should_prompt = interactive_prompt if interactive_prompt is not None else is_interactive()

    if should_prompt:
        if resolved_host is None:
            host_input = input("Host [localhost]: ").strip()
            resolved_host = host_input if host_input else "localhost"

        if resolved_port is None:
            port_input = input("Port [3306]: ").strip()
            resolved_port = int(port_input) if port_input else 3306

        if resolved_user is None:
            resolved_user = input("Username: ").strip()

        if resolved_password is None:
            resolved_password = getpass.getpass("Password: ")

        if resolved_database is None:
            database_input = input("Database [optional]: ").strip()
            resolved_database = database_input if database_input else ""

    else:
        # Non-interactive fallback defaults
        if resolved_host is None:
            resolved_host = "localhost"
        if resolved_port is None:
            resolved_port = 3306
        if resolved_user is None:
            resolved_user = ""
        if resolved_password is None:
            resolved_password = ""
        if resolved_database is None:
            resolved_database = ""

    return {
        "host": resolved_host,
        "port": int(resolved_port),
        "user": resolved_user,
        "password": resolved_password,
        "database": resolved_database,
    }


def resolve_bigquery_credentials(
    project: Optional[str] = None,
    dataset: Optional[str] = None,
    credentials_path: Optional[str] = None,
    location: Optional[str] = None,
    auth_method: Optional[str] = None,
    interactive_prompt: Optional[bool] = None,
) -> Dict[str, Any]:
    """Resolve BigQuery connection credentials from arguments, env vars, or interactive prompts.

    Args:
        project: GCP Project ID.
        dataset: Default BigQuery dataset name.
        credentials_path: Path to Google Service Account JSON key file.
        location: BigQuery dataset location (e.g. 'US', 'EU').
        auth_method: One of 'browser', 'adc', or 'service_account'. Auto-detected if None.
        interactive_prompt: Override interactive prompting behavior.

    Returns:
        Dict with keys: project, dataset, credentials_path, location, auth_method.
    """
    env_project = (
        os.getenv("ESJE_BIGQUERY_PROJECT")
        or os.getenv("GCP_PROJECT")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("BIGQUERY_PROJECT")
    )
    env_dataset = os.getenv("ESJE_BIGQUERY_DATASET") or os.getenv("BIGQUERY_DATASET")
    env_credentials_path = (
        os.getenv("ESJE_BIGQUERY_CREDENTIALS_PATH")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
    env_location = os.getenv("ESJE_BIGQUERY_LOCATION") or os.getenv("BIGQUERY_LOCATION")
    env_auth_method = os.getenv("ESJE_BIGQUERY_AUTH_METHOD")

    resolved_project = project if project is not None else env_project
    resolved_dataset = dataset if dataset is not None else env_dataset
    resolved_credentials_path = (
        credentials_path if credentials_path is not None else env_credentials_path
    )
    resolved_location = location if location is not None else env_location
    resolved_auth_method = auth_method if auth_method is not None else env_auth_method

    should_prompt = interactive_prompt if interactive_prompt is not None else is_interactive()

    # Auto-determine auth_method if not specified:
    # - If a credentials path is available -> service_account
    # - If interactive -> browser (opens login in browser)
    # - Otherwise -> adc (gcloud ADC)
    if resolved_auth_method is None:
        if resolved_credentials_path:
            resolved_auth_method = "service_account"
        elif should_prompt:
            resolved_auth_method = "browser"
        else:
            resolved_auth_method = "adc"

    if should_prompt and resolved_auth_method != "browser":
        # Only prompt for project/dataset when not using browser login
        # (browser flow can auto-detect these from the token)
        if resolved_project is None:
            project_input = input("GCP Project ID: ").strip()
            resolved_project = project_input if project_input else ""

        if resolved_dataset is None:
            dataset_input = input("BigQuery Dataset [optional]: ").strip()
            resolved_dataset = dataset_input if dataset_input else ""

        if resolved_auth_method == "service_account" and resolved_credentials_path is None:
            cred_input = input("Service Account JSON Path: ").strip()
            resolved_credentials_path = cred_input if cred_input else None

    elif should_prompt and resolved_auth_method == "browser":
        # For browser login, only ask for project if we really need it
        if resolved_project is None:
            project_input = input("GCP Project ID [optional, press Enter to auto-detect]: ").strip()
            resolved_project = project_input if project_input else ""

    return {
        "project": resolved_project or "",
        "dataset": resolved_dataset or "",
        "credentials_path": resolved_credentials_path,
        "location": resolved_location,
        "auth_method": resolved_auth_method,
    }


def resolve_postgres_credentials(
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    sslmode: Optional[str] = None,
    interactive_prompt: Optional[bool] = None,
) -> Dict[str, Any]:
    """Resolve PostgreSQL connection credentials from arguments, env vars, or interactive prompts.

    Args:
        host: Hostname or IP.
        port: Port number.
        user: Username.
        password: Password.
        database: Database name.
        sslmode: SSL connection mode (e.g. 'require', 'prefer', 'disable').
        interactive_prompt: Override interactive prompting behavior.

    Returns:
        Dict with keys: host, port, user, password, database, sslmode.
    """
    env_host = os.getenv("ESJE_POSTGRES_HOST") or os.getenv("POSTGRES_HOST") or os.getenv("PGHOST")
    env_port = os.getenv("ESJE_POSTGRES_PORT") or os.getenv("POSTGRES_PORT") or os.getenv("PGPORT")
    env_user = os.getenv("ESJE_POSTGRES_USER") or os.getenv("POSTGRES_USER") or os.getenv("PGUSER")
    env_password = os.getenv("ESJE_POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD")
    env_database = os.getenv("ESJE_POSTGRES_DATABASE") or os.getenv("POSTGRES_DATABASE") or os.getenv("PGDATABASE")
    env_sslmode = os.getenv("ESJE_POSTGRES_SSLMODE") or os.getenv("PGSSLMODE")

    resolved_host = host if host is not None else env_host
    resolved_port = port if port is not None else (int(env_port) if env_port else None)
    resolved_user = user if user is not None else env_user
    resolved_password = password if password is not None else env_password
    resolved_database = database if database is not None else env_database
    resolved_sslmode = sslmode if sslmode is not None else env_sslmode

    should_prompt = interactive_prompt if interactive_prompt is not None else is_interactive()

    if should_prompt:
        if resolved_host is None:
            host_input = input("Host [localhost]: ").strip()
            resolved_host = host_input if host_input else "localhost"

        if resolved_port is None:
            port_input = input("Port [5432]: ").strip()
            resolved_port = int(port_input) if port_input else 5432

        if resolved_user is None:
            user_input = input("Username [postgres]: ").strip()
            resolved_user = user_input if user_input else "postgres"

        if resolved_password is None:
            resolved_password = getpass.getpass("Password: ")

        if resolved_database is None:
            database_input = input("Database [postgres]: ").strip()
            resolved_database = database_input if database_input else "postgres"

    else:
        # Non-interactive fallback defaults
        if resolved_host is None:
            resolved_host = "localhost"
        if resolved_port is None:
            resolved_port = 5432
        if resolved_user is None:
            resolved_user = "postgres"
        if resolved_password is None:
            resolved_password = ""
        if resolved_database is None:
            resolved_database = "postgres"

    return {
        "host": resolved_host,
        "port": int(resolved_port),
        "user": resolved_user,
        "password": resolved_password,
        "database": resolved_database,
        "sslmode": resolved_sslmode,
    }


def resolve_duckdb_credentials(
    database: Optional[str] = None,
    read_only: Optional[bool] = None,
    interactive_prompt: Optional[bool] = None,
) -> Dict[str, Any]:
    """Resolve DuckDB database path and settings from arguments, env vars, or interactive prompts.

    Args:
        database: Path to DuckDB file or ':memory:'.
        read_only: Whether to open in read-only mode.
        interactive_prompt: Override interactive prompting behavior.

    Returns:
        Dict with keys: database, read_only.
    """
    env_database = os.getenv("ESJE_DUCKDB_DATABASE") or os.getenv("DUCKDB_DATABASE")
    env_read_only = os.getenv("ESJE_DUCKDB_READ_ONLY")

    resolved_database = database if database is not None else env_database
    if read_only is not None:
        resolved_read_only = read_only
    elif env_read_only is not None:
        resolved_read_only = env_read_only.lower() in ("true", "1", "yes")
    else:
        resolved_read_only = False

    should_prompt = interactive_prompt if interactive_prompt is not None else is_interactive()

    if should_prompt:
        if resolved_database is None:
            db_input = input("Database path [:memory:]: ").strip()
            resolved_database = db_input if db_input else ":memory:"
    else:
        if resolved_database is None:
            resolved_database = ":memory:"

    return {
        "database": resolved_database,
        "read_only": resolved_read_only,
    }



