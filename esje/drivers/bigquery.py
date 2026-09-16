"""Google BigQuery driver implementation for esje using google-cloud-bigquery or SQLAlchemy."""

import os
from typing import Any, Dict, Optional, Union

import pandas as pd

from esje.config import config
from esje.drivers.base import BaseDriver
from esje.errors import ConnectionError, QueryError

# BigQuery OAuth2 scopes required for read/write access
_BIGQUERY_SCOPES = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/cloud-platform",
]


class BigQueryDriver(BaseDriver):
    """BigQuery driver wrapping google-cloud-bigquery SDK and SQLAlchemy.

    Supports three authentication modes:
    - ``auth_method="browser"``  — launches a browser OAuth2 login flow (default when interactive).
    - ``auth_method="adc"``      — uses Application Default Credentials (gcloud auth application-default login).
    - ``auth_method="service_account"`` — uses a service account JSON key file.
    """

    def __init__(
        self,
        project: Optional[str] = None,
        dataset: str = "",
        credentials_path: Optional[str] = None,
        location: Optional[str] = None,
        auth_method: str = "browser",
        credentials_obj: Any = None,
        custom_client: Any = None,
        custom_engine: Any = None,
    ) -> None:
        self.project = project or ""
        self.dataset = dataset
        self.credentials_path = credentials_path
        self.location = location
        self.auth_method = auth_method
        self._credentials_obj = credentials_obj  # pre-built google.auth credentials object

        self._client = custom_client
        self._engine = custom_engine

        # Metadata for Connection handle display
        self.host = self.project or "bigquery"
        self.port = 443
        self.database = self.dataset
        if credentials_path:
            self.user = "service-account"
        elif auth_method == "browser":
            self.user = "oauth2-browser"
        else:
            self.user = "adc"

    @property
    def dialect(self) -> str:
        return "bigquery"

    def _build_browser_credentials(self) -> Any:
        """Launch Google OAuth2 browser login and return credentials."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        except ImportError:
            raise ConnectionError(
                "google-auth-oauthlib is not installed.",
                hint="Install it via: pip install 'esje[bigquery]' or pip install google-auth-oauthlib",
            )

        # Detect if running inside Jupyter/IPython (notebook environment)
        in_notebook = False
        try:
            from IPython import get_ipython
            ip = get_ipython()
            if ip is not None and hasattr(ip, "kernel"):
                in_notebook = True
        except ImportError:
            pass

        # Client config for native application OAuth2 (no client_secret required for installed apps)
        client_config = {
            "installed": {
                "client_id": "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com",
                "client_secret": "d-FL95Q19q7MQmFpd7hHD0Ty",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            }
        }

        if in_notebook:
            print(
                "\n🔐 esje | Login with Google required.\n"
                "   A browser window will open for authentication.\n"
                "   After signing in and granting access, return to your notebook.\n"
            )

        flow = InstalledAppFlow.from_client_config(client_config, scopes=_BIGQUERY_SCOPES)

        if in_notebook:
            # Use OOB (manual copy-paste) flow for Jupyter environments where
            # the redirect back to localhost may not work
            flow.run_local_server(port=0, open_browser=True)
        else:
            flow.run_local_server(port=0)

        return flow.credentials

    def _build_service_account_credentials(self) -> Any:
        """Build credentials from a service account JSON key file."""
        if not os.path.exists(self.credentials_path):
            raise ConnectionError(
                f"Service account file not found at: {self.credentials_path}",
                hint="Verify your service account JSON credentials file path.",
            )
        try:
            from google.oauth2 import service_account  # type: ignore
            return service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=_BIGQUERY_SCOPES,
            )
        except Exception as exc:
            raise ConnectionError(
                f"Failed to load service account credentials: {exc}",
                hint="Ensure the JSON key file is a valid Google Service Account key.",
            ) from (exc if config.verbose_errors else None)

    def connect(self) -> None:
        """Establish BigQuery client connection and run validation query."""
        if self._client is None and self._engine is None:
            try:
                from google.cloud import bigquery  # type: ignore
            except ImportError:
                raise ConnectionError(
                    "google-cloud-bigquery is not installed.",
                    hint="Install BigQuery support via: pip install 'esje[bigquery]'",
                )

            try:
                credentials = self._credentials_obj

                if credentials is None:
                    if self.auth_method == "service_account" and self.credentials_path:
                        credentials = self._build_service_account_credentials()
                    elif self.auth_method == "browser":
                        credentials = self._build_browser_credentials()
                    # auth_method == "adc": leave credentials as None → SDK uses ADC automatically

                client_kwargs: Dict[str, Any] = {}
                if self.project:
                    client_kwargs["project"] = self.project
                if credentials is not None:
                    client_kwargs["credentials"] = credentials
                if self.location:
                    client_kwargs["location"] = self.location
                if self.dataset and self.project:
                    client_kwargs["default_query_job_config"] = bigquery.QueryJobConfig(
                        default_dataset=f"{self.project}.{self.dataset}"
                    )

                self._client = bigquery.Client(**client_kwargs)

                # Discover project from client if not specified
                if not self.project and hasattr(self._client, "project"):
                    self.project = self._client.project or ""
                    self.host = self.project or "bigquery"

            except Exception as exc:
                if isinstance(exc, ConnectionError):
                    raise
                raise ConnectionError(
                    f"BigQuery connection failed: {exc}",
                    hint="Check GCP Project ID, authentication, and BigQuery API permissions.",
                ) from (exc if config.verbose_errors else None)

        # Validate connection with ping
        try:
            if self._client is not None:
                job = self._client.query("SELECT 1")
                job.result()
            elif self._engine is not None:
                from sqlalchemy import text
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
        except Exception as exc:
            raise ConnectionError(
                f"BigQuery ping check failed: {exc}",
                hint="Verify GCP Project ID, network connectivity, and BigQuery API quota.",
            ) from (exc if config.verbose_errors else None)

    def _translate_query(self, query: str) -> str:
        """Translate MySQL-style shorthand commands to BigQuery INFORMATION_SCHEMA equivalents."""
        import re
        q = query.strip().rstrip(";")
        ql = q.lower()

        # SHOW DATABASES  →  list all datasets in the project
        if re.match(r"^show\s+databases?$", ql) or re.match(r"^show\s+schemas?$", ql):
            return (
                f"SELECT schema_name AS `database`, creation_time, last_modified_time "
                f"FROM `{self.project}`.INFORMATION_SCHEMA.SCHEMATA"
                if self.project
                else "SELECT schema_name AS `database` FROM INFORMATION_SCHEMA.SCHEMATA"
            )

        # SHOW TABLES  /  SHOW TABLES IN dataset
        m = re.match(r"^show\s+tables?(?:\s+(?:in|from)\s+(\S+))?$", ql)
        if m:
            ds = m.group(1) or self.dataset or None
            if ds and self.project:
                return (
                    f"SELECT table_name, table_type, creation_time "
                    f"FROM `{self.project}.{ds}`.INFORMATION_SCHEMA.TABLES "
                    f"ORDER BY table_name"
                )
            elif self.project:
                return (
                    f"SELECT table_schema AS dataset, table_name, table_type "
                    f"FROM `{self.project}`.INFORMATION_SCHEMA.TABLES "
                    f"ORDER BY dataset, table_name"
                )

        # DESCRIBE table  /  DESC table
        m = re.match(r"^(?:describe|desc)\s+(\S+)$", ql)
        if m:
            ref = m.group(1).strip("`")
            parts = ref.split(".")
            if len(parts) == 3:
                proj, ds, tbl = parts
            elif len(parts) == 2:
                proj, ds, tbl = self.project, parts[0], parts[1]
            else:
                proj, ds, tbl = self.project, self.dataset, parts[0]
            return (
                f"SELECT column_name, data_type, is_nullable "
                f"FROM `{proj}.{ds}`.INFORMATION_SCHEMA.COLUMNS "
                f"WHERE table_name = '{tbl}' "
                f"ORDER BY ordinal_position"
            )

        return q

    def execute(self, query: str) -> Union[pd.DataFrame, Dict[str, Any]]:
        """Execute BigQuery SQL query and return DataFrame or execution summary."""
        if self._client is None and self._engine is None:
            raise ConnectionError("Not connected to BigQuery.")

        clean_query = self._translate_query(query)
        is_select = clean_query.lower().startswith(
            ("select", "with", "show", "describe", "desc", "explain")
        )

        try:
            if self._client is not None:
                query_job = self._client.query(clean_query)
                if is_select:
                    if config.use_pyarrow:
                        try:
                            return query_job.to_dataframe(dtype_backend="pyarrow")
                        except Exception:
                            return query_job.to_dataframe()
                    return query_job.to_dataframe()
                else:
                    query_job.result()
                    affected = getattr(query_job, "num_dml_affected_rows", None)
                    return {
                        "status": "BigQuery query executed successfully",
                        "affected_rows": affected if affected is not None else 0,
                    }

            elif self._engine is not None:
                from sqlalchemy import text
                with self._engine.connect() as conn:
                    if is_select:
                        if config.use_pyarrow:
                            try:
                                return pd.read_sql(text(query), con=conn, dtype_backend="pyarrow")
                            except Exception:
                                return pd.read_sql(text(query), con=conn)
                        return pd.read_sql(text(query), con=conn)
                    else:
                        result = conn.execute(text(query))
                        rowcount = getattr(result, "rowcount", 0)
                        return {"status": "BigQuery query executed successfully", "affected_rows": rowcount}

        except Exception as exc:
            raise QueryError(f"BigQuery Query Error: {exc}") from (
                exc if config.verbose_errors else None
            )

    def close(self) -> None:
        """Close BigQuery client or engine resources."""
        if self._client is not None:
            if hasattr(self._client, "close"):
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = None

        if self._engine is not None:
            try:
                self._engine.dispose()
            except Exception:
                pass
            self._engine = None
