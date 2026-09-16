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
    interactive_prompt: Optional[bool] = None,
) -> Dict[str, Any]:
    """Resolve BigQuery connection credentials from arguments, env vars, or interactive prompts.

    Args:
        project: GCP Project ID.
        dataset: Default BigQuery dataset name.
        credentials_path: Path to Google Service Account JSON key file.
        location: BigQuery dataset location (e.g. 'US', 'EU').
        interactive_prompt: Override interactive prompting behavior.

    Returns:
        Dict with keys: project, dataset, credentials_path, location.
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

    resolved_project = project if project is not None else env_project
    resolved_dataset = dataset if dataset is not None else env_dataset
    resolved_credentials_path = (
        credentials_path if credentials_path is not None else env_credentials_path
    )
    resolved_location = location if location is not None else env_location

    should_prompt = interactive_prompt if interactive_prompt is not None else is_interactive()

    if should_prompt:
        if resolved_project is None:
            project_input = input("GCP Project ID: ").strip()
            resolved_project = project_input if project_input else ""

        if resolved_dataset is None:
            dataset_input = input("BigQuery Dataset [optional]: ").strip()
            resolved_dataset = dataset_input if dataset_input else ""

        if resolved_credentials_path is None:
            cred_input = input("Service Account JSON Path [optional, press Enter for ADC]: ").strip()
            resolved_credentials_path = cred_input if cred_input else None

    return {
        "project": resolved_project or "",
        "dataset": resolved_dataset or "",
        "credentials_path": resolved_credentials_path,
        "location": resolved_location,
    }

